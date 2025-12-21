import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Özgürlük Savaşı",
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

def safe_float(value, default=0):
    """String'i güvenli şekilde float'a çevirir (virgül ve nokta desteği)"""
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if not value or value == '':
            return default
        # Virgülü noktaya çevir
        value_str = str(value).replace(',', '.')
        return float(value_str)
    except:
        return default

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
# İŞLEM YÖNETİMİ FONKSİYONLARI
# =============================================================================

def load_challenge_trades():
    """Özgürlük Savaşı işlemlerini yükler"""
    try:
        spreadsheet = get_google_sheets(st.session_state['credentials_data'])
        sheet = spreadsheet.worksheet('Challenge_Trades')
        data = get_sheet_data_as_dict(sheet)
        return data
    except gspread.exceptions.WorksheetNotFound:
        # Sheet yoksa oluştur
        spreadsheet = get_google_sheets(st.session_state['credentials_data'])
        sheet = spreadsheet.add_worksheet(title='Challenge_Trades', rows=100, cols=10)
        headers = ['ID', 'Yon', 'Enstruman', 'Giris_Fiyat', 'Lot', 'Cikis_Fiyat', 'Kar_Zarar', 'Durum', 'Acilis_Tarihi', 'Kapanis_Tarihi']
        sheet.append_row(headers)
        return []
    except Exception as e:
        st.error(f"İşlemler yüklenirken hata: {e}")
        return []

def add_trade(yon, enstruman, giris_fiyat, lot):
    """Yeni işlem aç"""
    try:
        spreadsheet = get_google_sheets(st.session_state['credentials_data'])
        sheet = spreadsheet.worksheet('Challenge_Trades')

        next_id = get_next_id(sheet)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        row = [
            next_id,
            yon,
            enstruman,
            float(giris_fiyat),
            float(lot),
            '',  # Çıkış fiyatı (henüz yok)
            '',  # Kar/Zarar (henüz yok)
            'ACIK',  # Durum
            now,  # Açılış tarihi
            ''  # Kapanış tarihi (henüz yok)
        ]

        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"İşlem eklenirken hata: {e}")
        return False

def close_trade(trade_id, cikis_fiyat):
    """İşlemi kapat"""
    try:
        spreadsheet = get_google_sheets(st.session_state['credentials_data'])
        sheet = spreadsheet.worksheet('Challenge_Trades')

        all_data = sheet.get_all_values()
        header = all_data[0]

        # Kolon indekslerini bul
        id_col = header.index('ID') + 1
        yon_col = header.index('Yon') + 1
        giris_col = header.index('Giris_Fiyat') + 1
        lot_col = header.index('Lot') + 1
        cikis_col = header.index('Cikis_Fiyat') + 1
        kar_zarar_col = header.index('Kar_Zarar') + 1
        durum_col = header.index('Durum') + 1
        kapanis_col = header.index('Kapanis_Tarihi') + 1

        # Satırı bul ve güncelle
        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(trade_id):
                yon = row[yon_col - 1]
                giris = float(row[giris_col - 1])
                lot = float(row[lot_col - 1])

                # Kar/Zarar hesapla
                if yon == 'LONG':
                    kar_zarar = (float(cikis_fiyat) - giris) * lot
                else:  # SHORT
                    kar_zarar = (giris - float(cikis_fiyat)) * lot

                # Güncelleme yap
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                sheet.update_cell(row_idx, cikis_col, float(cikis_fiyat))
                sheet.update_cell(row_idx, kar_zarar_col, round(kar_zarar, 2))
                sheet.update_cell(row_idx, durum_col, 'KAPALI')
                sheet.update_cell(row_idx, kapanis_col, now)

                return True, kar_zarar

        return False, 0
    except Exception as e:
        st.error(f"İşlem kapatılırken hata: {e}")
        return False, 0

def delete_closed_trade(trade_id):
    """Kapatılmış işlemi sil"""
    try:
        spreadsheet = get_google_sheets(st.session_state['credentials_data'])
        sheet = spreadsheet.worksheet('Challenge_Trades')

        all_data = sheet.get_all_values()
        header = all_data[0]
        id_col = header.index('ID') + 1

        # Satırı bul ve sil
        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(trade_id):
                sheet.delete_rows(row_idx)
                return True

        return False
    except Exception as e:
        st.error(f"İşlem silinirken hata: {e}")
        return False

