
import os, re, io, sys, json, pathlib, requests, pandas as pd
from datetime import datetime
from pdfminer.high_level import extract_text

DATA = pathlib.Path("data")
SEED = DATA/"seed_sources.csv"
GUID = DATA/"guidance_facts.csv"

PROMPT = """You are an extraction engine. From the text below, return ONLY JSON:
{ "company": "", "as_of_date": "YYYY-MM-DD", "facts":[
  {"metric":"PAT|Revenue|EBITDA","growth_type":"CAGR|YoY","growth_value_low":N,"growth_value_high":M,
   "base_period":"FY..","target_period":"FY..","time_horizon_months":int,
   "verbatim_quote":"...", "speaker":"...", "confidence":0.0}
], "document_url": "" }
Rules: extract only numeric forward guidance from management (not analysts). If none, facts=[].
"""


def fetch_text(url: str) -> str:
    h = {"User-Agent":"Mozilla/5.0"}
    r = requests.get(url, headers=h, timeout=60)
    r.raise_for_status()
    ctype = r.headers.get("content-type","").lower()
    if "pdf" in ctype or url.lower().endswith(".pdf"):
        with io.BytesIO(r.content) as f:
            try:
                txt = extract_text(f)
            except Exception:
                txt = ""
        return txt
    else:
        # crude HTML -> text
        html = r.text
        # remove scripts/styles
        html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", html)
        text = re.sub(r"(?is)<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text[:200000]  # cap to avoid giant pages


def call_llm(text: str, url: str, company: str, as_of_date: str) -> list[dict]:
    # Gemini 1.5 Flash via google-genai
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set; cannot extract.", file=sys.stderr)
        return []
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=[PROMPT, text],
        config={"response_mime_type":"application/json"}
    )
    try:
        data = json.loads(resp.text)
    except Exception:
        return []
    facts = data.get("facts") or []
    out = []
    for f in facts:
        metric = str(f.get("metric","")).upper()
        if metric not in {"PAT","REVENUE","EBITDA"}: 
            continue
        # numeric guardrails
        lo = f.get("growth_value_low"); hi=f.get("growth_value_high")
        if (lo is None and hi is None):
            continue
        out.append({
            "company": company,
            "as_of_date": as_of_date,
            "metric": metric,
            "growth_type": f.get("growth_type"),
            "growth_low": lo,
            "growth_high": hi,
            "base_period": f.get("base_period"),
            "target_period": f.get("target_period"),
            "time_horizon_months": f.get("time_horizon_months"),
            "quote": f.get("verbatim_quote"),
            "speaker": f.get("speaker"),
            "confidence": f.get("confidence"),
            "source": url
        })
    return out


def main():
    if not SEED.exists():
        print(f"Missing {SEED}. Create it with at least one row.", file=sys.stderr)
        sys.exit(1)
    seeds = pd.read_csv(SEED)
    all_rows = []
    for _, row in seeds.iterrows():
        url = row.get("source_url")
        company = row.get("company")
        as_of = row.get("as_of_date") or ""
        if not isinstance(url, str) or not url.startswith("http"):
            continue
        try:
            txt = fetch_text(url)
            extracted = call_llm(txt, url, company, as_of)
            all_rows.extend(extracted)
        except Exception as e:
            print("Error on", url, e, file=sys.stderr)
    if all_rows:
        pd.DataFrame(all_rows).to_csv(GUID, index=False)
        print("Wrote", GUID)
    else:
        # create empty file with headers so downstream steps don't break
        pd.DataFrame(columns=["company","as_of_date","metric","growth_type","growth_low","growth_high","base_period","target_period","time_horizon_months","quote","speaker","confidence","source"]).to_csv(GUID, index=False)
        print("No guidance extracted; wrote empty", GUID)

if __name__ == "__main__":
    main()
