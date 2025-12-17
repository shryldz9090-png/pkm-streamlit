import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Para Komuta Merkezi", page_icon="💰", layout="wide")

@st.cache_resource
def get_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    return client.open("PKM Database")

def main():
    st.title("💰 Para Komuta Merkezi")
    st.subheader("Portföy Yönetim Platformu")
    
    try:
        db = get_sheets()
        sheet = db.worksheet("portfoy_assets")
        st.success("✅ Google Sheets'e başarıyla bağlandı!")
        
        data = sheet.get_all_records()
        
        with st.sidebar:
            st.header("📋 Menü")
            sayfa = st.selectbox("Sayfa Seç", ["Ana Sayfa", "Portföy Görüntüle", "Yeni Varlık Ekle"])
        
        if sayfa == "Ana Sayfa":
            show_home(data)
        elif sayfa == "Portföy Görüntüle":
            show_portfolio(data)
        else:
            show_add_asset(sheet, data)
    except Exception as e:
        st.error(f"❌ Hata oluştu: {str(e)}")

def show_home(data):
    st.header("🏠 Ana Sayfa")
    if data:
        df = pd.DataFrame(data)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Toplam Varlık", len(data))
        with col2:
            if "Quantity" in df.columns and "Buy_Price" in df.columns:
                total = (df["Quantity"] * df["Buy_Price"]).sum()
                st.metric("Toplam Değer", f"₺{total:,.2f}")
        with col3:
            if "Asset_Type" in df.columns:
                st.metric("Varlık Türü", df["Asset_Type"].nunique())
        st.divider()
        st.subheader("Son Eklenen Varlıklar")
        st.dataframe(df.tail(5), use_container_width=True)
    else:
        st.info("📭 Henüz varlık eklenmemiş")

def show_portfolio(data):
    st.header("📊 Portföy Komuta Merkezi")
    if data:
        df = pd.DataFrame(data)
        if "Asset_Type" in df.columns:
            asset_types = ["Tümü"] + list(df["Asset_Type"].unique())
            selected_type = st.selectbox("Varlık Türü Filtrele", asset_types)
            if selected_type != "Tümü":
                df = df[df["Asset_Type"] == selected_type]
        st.dataframe(df, use_container_width=True)
        if "Quantity" in df.columns and "Buy_Price" in df.columns:
            total = (df["Quantity"] * df["Buy_Price"]).sum()
            st.metric("Toplam Portföy Değeri", f"₺{total:,.2f}")
    else:
        st.info("📭 Henüz varlık yok")

def show_add_asset(sheet, data):
    st.header("➕ Yeni Varlık Ekle")
    with st.form("new_asset_form"):
        col1, col2 = st.columns(2)
        with col1:
            symbol = st.text_input("Sembol (ör: THYAO, BTC)")
            asset_type = st.selectbox("Varlık Türü", ["hisse", "kripto", "emtia", "döviz"])
            quantity = st.number_input("Miktar", min_value=0.0, step=0.01)
        with col2:
            buy_price = st.number_input("Alış Fiyatı (₺)", min_value=0.0, step=0.01)
            buy_date = st.date_input("Alış Tarihi")
            notes = st.text_input("Notlar (opsiyonel)")
        
        submitted = st.form_submit_button("💾 Kaydet", use_container_width=True)
        
        if submitted:
            if symbol and quantity > 0 and buy_price > 0:
                new_id = max([item["ID"] for item in data], default=0) + 1
                sheet.append_row([new_id, symbol.upper(), asset_type, quantity, buy_price, str(buy_date), notes])
                st.success(f"✅ {symbol.upper()} başarıyla eklendi!")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Lütfen tüm zorunlu alanları doldurun!")

if __name__ == "__main__":
    main()
