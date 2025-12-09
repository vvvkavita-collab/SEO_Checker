# Full Premium SEO Checker (Patrika) — with paste box + logo + password
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font
import os

# ------------------------
# Config & Password
# ------------------------
st.set_page_config(page_title="Patrika Internal SEO Auditor – V1.0", layout="wide")
PASSWORD = "Patrika@2025"   # recommended password (change if you want)

def require_password():
    st.markdown("<h3 style='color:#bfe9ff;'>🔒 Enter Password to continue</h3>", unsafe_allow_html=True)
    pw = st.text_input("", type="password", key="pwd")
    if pw != PASSWORD:
        if pw:
            st.error("Incorrect password")
        st.stop()

require_password()

# ------------------------
# PREMIUM CSS + Logo Placeholder
# ------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
html, body, [class*="css"]  { font-family: 'Poppins', sans-serif; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp { background: linear-gradient(135deg, #071226, #102032); color: white !important; }

/* Heading glow */
h1 { color: #87e0ff !important; text-shadow: 0 0 12px rgba(135,224,255,0.6); }

/* Upload card */
div[data-testid="stFileUploader"] {
  background: #0f1720 !important;
  padding: 24px;
  border-radius: 12px;
  border: 1px solid rgba(79,195,247,0.25) !important;
  box-shadow: 0 8px 30px rgba(3,169,244,0.08);
}

/* Inputs */
textarea, input, .stTextArea textarea {
  background: #0b1420 !important;
  color: #dbefff !important;
  border: 1px solid rgba(79,195,247,0.18) !important;
}

/* Buttons */
div.stButton > button {
  background: linear-gradient(90deg,#0288D1,#03A9F4) !important;
  color: white !important;
  border-radius: 10px !important;
  padding: 10px 18px !important;
  font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ------------------------
# Logo: try local file first, else fallback URL
# ------------------------
logo_local = "patrika_logo.png"   # put your logo file next to this script for reliable display
logo_fallback = "https://upload.wikimedia.org/wikipedia/commons/9/98/Patrika_logo.png"  # fallback

if os.path.exists(logo_local):
    st.image(logo_local, width=160)
else:
    # try to show fallback URL (may be blocked in some deployments)
    st.image(logo_fallback, width=160)

# ------------------------
# App Title + subtitle
# ------------------------
st.markdown("<h1>URL Analysis → SEO Report Generator (Patrika)</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#cfeeff;'>Paste multiple URLs or upload a TXT/CSV/XLSX list. Summary column removed — output contains URL & Title only.</p>", unsafe_allow_html=True)

# ------------------------
# Inputs: Paste box + File uploader (both visible)
# ------------------------
st.markdown("### Paste URLs (one URL per line)")
urls_text = st.text_area("", height=160, placeholder="https://example.com/article-1\nhttps://example.com/article-2")

st.markdown("### Or upload a file (TXT / CSV / XLSX)")
uploaded = st.file_uploader("", type=["txt","csv","xlsx"])

# Helper to trim long strings to 20 chars with ellipsis
def trim20(s):
    s = "" if s is None else str(s)
    return s if len(s) <= 20 else s[:20] + "..."

# URL analyzer (simple: fetch title)
def fetch_title(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=12)
        r.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        return title
    except Exception:
        return "Error fetching"

# Build URL list from paste + upload
urls = []
# from paste
if urls_text and urls_text.strip():
    lines = [ln.strip() for ln in urls_text.splitlines() if ln.strip()]
    urls.extend(lines)

# from uploaded file
if uploaded is not None:
    try:
        name = uploaded.name.lower()
        if name.endswith(".txt"):
            txt = uploaded.read().decode("utf-8", errors="ignore")
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            urls.extend(lines)
        elif name.endswith(".csv"):
            df = pd.read_csv(uploaded, header=None)
            urls.extend(df.iloc[:,0].astype(str).str.strip().tolist())
        elif name.endswith(".xlsx"):
            df = pd.read_excel(uploaded, header=None)
            urls.extend(df.iloc[:,0].astype(str).str.strip().tolist())
    except Exception as e:
        st.error(f"Failed to parse uploaded file: {e}")

# De-duplicate and cleanup
urls = [u for i,u in enumerate(urls) if u and u not in urls[:i]]

# Show count
st.markdown(f"**Total URLs queued:** {len(urls)}")

# ------------------------
# Process & generate excel
# ------------------------
if st.button("Process & Create Excel"):
    if not urls:
        st.error("Paste URLs or upload a file first.")
    else:
        st.info("Processing — fetching page titles (this may take time depending on number of URLs)...")
        rows = []
        progress_bar = st.progress(0)
        for i, u in enumerate(urls, start=1):
            title = fetch_title(u)
            rows.append({"URL": trim20(u), "Title": trim20(title)})
            progress_bar.progress(i/len(urls))

        df_out = pd.DataFrame(rows)

        # show preview
        st.subheader("Preview")
        st.dataframe(df_out)

        # Build excel (no Summary column)
        wb = Workbook()
        ws = wb.active
        ws.title = "Audit"

        headers = ["URL", "Title"]
        ws.append(headers)

        # Styles
        header_fill = PatternFill("solid", fgColor="4FC3F7")
        header_font = Font(bold=True, color="000000")
        thin = Side(style="thin", color="4FC3F7")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # header style
        for c in ws[1]:
            c.fill = header_fill
            c.font = header_font
            c.border = border
            c.alignment = center

        # data rows
        for r in df_out.itertuples(index=False):
            ws.append(list(r))

        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.border = border
                cell.alignment = center

        # set column widths (URL 40, Title 40 — trimmed to 20 in values)
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 40

        # save to bytes
        out = BytesIO()
        wb.save(out)
        out.seek(0)

        st.success("Excel ready — download below")
        st.download_button("⬇️ Download Patrika SEO Audit (XLSX)", data=out, file_name="Patrika_SEO_Audit.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
