"""
Trade Journal SQLite veritabanındaki görsel tecrübeleri Google Sheets'e aktarır
Görselleri dosyadan okuyup Base64'e çevirir ve optimize eder
"""

import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import sys
import os
from PIL import Image
import io
import base64

# Windows için UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def optimize_and_encode_image_from_file(image_path):
    """
    Dosyadan resmi okur, optimize eder ve Base64'e çevirir
    - 800x600 boyutuna küçült
    - JPEG kalite 80%
    - Base64 string döndür
    """
    try:
        # Tam yolu oluştur
        base_path = r"C:\Users\LENOVO\Desktop\PKM YENİ BAŞTAN\PKM WEB PORTAL"
        full_path = os.path.join(base_path, image_path)

        if not os.path.exists(full_path):
            print(f"⚠️  Görsel dosyası bulunamadı: {full_path}")
            return None

        # Görüntüyü aç
        image = Image.open(full_path)

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
        print(f"⚠️  Görsel işlenirken hata: {e}")
        return None

def migrate_experiences():
    """SQLite'taki experiences tablosunu Google Sheets'e aktarır"""

    # SQLite bağlantısı
    db_path = r"C:\Users\LENOVO\Desktop\PKM YENİ BAŞTAN\PKM WEB PORTAL\databases\trade_journal.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("SQLite veritabanına bağlanıldı...")

    # Experiences tablosunu oku
    try:
        cursor.execute("SELECT * FROM experiences")
        experiences = cursor.fetchall()

        # Kolon isimlerini al
        cursor.execute("PRAGMA table_info(experiences)")
        columns = [col[1] for col in cursor.fetchall()]

        print(f"Toplam {len(experiences)} tecrübe bulundu")
        print(f"Kolonlar: {', '.join(columns)}")

    except Exception as e:
        print(f"❌ SQLite'tan veri okunamadı: {e}")
        conn.close()
        return

    # Google Sheets bağlantısı
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open('PKM Database')
        sheet = spreadsheet.worksheet('Gorsel_Tecrubeler')

        print("Google Sheets'e bağlanıldı...")

    except Exception as e:
        print(f"❌ Google Sheets'e bağlanılamadı: {e}")
        conn.close()
        return

    # Mevcut ID'leri al (duplicate önlemek için)
    existing_data = sheet.get_all_values()
    existing_ids = set()
    if len(existing_data) > 1:
        for row in existing_data[1:]:
            if row and row[0]:
                try:
                    existing_ids.add(int(row[0]))
                except:
                    pass

    print(f"Google Sheets'te {len(existing_ids)} mevcut kayıt var")

    # Her bir experience'i aktar
    migrated_count = 0
    skipped_count = 0

    for exp in experiences:
        # Dictionary'e çevir
        exp_dict = dict(zip(columns, exp))

        # ID kontrolü
        exp_id = exp_dict.get('id')
        if exp_id in existing_ids:
            print(f"⏭️  ID {exp_id} zaten mevcut, atlanıyor...")
            skipped_count += 1
            continue

        # Görseli Base64'e çevir
        image_path = exp_dict.get('image_path', '')
        image_base64 = ''

        if image_path:
            print(f"   📷 Görsel işleniyor: {image_path}")
            image_base64 = optimize_and_encode_image_from_file(image_path)
            if image_base64:
                print(f"   ✅ Görsel Base64'e çevrildi (~{len(image_base64) / 1024:.1f} KB)")
            else:
                print(f"   ⚠️  Görsel işlenemedi, boş bırakılıyor")
        else:
            print(f"   ℹ️  Görsel yok")

        # Google Sheets formatına çevir
        # Google Sheets kolonları: ID, Başlık, Kategori, Not, Görsel URL, Zarar Miktarı, Oluşturma Tarihi, Timestamp

        row_data = [
            exp_dict.get('id', ''),
            exp_dict.get('title', ''),
            exp_dict.get('category', ''),
            exp_dict.get('note', ''),
            image_base64,  # Base64 encoded image
            float(exp_dict.get('loss_amount', 0)) if exp_dict.get('loss_amount') else '',
            exp_dict.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            exp_dict.get('created_at', datetime.now().isoformat())
        ]

        try:
            sheet.append_row(row_data)
            migrated_count += 1
            print(f"✅ {migrated_count}. Tecrübe aktarıldı: {exp_dict.get('title', 'Başlıksız')}\n")
        except Exception as e:
            print(f"❌ Tecrübe aktarılamadı (ID: {exp_id}): {e}\n")

    conn.close()

    print("\n" + "="*60)
    print(f"✅ Migration tamamlandı!")
    print(f"   Aktarılan: {migrated_count}")
    print(f"   Atlanan (zaten mevcut): {skipped_count}")
    print(f"   Toplam: {len(experiences)}")
    print("="*60)

if __name__ == "__main__":
    print("🔄 Trade Journal → Google Sheets Migration Başlıyor...")
    print("="*60)
    migrate_experiences()
