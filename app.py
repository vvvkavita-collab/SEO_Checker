import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re
import unicodedata
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ================= CONFIG =================
st.set_page_config("Advanced SEO Auditor – Director Edition", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog")

HEADERS = {"User-Agent": "Mozilla/5.0"}
STOP_WORDS = {"and","or","the","is","was","of","to","for","with"}

# ================= INPUT =================
st.sidebar.header("Input")
bulk_file = st.sidebar.file_uploader("Upload URLs (TXT / CSV)", ["txt", "csv"])
single_url = st.text_input("Or Paste Single URL")
analyze = st.button("Analyze")

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def visible_len(text):
    return sum(1 for c in text if not unicodedata.category(c).startswith("C"))

def generate_seo_title(title, max_len=60):
    if visible_len(title) <= max_len:
        return title
    out = ""
    for w in title.split():
        temp = (out + " " + w).strip()
        if visible_len(temp) > max_len:
            break
        out = temp
    return out

def clean_slug(slug):
    words = [w for w in slug.split("-") if w and w not in STOP_WORDS]
    return "-".join(words[:10])

# ================= SEO SCORE =================
def calculate_seo_score(title, url):
    score = 0
    parsed = urlparse(url)
    slug = parsed.path.strip("/").lower()
    words = slug.split("-") if slug else []

    if visible_len(title) <= 60:
        score += 30
    if len(url) <= 80:
        score += 25
    if not any(w in STOP_WORDS for w in words):
        score += 20
    if len(words) <= 10:
        score += 15
    if "_" not in url and url == url.lower():
        score += 10

    return score

# ================= ARTICLE LOGIC =================
def get_article(soup):
    return soup.find("article") or soup

def get_real_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        t = p.get_text(" ", strip=True)
        if len(t) < 80:
            continue
        if re.search(r"(photo|agency|advertisement|read more)", t.lower()):
            continue
        paras.append(t)
    return paras

def get_real_images(article):
    imgs = []
    for img in article.find_all("img"):
        src = img.get("src","")
        if src and not any(x in src.lower() for x in ["logo","icon","sprite","ads"]):
            imgs.append(img)
    return imgs[:1]

def get_links(article, domain):
    internal = external = 0
    for a in article.find_all("a", href=True):
        if domain in a["href"]:
            internal += 1
        else:
            external += 1
    return internal, external

# ================= MAIN ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    article = get_article(soup)
    parsed = urlparse(url)

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else "No H1 Found"
    seo_title = generate_seo_title(title)

    paras = get_real_paragraphs(article)
    word_count = sum(len(p.split()) for p in paras)

    img_count = len(get_real_images(article))
    h1_count = len(article.find_all("h1"))
    h2_count = len(article.find_all("h2"))
    internal, external = get_links(article, parsed.netloc)

    slug = parsed.path.strip("/").lower()
    words = slug.split("-") if slug else []
    found_stop = sorted(set(w for w in words if w in STOP_WORDS))
    clean = clean_slug(slug)
    suggested_url = f"{parsed.scheme}://{parsed.netloc}/{clean}"

    score = calculate_seo_score(seo_title, url)

    rows = [
        ["Title Character Count", visible_len(title), "≤ 60", "❌" if visible_len(title) > 60 else "✅"],
        ["Suggested SEO Title", title, seo_title, "—"],
        ["Word Count", word_count, "250+", "❌" if word_count < 250 else "✅"],
        ["News Image Count", img_count, "1+", "❌" if img_count < 1 else "✅"],
        ["H1 Count", h1_count, "1", "❌" if h1_count != 1 else "✅"],
        ["H2 Count", h2_count, "2+", "❌" if h2_count < 2 else "✅"],
        ["Internal Links", internal, "2–10", "❌" if internal < 2 else "✅"],
        ["External Links", external, "0–2", "❌" if external > 2 else "✅"],

        ["Unnecessary Words", ", ".join(found_stop) if found_stop else "None", "No", "❌" if found_stop else "✅"],
        ["Suggested Clean SEO URL", suggested_url, "Clean URL", "—"],
        ["Title + URL SEO Score", f"{score} / 100", "≥ 80", "⚠️" if score < 80 else "✅"],
    ]

    return rows

# ================= SCORE TABLE =================
def seo_score_table():
    return pd.DataFrame([
        ["Title Length", "≤ 60 chars", 30],
        ["URL Length", "≤ 80 chars", 25],
        ["No Stop Words", "Clean slug", 20],
        ["Clear Topic", "≤ 10 words", 15],
        ["Lowercase + Hyphen", "Yes", 10],
        ["TOTAL", "", 100],
    ], columns=["Factor", "Condition", "Score"])

# ================= EXCEL =================
def format_excel(dfs):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for name, df in dfs.items():
            df.to_excel(writer, sheet_name=name, index=False)
    out.seek(0)
    return out

# ================= RUN =================
if analyze:
    urls = []
    if bulk_file:
        urls = [u.strip() for u in bulk_file.read().decode().splitlines() if u.strip()]
    elif single_url:
        urls = [single_url]

    all_rows = []
    for u in urls:
        all_rows.extend(analyze_url(u))

    df_main = pd.DataFrame(all_rows, columns=["Metric","Actual","Ideal","Verdict"])
    df_score = seo_score_table()

    st.subheader("📊 SEO Audit Report")
    st.dataframe(df_main, use_container_width=True)

    st.subheader("🧮 SEO Score Calculation Logic")
    st.dataframe(df_score, use_container_width=True)

    excel = format_excel({
        "SEO Audit Report": df_main,
        "SEO Score Logic": df_score
    })

    st.download_button(
        "⬇️ Download Combined SEO Excel",
        excel,
        "Final_SEO_Audit_Report.xlsx"
    )
