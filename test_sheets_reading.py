"""
Test script to debug how Google Sheets returns decimal values
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_reading():
    """Test how gspread reads decimal values from Google Sheets."""

    print("🔍 Testing Google Sheets data reading...\n")

    # Connect to Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    db = client.open("PKM Database")

    # Get assets worksheet
    assets_sheet = db.worksheet("assets")

    # Method 1: get_all_records() - What app currently uses
    print("=" * 60)
    print("METHOD 1: get_all_records()")
    print("=" * 60)
    records = assets_sheet.get_all_records()

    # Find FONET record
    fonet_record = None
    for record in records:
        if record.get('symbol') == 'FONET':
            fonet_record = record
            break

    if fonet_record:
        print(f"\nFONET record found:")
        print(f"  symbol: {fonet_record['symbol']}")
        print(f"  buy_price: {fonet_record['buy_price']}")
        print(f"  buy_price type: {type(fonet_record['buy_price'])}")
        print(f"  buy_price repr: {repr(fonet_record['buy_price'])}")
        print(f"  amount: {fonet_record['amount']}")
        print(f"  amount type: {type(fonet_record['amount'])}")

    # Method 2: get_all_values() - Raw cell values
    print("\n" + "=" * 60)
    print("METHOD 2: get_all_values() - Raw values")
    print("=" * 60)
    all_values = assets_sheet.get_all_values()

    # Find FONET in raw values
    headers = all_values[0]
    print(f"\nHeaders: {headers}")

    for row in all_values[1:]:  # Skip header
        if len(row) > 2 and row[2] == 'FONET':  # symbol column
            print(f"\nFONET raw row:")
            for i, (header, value) in enumerate(zip(headers, row)):
                print(f"  {header}: {repr(value)} (type: {type(value).__name__})")
            break

    # Method 3: Direct cell access to E62 (FONET buy_price from screenshot)
    print("\n" + "=" * 60)
    print("METHOD 3: Direct cell E62 access")
    print("=" * 60)

    # Find which row has FONET
    symbol_col = assets_sheet.col_values(3)  # Column C (symbol)
    try:
        fonet_row = symbol_col.index('FONET') + 1  # +1 because sheets are 1-indexed
        print(f"\nFONET found at row: {fonet_row}")

        # Get buy_price from column E
        buy_price_cell = assets_sheet.cell(fonet_row, 5)  # Column E
        print(f"Cell E{fonet_row} value: {repr(buy_price_cell.value)}")
        print(f"Cell E{fonet_row} value type: {type(buy_price_cell.value)}")
    except ValueError:
        print("\nFONET not found in symbol column")

    # Show first 5 records for comparison
    print("\n" + "=" * 60)
    print("FIRST 5 RECORDS (for comparison)")
    print("=" * 60)
    for i, record in enumerate(records[:5], 1):
        print(f"\n{i}. {record.get('symbol', 'NO SYMBOL')}")
        print(f"   buy_price: {record.get('buy_price')} (type: {type(record.get('buy_price'))})")
        print(f"   amount: {record.get('amount')} (type: {type(record.get('amount'))})")

if __name__ == "__main__":
    test_reading()
