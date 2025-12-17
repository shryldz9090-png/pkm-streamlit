"""
Trade Asistanı - Streamlit Version
Trading pozisyon yönetimi, hata analizi ve kontrol sistemi
"""

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import io
import base64

# imgbb entegrasyonu (yüksek kalite görsel hosting için)
try:
    from imgbb_utils import upload_image_to_imgbb, IMGBB_API_KEY
    IMGBB_ENABLED = IMGBB_API_KEY != "YOUR_API_KEY_HERE"
except:
    IMGBB_ENABLED = False

# Page Config
st.set_page_config(
    page_title="Trade Asistanı - PKM",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
    }

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }

    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #059669;
        font-weight: 700;
    }

    [data-testid="stMetricLabel"] {
        color: #64748b;
        font-weight: 500;
    }

    h1, h2, h3 {
        color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# GOOGLE SHEETS FUNCTIONS
# =============================================================================

@st.cache_resource
def get_google_sheets():
    """Google Sheets bağlantısını döndürür"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    return client.open("PKM Database")

def get_sheet_data_as_dict(sheet):
    """Sheet verisini dictionary listesi olarak döndürür - ID'leri integer'a çevirir"""
    try:
        all_values = sheet.get_all_values()
        if len(all_values) <= 1:
            return []

        headers = all_values[0]
        data = []

        for row in all_values[1:]:
            row_dict = {}
            for i, header in enumerate(headers):
                value = row[i] if i < len(row) else ""
                # ID sütununu integer'a çevir
                if header == "ID" and value:
                    try:
                        row_dict[header] = int(value)
                    except:
                        row_dict[header] = value
                else:
                    row_dict[header] = value
            data.append(row_dict)

        return data
    except Exception as e:
        st.error(f"Veri yüklenirken hata: {e}")
        return []

def get_next_id(sheet):
    """Bir sonraki ID değerini döndürür"""
    try:
        data = get_sheet_data_as_dict(sheet)
        if not data:
            return 1
        ids = [int(row['ID']) for row in data if row.get('ID')]
        return max(ids) + 1 if ids else 1
    except:
        return 1

# =============================================================================
# IMAGE OPTIMIZATION FUNCTIONS
# =============================================================================

def optimize_and_encode_image(uploaded_file):
    """
    Resmi optimize eder ve Base64'e çevirir
    - 800x600 boyutuna küçült
    - JPEG kalite 80%
    - Base64 string döndür
    """
    try:
        # Görüntüyü aç
        image = Image.open(uploaded_file)

        # RGB'ye çevir (RGBA ise)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background

        # Boyutlandır (aspect ratio koruyarak) - Daha büyük boyut
        image.thumbnail((600, 450), Image.Resampling.LANCZOS)

        # JPEG formatında buffer'a kaydet - Daha yüksek kalite
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=50, optimize=True)

        # Base64'e çevir
        base64_str = base64.b64encode(buffer.getvalue()).decode()

        return base64_str
    except Exception as e:
        st.error(f"Görsel optimize edilirken hata: {e}")
        return None

def decode_base64_image(base64_str):
    """Base64 string'i PIL Image'a çevirir"""
    try:
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))
        return image
    except Exception as e:
        st.error(f"Görsel yüklenirken hata: {e}")
        return None

# =============================================================================
# POZİSYON YÖNETİMİ FONKSİYONLARI
# =============================================================================

def load_positions_data():
    """Pozisyonları yükler ve cache'ler"""
    cache_key = "positions_cache"
    cache_time_key = "positions_cache_time"

    # Cache kontrolü (30 saniye)
    current_time = datetime.now().timestamp()
    if cache_key in st.session_state and cache_time_key in st.session_state:
        if current_time - st.session_state[cache_time_key] < 30:
            return st.session_state[cache_key]

    # Veriyi yükle
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Pozisyonlar')
        data = get_sheet_data_as_dict(sheet)

        # Cache'e kaydet
        st.session_state[cache_key] = data
        st.session_state[cache_time_key] = current_time

        return data
    except Exception as e:
        st.error(f"Pozisyonlar yüklenirken hata: {e}")
        return []

def clear_positions_cache():
    """Pozisyon cache'ini temizler"""
    if "positions_cache" in st.session_state:
        del st.session_state["positions_cache"]
    if "positions_cache_time" in st.session_state:
        del st.session_state["positions_cache_time"]

def add_position(position_type, entry_price, lot_size, stop_loss, take_profit, plan_note, market=""):
    """Yeni pozisyon ekler"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Pozisyonlar')

        next_id = get_next_id(sheet)
        now = datetime.now()
        timestamp = now.isoformat()
        date_str = now.strftime('%Y-%m-%d %H:%M:%S')

        row = [
            next_id,
            position_type,
            float(entry_price),
            float(lot_size),
            float(stop_loss) if stop_loss and stop_loss > 0 else "",
            float(take_profit) if take_profit and take_profit > 0 else "",
            plan_note,
            "OPEN",
            "",  # Sonuç
            "",  # Öğrenilen Ders
            date_str,  # Açılış Tarihi
            "",  # Kapanış Tarihi
            "",  # Çıkış Fiyatı
            market,
            timestamp
        ]

        sheet.append_row(row)
        clear_positions_cache()
        return True
    except Exception as e:
        st.error(f"Pozisyon eklenirken hata: {e}")
        return False

def close_position(position_id, exit_price, lesson_learned=""):
    """Pozisyonu kapatır"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Pozisyonlar')

        all_data = sheet.get_all_values()
        header = all_data[0]

        # Kolon indekslerini bul
        id_col = header.index('ID') + 1
        status_col = header.index('Durum') + 1
        result_col = header.index('Sonuç') + 1
        lesson_col = header.index('Öğrenilen Ders') + 1
        close_date_col = header.index('Kapanış Tarihi') + 1
        exit_price_col = header.index('Çıkış Fiyatı') + 1
        entry_price_col = header.index('Giriş Fiyatı') + 1
        lot_col = header.index('Lot Büyüklüğü') + 1
        type_col = header.index('Pozisyon Tipi') + 1

        # Satırı bul ve güncelle
        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(position_id):
                entry_price = float(row[entry_price_col - 1])
                lot_size = float(row[lot_col - 1])
                pos_type = row[type_col - 1]

                # Kar/Zarar hesapla
                if pos_type == 'LONG':
                    result = (float(exit_price) - entry_price) * lot_size
                else:  # SHORT
                    result = (entry_price - float(exit_price)) * lot_size

                # Güncelleme yap
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                sheet.update_cell(row_idx, status_col, 'CLOSED')
                sheet.update_cell(row_idx, result_col, round(result, 2))
                sheet.update_cell(row_idx, lesson_col, lesson_learned)
                sheet.update_cell(row_idx, close_date_col, now)
                sheet.update_cell(row_idx, exit_price_col, float(exit_price))

                clear_positions_cache()
                return True, result

        return False, 0
    except Exception as e:
        st.error(f"Pozisyon kapatılırken hata: {e}")
        return False, 0

def update_position(position_id, stop_loss=None, take_profit=None, plan_note=None):
    """Pozisyon bilgilerini günceller"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Pozisyonlar')

        all_data = sheet.get_all_values()
        header = all_data[0]

        id_col = header.index('ID') + 1
        sl_col = header.index('Stop Loss') + 1
        tp_col = header.index('Take Profit') + 1
        plan_col = header.index('Plan Notu') + 1

        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(position_id):
                if stop_loss is not None:
                    sheet.update_cell(row_idx, sl_col, float(stop_loss) if stop_loss > 0 else "")
                if take_profit is not None:
                    sheet.update_cell(row_idx, tp_col, float(take_profit) if take_profit > 0 else "")
                if plan_note is not None:
                    sheet.update_cell(row_idx, plan_col, plan_note)

                clear_positions_cache()
                return True

        return False
    except Exception as e:
        st.error(f"Pozisyon güncellenirken hata: {e}")
        return False

def delete_position(position_id):
    """Pozisyonu siler"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Pozisyonlar')

        all_data = sheet.get_all_values()
        header = all_data[0]
        id_col = header.index('ID') + 1

        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(position_id):
                sheet.delete_rows(row_idx)
                clear_positions_cache()
                return True

        return False
    except Exception as e:
        st.error(f"Pozisyon silinirken hata: {e}")
        return False

# =============================================================================
# GÖRSEL TECRÜBELER FONKSİYONLARI
# =============================================================================

def load_experiences_data():
    """Görsel tecrübeleri yükler ve cache'ler"""
    cache_key = "experiences_cache"
    cache_time_key = "experiences_cache_time"

    # Cache kontrolü (30 saniye)
    current_time = datetime.now().timestamp()
    if cache_key in st.session_state and cache_time_key in st.session_state:
        if current_time - st.session_state[cache_time_key] < 30:
            return st.session_state[cache_key]

    # Veriyi yükle
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Gorsel_Tecrubeler')
        data = get_sheet_data_as_dict(sheet)

        # Cache'e kaydet
        st.session_state[cache_key] = data
        st.session_state[cache_time_key] = current_time

        return data
    except Exception as e:
        st.error(f"Görsel tecrübeler yüklenirken hata: {e}")
        return []

def clear_experiences_cache():
    """Görsel tecrübeler cache'ini temizler"""
    if "experiences_cache" in st.session_state:
        del st.session_state["experiences_cache"]
    if "experiences_cache_time" in st.session_state:
        del st.session_state["experiences_cache_time"]

def load_categories():
    """Kategorileri yükler"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Kategoriler')
        data = get_sheet_data_as_dict(sheet)
        return [cat.get('Kategori Adı', '') for cat in data if cat.get('Kategori Adı')]
    except Exception as e:
        st.error(f"Kategoriler yüklenirken hata: {e}")
        return ["Kategorisiz"]

def add_experience(title, category, note, image_data, loss_amount=0, is_url=False):
    """
    Yeni görsel tecrübe ekler

    Args:
        image_data: Base64 string (eski) veya imgbb URL (yeni)
        is_url: True ise image_data bir URL'dir
    """
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Gorsel_Tecrubeler')

        next_id = get_next_id(sheet)
        now = datetime.now()
        timestamp = now.isoformat()
        date_str = now.strftime('%Y-%m-%d %H:%M:%S')

        row = [
            next_id,
            title,
            category,
            note,
            image_data,  # imgbb URL (yüksek kalite) veya Base64 (düşük kalite fallback)
            float(loss_amount) if loss_amount else "",
            date_str,
            timestamp
        ]

        sheet.append_row(row)
        clear_experiences_cache()
        return True
    except Exception as e:
        st.error(f"Tecrübe eklenirken hata: {e}")
        return False

def delete_experience(experience_id):
    """Görsel tecrübeyi siler"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Gorsel_Tecrubeler')

        all_data = sheet.get_all_values()
        header = all_data[0]
        id_col = header.index('ID') + 1

        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(experience_id):
                sheet.delete_rows(row_idx)
                clear_experiences_cache()
                return True

        return False
    except Exception as e:
        st.error(f"Tecrübe silinirken hata: {e}")
        return False

def update_experience(experience_id, title=None, category=None, note=None, loss_amount=None):
    """Görsel tecrübeyi günceller (görsel hariç)"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Gorsel_Tecrubeler')

        all_data = sheet.get_all_values()
        header = all_data[0]

        id_col = header.index('ID') + 1
        title_col = header.index('Başlık') + 1
        cat_col = header.index('Kategori') + 1
        note_col = header.index('Not') + 1
        loss_col = header.index('Zarar Miktarı') + 1

        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(experience_id):
                if title is not None:
                    sheet.update_cell(row_idx, title_col, title)
                if category is not None:
                    sheet.update_cell(row_idx, cat_col, category)
                if note is not None:
                    sheet.update_cell(row_idx, note_col, note)
                if loss_amount is not None:
                    sheet.update_cell(row_idx, loss_col, float(loss_amount) if loss_amount else "")

                clear_experiences_cache()
                return True

        return False
    except Exception as e:
        st.error(f"Tecrübe güncellenirken hata: {e}")
        return False

# =============================================================================
# ANA SAYFA FONKSİYONLARI
# =============================================================================

def load_quotes_data():
    """Özlü sözleri yükler"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Ozlu_Sozler')
        data = get_sheet_data_as_dict(sheet)
        # Sıraya göre sırala
        return sorted(data, key=lambda x: int(x.get('Sıra', 999)) if x.get('Sıra') else 999)
    except Exception as e:
        st.error(f"Özlü sözler yüklenirken hata: {e}")
        return []

def add_quote(quote_text, order, color="#3b82f6"):
    """Yeni özlü söz ekler"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Ozlu_Sozler')

        next_id = get_next_id(sheet)
        now = datetime.now()

        row = [
            next_id,
            quote_text,
            int(order),
            color,
            now.strftime('%Y-%m-%d %H:%M:%S'),
            now.isoformat()
        ]

        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Özlü söz eklenirken hata: {e}")
        return False

def update_quote(quote_id, quote_text, order, color):
    """Özlü sözü günceller"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Ozlu_Sozler')

        all_data = sheet.get_all_values()
        header = all_data[0]

        # Kolon indekslerini bul
        id_col = header.index('ID') + 1
        text_col = header.index('Söz') + 1
        order_col = header.index('Sıra') + 1
        color_col = header.index('Renk') + 1

        # Satırı bul ve güncelle
        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(quote_id):
                sheet.update_cell(row_idx, text_col, quote_text)
                sheet.update_cell(row_idx, order_col, int(order))
                sheet.update_cell(row_idx, color_col, color)
                return True

        return False
    except Exception as e:
        st.error(f"Özlü söz güncellenirken hata: {e}")
        return False

def delete_quote(quote_id):
    """Özlü sözü siler"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Ozlu_Sozler')

        all_data = sheet.get_all_values()
        header = all_data[0]
        id_col = header.index('ID') + 1

        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(quote_id):
                sheet.delete_rows(row_idx)
                return True

        return False
    except Exception as e:
        st.error(f"Özlü söz silinirken hata: {e}")
        return False

# =============================================================================
# KENDİME NOTLAR FONKSİYONLARI
# =============================================================================

def load_notes_data():
    """Kendime notları yükler ve cache'ler"""
    cache_key = "notes_cache"
    cache_time_key = "notes_cache_time"

    current_time = datetime.now().timestamp()
    if cache_key in st.session_state and cache_time_key in st.session_state:
        if current_time - st.session_state[cache_time_key] < 30:
            return st.session_state[cache_key]

    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Kendime_Notlar')
        data = get_sheet_data_as_dict(sheet)

        st.session_state[cache_key] = data
        st.session_state[cache_time_key] = current_time

        return data
    except Exception as e:
        st.error(f"Notlar yüklenirken hata: {e}")
        return []

def add_note(baslik, kategori, icerik, gorsel_url=""):
    """Yeni not ekler"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Kendime_Notlar')

        next_id = get_next_id(sheet)
        now = datetime.now()

        row = [
            next_id,
            baslik,
            kategori,
            icerik,
            gorsel_url,
            now.strftime('%Y-%m-%d %H:%M:%S'),
            now.isoformat()
        ]

        sheet.append_row(row)
        clear_notes_cache()
        return True
    except Exception as e:
        st.error(f"Not eklenirken hata: {e}")
        return False

def update_note(note_id, baslik, kategori, icerik, gorsel_url=""):
    """Notu günceller"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Kendime_Notlar')

        all_data = sheet.get_all_values()
        header = all_data[0]

        id_col = header.index('ID') + 1
        baslik_col = header.index('Başlık') + 1
        kategori_col = header.index('Kategori') + 1
        icerik_col = header.index('İçerik') + 1
        gorsel_col = header.index('Görsel URL') + 1

        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(note_id):
                sheet.update_cell(row_idx, baslik_col, baslik)
                sheet.update_cell(row_idx, kategori_col, kategori)
                sheet.update_cell(row_idx, icerik_col, icerik)
                sheet.update_cell(row_idx, gorsel_col, gorsel_url)
                clear_notes_cache()
                return True

        return False
    except Exception as e:
        st.error(f"Not güncellenirken hata: {e}")
        return False

def delete_note(note_id):
    """Notu siler"""
    try:
        spreadsheet = get_google_sheets()
        sheet = spreadsheet.worksheet('Kendime_Notlar')

        all_data = sheet.get_all_values()
        header = all_data[0]
        id_col = header.index('ID') + 1

        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(note_id):
                sheet.delete_rows(row_idx)
                clear_notes_cache()
                return True

        return False
    except Exception as e:
        st.error(f"Not silinirken hata: {e}")
        return False

def clear_notes_cache():
    """Not cache'ini temizler"""
    if "notes_cache" in st.session_state:
        del st.session_state["notes_cache"]
    if "notes_cache_time" in st.session_state:
        del st.session_state["notes_cache_time"]

# =============================================================================
# MAIN APP
# =============================================================================

st.title("📈 Trade Asistanı")

# Sidebar - Özellikler Menüsü
with st.sidebar:
    st.markdown("### 🎯 Özellikler")
    feature = st.radio(
        "Özellik Seç:",
        ["🏠 Ana Sayfa", "📊 Pozisyon Yönetimi", "🖼️ Görsel Tecrübeler", "✅ İşlem Öncesi Kontrol",
         "📝 Kendime Notlar", "🏆 Challenge"],
        key="feature_selector"
    )

# =============================================================================
# ANA SAYFA
# =============================================================================

if feature == "🏠 Ana Sayfa":
    st.markdown("## 🎯 Trading Motivasyon Merkezi")

    # Özlü Sözler Kartları
    st.markdown("### 💎 Özlü Sözler")
    quotes_data = load_quotes_data()

    if quotes_data:
        # Renk kartlar halinde göster
        cols_per_row = 2
        for i in range(0, len(quotes_data), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                idx = i + j
                if idx < len(quotes_data):
                    quote = quotes_data[idx]
                    quote_text = quote.get('Söz', '')
                    quote_color = quote.get('Renk', '#3b82f6')
                    quote_id = quote.get('ID')

                    with col:
                        # Renkli kart
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, {quote_color}20, {quote_color}40);
                            border-left: 4px solid {quote_color};
                            padding: 20px;
                            border-radius: 10px;
                            margin: 10px 0;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        ">
                            <p style="
                                font-size: 1.1rem;
                                font-weight: 500;
                                color: #1e293b;
                                margin: 0;
                                font-style: italic;
                            ">"{quote_text}"</p>
                        </div>
                        """, unsafe_allow_html=True)

                        # Düzenle ve Sil butonları
                        col_edit, col_del = st.columns(2)

                        with col_edit:
                            if st.button("✏️ Düzenle", key=f"edit_quote_{quote_id}", use_container_width=True):
                                st.session_state[f"edit_mode_quote_{quote_id}"] = True
                                st.rerun()

                        with col_del:
                            if st.button("🗑️ Sil", key=f"del_quote_{quote_id}", use_container_width=True):
                                if delete_quote(quote_id):
                                    st.success("Özlü söz silindi!")
                                    st.rerun()

                        # Düzenleme modu
                        if st.session_state.get(f"edit_mode_quote_{quote_id}", False):
                            with st.form(f"edit_form_quote_{quote_id}"):
                                st.markdown("**Özlü Sözü Düzenle:**")

                                edited_text = st.text_area(
                                    "Söz",
                                    value=quote_text,
                                    height=100,
                                    key=f"edit_text_{quote_id}"
                                )

                                col1, col2 = st.columns(2)
                                with col1:
                                    edited_order = st.number_input(
                                        "Sıra",
                                        min_value=1,
                                        value=int(quote.get('Sıra', 1)),
                                        step=1,
                                        key=f"edit_order_{quote_id}"
                                    )
                                with col2:
                                    edited_color = st.color_picker(
                                        "Renk",
                                        value=quote_color,
                                        key=f"edit_color_{quote_id}"
                                    )

                                col_save, col_cancel = st.columns(2)

                                with col_save:
                                    if st.form_submit_button("💾 Kaydet", type="primary", use_container_width=True):
                                        if edited_text.strip():
                                            if update_quote(quote_id, edited_text, edited_order, edited_color):
                                                st.success("✅ Özlü söz güncellendi!")
                                                del st.session_state[f"edit_mode_quote_{quote_id}"]
                                                st.rerun()
                                        else:
                                            st.error("Söz boş olamaz!")

                                with col_cancel:
                                    if st.form_submit_button("❌ İptal", use_container_width=True):
                                        del st.session_state[f"edit_mode_quote_{quote_id}"]
                                        st.rerun()
    else:
        st.info("Henüz özlü söz eklenmemiş. Aşağıdan ilk sözünü ekle!")

    # Yeni Özlü Söz Ekle
    st.markdown("---")
    with st.expander("➕ Yeni Özlü Söz Ekle"):
        with st.form("new_quote_form"):
            new_quote = st.text_area("Özlü Söz", placeholder='Örn: "Sabır trading de altın değerindedir."', height=100)

            col1, col2 = st.columns(2)
            with col1:
                quote_order = st.number_input("Sıra", min_value=1, value=1, step=1)
            with col2:
                quote_color = st.color_picker("Renk", value="#3b82f6")

            if st.form_submit_button("✅ Ekle", type="primary", use_container_width=True):
                if new_quote.strip():
                    if add_quote(new_quote, quote_order, quote_color):
                        st.success("✅ Özlü söz eklendi!")
                        st.rerun()
                else:
                    st.error("Lütfen bir söz girin!")

    st.markdown("---")

    # Trade Hedefleri Bölümü
    st.markdown("### 🎯 Trade Hedeflerim")

    # Hedef kartları
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #10b98120, #10b98140);
            border-left: 4px solid #10b981;
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        ">
            <div style="font-size: 4rem;">🏠</div>
            <h3 style="color: #1e293b; margin: 10px 0;">Ev Hayalim</h3>
            <p style="color: #64748b; font-size: 0.9rem;">Trading ile hayalimdeki eve kavuşacağım!</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #f59e0b20, #f59e0b40);
            border-left: 4px solid #f59e0b;
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        ">
            <div style="font-size: 4rem;">🚗</div>
            <h3 style="color: #1e293b; margin: 10px 0;">Araba Hayalim</h3>
            <p style="color: #64748b; font-size: 0.9rem;">Trading ile hayalimdeki arabayı alacağım!</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Hızlı İstatistikler
    st.markdown("### 📊 Hızlı Bakış")

    # Verileri yükle
    positions_data = load_positions_data()
    experiences_data = load_experiences_data()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        open_positions = len([p for p in positions_data if p.get('Durum') == 'OPEN']) if positions_data else 0
        st.metric("Açık Pozisyon", open_positions, delta=None)

    with col2:
        total_experiences = len(experiences_data) if experiences_data else 0
        st.metric("Tecrübe Sayısı", total_experiences, delta=None)

    with col3:
        closed_positions = [p for p in positions_data if p.get('Durum') == 'CLOSED'] if positions_data else []
        total_result = sum([float(p.get('Sonuç', 0)) for p in closed_positions if p.get('Sonuç')]) if closed_positions else 0
        st.metric("Toplam Kar/Zarar", f"₺{total_result:,.2f}", delta=total_result if total_result != 0 else None)

    with col4:
        total_loss = sum([float(exp.get('Zarar Miktarı', 0)) for exp in experiences_data if exp.get('Zarar Miktarı')]) if experiences_data else 0
        st.metric("Toplam Ders Maliyeti", f"₺{total_loss:,.2f}", delta=None)

# =============================================================================
# POZİSYON YÖNETİMİ
# =============================================================================

elif feature == "📊 Pozisyon Yönetimi":
    st.markdown("## 📊 Pozisyon Yönetimi")
    st.markdown("LONG ve SHORT pozisyonlarınızı yönetin, kar/zarar takibi yapın.")

    # Pozisyonları yükle
    positions_data = load_positions_data()
    positions_df = pd.DataFrame(positions_data) if positions_data else pd.DataFrame()

    # İstatistikler
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        open_count = len([p for p in positions_data if p.get('Durum') == 'OPEN']) if positions_data else 0
        st.metric("Açık Pozisyonlar", open_count)

    with col2:
        closed_positions = [p for p in positions_data if p.get('Durum') == 'CLOSED'] if positions_data else []
        total_result = sum([float(p.get('Sonuç', 0)) for p in closed_positions if p.get('Sonuç')]) if closed_positions else 0

        # Kar/Zarar rengini ayarla
        if total_result > 0:
            result_html = f"<div style='color: #10b981; font-size: 2rem; font-weight: 700;'>₺{total_result:,.2f}</div>"
        elif total_result < 0:
            result_html = f"<div style='color: #ef4444; font-size: 2rem; font-weight: 700;'>₺{total_result:,.2f}</div>"
        else:
            result_html = f"<div style='color: #64748b; font-size: 2rem; font-weight: 700;'>₺{total_result:,.2f}</div>"

        st.markdown("**Toplam Kar/Zarar**")
        st.markdown(result_html, unsafe_allow_html=True)

    with col3:
        if closed_positions:
            wins = len([p for p in closed_positions if float(p.get('Sonuç', 0)) > 0])
            total_trades = len(closed_positions)
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        else:
            win_rate = 0
        st.metric("Kazanma Oranı", f"{win_rate:.1f}%")

    with col4:
        st.metric("Toplam Pozisyon", len(positions_data) if positions_data else 0)

    st.markdown("---")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["➕ Yeni Pozisyon", "📋 Açık Pozisyonlar", "📜 Pozisyon Geçmişi"])

    # YENİ POZİSYON
    with tab1:
        st.markdown("### ➕ Yeni Pozisyon Aç")

        with st.form("new_position_form"):
            col1, col2 = st.columns(2)

            with col1:
                position_type = st.selectbox("Pozisyon Tipi", ["LONG", "SHORT"])
                entry_price = st.number_input("Giriş Fiyatı", min_value=0.0, step=0.01, format="%.4f")
                lot_size = st.number_input("Lot Büyüklüğü", min_value=0.01, step=0.01, format="%.2f")
                market = st.text_input("Piyasa (opsiyonel)", placeholder="Örn: BTCUSDT, EURUSD")

            with col2:
                stop_loss = st.number_input("Stop Loss (opsiyonel)", min_value=0.0, step=0.01, format="%.4f", value=0.0)
                take_profit = st.number_input("Take Profit (opsiyonel)", min_value=0.0, step=0.01, format="%.4f", value=0.0)
                plan_note = st.text_area("Plan / Neden Bu Pozisyonu Açıyorsun?",
                                         placeholder="Stratejini ve planını açıkla...", height=100)

            submitted = st.form_submit_button("✅ Pozisyon Aç", type="primary", use_container_width=True)

            if submitted:
                if entry_price > 0 and lot_size > 0 and plan_note.strip():
                    success = add_position(position_type, entry_price, lot_size, stop_loss, take_profit, plan_note, market)
                    if success:
                        st.success("✅ Pozisyon başarıyla açıldı!")
                        st.rerun()
                else:
                    st.error("❌ Lütfen tüm gerekli alanları doldurun!")

    # AÇIK POZİSYONLAR
    with tab2:
        st.markdown("### 📋 Açık Pozisyonlar")

        open_positions = [p for p in positions_data if p.get('Durum') == 'OPEN'] if positions_data else []

        if open_positions:
            for pos in open_positions:
                pos_id = pos.get('ID')
                with st.expander(f"{pos.get('Pozisyon Tipi')} - {pos.get('Piyasa', 'N/A')} | Giriş: {pos.get('Giriş Fiyatı')} | Lot: {pos.get('Lot Büyüklüğü')}", expanded=False):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**ID:** {pos_id}")
                        st.markdown(f"**Açılış Tarihi:** {pos.get('Açılış Tarihi', 'N/A')}")
                        st.markdown(f"**Stop Loss:** {pos.get('Stop Loss') if pos.get('Stop Loss') else 'Yok'}")
                        st.markdown(f"**Take Profit:** {pos.get('Take Profit') if pos.get('Take Profit') else 'Yok'}")
                        st.markdown(f"**Plan:** {pos.get('Plan Notu', 'N/A')}")

                    with col2:
                        st.markdown("**Pozisyonu Kapat:**")
                        exit_price = st.number_input("Çıkış Fiyatı", min_value=0.0, step=0.01,
                                                    format="%.4f", key=f"exit_{pos_id}")
                        lesson = st.text_area("Öğrenilen Ders", placeholder="Bu pozisyondan ne öğrendin?",
                                             key=f"lesson_{pos_id}", height=80)

                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            if st.button("✅ Kapat", key=f"close_{pos_id}", use_container_width=True):
                                if exit_price > 0:
                                    success, result = close_position(pos_id, exit_price, lesson)
                                    if success:
                                        st.success(f"✅ Pozisyon kapatıldı! Sonuç: ₺{result:,.2f}")
                                        st.rerun()
                                else:
                                    st.error("❌ Çıkış fiyatı girmelisiniz!")

                        with col_b:
                            if st.button("✏️ Düzenle", key=f"edit_{pos_id}", use_container_width=True):
                                st.session_state[f"edit_pos_{pos_id}"] = True
                                st.rerun()

                        with col_c:
                            if st.button("🗑️ Sil", key=f"del_{pos_id}", use_container_width=True):
                                if delete_position(pos_id):
                                    st.success("✅ Pozisyon silindi!")
                                    st.rerun()

                    # Edit modal
                    if st.session_state.get(f"edit_pos_{pos_id}"):
                        st.markdown("---")
                        st.markdown("**Pozisyonu Düzenle:**")

                        with st.form(f"edit_form_{pos_id}"):
                            new_sl = st.number_input("Yeni Stop Loss", min_value=0.0, step=0.01,
                                                    value=float(pos.get('Stop Loss', 0)) if pos.get('Stop Loss') else 0.0,
                                                    key=f"new_sl_{pos_id}")
                            new_tp = st.number_input("Yeni Take Profit", min_value=0.0, step=0.01,
                                                    value=float(pos.get('Take Profit', 0)) if pos.get('Take Profit') else 0.0,
                                                    key=f"new_tp_{pos_id}")
                            new_plan = st.text_area("Yeni Plan", value=pos.get('Plan Notu', ''),
                                                   key=f"new_plan_{pos_id}")

                            col_submit, col_cancel = st.columns(2)

                            with col_submit:
                                if st.form_submit_button("💾 Kaydet", use_container_width=True):
                                    if update_position(pos_id, new_sl, new_tp, new_plan):
                                        st.success("✅ Pozisyon güncellendi!")
                                        st.session_state[f"edit_pos_{pos_id}"] = False
                                        st.rerun()

                            with col_cancel:
                                if st.form_submit_button("❌ İptal", use_container_width=True):
                                    st.session_state[f"edit_pos_{pos_id}"] = False
                                    st.rerun()
        else:
            st.info("ℹ️ Henüz açık pozisyon yok.")

    # POZİSYON GEÇMİŞİ
    with tab3:
        col_title, col_clear = st.columns([3, 1])

        with col_title:
            st.markdown("### 📜 Kapatılmış Pozisyonlar")

        with col_clear:
            if st.button("🗑️ Geçmişi Temizle", type="secondary", use_container_width=True):
                st.session_state["confirm_clear_history"] = True
                st.rerun()

        # Geçmiş temizleme onayı
        if st.session_state.get("confirm_clear_history"):
            st.warning("⚠️ **TÜM kapatılmış pozisyonları silmek istediğinize emin misiniz? Bu işlem geri alınamaz!**")

            col_confirm, col_cancel = st.columns(2)

            with col_confirm:
                if st.button("✅ Evet, Tümünü Sil", key="confirm_clear", use_container_width=True):
                    try:
                        spreadsheet = get_google_sheets()
                        sheet = spreadsheet.worksheet('Pozisyonlar')
                        all_data = sheet.get_all_values()
                        header = all_data[0]

                        # CLOSED pozisyonları bul ve sil (sondan başa doğru)
                        status_col_idx = header.index('Durum')
                        rows_to_delete = []

                        for row_idx, row in enumerate(all_data[1:], start=2):
                            if row[status_col_idx] == 'CLOSED':
                                rows_to_delete.append(row_idx)

                        # Sondan başa doğru sil (indeks kayması olmasın)
                        for row_idx in reversed(rows_to_delete):
                            sheet.delete_rows(row_idx)

                        clear_positions_cache()
                        st.success(f"✅ {len(rows_to_delete)} kapatılmış pozisyon silindi!")
                        st.session_state["confirm_clear_history"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Geçmiş temizlenirken hata: {e}")

            with col_cancel:
                if st.button("❌ İptal", key="cancel_clear", use_container_width=True):
                    st.session_state["confirm_clear_history"] = False
                    st.rerun()

            st.markdown("---")

        closed_positions = [p for p in positions_data if p.get('Durum') == 'CLOSED'] if positions_data else []

        if closed_positions:
            # Grafik
            results = [float(p.get('Sonuç', 0)) for p in closed_positions if p.get('Sonuç')]
            dates = [p.get('Kapanış Tarihi', '') for p in closed_positions]
            colors = ['green' if x > 0 else 'red' for x in results]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=dates,
                y=results,
                marker_color=colors,
                name='Kar/Zarar'
            ))

            fig.update_layout(
                title="Pozisyon Kar/Zarar Grafiği",
                xaxis_title="Kapanış Tarihi",
                yaxis_title="Kar/Zarar (₺)",
                template="plotly_white",
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

            # Tablo - Renkli satırlarla
            st.markdown("#### 📊 Özet Tablo")

            # Tablo başlıkları
            header_cols = st.columns([0.5, 1, 1, 1, 1, 1, 1.5, 1.5, 1.5])
            headers = ['ID', 'Tip', 'Piyasa', 'Giriş', 'Çıkış', 'Lot', 'Sonuç', 'Açılış', 'Kapanış']

            for i, header in enumerate(headers):
                with header_cols[i]:
                    st.markdown(f"**{header}**")

            st.markdown("---")

            # Satırlar - Her satır kar/zarara göre renkli
            for pos in closed_positions:
                result = float(pos.get('Sonuç', 0))

                # Satır rengi
                if result > 0:
                    bg_color = "#d1fae5"  # Açık yeşil
                    text_color = "#065f46"  # Koyu yeşil
                elif result < 0:
                    bg_color = "#fee2e2"  # Açık kırmızı
                    text_color = "#991b1b"  # Koyu kırmızı
                else:
                    bg_color = "#f3f4f6"  # Gri
                    text_color = "#374151"  # Koyu gri

                # Satır HTML
                row_html = f"""
                <div style='background-color: {bg_color}; color: {text_color}; padding: 10px; border-radius: 5px; margin-bottom: 5px;'>
                    <div style='display: grid; grid-template-columns: 0.5fr 1fr 1fr 1fr 1fr 1fr 1.5fr 1.5fr 1.5fr; gap: 10px;'>
                        <div><strong>{pos.get('ID')}</strong></div>
                        <div>{pos.get('Pozisyon Tipi', 'N/A')}</div>
                        <div>{pos.get('Piyasa', 'N/A')}</div>
                        <div>{pos.get('Giriş Fiyatı', 'N/A')}</div>
                        <div>{pos.get('Çıkış Fiyatı', 'N/A')}</div>
                        <div>{pos.get('Lot Büyüklüğü', 'N/A')}</div>
                        <div><strong>₺{result:,.2f}</strong></div>
                        <div>{pos.get('Açılış Tarihi', 'N/A')}</div>
                        <div>{pos.get('Kapanış Tarihi', 'N/A')}</div>
                    </div>
                </div>
                """
                st.markdown(row_html, unsafe_allow_html=True)

            # Detaylı görünüm
            st.markdown("#### 📖 Pozisyon Detayları")
            for pos in closed_positions:
                result = float(pos.get('Sonuç', 0))
                result_color = "green" if result > 0 else "red"

                with st.expander(f"{pos.get('Pozisyon Tipi')} - {pos.get('Piyasa', 'N/A')} | Sonuç: ₺{result:,.2f}", expanded=False):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Giriş:** ₺{pos.get('Giriş Fiyatı', 0)}")
                        st.markdown(f"**Çıkış:** ₺{pos.get('Çıkış Fiyatı', 0)}")
                        st.markdown(f"**Lot:** {pos.get('Lot Büyüklüğü', 0)}")
                        st.markdown(f"**Açılış:** {pos.get('Açılış Tarihi', 'N/A')}")
                        st.markdown(f"**Kapanış:** {pos.get('Kapanış Tarihi', 'N/A')}")

                    with col2:
                        st.markdown(f"**Plan:** {pos.get('Plan Notu', 'N/A')}")
                        st.markdown(f"**Öğrenilen Ders:** {pos.get('Öğrenilen Ders', 'N/A')}")
                        st.markdown(f"<div style='background-color: {result_color}; color: white; padding: 10px; border-radius: 5px; text-align: center; font-size: 20px; font-weight: bold;'>₺{result:,.2f}</div>", unsafe_allow_html=True)
        else:
            st.info("ℹ️ Henüz kapatılmış pozisyon yok.")

# =============================================================================
# DİĞER ÖZELLİKLER (Placeholder)
# =============================================================================

elif feature == "🖼️ Görsel Tecrübeler":
    st.markdown("## 🖼️ Görsel Tecrübeler")
    st.markdown("Hatalı işlemlerinizden görsel olarak ders çıkarın. Ekran görüntüleri ile hatalarınızı belgeleyin.")

    # Kategorileri yükle
    categories = load_categories()

    # Tecrübeleri yükle
    experiences_data = load_experiences_data()

    # İstatistikler
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Toplam Tecrübe", len(experiences_data) if experiences_data else 0)

    with col2:
        total_loss = sum([float(exp.get('Zarar Miktarı', 0)) for exp in experiences_data if exp.get('Zarar Miktarı')]) if experiences_data else 0
        st.metric("Toplam Zarar", f"₺{total_loss:,.2f}")

    with col3:
        unique_categories = set([exp.get('Kategori', '') for exp in experiences_data if exp.get('Kategori')]) if experiences_data else set()
        st.metric("Kategori Sayısı", len(unique_categories))

    st.markdown("---")

    # Tabs
    tab1, tab2 = st.tabs(["➕ Yeni Tecrübe Ekle", "📚 Tecrübelerim"])

    # YENİ TECRÜBE EKLE
    with tab1:
        st.markdown("### ➕ Yeni Görsel Tecrübe Ekle")

        with st.form("new_experience_form"):
            title = st.text_input("Başlık", placeholder="Örn: RSI Hatası - BTCUSDT Short")
            category = st.selectbox("Kategori", categories)
            note = st.text_area("Not / Ne Öğrendin?", placeholder="Bu hatadan ne öğrendin? Bir daha yapmamak için ne yapmalısın?", height=150)
            loss_amount = st.number_input("Zarar Miktarı (opsiyonel)", min_value=0.0, step=0.01, format="%.2f", value=0.0)

            uploaded_file = st.file_uploader("Görsel Yükle (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"])

            # Görsel önizleme
            if uploaded_file is not None:
                st.markdown("**Önizleme:**")
                image = Image.open(uploaded_file)
                st.image(image, width=400)

                # Dosya boyutu bilgisi
                file_size_kb = len(uploaded_file.getvalue()) / 1024
                if IMGBB_ENABLED:
                    st.success(f"✅ imgbb aktif! Orijinal: {file_size_kb:.1f} KB → Yüksek kalite: 1920x1440 @ 90%")
                else:
                    st.warning(f"⚠️ imgbb pasif! Orijinal: {file_size_kb:.1f} KB → Düşük kalite: 600x450 @ 50%")
                    st.info("💡 imgbb_utils.py dosyasına API key ekleyerek yüksek kalite aktif edilebilir!")

            submitted = st.form_submit_button("✅ Tecrübe Ekle", type="primary", use_container_width=True)

            if submitted:
                if title.strip() and category and note.strip() and uploaded_file is not None:
                    with st.spinner("Görsel yükleniyor..."):
                        image_data = None
                        is_url = False

                        # imgbb aktifse yüksek kalitede yükle
                        if IMGBB_ENABLED:
                            image = Image.open(uploaded_file)
                            filename = f"{title.replace(' ', '_')[:30]}"
                            result = upload_image_to_imgbb(image, filename)

                            if result:
                                image_data = result['url']
                                is_url = True
                                st.success("✅ Yüksek kaliteli görsel yüklendi! (imgbb)")
                            else:
                                st.warning("imgbb yüklenemedi, Base64'e geçiliyor...")

                        # Fallback: Base64 kullan
                        if not image_data:
                            uploaded_file.seek(0)  # Dosya pointer'ını başa al
                            base64_image = optimize_and_encode_image(uploaded_file)
                            if base64_image:
                                image_data = base64_image
                                is_url = False
                                st.info("ℹ️ Düşük kaliteli görsel kullanıldı (Base64)")

                        if image_data:
                            success = add_experience(title, category, note, image_data, loss_amount, is_url=is_url)
                            if success:
                                st.success("✅ Görsel tecrübe başarıyla eklendi!")
                                st.rerun()
                        else:
                            st.error("❌ Görsel işlenemedi!")
                else:
                    st.error("❌ Lütfen tüm gerekli alanları doldurun ve bir görsel yükleyin!")

    # TECRÜBELERİM
    with tab2:
        st.markdown("### 📚 Tecrübelerim")

        if experiences_data:
            # Kategori filtresi
            col_filter, col_count = st.columns([2, 1])

            with col_filter:
                filter_category = st.selectbox("Kategori Filtrele", ["Tümü"] + categories, key="filter_category")

            with col_count:
                filtered_count = len([exp for exp in experiences_data if filter_category == "Tümü" or exp.get('Kategori') == filter_category])
                st.metric("Filtrelenmiş", filtered_count)

            # Filtrele
            if filter_category != "Tümü":
                filtered_experiences = [exp for exp in experiences_data if exp.get('Kategori') == filter_category]
            else:
                filtered_experiences = experiences_data

            st.markdown("---")

            # Lazy loading kontrolü
            if "exp_page" not in st.session_state:
                st.session_state["exp_page"] = 0

            page_size = 10
            total_pages = (len(filtered_experiences) + page_size - 1) // page_size
            start_idx = st.session_state["exp_page"] * page_size
            end_idx = min(start_idx + page_size, len(filtered_experiences))

            # Tecrübeleri göster
            for exp in filtered_experiences[start_idx:end_idx]:
                exp_id = exp.get('ID')

                with st.expander(f"**{exp.get('Başlık', 'Başlıksız')}** | Kategori: {exp.get('Kategori', 'N/A')} | Tarih: {exp.get('Oluşturma Tarihi', 'N/A')}", expanded=False):
                    col_img, col_info = st.columns([1, 1])

                    with col_img:
                        # Görsel göster (imgbb URL veya Base64)
                        image_data = exp.get('Görsel URL', '')
                        if image_data:
                            try:
                                # URL ise (imgbb)
                                if image_data.startswith('http'):
                                    st.image(image_data, use_container_width=True, caption="Yüksek Kalite (imgbb)")
                                # Base64 ise
                                else:
                                    decoded_image = decode_base64_image(image_data)
                                    if decoded_image:
                                        st.image(decoded_image, use_container_width=True, caption="Düşük Kalite (Base64)")
                            except Exception as e:
                                st.warning(f"Görsel yüklenemedi: {e}")
                        else:
                            st.info("Görsel bulunamadı")

                    with col_info:
                        st.markdown(f"**ID:** {exp_id}")
                        st.markdown(f"**Kategori:** {exp.get('Kategori', 'N/A')}")
                        st.markdown(f"**Tarih:** {exp.get('Oluşturma Tarihi', 'N/A')}")

                        loss = exp.get('Zarar Miktarı', '')
                        if loss:
                            st.markdown(f"**Zarar:** ₺{float(loss):,.2f}")

                        st.markdown(f"**Not:**")
                        st.markdown(f"{exp.get('Not', 'Not yok')}")

                        st.markdown("---")

                        # Düzenle ve Sil butonları
                        col_edit, col_delete = st.columns(2)

                        with col_edit:
                            if st.button("✏️ Düzenle", key=f"edit_exp_{exp_id}", use_container_width=True):
                                st.session_state[f"edit_exp_{exp_id}"] = True
                                st.rerun()

                        with col_delete:
                            if st.button("🗑️ Sil", key=f"del_exp_{exp_id}", use_container_width=True):
                                st.session_state[f"confirm_delete_exp_{exp_id}"] = True
                                st.rerun()

                    # Edit modal
                    if st.session_state.get(f"edit_exp_{exp_id}"):
                        st.markdown("---")
                        st.markdown("**Tecrübeyi Düzenle:**")

                        with st.form(f"edit_exp_form_{exp_id}"):
                            new_title = st.text_input("Başlık", value=exp.get('Başlık', ''))
                            new_category = st.selectbox("Kategori", categories, index=categories.index(exp.get('Kategori', categories[0])) if exp.get('Kategori') in categories else 0)
                            new_note = st.text_area("Not", value=exp.get('Not', ''), height=150)
                            new_loss = st.number_input("Zarar Miktarı", min_value=0.0, step=0.01, value=float(exp.get('Zarar Miktarı', 0)) if exp.get('Zarar Miktarı') else 0.0)

                            st.info("ℹ️ Görseli değiştirmek için tecrübeyi silip yeniden eklemelisiniz.")

                            col_submit, col_cancel = st.columns(2)

                            with col_submit:
                                if st.form_submit_button("💾 Kaydet", use_container_width=True):
                                    if update_experience(exp_id, new_title, new_category, new_note, new_loss):
                                        st.success("✅ Tecrübe güncellendi!")
                                        st.session_state[f"edit_exp_{exp_id}"] = False
                                        st.rerun()

                            with col_cancel:
                                if st.form_submit_button("❌ İptal", use_container_width=True):
                                    st.session_state[f"edit_exp_{exp_id}"] = False
                                    st.rerun()

                    # Delete confirmation
                    if st.session_state.get(f"confirm_delete_exp_{exp_id}"):
                        st.warning(f"⚠️ **{exp.get('Başlık', 'Bu tecrübe')}** tecrübesini silmek istediğinize emin misiniz?")

                        col_confirm, col_cancel = st.columns(2)

                        with col_confirm:
                            if st.button("✅ Evet, Sil", key=f"confirm_del_{exp_id}", use_container_width=True):
                                if delete_experience(exp_id):
                                    st.success("✅ Tecrübe silindi!")
                                    st.session_state[f"confirm_delete_exp_{exp_id}"] = False
                                    st.rerun()

                        with col_cancel:
                            if st.button("❌ İptal", key=f"cancel_del_{exp_id}", use_container_width=True):
                                st.session_state[f"confirm_delete_exp_{exp_id}"] = False
                                st.rerun()

            # Pagination
            if total_pages > 1:
                st.markdown("---")
                col_prev, col_info, col_next = st.columns([1, 2, 1])

                with col_prev:
                    if st.button("⬅️ Önceki", disabled=st.session_state["exp_page"] == 0, use_container_width=True):
                        st.session_state["exp_page"] -= 1
                        st.rerun()

                with col_info:
                    st.markdown(f"**Sayfa {st.session_state['exp_page'] + 1} / {total_pages}**")

                with col_next:
                    if st.button("Sonraki ➡️", disabled=st.session_state["exp_page"] >= total_pages - 1, use_container_width=True):
                        st.session_state["exp_page"] += 1
                        st.rerun()

        else:
            st.info("ℹ️ Henüz görsel tecrübe eklenmemiş. Hatalı işlemlerinizden ders çıkarmak için ekran görüntüsü ekleyin!")

elif feature == "✅ İşlem Öncesi Kontrol":
    st.markdown("## ✅ İşlem Öncesi Kontrol")
    st.info("🚧 Bu özellik yakında eklenecek...")

elif feature == "📝 Kendime Notlar":
    st.markdown("## 📝 Kendime Notlar")
    st.caption("Trade bilgi ve becerilerini geliştirmek için notlar")

    # Kategori renkleri
    kategori_colors = {
        "📊 Formasyon": "#10b981",
        "📈 İndikatör": "#3b82f6",
        "🎯 Strateji": "#8b5cf6",
        "💡 Genel": "#f59e0b"
    }

    # Tabs: Notlarım & Yeni Not
    tab1, tab2 = st.tabs(["📚 Notlarım", "➕ Yeni Not Ekle"])

    with tab2:
        st.markdown("### ➕ Yeni Not Ekle")

        with st.form("add_note_form", clear_on_submit=True):
            col_left, col_right = st.columns([2, 1])

            with col_left:
                note_title = st.text_input("📌 Başlık", placeholder="Örn: Double Bottom Formasyonu")
                note_category = st.selectbox("🏷️ Kategori", list(kategori_colors.keys()))
                note_content = st.text_area("📝 İçerik", placeholder="Notlarınızı buraya yazın...", height=200)

            with col_right:
                st.markdown("**🖼️ Görsel Ekle (Opsiyonel)**")
                uploaded_image = st.file_uploader("Görsel yükle", type=['png', 'jpg', 'jpeg'], key="note_image")

                if uploaded_image:
                    st.image(uploaded_image, caption="Önizleme", use_container_width=True)

            if st.form_submit_button("💾 Notu Kaydet", use_container_width=True):
                if not note_title:
                    st.error("❌ Başlık boş olamaz!")
                elif not note_content:
                    st.error("❌ İçerik boş olamaz!")
                else:
                    # Görsel yükleme (imgbb)
                    image_url = ""
                    if uploaded_image:
                        if IMGBB_ENABLED:
                            st.info("📤 Görsel yükleniyor...")
                            image = Image.open(uploaded_image)
                            filename = f"{note_title.replace(' ', '_')[:30]}"
                            result = upload_image_to_imgbb(image, filename)

                            if result:
                                image_url = result['url']
                                st.success("✅ Görsel yüklendi! (Yüksek kalite)")
                            else:
                                st.warning("⚠️ Görsel yüklenemedi, not yine de kaydedilecek")
                        else:
                            st.warning("⚠️ imgbb pasif, görsel atlandı")

                    # Notu kaydet
                    if add_note(note_title, note_category, note_content, image_url):
                        st.success("✅ Not başarıyla kaydedildi!")
                        st.rerun()
                    else:
                        st.error("❌ Not kaydedilemedi!")

    with tab1:
        st.markdown("### 📚 Tüm Notlarım")

        # Filtreler
        col_search, col_filter = st.columns([2, 1])

        with col_search:
            search_query = st.text_input("🔍 Ara (Başlık/İçerik)", placeholder="Arama yap...")

        with col_filter:
            filter_category = st.selectbox("🏷️ Kategori Filtrele", ["Tümü"] + list(kategori_colors.keys()))

        # Notları yükle
        notes_data = load_notes_data()

        # Filtreleme
        if filter_category != "Tümü":
            notes_data = [n for n in notes_data if n.get('Kategori') == filter_category]

        if search_query:
            notes_data = [n for n in notes_data if
                         search_query.lower() in n.get('Başlık', '').lower() or
                         search_query.lower() in n.get('İçerik', '').lower()]

        # Sıralama (en yeni üstte)
        notes_data = sorted(notes_data, key=lambda x: x.get('Timestamp', ''), reverse=True)

        if notes_data:
            st.markdown(f"**{len(notes_data)} not bulundu**")

            # Notları kartlar halinde göster
            for note in notes_data:
                note_id = note.get('ID')
                note_baslik = note.get('Başlık', 'Başlıksız')
                note_kategori = note.get('Kategori', '💡 Genel')
                note_icerik = note.get('İçerik', '')
                note_gorsel = note.get('Görsel URL', '')
                note_tarih = note.get('Oluşturma Tarihi', '')

                # Kategori rengi
                kategori_color = kategori_colors.get(note_kategori, '#6b7280')

                # Not kartı
                with st.container():
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, {kategori_color}15, {kategori_color}25);
                        border-left: 4px solid {kategori_color};
                        padding: 20px;
                        border-radius: 10px;
                        margin: 15px 0;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <h3 style="margin: 0; color: #1e293b;">{note_baslik}</h3>
                            <span style="
                                background: {kategori_color};
                                color: white;
                                padding: 5px 15px;
                                border-radius: 20px;
                                font-size: 0.85rem;
                                font-weight: 600;
                            ">{note_kategori}</span>
                        </div>
                        <p style="color: #64748b; font-size: 0.9rem; margin: 10px 0;">{note_icerik[:200]}{'...' if len(note_icerik) > 200 else ''}</p>
                        <p style="color: #94a3b8; font-size: 0.8rem; margin: 5px 0;">📅 {note_tarih}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Görsel varsa göster
                    if note_gorsel and note_gorsel.startswith('http'):
                        with st.expander("🖼️ Görseli Göster"):
                            st.image(note_gorsel, use_container_width=True, caption="Yüksek Kalite (imgbb)")

                    # Detayları göster / Düzenle / Sil
                    col_detail, col_edit, col_delete = st.columns([2, 1, 1])

                    with col_detail:
                        if st.button("📖 Detayları Göster", key=f"detail_note_{note_id}", use_container_width=True):
                            st.session_state[f"show_detail_note_{note_id}"] = not st.session_state.get(f"show_detail_note_{note_id}", False)
                            st.rerun()

                    with col_edit:
                        if st.button("✏️ Düzenle", key=f"edit_note_{note_id}", use_container_width=True):
                            st.session_state[f"edit_mode_note_{note_id}"] = True
                            st.rerun()

                    with col_delete:
                        if st.button("🗑️ Sil", key=f"del_note_{note_id}", use_container_width=True):
                            st.session_state[f"confirm_delete_note_{note_id}"] = True
                            st.rerun()

                    # Detay modal
                    if st.session_state.get(f"show_detail_note_{note_id}"):
                        st.markdown("---")
                        st.markdown(f"**📖 Tam İçerik:**")
                        st.markdown(note_icerik)
                        st.markdown("---")

                    # Edit modal
                    if st.session_state.get(f"edit_mode_note_{note_id}"):
                        st.markdown("---")
                        st.markdown("**✏️ Notu Düzenle:**")

                        with st.form(f"edit_note_form_{note_id}"):
                            new_baslik = st.text_input("Başlık", value=note_baslik)
                            new_kategori = st.selectbox("Kategori", list(kategori_colors.keys()),
                                                       index=list(kategori_colors.keys()).index(note_kategori) if note_kategori in kategori_colors.keys() else 0)
                            new_icerik = st.text_area("İçerik", value=note_icerik, height=200)

                            st.info("ℹ️ Görseli değiştirmek için notu silip yeniden eklemelisiniz.")

                            col_submit, col_cancel = st.columns(2)

                            with col_submit:
                                if st.form_submit_button("💾 Kaydet", use_container_width=True):
                                    if update_note(note_id, new_baslik, new_kategori, new_icerik, note_gorsel):
                                        st.success("✅ Not güncellendi!")
                                        st.session_state[f"edit_mode_note_{note_id}"] = False
                                        st.rerun()

                            with col_cancel:
                                if st.form_submit_button("❌ İptal", use_container_width=True):
                                    st.session_state[f"edit_mode_note_{note_id}"] = False
                                    st.rerun()

                    # Delete confirmation
                    if st.session_state.get(f"confirm_delete_note_{note_id}"):
                        st.warning(f"⚠️ **{note_baslik}** notunu silmek istediğinize emin misiniz?")

                        col_confirm, col_cancel = st.columns(2)

                        with col_confirm:
                            if st.button("✅ Evet, Sil", key=f"confirm_del_note_{note_id}", use_container_width=True):
                                if delete_note(note_id):
                                    st.success("✅ Not silindi!")
                                    st.session_state[f"confirm_delete_note_{note_id}"] = False
                                    st.rerun()

                        with col_cancel:
                            if st.button("❌ İptal", key=f"cancel_del_note_{note_id}", use_container_width=True):
                                st.session_state[f"confirm_delete_note_{note_id}"] = False
                                st.rerun()

        else:
            st.info("ℹ️ Henüz not eklenmemiş. Trade bilgilerinizi kaydetmek için yeni not ekleyin!")

elif feature == "🏆 Challenge":
    st.markdown("## 🏆 Challenge (Meydan Okuma)")
    st.info("🚧 Bu özellik yakında eklenecek...")
