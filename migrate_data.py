"""
Migrate data from SQLite (old Flask app) to Google Sheets
"""

import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys
import io
import time

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Paths
OLD_DB_PATH = r"C:\Users\LENOVO\Desktop\PKM YENİ BAŞTAN\ESKİ PORTFÖY KOMUTA MERKEZİ PROJESİ\portfoy.db"

def migrate():
    """Migrate all data from SQLite to Google Sheets."""

    print("🔄 Starting data migration...")

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

        # Clear existing data (keep headers)
        assets_sheet.clear()
        assets_sheet.append_row(["ID", "asset_type", "symbol", "amount", "buy_price", "data_source", "manual_price", "basket", "created_at"])

        for asset in assets:
            # Try to get basket, default to empty string if column doesn't exist
            try:
                basket = asset['basket'] if asset['basket'] else ''
            except (KeyError, IndexError):
                basket = ''

            row = [
                asset['id'],
                asset['asset_type'],
                asset['symbol'],
                asset['amount'],
                asset['buy_price'],
                asset['data_source'],
                asset['manual_price'] or 0,
                basket,
                asset['created_at']
            ]
            assets_sheet.append_row(row)
            time.sleep(0.5)  # Avoid rate limit

        print(f"✅ Migrated {len(assets)} assets")

    # Migrate debts
    print("\n💳 Migrating debts...")
    cursor.execute("SELECT * FROM debts ORDER BY id")
    debts = cursor.fetchall()

    if debts:
        debts_sheet = db.worksheet("debts")
        debts_sheet.clear()
        debts_sheet.append_row(["ID", "description", "amount", "created_at"])

        for debt in debts:
            row = [
                debt['id'],
                debt['description'],
                debt['amount'],
                debt['created_at']
            ]
            debts_sheet.append_row(row)
            time.sleep(0.5)  # Avoid rate limit

        print(f"✅ Migrated {len(debts)} debts")

    # Migrate asset history
    print("\n📈 Migrating asset history...")
    cursor.execute("SELECT * FROM asset_history ORDER BY date")
    history = cursor.fetchall()

    if history:
        history_sheet = db.worksheet("asset_history")
        history_sheet.clear()
        history_sheet.append_row(["ID", "date", "total_value"])

        for idx, record in enumerate(history, 1):
            row = [
                idx,
                record['date'],
                record['total_value']
            ]
            history_sheet.append_row(row)
            time.sleep(0.5)  # Avoid rate limit

        print(f"✅ Migrated {len(history)} history records")

    # Migrate debt history
    print("\n💰 Migrating debt history...")
    cursor.execute("SELECT * FROM debt_history ORDER BY date")
    debt_hist = cursor.fetchall()

    if debt_hist:
        debt_hist_sheet = db.worksheet("debt_history")
        debt_hist_sheet.clear()
        debt_hist_sheet.append_row(["ID", "date", "total_debt"])

        for idx, record in enumerate(debt_hist, 1):
            row = [
                idx,
                record['date'],
                record['total_debt']
            ]
            debt_hist_sheet.append_row(row)
            time.sleep(0.5)  # Avoid rate limit

        print(f"✅ Migrated {len(debt_hist)} debt history records")

    # Migrate closed positions
    print("\n🔒 Migrating closed positions...")
    cursor.execute("SELECT * FROM closed_positions ORDER BY date")
    closed = cursor.fetchall()

    if closed:
        closed_sheet = db.worksheet("closed_positions")
        closed_sheet.clear()
        closed_sheet.append_row(["ID", "date", "symbol", "buy_price", "sell_price", "profit_loss_percent", "created_at"])

        for pos in closed:
            row = [
                pos['id'],
                pos['date'],
                pos['symbol'],
                pos['buy_price'],
                pos['sell_price'],
                pos['profit_loss_percent'],
                pos['created_at']
            ]
            closed_sheet.append_row(row)
            time.sleep(0.5)  # Avoid rate limit

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
