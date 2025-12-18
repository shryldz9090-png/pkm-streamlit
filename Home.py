import streamlit as st
import json
import os

st.set_page_config(
    page_title="Para Komuta Merkezi",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    """)

    password = st.text_input("🔑 Giriş Şifresi", type="password", placeholder="YouTube'da paylaşılan şifre")

    if st.button("🚀 Giriş Yap", use_container_width=True):
        # Şifre kontrolü (YouTube'da paylaşacağın şifre)
        if password == "TRADE2025":
            st.session_state['authenticated'] = True
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
                # Geçici dosyaya kaydet
                with open('credentials.json', 'w') as f:
                    json.dump(creds_data, f)

                st.session_state['credentials_loaded'] = True
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

# Sidebar - Kurulum Durumu
with st.sidebar:
    st.success("✅ Giriş yapıldı")
    st.success("✅ Credentials yüklendi")
    st.success("✅ imgbb API aktif")
    st.markdown("---")

    # Çıkış butonu
    if st.button("🚪 Çıkış Yap", use_container_width=True):
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
