"""
Mevcut tecrübeleri siler (onay gerektirmez)
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys

# Windows için UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def clear_experiences():
    """Google Sheets'teki tüm tecrübeleri siler"""

    # Google Sheets bağlantısı
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open('PKM Database')
    sheet = spreadsheet.worksheet('Gorsel_Tecrubeler')

    print("Google Sheets'e bağlanıldı...")

    # Mevcut tüm verileri al
    all_data = sheet.get_all_values()

    if len(all_data) > 1:
        # Header hariç tüm satırları sil (sondan başa doğru)
        total_rows = len(all_data)
        print(f"\n{total_rows - 1} kayıt siliniyor...")

        # 2. satırdan sonuna kadar sil
        sheet.delete_rows(2, total_rows)

        print(f"✅ {total_rows - 1} kayıt silindi!")
    else:
        print("ℹ️  Zaten boş, silinecek kayıt yok")

    print("\n" + "="*60)
    print("✅ Google Sheets temizlendi!")
    print("="*60)

if __name__ == "__main__":
    print("🗑️  Mevcut Tecrübeler Siliniyor...")
    print("="*60)
    clear_experiences()
