import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
import re
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import unicodedata

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Advanced SEO Auditor – Director Edition", layout="wide")
st.title("🧠 Advanced SEO Auditor – News & Blog")

# ================= SIDEBAR =================
st.sidebar.header("SEO Mode")
content_type = st.sidebar.radio("Select Content Type", ["News Article", "Blog / Evergreen"])
st.sidebar.markdown("---")
bulk_file = st.sidebar.file_uploader("Upload Bulk URLs (TXT / CSV)", type=["txt", "csv"])
url = st.text_input("Paste URL")
analyze = st.button("Analyze")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_article(soup):
    return soup.find("article") or soup.find("div", class_=re.compile("content|story", re.I)) or soup

# -------- IMAGE LOGIC --------
def get_real_images(article):
    images = []
    for fig in article.find_all("figure"):
        img = fig.find("img")
        if img:
            src = img.get("src") or ""
            if src and not any(x in src.lower() for x in ["logo", "icon", "sprite", "ads"]):
                images.append(img)
    if not images:
        for img in article.find_all("img"):
            cls = " ".join(img.get("class", []))
            src = img.get("src") or ""
            if any(x in cls.lower() for x in ["featured", "post", "hero"]) and src:
                images.append(img)
    return images[:1]

# -------- PARAGRAPHS --------
def get_real_paragraphs(article):
    paras = []
    for p in article.find_all("p"):
        text = p.get_text(" ", strip=True)
        if len(text) < 80:
            continue
        if re.search(r"(photo|file|agency|inputs|also read|read more|advertisement)", text.lower()):
            continue
        paras.append(text)
    return paras

# -------- LINKS --------
def get_links(article, domain):
    internal = external = 0
    for p in article.find_all("p"):
        for a in p.find_all("a", href=True):
            h = a["href"]
            if h.startswith("http"):
                if domain in h:
                    internal += 1
                else:
                    external += 1
            else:
                internal += 1
    return internal, external

