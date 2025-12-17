import streamlit as st

st.set_page_config(
    page_title="Para Komuta Merkezi",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        - Hatalı işlemlerinizden ders çıkarın
        - İşlem öncesi kontrol sistemi
        - Challenge (Meydan okuma) takibi
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