def update_closed_trade(trade_id, cikis_fiyat):
    """Kapatılmış işlemin çıkış fiyatını güncelle"""
    try:
        spreadsheet = get_google_sheets(st.session_state['credentials_data'])
        sheet = spreadsheet.worksheet('Challenge_Trades')

        all_data = sheet.get_all_values()
        header = all_data[0]

        # Kolon indekslerini bul
        id_col = header.index('ID') + 1
        yon_col = header.index('Yon') + 1
        giris_col = header.index('Giris_Fiyat') + 1
        lot_col = header.index('Lot') + 1
        cikis_col = header.index('Cikis_Fiyat') + 1
        kar_zarar_col = header.index('Kar_Zarar') + 1

        # Satırı bul ve güncelle
        for row_idx, row in enumerate(all_data[1:], start=2):
            if str(row[id_col - 1]) == str(trade_id):
                yon = row[yon_col - 1]
                giris = float(row[giris_col - 1])
                lot = float(row[lot_col - 1])

                # Kar/Zarar yeniden hesapla
                if yon == 'LONG':
                    kar_zarar = (float(cikis_fiyat) - giris) * lot
                else:  # SHORT
                    kar_zarar = (giris - float(cikis_fiyat)) * lot

                # Güncelleme yap
                sheet.update_cell(row_idx, cikis_col, float(cikis_fiyat))
                sheet.update_cell(row_idx, kar_zarar_col, round(kar_zarar, 2))

                return True

        return False
    except Exception as e:
        st.error(f"İşlem güncellenirken hata: {e}")
        return False

# =============================================================================
# MAIN PAGE
# =============================================================================

st.title("🏆 Özgürlük Savaşı")
st.markdown("### Finansal özgürlüğe giden yolculuk!")
st.markdown("---")

# Challenge ayarlarını kontrol et
settings = get_challenge_settings()

