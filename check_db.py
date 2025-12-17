import sqlite3

db_path = r"C:\Users\LENOVO\Desktop\PKM YENİ BAŞTAN\PKM WEB PORTAL\databases\trade_journal.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Tabloları listele
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tablolar:")
for table in tables:
    print(f"  - {table[0]}")

# Experiences tablosu varsa yapısını göster
try:
    cursor.execute("PRAGMA table_info(experiences)")
    columns = cursor.fetchall()
    print("\nExperiences tablosu kolonları:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

    # Kayıt sayısı
    cursor.execute("SELECT COUNT(*) FROM experiences")
    count = cursor.fetchone()[0]
    print(f"\nToplam kayıt: {count}")

    # İlk 3 kaydı göster
    if count > 0:
        cursor.execute("SELECT * FROM experiences LIMIT 3")
        records = cursor.fetchall()
        print("\nİlk 3 kayıt:")
        for i, record in enumerate(records, 1):
            print(f"\n{i}. Kayıt:")
            for j, col in enumerate(columns):
                value = record[j]
                # Base64 string çok uzunsa kısalt
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "... (uzun string)"
                print(f"  {col[1]}: {value}")
except Exception as e:
    print(f"\nExperiences tablosu bulunamadı: {e}")

conn.close()
