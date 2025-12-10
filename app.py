import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Alignment, Border, Side, Font
import os
import json
import time

# ---- OpenAI client (uses 'openai' new client) ----
try:
    # Prefer official modern client if available
    from openai import OpenAI
    _OPENAI_CLIENT_AVAILABLE = True
except Exception:
    _OPENAI_CLIENT_AVAILABLE = False

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Advanced SEO Auditor – Premium Edition (OpenAI)", layout="wide")

# ---------------- PREMIUM LAYOUT CSS ----------------
st.markdown("""<style>
header[data-testid="stHeader"] {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}
footer {display: none !important; visibility: hidden !important;}
[data-testid="stAppViewContainer"] { background: linear-gradient(135deg, #141E30, #243B55) !important; color: white !important; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0F2027, #203A43, #2C5364); color: white !important; }
h1,h2,h3,p,span,div,label { color: white !important; }
.stTextArea textarea, .stTextInput input { background: #1e2a3b !important; border: 2px solid #4F81BD !important; border-radius: 12px !important; color: white !important; }
.stButton>button { background: #4F81BD !important; color: white !important; border-radius: 10px; padding: 10px 20px; font-size: 18px; border: none; box-shadow: 0px 4px 10px rgba(79,129,189,0.5); }
</style>""", unsafe_allow_html=True)

# ---------------- SAFE GET TEXT ----------------
def safe_get_text(tag):
    try:
        return tag.get_text(" ", strip=True)
    except Exception:
        return ""

# ---------------- STRONG REQUEST HEADERS ----------------
REQ_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "keep-alive",
}