# ================= SEO TITLE =================
def generate_seo_title(actual_title, content="", max_len=68):
    import re
    import unicodedata

    # 1) Normalize
    t = (actual_title or "").strip()
    t = re.sub(r"[\"\'“”‘’]", "", t)
    t = re.sub(r"\s+", " ", t)

    # 2) Clause split (Hindi/English separators)
    clauses = re.split(r"[,:।!?\-–—]|(?<=\))", t)
    clauses = [c.strip() for c in clauses if c and len(c.strip()) > 2]

    # 3) Remove fillers but keep impact words
    filler = [
        "ने कहा", "बताया", "बताया कि", "के बयान पर", "पर बयान", "पर प्रतिक्रिया",
        "उद्घाटन समारोह", "खबर", "समाचार", "रिपोर्ट", "विवाद", "चर्चा",
        "पोल खोल", "इशारा", "फिर", "एक दिन की", "डेटा से", "समाधान"
    ]
    def clean_phrase(p):
        p = re.sub(r"\b(" + "|".join(map(re.escape, filler)) + r")\b", "", p)
        p = re.sub(r"\s+", " ", p).strip()
        return p

    clauses = [clean_phrase(c) for c in clauses]
    clauses = [c for c in clauses if c]  # drop empties

    # 4) Compress common Hindi patterns
    def compress_hindi(s):
        # "से ज्यादा/अधिक" → "+"
        s = re.sub(r"(\d+)\s*लाख\s*से\s*ज्यादा", r"\1+ लाख", s)
        s = re.sub(r"(\d+)\s*लाख\s*अधिक", r"\1+ लाख", s)

        # "ने X पर बैन लगाया था/लगाया" → "X पर बैन"
        s = re.sub(r"ने\s+([^,]+?)\s+पर\s+बैन\s+लगाया(?:\s+था)?", r"\1 पर बैन", s)

        # "मचा घमासान/बवाल" → keep single impact word
        s = re.sub(r"मचा\s+(घमासान|बवाल)", r"\1", s)

        # Trim multiple spaces
        s = re.sub(r"\s+", " ", s).strip()
        return s

    clauses = [compress_hindi(c) for c in clauses]

    # 5) Rank clauses (keep keyword‑rich first)
    impact_words = {"पलटवार","घमासान","बवाल","भर्ती","नौकरियां","हाइलाइट्स","अपडेट","आवेदन","विवाद","बैन"}
    def score(c):
        sc = 0
        # numbers, entities, impact boosts
        if re.search(r"\d", c): sc += 2
        sc += sum(2 for w in impact_words if w in c)
        # known topical hints
        topical = ["RSS","सरदार पटेल","कांग्रेस","मोहन भागवत","Bihar","Sarkari","Naukri","भर्ती","परकोटा","स्मार्ट"]
        sc += sum(1 for w in topical if w in c)
        # shorter but meaningful get small boost
        sc += max(0, 20 - len(c.split())) * 0.1
        return sc

    clauses = sorted(clauses, key=score, reverse=True)

    # 6) Build with templates ensuring difference from actual
    modifiers = ["ताज़ा खबर", "Breaking", "Explained"]
    base = modifiers[0] + ": "

    # Compose: primary + optional impact/secondary
    title = base
    for c in clauses:
        candidate = (title + c).strip()
        vis_len = sum(1 for ch in candidate if not unicodedata.category(ch).startswith("C"))
        if vis_len <= max_len:
            title = candidate
            # Try appending a second clause if space allows
            for d in clauses:
                if d == c: continue
                candidate2 = (title + ", " + d).strip()
                vis_len2 = sum(1 for ch in candidate2 if not unicodedata.category(ch).startswith("C"))
                if vis_len2 <= max_len:
                    title = candidate2
            break

    # 7) If still too similar to actual start, force alternative phrasing
    def starts_similar(a, b):
        a0 = re.sub(r"\W+", " ", a).strip().lower()
        b0 = re.sub(r"\W+", " ", b).strip().lower()
        return a0.startswith(b0[:max(10, len(b0)//3)])

    if starts_similar(title.replace(base, ""), t):
        # Switch template: Impact first, then subject
        if len(clauses) >= 2:
            alt = f"{base}{clauses[1]}, {clauses[0]}"
        else:
            alt = f"{modifiers[1]}: {clauses[0]}"
        # length guard
        vis_len = sum(1 for ch in alt if not unicodedata.category(ch).startswith("C"))
        if vis_len <= max_len:
            title = alt

    # 8) Final tidy: strip trailing comma
    title = title.rstrip(", ")

    return title

# ================= EXCEL FORMAT =================
def format_excel(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    wb = load_workbook(output)
    ws = wb.active

    header_fill = PatternFill("solid", fgColor="D9EAF7")
    bold = Font(bold=True)
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for col in ws.columns:
        max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
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

# ================= H2 COUNT FIX =================
def get_h2_count_fixed(article):
    h2s = article.find_all("h2")
    real_h2 = []
    for idx, h2 in enumerate(h2s):
        text = h2.get_text(strip=True)
        if idx == 0 and len(text) > 100:
            continue
        if re.search(r"(advertisement|related|subscribe|promo|sponsored|news in short)", text, re.I):
            continue
        if len(text) < 20:
            continue
        real_h2.append(h2)
    return len(real_h2)

# ================= ANALYSIS =================
def analyze_url(url):
    soup = get_soup(url)
    article = get_article(soup)
    domain = urlparse(url).netloc

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "No H1 Found"
    title_len = len(title)

    paragraphs = get_real_paragraphs(article)
    word_count = sum(len(p.split()) for p in paragraphs)

    img_count = len(get_real_images(article))
    h1_count = len(article.find_all("h1"))
    h2_count = get_h2_count_fixed(article)
    internal, external = get_links(article, domain)

    seo_title = generate_seo_title(title)

    return [
        ["Title Character Count", title_len, "≤ 60", "❌" if title_len > 60 else "✅"],
        ["Suggested SEO Title", title, seo_title, "—"],
        ["Word Count", word_count, "250+", "✅" if word_count >= 250 else "❌"],
        ["News Image Count", img_count, "1+", "✅" if img_count >= 1 else "❌"],
        ["H1 Count", h1_count, "1", "✅" if h1_count == 1 else "❌"],
        ["H2 Count", h2_count, "2+", "✅" if h2_count >= 2 else "❌"],
        ["Internal Links", internal, "2–10", "❌" if internal < 2 else "✅"],
        ["External Links", external, "0–2", "❌" if external > 2 else "✅"],
    ]

# ================= RUN =================
if analyze:
    urls = []
    if bulk_file:
        lines = bulk_file.read().decode("utf-8").splitlines()
        urls = [l.strip() for l in lines if l.strip()]
    elif url:
        urls = [url]

    for idx, u in enumerate(urls):
        data = analyze_url(u)
        df = pd.DataFrame(data, columns=["Metric", "Actual", "Ideal", "Verdict"])

        st.subheader(f"📊 SEO Audit Report – URL {idx+1}")
        st.dataframe(df, use_container_width=True)

        excel = format_excel(df)
        st.download_button(
            label="⬇️ Download Director Ready SEO Report",
            data=excel,
            file_name=f"SEO_Audit_Report_{idx+1}.xlsx",
            key=f"download_{idx}"
        )