if not settings or settings['baslangic_sermaye'] == 0:
    # İlk kurulum
    st.info("🎯 Savaşı başlatmak için aşağıdaki bilgileri girin!")

    col1, col2, col3 = st.columns(3)

    with col1:
        baslangic_sermaye = st.number_input(
            "💰 Başlangıç Sermayesi ($)",
            min_value=0.0,
            step=100.0,
            value=1000.0
        )

    with col2:
        hedef_tutar = st.number_input(
            "🎯 Hedef Tutar ($)",
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
    # Challenge aktif

    # İşlemleri yükle
    trades = load_challenge_trades()
    acik_trades = [t for t in trades if t.get('Durum') == 'ACIK']
    kapali_trades = [t for t in trades if t.get('Durum') == 'KAPALI']

    # Toplam kar/zarar hesapla
    toplam_kar_zarar = sum([float(t.get('Kar_Zarar', 0)) for t in kapali_trades if t.get('Kar_Zarar')])

    # Anlık kasa
    current_kasa = settings['baslangic_sermaye'] + toplam_kar_zarar

    # Başlangıç tarihi
    start_date = datetime.strptime(settings['baslangic_tarihi'], '%Y-%m-%d')
    current_date = datetime.now()

    # Geçen ve kalan gün
    days_passed = (current_date - start_date).days
    remaining_days = max(0, settings['hedef_sure_gun'] - days_passed)

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
            value=f"${current_kasa:,.2f}",
            delta=f"${toplam_kar_zarar:,.2f}"
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
            value=f"${hedefe_kalan:,.2f}",
            delta=f"Hedef: ${settings['hedef_tutar']:,.2f}"
        )

    with col4:
        st.metric(
            label="📈 Günlük Hedef",
            value=f"${gunluk_hedef:,.2f}/gün",
            delta="Ortalama kazanç hedefi"
        )

    st.markdown("---")

    # YENİ İŞLEM AÇ
    with st.expander("➕ Yeni İşlem Aç", expanded=False):
        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            yon = st.selectbox("📊 İşlem Yönü", ["LONG", "SHORT"])

        with col_b:
            enstruman = st.text_input("🪙 Enstrüman", placeholder="GOLD, BTC, EUR/USD...")

        with col_c:
            giris_fiyat = st.number_input("💵 Giriş Fiyatı", min_value=0.0, step=0.01, value=0.0)

        with col_d:
            lot = st.number_input("📏 Lot Büyüklüğü", min_value=0.0, step=0.01, value=1.0)

        if st.button("💾 İşlemi Kaydet", type="primary", use_container_width=True):
            if enstruman and giris_fiyat > 0 and lot > 0:
                if add_trade(yon, enstruman, giris_fiyat, lot):
                    st.success("✅ İşlem açıldı!")
                    st.rerun()
            else:
                st.error("❌ Lütfen tüm alanları doldurun!")

    st.markdown("---")

    # AÇIK İŞLEMLER
    st.markdown("### 🟢 Açık İşlemler")

    if acik_trades:
        for trade in acik_trades:
            trade_id = trade.get('ID')
            yon = trade.get('Yon')
            enstruman = trade.get('Enstruman')
            giris = float(trade.get('Giris_Fiyat', 0))
            lot = float(trade.get('Lot', 0))
            tarih = trade.get('Acilis_Tarihi', '')

            with st.container():
                col_info, col_action = st.columns([3, 1])

                with col_info:
                    yon_emoji = "🟢" if yon == "LONG" else "🔴"
                    st.markdown(f"**{yon_emoji} {yon} - {enstruman}**")
                    st.markdown(f"Giriş: ${giris:,.2f} | Lot: {lot} | Tarih: {tarih}")

                with col_action:
                    cikis_fiyat = st.number_input(
                        "Çıkış Fiyatı",
                        min_value=0.0,
                        step=0.01,
                        value=0.0,
                        key=f"cikis_{trade_id}"
                    )

                    if st.button("❌ Kapat", key=f"close_{trade_id}", use_container_width=True):
                        if cikis_fiyat > 0:
                            success, kar_zarar = close_trade(trade_id, cikis_fiyat)
                            if success:
                                st.success(f"✅ İşlem kapatıldı! Kar/Zarar: ${kar_zarar:,.2f}")
                                st.rerun()
                        else:
                            st.error("❌ Çıkış fiyatı girmelisiniz!")

                st.markdown("---")
    else:
        st.info("ℹ️ Henüz açık işlem yok.")

    st.markdown("---")

    # KASA GRAFİĞİ
    st.markdown("### 📈 Kasa Gelişimi")

    if kapali_trades:
        # Kasa gelişimini hesapla
        kasa_data = []
        running_kasa = settings['baslangic_sermaye']

        # Başlangıç noktası
        kasa_data.append({
            'Tarih': settings['baslangic_tarihi'],
            'Kasa': running_kasa
        })

        # Her işlemden sonra kasayı güncelle
        sorted_trades = sorted(kapali_trades, key=lambda x: x.get('Kapanis_Tarihi', ''))
        for trade in sorted_trades:
            kar_zarar = safe_float(trade.get('Kar_Zarar', 0))
            running_kasa += kar_zarar
            kasa_data.append({
                'Tarih': trade.get('Kapanis_Tarihi', '').split(' ')[0],  # Sadece tarih
                'Kasa': running_kasa
            })

        # DataFrame oluştur
        df_kasa = pd.DataFrame(kasa_data)
        df_kasa['Tarih'] = pd.to_datetime(df_kasa['Tarih'])

        # Plotly grafik
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_kasa['Tarih'],
            y=df_kasa['Kasa'],
            mode='lines+markers',
            name='Kasa',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=8),
            fill='tozeroy',
            fillcolor='rgba(59, 130, 246, 0.1)'
        ))

        fig.update_layout(
            title="Kasa-Tarih Grafiği",
            xaxis_title="Tarih",
            yaxis_title="Kasa ($)",
            hovermode='x unified',
            template='plotly_white',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # KAPATILAN İŞLEMLER
    st.markdown("### 📋 Kapatılan İşlemler")

    if kapali_trades:
        # En son kapananlar üstte olsun
        sorted_trades = sorted(kapali_trades, key=lambda x: x.get('Kapanis_Tarihi', ''), reverse=True)

        # Tablo başlığı
        header_cols = st.columns([1, 1.5, 1, 0.8, 1, 1, 1.5, 1.5, 1.5])
        header_cols[0].markdown("**Yon**")
        header_cols[1].markdown("**Enstruman**")
        header_cols[2].markdown("**Giriş_Fiyat**")
        header_cols[3].markdown("**Lot**")
        header_cols[4].markdown("**Çıkış_Fiyat**")
        header_cols[5].markdown("**Kar_Zarar**")
        header_cols[6].markdown("**Açılış_Tarihi**")
        header_cols[7].markdown("**Kapanış_Tarihi**")
        header_cols[8].markdown("**İşlemler**")

        st.markdown("---")

        # Her işlem için satır
        for trade in sorted_trades:
            trade_id = trade.get('ID', '')
            kar_zarar = safe_float(trade.get('Kar_Zarar', 0))

            # Kar/Zarar için renk
            if kar_zarar > 0:
                kar_zarar_color = "🟢"  # Yeşil
                kar_zarar_text = f"${kar_zarar:,.2f}"
            else:
                kar_zarar_color = "🔴"  # Kırmızı
                kar_zarar_text = f"${kar_zarar:,.2f}"

            cols = st.columns([1, 1.5, 1, 0.8, 1, 1, 1.5, 1.5, 1.5])

            cols[0].write(trade.get('Yon', ''))
            cols[1].write(trade.get('Enstruman', ''))
            cols[2].write(f"${safe_float(trade.get('Giris_Fiyat', 0)):,.2f}")
            cols[3].write(trade.get('Lot', ''))
            cols[4].write(f"${safe_float(trade.get('Cikis_Fiyat', 0)):,.2f}")
            cols[5].markdown(f"{kar_zarar_color} **{kar_zarar_text}**")
            cols[6].write(trade.get('Acilis_Tarihi', ''))
            cols[7].write(trade.get('Kapanis_Tarihi', ''))

            # İşlem butonları
            btn_col1, btn_col2 = cols[8].columns(2)

            # Düzenle butonu
            if btn_col1.button("✏️", key=f"edit_closed_{trade_id}", help="Düzenle"):
                st.session_state[f'edit_closed_{trade_id}'] = True

            # Sil butonu
            if btn_col2.button("🗑️", key=f"del_closed_{trade_id}", help="Sil"):
                if delete_closed_trade(trade_id):
                    st.success("✅ İşlem silindi!")
                    st.rerun()
                else:
                    st.error("❌ İşlem silinemedi!")

            # Düzenleme modalı
            if st.session_state.get(f'edit_closed_{trade_id}', False):
                with st.expander(f"✏️ İşlem #{trade_id} Düzenle", expanded=True):
                    new_cikis = st.number_input(
                        "Yeni Çıkış Fiyatı",
                        value=safe_float(trade.get('Cikis_Fiyat', 0)),
                        step=0.01,
                        key=f"new_cikis_{trade_id}"
                    )

                    col_btn1, col_btn2 = st.columns(2)

                    if col_btn1.button("💾 Kaydet", key=f"save_{trade_id}"):
                        if update_closed_trade(trade_id, new_cikis):
                            st.success("✅ İşlem güncellendi!")
                            st.session_state[f'edit_closed_{trade_id}'] = False
                            st.rerun()
                        else:
                            st.error("❌ Güncelleme başarısız!")

                    if col_btn2.button("❌ İptal", key=f"cancel_{trade_id}"):
                        st.session_state[f'edit_closed_{trade_id}'] = False
                        st.rerun()

            st.markdown("---")
    else:
        st.info("ℹ️ Henüz kapatılmış işlem yok.")

    st.markdown("---")

    # RESET BUTONU
    with st.expander("⚙️ Challenge Ayarları"):
        st.warning("⚠️ Challenge'ı sıfırlamak tüm kayıtları silecektir!")

        if st.button("🔄 Challenge'ı Sıfırla", type="secondary"):
            try:
                spreadsheet = get_google_sheets(st.session_state['credentials_data'])

                # Tüm sheet'leri temizle
                for sheet_name in ['Challenge', 'Challenge_Settings', 'Challenge_Trades']:
                    try:
                        sheet = spreadsheet.worksheet(sheet_name)
                        sheet.clear()

                        # Başlıkları geri ekle
                        if sheet_name == 'Challenge':
                            sheet.append_row(['ID', 'Tarih', 'Kar_Zarar', 'Kasa', 'Kalan_Gun', 'Hedef', 'Hedefe_Kalan_Tutar'])
                        elif sheet_name == 'Challenge_Settings':
                            sheet.append_row(['Baslangic_Sermaye', 'Hedef_Tutar', 'Hedef_Sure_Gun', 'Baslangic_Tarihi'])
                        elif sheet_name == 'Challenge_Trades':
                            sheet.append_row(['ID', 'Yon', 'Enstruman', 'Giris_Fiyat', 'Lot', 'Cikis_Fiyat', 'Kar_Zarar', 'Durum', 'Acilis_Tarihi', 'Kapanis_Tarihi'])
                    except:
                        pass

                st.success("✅ Challenge sıfırlandı!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Sıfırlama hatası: {e}")
