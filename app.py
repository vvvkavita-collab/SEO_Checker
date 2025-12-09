import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font

# ---------------- Streamlit Page Config ----------------
st.set_page_config(page_title="Patrika SEO Checker", layout="wide", page_icon=":mag:")

# Custom CSS for impressive look
st.markdown("""
    <style>
    body {
        background-color: #0b3d91;
        color: white;
    }
    .stButton>button {
        background-color: #0073e6;
        color: white;
        font-weight: bold;
    }
    .stTextInput>div>div>input {
        background-color: #ffffff;
        color: black;
    }
    h1, h2, h3 {
        color: white;
    }
    .stDataFrame {
        color: black;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Patrika SEO Checker")
st.write("Upload URLs CSV or Excel file to check SEO parameters.")

# ---------------- File Upload ----------------
uploaded_file = st.file_uploader("Choose CSV/Excel file", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_urls = pd.read_csv(uploaded_file)
        else:
            df_urls = pd.read_excel(uploaded_file)

        if 'URL' not in df_urls.columns:
            st.error("File must contain 'URL' column.")
        else:
            st.success(f"File loaded successfully! {len(df_urls)} URLs found.")
            
            results = []

            for url in df_urls['URL']:
                try:
                    r = requests.get(url, timeout=10)
                    soup = BeautifulSoup(r.text, 'html.parser')

                    # Title
                    title_tag = soup.find('title')
                    title = title_tag.text.strip() if title_tag else ''

                    # Meta description
                    meta_tag = soup.find('meta', attrs={'name': 'description'})
                    meta = meta_tag['content'].strip() if meta_tag and 'content' in meta_tag.attrs else ''

                    # Limit length to 20 chars
                    title_short = (title[:20] + '...') if len(title) > 20 else title
                    meta_short = (meta[:20] + '...') if len(meta) > 20 else meta

                    results.append({
                        'URL': (url[:20] + '...') if len(url) > 20 else url,
                        'Title': title_short,
                        'Meta': meta_short
                    })

                except Exception as e:
                    results.append({
                        'URL': (url[:20] + '...') if len(url) > 20 else url,
                        'Title': 'Error',
                        'Meta': 'Error'
                    })

            df_result = pd.DataFrame(results)
            st.subheader("SEO Results")
            st.dataframe(df_result)

            # ---------------- Excel Download ----------------
            def to_excel(df):
                output = BytesIO()
                wb = Workbook()
                ws = wb.active
                ws.title = "SEO Results"

                # Header
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill("solid", fgColor="0073e6")
                border = Border(left=Side(style='thin', color='BDD7EE'),
                                right=Side(style='thin', color='BDD7EE'),
                                top=Side(style='thin', color='BDD7EE'),
                                bottom=Side(style='thin', color='BDD7EE'))

                for col_num, col_name in enumerate(df.columns, 1):
                    cell = ws.cell(row=1, column=col_num, value=col_name)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                    cell.border = border

                # Data
                for r_idx, row in enumerate(df.itertuples(index=False), 2):
                    for c_idx, value in enumerate(row, 1):
                        cell = ws.cell(row=r_idx, column=c_idx, value=value)
                        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                        cell.border = border

                # Column width auto-adjust
                for col in ws.columns:
                    max_length = 0
                    column = col[0].column_letter
                    for cell in col:
                        try:
                            if cell.value:
                                max_length = max(max_length, len(str(cell.value)))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    ws.column_dimensions[column].width = adjusted_width

                wb.save(output)
                processed_data = output.getvalue()
                return processed_data

            excel_data = to_excel(df_result)
            st.download_button(label='Download Excel', data=excel_data, file_name='SEO_Results.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        st.error(f"Error loading file: {e}")
