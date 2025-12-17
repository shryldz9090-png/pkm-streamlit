"""
Migrate data from SQLite (old Flask app) to Google Sheets - BATCH VERSION
Much faster - uses batch updates instead of row-by-row
"""

import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Paths
OLD_DB_PATH = r"C:\Users\LENOVO\Desktop\PKM YENİ BAŞTAN\ESKİ PORTFÖY KOMUTA MERKEZİ PROJESİ\portfoy.db"

def migrate():
    """Migrate all data from SQLite to Google Sheets using batch updates."""

    print("🔄 Starting BATCH data migration...")

    # Connect to SQLite
    conn = sqlite3.connect(OLD_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Connect to Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    db = client.open("PKM Database")

    # Migrate assets
    print("\n📊 Migrating assets...")
    cursor.execute("SELECT * FROM assets ORDER BY id")
    assets = cursor.fetchall()

    if assets:
        assets_sheet = db.worksheet("assets")
        assets_sheet.clear()

        # Prepare all rows
        headers = ["ID", "asset_type", "symbol", "amount", "buy_price", "data_source", "manual_price", "basket", "created_at"]
        rows = [headers]

        for asset in assets:
            try:
                basket = asset['basket'] if asset['basket'] else ''
            except (KeyError, IndexError):
                basket = ''

            # IMPORTANT: Convert numbers to floats to prevent Google Sheets locale issues
            row = [
                int(asset['id']),
                str(asset['asset_type']),
                str(asset['symbol']),
                float(asset['amount']),
                float(asset['buy_price']),
                str(asset['data_source']),
                float(asset['manual_price'] or 0),
                str(basket),
                str(asset['created_at'])
            ]
            rows.append(row)

        # Batch update with RAW value input option to prevent Google Sheets auto-formatting
        assets_sheet.update('A1', rows, value_input_option='RAW')
        print(f"✅ Migrated {len(assets)} assets")

    # Migrate debts
    print("\n💳 Migrating debts...")
    cursor.execute("SELECT * FROM debts ORDER BY id")
    debts = cursor.fetchall()

    if debts:
        debts_sheet = db.worksheet("debts")
        debts_sheet.clear()

        headers = ["ID", "description", "amount", "created_at"]
        rows = [headers]

        for debt in debts:
            row = [
                int(debt['id']),
                str(debt['description']),
                float(debt['amount']),
                str(debt['created_at'])
            ]
            rows.append(row)

        debts_sheet.update('A1', rows, value_input_option='RAW')
        print(f"✅ Migrated {len(debts)} debts")

    # Migrate asset history
    print("\n📈 Migrating asset history...")
    cursor.execute("SELECT * FROM asset_history ORDER BY date")
    history = cursor.fetchall()

    if history:
        history_sheet = db.worksheet("asset_history")
        history_sheet.clear()

        headers = ["ID", "date", "total_value"]
        rows = [headers]

        for idx, record in enumerate(history, 1):
            row = [
                int(idx),
                str(record['date']),
                float(record['total_value'])
            ]
            rows.append(row)

        history_sheet.update('A1', rows, value_input_option='RAW')
        print(f"✅ Migrated {len(history)} history records")

    # Migrate debt history
    print("\n💰 Migrating debt history...")
    cursor.execute("SELECT * FROM debt_history ORDER BY date")
    debt_hist = cursor.fetchall()

    if debt_hist:
        debt_hist_sheet = db.worksheet("debt_history")
        debt_hist_sheet.clear()

        headers = ["ID", "date", "total_debt"]
        rows = [headers]

        for idx, record in enumerate(debt_hist, 1):
            row = [
                int(idx),
                str(record['date']),
                float(record['total_debt'])
            ]
            rows.append(row)

        debt_hist_sheet.update('A1', rows, value_input_option='RAW')
        print(f"✅ Migrated {len(debt_hist)} debt history records")

    # Migrate closed positions
    print("\n🔒 Migrating closed positions...")
    cursor.execute("SELECT * FROM closed_positions ORDER BY date")
    closed = cursor.fetchall()

    if closed:
        closed_sheet = db.worksheet("closed_positions")
        closed_sheet.clear()

        headers = ["ID", "date", "symbol", "buy_price", "sell_price", "profit_loss_percent", "created_at"]
        rows = [headers]

        for pos in closed:
            row = [
                int(pos['id']),
                str(pos['date']),
                str(pos['symbol']),
                float(pos['buy_price']),
                float(pos['sell_price']),
                float(pos['profit_loss_percent']),
                str(pos['created_at'])
            ]
            rows.append(row)

        closed_sheet.update('A1', rows, value_input_option='RAW')
        print(f"✅ Migrated {len(closed)} closed positions")

    conn.close()

    print("\n🎉 Migration completed successfully!")
    print(f"   - {len(assets)} assets")
    print(f"   - {len(debts)} debts")
    print(f"   - {len(history)} asset history records")
    print(f"   - {len(debt_hist)} debt history records")
    print(f"   - {len(closed)} closed positions")

if __name__ == "__main__":
    migrate()
