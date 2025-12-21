import streamlit as st
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(
    page_title="Para Komuta Merkezi",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# GOOGLE SHEETS AUTO-SETUP FUNCTIONS
# =============================================================================

@st.cache_resource
def get_sheets_client(_creds_data):
    """Connect to Google Sheets using credentials from session state."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(_creds_data, scope)
    client = gspread.authorize(creds)
    return client.open("PKM Database")

def initialize_all_sheets(spreadsheet):
    """
    Tüm gerekli sheet'leri kontrol et ve eksik olanları oluştur.
    Kullanıcı hiçbir şey yapmaz - otomatik kurulum!
    """
    # Tüm gerekli sheet'ler ve başlık satırları
    required_sheets = {
        'assets': ['ID', 'asset_type', 'symbol', 'amount', 'buy_price', 'data_source', 'manual_price', 'basket', 'created_at'],
        'debts': ['ID', 'debt_type', 'description', 'amount', 'due_date'],
        'asset_history': ['ID', 'asset_id', 'action', 'amount', 'price', 'date', 'notes'],
        'debt_history': ['ID', 'debt_id', 'action', 'amount', 'date', 'notes'],
        'closed_positions': ['ID', 'symbol', 'asset_type', 'amount', 'buy_price', 'sell_price', 'profit_loss', 'buy_date', 'sell_date', 'notes'],
        'Pozisyonlar': ['ID', 'Symbol', 'Tip', 'Pozisyon', 'Giriş', 'Stop', 'Hedef', 'Miktar', 'Durum', 'Tarih'],
        'Gorsel_Tecrubeler': ['ID', 'Tarih', 'Baslik', 'Aciklama', 'Kategori', 'Gorsel_URL', 'Delete_URL'],
        'Kategoriler': ['ID', 'Kategori_Adi', 'Renk'],
        'Ozlu_Sozler': ['ID', 'Tarih', 'Soz'],
        'Kendime_Notlar': ['ID', 'Tarih', 'Not'],
        'Challenge': ['ID', 'Tarih', 'Kar_Zarar', 'Kasa', 'Kalan_Gun', 'Hedef', 'Hedefe_Kalan_Tutar'],
        'Challenge_Settings': ['Baslangic_Sermaye', 'Hedef_Tutar', 'Hedef_Sure_Gun', 'Baslangic_Tarihi']
    }

    created_sheets = []
    existing_sheets = []

    for sheet_name, headers in required_sheets.items():
        try:
            # Önce var mı kontrol et
            spreadsheet.worksheet(sheet_name)
            existing_sheets.append(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # Yoksa oluştur
            try:
                sheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=len(headers))
                # Başlık satırını ekle
                sheet.append_row(headers)
                created_sheets.append(sheet_name)
            except Exception as e:
                st.error(f"❌ '{sheet_name}' sheet'i oluşturulurken hata: {e}")

    return created_sheets, existing_sheets

# =============================================================================
# LOCALSTORAGE PERSISTENCE
# =============================================================================
# NOT: localStorage verileri tarayıcıda saklanır ve sayfa yenilense bile kalır

# =============================================================================
# AUTHENTICATION & SETUP
# =============================================================================

# Session state başlatma
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'credentials_loaded' not in st.session_state:
    st.session_state['credentials_loaded'] = False
if 'imgbb_api_key' not in st.session_state:
    st.session_state['imgbb_api_key'] = ''


# 1. ŞİFRE KONTROLÜ
if not st.session_state['authenticated']:
    st.title("🔐 Para Komuta Merkezi - Giriş")
    st.markdown("---")

    st.markdown("""
    ### Hoş Geldiniz! 👋

    Bu platform **YouTube takipçilerimiz için özel** olarak hazırlanmıştır.

    Giriş şifresini YouTube videosunda bulabilirsiniz.

    💾 **Bir kez giriş yaptığınızda, bilgileriniz tarayıcınızda saklanacak ve bir daha girmenize gerek kalmayacak!**
    """)

    password = st.text_input("🔑 Giriş Şifresi", type="password", placeholder="YouTube'da paylaşılan şifre")

    if st.button("🚀 Giriş Yap", use_container_width=True):
        # Şifre kontrolü (YouTube'da paylaşacağın şifre)
        if password == "TRADE2025":
            st.session_state['authenticated'] = True

            # localStorage'a kaydet
            st.markdown(f"""
            <script>
            localStorage.setItem('pkm_password', 'TRADE2025');
            </script>
            """, unsafe_allow_html=True)

            st.success("✅ Giriş başarılı! Hoş geldiniz!")
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Yanlış şifre! Lütfen YouTube videosunu kontrol edin.")

    st.markdown("---")
    st.info("💡 **İlk kullanım mı?** YouTube kanalımızda kurulum videosunu izleyin!")
    st.stop()

# 2. CREDENTIALS.JSON YÜKLEME
if not st.session_state['credentials_loaded']:
    st.title("📄 Google Credentials Kurulumu")
    st.markdown("---")

    st.markdown("""
    ### Adım 2: Google Cloud Credentials Yükleyin

    Google Sheets'inizle bağlantı kurmak için **credentials.json** dosyanızı yüklemeniz gerekiyor.

    **Nasıl alınır?**
    1. [Google Cloud Console](https://console.cloud.google.com) → Projenize gidin
    2. "APIs & Services" → "Credentials"
    3. Service Account → Keys → JSON formatında indirin
    """)

    uploaded_file = st.file_uploader(
        "📤 credentials.json dosyanızı yükleyin",
        type=['json'],
        help="Google Cloud Console'dan indirdiğiniz service account key dosyası"
    )

    if uploaded_file:
        try:
            # JSON formatını kontrol et
            creds_data = json.load(uploaded_file)

            # Gerekli alanları kontrol et
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            if all(field in creds_data for field in required_fields):
                # Session state'e kaydet (dosyaya değil!)
                st.session_state['credentials_data'] = creds_data
                st.session_state['credentials_loaded'] = True

                # localStorage'a kaydet
                creds_json = json.dumps(creds_data)
                st.markdown(f"""
                <script>
                localStorage.setItem('pkm_credentials', '{creds_json.replace("'", "\\'")}');
                </script>
                """, unsafe_allow_html=True)

                st.success("✅ Credentials başarıyla yüklendi!")
                st.info(f"📧 Service Account: {creds_data['client_email']}")

                if st.button("Devam Et →"):
                    st.rerun()
            else:
                st.error("❌ Geçersiz credentials dosyası! Gerekli alanlar eksik.")
        except json.JSONDecodeError:
            st.error("❌ Geçersiz JSON dosyası!")
        except Exception as e:
            st.error(f"❌ Hata: {e}")

    st.markdown("---")
    with st.expander("❓ Yardıma mı ihtiyacınız var?"):
        st.markdown("""
        **Adım adım kurulum:**

        1. **Google Cloud Console'a gidin:** https://console.cloud.google.com
        2. **Yeni proje oluşturun** (veya mevcut projenizi seçin)
        3. **APIs & Services → Enable APIs** → "Google Sheets API" ve "Google Drive API" aktif edin
        4. **APIs & Services → Credentials → Create Credentials → Service Account**
        5. Service Account oluşturun, Keys sekmesine gidin
        6. **Add Key → Create New Key → JSON** formatını seçin
        7. İndirilen dosyayı buraya yükleyin
        """)

    st.stop()

# 3. IMGBB API KEY
if not st.session_state['imgbb_api_key']:
    st.title("🖼️ imgbb API Kurulumu")
    st.markdown("---")

    st.markdown("""
    ### Adım 3: imgbb API Key Girin

    Yüksek kaliteli görsel yükleme için **imgbb.com** hesabınızın API key'ini girin.

    **Nasıl alınır?**
    1. [imgbb.com](https://imgbb.com) → Ücretsiz kayıt olun
    2. [API sayfasına](https://api.imgbb.com/) gidin
    3. API Key'inizi kopyalayın
    """)

    col1, col2 = st.columns([3, 1])

    with col1:
        api_key = st.text_input(
            "🔑 imgbb API Key",
            type="password",
            placeholder="Örn: abc123def456..."
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Kaydet", use_container_width=True):
            if api_key and len(api_key) > 10:
                st.session_state['imgbb_api_key'] = api_key

                # localStorage'a kaydet
                st.markdown(f"""
                <script>
                localStorage.setItem('pkm_imgbb_api', '{api_key}');
                </script>
                """, unsafe_allow_html=True)

                st.success("✅ API Key kaydedildi!")
                st.rerun()
            else:
                st.error("❌ Geçerli bir API Key girin!")

    st.markdown("---")
    st.info("💡 **imgbb ücretsiz mi?** Evet! Aylık 5000 görsel yükleme limiti var (tamamen yeterli).")

    with st.expander("❓ imgbb hesabı nasıl açılır?"):
        st.markdown("""
        **Adım adım:**

        1. https://imgbb.com adresine gidin
        2. Sağ üstte **"Sign Up"** tıklayın
        3. E-posta ve şifre ile kayıt olun
        4. https://api.imgbb.com/ adresine gidin
        5. **"Get API Key"** butonuna tıklayın
        6. API Key'inizi kopyalayın ve buraya yapıştırın

        **Süre:** 2 dakika ⚡
        """)

    st.stop()

# =============================================================================
# ANA SAYFA (TÜM SETUP TAMAMLANDIYSA)
# =============================================================================

# =============================================================================
# OTOMATIK GOOGLE SHEETS KURULUMU
# =============================================================================

# İlk giriş kontrolü - sheet'leri otomatik oluştur
if 'sheets_initialized' not in st.session_state:
    st.session_state['sheets_initialized'] = False

if st.session_state['credentials_loaded'] and not st.session_state['sheets_initialized']:
    with st.spinner("📊 Google Sheets bağlantısı kontrol ediliyor..."):
        try:
            db = get_sheets_client(st.session_state['credentials_data'])

            with st.spinner("🔧 Gerekli sheet'ler kontrol ediliyor ve oluşturuluyor..."):
                created_sheets, existing_sheets = initialize_all_sheets(db)

            # Sonuç mesajı
            if created_sheets:
                st.success(f"✅ {len(created_sheets)} yeni sheet oluşturuldu!")
                with st.expander("📋 Oluşturulan sheet'ler"):
                    for sheet in created_sheets:
                        st.write(f"- {sheet}")

            if existing_sheets:
                st.info(f"ℹ️ {len(existing_sheets)} sheet zaten mevcut.")

            # Başarılı kurulum işaretle
            st.session_state['sheets_initialized'] = True

            # 2 saniye bekle ve sayfayı yenile
            import time
            time.sleep(2)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Google Sheets bağlantı hatası: {e}")
            st.warning("Lütfen Google Sheets'inizin adının **'PKM Database'** olduğundan ve service account'a paylaşıldığından emin olun!")
            st.stop()

# Sidebar - Kurulum Durumu
with st.sidebar:
    st.success("✅ Giriş yapıldı")
    st.success("✅ Credentials yüklendi")
    st.success("✅ imgbb API aktif")
    if st.session_state.get('sheets_initialized'):
        st.success("✅ Google Sheets hazır")
    st.markdown("---")

    # Çıkış butonu
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        # localStorage'ı temizle
        st.markdown("""
        <script>
        localStorage.removeItem('pkm_password');
        localStorage.removeItem('pkm_credentials');
        localStorage.removeItem('pkm_imgbb_api');
        </script>
        """, unsafe_allow_html=True)

        # Session state temizle
        st.session_state.clear()
        st.rerun()

# Ana sayfa başlık
st.title("💰 Para Komuta Merkezi")
st.markdown("### Hoş Geldiniz!")
st.markdown("---")

# Açıklama
st.markdown("""
**Para Komuta Merkezi**, finansal verilerinizi tek bir yerden yönetmenizi sağlayan kapsamlı bir platformdur.

Soldaki menüden bir modül seçerek başlayın! 👈
""")

st.markdown("---")

# Modül kartları
st.markdown("## 📚 Modüller")

col1, col2 = st.columns(2)

with col1:
    with st.container():
        st.markdown("### 📊 Portföy Yönetimi")
        st.markdown("""
        - Hisse senetleri, kripto paralar, emtia ve nakit varlıklarınızı takip edin
        - Güncel fiyatları otomatik çekin
        - Kar/Zarar hesaplamaları
        - Portföy dağılımı grafikleri
        """)
        if st.button("📊 Portföy'e Git", key="btn_portfoy", use_container_width=True):
            st.switch_page("pages/1_📊_Portföy.py")

with col2:
    with st.container():
        st.markdown("### 📈 Trade Asistanı")
        st.markdown("""
        - Trading pozisyonlarınızı yönetin
        - Hatalı işlemlerinizden ders çıkarın (Görsel Tecrübeler)
        - Kendime Notlar: Trade bilgilerinizi kaydedin
        - İşlem öncesi kontrol sistemi
        """)
        if st.button("📈 Trade Asistanı'na Git", key="btn_trade", use_container_width=True):
            st.switch_page("pages/2_📈_Trade_Asistani.py")

st.markdown("---")

col3, col4 = st.columns(2)

with col3:
    with st.container():
        st.markdown("### 💰 Bilanço Analizi")
        st.markdown("""
        - Şirket bilançolarını analiz edin
        - Finansal performans takibi
        - Trend analizi
        """)
        st.info("🚧 Yakında...")

with col4:
    with st.container():
        st.markdown("### 📉 F/K Analizi")
        st.markdown("""
        - Fiyat/Kazanç oranı analizi
        - Değerleme metrikleri
        - Karşılaştırmalı analiz
        """)
        st.info("🚧 Yakında...")

st.markdown("---")

# Footer
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>💰 Para Komuta Merkezi © 2024</p>
    <p>Finansal verilerinizi güvenle yönetin</p>
</div>
""", unsafe_allow_html=True)
