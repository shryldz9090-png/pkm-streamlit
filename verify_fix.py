"""
Quick verification that decimal parsing is now working correctly
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def parse_turkish_decimal(value):
    """Parse Turkish decimal format (comma as decimal separator) to float."""
    if value is None or value == '':
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.strip().replace(' TL', '').replace('TL', '').strip()
        value = value.replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0

def get_sheet_data_as_dict(worksheet):
    """Get worksheet data as list of dictionaries with proper Turkish decimal handling."""
    all_values = worksheet.get_all_values()

    if not all_values or len(all_values) < 2:
        return []

    headers = all_values[0]
    records = []

    for row in all_values[1:]:
        if not any(row):
            continue

        record = {}
        for i, header in enumerate(headers):
            if i < len(row):
                value = row[i]

                if header in ['amount', 'buy_price', 'manual_price', 'total_value', 'total_debt',
                              'sell_price', 'profit_loss_percent']:
                    record[header] = parse_turkish_decimal(value)
                elif header == 'ID':
                    try:
                        record[header] = int(value) if value else 0
                    except ValueError:
                        record[header] = 0
                else:
                    record[header] = str(value)
            else:
                record[header] = ''

        records.append(record)

    return records

def verify():
    """Verify the decimal parsing is working correctly."""

    print("🔍 Verifying Turkish decimal parsing fix...\n")

    # Connect to Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    db = client.open("PKM Database")

    # Get assets
    assets_sheet = db.worksheet("assets")
    assets_data = get_sheet_data_as_dict(assets_sheet)

    # Find FONET
    fonet = None
    for asset in assets_data:
        if asset.get('symbol') == 'FONET':
            fonet = asset
            break

    if fonet:
        print("✅ FONET asset found!")
        print(f"   Symbol: {fonet['symbol']}")
        print(f"   Buy Price: {fonet['buy_price']} TL")
        print(f"   Amount: {fonet['amount']}")
        print(f"   Manual Price: {fonet['manual_price']} TL")
        print(f"   Data Source: {fonet['data_source']}")

        # Calculate value
        price = fonet['manual_price'] if fonet['data_source'] == 'manuel' else fonet['buy_price']
        value = fonet['amount'] * price
        print(f"   Value: {value:,.2f} TL")

        # Check if correct
        if fonet['buy_price'] == 16.23:
            print("\n✅ SUCCESS! Buy price is correct: 16.23 TL")
        else:
            print(f"\n❌ ERROR! Buy price should be 16.23, but got: {fonet['buy_price']}")
    else:
        print("❌ FONET asset not found!")

    # Calculate total portfolio value
    print("\n" + "="*60)
    print("PORTFOLIO TOTALS")
    print("="*60)

    total = 0
    for asset in assets_data:
        price = asset['manual_price'] if asset['data_source'] == 'manuel' else asset['buy_price']
        value = asset['amount'] * price
        total += value

    print(f"Total Assets Value: ₺{total:,.2f}")
    print(f"\nExpected: ~₺7,647,630")
    print(f"Actual:   ₺{total:,.2f}")

    if 7_500_000 < total < 8_000_000:
        print("\n✅✅✅ SUCCESS! Portfolio value is in expected range!")
    else:
        print("\n❌ WARNING: Portfolio value seems incorrect")

if __name__ == "__main__":
    verify()
