import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import sys

# Windows için UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Google Sheets API bağlantısı
def setup_sheets():
    """Trade Asistanı için Google Sheets tablolarını oluşturur"""

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)

    # Ana spreadsheet'i aç (Portföy ile aynı)
    spreadsheet = client.open('PKM Database')
    print("Mevcut spreadsheet bulundu: PKM Database")

    # 1. POZISYONLAR TABLOSU
    try:
        positions_sheet = spreadsheet.worksheet('Pozisyonlar')
        print("✓ Pozisyonlar sayfası zaten mevcut")
    except:
        positions_sheet = spreadsheet.add_worksheet(title='Pozisyonlar', rows=1000, cols=15)
        positions_sheet.append_row([
            'ID', 'Pozisyon Tipi', 'Giriş Fiyatı', 'Lot Büyüklüğü',
            'Stop Loss', 'Take Profit', 'Plan Notu', 'Durum',
            'Sonuç', 'Öğrenilen Ders', 'Açılış Tarihi', 'Kapanış Tarihi',
            'Çıkış Fiyatı', 'Piyasa', 'Timestamp'
        ])
        print("✓ Pozisyonlar sayfası oluşturuldu")

    # 2. GÖRSEL TECRÜBELER TABLOSU
    try:
        experiences_sheet = spreadsheet.worksheet('Gorsel_Tecrubeler')
        print("✓ Görsel Tecrübeler sayfası zaten mevcut")
    except:
        experiences_sheet = spreadsheet.add_worksheet(title='Gorsel_Tecrubeler', rows=1000, cols=10)
        experiences_sheet.append_row([
            'ID', 'Başlık', 'Kategori', 'Not', 'Görsel URL',
            'Zarar Miktarı', 'Oluşturma Tarihi', 'Timestamp'
        ])
        print("✓ Görsel Tecrübeler sayfası oluşturuldu")

    # 3. KATEGORİLER TABLOSU
    try:
        categories_sheet = spreadsheet.worksheet('Kategoriler')
        print("✓ Kategoriler sayfası zaten mevcut")
    except:
        categories_sheet = spreadsheet.add_worksheet(title='Kategoriler', rows=100, cols=5)
        categories_sheet.append_row([
            'ID', 'Kategori Adı', 'Varsayılan mı?', 'Oluşturma Tarihi', 'Timestamp'
        ])
        # Varsayılan kategorileri ekle
        default_categories = [
            "RSI Hatası", "WT-Cross Hatası", "Erken Giriş", "Geç Giriş",
            "Kaçırdığım Short", "Başarılı İşlem", "Diğer", "Kategorisiz"
        ]
        for i, cat in enumerate(default_categories, start=1):
            categories_sheet.append_row([
                str(i), cat, 'EVET', datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().isoformat()
            ])
        print("✓ Kategoriler sayfası oluşturuldu ve varsayılan kategoriler eklendi")

    # 4. CHECKLIST LOGS TABLOSU
    try:
        checklist_sheet = spreadsheet.worksheet('Checklist_Logs')
        print("✓ Checklist Logs sayfası zaten mevcut")
    except:
        checklist_sheet = spreadsheet.add_worksheet(title='Checklist_Logs', rows=1000, cols=10)
        checklist_sheet.append_row([
            'ID', 'RSI Kontrol', 'WT-Cross Kontrol', 'EMA Kontrol',
            'Duygusal Kontrol', 'Geçti mi?', 'Uyarılar', 'Oluşturma Tarihi', 'Timestamp'
        ])
        print("✓ Checklist Logs sayfası oluşturuldu")

    # 5. CHALLENGE (Meydan Okuma) TABLOSU
    try:
        challenge_sheet = spreadsheet.worksheet('Challenges')
        print("✓ Challenges sayfası zaten mevcut")
    except:
        challenge_sheet = spreadsheet.add_worksheet(title='Challenges', rows=100, cols=8)
        challenge_sheet.append_row([
            'ID', 'Başlangıç Sermaye', 'Güncel Kasa', 'Durum',
            'Başlangıç Tarihi', 'Bitiş Tarihi', 'Timestamp'
        ])
        print("✓ Challenges sayfası oluşturuldu")

    # 6. KASA GEÇMİŞİ TABLOSU (Challenge grafiği için)
    try:
        kasa_sheet = spreadsheet.worksheet('Kasa_Gecmisi')
        print("✓ Kasa Geçmişi sayfası zaten mevcut")
    except:
        kasa_sheet = spreadsheet.add_worksheet(title='Kasa_Gecmisi', rows=1000, cols=10)
        kasa_sheet.append_row([
            'ID', 'Challenge ID', 'Position ID', 'Kasa Öncesi',
            'Kasa Sonrası', 'Değişim', 'İşlem Tipi', 'Kayıt Tarihi', 'Timestamp'
        ])
        print("✓ Kasa Geçmişi sayfası oluşturuldu")

    # 7. KENDİME NOTLAR TABLOSU
    try:
        notlar_sheet = spreadsheet.worksheet('Kendime_Notlar')
        print("✓ Kendime Notlar sayfası zaten mevcut")
    except:
        notlar_sheet = spreadsheet.add_worksheet(title='Kendime_Notlar', rows=1000, cols=8)
        notlar_sheet.append_row([
            'ID', 'Başlık', 'Kategori', 'İçerik', 'Görsel URL',
            'Oluşturma Tarihi', 'Timestamp'
        ])
        print("✓ Kendime Notlar sayfası oluşturuldu")

    # 8. ÖZLÜ SÖZLER TABLOSU
    try:
        quotes_sheet = spreadsheet.worksheet('Ozlu_Sozler')
        print("✓ Özlü Sözler sayfası zaten mevcut")
    except:
        quotes_sheet = spreadsheet.add_worksheet(title='Ozlu_Sozler', rows=100, cols=6)
        quotes_sheet.append_row([
            'ID', 'Söz', 'Sıra', 'Renk', 'Oluşturma Tarihi', 'Timestamp'
        ])
        print("✓ Özlü Sözler sayfası oluşturuldu")

    # 9. STRATEJİLER TABLOSU
    try:
        strategies_sheet = spreadsheet.worksheet('Stratejiler')
        print("✓ Stratejiler sayfası zaten mevcut")
    except:
        strategies_sheet = spreadsheet.add_worksheet(title='Stratejiler', rows=100, cols=6)
        strategies_sheet.append_row([
            'ID', 'Strateji Adı', 'Tip', 'Oluşturma Tarihi', 'Timestamp'
        ])
        print("✓ Stratejiler sayfası oluşturuldu")

    # 10. STRATEJİ KURALLARI TABLOSU
    try:
        strategy_rules_sheet = spreadsheet.worksheet('Strateji_Kurallari')
        print("✓ Strateji Kuralları sayfası zaten mevcut")
    except:
        strategy_rules_sheet = spreadsheet.add_worksheet(title='Strateji_Kurallari', rows=500, cols=6)
        strategy_rules_sheet.append_row([
            'ID', 'Strateji ID', 'Kural Metni', 'Sıra', 'Timestamp'
        ])
        print("✓ Strateji Kuralları sayfası oluşturuldu")

    # 11. İŞLEM KONTROLLERİ TABLOSU
    try:
        checks_sheet = spreadsheet.worksheet('Islem_Kontrolleri')
        print("✓ İşlem Kontrolleri sayfası zaten mevcut")
    except:
        checks_sheet = spreadsheet.add_worksheet(title='Islem_Kontrolleri', rows=100, cols=7)
        checks_sheet.append_row([
            'ID', 'Kontrol Adı', 'Kontrol Tipi', 'Sıra',
            'Aktif mi?', 'Oluşturma Tarihi', 'Timestamp'
        ])
        print("✓ İşlem Kontrolleri sayfası oluşturuldu")

    print("\n" + "="*60)
    print("✅ Trade Asistanı Google Sheets tabloları başarıyla oluşturuldu!")
    print("="*60)
    print(f"\nSpreadsheet URL: {spreadsheet.url}")
    print("\nOluşturulan Tablolar:")
    print("  1. Pozisyonlar - LONG/SHORT pozisyon takibi")
    print("  2. Görsel Tecrübeler - Hatalı işlemlerden görsel ders çıkarma")
    print("  3. Kategoriler - Tecrübe kategorileri")
    print("  4. Checklist Logs - İşlem öncesi kontrol kayıtları")
    print("  5. Challenges - Meydan okuma takibi")
    print("  6. Kasa Geçmişi - Challenge grafik verisi")
    print("  7. Kendime Notlar - Kişisel notlar")
    print("  8. Özlü Sözler - Motivasyon sözleri")
    print("  9. Stratejiler - Trading stratejileri")
    print(" 10. Strateji Kuralları - Strateji detayları")
    print(" 11. İşlem Kontrolleri - Özelleştirilebilir checkler")

    return spreadsheet

if __name__ == "__main__":
    setup_sheets()
