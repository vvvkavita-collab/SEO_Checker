import streamlit as st
import pandas as pd
import requests, re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import Border, Side, PatternFill, Font, Alignment

# ================= PAGE =================
st.set_page_config(page_title="Advanced SEO Auditor", layout="wide")
st.title("🧠 Advanced SEO Auditor – News Focused")

# ================= INPUT =================
uploaded = st.file_uploader("Upload URLs (TXT / CSV / XLSX)", type=["txt","csv","xlsx"])
urls_text = st.text_area("Or paste URLs (one per line)", height=200)
analyze = st.button("Analyze URLs")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= HELPERS =================
def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def real_paragraphs(article):
    out=[]
    for p in article.find_all("p"):
        t=p.get_text(" ",strip=True)
        if len(t)<80: continue
        if re.search(r"(photo|agency|inputs|also read)",t.lower()): continue
        out.append(t)
    return out

def real_image(article):
    for fig in article.find_all("figure"):
        img=fig.find("img")
        if img and img.get("src") and not any(x in img["src"].lower() for x in ["logo","icon","ads"]):
            return 1
    return 0

def links(article, domain):
    i=e=0
    for p in article.find_all("p"):
        for a in p.find_all("a",href=True):
            h=a["href"]
            if h.startswith("http"):
                if domain in h: i+=1
                else: e+=1
            else: i+=1
    return i,e

def clean(text):
    return " ".join(text.replace("\n"," ").split()).strip()

def seo_title(title, limit=65):
    if len(title)<=limit: return title
    cut=title[:limit+10]
    if ":" in cut:
        cut=cut.split(":")[0]+": "+cut.split(":")[1].rsplit(" ",1)[0]
    else:
        cut=cut.rsplit(" ",1)[0]
    return cut

# ================= URL COLLECT =================
urls=[]
if uploaded:
    if uploaded.type=="text/plain":
        urls=uploaded.read().decode().splitlines()
    elif uploaded.type=="text/csv":
        urls=pd.read_csv(uploaded,header=None)[0].tolist()
    else:
        urls=pd.read_excel(uploaded,header=None)[0].tolist()

if urls_text.strip():
    urls+=urls_text.splitlines()

urls=[u.strip() for u in urls if u.strip()]
urls=list(dict.fromkeys(urls))  # remove duplicate

# ================= PROCESS =================
rows=[]
if analyze and urls:
    for url in urls:
        soup=get_soup(url)
        domain=urlparse(url).netloc
        article=soup.find("article") or soup

        title=soup.find("h1").get_text(strip=True)
        meta=soup.find("meta",attrs={"name":"description"})
        meta=clean(meta["content"]) if meta else ""

        paras=real_paragraphs(article)
        wc=sum(len(p.split()) for p in paras)

        img=real_image(article)
        il,el=links(article,domain)

        rows.append({
            "URL":url,
            "Title Length":len(title),
            "Suggested SEO Title":seo_title(title),
            "Meta Characters":len(meta),
            "Word Count":wc,
            "Image Count":img,
            "Internal Links":il,
            "External Links":el
        })

    df=pd.DataFrame(rows)

    # ================= GUIDE SHEET =================
    guide=pd.DataFrame([
        ["Title Length","Title ke characters","50–65","CTR improve hota hai"],
        ["Meta Characters","Meta description size","70–160","Click badhta hai"],
        ["Word Count","Main content words","250+","Ranking strong hoti hai"],
        ["Image Count","News related image","1+","Discover visibility"],
        ["Internal Links","Same site links","2–10","Crawl improve"],
        ["External Links","Other site links","0–2","Trust signal"],
    ],columns=["Metric","Meaning","Ideal","SEO Impact"])

    # ================= EXCEL FORMAT =================
    output=BytesIO()
    with pd.ExcelWriter(output,engine="openpyxl") as w:
        df.to_excel(w,index=False,sheet_name="SEO_Audit")
        guide.to_excel(w,index=False,sheet_name="SEO_Guide")

    wb=load_workbook(output)
    blue=Side(style="thin",color="4F81BD")
    border=Border(left=blue,right=blue,top=blue,bottom=blue)
    head_fill=PatternFill("solid","4F81BD")
    head_font=Font(bold=True,color="FFFFFF")

    for ws in wb:
        ws.sheet_view.showGridLines=False
        for c in ws[1]:
            c.fill=head_fill; c.font=head_font; c.border=border; c.alignment=Alignment(horizontal="center")
        for r in ws.iter_rows(min_row=2):
            for c in r:
                c.border=border; c.alignment=Alignment(horizontal="center")
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width=22

    final=BytesIO()
    wb.save(final)

    st.success("✅ SEO Audit Ready")
    st.dataframe(df,use_container_width=True)
    st.download_button("⬇ Download Formatted SEO Report",final.getvalue(),"SEO_Audit.xlsx")
