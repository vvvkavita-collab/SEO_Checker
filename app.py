import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font
from openpyxl.utils import get_column_letter

# ------------------- Streamlit Page Config -------------------
st.set_page_config(
    page_title="Patrika SEO Checker",
    page_icon="📈",
    layout="wide"
)

# Custom CSS for Streamlit page
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
    color: white;
}
h1, h2, h3, h4, h5 {
    color: white;
}
.stButton>button {
    background-color: #1E90FF;
    color: white;
    border-radius: 8px;
}
.stTextArea textarea {
    background-color: #203a43;
    color: white;
}
.stTextInput>div>input {
    background-color: #203a43;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ------------------- Helper Functions -------------------
def fetch_seo_data(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Title
        title = soup.title.string.strip() if soup.title else ""

        # Meta description
        meta_desc_tag = soup.find('meta', attrs={"name":"description"})
        meta_desc = meta_desc_tag['content'].strip() if meta_desc_tag else ""

        # Word counts
        title_words = len(title.split())
        meta_words = len(meta_desc.split())

        # Ideal SEO word counts
        ideal_title_words = 10
        ideal_meta_words = 20

        # Summary (first 20 chars of meta)
        summary = meta_desc[:20]

        return {
            "URL": url,
            "Title": title[:20],
            "Title Words (Actual)": title_words,
            "Title Words (Ideal)": ideal_title_words,
            "Meta Description": meta_desc[:20],
            "Meta Words (Actual)": meta_words,
            "Meta Words (Ideal)": ideal_meta_words,
            "Summary": summary
        }

    except Exception as e:
        return {
            "URL": url,
            "Title": "Error",
            "Title Words (Actual)": 0,
            "Title Words (Ideal)": 10,
            "Meta Description": "Error",
            "Meta Words (Actual)": 0,
            "Meta Words (Ideal)": 20,
            "Summary": "Error"
        }

def generate_excel(df):
    wb = Workbook()
    ws = wb.active
    ws.title = "SEO Report"

    # Append headers
    headers = list(df.columns)
    ws.append(headers)

    # Append data
    for row in df.itertuples(index=False):
        ws.append(list(row))

    # Styles
    thin_border = Border(left=Side(style='thin', color="ADD8E6"),
                         right=Side(style='thin', color="ADD8E6"),
                         top=Side(style='thin', color="ADD8E6"),
                         bottom=Side(style='thin', color="ADD8E6"))
    
    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = thin_border
            if cell.row == 1:
                cell.font = Font(bold=True, color="000000")
                cell.fill = PatternFill("solid", fgColor="ADD8E6")
            else:
                cell.fill = PatternFill("solid", fgColor="E0F7FA")
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[col_letter].width = adjusted_width

    # Remove gridlines in Excel
    ws.sheet_view.showGridLines = False

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream

# ------------------- Streamlit Layout -------------------
st.title("📈 Patrika SEO Checker")
st.markdown("Paste multiple URLs (one per line) to analyze SEO metrics.")

urls_input = st.text_area("Enter URLs here", height=150)

if st.button("Analyze SEO"):
    if urls_input.strip() == "":
        st.warning("Please enter at least one URL.")
    else:
        urls = [u.strip() for u in urls_input.strip().split("\n") if u.strip()]
        results = []
        for url in urls:
            results.append(fetch_seo_data(url))

        df = pd.DataFrame(results)
        st.markdown("### SEO Results")
        st.dataframe(df, height=400)

        excel_file = generate_excel(df)
        st.download_button(
            label="📥 Download Excel Report",
            data=excel_file,
            file_name="SEO_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
