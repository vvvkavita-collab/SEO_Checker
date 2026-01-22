import streamlit as st
import pandas as pd
import requests, re, json, unicodedata
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ================= PAGE CONFIG =================
st.set_page_config("SEO Training Auditor", layout="wide")
st.title("🧠 News SEO Auditor & Training Tracker")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= STOP WORDS =================
TITLE_STOP = ["breaking","exclusive","viral","shocking","must read","big","alert"]
URL_STOP = ["news","latest","update","today","information","details","story",
            "about","on","in","to","of","with","what","why","how","when","where",
            "page","index","tag","category","amp"]

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def visible_len(t):
    return sum(1 for c in t if not unicodedata.category(c).startswith("C"))

def safe_text(el):
    return el.get_text(" ", strip=True) if el else ""

def get_article(soup):
    return soup.find("article") or soup

def clean_paragraphs(article):
    p = []
    for x in article.find_all("p"):
        t = x.get_text(" ", strip=True)
        if len(t) > 80 and not re.search(r"advertisement|promo|subscribe", t, re.I):
            p.append(t)
    return p

def get_url_words(url):
    return re.sub(r"[^a-z0-9\-]", "", urlparse(url).path.lower()).split("-")

def count_links(article, domain):
    i = e = 0
    for a in article.find_all("a", href=True):
        h = a["href"]
        if h.startswith("http"):
            e += domain not in h
            i += domain in h
        elif h.startswith("/"):
            i += 1
    return i, e

def extract_schema(soup):
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            j = json.loads(s.string)
            if "NewsArticle" in json.dumps(j):
                return True
        except:
            pass
    return False

# ================= SCORING =================
def score_title(title, meta):
    s = 0
    l = visible_len(title)
    if 55 <= l <= 70: s += 10
    if meta and 140 <= len(meta) <= 160: s += 10
    return s

def score_url(url):
    words = get_url_words(url)
    bad = [w for w in words if w in URL_STOP]
    return 10 if len(bad) == 0 and 3 <= len(words) <= 6 else 5 if len(bad)<=2 else 0

def score_headings(h1,h2,h3,word_count):
    s = 0
    if h1 == 1: s += 6
    if 3 <= h2 <= 10: s += 8
    if h3 >= 1: s += 4
    if word_count / max((h2+h3),1) >= 200: s += 2
    return s

def score_content(words):
    if words >= 800: return 15
    if words >= 500: return 12
    if words >= 300: return 8
    return 0

def score_paragraphs(paras):
    avg = sum(len(p.split()) for p in paras) / max(len(paras),1)
    return 10 if 60 <= avg <= 120 else 5

def score_links(i,e):
    s=0
    if 2<=i<=10: s+=5
    if 1<=e<=2: s+=5
    return s

def score_images(img, og):
    s=0
    if img>=1: s+=5
    if og: s+=5
    return s

def score_tech(schema, amp):
    s=0
    if schema: s+=3
    if amp: s+=2
    return s

# ================= ANALYSIS =================
def analyze(url):
    soup = get_soup(url)
    art = get_article(soup)
    domain = urlparse(url).netloc

    title = safe_text(soup.find("title"))
    meta = soup.find("meta", attrs={"name":"description"})
    meta = meta["content"] if meta else ""

    paras = clean_paragraphs(art)
    words = sum(len(p.split()) for p in paras)

    h1 = len(art.find_all("h1"))
    h2 = len(art.find_all("h2"))
    h3 = len(art.find_all("h3"))

    internal, external = count_links(art, domain)
    imgs = len(art.find_all("img"))
    og = soup.find("meta", property="og:image")

    schema = extract_schema(soup)
    amp = bool(soup.find("link", rel="amphtml"))

    score = (
        score_title(title, meta) +
        score_url(url) +
        score_headings(h1,h2,h3,words) +
        score_content(words) +
        score_paragraphs(paras) +
        score_links(internal,external) +
        score_images(imgs,og) +
        score_tech(schema,amp)
    )

    data = [
        ("Title Length", visible_len(title), "55–70"),
        ("Meta Description", len(meta), "140–160"),
        ("URL Words", len(get_url_words(url)), "3–6"),
        ("H1 / H2 / H3", f"{h1}/{h2}/{h3}", "1 / 3–10 / logical"),
        ("Word Count", words, "300+"),
        ("Paragraph Avg Words", int(sum(len(p.split()) for p in paras)/max(len(paras),1)), "60–120"),
        ("Internal Links", internal, "2–10"),
        ("External Links", external, "1–2"),
        ("Images", imgs, "1+"),
        ("Schema", schema, "Yes"),
        ("AMP", amp, "Optional"),
        ("FINAL SEO SCORE", score, "≥80 = Good")
    ]

    return pd.DataFrame(data, columns=["Metric","Actual","Ideal"])

# ================= UI =================
url = st.text_input("Paste News URL")
if st.button("Run SEO Audit") and url:
    df = analyze(url)
    st.dataframe(df, use_container_width=True)

    excel = BytesIO()
    df.to_excel(excel, index=False)
    excel.seek(0)

    st.download_button("⬇ Download SEO Audit Excel",
        data=excel,
        file_name="News_SEO_Training_Audit.xlsx"
    )
