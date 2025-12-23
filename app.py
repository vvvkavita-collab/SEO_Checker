import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re
import json
import unicodedata
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor – Google Guidelines", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog (Google Ready)")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
bulk_file = st.sidebar.file_uploader("Upload Bulk URLs (TXT / CSV)", type=["txt", "csv"])
url_input = st.text_input("Paste URL")
analyze = st.button("Analyze")

# ================= STOP WORDS =================
TITLE_STOP_WORDS = [
    "breaking", "exclusive", "shocking", "must read", "update", "alert"
]

URL_STOP_WORDS = [
    "for", "today", "latest", "news", "update", "information",
    "details", "story", "article", "this", "that", "here", "now"
]

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_article(soup):
    return (
        soup.find("article")
        or soup.find("div", class_=re.compile("content|story|article|post-body", re.I))
        or soup
    )

def visible_len(text):
    return sum(1 for c in text if not unicodedata.category(c).startswith("C"))

def safe_text(el):
    return el.get_text(" ", strip=True) if el else ""

def get_real_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) < 80:
            continue
        if re.search(r"(advertisement|also read|read more|inputs|agency)", text, re.I):
            continue
        paras.append(text)
    return paras

def get_real_images(article):
    imgs = []
    for fig in article.find_all("figure"):
        img = fig.find("img")
        if img and img.get("src"):
            if not re.search(r"(logo|icon|sprite|ads)", img["src"], re.I):
                imgs.append(img)
    if not imgs:
        for img in article.find_all("img"):
            if img.get("src") and "featured" in " ".join(img.get("class", [])):
                imgs.append(img)
    return imgs[:1]

def get_links(article, domain):
    internal = external = 0
    for p in article.find_all("p"):
        for a in p.find_all("a", href=True):
            h = a["href"].strip()
            if h.startswith("#") or "javascript" in h:
                continue
            if h.startswith("http"):
                if domain in h:
                    internal += 1
                else:
                    external += 1
            else:
                internal += 1
    return internal, external

def get_h2_count_fixed(article):
    h2s = article.find_all("h2")
    real = []
    for idx, h2 in enumerate(h2s):
        t = h2.get_text(strip=True)
        if idx == 0 and len(t) > 100:
            continue
        if len(t) < 20:
            continue
        if re.search(r"(advertisement|related|subscribe|promo)", t, re.I):
            continue
        real.append(h2)
    return len(real)

def generate_seo_title(title, max_len=70):
    if visible_len(title) <= max_len:
        return title
    words = title.split()
    out = ""
    for w in words:
        test = (out + " " + w).strip()
        if visible_len(test) > max_len:
            break
        out = test
    return out

# ================= URL CLEAN LOGIC =================
def get_url_words(url):
    path = urlparse(url).path
    path = re.sub(r"[^a-zA-Z0-9\-]", "", path)
    return [w for w in path.lower().strip("/").split("-") if w]

def detect_unnecessary_url_words(url):
    words = get_url_words(url)
    safe_patterns = [
        r"jobs-for-(women|students|farmers)",
        r"scheme-for-(women|students|farmers)",
        r"scholarship-for-(students|girls)"
    ]
    joined = "-".join(words)
    for p in safe_patterns:
        if re.search(p, joined):
            return []

    return [w for w in words if w in URL_STOP_WORDS]

# ================= SCORE LOGIC =================
def calculate_score(title_len, word_count, img_count, h1_count, h2_count,
                    internal_links, external_links, has_stop_title,
                    has_schema, amp_flag, url_clean_flag, meta_image):
    score = 100
    if title_len > 70 or title_len < 55: score -= 12
    if word_count < 300: score -= 12
    if img_count < 1: score -= 10
    if not meta_image: score -= 5
    if h1_count != 1: score -= 10
    if h2_count < 2: score -= 8
    if internal_links < 2 or internal_links > 10: score -= 5
    if external_links > 2: score -= 4
    if has_stop_title: score -= 6
    if not has_schema: score -= 10
    if not amp_flag: score -= 3
    if not url_clean_flag: score -= 5
    return max(score, 0)

def extract_meta_image(soup):
    og = soup.find("meta", property="og:image")
    tw = soup.find("meta", property="twitter:image")
    return og["content"] if og and og.get("content") else (tw["content"] if tw and tw.get("content") else None)

