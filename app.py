import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font

# ============================
# PASSWORD PROTECTION
# ============================
st.set_page_config(page_title="Patrika Internal SEO Auditor – V1.0", layout="wide")

PASSWORD = "Patrika@2025"  # ← Recommended secure password

def check_password():
    st.markdown("<h2 style='color:white; margin-top:40px;'>🔐 Secure Login</h2>", unsafe_allow_html=True)
    password = st.text_input("Enter Password", type="password")
    if password == PASSWORD:
        return True
    else:
        if password:
            st.error("Incorrect Password!")
        return False

if not check_password():
    st.stop()

# ============================
# PAGE DESIGN / WHITE LABEL
# ============================
st.markdown("""
    <style>
        body {
            background-color: #0b1e39;
        }
        .main {
            background-color: #0b1e39;
        }
        header {visibility: hidden;} /* hide top Streamlit bar */
        .st-emotion-cache-1avcm0n {
            background-color:#0b1e39;
        }
        .st-emotion-cache-1r6slb0 { color: white; }

        .stFileUploader label {
            color: #1E90FF !important;
            font-size: 18px !important;
            font-weight: 600;
        }
        .stUploadDropzone { color: #1E90FF !important; }
    </style>
""", unsafe_allow_html=True)

# ============================
# LOGO + TITLE
# ============================
st.image("https://i.ibb.co/WVh6sHZ/patrika-logo.png", width=160)

st.markdown("""
<h1 style='color:white; font-weight:700;'>
    Patrika Internal SEO Auditor – V1.0
</h1>
<h3 style='color:#79c2ff; margin-top:-10px;'>
    URL Analysis → Excel Report → SEO Guidelines (Auto Generated)
</h3>
""", unsafe_allow_html=True)

# ============================
# EXTRACT FUNCTION
# ============================
def extract_details(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.string.strip() if soup.title else "N/A"
        title = (title[:20] + "...") if len(title) > 20 else title

        return [url[:20] + "...", title]
    except:
        return [url[:20] + "...", "Error"]

# ============================
# INPUT BOXES
# ============================
uploaded_file = st.file_uploader("Upload URL List (TXT/CSV/XLSX)", type=['txt', 'csv', 'xlsx'])

st.write("")
st.markdown("<h4 style='color:white;'>Paste URLs here</h4>", unsafe_allow_html=True)
url_text = st.text_area("", height=150)

def parse_urls(text):
    return list(filter(None, [line.strip() for line in text.split("\n")]))

# ============================
# PROCESS
# ============================
if st.button("Process & Create Excel", use_container_width=True):
    urls = []

    if uploaded_file:
        if uploaded_file.name.endswith("txt"):
            urls = uploaded_file.read().decode().splitlines()
        elif uploaded_file.name.endswith("csv"):
            df = pd.read_csv(uploaded_file)
            urls = df.iloc[:, 0].tolist()
        elif uploaded_file.name.endswith("xlsx"):
            df = pd.read_excel(uploaded_file)
            urls = df.iloc[:, 0].tolist()

    urls += parse_urls(url_text)

    if not urls:
        st.error("Please upload or paste URLs.")
        st.stop()

    st.info("⏳ Processing URLs... please wait")

    data = []
    for url in urls:
        row = extract_details(url)
        data.append(row)

    # ============================
    # CREATE EXCEL
    # ============================
    wb = Workbook()
    ws = wb.active
    ws.title = "SEO Report"
    headers = ["URL", "Title"]
    ws.append(headers)

    fill = PatternFill("solid", fgColor="ddeeff")
    border = Border(left=Side(style="thin", color="6699cc"),
                    right=Side(style="thin", color="6699cc"),
                    top=Side(style="thin", color="6699cc"),
                    bottom=Side(style="thin", color="6699cc"))
    center = Alignment(horizontal="center", vertical="center")

    for row in data:
        ws.append(row)

    for row in ws.iter_rows():
        for cell in row:
            cell.fill = fill
            cell.border = border
            cell.alignment = center
            cell.font = Font(bold=True)

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 25

    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)

    st.success("🎉 SEO Audit Excel Ready!")

    st.download_button(
        label="⬇️ Download SEO Report",
        data=excel_file,
        file_name="Patrika_SEO_Audit.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
