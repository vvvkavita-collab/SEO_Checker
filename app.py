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

STOP_WORDS = [
    "breaking", "exclusive", "shocking", "must read", "update", "alert"
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

# ================= H2 COUNT (EXCLUDE H1) =================
def get_h2_count_fixed(article, h1_list=None):
    """
    Counts only true H2 headings inside the article.
    Excludes H1 headings passed in h1_list.
    Skips empty or ad/related/promo headings.
    """
    if h1_list is None:
        h1_list = []

    h2s = article.find_all("h2")
    real = []
    for h2 in h2s:
        t = h2.get_text(" ", strip=True)
        if not t:
            continue
        # Skip headings matching H1 text exactly
        if t in h1_list:
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

# ================= SCORE LOGIC =================
def calculate_score(title_len, word_count, img_count, h1_count, h2_count,
                    internal_links, external_links, has_stop, has_schema, amp_flag, url_clean_flag, meta_image):
    score = 100
    if title_len > 70 or title_len < 55: score -= 12
    if word_count < 300: score -= 12
    if img_count < 1: score -= 10
    if not meta_image: score -= 5
    if h1_count != 1: score -= 10
    if h2_count < 2: score -= 8
    if internal_links < 2 or internal_links > 10: score -= 5
    if external_links > 2: score -= 4
    if has_stop: score -= 6
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
    json_list = []
    for s in scripts:
        try:
            data = json.loads(s.string)
            json_list.append(data)
        except:
            continue
    return json_list

def has_newsarticle_schema(json_ld_list):
    for jd in json_ld_list:
        if isinstance(jd, dict) and jd.get("@type") == "NewsArticle":
            return True
        if isinstance(jd, list):
            for item in jd:
                if isinstance(item, dict) and item.get("@type") == "NewsArticle":
                    return True
    return False

def is_amp(soup):
    amp_tag = soup.find("link", rel="amphtml")
    return bool(amp_tag)

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
        err_df = pd.DataFrame([["Error", str(e), "-", "❌"]], columns=["Metric","Actual","Ideal","Verdict"])
        return err_df, pd.DataFrame([["Final Score", 0]], columns=["Scoring Rule", "Value"])

    article = get_article(soup)
    domain = urlparse(url).netloc

    title_tag = soup.find("h1") or soup.find("title")
    title = safe_text(title_tag) if title_tag else "No H1/Title Found"
    h1_texts = [title]  # exclude H1 from H2 count

    h1_count = len(article.find_all("h1")) or len(soup.find_all("h1"))
    h2_count = get_h2_count_fixed(article, h1_list=h1_texts)

    seo_title = generate_seo_title(title)
    paragraphs = get_real_paragraphs(article)
    word_count = sum(len(p.split()) for p in paragraphs)
    images = get_real_images(article)
    img_count = len(images)
    meta_image = extract_meta_image(soup)
    internal, external = get_links(article, domain)
    found_stop = [w for w in STOP_WORDS if f" {w} " in title.lower()]
    json_ld = extract_json_ld(soup)
    schema_flag = has_newsarticle_schema(json_ld)
    amp_flag = is_amp(soup)
    title_len = visible_len(title)

    score = calculate_score(
        title_len=title_len,
        word_count=word_count,
        img_count=img_count,
        h1_count=h1_count,
        h2_count=h2_count,
        internal_links=internal,
        external_links=external,
        has_stop=bool(found_stop),
        has_schema=schema_flag,
        amp_flag=amp_flag,
        url_clean_flag=True,
        meta_image=meta_image
    )

    url_status = "Sahi hai" if len(url) <= 100 else "Lengthy hai"

    audit_df = pd.DataFrame([
        ["Title Character Count", title_len, "55–70", "✅" if 55 <= title_len <= 70 else "⚠️"],
        ["Suggested SEO Title", title, seo_title, "—"],
        ["Word Count", word_count, "300+", "✅" if word_count >= 300 else "⚠️"],
        ["News Image Count", img_count, "1+", "✅" if img_count >= 1 else "⚠️"],
        ["Meta Image (OG/Twitter)", meta_image or "None", "Present", "✅" if meta_image else "⚠️"],
        ["H1 Count", h1_count, "1", "✅" if h1_count == 1 else "⚠️"],
        ["H2 Count", h2_count, "2+", "✅" if h2_count >= 2 else "⚠️"],
        ["Internal Links", internal, "2–10", "✅" if 2 <= internal <= 10 else "⚠️"],
        ["External Links", external, "0–2", "✅" if external <= 2 else "⚠️"],
        ["Unnecessary Words", ", ".join(found_stop) if found_stop else "None", "No", "✅" if not found_stop else "⚠️"],
        ["Structured Data (NewsArticle)", "Yes" if schema_flag else "No", "Yes", "✅" if schema_flag else "⚠️"],
        ["AMP Presence", "Yes" if amp_flag else "No", "Optional", "✅" if amp_flag else "ℹ️"],
        ["URL Length Status", url, url_status, "✅" if url_status=="Sahi hai" else "⚠️"],
        ["Title + URL SEO Score", f"{score} / 100", "≥80", "✅" if score >= 80 else "⚠️"],
    ], columns=["Metric", "Actual", "Ideal", "Verdict"])

    penalties = [
        ["Base Score", 100],
        ["Title outside 55–70", -12 if title_len > 70 or title_len < 55 else 0],
        ["Word Count < 300", -12 if word_count < 300 else 0],
        ["News Image Count < 1", -10 if img_count < 1 else 0],
        ["No Meta Image", -5 if not meta_image else 0],
        ["H1 Count != 1", -10 if h1_count != 1 else 0],
        ["H2 Count < 2", -8 if h2_count < 2 else 0],
        ["Internal Links out of range", -5 if internal < 2 or internal > 10 else 0],
        ["External Links > 2", -4 if external > 2 else 0],
        ["Unnecessary words in title", -6 if found_stop else 0],
        ["No NewsArticle schema", -10 if not schema_flag else 0],
        ["No AMP", -3 if not amp_flag else 0],
        ["Final Score", score]
    ]
    grading_df = pd.DataFrame(penalties, columns=["Scoring Rule", "Value"])

    return audit_df, grading_df

# ================= RUN =================
if analyze:
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

    urls = [u for u in urls if u]
    if not urls:
        st.warning("Please paste a URL or upload a TXT/CSV with URLs.")
    else:
        all_audit = []
        all_grading = []

        progress = st.progress(0)
        status = st.empty()

        total = len(urls)
        for idx, u in enumerate(urls, start=1):
            status.text(f"Analyzing {idx}/{total}: {u}")
            try:
                audit_df, grading_df = analyze_url(u)
            except Exception as e:
                audit_df = pd.DataFrame([["Error", str(e), "-", "❌"]],
                                        columns=["Metric","Actual","Ideal","Verdict"])
                grading_df = pd.DataFrame([["Final Score", 0]],
                                          columns=["Scoring Rule","Value"])

            st.subheader(f"📊 SEO Audit – {u}")
            st.dataframe(audit_df, use_container_width=True)

            st.subheader("📐 SEO Score / Grading Logic")
            st.dataframe(grading_df, use_container_width=True)

            audit_df = audit_df.copy()
            audit_df.insert(0, "URL", u)
            grading_df = grading_df.copy()
            grading_df.insert(0, "URL", u)

            all_audit.append(audit_df)
            all_grading.append(grading_df)

            progress.progress(idx / total)

        status.text("Analysis complete ✔️")

        if all_audit:
            EXPLANATIONS = pd.DataFrame([
                ["Title Character Count", "Title length should be 55–70 chars for Google SERP", "Correct → CTR increases, snippet fully visible"],
                ["Word Count", "Content depth", "300+ words considered informative by Google"],
                ["News Image Count", "Minimum 1 authentic image", "Improves Google Discover & CTR"],
                ["Meta Image (OG/Twitter)", "Thumbnail for social/discover", "CTR & visibility improve"],
                ["H1 Count", "Main headline clarity", "1 H1 helps Google understand topic"],
                ["H2 Count", "Subheadings readability", "2+ H2 → structured content"],
                ["Internal Links", "Navigation + SEO juice", "2–10 links → better crawl & engagement"],
                ["External Links", "References & credibility", "≤2 → authority improves"],
                ["Unnecessary Words", "Filler words in title", "Avoid → clarity & CTR improve"],
                ["Structured Data (NewsArticle)", "JSON-LD schema", "Correct → Google News/Top Stories possible"],
                ["AMP Presence", "Accelerated Mobile Pages support", "Mobile visibility & Discover improve"],
                ["URL Length Status", "Original URL length check", "Sahi hai / Lengthy hai"],
                ["Title + URL SEO Score", "Overall SEO health", "≥80 → strong Google visibility"],
            ], columns=["Metric","Meaning","Impact if Correct"])
            
            excel = format_excel({
                "SEO Audit": pd.concat(all_audit, ignore_index=True),
                "Score Logic": pd.concat(all_grading, ignore_index=True),
                "Explanation": EXPLANATIONS
            })

            st.download_button(
                "⬇️ Download Final SEO Audit Excel",
                data=excel,
                file_name="SEO_Audit_Final.xlsx"
            )
