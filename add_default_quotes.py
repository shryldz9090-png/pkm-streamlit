"""
Trade Asistanı için varsayılan özlü sözleri ekler
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import sys

# Windows için UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def add_default_quotes():
    """Varsayılan özlü sözleri ekler"""

    # Google Sheets bağlantısı
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open('PKM Database')

    try:
        sheet = spreadsheet.worksheet('Ozlu_Sozler')
        print("Ozlu_Sozler tablosu bulundu!")
    except:
        print("Ozlu_Sozler tablosu bulunamadi, olusturuluyor...")
        sheet = spreadsheet.add_worksheet(title='Ozlu_Sozler', rows=100, cols=6)
        sheet.append_row([
            'ID', 'Söz', 'Sıra', 'Renk', 'Oluşturma Tarihi', 'Timestamp'
        ])
        print("Ozlu_Sozler tablosu olusturuldu!")

    # Varsayılan özlü sözler
    default_quotes = [
        {
            'text': 'Sabır, trading\'de en büyük sermayedir.',
            'order': 1,
            'color': '#3b82f6'
        },
        {
            'text': 'Kayıplarını kısa kes, kazançlarını uzat.',
            'order': 2,
            'color': '#10b981'
        },
        {
            'text': 'Piyasa her zaman haklıdır, ego bırak.',
            'order': 3,
            'color': '#f59e0b'
        },
        {
            'text': 'Disiplin, kârdan daha önemlidir.',
            'order': 4,
            'color': '#8b5cf6'
        },
        {
            'text': 'Risk yönetimi, başarının anahtarıdır.',
            'order': 5,
            'color': '#ef4444'
        },
        {
            'text': 'Her kayıp bir ders, her kazanç bir imkandır.',
            'order': 6,
            'color': '#06b6d4'
        },
        {
            'text': 'Trading bir maratondur, sprint değil.',
            'order': 7,
            'color': '#ec4899'
        },
        {
            'text': 'Plan yapmadan işlem yapma!',
            'order': 8,
            'color': '#f97316'
        }
    ]

    # Mevcut ID'leri kontrol et
    all_data = sheet.get_all_values()
    existing_count = len(all_data) - 1  # Header hariç

    print(f"\nMevcut ozlu soz sayisi: {existing_count}")

    if existing_count > 0:
        print("Mevcut sozler siliniyor...")
        if existing_count > 0:
            sheet.delete_rows(2, len(all_data))
        print(f"{existing_count} soz silindi!")

    # Yeni sözleri ekle
    print("\nVarsayilan sozler ekleniyor...")
    now = datetime.now()

    for i, quote in enumerate(default_quotes, start=1):
        row = [
            i,
            quote['text'],
            quote['order'],
            quote['color'],
            now.strftime('%Y-%m-%d %H:%M:%S'),
            now.isoformat()
        ]

        sheet.append_row(row)
        print(f"  {i}. \"{quote['text']}\" ({quote['color']})")

    print("\n" + "="*60)
    print(f"Basariyla {len(default_quotes)} varsayilan ozlu soz eklendi!")
    print("="*60)

if __name__ == "__main__":
    print("Varsayilan Ozlu Sozler Ekleniyor...")
    print("="*60)
    add_default_quotes()
