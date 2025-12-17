# Google Sheets Database Schema
## Para Komuta Merkezi - Streamlit Version

### Worksheet 1: assets
| ID | asset_type | symbol | amount | buy_price | data_source | manual_price | basket | created_at |
|----|------------|--------|--------|-----------|-------------|--------------|--------|------------|

**Columns:**
- ID: Unique identifier (number)
- asset_type: hisse, kripto, hisse_fonlari, Nakit_ve_Benzeri, emtia
- symbol: Stock symbol/crypto ticker (THYAO, BTC, etc.)
- amount: Quantity owned (decimal)
- buy_price: Purchase price in TL (decimal)
- data_source: "auto" or "manuel"
- manual_price: Manual price if data_source is manuel (decimal, default 0)
- basket: buffet, tesla, tosuncuk, or empty (for stock filtering)
- created_at: Timestamp (YYYY-MM-DD HH:MM:SS)

### Worksheet 2: debts
| ID | description | amount | created_at |
|----|-------------|--------|------------|

**Columns:**
- ID: Unique identifier (number)
- description: Debt description (text)
- amount: Debt amount in TL (decimal)
- created_at: Timestamp (YYYY-MM-DD HH:MM:SS)

### Worksheet 3: asset_history
| ID | date | total_value |
|----|------|-------------|

**Columns:**
- ID: Unique identifier (number)
- date: Date (YYYY-MM-DD)
- total_value: Total portfolio value on that date (decimal)

### Worksheet 4: debt_history
| ID | date | total_debt |
|----|------|------------|

**Columns:**
- ID: Unique identifier (number)
- date: Date (YYYY-MM-DD)
- total_debt: Total debt on that date (decimal)

### Worksheet 5: closed_positions
| ID | date | symbol | buy_price | sell_price | profit_loss_percent | created_at |
|----|------|--------|-----------|------------|---------------------|------------|

**Columns:**
- ID: Unique identifier (number)
- date: Closing date (YYYY-MM-DD)
- symbol: Asset symbol (text)
- buy_price: Purchase price (decimal)
- sell_price: Sale price (decimal)
- profit_loss_percent: Calculated profit/loss % (decimal)
- created_at: Timestamp (YYYY-MM-DD HH:MM:SS)

### Worksheet 6: settings
| key | value |
|-----|-------|

**Columns:**
- key: Setting key (text)
- value: Setting value (text)

## Notes:
- All worksheets will be created in the existing "PKM Database" spreadsheet
- The existing "portfoy_assets" worksheet will be renamed to "assets"
- Data types will be enforced through validation where possible
- Timestamps will use Turkey timezone (UTC+3)
