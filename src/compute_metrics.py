
import pandas as pd, pathlib

DATA = pathlib.Path("data")
G = DATA/"guidance_facts.csv"
PE = DATA/"pe_snapshots.csv"
X = DATA/"financials_rollup.csv"   # optional; populate via XBRL parser later
OUT = DATA/"forward_peg.csv"

def midpoint(lo, hi):
    vals = [v for v in [lo, hi] if pd.notna(v) and v!='']
    if not vals: return None
    if len(vals)==1: return float(vals[0])
    return float(sum(map(float, vals))/len(vals))

def cfo_pat_cum(fin, company):
    if fin is None or fin.empty:
        return None
    df = fin[fin["company"]==company].sort_values("fiscal_year").tail(5)
    if df.empty or df["pat"].sum()==0:
        return None
    return float(df["cfo"].sum()/df["pat"].sum())

def latest_pe(pe_df, symbol):
    if pe_df is None or pe_df.empty:
        return None
    rows = pe_df[pe_df["symbol"]==symbol].copy()
    if rows.empty: return None
    rows["as_of_date"] = pd.to_datetime(rows["as_of_date"], errors="coerce")
    rows = rows.sort_values("as_of_date")
    return float(rows["pe"].iloc[-1]) if pd.notna(rows["pe"].iloc[-1]) else None

def run():
    g = pd.read_csv(G) if G.exists() else pd.DataFrame()
    pe = pd.read_csv(PE) if PE.exists() else pd.DataFrame()
    fin = pd.read_csv(X) if X.exists() else pd.DataFrame()
    out=[]
    for _, r in g.iterrows():
        company = r.get("company")
        symbol  = r.get("symbol") or ""  # symbol can be added to seed_sources later
        mid = midpoint(r.get("growth_low"), r.get("growth_high"))
        pe_val = latest_pe(pe, symbol) if symbol else None
        peg = None
        if pe_val is not None and mid and float(mid)!=0.0:
            peg = pe_val/float(mid)
        out.append({
            "Company": company,
            "Symbol": symbol,
            "Metric": str(r.get("metric") or "").upper(),
            "GrowthType": r.get("growth_type"),
            "GrowthLow": r.get("growth_low"),
            "GrowthHigh": r.get("growth_high"),
            "GrowthMid": mid,
            "Horizon": None,
            "PE": pe_val,
            "PEG": peg,
            "CFO_PAT_Cum": cfo_pat_cum(fin, company),
            "BasePeriod": r.get("base_period"),
            "TargetPeriod": r.get("target_period"),
            "Source": r.get("source"),
        })
    pd.DataFrame(out).to_csv(OUT, index=False)
    print("Wrote", OUT)

if __name__ == "__main__":
    run()
