import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font

# ======================================
#            PREMIUM UI CSS
# ======================================
st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

html, body, [class*="css"]  {
    font-family: 'Poppins', sans-serif;
}

/* Remove Streamlit defaults */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* App Background */
.stApp {
    background: linear-gradient(135deg, #0f0f0f, #1c1c1c);
    color: white !important;
}

/* Headings */
h1, h2, h3, h4 {
    color: #4FC3F7 !important;
    text-shadow: 0px 0px 8px rgba(79,195,247,0.7);
}

/* Upload Box */
div[data-testid="stFileUploader"] {
    background: #1a1f24 !important;
    padding: 30px;
    border-radius: 16px;
    border: 1px solid #4FC3F7 !important;
    box-shadow: 0px 4px 15px rgba(0, 150, 255, 0.3);
}

/* Input fields */
input, textarea {
    background-color: #1f1f1f !important;
    color: white !important;
    border-radius: 10px !important;
    border: 1px solid #4FC3F7 !important;
}

/* Buttons */
div.stButton > button {
    background: linear-gradient(90deg, #0288D1, #03A9F4);
    color: white !important;
    border-radius: 10px;
    padding: 12px 26px;
    border: none;
    font-size: 16px;
    font-weight: 600;
    box-shadow: 0 0 10px rgba(3,169,244,0.6);
}
div.stButton > button:hover {
    background: linear-gradient(90deg, #03A9F4, #4FC3F7);
    box-shadow: 0 0 25px rgba(79,195,247,0.9);
}

</style>
""", unsafe_allow_html=True)

# ---------- LOGO -------------
st.markdown("""
<div style='text-align:center; margin-bottom:30px;'>
    <img src='https://i.ibb.co/Zm8Jr3r/logo.png' width='160'>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------
#             APP TITLE
# -----------------------------------------
st.title("URL Analysis → SEO Report Generator (Premium)")

# -----------------------------------------
#           FILE UPLOAD SECTION
# -----------------------------------------
uploaded_file = st.file_uploader("Upload URL List (TXT/CSV/XLSX)", type=["txt", "csv", "xlsx"])

def limit_length(text, limit=20):
    if not isinstance(text, str):
        return text
    return text[:limit] + "..." if len(text) > limit else text

# -----------------------------------------
#           URL PROCESSING FUNCTION
# -----------------------------------------
def analyze_url(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.string.strip() if soup.title else ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        summary = meta_desc["content"].strip() if meta_desc else ""

        return {
            "URL": limit_length(url),
            "Title": limit_length(title),
            "Summary": limit_length(summary)
        }
    except:
        return {
            "URL": limit_length(url),
            "Title": "Error",
            "Summary": "Error"
        }

# -----------------------------------------
#        MAIN PROCESSING BLOCK
# -----------------------------------------
if uploaded_file:
    df = None

    if uploaded_file.name.endswith(".txt"):
        urls = [line.strip() for line in uploaded_file.readlines()]
    elif uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        urls = df[df.columns[0]].tolist()
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
        urls = df[df.columns[0]].tolist()

    st.success("File uploaded successfully!")

    result_data = []
    progress = st.progress(0)

    for i, url in enumerate(urls):
        result_data.append(analyze_url(url))
        progress.progress((i + 1) / len(urls))

    result_df = pd.DataFrame(result_data)

    st.subheader("Preview of Results")
    st.dataframe(result_df)

    # -----------------------------------------
    #        EXCEL EXPORT (PREMIUM FORMAT)
    # -----------------------------------------
    if st.button("Download SEO Excel Report"):
        wb = Workbook()
        ws = wb.active
        ws.title = "SEO Report"

        headers = list(result_df.columns)
        ws.append(headers)

        # Styles
        header_fill = PatternFill(start_color="4FC3F7", end_color="4FC3F7", fill_type="solid")
        header_font = Font(color="000000", bold=True)
        cell_border = Border(left=Side(border_style="thin", color="4FC3F7"),
                             right=Side(border_style="thin", color="4FC3F7"),
                             top=Side(border_style="thin", color="4FC3F7"),
                             bottom=Side(border_style="thin", color="4FC3F7"))

        # Header Styling
        for col in ws[1]:
            col.fill = header_fill
            col.font = header_font
            col.alignment = Alignment(horizontal="center", vertical="center")
            col.border = cell_border

        # Data rows
        for row in result_df.values:
            ws.append(list(row))

        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="center")
                cell.border = cell_border

        # Adjust column width
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 25

        # Save to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        st.download_button(
            label="Download Excel File",
            data=output,
            file_name="SEO_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
