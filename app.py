import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# --- Configuration ---
st.set_page_config(page_title="PhonePe Statement Analyzer", page_icon="📱", layout="wide")

def clean_amount(amount_str):
    """
    Cleans amount string: removes '₹', commas, and converts to float.
    """
    if not amount_str:
        return 0.0
    # Remove any character that is not a digit or a decimal point
    clean_str = re.sub(r'[^\d.]', '', amount_str)
    try:
        return float(clean_str)
    except ValueError:
        return 0.0

def parse_phonepe_pdf(uploaded_file):
    """
    Extracts transactions from PhonePe PDF using text parsing and Regex
    instead of table extraction for better reliability.
    """
    data = []
    
    # Regex Pattern Breakdown:
    # 1. Date: Starts with line, e.g., "Oct 30, 2025" -> ^([A-Z][a-z]{3}\s\d{1,2},\s\d{4})
    # 2. Details: Anything in the middle -> (.*?)
    # 3. Type: Must be CREDIT or DEBIT -> (CREDIT|DEBIT)
    # 4. Amount: Ends with amount (with or without ₹) -> ₹?([\d,]+\.?\d*)
    line_pattern = re.compile(
        r'^([A-Z][a-z]{2}\s\d{2},\s\d{4})\s{1}(.*)\s+(CREDIT|DEBIT)\s+₹([\d,]+)$'
    )

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            # Extract raw text from the page
            text = page.extract_text()
            if not text:
                continue
            
            # Process line by line
            print("Total length of extracted text:", len(text))  # Debugging line
            lines = text.split('\n')
            for line in lines:
                match = line_pattern.search(line)
                if match:
                    # Extract groups from regex
                    date_str = match.group(1)
                    details_str = match.group(2).strip()
                    trans_type = match.group(3)
                    amount_str = match.group(4)

                    # Append to list
                    data.append({
                        "Date": date_str,
                        "Transaction Details": details_str,
                        "Type": trans_type,
                        "Amount": clean_amount(amount_str)
                    })

    df = pd.DataFrame(data)
    return df

# --- Streamlit UI ---

st.title("📱 PhonePe Statement Converter & Analyzer")
st.markdown("""
Upload your PhonePe PDF statement. This tool will:
1. **Convert** it to a clean Excel/CSV file (removing icons & UTRs).
2. **Calculate** the total 'Received' (Credit) amount per day.
""")

uploaded_file = st.file_uploader("Upload PhonePe PDF Statement", type=["pdf"])

if uploaded_file is not None:
    with st.spinner("Parsing PDF..."):
        try:
            # 1. Parse Data
            df = parse_phonepe_pdf(uploaded_file)
            
            if df.empty:
                st.error("No transactions found! Please check if the PDF format is standard.")
            else:
                st.success(f"Successfully extracted {len(df)} transactions.")

                # 2. Data Processing
                # Convert Date to datetime for sorting
                df['Date_Object'] = pd.to_datetime(df['Date'], format='%b %d, %Y', errors='coerce')
                
                # Filter for CREDITS only
                credits_df = df[df['Type'] == 'CREDIT'].copy()
                
                # Group by Date and Sum
                daily_credits = credits_df.groupby('Date_Object')['Amount'].sum().reset_index()
                
                # Format for display
                daily_credits['Date'] = daily_credits['Date_Object'].dt.strftime('%Y-%m-%d')
                daily_credits = daily_credits[['Date', 'Amount']].sort_values(by='Date', ascending=False)
                daily_credits.rename(columns={'Amount': 'Total Received (₹)'}, inplace=True)

                # --- Display Results ---
                
                # Metrics
                total_received = daily_credits['Total Received (₹)'].sum()
                st.metric("Total Money Received (Total Credits)", f"₹ {total_received:,.2f}")

                tab1, tab2 = st.tabs(["📅 Daily Credits Sum", "📋 Cleaned Statement Data"])

                with tab1:
                    st.subheader("Sum of Credits per Day")
                    st.dataframe(daily_credits, width='stretch', hide_index=True)

                with tab2:
                    st.subheader("All Transactions (Cleaned)")
                    st.dataframe(df.drop(columns=['Date_Object']), width='stretch', hide_index=True)

                # --- Download Section ---
                st.markdown("---")
                st.subheader("📥 Download Converted Files")
                
                col1, col2 = st.columns(2)
                
                # CSV Download
                csv_data = df.drop(columns=['Date_Object']).to_csv(index=False).encode('utf-8')
                col1.download_button(
                    label="Download as CSV",
                    data=csv_data,
                    file_name="phonepe_cleaned_data.csv",
                    mime="text/csv"
                )

                # Excel Download
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.drop(columns=['Date_Object']).to_excel(writer, sheet_name='All Transactions', index=False)
                    daily_credits.to_excel(writer, sheet_name='Daily Summary', index=False)
                
                col2.download_button(
                    label="Download as Excel (XLSX)",
                    data=buffer.getvalue(),
                    file_name="phonepe_statement_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"An error occurred: {e}")