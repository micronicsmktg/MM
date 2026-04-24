import streamlit as st
import pandas as pd
from PIL import Image
import requests
from io import BytesIO

st.set_page_config(page_title="Interactive Pricelist", layout="wide")
st.title("📋 Interactive Pricelist")

# Google Sheets setup
st.sidebar.header("📊 Data Source")
sheet_url = st.sidebar.text_input(
    "Enter Google Sheets Shareable Link",
    placeholder="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit?usp=sharing"
)

def get_sheet_id_from_url(url):
    """Extract sheet ID from shareable link"""
    try:
        sheet_id = url.split("/d/")[1].split("/")[0]
        return sheet_id
    except:
        return None

def read_google_sheet(sheet_id, sheet_name):
    """Read specific sheet from Google Sheets"""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/query?tqx=out:csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(url)
        # Auto-convert column names: spaces to underscores
        df.columns = df.columns.str.replace(" ", "_").str.replace("?", "").str.strip()
        return df
    except Exception as e:
        st.error(f"Error reading sheet: {e}")
        return None

# Password toggle for retail price
st.sidebar.markdown("---")
retail_password = st.sidebar.text_input("Enter password to show Retail prices", type="password")
show_retail = retail_password == "admin123"  # Change this password as needed

if sheet_url:
    sheet_id = get_sheet_id_from_url(sheet_url)
    
    if sheet_id:
        st.sidebar.success("✅ Sheet ID extracted!")
        
        # Read both sheets
        inventory_df = read_google_sheet(sheet_id, "INVTY")
        photos_df = read_google_sheet(sheet_id, "PhotoDatabase")
        
        if inventory_df is not None and photos_df is not None:
            # Merge on Item ID
            merged_df = inventory_df.merge(photos_df, on="Item_ID", how="left")
            
            # Filter: Only Active items
            merged_df = merged_df[merged_df["Active"].astype(str).str.lower() == "yes"]
            
            # Filter: Only items with Photo
            merged_df = merged_df[merged_df["Photo"].notna()]
            merged_df = merged_df[merged_df["Photo"].str.strip() != ""]
            
            # Add Status column based on Qty on Hand
            merged_df["Status"] = merged_df["Qty_on_Hand"].apply(
                lambda x: "✅ Available" if x > 0 else "🛒 Order Basis"
            )
            
            # Combine Item Description + Description for Sales
            merged_df["Item"] = merged_df["Item_Description"] + " - " + merged_df["Description_for_Sales"].astype(str)
            
            # Display interactive table
            st.subheader("Product Catalog")
            
            # Filter options
            col1, col2 = st.columns(2)
            
            with col1:
                notes_options = sorted(merged_df["Notes"].dropna().unique().tolist())
                notes_filter = st.multiselect(
                    "Filter by Category (Notes)",
                    options=notes_options,
                    default=notes_options
                )
            
            with col2:
                search_term = st.text_input("Search by Item")
            
            # Apply filters
            filtered_df = merged_df[merged_df["Notes"].isin(notes_filter)]
            
            if search_term:
                filtered_df = filtered_df[
                    filtered_df["Item"].str.contains(search_term, case=False, na=False)
                ]
            
            st.write(f"Showing {len(filtered_df)} products")
            
            # Display products in grid (3 columns)
            cols = st.columns(3)
            for idx, (i, row) in enumerate(filtered_df.iterrows()):
                with cols[idx % 3]:
                    st.markdown("---")
                    
                    # Display photo
                    try:
                        response = requests.get(row["Photo"], timeout=5)
                        img = Image.open(BytesIO(response.content))
                        st.image(img, use_column_width=True)
                    except:
                        st.write("📷 Photo unavailable")
                    
                    # Display product info
                    st.write(f"**{row['Item']}**")
                    st.markdown(f"### {row['Status']}")
                    
                    # Show retail price only if password correct
                    if show_retail:
                        st.write(f"**Retail:** ${row['Retail']:.2f}" if pd.notna(row['Retail']) else "")
                    
                    st.write(f"**Category:** {row['Notes']}")
            
            # Display full table view
            st.subheader("Full Table View")
            
            if show_retail:
                display_cols = ["Photo", "Item", "Status", "Retail", "Notes"]
                table_data = filtered_df[["Photo", "Item", "Status", "Retail", "Notes"]].copy()
            else:
                display_cols = ["Photo", "Item", "Status", "Notes"]
                table_data = filtered_df[["Photo", "Item", "Status", "Notes"]].copy()
            
            # Create display dataframe (hide Photo URL, show as clickable)
            display_df = table_data.copy()
            display_df["Photo"] = display_df["Photo"].apply(lambda x: "📷" if pd.notna(x) else "")
            
            st.dataframe(
                display_df,
                use_container_width=True
            )
            
            # Download option
            csv = filtered_df[["Item_ID", "Item", "Status", "Retail", "Notes"]].to_csv(index=False)
            st.download_button(
                label="📥 Download Filtered Data",
                data=csv,
                file_name="pricelist.csv",
                mime="text/csv"
            )
            
            # Show password hint for admin
            if not show_retail:
                st.sidebar.info("💡 Enter password to view Retail prices")
        else:
            st.error("❌ Could not read sheets. Make sure sheet names are 'INVTY' and 'PhotoDatabase'")
    else:
        st.error("❌ Invalid Google Sheets link. Check the URL.")
else:
    st.info("👈 Paste your Google Sheets shareable link in the sidebar to get started")
    
    st.markdown("""
    ### Setup Instructions:
    1. Your Google Sheet must have 2 tabs:
       - **INVTY**: Item ID, Active?, Item Description, Description for Sales, Qty on Hand, Retail, etc.
       - **PhotoDatabase**: Item ID, Photo (URL), Notes (Category)
    2. Share the sheet (anyone with link can view)
    3. Paste the shareable link above
    4. Only Active items with photos will show! ✅
    """)