def extract_json_ld(soup):
    scripts = soup.find_all("script", type="application/ld+json")
    out = []
    for s in scripts:
        try:
            out.append(json.loads(s.string))
        except:
            pass
    return out

def has_newsarticle_schema(json_ld_list):
    for jd in json_ld_list:
        if isinstance(jd, dict) and jd.get("@type") == "NewsArticle":
            return True
        if isinstance(jd, list):
            for i in jd:
                if isinstance(i, dict) and i.get("@type") == "NewsArticle":
                    return True
    return False

def is_amp(soup):
    return bool(soup.find("link", rel="amphtml"))

# ================= EXCEL FORMAT =================
def format_excel(sheets):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    output.seek(0)
    wb = load_workbook(output)
    for ws in wb.worksheets:
        header_fill = PatternFill("solid", fgColor="D9EAF7")
        bold = Font(bold=True)
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        for col in ws.columns:
            max_len = max(len(str(c.value)) if c.value else 0 for c in col)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 3, 40)
        for cell in ws[1]:
            cell.font = bold
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                cell.border = border
        ws.sheet_view.showGridLines = False
    final = BytesIO()
    wb.save(final)
    final.seek(0)
    return final

# ================= ANALYSIS =================
def analyze_url(url):
    try:
        soup = get_soup(url)
    except Exception as e:
        return pd.DataFrame([["Error", str(e), "-", "❌"]], columns=["Metric","Actual","Ideal","Verdict"]), pd.DataFrame([["Final Score", 0]], columns=["Scoring Rule","Value"])

    article = get_article(soup)
    domain = urlparse(url).netloc

    title_tag = soup.find("h1") or soup.find("title")
    title = safe_text(title_tag)

    seo_title = generate_seo_title(title)
    title_len = visible_len(title)

    paragraphs = get_real_paragraphs(article)
    word_count = sum(len(p.split()) for p in paragraphs)

    img_count = len(get_real_images(article))
    meta_image = extract_meta_image(soup)

    h1_count = len(article.find_all("h1")) or len(soup.find_all("h1"))
    h2_count = get_h2_count_fixed(article)

    internal, external = get_links(article, domain)

    found_title_stop = [w for w in TITLE_STOP_WORDS if w in title.lower()]
    found_url_stop = detect_unnecessary_url_words(url)

    json_ld = extract_json_ld(soup)
    schema_flag = has_newsarticle_schema(json_ld)
    amp_flag = is_amp(soup)

    url_clean_flag = not bool(found_url_stop)

    score = calculate_score(
        title_len, word_count, img_count, h1_count, h2_count,
        internal, external, bool(found_title_stop),
        schema_flag, amp_flag, url_clean_flag, meta_image
    )

    # --- AUDIT TABLE ---
    audit_df = pd.DataFrame([
        ["Title Character Count", title_len, "55–70", "✅" if 55 <= title_len <= 70 else "⚠️"],
        ["Suggested SEO Title", title, seo_title, "—"],
        ["Word Count", word_count, "300+", "✅" if word_count >= 300 else "⚠️"],
        ["News Image Count", img_count, "1+", "✅" if img_count >= 1 else "⚠️"],
        ["Meta Image", meta_image or "None", "Present", "✅" if meta_image else "⚠️"],
        ["H1 Count", h1_count, "1", "✅" if h1_count == 1 else "⚠️"],
        ["H2 Count", h2_count, "2+", "✅" if h2_count >= 2 else "⚠️"],
        ["Internal Links", internal, "2–10", "✅" if 2 <= internal <= 10 else "⚠️"],
        ["External Links", external, "0–2", "✅" if external <= 2 else "⚠️"],
        ["Unnecessary Words (Title)", ", ".join(found_title_stop) or "None", "No", "⚠️" if found_title_stop else "✅"],
        ["Unnecessary Words (URL)", ", ".join(found_url_stop) or "None", "No", "⚠️" if found_url_stop else "✅"],
        ["Structured Data", "Yes" if schema_flag else "No", "Yes", "✅" if schema_flag else "⚠️"],
        ["AMP Presence", "Yes" if amp_flag else "No", "Optional", "ℹ️"],
        ["Final SEO Score", f"{score}/100", "≥80", "✅" if score >= 80 else "⚠️"],
    ], columns=["Metric", "Actual", "Ideal", "Verdict"])

    # --- SCORE LOGIC TABLE ---
    grading_df = pd.DataFrame([
        ["Base Score", 100],
        ["Title outside 55–70", -12 if title_len < 55 or title_len > 70 else 0],
        ["Word Count < 300", -12 if word_count < 300 else 0],
        ["News Image Count < 1", -10 if img_count < 1 else 0],
        ["No Meta Image", -5 if not meta_image else 0],
        ["H1 Count != 1", -10 if h1_count != 1 else 0],
        ["H2 Count < 2", -8 if h2_count < 2 else 0],
        ["Internal Links out of range", -5 if internal < 2 or internal > 10 else 0],
        ["External Links > 2", -4 if external > 2 else 0],
        ["Unnecessary Words in Title", -6 if found_title_stop else 0],
        ["Unnecessary Words in URL", -5 if found_url_stop else 0],
        ["No NewsArticle schema", -10 if not schema_flag else 0],
        ["No AMP", -3 if not amp_flag else 0],
        ["Final Score", score]
    ], columns=["Scoring Rule","Value"])

    return audit_df, grading_df

