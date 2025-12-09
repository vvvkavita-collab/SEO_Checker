import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font
import os

# -------------------------
# Config
# -------------------------
st.set_page_config(
    page_title="Patrika (SEO CHECKER)",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={}
)

# -------------------------
# Simple Password Protect + Logout
# -------------------------
PASSWORD = "Patrika@2025"
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

def login_block():
    st.markdown("<h3 style='color:#bfe9ff;'>🔒 Patrika (SEO CHECKER) — Internal Login</h3>", unsafe_allow_html=True)
    pw = st.text_input("Enter password", type="password", key="pw_input")
    if pw:
        if pw == PASSWORD:
            st.session_state["logged_in"] = True
            st.session_state.pop("pw_input", None)
            st.experimental_rerun()
        else:
            st.error("Incorrect password")

if not st.session_state["logged_in"]:
    login_block()
    st.stop()

# logout UI
col_l, col_r = st.columns([1, 6])
with col_l:
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        # clear other session state items if any
        for k in list(st.session_state.keys()):
            if k not in ("logged_in",):
                try:
                    del st.session_state[k]
                except:
                    pass
        st.experimental_rerun()

# -------------------------
# Premium CSS
# -------------------------
st.markdown("""
<style>
/* Hide defaults */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* App background & fonts */
.stApp {
    background: linear-gradient(135deg, #071226, #102032);
    color: white !important;
    font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial;
}

/* Headings forced white + bolder */
h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
    font-weight: 700 !important;
    text-shadow: 0 2px 12px rgba(0,0,0,0.6);
}

/* Uploader card */
div[data-testid="stFileUploader"] {
    background: linear-gradient(180deg, rgba(20,30,45,0.7), rgba(12,20,30,0.6)) !important;
    padding: 16px;
    border-radius: 12px;
    border: 2px dashed rgba(79,129,189,0.35) !important;
    color: white !important;
}

/* Uploader label visible blue */
.stFileUploader label, .stFileUploader .uploading, .stFileUploader .stMarkdown p {
    color: #1E90FF !important;
    font-weight: 600;
}

/* Inputs & Text Area */
.stTextArea textarea, .stTextInput input {
    background: #0f1720 !important;
    color: #dbefff !important;
    border: 1px solid rgba(79,195,247,0.12) !important;
    border-radius: 8px !important;
}

/* Buttons */
div.stButton > button {
    background: linear-gradient(90deg,#1177bb,#39b0ff) !important;
    color: white !important;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
    box-shadow: 0 6px 18px rgba(56,140,200,0.18);
}
div.stButton > button:hover {
    box-shadow: 0 10px 30px rgba(56,140,200,0.28);
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# Logo
# -------------------------
logo_local = "patrika_logo.png"
logo_fallback = "https://upload.wikimedia.org/wikipedia/commons/9/98/Patrika_logo.png"
try:
    if os.path.exists(logo_local):
        st.image(logo_local, width=140)
    else:
        st.image(logo_fallback, width=140)
except Exception:
    pass

st.markdown("<h1>Patrika (SEO CHECKER) — Internal Tool</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#cfeeff;'>URL Analysis → Audit Excel → SEO Guidelines (All values show Ideal vs Actual for easy review)</p>", unsafe_allow_html=True)

# -------------------------
# Helper functions
# -------------------------
def safe_get_text(tag):
    try:
        return tag.get_text(" ", strip=True)
    except:
        return ""

def trim_text(val, limit=20):
    try:
        s = str(val)
        return s if len(s) <= limit else s[:limit] + "..."
    except:
        return val

def char_count(s):
    return len(s) if s is not None else 0

def word_count(s):
    if s is None:
        return 0
    # treat multiple spaces and punctuations
    tokens = re.findall(r'\S+', str(s))
    return len(tokens)

# -------------------------
# Article extractor (keeps article text & article word count)
# -------------------------
def extract_article(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        meta_desc = ""
        md = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if md and md.get("content"):
            meta_desc = md.get("content").strip()

        paras = soup.find_all("p")
        article = " ".join([safe_get_text(p) for p in paras]).strip()
        article = re.sub(r"\s+", " ", article)

        h1_list = [safe_get_text(t) for t in soup.find_all("h1")]
        h2_list = [safe_get_text(t) for t in soup.find_all("h2")]

        imgs = soup.find_all("img")
        img_count = len(imgs)
        alt_with = sum(1 for im in imgs if (im.get("alt") or "").strip())

        anchors = soup.find_all("a")
        internal_links = 0
        external_links = 0
        domain = urlparse(url).netloc.lower()
        for a in anchors:
            href = a.get("href") or ""
            if href.startswith("#") or href.startswith("mailto:") or href.strip() == "":
                continue
            parsed = urlparse(href)
            if parsed.netloc and parsed.netloc.lower() != domain:
                external_links += 1
            else:
                internal_links += 1

        paragraph_count = len([p for p in paras if safe_get_text(p)])
        sentences = re.split(r"[.!?]\s+", article)
        sentence_count = len([s for s in sentences if s.strip()])
        words = article.split()
        word_count_total = len(words)
        avg_words_per_sentence = round(word_count_total / max(1, sentence_count), 2)

        summary = ""
        if sentence_count >= 1:
            summary = ". ".join(sentence.strip() for sentence in sentences[:2]).strip()
            if summary and not summary.endswith("."):
                summary += "."

        return {
            "title": title,
            "meta": meta_desc,
            "article": article,
            "h1_list": h1_list,
            "h2_list": h2_list,
            "img_count": img_count,
            "alt_with": alt_with,
            "internal_links": internal_links,
            "external_links": external_links,
            "paragraph_count": paragraph_count,
            "sentence_count": sentence_count,
            "word_count": word_count_total,
            "avg_words_per_sentence": avg_words_per_sentence,
            "summary": summary,
        }
    except Exception:
        return {
            "title": "",
            "meta": "",
            "article": "",
            "h1_list": [],
            "h2_list": [],
            "img_count": 0,
            "alt_with": 0,
            "internal_links": 0,
            "external_links": 0,
            "paragraph_count": 0,
            "sentence_count": 0,
            "word_count": 0,
            "avg_words_per_sentence": 0,
            "summary": "",
        }

# -------------------------
# SEO ideal values (defaults)
# -------------------------
IDEALS = {
    "title_chars": (50, 60),
    "title_words": (6, 10),
    "meta_chars": (130, 160),
    "meta_words": (20, 30),
    "h1_words": (6, 10),
    "h2_words": (6, 14),
    "content_words": (600, 1200),
    "paragraphs": (8, 12),
    "url_chars": (0, 75),   # ideal: less than 75
    "image_alt_ratio": (1, 1),  # ideally all images have alt (actual alt_with == img_count)
}

def in_range(val, rng):
    if val is None:
        return False
    low, high = rng
    try:
        v = float(val)
    except:
        return False
    return low <= v <= high

def status_text(actual, ideal_range, kind="num"):
    # kind not used right now but can be for special messages
    low, high = ideal_range
    try:
        v = float(actual)
    except:
        return "Check"
    if low <= v <= high:
        return "OK"
    else:
        return "Improve"

# -------------------------
# UI Inputs
# -------------------------
uploaded = st.file_uploader("Upload URL List (TXT/CSV/XLSX)", type=["txt", "csv", "xlsx"])
urls_input = st.text_area("Paste URLs here (one per line)", height=200)

# merge uploaded into text area if uploaded
if uploaded is not None:
    try:
        if uploaded.type == "text/plain":
            content = uploaded.read().decode("utf-8", errors="ignore")
            st.session_state["uploaded_urls"] = "\n".join([l.strip() for l in content.splitlines() if l.strip()])
        elif uploaded.type == "text/csv" or uploaded.name.lower().endswith(".csv"):
            df_tmp = pd.read_csv(uploaded, header=None)
            st.session_state["uploaded_urls"] = "\n".join(df_tmp.iloc[:,0].astype(str).str.strip())
        else:
            df_tmp = pd.read_excel(uploaded, header=None)
            st.session_state["uploaded_urls"] = "\n".join(df_tmp.iloc[:,0].astype(str).str.strip())
        st.info("File processed. Merged into the text area below.")
        existing = urls_input.strip()
        merged = (existing + "\n" + st.session_state.get("uploaded_urls", "")).strip() if existing else st.session_state.get("uploaded_urls", "")
        urls_input = merged
    except Exception as e:
        st.error(f"Failed to read uploaded file: {e}")

process = st.button("Process & Create Excel")

# -------------------------
# Processing
# -------------------------
if process:
    if not urls_input.strip():
        st.error("Please paste some URLs or upload a file.")
    else:
        urls = [u.strip() for u in urls_input.splitlines() if u.strip()]
        rows = []
        pairs_reference = None

        progress = st.progress(0)
        status_box = st.empty()

        for i, url in enumerate(urls, start=1):
            status_box.text(f"Processing {i}/{len(urls)} : {url}")
            data = extract_article(url)

            # Score + pairs from existing analysis
            score, grade, predicted, pairs, extras = 0, "", 0, [], {"Summary": data.get("summary","")}

            # Build item with many Ideal vs Actual fields
            title = data.get("title","")
            meta = data.get("meta","")
            article_text = data.get("article","")
            h1_list = data.get("h1_list", [])
            h2_list = data.get("h2_list", [])
            img_count = data.get("img_count", 0)
            alt_with = data.get("alt_with", 0)
            paragraph_count = data.get("paragraph_count", 0)
            content_words = data.get("word_count", 0)

            # Title counts
            title_chars_actual = char_count(title)
            title_words_actual = word_count(title)
            title_chars_ideal = f"{IDEALS['title_chars'][0]}–{IDEALS['title_chars'][1]}"
            title_words_ideal = f"{IDEALS['title_words'][0]}–{IDEALS['title_words'][1]}"
            title_chars_status = status_text(title_chars_actual, IDEALS['title_chars'])
            title_words_status = status_text(title_words_actual, IDEALS['title_words'])

            # Meta counts
            meta_chars_actual = char_count(meta)
            meta_words_actual = word_count(meta)
            meta_chars_ideal = f"{IDEALS['meta_chars'][0]}–{IDEALS['meta_chars'][1]}"
            meta_words_ideal = f"{IDEALS['meta_words'][0]}–{IDEALS['meta_words'][1]}"
            meta_chars_status = status_text(meta_chars_actual, IDEALS['meta_chars'])
            meta_words_status = status_text(meta_words_actual, IDEALS['meta_words'])

            # H1 / H2 (use first items if present)
            h1_text = h1_list[0] if h1_list else ""
            h2_text = h2_list[0] if h2_list else ""
            h1_words_actual = word_count(h1_text)
            h2_words_actual = word_count(h2_text)
            h1_words_ideal = f"{IDEALS['h1_words'][0]}–{IDEALS['h1_words'][1]}"
            h2_words_ideal = f"{IDEALS['h2_words'][0]}–{IDEALS['h2_words'][1]}"
            h1_status = status_text(h1_words_actual, IDEALS['h1_words'])
            h2_status = status_text(h2_words_actual, IDEALS['h2_words'])

            # Content / Article
            content_words_actual = content_words
            content_words_ideal = f"{IDEALS['content_words'][0]}–{IDEALS['content_words'][1]}"
            content_status = status_text(content_words_actual, IDEALS['content_words'])

            # Paragraph count
            paragraph_actual = paragraph_count
            paragraph_ideal = f"{IDEALS['paragraphs'][0]}–{IDEALS['paragraphs'][1]}"
            paragraph_status = status_text(paragraph_actual, IDEALS['paragraphs'])

            # URL length
            url_chars_actual = char_count(url)
            url_chars_ideal = f"< {IDEALS['url_chars'][1]}"
            url_status = "OK" if url_chars_actual <= IDEALS['url_chars'][1] else "Improve"

            # Image ALT ratio / actual
            image_alt_actual = f"{alt_with}/{img_count}"
            image_alt_ideal = "All images should have ALT"
            image_alt_status = "OK" if img_count == alt_with else "Improve"

            # Summary trimmed
            summary_trimmed = trim_text(extras.get("Summary",""), 20)

            # build row dict
            row = {
                "URL": url,
                # Title
                "Title (Chars) Actual": title_chars_actual,
                "Title (Chars) Ideal": title_chars_ideal,
                "Title (Chars) Status": title_chars_status,
                "Title (Words) Actual": title_words_actual,
                "Title (Words) Ideal": title_words_ideal,
                "Title (Words) Status": title_words_status,
                # Meta
                "Meta (Chars) Actual": meta_chars_actual,
                "Meta (Chars) Ideal": meta_chars_ideal,
                "Meta (Chars) Status": meta_chars_status,
                "Meta (Words) Actual": meta_words_actual,
                "Meta (Words) Ideal": meta_words_ideal,
                "Meta (Words) Status": meta_words_status,
                # H1
                "H1 Text": h1_text,
                "H1 (Words) Actual": h1_words_actual,
                "H1 (Words) Ideal": h1_words_ideal,
                "H1 (Words) Status": h1_status,
                # H2
                "H2 Text": h2_text,
                "H2 (Words) Actual": h2_words_actual,
                "H2 (Words) Ideal": h2_words_ideal,
                "H2 (Words) Status": h2_status,
                # Content
                "Content (Words) Actual": content_words_actual,
                "Content (Words) Ideal": content_words_ideal,
                "Content (Words) Status": content_status,
                # Paragraph
                "Paragraph (Actual)": paragraph_actual,
                "Paragraph (Ideal)": paragraph_ideal,
                "Paragraph (Status)": paragraph_status,
                # URL length
                "URL (Chars) Actual": url_chars_actual,
                "URL (Chars) Ideal": url_chars_ideal,
                "URL (Chars) Status": url_status,
                # Images / ALT
                "Images Count": img_count,
                "Image ALT Actual": image_alt_actual,
                "Image ALT Ideal": image_alt_ideal,
                "Image ALT Status": image_alt_status,
                # Summary (trimmed)
                "Summary": summary_trimmed,
            }

            rows.append(row)
            progress.progress(int((i / len(urls)) * 100))

        # build dataframe
        df = pd.DataFrame(rows)

        # show preview
        st.subheader("Preview (Ideal vs Actual)")
        st.dataframe(df)

        # Excel export
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Audit")
            wb_in_writer = writer.book
            ws_g = wb_in_writer.create_sheet("SEO Guidelines")
            ws_g.append(["Parameter", "Meaning / Purpose", "Ideal Range", "Why Important"])
            guidelines = [
                ("Title Length (chars)", "Main headline length", "50–60 chars", "CTR + SERP display"),
                ("Title Words", "Words in title", "6–10 words", "Readable + CTR"),
                ("Meta Description", "Search snippet", "130–160 chars", "CTR improvement"),
                ("H1 Count", "Main heading", "1", "Topic clarity"),
                ("H2 Count", "Subheadings", "2–5", "Readability + SEO"),
                ("Content Length", "Total words", "600–1200 words", "Depth of content"),
                ("Paragraph Count", "Sections", "8–12", "User experience"),
                ("Images", "Visuals", "3+ recommended", "Engagement"),
                ("Alt Tags", "Image alt text", "Every image", "Image SEO"),
            ]
            for r in guidelines:
                ws_g.append(r)
            for col in ws_g.columns:
                ws_g.column_dimensions[col[0].column_letter].width = 25

        # Apply Excel formatting + trim summary again for safety
        final_bytes = apply_excel_formatting(out.getvalue())

        st.success("🎉 Excel created successfully!")
        st.download_button(
            "Download Patrika SEO Audit (Excel)",
            data=final_bytes,
            file_name="Patrika_SEO_Audit.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
