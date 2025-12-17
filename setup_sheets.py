"""
Setup Google Sheets Database Structure
Creates all necessary worksheets with proper headers
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def setup_sheets():
    """Creates all worksheets needed for the portfolio app."""

    # Connect to Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    # Open the database
    db = client.open("PKM Database")

    print("Setting up Google Sheets database structure...")

    # 1. Assets worksheet (rename existing portfoy_assets)
    try:
        assets_sheet = db.worksheet("portfoy_assets")
        print("✓ Found existing 'portfoy_assets' worksheet")
    except:
        assets_sheet = db.add_worksheet(title="assets", rows=1000, cols=9)
        print("✓ Created 'assets' worksheet")

    # Set headers for assets
    assets_headers = ["ID", "asset_type", "symbol", "amount", "buy_price", "data_source", "manual_price", "basket", "created_at"]
    assets_sheet.update('A1:I1', [assets_headers])
    print("✓ Set headers for 'assets' worksheet")

    # 2. Debts worksheet
    try:
        debts_sheet = db.worksheet("debts")
        print("✓ Found existing 'debts' worksheet")
    except:
        debts_sheet = db.add_worksheet(title="debts", rows=500, cols=4)
        debts_headers = ["ID", "description", "amount", "created_at"]
        debts_sheet.update('A1:D1', [debts_headers])
        print("✓ Created 'debts' worksheet")

    # 3. Asset History worksheet
    try:
        history_sheet = db.worksheet("asset_history")
        print("✓ Found existing 'asset_history' worksheet")
    except:
        history_sheet = db.add_worksheet(title="asset_history", rows=1000, cols=3)
        history_headers = ["ID", "date", "total_value"]
        history_sheet.update('A1:C1', [history_headers])
        print("✓ Created 'asset_history' worksheet")

    # 4. Debt History worksheet
    try:
        debt_history_sheet = db.worksheet("debt_history")
        print("✓ Found existing 'debt_history' worksheet")
    except:
        debt_history_sheet = db.add_worksheet(title="debt_history", rows=1000, cols=3)
        debt_history_headers = ["ID", "date", "total_debt"]
        debt_history_sheet.update('A1:C1', [debt_history_headers])
        print("✓ Created 'debt_history' worksheet")

    # 5. Closed Positions worksheet
    try:
        closed_sheet = db.worksheet("closed_positions")
        print("✓ Found existing 'closed_positions' worksheet")
    except:
        closed_sheet = db.add_worksheet(title="closed_positions", rows=1000, cols=7)
        closed_headers = ["ID", "date", "symbol", "buy_price", "sell_price", "profit_loss_percent", "created_at"]
        closed_sheet.update('A1:G1', [closed_headers])
        print("✓ Created 'closed_positions' worksheet")

    # 6. Settings worksheet
    try:
        settings_sheet = db.worksheet("settings")
        print("✓ Found existing 'settings' worksheet")
    except:
        settings_sheet = db.add_worksheet(title="settings", rows=100, cols=2)
        settings_headers = ["key", "value"]
        settings_sheet.update('A1:B1', [settings_headers])
        print("✓ Created 'settings' worksheet")

    print("\n✅ All worksheets created successfully!")
    print("\nWorksheet list:")
    for sheet in db.worksheets():
        print(f"  - {sheet.title}")

if __name__ == "__main__":
    setup_sheets()
