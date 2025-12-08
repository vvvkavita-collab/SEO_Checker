import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
from urllib.parse import urlparse
from io import BytesIO

# -----------------------------
# Helper Functions
# -----------------------------
def clean_text(text, max_length=20):
    """Clean and truncate text to max_length characters."""
    text = re.sub(r'\s+', ' ', text)  # Remove extra spaces/newlines
    return text[:max_length] + ('...' if len(text) > max_length else '')

def extract_summary(url):
    """Extract page title and meta description."""
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.title.string if soup.title else ''
        meta = soup.find('meta', attrs={'name': 'description'})
        description = meta['content'] if meta else ''
        return clean_text(title), clean_text(description)
    except:
        return '', ''

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="SEO Checker", page_icon="🔍", layout="wide")

# Custom CSS for colored background and improved UI
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #e0f7fa, #b2ebf2);
}
.stButton>button {
    background-color: #007acc;
    color: white;
    font-weight: bold;
    border-radius: 8px;
    padding: 0.5em 1.5em;
}
.stDataFrame th {
    background-color: #007acc;
    color: white;
    text-align: center;
}
.stDataFrame td {
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

st.title("🔍 SEO Checker")
st.markdown("Enter URLs below or upload an Excel/CSV file to analyze SEO metadata.")

# -----------------------------
# URL Input / File Upload
# -----------------------------
urls = st.text_area("Enter URLs (one per line)")
uploaded_file = st.file_uploader("Or upload Excel/CSV file", type=['csv', 'xlsx'])

url_list = []

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_file = pd.read_csv(uploaded_file)
        else:
            df_file = pd.read_excel(uploaded_file)
        if 'URL' in df_file.columns:
            url_list = df_file['URL'].tolist()
        else:
            st.error("Uploaded file must contain a column named 'URL'.")
    except Exception as e:
        st.error(f"Error reading file: {e}")

if urls:
    url_list.extend(urls.splitlines())

url_list = [u.strip() for u in url_list if u.strip()]

# -----------------------------
# SEO Extraction
# -----------------------------
if st.button("Check SEO"):
    if not url_list:
        st.warning("Please enter at least one URL or upload a file.")
    else:
        data = []
        progress = st.progress(0)
        total = len(url_list)

        for idx, url in enumerate(url_list):
            title, summary = extract_summary(url)
            data.append({
                "URL": clean_text(url),
                "Title": title,
                "Summary": summary
            })
            progress.progress((idx + 1)/total)

        df_result = pd.DataFrame(data)

        # Display in Streamlit with better style
        st.subheader("SEO Metadata")
        st.dataframe(df_result, use_container_width=True)

        # Download button
        towrite = BytesIO()
        df_result.to_excel(towrite, index=False, engine='openpyxl')
        towrite.seek(0)
        st.download_button(
            label="📥 Download Excel",
            data=towrite,
            file_name="SEO_Metadata.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.markdown("---")
st.markdown("**Designed & Developed by Piyush Vashisth**")
