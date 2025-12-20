import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Advanced SEO Auditor", layout="wide")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ---------------- UI ----------------
st.title("🧠 Advanced SEO Auditor – News & Blog")

st.sidebar.title("SEO Mode")
SEO_MODE = st.sidebar.radio("Select Content Type", ["News Article", "Blog / Evergreen"])

urls_input = st.text_area("Paste URLs (one per line)", height=150)

# ---------------- CORE EXTRACTION ----------------
def extract_article(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")

        # ----- TITLE & META -----
        title = soup.title.text.strip() if soup.title else ""
        meta = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta["content"].strip() if meta else ""

        # ----- H1 -----
        h1 = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""

        # ----- MAIN CONTENT (PATRiKA SAFE) -----
        story_box = soup.find("div", class_="storyDetail")
        story = story_box.find("div", class_="storyContent") if story_box else None
        if not story:
            return None

        paragraphs = [
            p.get_text(" ", strip=True)
            for p in story.find_all("p")
            if len(p.get_text(strip=True)) > 40
        ]

        images = story.find_all("img")
        alt_count = sum(1 for img in images if img.get("alt"))

        h2s = story.find_all("h2")

        domain = urlparse(url).netloc
        internal = external = 0
        for a in story.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http"):
                if domain in href:
                    internal += 1
                else:
                    external += 1
            else:
                internal += 1

        words = " ".join(paragraphs).split()

        return {
            "URL": url,
            "Title Length": len(title),
            "Meta Length": len(meta_desc),
            "H1 Length": len(h1),
            "H2 Count": len(h2s),
            "Word Count": len(words),
            "Paragraph Count": len(paragraphs),
            "Image Count": len(images),
            "Alt Tags": alt_count,
            "Internal Links": internal,
            "External Links": external
        }

    except:
        return None

# ---------------- SCORING ----------------
def score_news(d):
    if not d:
        return 0

    score = 0
    score += 15 if d["Word Count"] >= 250 else 0
    score += 10 if d["Paragraph Count"] >= 4 else 0
    score += 10 if d["Image Count"] >= 1 else 0
    score += 10 if d["H1 Length"] >= 20 else 0
    score += 10 if d["Meta Length"] >= 70 else 0
    return score

def seo_grade(score):
    if score >= 85: return "A+"
    if score >= 70: return "A"
    if score >= 55: return "B"
    if score >= 40: return "C"
    return "D"

# ---------------- IDEAL RANGE ----------------
IDEAL = {
    "Word Count": "250+",
    "Paragraph Count": "4+",
    "Image Count": "1+",
    "Internal Links": "2–10",
    "External Links": "0–2",
    "Meta Length": "70–160",
    "H1 Length": "20–70"
}

def verdict(actual, key):
    if key == "Internal Links":
        return "✅" if 2 <= actual <= 10 else "❌"
    if key == "External Links":
        return "✅" if actual <= 2 else "❌"
    if key == "Meta Length":
        return "✅" if 70 <= actual <= 160 else "❌"
    if key == "H1 Length":
        return "✅" if actual >= 20 else "❌"
    if key == "Word Count":
        return "✅" if actual >= 250 else "❌"
    if key == "Paragraph Count":
        return "✅" if actual >= 4 else "❌"
    if key == "Image Count":
        return "✅" if actual >= 1 else "❌"
    return "❌"

# ---------------- ANALYZE ----------------
if st.button("Analyze"):
    rows = []

    for url in urls_input.splitlines():
        url = url.strip()
        if not url:
            continue

        data = extract_article(url)
        if not data:
            st.warning(f"Content not detected: {url}")
            continue

        score = score_news(data) if SEO_MODE == "News Article" else score_news(data)
        grade = seo_grade(score)

        for k in IDEAL:
            rows.append({
                "URL": url,
                "Metric": k,
                "Actual": data.get(k, 0),
                "Ideal": IDEAL[k],
                "Verdict": verdict(data.get(k, 0), k),
                "SEO Score": score,
                "SEO Grade": grade
            })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    # ---------------- EXCEL DOWNLOAD ----------------
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="SEO Audit")

        edu = pd.DataFrame({
            "Heading": ["H1", "H2", "Meta Description"],
            "Why Important": [
                "Primary topic for Google",
                "Content structure & clarity",
                "CTR & search snippet"
            ],
            "If Correct": [
                "Better ranking relevance",
                "Improved readability",
                "Higher click-through"
            ],
            "If Wrong": [
                "Ranking confusion",
                "Poor UX",
                "Low CTR"
            ]
        })
        edu.to_excel(writer, index=False, sheet_name="SEO Education")

    st.download_button(
        "📥 Download SEO Report",
        output.getvalue(),
        file_name="SEO_Audit_Report.xlsx"
    )
