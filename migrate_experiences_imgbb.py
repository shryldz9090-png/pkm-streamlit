"""
Trade Journal SQLite veritabanındaki görsel tecrübeleri Google Sheets'e aktarır
Görselleri imgbb.com'a yükler ve URL'lerini saklar
"""

import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import sys
import os
from imgbb_utils import upload_image_to_imgbb

# Windows için UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def migrate_experiences_with_imgbb():
    """SQLite'taki experiences tablosunu Google Sheets'e aktarır (imgbb ile)"""

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

        # Görseli imgbb'ye yükle
        image_path = exp_dict.get('image_path', '')
        image_url = ''

        if image_path:
            print(f"\n📷 Görsel yükleniyor: {image_path}")

            # Tam yolu oluştur
            base_path = r"C:\Users\LENOVO\Desktop\PKM YENİ BAŞTAN\PKM WEB PORTAL"
            full_path = os.path.join(base_path, image_path)

            if os.path.exists(full_path):
                # Dosya adı oluştur
                filename = f"exp_{exp_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # imgbb'ye yükle
                result = upload_image_to_imgbb(full_path, filename, is_path=True)

                if result:
                    image_url = result['url']  # Direkt görüntü URL'i
                    print(f"   ✅ Yüksek kaliteli görsel yüklendi! (1920x1440 @ 90%)")
                else:
                    print(f"   ⚠️  Görsel yüklenemedi, boş bırakılıyor")
            else:
                print(f"   ⚠️  Görsel dosyası bulunamadı: {full_path}")
        else:
            print(f"   ℹ️  Görsel yok")

        # Google Sheets formatına çevir
        # Google Sheets kolonları: ID, Başlık, Kategori, Not, Görsel URL, Zarar Miktarı, Oluşturma Tarihi, Timestamp

        row_data = [
            exp_dict.get('id', ''),
            exp_dict.get('title', ''),
            exp_dict.get('category', ''),
            exp_dict.get('note', ''),
            image_url,  # imgbb URL (yüksek kalite!)
            float(exp_dict.get('loss_amount', 0)) if exp_dict.get('loss_amount') else '',
            exp_dict.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            exp_dict.get('created_at', datetime.now().isoformat())
        ]

        try:
            sheet.append_row(row_data)
            migrated_count += 1
            print(f"✅ {migrated_count}. Tecrübe aktarıldı: {exp_dict.get('title', 'Başlıksız')}")
        except Exception as e:
            print(f"❌ Tecrübe aktarılamadı (ID: {exp_id}): {e}")

    conn.close()

    print("\n" + "="*60)
    print(f"✅ Migration tamamlandı!")
    print(f"   Aktarılan: {migrated_count}")
    print(f"   Atlanan (zaten mevcut): {skipped_count}")
    print(f"   Toplam: {len(experiences)}")
    print("="*60)
    print("\n📸 Görseller artık YÜKSEK KALİTEDE imgbb'de saklanıyor!")
    print("   Boyut: 1920x1440 @ 90% JPEG kalitesi")

if __name__ == "__main__":
    print("🔄 Trade Journal → Google Sheets + imgbb Migration Başlıyor...")
    print("="*60)
    migrate_experiences_with_imgbb()
