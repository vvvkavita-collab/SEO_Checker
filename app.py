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

# ================= CONTENT LOGIC (RESTORED) =================
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
    # Restore original: prefer figure>img excluding logos/icons/ads; fallback to <img> with 'featured' class; return up to 1
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
    return imgs[:1]  # count hero image only, as per original script

def get_links(article, domain):
    # Restore original: count links only within paragraphs to avoid nav/footer noise
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
def generate_seo_title(title, max_len=70):
    # Aim 55–70, truncate beyond 70
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
        return url  # fallback
    path_parts = [p for p in parsed.path.split("/") if p]
    if path_parts:
        path_parts[-1] = slug
    else:
        path_parts = [slug]
    clean_path = "/" + "/".join(path_parts)
    return f"{parsed.scheme}://{parsed.netloc}{clean_path}"

def is_url_clean(url, seo_url):
    orig_slug = urlparse(url).path.rstrip("/").split("/")[-1]
    clean_slug_part = urlparse(seo_url).path.rstrip("/").split("/")[-1]
    return orig_slug == clean_slug_part

# ================= STRUCTURED DATA & META =================
def extract_json_ld(soup):
    data = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            parsed = json.loads(tag.string or "{}")
            if isinstance(parsed, list):
                data.extend(parsed)
            else:
                data.append(parsed)
        except Exception:
            continue
    return data

def has_newsarticle_schema(json_ld):
    for obj in json_ld:
        t = obj.get("@type")
        if isinstance(t, list):
            if any(isinstance(tt, str) and tt.lower() == "newsarticle" for tt in t):
                return True
        elif isinstance(t, str) and t.lower() == "newsarticle":
            return True
    return False

def extract_meta_image(soup):
    for prop in ["og:image", "twitter:image", "twitter:image:src"]:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            return tag["content"]
    return None

def is_amp(soup):
    if soup.find("link", rel="amphtml"):
        return True
    html_tag = soup.find("html")
    if html_tag and ("amp" in html_tag.attrs or "⚡" in html_tag.attrs):
        return True
    return False

