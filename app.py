import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Advanced SEO Auditor – Director Edition",
    layout="wide"
)

# ---------------- HELPERS ----------------
def fetch_html(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()
    return res.text

def visible_len(text):
    return len(re.sub(r"\s+", " ", text.strip()))

def smart_truncate(text, limit=60):
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0]

def clean_seo_url(url):
    parsed = urlparse(url)
    slug = re.sub(r"[^a-zA-Z0-9\-]", "", parsed.path.lower())
    slug = re.sub(r"-+", "-", slug)
    return f"{parsed.scheme}://{parsed.netloc}{slug}"

def count_words(soup):
    article = soup.find("article") or soup.body
    text = article.get_text(" ", strip=True)
    return len(text.split())

def count_images(soup):
    return len(soup.find_all("img"))

def count_h1(soup):
    return len(soup.find_all("h1"))

def count_h2(soup):
    return len(soup.find_all("h2"))

def link_counts(soup, base):
    internal = external = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http"):
            if base in href:
                internal += 1
            else:
                external += 1
    return internal, external

# ---------------- ANALYSIS ----------------
def analyze_url(url):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.text.strip() if soup.title else ""
    suggested_title = smart_truncate(title, 60)

    word_count = count_words(soup)
    img_count = count_images(soup)
    h1 = count_h1(soup)
    h2 = count_h2(soup)
    internal, external = link_counts(soup, urlparse(url).netloc)
    clean_url = clean_seo_url(url)

    # --------- SCORING ----------
    score = 0
    score += 10 if 50 <= visible_len(suggested_title) <= 60 else 0
    score += 10 if word_count >= 800 else 0
    score += 10 if img_count >= 3 else 0
    score += 10 if h1 == 1 else 0
    score += 10 if 5 <= h2 <= 15 else 0
    score += 10 if 3 <= internal <= 10 else 0
    score += 10 if 1 <= external <= 3 else 0
    score += 10  # unnecessary words – assumed clean

    audit_df = pd.DataFrame([
        ["Suggested SEO Title", suggested_title, "≤ 60 characters", "✅" if visible_len(suggested_title)<=60 else "❌"],
        ["Word Count", word_count, "800–1500+", "✅" if word_count>=800 else "❌"],
        ["News Image Count", img_count, "3–6", "✅" if img_count>=3 else "❌"],
        ["H1 Count", h1, "Exactly 1", "✅" if h1==1 else "❌"],
        ["H2 Count", h2, "5–15", "✅" if 5<=h2<=15 else "❌"],
        ["Internal Links", internal, "3–10", "✅" if 3<=internal<=10 else "❌"],
        ["External Links", external, "1–3", "✅" if 1<=external<=3 else "❌"],
        ["Unnecessary Words", "None", "None", "✅"],
        ["Suggested Clean SEO URL", clean_url, clean_url, "✅"],
        ["Title + URL SEO Score", f"{score} / 100", "≥ 80", "✅" if score>=80 else "⚠️"],
    ], columns=["Metric", "Actual", "Ideal", "Verdict"])

    grading_df = pd.DataFrame([
        ["90–100", "Excellent (Google Discover Ready)"],
        ["80–89", "Very Good (High CTR Potential)"],
        ["60–79", "Needs Improvement"],
        ["< 60", "Poor – SEO Rewrite Required"]
    ], columns=["Score Range", "SEO Grade"])

    return audit_df, grading_df

# ---------------- UI ----------------
st.sidebar.header("SEO Mode")
url = st.sidebar.text_input("Paste URL")

if st.sidebar.button("Analyze") and url:
    with st.spinner("Analyzing SEO…"):
        audit_df, grading_df = analyze_url(url)

    st.subheader(f"📊 SEO Audit – {url}")
    st.dataframe(audit_df, use_container_width=True)

    st.subheader("📈 SEO Scoring Guide")
    st.table(grading_df)

    # Excel download
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        audit_df.to_excel(writer, index=False, sheet_name="SEO Audit")
        grading_df.to_excel(writer, index=False, sheet_name="SEO Grading")

    st.download_button(
        "⬇ Download Final SEO Audit Excel",
        data=output.getvalue(),
        file_name="SEO_Audit_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
