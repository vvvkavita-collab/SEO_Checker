import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Advanced SEO Auditor – News & Blog", layout="wide")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ---------------- UI ----------------
st.title("🧠 Advanced SEO Auditor – News & Blog")

st.sidebar.title("SEO Mode")
SEO_MODE = st.sidebar.radio("Select Content Type", ["News Article", "Blog / Evergreen"])

urls_input = st.text_area("Paste URLs (one per line)", height=160)

# ---------------- CONTENT EXTRACTOR ----------------
def extract_article(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(r.text, "html.parser")

        # ---------- TITLE ----------
        title = soup.title.get_text(strip=True) if soup.title else ""

        # ---------- META ----------
        meta_tag = soup.find("meta", attrs={"name": "description"}) or \
                   soup.find("meta", attrs={"property": "og:description"})
        meta = meta_tag.get("content", "").strip() if meta_tag else ""

        # ---------- H1 ----------
        h1_tag = soup.find("h1")
        h1 = h1_tag.get_text(strip=True) if h1_tag else ""

        # ---------- ARTICLE BODY (MULTI FALLBACK) ----------
        article = (
            soup.find("article") or
            soup.find("div", itemprop="articleBody") or
            soup.find("div", class_=lambda x: x and "story" in x.lower())
        )

        if not article:
            return None

        # ---------- PARAGRAPHS ----------
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in article.find_all("p")
            if len(p.get_text(strip=True)) > 40
        ]

        if len(paragraphs) < 2:
            return None

        # ---------- WORD COUNT ----------
        word_count = len(" ".join(paragraphs).split())

        # ---------- IMAGES ----------
        images = article.find_all("img")
        img_count = len(images)
        alt_count = sum(1 for i in images if i.get("alt"))

        # ---------- H2 ----------
        h2_count = len(article.find_all("h2"))

        # ---------- LINKS ----------
        domain = urlparse(url).netloc
        internal = external = 0

        for a in article.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http"):
                if domain in href:
                    internal += 1
                else:
                    external += 1
            else:
                internal += 1

        return {
            "URL": url,
            "Title Length": len(title),
            "Meta Length": len(meta),
            "H1 Length": len(h1),
            "H2 Count": h2_count,
            "Word Count": word_count,
            "Paragraph Count": len(paragraphs),
            "Image Count": img_count,
            "Alt Tags": alt_count,
            "Internal Links": internal,
            "External Links": external
        }

    except Exception:
        return None

# ---------------- IDEAL RANGE ----------------
IDEAL = {
    "Word Count": "250+",
    "Paragraph Count": "4+",
    "Image Count": "1+",
    "Internal Links": "2–10",
    "External Links": "0–2",
    "Meta Length": "70–160",
    "H1 Length": "20–70",
    "H2 Count": "1–6"
}

def verdict(actual, key):
    rules = {
        "Word Count": actual >= 250,
        "Paragraph Count": actual >= 4,
        "Image Count": actual >= 1,
        "Internal Links": 2 <= actual <= 10,
        "External Links": actual <= 2,
        "Meta Length": 70 <= actual <= 160,
        "H1 Length": actual >= 20,
        "H2 Count": 1 <= actual <= 6
    }
    return "🟢 Good" if rules.get(key, False) else "🔴 Needs Fix"

# ---------------- SCORING ----------------
def score_news(d):
    score = 0
    score += 20 if d["Word Count"] >= 250 else 0
    score += 10 if d["Paragraph Count"] >= 4 else 0
    score += 10 if d["Image Count"] >= 1 else 0
    score += 10 if d["H1 Length"] >= 20 else 0
    score += 10 if 70 <= d["Meta Length"] <= 160 else 0
    score += 10 if 2 <= d["Internal Links"] <= 10 else 0
    score += 10 if d["External Links"] <= 2 else 0
    return score

def grade(score):
    if score >= 85: return "A+"
    if score >= 70: return "A"
    if score >= 55: return "B"
    if score >= 40: return "C"
    return "D"

# ---------------- ANALYZE ----------------
if st.button("Analyze"):
    rows = []

    for url in urls_input.splitlines():
        url = url.strip()
        if not url:
            continue

        data = extract_article(url)

        if not data:
            st.warning(f"⚠️ Content not detected: {url}")
            continue

        score = score_news(data)
        seo_grade = grade(score)

        for k in IDEAL:
            rows.append({
                "URL": url,
                "Metric": k,
                "Actual": data.get(k, 0),
                "Ideal": IDEAL[k],
                "Verdict": verdict(data.get(k, 0), k),
                "SEO Score": score,
                "SEO Grade": seo_grade
            })

    if not rows:
        st.error("No valid articles detected.")
    else:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        # -------- EXCEL --------
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="SEO_Audit")

            explain = pd.DataFrame({
                "Heading": ["Title", "Meta Description", "H1", "H2", "Images", "Internal Links"],
                "Why Important": [
                    "Search relevance",
                    "CTR in Google",
                    "Main topic clarity",
                    "Content structure",
                    "User engagement",
                    "SEO crawl strength"
                ],
                "If Correct": [
                    "Higher ranking",
                    "More clicks",
                    "Clear topic",
                    "Better readability",
                    "Lower bounce",
                    "Better indexing"
                ],
                "If Wrong": [
                    "Ranking loss",
                    "Low CTR",
                    "Topic confusion",
                    "Poor UX",
                    "Low engagement",
                    "Weak SEO"
                ]
            })
            explain.to_excel(writer, index=False, sheet_name="SEO_Why_It_Matters")

        st.download_button(
            "📥 Download SEO Report",
            output.getvalue(),
            file_name="SEO_Audit_Report.xlsx"
        )
