"""
Para Komuta Merkezi - Streamlit Version
Portfolio Management Platform with Dark Theme
"""

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from time import time
import threading

# Page Config
st.set_page_config(
    page_title="Para Komuta Merkezi",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"  # Hide sidebar by default (Flask app doesn't have sidebar)
)

# Custom CSS - Light Theme (Clean and Professional)
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #f8fafc;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }

    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #059669;
        font-weight: 700;
    }

    [data-testid="stMetricLabel"] {
        color: #64748b;
        font-weight: 500;
    }

    /* Headers - Daha büyük ve kalın siyah */
    h1 {
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 3rem !important;
    }

    h2 {
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 2rem !important;
    }

    h3 {
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 1.75rem !important;
    }

    h4 {
        color: #000000 !important;
        font-weight: 700 !important;
        font-size: 1.5rem !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f1f5f9;
        padding: 0.5rem;
        border-radius: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        color: #475569;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        border: 1px solid #e2e8f0;
    }

    .stTabs [aria-selected="true"] {
        background-color: #3b82f6;
        color: white;
        border-color: #3b82f6;
    }

    /* Dataframes - Koyu siyah ve büyük yazı (2 punto daha büyük) */
    [data-testid="stDataFrame"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
    }

    [data-testid="stDataFrame"] table {
        font-size: 1.3rem !important;
        color: #000000 !important;
        font-weight: 900 !important;
    }

    [data-testid="stDataFrame"] th {
        font-size: 1.4rem !important;
        color: #000000 !important;
        font-weight: 900 !important;
    }

    [data-testid="stDataFrame"] td {
        font-size: 1.3rem !important;
        color: #000000 !important;
        font-weight: 900 !important;
    }

    /* Buttons */
    .stButton>button {
        background-color: #10b981;
        color: white;
        border-radius: 0.5rem;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }

    .stButton>button:hover {
        background-color: #059669;
    }

    /* Input fields */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>select {
        background-color: #ffffff;
        color: #0f172a;
        border: 1px solid #cbd5e1;
    }

    /* Success/Error boxes */
    .stSuccess {
        background-color: #d1fae5;
        color: #065f46;
        border: 1px solid #6ee7b7;
    }

    .stError {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fca5a5;
    }

    .stInfo {
        background-color: #dbeafe;
        color: #1e40af;
        border: 1px solid #93c5fd;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CREDENTIALS CHECK
# =============================================================================

# Credentials kontrolü - Eğer yüklenmemişse ana sayfaya yönlendir
if 'credentials_data' not in st.session_state or not st.session_state.get('credentials_loaded', False):
    st.error("❌ Credentials yüklenmemiş! Lütfen ana sayfadan credentials.json dosyanızı yükleyin.")
    if st.button("🏠 Ana Sayfaya Git"):
        st.switch_page("Home.py")
    st.stop()

# Cache for Google Sheets connection
@st.cache_resource
def get_sheets_client(_creds_data):
    """Connect to Google Sheets using credentials from session state."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(_creds_data, scope)
    client = gspread.authorize(creds)
    return client.open("PKM Database")

# Price cache to avoid too many API calls
price_cache = {}
cache_lock = threading.Lock()
CACHE_DURATION = 1800  # 30 minutes (daha az API çağrısı = daha hızlı)

def parse_turkish_decimal(value):
    """
    Parse Turkish decimal format (comma as decimal separator) to float.
    Google Sheets with Turkish locale returns decimals as "16,23" instead of "16.23"
    """
    if value is None or value == '':
        return 0.0

    # If already a number, return it
    if isinstance(value, (int, float)):
        return float(value)

    # If string, parse Turkish format
    if isinstance(value, str):
        # Remove any spaces and TL currency symbol
        value = value.strip().replace(' TL', '').replace('TL', '').strip()

        # Replace comma with period for decimal parsing
        value = value.replace(',', '.')

        try:
            return float(value)
        except ValueError:
            return 0.0

    return 0.0

def format_currency(value):
    """Format currency value, hiding if privacy mode is active."""
    if st.session_state.get('privacy_mode', False):
        return "₺***********"
    return f"₺{value:,.2f}"

def format_number(value, decimals=2):
    """Format number, hiding if privacy mode is active."""
    if st.session_state.get('privacy_mode', False):
        return "***"
    if decimals == 0:
        return f"{value:,.0f}"
    return f"{value:,.{decimals}f}"

def get_sheet_data_as_dict(worksheet):
    """
    Get worksheet data as list of dictionaries, properly handling Turkish decimal format.
    This replaces get_all_records() which incorrectly parses Turkish decimals.
    """
    # Get all values as raw strings
    all_values = worksheet.get_all_values()

    if not all_values or len(all_values) < 2:
        return []

    # First row is headers
    headers = all_values[0]

    # Convert rows to dictionaries
    records = []
    for row in all_values[1:]:  # Skip header
        if not any(row):  # Skip empty rows
            continue

        record = {}
        for i, header in enumerate(headers):
            if i < len(row):
                value = row[i]

                # Parse numeric columns with Turkish decimal format
                if header in ['amount', 'buy_price', 'manual_price', 'total_value', 'total_debt',
                              'sell_price', 'profit_loss_percent']:
                    record[header] = parse_turkish_decimal(value)
                # Parse ID columns as integers
                elif header == 'ID':
                    try:
                        record[header] = int(value) if value else 0
                    except ValueError:
                        record[header] = 0
                # Everything else as string
                else:
                    record[header] = str(value)
            else:
                record[header] = ''

        records.append(record)

    return records

def fetch_price(symbol, asset_type):
    """Fetch current price using yfinance with caching and timeout protection."""
    cache_key = f"{asset_type}:{symbol}"

    # Check cache
    with cache_lock:
        if cache_key in price_cache:
            cached_data = price_cache[cache_key]
            if time() - cached_data['timestamp'] < CACHE_DURATION:
                return cached_data['price']

    try:
        # Hisse senetleri için .IS ekleme
        if asset_type == 'hisse' and not symbol.endswith('.IS'):
            symbol = symbol + '.IS'

        ticker = yf.Ticker(symbol)

        # TIMEOUT: Maksimum 5 saniye (agresif!)
        data = ticker.history(period='1d', timeout=5)

        if not data.empty:
            price = data['Close'].iloc[-1]

            # Cache the price
            with cache_lock:
                price_cache[cache_key] = {
                    'price': price,
                    'timestamp': time()
                }

            return price
        else:
            print(f"⚠️ {symbol} - Veri boş döndü")

    except TimeoutError as e:
        print(f"⏱️ {symbol} - TIMEOUT (5 saniye aşıldı), alış fiyatı kullanılacak")
    except Exception as e:
        print(f"❌ {symbol} - Hata: {str(e)[:100]}")

    return None

def get_usd_tl_rate():
    """Get USD/TL exchange rate - tries multiple tickers with timeout."""
    # Birden fazla ticker dene (Yahoo Finance bazen ticker değiştiriyor)
    tickers_to_try = ["USDTRY=X", "TRY=X", "TRYUSD=X"]

    for ticker_symbol in tickers_to_try:
        try:
            ticker = yf.Ticker(ticker_symbol)
            # TIMEOUT: Maksimum 5 saniye (agresif!)
            data = ticker.history(period='1d', timeout=5)
            if not data.empty:
                rate = data['Close'].iloc[-1]
                # TRY=X tersten geliyorsa düzelt
                if ticker_symbol == "TRY=X" and rate < 1:
                    rate = 1 / rate
                # Makul aralıkta mı kontrol et (30-50 TL arası)
                if 30 <= rate <= 50:
                    print(f"✅ USD/TL kuru: {rate:.4f} ({ticker_symbol})")
                    return rate
        except TimeoutError:
            print(f"⏱️ {ticker_symbol} timeout - sonrakini deniyorum")
            continue
        except Exception as e:
            print(f"❌ {ticker_symbol} hata: {str(e)[:50]}")
            continue

    # Hiçbiri çalışmazsa fallback
    print("⚠️ USD/TL kuru çekilemedi, fallback kullanılıyor: 42.0")
    return 42.0  # Güncel fallback değer (manuel güncelle)

def get_market_data():
    """Get market data for dashboard."""
    market_data = {}

    try:
        # USD/TL
        usd_tl = get_usd_tl_rate()
        market_data['usd_tl'] = usd_tl

        # Gold (USD)
        gold_ticker = yf.Ticker("GC=F")
        gold_data = gold_ticker.history(period='1d')
        if not gold_data.empty:
            market_data['gold'] = gold_data['Close'].iloc[-1]

        # Bitcoin
        btc_ticker = yf.Ticker("BTC-USD")
        btc_data = btc_ticker.history(period='1d')
        if not btc_data.empty:
            market_data['bitcoin'] = btc_data['Close'].iloc[-1]

        # BIST100
        bist_ticker = yf.Ticker("XU100.IS")
        bist_data = bist_ticker.history(period='1d')
        if not bist_data.empty:
            market_data['bist100'] = bist_data['Close'].iloc[-1]
    except Exception as e:
        st.warning(f"Piyasa verisi alma hatası: {e}")

    return market_data

def calculate_portfolio_value(assets_df):
    """Calculate total portfolio value - EXACTLY like Flask app."""
    if assets_df.empty:
        return 0

    usd_tl_rate = get_usd_tl_rate()
    total_value = 0

    for _, asset in assets_df.iterrows():
        # Manuel veri kaynağı kontrolü (EXACTLY like Flask app)
        if asset['data_source'] == 'manuel':
            current_price = asset['manual_price']
        else:
            # Otomatik fiyat getir
            current_price = fetch_price(asset['symbol'], asset['asset_type'])
            if current_price is None:
                # Fiyat alınamazsa alış fiyatını kullan (EXACTLY like Flask app)
                current_price = asset['buy_price']

        asset_value = asset['amount'] * current_price

        # Kripto paralar USD bazlı, TL'ye çevir (EXACTLY like Flask app)
        if asset['asset_type'] == 'kripto':
            asset_value = asset_value * usd_tl_rate

        total_value += asset_value

    return total_value

def calculate_asset_distribution(assets_df):
    """Calculate asset distribution by type - EXACTLY like Flask app."""
    if assets_df.empty:
        return None

    usd_tl_rate = get_usd_tl_rate()
    distribution = {}

    for _, asset in assets_df.iterrows():
        asset_type = asset['asset_type']

        # Get current price
        if asset['data_source'] == 'manuel':
            current_price = asset['manual_price']
        else:
            current_price = fetch_price(asset['symbol'], asset['asset_type'])
            if current_price is None:
                current_price = asset['buy_price']

        value = asset['amount'] * current_price

        # Kripto paralar USD bazlı, TL'ye çevir
        if asset_type == 'kripto':
            value = value * usd_tl_rate

        if asset_type in distribution:
            distribution[asset_type] += value
        else:
            distribution[asset_type] = value

    # Kategori isimleri - Flask uygulamasındaki gibi
    labels_map = {
        'hisse': 'Hisse Senetleri',
        'kripto': 'Kripto Paralar',
        'hisse_fonlari': 'Hisse Fonları',
        'Nakit_ve_Benzeri': 'Nakit ve Benzeri',
        'emtia': 'Emtia'
    }

    labels = [labels_map.get(k, k) for k in distribution.keys()]
    values = list(distribution.values())

    return {'labels': labels, 'values': values}

def main():
    # Header with title and action buttons (EXACTLY like Flask app)
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

    with col1:
        st.title("💰 Para Komuta Merkezi")
        st.markdown("#### Portföy Yönetim Platformu")

    with col2:
        # Initialize privacy mode
        if 'privacy_mode' not in st.session_state:
            st.session_state.privacy_mode = False

        # Privacy mode toggle button (Flask'taki "Göster" butonu gibi)
        if st.button("👁️ Göster" if st.session_state.privacy_mode else "🔒 Gizle", use_container_width=True):
            st.session_state.privacy_mode = not st.session_state.privacy_mode
            st.rerun()

    with col3:
        # Notes button (Flask'taki "Notlar" butonu gibi)
        if st.button("📝 Notlar", use_container_width=True):
            st.session_state.show_notes_modal = not st.session_state.get('show_notes_modal', False)
            st.rerun()

    with col4:
        # Ana Sayfa butonu placeholder (Flask'taki gibi)
        st.button("🏠 Ana Sayfa", use_container_width=True, disabled=True)

    # Notes Modal (Flask uygulamasındaki gibi modal popup)
    if st.session_state.get('show_notes_modal', False):
        st.markdown("---")
        st.markdown("### 📝 Notlar")

        # Initialize notes in session state
        if 'notes' not in st.session_state:
            st.session_state.notes = []

        # Add note form
        with st.form("add_note_form", clear_on_submit=True):
            note_text = st.text_area("Yeni not ekle", placeholder="Buraya notunuzu yazın...", height=100)

            col_submit, col_close = st.columns(2)
            with col_submit:
                submitted = st.form_submit_button("➕ Not Ekle", use_container_width=True)
            with col_close:
                if st.form_submit_button("❌ Kapat", use_container_width=True):
                    st.session_state.show_notes_modal = False
                    st.rerun()

            if submitted and note_text.strip():
                new_note = {
                    'id': len(st.session_state.notes) + 1,
                    'text': note_text.strip(),
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'date': datetime.now().strftime("%d.%m.%Y %H:%M")
                }
                st.session_state.notes.append(new_note)
                st.success("✅ Not eklendi!")
                st.rerun()

        # Display notes
        if st.session_state.notes:
            st.markdown(f"**Toplam {len(st.session_state.notes)} not**")
            st.divider()

            # Display in reverse order (newest first)
            for note in reversed(st.session_state.notes):
                col1, col2 = st.columns([5, 1])

                with col1:
                    st.markdown(f"<small style='color: #64748b;'>{note['date']}</small>", unsafe_allow_html=True)
                    st.markdown(note['text'])

                with col2:
                    if st.button("🗑️", key=f"delete_note_{note['id']}", help="Notu sil"):
                        st.session_state.notes = [n for n in st.session_state.notes if n['id'] != note['id']]
                        st.rerun()

                st.divider()
        else:
            st.info("📭 Henüz not eklenmedi")

        st.markdown("---")

    try:
        # Connect to database using credentials from session state
        db = get_sheets_client(st.session_state['credentials_data'])
        assets_sheet = db.worksheet("assets")
        debts_sheet = db.worksheet("debts")

        # Get data - Using custom function to handle Turkish decimal format
        assets_data = get_sheet_data_as_dict(assets_sheet)
        debts_data = get_sheet_data_as_dict(debts_sheet)

        # Convert to DataFrames
        assets_df = pd.DataFrame(assets_data) if assets_data else pd.DataFrame()
        debts_df = pd.DataFrame(debts_data) if debts_data else pd.DataFrame()

        # Calculate totals
        total_wealth = calculate_portfolio_value(assets_df) if not assets_df.empty else 0
        total_debt = debts_df['amount'].sum() if not debts_df.empty and 'amount' in debts_df.columns else 0
        net_worth = total_wealth - total_debt

        # Dashboard - Top Metrics (with privacy mode support) - Çerçeveli ve modern tasarım
        st.markdown("### 📊 Finansal Özet")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                border: 3px solid #10b981;
                border-radius: 1rem;
                padding: 1.5rem;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <div style="color: #065f46; font-size: 1.1rem; font-weight: 700; margin-bottom: 0.5rem;">
                    💰 Toplam Varlık
                </div>
                <div style="color: #000000; font-size: 2.2rem; font-weight: 900;">
                    {format_currency(total_wealth)}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
                border: 3px solid #ef4444;
                border-radius: 1rem;
                padding: 1.5rem;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <div style="color: #991b1b; font-size: 1.1rem; font-weight: 700; margin-bottom: 0.5rem;">
                    💳 Toplam Borç
                </div>
                <div style="color: #000000; font-size: 2.2rem; font-weight: 900;">
                    {format_currency(total_debt)}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
                border: 3px solid #3b82f6;
                border-radius: 1rem;
                padding: 1.5rem;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <div style="color: #1e40af; font-size: 1.1rem; font-weight: 700; margin-bottom: 0.5rem;">
                    💎 Net Değer
                </div>
                <div style="color: #000000; font-size: 2.2rem; font-weight: 900;">
                    {format_currency(net_worth)}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Market Data - Colored Cards (EXACTLY like Flask app)
        st.markdown("### 📈 Piyasa Verileri")
        market_data = get_market_data()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if 'usd_tl' in market_data:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
                    border: 2px solid #60a5fa;
                    border-radius: 0.5rem;
                    padding: 1rem;
                    text-align: center;
                ">
                    <div style="color: #93c5fd; font-size: 0.875rem; margin-bottom: 0.25rem;">
                        💵 USD/TL Kuru
                    </div>
                    <div style="color: #dbeafe; font-size: 1.25rem; font-weight: bold;">
                        ₺{market_data['usd_tl']:.4f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            if 'gold' in market_data:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #78350f 0%, #fbbf24 100%);
                    border: 2px solid #fcd34d;
                    border-radius: 0.5rem;
                    padding: 1rem;
                    text-align: center;
                ">
                    <div style="color: #fde68a; font-size: 0.875rem; margin-bottom: 0.25rem;">
                        🥇 Ons Altın
                    </div>
                    <div style="color: #fef3c7; font-size: 1.25rem; font-weight: bold;">
                        ${market_data['gold']:,.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with col3:
            if 'bitcoin' in market_data:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #7c2d12 0%, #f97316 100%);
                    border: 2px solid #fb923c;
                    border-radius: 0.5rem;
                    padding: 1rem;
                    text-align: center;
                ">
                    <div style="color: #fed7aa; font-size: 0.875rem; margin-bottom: 0.25rem;">
                        ₿ Bitcoin
                    </div>
                    <div style="color: #ffedd5; font-size: 1.25rem; font-weight: bold;">
                        ${market_data['bitcoin']:,.0f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with col4:
            if 'bist100' in market_data:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #14532d 0%, #22c55e 100%);
                    border: 2px solid #4ade80;
                    border-radius: 0.5rem;
                    padding: 1rem;
                    text-align: center;
                ">
                    <div style="color: #bbf7d0; font-size: 0.875rem; margin-bottom: 0.25rem;">
                        📊 BIST 100
                    </div>
                    <div style="color: #dcfce7; font-size: 1.25rem; font-weight: bold;">
                        {market_data['bist100']:,.0f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # Charts Section
        st.markdown("### 📊 Grafikler")
        chart_col1, chart_col2 = st.columns([1, 2])

        with chart_col1:
            # Asset Distribution Pie Chart - Çerçeveli ve büyük tasarım
            if not assets_df.empty:
                # Başlık ve çerçeve container
                st.markdown("""
                <div style="
                    background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
                    border: 3px solid #cbd5e1;
                    border-radius: 1rem;
                    padding: 1.5rem;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    margin-bottom: 1rem;
                ">
                    <h4 style="text-align: center; color: #000000; font-weight: 900; margin-bottom: 1rem;">
                        📊 Varlık Dağılımı
                    </h4>
                </div>
                """, unsafe_allow_html=True)

                distribution = calculate_asset_distribution(assets_df)

                if distribution:
                    # Renk haritası - Flask uygulamasındaki gibi
                    color_map = {
                        'Hisse Senetleri': '#ef4444',      # KIRMIZI
                        'Kripto Paralar': '#3b82f6',       # MAVİ
                        'Emtia': '#fbbf24',                # SARI
                        'Nakit ve Benzeri': '#22c55e',     # YEŞİL
                        'Hisse Fonları': '#8b5cf6'         # MOR
                    }

                    colors = [color_map.get(label, '#9ca3af') for label in distribution['labels']]

                    fig = go.Figure(data=[go.Pie(
                        labels=distribution['labels'],
                        values=distribution['values'],
                        marker=dict(colors=colors, line=dict(color='#1f2937', width=4)),
                        textinfo='label+percent',
                        textposition='inside',
                        # Yüzde rakamlarını 1 punto büyüt ve kalın yap
                        textfont=dict(size=16, color='white', family='Arial Black'),
                        hovertemplate='<b>%{label}</b><br>₺%{value:,.2f}<br>%{percent}<extra></extra>',
                        pull=[0.05] * len(distribution['labels'])  # Dilimler arasında hafif boşluk
                    )])

                    fig.update_layout(
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            yanchor="middle",
                            y=0.5,
                            xanchor="left",
                            x=1.05,
                            font=dict(color='#000000', size=13, family='Arial')
                        ),
                        paper_bgcolor='#ffffff',
                        plot_bgcolor='#ffffff',
                        height=500,  # Daha büyük yükseklik
                        margin=dict(l=20, r=120, t=20, b=20)
                    )

                    st.plotly_chart(fig, use_container_width=True)

        with chart_col2:
            # Asset History Line Chart - Modern ve dramatik görünüm
            st.markdown("#### Toplam Varlığın Tarihsel Değişimi")
            history_sheet = db.worksheet("asset_history")
            history_data = get_sheet_data_as_dict(history_sheet)

            if history_data:
                dates = [h['date'] for h in history_data]
                values = [h['total_value'] for h in history_data]

                # Y eksenini daha dar tutarak yükselişi keskinleştir
                min_value = min(values)
                max_value = max(values)
                value_range = max_value - min_value

                # Y ekseninin alt sınırını minimum değerin %95'ine ayarla (yükseliş daha keskin görünsün)
                y_min = min_value - (value_range * 0.05)
                y_max = max_value + (value_range * 0.05)

                # Privacy mode: Gizleme özelliği aktifken rakamları gizle
                privacy_mode = st.session_state.get('privacy_mode', False)

                # Hover template - Privacy mode'da rakam gösterme
                if privacy_mode:
                    hover_template = '<b>%{x}</b><br><b style="font-size: 1.2em;">******</b><extra></extra>'
                else:
                    hover_template = '<b>%{x}</b><br><b style="font-size: 1.2em;">₺%{y:,.2f}</b><extra></extra>'

                fig = go.Figure(data=[go.Scatter(
                    x=dates,
                    y=values,
                    mode='lines+markers',
                    name='Toplam Varlık (TL)',
                    line=dict(
                        color='#10b981',
                        width=5,
                        shape='spline',  # Smooth curve
                        smoothing=0.3
                    ),
                    fill='tozeroy',
                    fillcolor='rgba(16, 185, 129, 0.15)',
                    marker=dict(
                        size=10,
                        color='#10b981',
                        line=dict(color='#ffffff', width=3),
                        symbol='circle'
                    ),
                    hovertemplate=hover_template
                )])

                # Y ekseni tick labels - Privacy mode'da "******" göster
                if privacy_mode:
                    # Y ekseninde 5 adet "******" göster
                    num_ticks = 5
                    tick_values = [y_min + (y_max - y_min) * i / (num_ticks - 1) for i in range(num_ticks)]
                    tick_texts = ["******"] * num_ticks

                    yaxis_config = dict(
                        title=dict(text='<b>Toplam Varlık (₺)</b>', font=dict(color='#000000', size=16, family='Arial Black')),
                        tickfont=dict(color='#1f2937', size=13, family='Arial'),
                        gridcolor='#e5e7eb',
                        showgrid=True,
                        linecolor='#9ca3af',
                        linewidth=2,
                        range=[y_min, y_max],
                        tickmode='array',
                        tickvals=tick_values,
                        ticktext=tick_texts
                    )
                else:
                    yaxis_config = dict(
                        title=dict(text='<b>Toplam Varlık (₺)</b>', font=dict(color='#000000', size=16, family='Arial Black')),
                        tickfont=dict(color='#1f2937', size=13, family='Arial'),
                        gridcolor='#e5e7eb',
                        showgrid=True,
                        tickformat=',.0f',
                        linecolor='#9ca3af',
                        linewidth=2,
                        range=[y_min, y_max]
                    )

                fig.update_layout(
                    xaxis=dict(
                        title=dict(text='<b>Tarih</b>', font=dict(color='#000000', size=16, family='Arial Black')),
                        tickfont=dict(color='#1f2937', size=12, family='Arial'),
                        gridcolor='#e5e7eb',
                        showgrid=True,
                        linecolor='#9ca3af',
                        linewidth=2
                    ),
                    yaxis=yaxis_config,
                    paper_bgcolor='#ffffff',
                    plot_bgcolor='#f9fafb',
                    height=450,
                    margin=dict(l=80, r=30, t=30, b=70),
                    hovermode='x unified',
                    font=dict(color='#000000', size=13),
                    hoverlabel=dict(
                        bgcolor='#ffffff',
                        font_size=14,
                        font_family='Arial',
                        bordercolor='#10b981'
                    )
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 Henüz tarihsel veri bulunmuyor. 'Günlük Snapshot Kaydet' butonuna tıklayarak veri eklemeye başlayın.")

        st.divider()

        # Tabs for different asset types
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🏠 Hisse Senetleri",
            "₿ Kripto",
            "📊 Hisse Fonları",
            "💵 Nakit",
            "🥇 Emtia",
            "💳 Borçlar",
            "🔒 Kapanan Pozisyonlar"
        ])

        with tab1:
            show_assets_tab(assets_df, assets_sheet, "hisse", "Hisse Senedi")

        with tab2:
            show_assets_tab(assets_df, assets_sheet, "kripto", "Kripto Para")

        with tab3:
            show_assets_tab(assets_df, assets_sheet, "hisse_fonlari", "Hisse Fonu")

        with tab4:
            show_assets_tab(assets_df, assets_sheet, "Nakit_ve_Benzeri", "Nakit")

        with tab5:
            show_assets_tab(assets_df, assets_sheet, "emtia", "Emtia")

        with tab6:
            show_debts_tab(debts_df, debts_sheet)

        with tab7:
            show_closed_positions_tab(db)

        st.divider()

        # Daily Snapshot Button
        col_center = st.columns([1, 2, 1])[1]
        with col_center:
            if st.button("💾 Günlük Snapshot Kaydet", use_container_width=True, type="primary"):
                try:
                    date_str = datetime.now().strftime('%Y-%m-%d')

                    # Save to asset_history
                    history_sheet = db.worksheet("asset_history")
                    history_data = get_sheet_data_as_dict(history_sheet)

                    # Get max ID
                    max_id = max([h.get('ID', 0) for h in history_data], default=0) if history_data else 0
                    new_id = max_id + 1

                    # Add new history record
                    history_sheet.append_row([new_id, date_str, total_wealth])

                    # Save to debt_history
                    debt_history_sheet = db.worksheet("debt_history")
                    debt_hist_data = get_sheet_data_as_dict(debt_history_sheet)

                    # Get max ID
                    max_id = max([d.get('ID', 0) for d in debt_hist_data], default=0) if debt_hist_data else 0
                    new_id = max_id + 1

                    # Add new debt history record
                    debt_history_sheet.append_row([new_id, date_str, total_debt])

                    st.success(f"✅ Günlük snapshot başarıyla kaydedildi! ({date_str})")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Snapshot kaydedilemedi: {str(e)}")

    except Exception as e:
        st.error(f"❌ Hata oluştu: {str(e)}")
        st.exception(e)

def show_assets_tab(assets_df, sheet, asset_type, type_label):
    """Show assets for a specific type."""

    # Filter assets by type
    if not assets_df.empty and 'asset_type' in assets_df.columns:
        filtered_df = assets_df[assets_df['asset_type'] == asset_type].copy()
    else:
        filtered_df = pd.DataFrame()

    # PRE-CALCULATE EVERYTHING ONCE - Store in session state with unique key per asset_type
    display_cache_key = f"display_data_{asset_type}"

    # Only recalculate if not in cache
    if display_cache_key not in st.session_state and not filtered_df.empty:
        # Calculate all display data ONCE
        usd_tl_rate = get_usd_tl_rate()
        all_display_data = []

        for _, asset in filtered_df.iterrows():
            if asset['data_source'] == 'manuel':
                current_price = asset['manual_price']
            else:
                current_price = fetch_price(asset['symbol'], asset['asset_type'])
                if current_price is None:
                    current_price = asset['buy_price']

            current_value = asset['amount'] * current_price

            # Convert crypto to TL
            if asset['asset_type'] == 'kripto':
                current_value_tl = current_value * usd_tl_rate
            else:
                current_value_tl = current_value

            profit_loss = ((current_price - asset['buy_price']) / asset['buy_price'] * 100) if asset['buy_price'] > 0 else 0

            # Add basket badge for stocks
            basket_display = ""
            if asset_type == 'hisse' and asset.get('basket'):
                basket_emoji = {
                    'buffet': '⭐',
                    'tesla': '⚡',
                    'tosuncuk': '💖'
                }
                basket_display = basket_emoji.get(asset['basket'], '')

            row_data = {
                'Sembol': f"{basket_display} {asset['symbol']}" if basket_display else asset['symbol'],
                'Miktar': format_number(asset['amount'], decimals=4),
                'Alış Fiyatı': format_currency(asset['buy_price']),
                'Güncel Fiyat': format_currency(current_price),
                'Güncel Değer': format_currency(current_value_tl),
                'K/Z %': f"{profit_loss:+.2f}%",
                'Kaynak': asset['data_source'],
                'ID': asset['ID'],
                'basket': asset.get('basket', '')  # Store basket for filtering
            }

            # Add basket column only for stocks
            if asset_type == 'hisse':
                basket_names = {
                    'buffet': 'Buffet',
                    'tesla': 'Tesla',
                    'tosuncuk': 'Tosuncuk',
                    '': '-'
                }
                row_data['Sepet'] = basket_names.get(asset.get('basket', ''), '-')

            all_display_data.append(row_data)

        # Store in session state
        st.session_state[display_cache_key] = all_display_data

    # BASKET FILTER BUTTONS - Only for stocks (hisse)
    if asset_type == 'hisse' and not filtered_df.empty:
        st.markdown("#### 🗂️ Sepet Filtresi")

        # Initialize basket filter in session state
        if f"basket_filter_{asset_type}" not in st.session_state:
            st.session_state[f"basket_filter_{asset_type}"] = "all"

        # Radio buttons instead of individual buttons - MUCH FASTER
        current_filter = st.radio(
            "Sepet seçin:",
            options=["all", "buffet", "tesla", "tosuncuk"],
            format_func=lambda x: {
                "all": "📋 Tümü",
                "buffet": "⭐ Buffet Sepeti",
                "tesla": "⚡ Tesla Sepeti",
                "tosuncuk": "💖 Tosuncuk Sepeti"
            }[x],
            key=f"basket_filter_{asset_type}",
            horizontal=True,
            label_visibility="collapsed"
        )

        st.divider()

    # Add asset button
    if st.button(f"➕ Yeni {type_label} Ekle", key=f"add_{asset_type}"):
        st.session_state[f"show_add_modal_{asset_type}"] = True

    # Show add form if button clicked
    if st.session_state.get(f"show_add_modal_{asset_type}", False):
        with st.form(f"add_form_{asset_type}"):
            st.subheader(f"Yeni {type_label} Ekle")

            col1, col2 = st.columns(2)

            with col1:
                symbol = st.text_input("Sembol", key=f"symbol_{asset_type}")
                amount = st.number_input("Miktar", min_value=0.0, step=0.01, key=f"amount_{asset_type}")
                buy_price = st.number_input("Alış Fiyatı (₺)", min_value=0.0, step=0.01, key=f"buy_price_{asset_type}")

            with col2:
                data_source = st.selectbox("Veri Kaynağı", ["auto", "manuel"], key=f"data_source_{asset_type}")
                manual_price = 0
                if data_source == "manuel":
                    manual_price = st.number_input("Manuel Fiyat", min_value=0.0, step=0.01, key=f"manual_price_{asset_type}")
                basket = st.selectbox("Sepet (Opsiyonel)", ["", "buffet", "tesla", "tosuncuk"], key=f"basket_{asset_type}")

            col_submit, col_cancel = st.columns(2)

            with col_submit:
                submitted = st.form_submit_button("💾 Kaydet", use_container_width=True)

            with col_cancel:
                cancelled = st.form_submit_button("❌ İptal", use_container_width=True)

            if submitted and symbol and amount > 0 and buy_price > 0:
                # Get max ID
                all_data = get_sheet_data_as_dict(sheet)
                max_id = max([item.get("ID", 0) for item in all_data], default=0)
                new_id = max_id + 1

                # Add to sheet
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sheet.append_row([
                    new_id,
                    asset_type,
                    symbol.upper(),
                    amount,
                    buy_price,
                    data_source,
                    manual_price,
                    basket,
                    now
                ])

                st.success(f"✅ {symbol.upper()} başarıyla eklendi!")
                st.session_state[f"show_add_modal_{asset_type}"] = False
                st.rerun()

            if cancelled:
                st.session_state[f"show_add_modal_{asset_type}"] = False
                st.rerun()

    # Show assets table
    if not filtered_df.empty and display_cache_key in st.session_state:
        # Get cached display data
        all_display_data = st.session_state[display_cache_key]

        # Filter by basket if needed (ONLY FOR STOCKS)
        if asset_type == 'hisse':
            current_filter = st.session_state.get(f"basket_filter_{asset_type}", "all")
            if current_filter != "all":
                display_data = [row for row in all_display_data if row.get('basket') == current_filter]
            else:
                display_data = all_display_data
        else:
            display_data = all_display_data

        st.markdown(f"#### Toplam: {len(display_data)} {type_label}")

        # TABLE HEADERS
        if asset_type == 'hisse':
            header_cols = st.columns([1.2, 0.8, 0.8, 0.8, 1, 0.8, 0.6, 0.8, 1.5])
        else:
            header_cols = st.columns([1.2, 0.8, 0.8, 0.8, 1, 0.8, 0.6, 1.5])

        header_idx = 0
        with header_cols[header_idx]:
            st.markdown("**Sembol**")
        header_idx += 1

        with header_cols[header_idx]:
            st.markdown("**Miktar**")
        header_idx += 1

        with header_cols[header_idx]:
            st.markdown("**Alış Fiyatı**")
        header_idx += 1

        with header_cols[header_idx]:
            st.markdown("**Güncel Fiyat**")
        header_idx += 1

        with header_cols[header_idx]:
            st.markdown("**Güncel Değer**")
        header_idx += 1

        with header_cols[header_idx]:
            st.markdown("**K/Z %**")
        header_idx += 1

        with header_cols[header_idx]:
            st.markdown("**Kaynak**")
        header_idx += 1

        if asset_type == 'hisse':
            with header_cols[header_idx]:
                st.markdown("**Sepet**")
            header_idx += 1

        with header_cols[header_idx]:
            st.markdown("**İşlemler**")

        st.markdown("---")

        # Privacy mode check
        privacy_mode = st.session_state.get('privacy_mode', False)

        # Display table with action buttons for each row
        for idx, asset_row in enumerate(display_data):
            asset_id = asset_row.get('ID')

            # Create columns for table-like display
            if asset_type == 'hisse':
                cols = st.columns([1.2, 0.8, 0.8, 0.8, 1, 0.8, 0.6, 0.8, 1.5])
            else:
                cols = st.columns([1.2, 0.8, 0.8, 0.8, 1, 0.8, 0.6, 1.5])

            col_idx = 0

            # Sembol
            with cols[col_idx]:
                st.markdown(f"**{asset_row.get('Sembol', '')}**")
            col_idx += 1

            # Miktar (hide if privacy mode)
            with cols[col_idx]:
                if privacy_mode:
                    st.markdown("****")
                else:
                    st.markdown(asset_row.get('Miktar', ''))
            col_idx += 1

            # Alış Fiyatı
            with cols[col_idx]:
                st.markdown(asset_row.get('Alış Fiyatı', ''))
            col_idx += 1

            # Güncel Fiyat
            with cols[col_idx]:
                st.markdown(asset_row.get('Güncel Fiyat', ''))
            col_idx += 1

            # Güncel Değer (hide if privacy mode)
            with cols[col_idx]:
                if privacy_mode:
                    st.markdown("₺****")
                else:
                    st.markdown(asset_row.get('Güncel Değer', ''))
            col_idx += 1

            # K/Z %
            with cols[col_idx]:
                kz = asset_row.get('K/Z %', '0%')
                color = "#10b981" if '+' in str(kz) else "#ef4444"
                st.markdown(f"<span style='color: {color}; font-weight: bold;'>{kz}</span>", unsafe_allow_html=True)
            col_idx += 1

            # Kaynak
            with cols[col_idx]:
                st.markdown(asset_row.get('Kaynak', ''))
            col_idx += 1

            # Sepet (only for stocks)
            if asset_type == 'hisse':
                with cols[col_idx]:
                    st.markdown(asset_row.get('Sepet', '-'))
                col_idx += 1

            # İşlemler (Action buttons)
            with cols[col_idx]:
                action_cols = st.columns(3)

                # Edit button
                with action_cols[0]:
                    if st.button("✏️", key=f"edit_{asset_type}_{asset_id}", help="Düzenle"):
                        st.session_state[f"edit_asset_id_{asset_type}"] = asset_id
                        original_data = filtered_df[filtered_df['ID'] == asset_id].iloc[0].to_dict()
                        st.session_state[f"edit_asset_data_{asset_type}"] = original_data
                        st.rerun()

                # Close Position button
                with action_cols[1]:
                    if st.button("🚪", key=f"close_{asset_type}_{asset_id}", help="Pozisyon Kapat"):
                        st.session_state[f"close_position_id_{asset_type}"] = asset_id
                        original_data = filtered_df[filtered_df['ID'] == asset_id].iloc[0].to_dict()
                        st.session_state[f"close_position_data_{asset_type}"] = original_data
                        st.rerun()

                # Delete button
                with action_cols[2]:
                    if st.button("🗑️", key=f"delete_{asset_type}_{asset_id}", help="Sil"):
                        st.session_state[f"delete_asset_id_{asset_type}"] = asset_id
                        st.session_state[f"delete_asset_symbol_{asset_type}"] = asset_row.get('Sembol', '')
                        st.rerun()

            st.divider()

        # Total value (hide if privacy mode active)
        privacy_mode = st.session_state.get('privacy_mode', False)
        if not privacy_mode:
            total = sum([float(item['Güncel Değer'].replace('₺', '').replace(',', '').replace('*', '0')) for item in display_data])
            st.markdown(f"**Toplam Değer: ₺{total:,.2f}**")

        # Show edit modal if edit button clicked
        if st.session_state.get(f"edit_asset_id_{asset_type}"):
            edit_data = st.session_state[f"edit_asset_data_{asset_type}"]

            with st.form(f"edit_asset_form_{asset_type}"):
                st.subheader(f"✏️ Düzenle: {edit_data.get('symbol', '')}")

                col1, col2 = st.columns(2)

                with col1:
                    new_symbol = st.text_input("Sembol", value=edit_data.get('symbol', ''))
                    new_amount = st.number_input("Miktar", min_value=0.0, step=0.01, value=float(edit_data.get('amount', 0)))
                    new_buy_price = st.number_input("Alış Fiyatı (₺)", min_value=0.0, step=0.01, value=float(edit_data.get('buy_price', 0)))

                with col2:
                    new_data_source = st.selectbox("Veri Kaynağı", ["auto", "manuel"], index=0 if edit_data.get('data_source') == 'auto' else 1)
                    new_manual_price = st.number_input("Manuel Fiyat", min_value=0.0, step=0.01, value=float(edit_data.get('manual_price', 0)))
                    if asset_type == 'hisse':
                        basket_options = ["", "buffet", "tesla", "tosuncuk"]
                        current_basket = edit_data.get('basket', '')
                        basket_index = basket_options.index(current_basket) if current_basket in basket_options else 0
                        new_basket = st.selectbox("Sepet", basket_options, index=basket_index)

                col_submit, col_cancel = st.columns(2)

                with col_submit:
                    submitted = st.form_submit_button("💾 Güncelle", use_container_width=True)

                with col_cancel:
                    cancelled = st.form_submit_button("❌ İptal", use_container_width=True)

                if submitted and new_symbol and new_amount > 0 and new_buy_price > 0:
                    # Find and update the row in Google Sheets
                    all_values = sheet.get_all_values()

                    for row_idx, row in enumerate(all_values[1:], start=2):  # Start from row 2 (skip header)
                        if int(row[0]) == st.session_state[f"edit_asset_id_{asset_type}"]:
                            # Update the row
                            updated_row = [
                                st.session_state[f"edit_asset_id_{asset_type}"],
                                asset_type,
                                new_symbol.upper(),
                                new_amount,
                                new_buy_price,
                                new_data_source,
                                new_manual_price,
                                new_basket if asset_type == 'hisse' else edit_data.get('basket', ''),
                                row[8] if len(row) > 8 else ''  # Keep original created_at
                            ]
                            sheet.update(f'A{row_idx}:I{row_idx}', [updated_row])
                            break

                    st.success(f"✅ {new_symbol.upper()} güncellendi!")
                    st.session_state[f"edit_asset_id_{asset_type}"] = None
                    st.session_state[f"edit_asset_data_{asset_type}"] = None
                    # Clear cache to force recalculation
                    if display_cache_key in st.session_state:
                        del st.session_state[display_cache_key]
                    st.rerun()

                if cancelled:
                    st.session_state[f"edit_asset_id_{asset_type}"] = None
                    st.session_state[f"edit_asset_data_{asset_type}"] = None
                    st.rerun()

        # Show close position modal if close position button clicked
        if st.session_state.get(f"close_position_id_{asset_type}"):
            close_data = st.session_state[f"close_position_data_{asset_type}"]

            with st.form(f"close_position_form_{asset_type}"):
                st.subheader(f"🚪 Pozisyon Kapat: {close_data.get('symbol', '')}")

                st.info(f"**Alış Fiyatı:** ₺{close_data.get('buy_price', 0):,.2f}")

                sell_price = st.number_input("Satış Fiyatı (₺)", min_value=0.0, step=0.01, value=float(close_data.get('buy_price', 0)))

                # Calculate profit/loss preview
                if close_data.get('buy_price', 0) > 0:
                    profit_loss_pct = ((sell_price - close_data.get('buy_price', 0)) / close_data.get('buy_price', 0)) * 100
                    color = "green" if profit_loss_pct >= 0 else "red"
                    st.markdown(f"**Kar/Zarar:** <span style='color:{color}; font-weight:bold;'>{profit_loss_pct:+.2f}%</span>", unsafe_allow_html=True)

                col_submit, col_cancel = st.columns(2)

                with col_submit:
                    submitted = st.form_submit_button("💾 Pozisyonu Kapat", use_container_width=True)

                with col_cancel:
                    cancelled = st.form_submit_button("❌ İptal", use_container_width=True)

                if submitted and sell_price > 0:
                    # Calculate profit/loss
                    profit_loss = ((sell_price - close_data.get('buy_price', 0)) / close_data.get('buy_price', 0)) * 100 if close_data.get('buy_price', 0) > 0 else 0

                    # Get closed positions sheet
                    closed_sheet = db.worksheet("closed_positions")
                    closed_data = get_sheet_data_as_dict(closed_sheet)

                    # Get max ID
                    max_id = max([item.get("ID", 0) for item in closed_data], default=0) if closed_data else 0
                    new_id = max_id + 1

                    # Add to closed positions
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    closed_sheet.append_row([
                        new_id,
                        date_str,
                        close_data.get('symbol', '').upper(),
                        close_data.get('buy_price', 0),
                        sell_price,
                        profit_loss,
                        now
                    ])

                    # Delete from assets
                    all_values = sheet.get_all_values()
                    for row_idx, row in enumerate(all_values[1:], start=2):
                        if int(row[0]) == st.session_state[f"close_position_id_{asset_type}"]:
                            sheet.delete_rows(row_idx)
                            break

                    st.success(f"✅ {close_data.get('symbol', '').upper()} pozisyonu kapatıldı! K/Z: {profit_loss:+.2f}%")
                    st.session_state[f"close_position_id_{asset_type}"] = None
                    st.session_state[f"close_position_data_{asset_type}"] = None
                    # Clear cache
                    if display_cache_key in st.session_state:
                        del st.session_state[display_cache_key]
                    st.rerun()

                if cancelled:
                    st.session_state[f"close_position_id_{asset_type}"] = None
                    st.session_state[f"close_position_data_{asset_type}"] = None
                    st.rerun()

        # Show delete confirmation if delete button clicked
        if st.session_state.get(f"delete_asset_id_{asset_type}"):
            st.warning(f"⚠️ **{st.session_state[f'delete_asset_symbol_{asset_type}']}** varlığını silmek istediğinize emin misiniz?")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🗑️ Evet, Sil", key=f"confirm_delete_{asset_type}", use_container_width=True):
                    # Find and delete the row
                    all_values = sheet.get_all_values()

                    for row_idx, row in enumerate(all_values[1:], start=2):  # Start from row 2
                        if int(row[0]) == st.session_state[f"delete_asset_id_{asset_type}"]:
                            sheet.delete_rows(row_idx)
                            break

                    st.success(f"✅ {st.session_state[f'delete_asset_symbol_{asset_type}']} silindi!")
                    st.session_state[f"delete_asset_id_{asset_type}"] = None
                    st.session_state[f"delete_asset_symbol_{asset_type}"] = None
                    # Clear cache to force recalculation
                    if display_cache_key in st.session_state:
                        del st.session_state[display_cache_key]
                    st.rerun()

            with col2:
                if st.button("❌ İptal", key=f"cancel_delete_{asset_type}", use_container_width=True):
                    st.session_state[f"delete_asset_id_{asset_type}"] = None
                    st.session_state[f"delete_asset_symbol_{asset_type}"] = None
                    st.rerun()

        # Asset distribution pie chart
        if len(display_data) > 0 and not privacy_mode:
            fig = go.Figure(data=[go.Pie(
                labels=[item['Sembol'] for item in display_data],
                values=[float(item['Güncel Değer'].replace('₺', '').replace(',', '')) for item in display_data],
                hole=0.3
            )])
            fig.update_layout(
                title=f"{type_label} Dağılımı",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f3f4f6')
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"📭 Henüz {type_label} eklenmemiş")

def show_debts_tab(debts_df, sheet):
    """Show debts tab."""

    if st.button("➕ Yeni Borç Ekle"):
        st.session_state["show_add_debt_modal"] = True

    # Show add form
    if st.session_state.get("show_add_debt_modal", False):
        with st.form("add_debt_form"):
            st.subheader("Yeni Borç Ekle")

            description = st.text_input("Açıklama")
            amount = st.number_input("Tutar (₺)", min_value=0.0, step=0.01)

            col_submit, col_cancel = st.columns(2)

            with col_submit:
                submitted = st.form_submit_button("💾 Kaydet", use_container_width=True)

            with col_cancel:
                cancelled = st.form_submit_button("❌ İptal", use_container_width=True)

            if submitted and description and amount > 0:
                # Get max ID
                all_data = get_sheet_data_as_dict(sheet)
                max_id = max([item.get("ID", 0) for item in all_data], default=0)
                new_id = max_id + 1

                # Add to sheet
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sheet.append_row([new_id, description, amount, now])

                st.success(f"✅ Borç başarıyla eklendi!")
                st.session_state["show_add_debt_modal"] = False
                st.rerun()

            if cancelled:
                st.session_state["show_add_debt_modal"] = False
                st.rerun()

    # Show debts table
    if not debts_df.empty and 'description' in debts_df.columns:
        st.markdown(f"#### Toplam Borç Sayısı: {len(debts_df)}")

        # Display each debt with Edit/Delete buttons
        for _, debt in debts_df.iterrows():
            debt_id = debt['ID']

            with st.container():
                cols = st.columns([2, 1.5, 1.5, 0.6, 0.6])

                with cols[0]:
                    st.markdown(f"**{debt.get('description', '')}**")

                with cols[1]:
                    st.markdown(format_currency(debt.get('amount', 0)))

                with cols[2]:
                    st.markdown(debt.get('created_at', ''))

                with cols[3]:
                    if st.button("✏️", key=f"edit_debt_{debt_id}", help="Düzenle"):
                        st.session_state["edit_debt_id"] = debt_id
                        st.session_state["edit_debt_data"] = debt.to_dict()
                        st.rerun()

                with cols[4]:
                    if st.button("🗑️", key=f"delete_debt_{debt_id}", help="Sil"):
                        st.session_state["delete_debt_id"] = debt_id
                        st.session_state["delete_debt_description"] = debt.get('description', '')
                        st.rerun()

                st.divider()

        total_debt = debts_df['amount'].sum()
        st.markdown(f"**Toplam Borç: {format_currency(total_debt)}**")

        # Show edit modal if edit button clicked
        if st.session_state.get("edit_debt_id"):
            edit_data = st.session_state["edit_debt_data"]

            with st.form("edit_debt_form"):
                st.subheader(f"✏️ Düzenle: {edit_data.get('description', '')}")

                new_description = st.text_input("Açıklama", value=edit_data.get('description', ''))
                new_amount = st.number_input("Tutar (₺)", min_value=0.0, step=0.01, value=float(edit_data.get('amount', 0)))

                col_submit, col_cancel = st.columns(2)

                with col_submit:
                    submitted = st.form_submit_button("💾 Güncelle", use_container_width=True)

                with col_cancel:
                    cancelled = st.form_submit_button("❌ İptal", use_container_width=True)

                if submitted and new_description and new_amount > 0:
                    # Find and update the row in Google Sheets
                    all_values = sheet.get_all_values()

                    for row_idx, row in enumerate(all_values[1:], start=2):  # Start from row 2 (skip header)
                        if int(row[0]) == st.session_state["edit_debt_id"]:
                            # Update the row
                            updated_row = [
                                st.session_state["edit_debt_id"],
                                new_description,
                                new_amount,
                                row[3] if len(row) > 3 else ''  # Keep original created_at
                            ]
                            sheet.update(f'A{row_idx}:D{row_idx}', [updated_row])
                            break

                    st.success(f"✅ {new_description} güncellendi!")
                    st.session_state["edit_debt_id"] = None
                    st.session_state["edit_debt_data"] = None
                    st.rerun()

                if cancelled:
                    st.session_state["edit_debt_id"] = None
                    st.session_state["edit_debt_data"] = None
                    st.rerun()

        # Show delete confirmation if delete button clicked
        if st.session_state.get("delete_debt_id"):
            st.warning(f"⚠️ **{st.session_state['delete_debt_description']}** borcunu silmek istediğinize emin misiniz?")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🗑️ Evet, Sil", key="confirm_delete_debt", use_container_width=True):
                    # Find and delete the row
                    all_values = sheet.get_all_values()

                    for row_idx, row in enumerate(all_values[1:], start=2):  # Start from row 2
                        if int(row[0]) == st.session_state["delete_debt_id"]:
                            sheet.delete_rows(row_idx)
                            break

                    st.success(f"✅ {st.session_state['delete_debt_description']} silindi!")
                    st.session_state["delete_debt_id"] = None
                    st.session_state["delete_debt_description"] = None
                    st.rerun()

            with col2:
                if st.button("❌ İptal", key="cancel_delete_debt", use_container_width=True):
                    st.session_state["delete_debt_id"] = None
                    st.session_state["delete_debt_description"] = None
                    st.rerun()

    else:
        st.info("📭 Henüz borç eklenmemiş")

def show_closed_positions_tab(db):
    """Show closed positions with statistics and CRUD operations - Flask uygulamasındaki gibi."""

    st.markdown("### 🔒 Kapanan Pozisyonlar")
    st.markdown("Geçmiş alım-satım işlemleriniz")

    # Get closed positions data
    closed_sheet = db.worksheet("closed_positions")
    closed_data = get_sheet_data_as_dict(closed_sheet)

    if closed_data:
        # Calculate statistics - Flask uygulamasındaki gibi
        total_count = len(closed_data)
        profitable = [p for p in closed_data if p.get('profit_loss_percent', 0) > 0]
        loss_making = [p for p in closed_data if p.get('profit_loss_percent', 0) < 0]
        avg_profit_loss = sum([p.get('profit_loss_percent', 0) for p in closed_data]) / total_count if total_count > 0 else 0

        # Statistics cards
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="📊 Toplam İşlem",
                value=total_count
            )

        with col2:
            st.metric(
                label="✅ Karlı İşlem",
                value=len(profitable),
                delta=f"{(len(profitable)/total_count*100):.1f}%" if total_count > 0 else "0%"
            )

        with col3:
            st.metric(
                label="❌ Zararlı İşlem",
                value=len(loss_making),
                delta=f"-{(len(loss_making)/total_count*100):.1f}%" if total_count > 0 else "0%"
            )

        with col4:
            st.metric(
                label="📈 Ortalama K/Z %",
                value=f"{avg_profit_loss:+.2f}%",
                delta="Pozitif" if avg_profit_loss > 0 else "Negatif"
            )

        st.divider()

    # Add new closed position button
    if st.button("➕ Kapanan Pozisyon Ekle", key="add_closed_position"):
        st.session_state["show_add_closed_modal"] = True

    # Show add form
    if st.session_state.get("show_add_closed_modal", False):
        with st.form("add_closed_position_form"):
            st.subheader("Yeni Kapanan Pozisyon Ekle")

            col1, col2 = st.columns(2)

            with col1:
                date = st.date_input("Tarih", value=datetime.now())
                symbol = st.text_input("Sembol")
                buy_price = st.number_input("Alış Fiyatı (₺)", min_value=0.0, step=0.01)

            with col2:
                sell_price = st.number_input("Satış Fiyatı (₺)", min_value=0.0, step=0.01)

                # Calculate profit/loss automatically
                if buy_price > 0:
                    calculated_pl = ((sell_price - buy_price) / buy_price) * 100
                    st.info(f"💡 Kar/Zarar: {calculated_pl:+.2f}%")

            col_submit, col_cancel = st.columns(2)

            with col_submit:
                submitted = st.form_submit_button("💾 Kaydet", use_container_width=True)

            with col_cancel:
                cancelled = st.form_submit_button("❌ İptal", use_container_width=True)

            if submitted and symbol and buy_price > 0 and sell_price > 0:
                # Calculate profit/loss percent
                profit_loss_percent = ((sell_price - buy_price) / buy_price) * 100

                # Get max ID
                max_id = max([item.get("ID", 0) for item in closed_data], default=0) if closed_data else 0
                new_id = max_id + 1

                # Add to sheet
                date_str = date.strftime('%Y-%m-%d')
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                closed_sheet.append_row([
                    new_id,
                    date_str,
                    symbol.upper(),
                    buy_price,
                    sell_price,
                    profit_loss_percent,
                    now
                ])

                st.success(f"✅ {symbol.upper()} kapanan pozisyon olarak eklendi!")
                st.session_state["show_add_closed_modal"] = False
                st.rerun()

            if cancelled:
                st.session_state["show_add_closed_modal"] = False
                st.rerun()

    # Show closed positions table with Edit/Delete buttons
    if closed_data:
        st.markdown(f"#### Toplam: {len(closed_data)} Kapanan Pozisyon")

        # TABLE HEADERS
        header_cols = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 1, 1])

        with header_cols[0]:
            st.markdown("**Tarih**")

        with header_cols[1]:
            st.markdown("**Sembol**")

        with header_cols[2]:
            st.markdown("**Alış Fiyatı**")

        with header_cols[3]:
            st.markdown("**Kapanış Fiyatı**")

        with header_cols[4]:
            st.markdown("**K/Z Oranı**")

        with header_cols[5]:
            st.markdown("**Düzenle**")

        with header_cols[6]:
            st.markdown("**Sil**")

        st.markdown("---")

        # Display each position with action buttons
        for idx, pos in enumerate(closed_data):
            profit_loss = pos.get('profit_loss_percent', 0)
            pos_id = pos.get('ID', 0)

            # Color-code based on profit/loss
            if profit_loss > 0:
                color = "#10b981"  # Green for profit
                icon = "✅"
            else:
                color = "#ef4444"  # Red for loss
                icon = "❌"

            # Create a card-like container for each position
            with st.container():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 1, 1])

                with col1:
                    st.markdown(f"**{pos.get('date', '')}**")

                with col2:
                    st.markdown(f"**{pos.get('symbol', '')}**")

                with col3:
                    st.markdown(format_currency(pos.get('buy_price', 0)))

                with col4:
                    st.markdown(format_currency(pos.get('sell_price', 0)))

                with col5:
                    st.markdown(f"<span style='color: {color}; font-weight: bold;'>{icon} {profit_loss:+.2f}%</span>", unsafe_allow_html=True)

                with col6:
                    if st.button("✏️", key=f"edit_closed_{pos_id}", help="Düzenle"):
                        st.session_state["edit_closed_id"] = pos_id
                        st.session_state["edit_closed_data"] = pos
                        st.rerun()

                with col7:
                    if st.button("🗑️", key=f"delete_closed_{pos_id}", help="Sil"):
                        st.session_state["delete_closed_id"] = pos_id
                        st.session_state["delete_closed_symbol"] = pos.get('symbol', '')
                        st.rerun()

                st.divider()

        # Show edit modal if edit button clicked
        if "edit_closed_id" in st.session_state and st.session_state["edit_closed_id"]:
            edit_data = st.session_state["edit_closed_data"]

            with st.form("edit_closed_position_form"):
                st.subheader(f"✏️ Düzenle: {edit_data.get('symbol', '')}")

                col1, col2 = st.columns(2)

                with col1:
                    # Parse date string to datetime object
                    date_str = edit_data.get('date', '')
                    try:
                        edit_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except:
                        edit_date = datetime.now().date()

                    new_date = st.date_input("Tarih", value=edit_date)
                    new_symbol = st.text_input("Sembol", value=edit_data.get('symbol', ''))
                    new_buy_price = st.number_input("Alış Fiyatı (₺)", min_value=0.0, step=0.01, value=float(edit_data.get('buy_price', 0)))

                with col2:
                    new_sell_price = st.number_input("Satış Fiyatı (₺)", min_value=0.0, step=0.01, value=float(edit_data.get('sell_price', 0)))

                    # Calculate profit/loss automatically
                    if new_buy_price > 0:
                        calculated_pl = ((new_sell_price - new_buy_price) / new_buy_price) * 100
                        st.info(f"💡 Kar/Zarar: {calculated_pl:+.2f}%")

                col_submit, col_cancel = st.columns(2)

                with col_submit:
                    submitted = st.form_submit_button("💾 Güncelle", use_container_width=True)

                with col_cancel:
                    cancelled = st.form_submit_button("❌ İptal", use_container_width=True)

                if submitted and new_symbol and new_buy_price > 0 and new_sell_price > 0:
                    # Calculate profit/loss percent
                    new_profit_loss = ((new_sell_price - new_buy_price) / new_buy_price) * 100

                    # Find the row to update
                    all_values = closed_sheet.get_all_values()
                    headers = all_values[0]

                    for row_idx, row in enumerate(all_values[1:], start=2):  # Start from row 2 (skip header)
                        if int(row[0]) == st.session_state["edit_closed_id"]:
                            # Update the row
                            date_str = new_date.strftime('%Y-%m-%d')
                            closed_sheet.update(f'A{row_idx}:G{row_idx}', [[
                                st.session_state["edit_closed_id"],
                                date_str,
                                new_symbol.upper(),
                                new_buy_price,
                                new_sell_price,
                                new_profit_loss,
                                row[6]  # Keep original created_at
                            ]])
                            break

                    st.success(f"✅ {new_symbol.upper()} güncellendi!")
                    st.session_state["edit_closed_id"] = None
                    st.session_state["edit_closed_data"] = None
                    st.rerun()

                if cancelled:
                    st.session_state["edit_closed_id"] = None
                    st.session_state["edit_closed_data"] = None
                    st.rerun()

        # Show delete confirmation if delete button clicked
        if "delete_closed_id" in st.session_state and st.session_state["delete_closed_id"]:
            st.warning(f"⚠️ **{st.session_state['delete_closed_symbol']}** kapanan pozisyonunu silmek istediğinize emin misiniz?")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🗑️ Evet, Sil", key="confirm_delete_closed", use_container_width=True):
                    # Find and delete the row
                    all_values = closed_sheet.get_all_values()

                    for row_idx, row in enumerate(all_values[1:], start=2):  # Start from row 2
                        if int(row[0]) == st.session_state["delete_closed_id"]:
                            closed_sheet.delete_rows(row_idx)
                            break

                    st.success(f"✅ {st.session_state['delete_closed_symbol']} silindi!")
                    st.session_state["delete_closed_id"] = None
                    st.session_state["delete_closed_symbol"] = None
                    st.rerun()

            with col2:
                if st.button("❌ İptal", key="cancel_delete_closed", use_container_width=True):
                    st.session_state["delete_closed_id"] = None
                    st.session_state["delete_closed_symbol"] = None
                    st.rerun()

    else:
        st.info("📭 Henüz kapanan pozisyon bulunmuyor")

if __name__ == "__main__":
    main()
