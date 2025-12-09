import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font

# ----------------------- Streamlit Page Config -----------------------
st.set_page_config(
    page_title="SEO Checker",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for design
st.markdown("""
    <style>
    body {
        background: linear-gradient(135deg, #a1c4fd, #c2e9fb);
        color: white;
        font-family: 'Arial', sans-serif;
    }
    .stButton>button {
        background-color: #0072b1;
        color: white;
        font-weight: bold;
    }
    .stTextInput>div>input {
        color: black;
    }
    .stFileUploader>div>input {
        background-color: white;
        color: black;
    }
    .dataframe tbody tr th, .dataframe tbody tr td {
        color: black;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 SEO Checker")
st.write("Paste URLs below (one per line) to analyze their SEO metrics:")

# ----------------------- Input URLs -----------------------
urls_input = st.text_area("Enter URLs", height=150)
urls_list = [u.strip() for u in urls_input.split("\n") if u.strip()]

# ----------------------- SEO Helper Functions -----------------------
def get_soup(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        return BeautifulSoup(r.text, "html.parser")
    except:
        return None

def seo_analysis(url):
    soup = get_soup(url)
    if not soup:
        return {
            "URL": url,
            "Title": "",
            "Summary": "",
            "SEO Score": 0,
            "SEO Grade": "",
            "Predicted Public Rating": "",
            "Title Length Ideal": 60,
            "Title Length Actual": 0,
            "Meta Length Ideal": 160,
            "Meta Length Actual": 0,
            "H1 Count Ideal": 1,
            "H1 Count Actual": 0,
            "H2 Count Ideal": 2,
            "H2 Count Actual": 0,
            "Content Length Ideal": 300,
            "Content Length Actual": 0,
            "Paragraph Count Ideal": 3,
            "Paragraph Count Actual": 0,
            "Keyword Density Ideal": 2,
            "Keyword Density Actual": 0,
            "Image Count Ideal": 2,
            "Image Count Actual": 0
        }

    # Title
    title_tag = soup.title.string if soup.title else ""
    title_length = len(title_tag)

    # Meta Description
    meta_tag = soup.find("meta", attrs={"name":"description"})
    meta_content = meta_tag['content'] if meta_tag else ""
    meta_length = len(meta_content)

    # H1 & H2 count
    h1_count = len(soup.find_all("h1"))
    h2_count = len(soup.find_all("h2"))

    # Paragraphs & content length
    paragraphs = soup.find_all("p")
    para_count = len(paragraphs)
    content_length = sum(len(p.get_text()) for p in paragraphs)

    # Keyword density (simple approach using first 3 words of title)
    keywords = title_tag.split()[:3]
    text = soup.get_text().lower()
    keyword_density = round(sum(text.count(k.lower()) for k in keywords)/max(1,len(text.split()))*100, 2)

    # Image count
    img_count = len(soup.find_all("img"))

    # SEO score (simple heuristic)
    score = 0
    if 50 <= title_length <= 70: score += 15
    if 50 <= meta_length <= 160: score += 15
    if h1_count == 1: score += 15
    if h2_count >= 1: score += 10
    if content_length >= 300: score += 20
    if keyword_density >= 1: score += 10
    if img_count >= 1: score += 15

    # SEO Grade
    grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >=40 else "D"

    # Summary (first 20 words)
    summary = ' '.join(meta_content.split()[:20])

    return {
        "URL": url,
        "Title": title_tag[:20],
        "Summary": summary,
        "SEO Score": score,
        "SEO Grade": grade,
        "Predicted Public Rating": "",
        "Title Length Ideal": 60,
        "Title Length Actual": title_length,
        "Meta Length Ideal": 160,
        "Meta Length Actual": meta_length,
        "H1 Count Ideal": 1,
        "H1 Count Actual": h1_count,
        "H2 Count Ideal": 2,
        "H2 Count Actual": h2_count,
        "Content Length Ideal": 300,
        "Content Length Actual": content_length,
        "Paragraph Count Ideal": 3,
        "Paragraph Count Actual": para_count,
        "Keyword Density Ideal": 2,
        "Keyword Density Actual": keyword_density,
        "Image Count Ideal": 2,
        "Image Count Actual": img_count
    }

# ----------------------- Analyze Button -----------------------
if st.button("Analyze URLs"):
    if not urls_list:
        st.warning("Please enter at least one URL!")
    else:
        results = []
        for u in urls_list:
            results.append(seo_analysis(u))
        df = pd.DataFrame(results)
        st.dataframe(df, height=400)

        # ----------------------- Excel Download -----------------------
        buffer = BytesIO()
        wb = Workbook()
        ws = wb.active
        ws.title = "SEO Report"

        # Add headers
        headers = list(df.columns)
        ws.append(headers)

        # Add data
        for row in df.values.tolist():
            ws.append(row)

        # Styles
        for col in ws.iter_cols(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in col:
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.border = Border(left=Side(style='thin', color='B0C4DE'),
                                     right=Side(style='thin', color='B0C4DE'),
                                     top=Side(style='thin', color='B0C4DE'),
                                     bottom=Side(style='thin', color='B0C4DE'))
                if cell.row == 1:
                    cell.fill = PatternFill("solid", fgColor="87CEEB")
                    cell.font = Font(bold=True)

        wb.save(buffer)
        st.download_button(
            label="📥 Download SEO Report",
            data=buffer,
            file_name="SEO_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
