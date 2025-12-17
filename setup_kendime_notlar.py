"""
Kendime Notlar için Google Sheets tablosu oluşturur
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys

# Windows için UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def setup_kendime_notlar():
    """Kendime Notlar tablosu oluşturur"""

    # Google Sheets bağlantısı
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open('PKM Database')

    print("PKM Database bulundu!")

    # Kendime_Notlar tablosu var mı kontrol et
    try:
        sheet = spreadsheet.worksheet('Kendime_Notlar')
        print("Kendime_Notlar tablosu zaten mevcut!")
    except:
        print("Kendime_Notlar tablosu olusturuluyor...")
        sheet = spreadsheet.add_worksheet(title='Kendime_Notlar', rows=500, cols=8)

        # Header ekle
        sheet.append_row([
            'ID',
            'Başlık',
            'Kategori',
            'İçerik',
            'Görsel URL',
            'Oluşturma Tarihi',
            'Timestamp'
        ])

        print("Kendime_Notlar tablosu olusturuldu!")

    print("\n" + "="*60)
    print("Basariyla tamamlandi!")
    print("="*60)

if __name__ == "__main__":
    print("Kendime Notlar Tablosu Olusturuluyor...")
    print("="*60)
    setup_kendime_notlar()