# ================= SCORE LOGIC =================
def calculate_score(title_len, word_count, img_count, h1_count, h2_count,
                    internal_links, external_links, has_stop, has_schema, amp_flag):
    score = 100
    # Title length (aim 55–70)
    if title_len > 70 or title_len < 55:
        score -= 12
    # Word count (news minimum depth)
    if word_count < 300:
        score -= 12
    # Images (hero image expected)
    if img_count < 1:
        score -= 10
    # H1
    if h1_count != 1:
        score -= 10
    # H2
    if h2_count < 2:
        score -= 8
    # Links (paragraph-level only)
    if internal_links < 2 or internal_links > 10:
        score -= 5
    if external_links > 2:
        score -= 4
    # Stop words in title
    if has_stop:
        score -= 6
    # Structured data
    if not has_schema:
        score -= 10
    # AMP (optional bonus)
    if not amp_flag:
        score -= 3
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
        # Autosize
        for col in ws.columns:
            max_len = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 3, 60)
        # Header style
        for cell in ws[1]:
            cell.font = bold
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border
        # Body style
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
        err_df = pd.DataFrame([
            ["Error", str(e), "-", "❌"]
        ], columns=["Metric","Actual","Ideal","Verdict"])
        return err_df, pd.DataFrame([["Final Score", 0]], columns=["Scoring Rule", "Value"])

    article = get_article(soup)
    domain = urlparse(url).netloc

    # Title (H1 preferred; fallback to <title>)
    title_tag = soup.find("h1") or soup.find("title")
    title = safe_text(title_tag) if title_tag else "No H1/Title Found"

    seo_title = generate_seo_title(title)
    clean_url = generate_clean_url(url, seo_title)
    url_clean_flag = is_url_clean(url, clean_url)

    paragraphs = get_real_paragraphs(article)
    word_count = sum(len(p.split()) for p in paragraphs)

    images = get_real_images(article)
    img_count = len(images)
    meta_image = extract_meta_image(soup)

    # H1/H2 counts: within article; fallback to whole soup for H1
    h1_count = len(article.find_all("h1")) or len(soup.find_all("h1"))
    h2_count = get_h2_count_fixed(article)

    # Links (paragraph-level only, restored)
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
        amp_flag=amp_flag
    )

    # ---- SEO Audit Table ----
    audit_df = pd.DataFrame([
        ["Title Character Count", title_len, "55–70", "✅" if 55 <= title_len <= 70 else "⚠️"],
        ["Suggested SEO Title", title, seo_title, "—"],
        ["Word Count", word_count, "300+", "✅" if word_count >= 300 else "⚠️"],
        ["News Image Count", img_count, "1+", "✅" if img_count >= 1 else "⚠️"],
        ["Meta Image (OG/Twitter)", meta_image or "None", "Present", "✅" if meta_image else "⚠️"],
        ["H1 Count", h1_count, "1", "✅" if h1_count == 1 else "⚠️"],
        ["H2 Count", h2_count, "2+", "✅" if h2_count >= 2 else "⚠️"],
        ["Internal Links (paragraphs)", internal, "2–10", "✅" if 2 <= internal <= 10 else "⚠️"],
        ["External Links (paragraphs)", external, "0–2", "✅" if external <= 2 else "⚠️"],
        ["Unnecessary Words", ", ".join(found_stop) if found_stop else "None", "No", "✅" if not found_stop else "⚠️"],
        ["Structured Data (NewsArticle)", "Yes" if schema_flag else "No", "Yes", "✅" if schema_flag else "⚠️"],
        ["AMP Presence", "Yes" if amp_flag else "No", "Optional (Yes preferred)", "✅" if amp_flag else "ℹ️"],
        ["Suggested Clean SEO URL", url, clean_url, "✅" if url_clean_flag else "⚠️"],
        ["Title + URL SEO Score", f"{score} / 100", "≥ 80", "✅" if score >= 80 else "⚠️"],
    ], columns=["Metric", "Actual", "Ideal", "Verdict"])

    # ---- Grading / Score Table ----
    penalties = [
        ["Base Score", 100],
        ["Title outside 55–70", -12 if title_len > 70 or title_len < 55 else 0],
        ["Word Count < 300", -12 if word_count < 300 else 0],
        ["News Image Count < 1", -10 if img_count < 1 else 0],
        ["H1 Count != 1", -10 if h1_count != 1 else 0],
        ["H2 Count < 2", -8 if h2_count < 2 else 0],
        ["Internal Links out of range (paragraphs)", -5 if internal < 2 or internal > 10 else 0],
        ["External Links > 2 (paragraphs)", -4 if external > 2 else 0],
        ["Unnecessary words in title", -6 if found_stop else 0],
        ["No NewsArticle schema", -10 if not schema_flag else 0],
        ["No AMP", -3 if not amp_flag else 0],
        ["Final Score", score]
    ]
    grading_df = pd.DataFrame(penalties, columns=["Scoring Rule", "Value"])

    return audit_df, grading_df

# ================= RUN =================
if analyze:
    # Collect URLs
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

            # Tag with URL for Excel consolidation
            audit_df = audit_df.copy()
            audit_df.insert(0, "URL", u)
            grading_df = grading_df.copy()
            grading_df.insert(0, "URL", u)

            all_audit.append(audit_df)
            all_grading.append(grading_df)

            progress.progress(idx / total)

        status.text("Analysis complete ✔️")

        if all_audit:
            excel = format_excel({
                "SEO Audit": pd.concat(all_audit, ignore_index=True),
                "Score Logic": pd.concat(all_grading, ignore_index=True)
            })

            st.download_button(
                "⬇️ Download Final SEO Audit Excel",
                data=excel,
                file_name="SEO_Audit_Final.xlsx"
            )

# ================= NOTES =================
st.markdown("""
> Restored logic:
> - News Image Count: figure>img (excluding logo/icon/ads), fallback to featured <img>, limited to 1 (hero image).
> - Internal/External Links: counted only inside paragraphs to avoid nav/footer noise.
> Google-friendly benchmarks kept:
> - Title: 55–70 chars; Word count: 300+; H1=1; H2≥2; Internal 2–10; External ≤2; NewsArticle schema; AMP preferred; Clean URL.
""")