# ================= RUN =================
urls = []
if bulk_file:
    try:
        raw = bulk_file.read().decode("utf-8", errors="ignore")
        if bulk_file.name.lower().endswith(".csv"):
            df_bulk = pd.read_csv(BytesIO(raw.encode("utf-8")), header=None)
            urls = [str(x).strip() for x in df_bulk.iloc[:,0].tolist() if str(x).strip()]
        else:
            urls = [l.strip() for l in raw.splitlines() if l.strip()]
    except Exception:
        st.error("Could not read bulk file. Make sure it's a simple TXT/CSV with URLs.")
if url_input:
    urls.append(url_input.strip())

if analyze and urls:
    all_audit = []
    all_grading = []

    for idx, u in enumerate(urls, start=1):
        st.subheader(f"📊 SEO Audit – {u}")
        audit_df, grading_df = analyze_url(u)
        st.dataframe(audit_df, use_container_width=True)
        st.subheader("📐 SEO Score / Grading Logic")
        st.dataframe(grading_df, use_container_width=True)

        audit_df.insert(0, "URL", u)
        grading_df.insert(0, "URL", u)
        all_audit.append(audit_df)
        all_grading.append(grading_df)

    # --- Excel Export ---
    EXPLANATIONS = pd.DataFrame([
        ["Title Character Count", "Title length should be 55–70 chars for Google SERP", "Correct → CTR increases, snippet fully visible"],
        ["Word Count", "Content depth", "300+ words considered informative by Google"],
        ["News Image Count", "Minimum 1 authentic image", "Improves Google Discover & CTR"],
        ["Meta Image", "Thumbnail for social/discover", "CTR & visibility improve"],
        ["H1 Count", "Main headline clarity", "1 H1 helps Google understand topic"],
        ["H2 Count", "Subheadings readability", "2+ H2 → structured content"],
        ["Internal Links", "Navigation + SEO juice", "2–10 links → better crawl & engagement"],
        ["External Links", "References & credibility", "≤2 → authority improves"],
        ["Unnecessary Words (Title/URL)", "Filler words in title/url", "Avoid → clarity & CTR improve"],
        ["Structured Data", "JSON-LD schema", "Correct → Google News/Top Stories possible"],
        ["AMP Presence", "Accelerated Mobile Pages support", "Mobile visibility & Discover improve"],
        ["Final SEO Score", "Overall SEO health", "≥80 → strong Google visibility"]
    ], columns=["Metric","Meaning","Impact if Correct"])

    excel_file = format_excel({
        "SEO Audit": pd.concat(all_audit, ignore_index=True),
        "Score Logic": pd.concat(all_grading, ignore_index=True),
        "Explanation": EXPLANATIONS
    })

    st.download_button(
        "⬇️ Download Final SEO Audit Excel",
        data=excel_file,
        file_name="SEO_Audit_Final.xlsx"
    )
