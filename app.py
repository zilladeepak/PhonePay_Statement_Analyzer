import streamlit as st
import pdfplumber
import pandas as pd
import numpy as np
import re
from io import BytesIO

# --- App configuration ---
# Configure Streamlit page metadata before rendering any components.
st.set_page_config(page_title="PhonePe Statement Analyzer", page_icon="📱", layout="wide")

def clean_amount(amount_str):
    """
    Convert an extracted numeric amount string into a float.
    Removes currency symbols and commas so values can be summed.
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
    Open the uploaded PDF and extract transaction rows into a DataFrame.
    This parser uses regex on extracted text lines to identify each transaction.
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
            # Extract raw text from the page and skip pages without text.
            text = page.extract_text()
            if not text:
                continue
            
            # Split the page text into lines and match each line against the regex.
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

    # Build transaction DataFrame and annotate credit/debit/cash flow columns.
    df = pd.DataFrame(data)
    if not df.empty:
        df['Credit'] = df.apply(lambda row: row['Amount'] if row['Type'] == 'CREDIT' else 0.0, axis=1)
        df['Debit'] = df.apply(lambda row: row['Amount'] if row['Type'] == 'DEBIT' else 0.0, axis=1)
        df['Transaction Cash Flow'] = df['Credit'] - df['Debit']
        # Cumulative cash flow within each date, shown in the cleaned transaction table.
        df['Total Cash Flow'] = df.groupby('Date')['Transaction Cash Flow'].transform('cumsum')
    return df

# --- Streamlit UI ---
# Render the main app title and instructions.

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
            # 1. Parse uploaded PDF into a transaction DataFrame.
            df = parse_phonepe_pdf(uploaded_file)
            
            if df.empty:
                st.error("No transactions found! Please check if the PDF format is standard.")
            else:
                st.success(f"Successfully extracted {len(df)} transactions.")

                # 2. Data Processing
                # Convert date strings into datetime objects for grouping and sorting.
                df['Date_Object'] = pd.to_datetime(df['Date'], format='%b %d, %Y', errors='coerce')
                
                # Compute daily totals for credit, debit, and cash flow
                # This summary is shown in the first tab.
                daily_summary = df.groupby('Date_Object').agg(
                    Total_Received=('Credit', 'sum'),
                    Total_Debits=('Debit', 'sum'),
                    Total_Cash_Flow=('Transaction Cash Flow', 'sum')
                ).reset_index()
                
                # Format for display
                daily_summary['Date'] = daily_summary['Date_Object'].dt.strftime('%Y-%m-%d')
                daily_summary = daily_summary[['Date', 'Total_Received', 'Total_Debits', 'Total_Cash_Flow']].sort_values(by='Date', ascending=False)
                daily_summary.rename(columns={
                    'Total_Received': 'Total Received (₹)',
                    'Total_Debits': 'Total Debits (₹)',
                    'Total_Cash_Flow': 'Total Cash Flow (₹)'
                }, inplace=True)

                # --- Display Results ---
                
                total_received = daily_summary['Total Received (₹)'].sum()
                st.metric("Total Money Received (Total Credits)", f"₹ {total_received:,.2f}")

                tab1, tab2 = st.tabs(["📅 Daily Credits Sum", "📋 Cleaned Statement Data"])

                with tab1:
                    st.subheader("Daily Cash Flow Summary")
                    st.dataframe(daily_summary, width='stretch', hide_index=True)

                with tab2:
                    st.subheader("All Transactions (Cleaned)")
                    
                    # Insert an empty row between dates for readability.
                    display_rows = []
                    prev_date = None
                    display_df = df.drop(columns=['Date_Object']).copy()
                    numeric_cols = ['Amount', 'Credit', 'Debit', 'Transaction Cash Flow', 'Total Cash Flow']
                    for _, row in display_df.iterrows():
                        if prev_date is not None and row['Date'] != prev_date:
                            display_rows.append({
                                col: np.nan if col in numeric_cols else ''
                                for col in display_df.columns
                            })
                        display_rows.append(row.to_dict())
                        prev_date = row['Date']

                    # Create a DataFrame for display and apply styling to highlight debits in red.
                    display_df = pd.DataFrame(display_rows)
                    styled_df = display_df.style.apply(
                        lambda row: ['color: red' if row['Type'] == 'DEBIT' else '' for _ in row],
                        axis=1
                    ).format({
                        'Amount': '{:.2f}',
                        'Credit': '{:.2f}',
                        'Debit': '{:.2f}',
                        'Transaction Cash Flow': '{:.2f}',
                        'Total Cash Flow': '{:.2f}'
                    })
                    st.dataframe(styled_df, width='stretch', hide_index=True)

                # --- Download Section ---
                # Provide cleaned transaction downloads in CSV and XLSX formats.
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
                    daily_summary.to_excel(writer, sheet_name='Daily Summary', index=False)
                
                col2.download_button(
                    label="Download as Excel (XLSX)",
                    data=buffer.getvalue(),
                    file_name="phonepe_statement_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"An error occurred: {e}")