# ---------------- ARTICLE EXTRACTOR ----------------
def extract_article(url):
    try:
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url.lstrip("/")
        r = requests.get(url, headers=REQ_HEADERS, timeout=25, allow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        md = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        meta_desc = md.get("content").strip() if md and md.get("content") else ""
        paras = soup.find_all("p")
        article = ".".join([safe_get_text(p) for p in paras]).strip()
        article = re.sub(r"\s+", " ", article)
        h1 = [safe_get_text(t) for t in soup.find_all("h1")]
        h2 = [safe_get_text(t) for t in soup.find_all("h2")]
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
            parsed = urlparse(href if href.startswith(("http://", "https://")) else "https://" + domain + href)
            if parsed.netloc and parsed.netloc.lower() != domain:
                external_links += 1
            else:
                internal_links += 1
        paragraph_count = len([p for p in paras if safe_get_text(p)])
        sentences = re.split(r"[.!?]\s+", article)
        sentence_count = len([s for s in sentences if s.strip()])
        words = article.split()
        word_count = len(words)
        avg_words_per_sentence = round(word_count / max(1, sentence_count), 2)
        summary = ""
        if sentence_count >= 1:
            summary = ". ".join(sentence.strip() for sentence in sentences[:2]).strip()
            if summary and not summary.endswith("."):
                summary += "."
        return {
            "title": title,
            "meta": meta_desc,
            "h1": h1,
            "h2": h2,
            "img_count": img_count,
            "alt_with": alt_with,
            "internal_links": internal_links,
            "external_links": external_links,
            "paragraph_count": paragraph_count,
            "word_count": word_count,
            "avg_words_per_sentence": avg_words_per_sentence,
            "summary": summary,
            "raw_text": article[:3000],
        }
    except Exception:
        return {
            "title": "",
            "meta": "",
            "h1": [],
            "h2": [],
            "img_count": 0,
            "alt_with": 0,
            "internal_links": 0,
            "external_links": 0,
            "paragraph_count": 0,
            "word_count": 0,
            "avg_words_per_sentence": 0,
            "summary": "",
            "raw_text": "",
        }

# ---------------- HUMAN VERDICT ----------------
def verdict(actual, ideal_min=None, ideal_max=None, ideal_exact=None):
    try:
        val = float(actual)
    except Exception:
        return "❌ Needs Fix"
    if ideal_exact is not None:
        return "✅ Good" if val == ideal_exact else "❌ Needs Fix"
    if ideal_min is not None and ideal_max is not None:
        if ideal_min <= val <= ideal_max:
            return "✅ Good"
        elif val > ideal_max:
            return "⚠️ Excessive"
        else:
            return "❌ Needs Fix"
    if ideal_min is not None:
        return "✅ Good" if val >= ideal_min else "❌ Needs Fix"
    return "❌ Needs Fix"

# ---------------- SEO ANALYSIS ----------------
def seo_analysis_struct(data):
    title = data["title"]
    meta = data["meta"]
    word_count = data["word_count"]
    paragraph_count = data["paragraph_count"]
    img_count = data["img_count"]
    alt_with = data["alt_with"]
    h1_count = len(data["h1"])
    h2_count = len(data["h2"])
    internal_links = data["internal_links"]
    external_links = data["external_links"]
    avg_wps = data["avg_words_per_sentence"]

    metrics = [
        ("Title Length Actual", len(title), "Title Length Ideal", "50–60 characters", "Title Verdict", verdict(len(title), 50, 60)),
        ("Meta Length Actual", len(meta), "Meta Length Ideal", "150–160 characters", "Meta Verdict", verdict(len(meta), 150, 160)),
        ("H1 Count Actual", h1_count, "H1 Count Ideal", "Exactly 1", "H1 Verdict", verdict(h1_count, ideal_exact=1)),
        ("H2 Count Actual", h2_count, "H2 Count Ideal", "2–5", "H2 Verdict", verdict(h2_count, 2, 5)),
        ("Content Length Actual", word_count, "Content Length Ideal", "600+ words", "Content Verdict", verdict(word_count, 600, None)),
        ("Paragraph Count Actual", paragraph_count, "Paragraph Count Ideal", "8+ paragraphs", "Paragraph Verdict", verdict(paragraph_count, 8, None)),
        ("Image Count Actual", img_count, "Image Count Ideal", "3+ images", "Image Verdict", verdict(img_count, 3, None)),
        ("Alt Tags Actual", alt_with, "Alt Tags Ideal", "All images must have alt text", "Alt Tags Verdict", verdict(alt_with, ideal_exact=img_count)),
        ("Internal Links Actual", internal_links, "Internal Links Ideal", "2–5", "Internal Links Verdict", verdict(internal_links, 2, 5)),
        ("External Links Actual", external_links, "External Links Ideal", "2–4", "External Links Verdict", verdict(external_links, 2, 4)),
        ("Readability Actual", avg_wps, "Readability Ideal", "10–20 words/sentence", "Readability Verdict", verdict(avg_wps, 10, 20)),
    ]

    score = 0
    if 50 <= len(title) <= 60: score += 10
    if 150 <= len(meta) <= 160: score += 10
    if h1_count == 1: score += 8
    if 2 <= h2_count <= 5: score += 6
    if word_count >= 600: score += 12
    if paragraph_count >= 8: score += 6
    if img_count >= 3: score += 8
    if img_count > 0 and alt_with == img_count: score += 6
    if 2 <= internal_links <= 5: score += 4
    if 2 <= external_links <= 4: score += 4
    if 10 <= avg_wps <= 20: score += 8

    score = min(score, 100)
    grade = "A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"
    extras = {"Summary": (data["summary"] or "")[:160]}
    return score, grade, metrics, extras

# ---------------- OpenAI SUGGESTION GENERATOR ----------------
def get_openai_client():
    # === Directly add your OpenAI API key here ===
    key = "AIzaSyDN8yBeXcnXpsS7XRrX52nIaqLvo3et8wA"   # <<--- Replace this with your actual OpenAI API key
    
    if not key:
        return None, None
    if _OPENAI_CLIENT_AVAILABLE:
        client = OpenAI(api_key=key)
        return client, key
    else:
        try:
            import openai
            openai.api_key = key
            return openai, key
        except Exception:
            return None, None

# ---------------- AI / Rule-based Suggestions ----------------
def ai_generate_suggestions(client_obj, data, model="gpt-3.5-turbo", max_tokens=700):
    sys = ("You are an expert news SEO editor. "
           "Given the extracted article metadata and short article text, return a JSON object only (no extra text) "
           "with suggested_title, suggested_meta, short_summary, issues, fixes, keywords, content_quality_score")
    payload = {k:data.get(k,"") for k in ["title","meta","summary"]}
    payload.update({
        "word_count": data.get("word_count",0),
        "h1_count": len(data.get("h1",[])),
        "h2_count": len(data.get("h2",[])),
        "img_count": data.get("img_count",0),
        "alt_with": data.get("alt_with",0),
        "internal_links": data.get("internal_links",0),
        "external_links": data.get("external_links",0),
        "avg_words_per_sentence": data.get("avg_words_per_sentence",0),
        "raw_text_excerpt": data.get("raw_text","")
    })
    user_prompt = "Extracted data (JSON):\n" + json.dumps(payload, ensure_ascii=False, indent=0) + "\n\nProduce JSON now."
    try:
        if _OPENAI_CLIENT_AVAILABLE and hasattr(client_obj, "chat"):
            resp = client_obj.chat.completions.create(
                model=model,
                messages=[{"role":"system","content":sys},{"role":"user","content":user_prompt}],
                temperature=0.0,
                max_tokens=max_tokens,
            )
            text = resp.choices[0].message["content"]
        else:
            resp = client_obj.ChatCompletion.create(
                model=model,
                messages=[{"role":"system","content":sys},{"role":"user","content":user_prompt}],
                temperature=0.0,
                max_tokens=max_tokens,
            )
            text = resp.choices[0].message["content"]
        first = text.find("{")
        last = text.rfind("}")
        json_text = text[first:last+1] if first!=-1 and last!=-1 else text
        suggestions = json.loads(json_text)
        return {k:suggestions.get(k,"") if k!="issues" and k!="fixes" and k!="keywords" else suggestions.get(k,[]) for k in ["suggested_title","suggested_meta","short_summary","issues","fixes","keywords","content_quality_score"]}
    except Exception:
        return None

def rule_based_suggestions(data):
    title = data.get("title","") or ""
    meta = data.get("meta","") or ""
    summary = data.get("summary","") or ""
    words = data.get("word_count",0)
    issues, fixes, keywords = [], [], []
    if len(title)<40:
        issues.append("Title too short")
        fixes.append("Make title more descriptive including subject and verb.")
    if len(title)>70:
        issues.append("Title too long")
        fixes.append("Shorten title to 50-70 characters focusing main entity.")
    if not meta or len(meta)<80:
        issues.append("Weak meta")
        fixes.append("Write a 120-155 char meta summarizing key facts.")
    if words<400:
        issues.append("Short content")
        fixes.append("Add context, quotes to reach 600+ words.")
    if data.get("img_count",0)<1:
        issues.append("Few images")
        fixes.append("Add at least one image with alt text.")
    for w in re.findall(r"\w+", title):
        if len(w)>4: keywords.append(w.lower())
    keywords = list(dict.fromkeys(keywords))[:5]
    suggested_title = title if title else ((" ".join(keywords[:3])[:60]) or "Suggested Headline")
    suggested_meta = (meta[:155]+"...") if len(meta)>155 else (meta or (summary[:150]+"..."))
    return {
        "suggested_title": suggested_title,
        "suggested_meta": suggested_meta,
        "short_summary": summary[:160],
        "issues": issues,
        "fixes": fixes,
        "keywords": keywords,
        "content_quality_score": min(90,max(30,int((words/1000)*100)))
    }

# ---------------- Remaining code (Excel formatting + UI) ----------------
# (Ye part exactly same hai jaise aapka existing code me tha, no changes required)

# ---------------- EXCEL FORMATTER ----------------
def apply_excel_formatting(workbook_bytes):
    wb = load_workbook(BytesIO(workbook_bytes))
    ws = wb["Audit"]
    ws.sheet_view.showGridLines = False

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4F81BD")
    red_fill = PatternFill("solid", fgColor="FF7F7F")
    thin_border = Border(
        left=Side(style="thin", color="4F81BD"),
        right=Side(style="thin", color="4F81BD"),
        top=Side(style="thin", color="4F81BD"),
        bottom=Side(style="thin", color="4F81BD"),
    )
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Style headers
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align

    headers = [c.value for c in ws[1]]

    def num(v):
        try:
            return float(v)
        except Exception:
            try:
                return int(v)
            except Exception:
                return None

    # Red highlight failing Actuals
    for row in ws.iter_rows(min_row=2):
        lookup = {headers[i]: row[i] for i in range(len(headers))}

        def val(h):
            c = lookup.get(h)
            return c.value if c else None

        def mark_red(h, cond):
            c = lookup.get(h)
            if c and cond:
                c.fill = red_fill

        mark_red("Title Length Actual", not (50 <= (num(val("Title Length Actual")) or -1) <= 60))
        mark_red("Meta Length Actual", not (150 <= (num(val("Meta Length Actual")) or -1) <= 160))
        mark_red("H1 Count Actual", (num(val("H1 Count Actual")) or -1) != 1)
        mark_red("H2 Count Actual", not (2 <= (num(val("H2 Count Actual")) or -1) <= 5))
        mark_red("Content Length Actual", (num(val("Content Length Actual")) or -1) < 600)
        mark_red("Paragraph Count Actual", (num(val("Paragraph Count Actual")) or -1) < 8)
        mark_red("Image Count Actual", (num(val("Image Count Actual")) or -1) < 3)
        img_actual = num(val("Image Count Actual")) or 0
        alt_actual = num(val("Alt Tags Actual")) or 0
        mark_red("Alt Tags Actual", alt_actual < img_actual)
        mark_red("Internal Links Actual", not (2 <= (num(val("Internal Links Actual")) or -1) <= 5))
        mark_red("External Links Actual", not (2 <= (num(val("External Links Actual")) or -1) <= 4))
        mark_red("Readability Actual", not (10 <= (num(val("Readability Actual")) or -1) <= 20))

        for cell in row:
            cell.border = thin_border
            cell.alignment = center_align

    # Column widths
    for col in ws.columns:
        col_letter = col[0].column_letter
        header_val = ws[f"{col_letter}1"].value
        if header_val == "Summary" or header_val == "short_summary":
            ws.column_dimensions[col_letter].width = 40
        elif header_val and "Verdict" in str(header_val):
            ws.column_dimensions[col_letter].width = 18
        elif header_val and "Ideal" in str(header_val):
            ws.column_dimensions[col_letter].width = 30
        else:
            ws.column_dimensions[col_letter].width = 26

    out = BytesIO()
    wb.save(out)
    return out.getvalue()

# ---------------- UI + STATE ----------------
st.title("🚀 Advanced SEO Auditor – Premium Edition (OpenAI)")
st.subheader("URL Analysis → OpenAI Suggestions → Excel Report → Actual vs Ideal + Human Verdicts")

if "merged_urls" not in st.session_state:
    st.session_state.merged_urls = ""

uploaded = st.file_uploader("Upload URL List (TXT/CSV/XLSX)", type=["txt", "csv", "xlsx"])
urls_input = st.text_area("Paste URLs here", value=st.session_state.merged_urls, height=220)

# Merge uploaded into session_state (reliable across reruns)
if uploaded is not None:
    try:
        if uploaded.type == "text/plain":
            content = uploaded.read().decode("utf-8", errors="ignore")
            uploaded_urls = "\n".join([l.strip() for l in content.splitlines() if l.strip()])
        elif uploaded.type == "text/csv":
            df_u = pd.read_csv(uploaded, header=None)
            uploaded_urls = "\n".join(df_u.iloc[:, 0].astype(str).str.strip())
        else:
            df_u = pd.read_excel(uploaded, header=None)
            uploaded_urls = "\n".join(df_u.iloc[:, 0].astype(str).str.strip())
        st.info("File processed. Merged into the text area below.")
        existing = urls_input.strip()
        st.session_state.merged_urls = (existing + "\n" + uploaded_urls).strip() if existing else uploaded_urls
        # Reflect immediately in the textarea
        urls_input = st.session_state.merged_urls
    except Exception as e:
        st.error(f"Failed to read uploaded file: {e}")

process = st.button("Process & Create Report (with OpenAI suggestions)")

if process:
    if not urls_input.strip():
        st.error("Please paste some URLs or upload a file.")
    else:
        # create OpenAI client (if key exists)
        client_obj, key = get_openai_client()
        if not key:
            st.warning("OpenAI API key not found. Set OPENAI_API_KEY in Streamlit secrets or environment to enable AI suggestions. Continuing with rule-based suggestions.")
        # Build clean URL list (remove duplicates while preserving order)
        seen = set()
        urls = []
        for u in urls_input.splitlines():
            u = u.strip()
            if not u:
                continue
            if u not in seen:
                seen.add(u)
                urls.append(u)

        rows = []
        progress = st.progress(0)
        status = st.empty()

        for i, url in enumerate(urls, start=1):
            status.text(f"Processing {i}/{len(urls)} : {url}")
            data = extract_article(url)  # Per-URL fresh fetch with strong headers
            score, grade, metrics, extras = seo_analysis_struct(data)

            # Attempt AI suggestions
            suggestions = None
            if key and client_obj:
                suggestions = ai_generate_suggestions(client_obj, data)
                # small delay to be kind to API / avoid bursts (adjust as needed)
                time.sleep(0.4)

            if not suggestions:
                suggestions = rule_based_suggestions(data)

            # Build row
            row = {
                "URL": url,
                "Extracted Title": data.get("title",""),
                "Title Length Actual": len(data.get("title","")),
                "Extracted Meta": data.get("meta",""),
                "Meta Length Actual": len(data.get("meta","")),
                "Summary": extras.get("Summary",""),
                "SEO Score": score,
                "SEO Grade": grade,
                "Suggested SEO Title": suggestions.get("suggested_title",""),
                "Suggested SEO Meta": suggestions.get("suggested_meta",""),
                "Short Summary (AI)": suggestions.get("short_summary",""),
                "Issues (AI)": "; ".join(suggestions.get("issues",[])),
                "Fixes (AI)": "; ".join(suggestions.get("fixes",[])),
                "Keyword Suggestions": ", ".join(suggestions.get("keywords",[])),
                "Content Quality Score (AI)": suggestions.get("content_quality_score",0)
            }

            # Add Actual + Ideal + Verdict for each essential metric
            for actual_h, actual_v, ideal_h, ideal_v, verdict_h, verdict_v in metrics:
                row[actual_h] = actual_v
                row[ideal_h] = ideal_v
                row[verdict_h] = verdict_v

            rows.append(row)
            progress.progress(int((i / len(urls)) * 100))

        df = pd.DataFrame(rows)

        # Excel: Audit + Column Definitions sheets
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Audit")

            # Create Column Definitions sheet (ONLY IDEAL HEADINGS)
            wb = writer.book
            ws_def = wb.create_sheet("Column Definitions")
            ws_def.append(["Ideal Column Heading", "Meaning (Kya hai)", "Why Important (Kyu zaruri)"])

            ideal_definitions = [
                ("Title Length Ideal", "Recommended title length", "Fits search snippet, readable headline, improves CTR"),
                ("Meta Length Ideal", "Recommended meta description length", "Fits Google snippet, persuasive summary without truncation"),
                ("H1 Count Ideal", "Exactly one H1 tag", "Clear main headline, avoids confusion for users and crawlers"),
                ("H2 Count Ideal", "2–5 H2 subheadings", "Improves structure and readability, helps users scan content"),
                ("Content Length Ideal", "600+ words in article", "Shows depth and authority, increases dwell time and trust"),
                ("Paragraph Count Ideal", "8+ paragraphs", "Makes content scannable, reduces fatigue, improves UX"),
                ("Image Count Ideal", "3+ images", "Boosts visual engagement, breaks monotony, supports storytelling"),
                ("Alt Tags Ideal", "All images have alt text", "Accessibility compliance, better image SEO and context"),
                ("Internal Links Ideal", "2–5 internal links", "Guides readers to related content, improves site navigation and retention"),
                ("External Links Ideal", "2–4 external links", "Adds credibility via trusted references, supports fact-checking"),
                ("Readability Ideal", "10–20 words per sentence", "Natural flow, easier comprehension, reduces cognitive load"),
            ]

            for r in ideal_definitions:
                ws_def.append(r)

            for col in ws_def.columns:
                ws_def.column_dimensions[col[0].column_letter].width = 32

        final_bytes = apply_excel_formatting(out.getvalue())

        st.success("🎉 Report created successfully! Download below.")
        st.download_button(
            "Download SEO Audit Excel (with suggestions)",
            data=final_bytes,
            file_name="SEO_Audit_Final_with_OpenAI.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


