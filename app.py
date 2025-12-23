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

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor – Director Edition", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
bulk_file = st.sidebar.file_uploader("Upload Bulk URLs (TXT / CSV)", type=["txt", "csv"])
url_input = st.text_input("Paste URL")
analyze = st.button("Analyze")

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_article(soup):
    return (
        soup.find("article")
        or soup.find("div", class_=re.compile("content|story|article", re.I))
        or soup
    )

def visible_len(text):
    return sum(1 for c in text if not unicodedata.category(c).startswith("C"))

# ================= CONTENT LOGIC =================
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

# ================= SEO TITLE =================
def generate_seo_title(title, max_len=60):
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

# ================= CLEAN URL =================
STOP_WORDS = {"is","the","and","of","to","in","for","on","with","by","who"}

def clean_slug(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    words = [w for w in text.split() if w not in STOP_WORDS]
    return "-".join(words[:10])

def generate_clean_url(url, title):
    parsed = urlparse(url)
    slug = clean_slug(title)
    if not slug:
        return url  # fallback to original

    # Build base path safely
    path_parts = [p for p in parsed.path.split("/") if p]  # remove empty
    if path_parts:
        path_parts[-1] = slug  # replace last part with slug
    else:
        path_parts = [slug]

    clean_path = "/" + "/".join(path_parts)
    return f"{parsed.scheme}://{parsed.netloc}{clean_path}"

def is_url_clean(url, seo_url):
    orig_slug = urlparse(url).path.rstrip("/").split("/")[-1]
    clean_slug_part = urlparse(seo_url).path.rstrip("/").split("/")[-1]
    return orig_slug == clean_slug_part

# ================= SCORE LOGIC =================
def calculate_score(title_len, word_count, img_count, h1_count, h2_count, internal_links, external_links, has_stop):
    score = 100

    # Title Character Count
    if title_len > 60:
        score -= 15

    # Word Count
    if word_count < 250:
        score -= 15

    # News Image Count
    if img_count < 1:
        score -= 10

    # H1 Count
    if h1_count != 1:
        score -= 10

    # H2 Count
    if h2_count < 2:
        score -= 10

    # Internal Links
    if internal_links < 2 or internal_links > 10:
        score -= 5

    # External Links
    if external_links > 2:
        score -= 5

    # Unnecessary Words (Stop words in title)
    if has_stop:
        score -= 10

    # Ensure score is not negative
    return max(score, 0)
    
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
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 3, 50)

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
    soup = get_soup(url)
    article = get_article(soup)
    domain = urlparse(url).netloc

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "No H1 Found"

    seo_title = generate_seo_title(title)
    clean_url = generate_clean_url(url, seo_title)
    url_clean_flag = is_url_clean(url, clean_url)

    paragraphs = get_real_paragraphs(article)
    word_count = sum(len(p.split()) for p in paragraphs)

    img_count = len(get_real_images(article))
    h1_count = len(article.find_all("h1"))
    h2_count = get_h2_count_fixed(article)
    internal, external = get_links(article, domain)

    found_stop = [w for w in STOP_WORDS if f" {w} " in title.lower()]

    score = calculate_score(visible_len(title), url_clean_flag, bool(found_stop))

    # ---- SEO Audit Table ----
    audit_df = pd.DataFrame([
        ["Title Character Count", visible_len(title), "≤ 60", "❌" if visible_len(title) > 60 else "✅"],
        ["Suggested SEO Title", title, seo_title, "—"],
        ["Word Count", word_count, "450+", "❌" if word_count < 450 else "✅"],
        ["News Image Count", img_count, "1+", "❌" if img_count < 1 else "✅"],
        ["H1 Count", h1_count, "1", "❌" if h1_count != 1 else "✅"],
        ["H2 Count", h2_count, "2+", "❌" if h2_count < 2 else "✅"],
        ["Internal Links", internal, "2–10", "❌" if internal < 2 else "✅"],
        ["External Links", external, "0–2", "❌" if external > 2 else "✅"],
        ["Unnecessary Words", ", ".join(found_stop) if found_stop else "None", "No", "❌" if found_stop else "✅"],
        ["Suggested Clean SEO URL", url, clean_url, "✅" if url_clean_flag else "❌"],
        ["Title + URL SEO Score", f"{score} / 100", "≥ 80", "⚠️" if score < 80 else "✅"],
    ], columns=["Metric", "Actual", "Ideal", "Verdict"])

    # ---- Grading / Score Table ----
    penalties = []
    penalties.append(["Base Score", 100])
    if visible_len(title) > 60:
        penalties.append(["Title > 60 characters", -20])
    if not url_clean_flag:
        penalties.append(["URL not clean", -30])
    if found_stop:
        penalties.append(["Unnecessary words in title", -10])
    penalties.append(["Final Score", score])

    grading_df = pd.DataFrame(penalties, columns=["Scoring Rule", "Value"])

    return audit_df, grading_df

# ================= RUN =================
if analyze:
    urls = []
    if bulk_file:
        urls = [l.strip() for l in bulk_file.read().decode("utf-8").splitlines() if l.strip()]
    elif url_input:
        urls = [url_input]

    all_audit = []
    grading_table = None

    for u in urls:
        audit_df, grading_df = analyze_url(u)
        grading_table = grading_df

        st.subheader(f"📊 SEO Audit – {u}")
        st.dataframe(audit_df, use_container_width=True)

        st.subheader("📐 SEO Score / Grading Logic")
        st.dataframe(grading_df, use_container_width=True)

        all_audit.append(audit_df)

    if all_audit:
        excel = format_excel({
            "SEO Audit": pd.concat(all_audit, ignore_index=True),
            "Score Logic": grading_table
        })

        st.download_button(
            "⬇️ Download Final SEO Audit Excel",
            data=excel,
            file_name="SEO_Audit_Final.xlsx"
        )


