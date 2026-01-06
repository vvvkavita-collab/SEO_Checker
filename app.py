# ================= IMPORTS =================
import streamlit as st
import pandas as pd
import requests
import re, json, unicodedata
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ================= CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor – Google News + Gemini", layout="wide")
st.title("🧠 Advanced SEO Auditor (Audit + Score + Gemini + CTR)")

HEADERS = {"User-Agent": "Mozilla/5.0"}
GEMINI_API_KEY = "PASTE_YOUR_API_KEY_HERE"

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
bulk_file = st.sidebar.file_uploader("Upload URLs (TXT / CSV)", type=["txt", "csv"])
url_input = st.text_input("Paste URL")
analyze = st.button("Analyze")

# ================= WORD LISTS =================
TITLE_STOP_WORDS = ["breaking","exclusive","viral","shocking","alert"]
URL_STOP_WORDS = ["news","latest","update","today","information","story"]
POWER_WORDS = ["how","why","what","top","big","revealed","exclusive"]

# ================= HELPERS =================
def visible_len(text):
    return sum(1 for c in text if not unicodedata.category(c).startswith("C"))

def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def safe_text(el):
    return el.get_text(" ", strip=True) if el else ""

# ================= GEMINI =================
def fetch_gemini_titles(title):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
Generate 5 SEO friendly Google News headlines.
Rules:
- 55 to 65 characters
- No clickbait
- Professional news tone
Title:
{title}
"""
    payload = {"contents":[{"parts":[{"text":prompt}]}]}
    r = requests.post(url, json=payload, timeout=30)
    data = r.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return [t.strip("- ").strip() for t in text.split("\n") if len(t.strip()) > 15]

# ================= CTR SCORE =================
def ctr_score(title):
    score = 50
    l = visible_len(title)
    if 55 <= l <= 65: score += 20
    if any(w in title.lower() for w in POWER_WORDS): score += 10
    if re.search(r"\d", title): score += 10
    if "?" in title: score += 5
    return min(score, 100)

# ================= SCORE LOGIC =================
def calculate_score(title_len, word_count, img_count):
    score = 100
    if title_len < 55 or title_len > 70: score -= 12
    if word_count < 300: score -= 12
    if img_count < 1: score -= 10
    return max(score, 0)

# ================= ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    article = soup.find("article") or soup
    title_tag = soup.find("h1") or soup.find("title")
    title = safe_text(title_tag)

    title_len = visible_len(title)
    word_count = sum(len(p.get_text().split()) for p in article.find_all("p"))
    img_count = len(article.find_all("img"))

    final_score = calculate_score(title_len, word_count, img_count)

    audit_df = pd.DataFrame([
        ["Title Length", title_len, "55–70", "✅" if 55 <= title_len <= 70 else "⚠️"],
        ["Word Count", word_count, "300+", "✅" if word_count >= 300 else "⚠️"],
        ["Image Count", img_count, "1+", "✅" if img_count >= 1 else "⚠️"],
        ["Final SEO Score", f"{final_score}/100", "≥80", "✅" if final_score >= 80 else "⚠️"],
    ], columns=["Metric","Actual","Ideal","Verdict"])

    grading_df = pd.DataFrame([
        ["Base Score",100],
        ["Title Issue",-12 if title_len < 55 or title_len > 70 else 0],
        ["Low Word Count",-12 if word_count < 300 else 0],
        ["No Image",-10 if img_count < 1 else 0],
        ["Final Score",final_score],
    ], columns=["Scoring Rule","Value"])

    # Gemini + CTR
    gemini_titles = fetch_gemini_titles(title)
    ctr_rows = [(t, ctr_score(t)) for t in gemini_titles]
    ctr_rows.sort(key=lambda x: x[1], reverse=True)
    ctr_df = pd.DataFrame(ctr_rows, columns=["Suggested Headline","CTR Score"])

    return audit_df, grading_df, ctr_df

# ================= RUN =================
urls = []
if bulk_file:
    raw = bulk_file.read().decode("utf-8", errors="ignore")
    urls.extend([l.strip() for l in raw.splitlines() if l.strip()])
if url_input:
    urls.append(url_input.strip())

all_audit, all_grading = [], []

if analyze and urls:
    for u in urls:
        st.subheader(f"🔍 SEO Audit – {u}")
        audit_df, grading_df, ctr_df = analyze_url(u)

        st.dataframe(audit_df, use_container_width=True)
        st.subheader("📐 SEO Score Logic")
        st.dataframe(grading_df, use_container_width=True)

        st.subheader("✨ Gemini Headlines (CTR Based)")
        st.dataframe(ctr_df, use_container_width=True)

        best_title = ctr_df.iloc[0]["Suggested Headline"]
        st.code(best_title)
        st.button("📋 Copy Best Title", key=u)

        audit_df.insert(0,"URL",u)
        grading_df.insert(0,"URL",u)
        all_audit.append(audit_df)
        all_grading.append(grading_df)

    excel = BytesIO()
    with pd.ExcelWriter(excel, engine="openpyxl") as writer:
        pd.concat(all_audit).to_excel(writer, sheet_name="SEO Audit", index=False)
        pd.concat(all_grading).to_excel(writer, sheet_name="Score Logic", index=False)

    excel.seek(0)
    st.download_button("⬇️ Download SEO Audit Excel", excel, "SEO_Audit_Final.xlsx")
