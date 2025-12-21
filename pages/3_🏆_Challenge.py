import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Challenge - Özgürlük Savaşı",
    page_icon="🏆",
    layout="wide"
)

# =============================================================================
# CREDENTIALS CHECK
# =============================================================================

if 'credentials_data' not in st.session_state or not st.session_state.get('credentials_loaded', False):
    st.error("❌ Credentials yüklenmemiş! Lütfen ana sayfadan credentials.json dosyanızı yükleyin.")
    if st.button("🏠 Ana Sayfaya Git"):
        st.switch_page("Home.py")
    st.stop()

# =============================================================================
# GOOGLE SHEETS FUNCTIONS
# =============================================================================

@st.cache_resource
def get_google_sheets(_creds_data):
    """Google Sheets bağlantısını döndürür"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(_creds_data, scope)
    client = gspread.authorize(creds)
    return client.open("PKM Database")

def get_sheet_data_as_dict(sheet):
    """Sheet verisini dictionary listesi olarak döndürür"""
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
# CHALLENGE FUNCTIONS
# =============================================================================

def get_challenge_settings():
    """Challenge ayarlarını yükler"""
    try:
        spreadsheet = get_google_sheets(st.session_state['credentials_data'])
        sheet = spreadsheet.worksheet('Challenge_Settings')
        data = get_sheet_data_as_dict(sheet)

        if data:
            return {
                'baslangic_sermaye': float(data[0].get('Baslangic_Sermaye', 0)),
                'hedef_tutar': float(data[0].get('Hedef_Tutar', 0)),
                'hedef_sure_gun': int(data[0].get('Hedef_Sure_Gun', 0)),
                'baslangic_tarihi': data[0].get('Baslangic_Tarihi', '')
            }
        return None
    except Exception as e:
        st.error(f"Challenge ayarları yüklenirken hata: {e}")
        return None

def save_challenge_settings(baslangic_sermaye, hedef_tutar, hedef_sure_gun):
    """Challenge ayarlarını kaydeder"""
    try:
        spreadsheet = get_google_sheets(st.session_state['credentials_data'])
        sheet = spreadsheet.worksheet('Challenge_Settings')

        # Mevcut veriyi temizle
        sheet.clear()

        # Başlık satırı
        headers = ['Baslangic_Sermaye', 'Hedef_Tutar', 'Hedef_Sure_Gun', 'Baslangic_Tarihi']
        sheet.append_row(headers)

        # Ayarları kaydet
        now = datetime.now().strftime('%Y-%m-%d')
        row = [baslangic_sermaye, hedef_tutar, hedef_sure_gun, now]
        sheet.append_row(row)

        # İlk gün kaydını Challenge sheet'ine ekle
        challenge_sheet = spreadsheet.worksheet('Challenge')
        challenge_data = get_sheet_data_as_dict(challenge_sheet)

        # Eğer hiç kayıt yoksa ilk günü ekle
        if not challenge_data:
            next_id = get_next_id(challenge_sheet)
            challenge_row = [
                next_id,
                now,
                0,  # Kar/Zarar (ilk gün 0)
                baslangic_sermaye,  # Kasa
                hedef_sure_gun,  # Kalan Gün
                hedef_tutar,  # Hedef
                hedef_tutar - baslangic_sermaye  # Hedefe Kalan Tutar
            ]
            challenge_sheet.append_row(challenge_row)

        return True
    except Exception as e:
        st.error(f"Challenge ayarları kaydedilirken hata: {e}")
        return False

def get_challenge_data():
    """Challenge verilerini yükler"""
    try:
        spreadsheet = get_google_sheets(st.session_state['credentials_data'])
        sheet = spreadsheet.worksheet('Challenge')
        data = get_sheet_data_as_dict(sheet)
        return data
    except Exception as e:
        st.error(f"Challenge verileri yüklenirken hata: {e}")
        return []

def get_current_portfolio_value():
    """Portföy sayfasından toplam varlık değerini alır"""
    try:
        spreadsheet = get_google_sheets(st.session_state['credentials_data'])
        assets_sheet = spreadsheet.worksheet('assets')
        assets = get_sheet_data_as_dict(assets_sheet)

        # Basit toplam hesaplama (gerçek fiyatları çekmeden)
        total = 0
        for asset in assets:
            try:
                amount = float(asset.get('amount', 0))
                buy_price = float(asset.get('buy_price', 0))
                total += amount * buy_price
            except:
                continue

        return total
    except Exception as e:
        st.error(f"Portföy değeri hesaplanırken hata: {e}")
        return 0

def add_daily_record(kasa_tutari, settings):
    """Günlük kayıt ekler"""
    try:
        spreadsheet = get_google_sheets(st.session_state['credentials_data'])
        sheet = spreadsheet.worksheet('Challenge')

        # Bugünün tarihi
        today = datetime.now().strftime('%Y-%m-%d')

        # Bugün kayıt var mı kontrol et
        data = get_sheet_data_as_dict(sheet)
        today_exists = any(row.get('Tarih') == today for row in data)

        if today_exists:
            st.warning("⚠️ Bugün için kayıt zaten mevcut!")
            return False

        # Başlangıç tarihi
        start_date = datetime.strptime(settings['baslangic_tarihi'], '%Y-%m-%d')
        current_date = datetime.now()

        # Geçen gün sayısı
        days_passed = (current_date - start_date).days

        # Kalan gün
        remaining_days = settings['hedef_sure_gun'] - days_passed

        # Önceki gün kasası (kar/zarar hesabı için)
        previous_kasa = settings['baslangic_sermaye']
        if data:
            # En son kaydı bul
            sorted_data = sorted(data, key=lambda x: x.get('Tarih', ''), reverse=True)
            if sorted_data:
                previous_kasa = float(sorted_data[0].get('Kasa', settings['baslangic_sermaye']))

        # Kar/Zarar
        kar_zarar = kasa_tutari - previous_kasa

        # Hedefe kalan tutar
        hedefe_kalan = settings['hedef_tutar'] - kasa_tutari

        # Yeni kayıt ekle
        next_id = get_next_id(sheet)
        row = [
            next_id,
            today,
            kar_zarar,
            kasa_tutari,
            remaining_days,
            settings['hedef_tutar'],
            hedefe_kalan
        ]

        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Günlük kayıt eklenirken hata: {e}")
        return False

# =============================================================================
# MAIN PAGE
# =============================================================================

st.title("🏆 Özgürlük Savaşı")
st.markdown("### Finansal hedefine ulaşma yolculuğunu takip et!")
st.markdown("---")

# Challenge ayarlarını kontrol et
settings = get_challenge_settings()

if not settings or settings['baslangic_sermaye'] == 0:
    # İlk kurulum
    st.info("🎯 Challenge'ı başlatmak için aşağıdaki bilgileri girin!")

    col1, col2, col3 = st.columns(3)

    with col1:
        baslangic_sermaye = st.number_input(
            "💰 Başlangıç Sermayesi (TL)",
            min_value=0.0,
            step=100.0,
            value=1000.0
        )

    with col2:
        hedef_tutar = st.number_input(
            "🎯 Hedef Tutar (TL)",
            min_value=0.0,
            step=1000.0,
            value=10000.0
        )

    with col3:
        hedef_sure_gun = st.number_input(
            "⏱️ Hedef Süre (Gün)",
            min_value=1,
            step=1,
            value=365
        )

    st.markdown("---")

    if st.button("🚀 Savaşı Başlat!", type="primary", use_container_width=True):
        if baslangic_sermaye > 0 and hedef_tutar > baslangic_sermaye and hedef_sure_gun > 0:
            if save_challenge_settings(baslangic_sermaye, hedef_tutar, hedef_sure_gun):
                st.success("✅ Challenge başlatıldı!")
                st.balloons()
                st.rerun()
        else:
            st.error("❌ Lütfen geçerli değerler girin! (Hedef > Başlangıç olmalı)")

else:
    # Challenge aktif - verileri göster

    # Güncel verileri al
    challenge_data = get_challenge_data()

    # Başlangıç tarihi
    start_date = datetime.strptime(settings['baslangic_tarihi'], '%Y-%m-%d')
    current_date = datetime.now()

    # Geçen ve kalan gün
    days_passed = (current_date - start_date).days
    remaining_days = max(0, settings['hedef_sure_gun'] - days_passed)

    # Anlık kasa (en son kayıt)
    current_kasa = settings['baslangic_sermaye']
    if challenge_data:
        sorted_data = sorted(challenge_data, key=lambda x: x.get('Tarih', ''), reverse=True)
        if sorted_data:
            current_kasa = float(sorted_data[0].get('Kasa', settings['baslangic_sermaye']))

    # Hedefe kalan tutar
    hedefe_kalan = settings['hedef_tutar'] - current_kasa

    # Günlük hedef
    if remaining_days > 0:
        gunluk_hedef = hedefe_kalan / remaining_days
    else:
        gunluk_hedef = 0

    # ÜST BİLGİ KUTULARI
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="💵 Anlık Kasa",
            value=f"₺{current_kasa:,.2f}",
            delta=f"₺{current_kasa - settings['baslangic_sermaye']:,.2f}"
        )

    with col2:
        st.metric(
            label="⏰ Kalan Gün",
            value=f"{remaining_days} gün",
            delta=f"-{days_passed} gün geçti"
        )

    with col3:
        st.metric(
            label="🎯 Hedefe Kalan",
            value=f"₺{hedefe_kalan:,.2f}",
            delta=f"Hedef: ₺{settings['hedef_tutar']:,.2f}"
        )

    with col4:
        st.metric(
            label="📈 Günlük Hedef",
            value=f"₺{gunluk_hedef:,.2f}/gün",
            delta="Ortalama kazanç hedefi"
        )

    st.markdown("---")

    # GÜNLÜK KAYIT EKLEME
    with st.expander("➕ Bugünün Kaydını Ekle"):
        st.markdown("**Portföy değerinizi manuel girin veya otomatik hesaplayın:**")

        col_a, col_b = st.columns(2)

        with col_a:
            manual_kasa = st.number_input(
                "💰 Bugünkü Kasa Tutarı (TL)",
                min_value=0.0,
                step=10.0,
                value=current_kasa
            )

        with col_b:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📊 Portföyden Otomatik Al"):
                portfolio_value = get_current_portfolio_value()
                if portfolio_value > 0:
                    manual_kasa = portfolio_value
                    st.success(f"✅ Portföy değeri: ₺{portfolio_value:,.2f}")

        if st.button("💾 Bugünün Kaydını Kaydet", type="primary", use_container_width=True):
            if add_daily_record(manual_kasa, settings):
                st.success("✅ Bugünün kaydı eklendi!")
                st.rerun()

    st.markdown("---")

    # GRAFİK
    if challenge_data:
        st.markdown("### 📈 Kasa Gelişimi")

        # Veriyi DataFrame'e çevir
        df = pd.DataFrame(challenge_data)
        df['Tarih'] = pd.to_datetime(df['Tarih'])
        df['Kasa'] = df['Kasa'].astype(float)
        df = df.sort_values('Tarih')

        # Plotly grafik
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df['Tarih'],
            y=df['Kasa'],
            mode='lines+markers',
            name='Kasa',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=8)
        ))

        fig.update_layout(
            title="Kasa-Tarih Grafiği",
            xaxis_title="Tarih",
            yaxis_title="Kasa (TL)",
            hovermode='x unified',
            template='plotly_white',
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # TABLO
    if challenge_data:
        st.markdown("### 📋 Kayıtlar")

        # Veriyi DataFrame'e çevir
        df = pd.DataFrame(challenge_data)

        # Sütunları düzenle
        df = df[['Tarih', 'Kar_Zarar', 'Kasa', 'Kalan_Gun', 'Hedef', 'Hedefe_Kalan_Tutar']]

        # Kolonları Türkçe yap
        df.columns = ['Tarih', 'Kar/Zarar', 'Kasa', 'Kalan Gün', 'Hedef', 'Hedefe Kalan']

        # Tarihe göre sırala (en yeni en üstte)
        df = df.sort_values('Tarih', ascending=False)

        # Sayısal formatlama
        df['Kar/Zarar'] = df['Kar/Zarar'].astype(float).apply(lambda x: f"₺{x:,.2f}")
        df['Kasa'] = df['Kasa'].astype(float).apply(lambda x: f"₺{x:,.2f}")
        df['Hedef'] = df['Hedef'].astype(float).apply(lambda x: f"₺{x:,.2f}")
        df['Hedefe Kalan'] = df['Hedefe Kalan'].astype(float).apply(lambda x: f"₺{x:,.2f}")

        st.dataframe(df, use_container_width=True, height=400)

    st.markdown("---")

    # RESET BUTONU
    with st.expander("⚙️ Challenge Ayarları"):
        st.warning("⚠️ Challenge'ı sıfırlamak tüm kayıtları silecektir!")

        if st.button("🔄 Challenge'ı Sıfırla", type="secondary"):
            try:
                spreadsheet = get_google_sheets(st.session_state['credentials_data'])

                # Challenge ve Settings sheet'lerini temizle
                challenge_sheet = spreadsheet.worksheet('Challenge')
                settings_sheet = spreadsheet.worksheet('Challenge_Settings')

                challenge_sheet.clear()
                settings_sheet.clear()

                # Başlıkları geri ekle
                challenge_sheet.append_row(['ID', 'Tarih', 'Kar_Zarar', 'Kasa', 'Kalan_Gun', 'Hedef', 'Hedefe_Kalan_Tutar'])
                settings_sheet.append_row(['Baslangic_Sermaye', 'Hedef_Tutar', 'Hedef_Sure_Gun', 'Baslangic_Tarihi'])

                st.success("✅ Challenge sıfırlandı!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Sıfırlama hatası: {e}")
