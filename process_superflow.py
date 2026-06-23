"""
Processes Superflow Meta ads data into the structure needed by the dashboard.
Reads superflow_daily.json and superflow_ads.json and emits superflow_processed.json.
"""
import json
import re
from collections import defaultdict
from datetime import datetime

import os
BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, "superflow_daily.json")) as f:
    daily = json.load(f)
with open(os.path.join(BASE, "superflow_ads.json")) as f:
    ads = json.load(f)

# --- Language parsing from campaign name -------------------------------------
LANG_MAP = {
    "HSM": "Hindi (HSM)",
    "ML":  "Malayalam (ML)",
    "TL":  "Telugu (TL)",
    "KA":  "Kannada (KA)",
    "BN":  "Bengali (BN)",
    "MT":  "Marathi (MT)",
    "TN":  "Tamil (TN)",
    "GT":  "Gujarati (GT)",
}
# Order in regex: longer tokens first ensure HSM > HS, etc.
LANG_RE = re.compile(r"-(HSM|ML|TL|KA|BN|MT|TN|GT)-")
PRICE_RE = re.compile(r"-(10\+199|10\+149|199|99)-")

def parse_campaign(name):
    lang_m = LANG_RE.search(name)
    price_m = PRICE_RE.search(name)
    lang = LANG_MAP.get(lang_m.group(1), "Other") if lang_m else "Other"
    price = price_m.group(1) if price_m else "Other"
    return lang, price

# --- Theme classification from ad name ---------------------------------------
# Top-level: AI vs Human (mutex)
# Within Human: In-house Influencer vs In-house (mutex)
# Sub-themes: multi-tag (Pattern Interrupt, Bhumi Replication, How-to-say-this, ...)

AI_FX_KEYWORDS = [
    "kbh",            # KBH Lighting, KBH Black Hole, KBH Pyro, KBH IOS, KBH 404, KBH Drill, etc.
    "tractor beam", "red marker",
    "phone axe", "axe",
    "phone keyboard hammer", "keyboard hammer",
    "wrecking", "wrecking ball",
    "hammer",
    "drill",
    "pyro",
    "lightning", "blackhole", "black hole",
    "trex", "t-rex",
    "energy burst", "energy",
    "steamroller",
    "hydraulic",
    "nitrogen",
    "cosmic",
    "404",
    "chalkboard",
    "cursor trash",
    "camerazoom",
]

INHOUSE_TALENT = ["bhumi", "akshara", "aks", "leka"]  # if name appears (without AI), top-level Human > In-house

def is_ai(name):
    n = name.lower()
    # explicit AI tag
    if " ai " in f" {n} " or "-ai-" in n or " ai-" in n or "-ai " in n or " ai–" in n:
        return True
    if "translated" in n:
        return True
    # AI b-roll keywords
    for kw in AI_FX_KEYWORDS:
        if kw in n:
            return True
    return False

def classify(name):
    """Returns (top_level, sub_level, sub_themes_list)."""
    n = name.lower()
    if is_ai(name):
        top = "AI"
        sub = None
    else:
        top = "Human"
        if "inhouse inf" in n or "in-house inf" in n:
            sub = "In-house Influencer"
        elif "inhouse" in n or "in-house" in n:
            sub = "In-house"
        elif any(t in n for t in INHOUSE_TALENT):
            sub = "In-house"
        else:
            sub = "In-house"  # default bucket for Human

    sub_themes = []
    # Pattern Interrupt now includes all AI FX names + bulldozer/tank
    pi_keywords = AI_FX_KEYWORDS + ["bulldozer", "tank", "pattern interrupt", "pattern-interrupt"]
    if any(k in n for k in pi_keywords):
        sub_themes.append("Pattern Interrupt")
    if "bhumi" in n:
        sub_themes.append("Bhumi Replication")
    if "how to say this" in n:
        sub_themes.append("How-to-say-this")
    if "wa chat" in n or "whatsapp" in n or "wp chat" in n:
        sub_themes.append("WhatsApp Chat")
    if "testimonial" in n:
        sub_themes.append("Testimonial")
    if "ots ads" in n or "ots ad" in n:
        sub_themes.append("OTS")
    if "frustrated" in n or "disappointed" in n or "humiliation" in n or "stressing" in n:
        sub_themes.append("Pain Point")
    if "game screen" in n or "game recording" in n:
        sub_themes.append("Game/App Screen")
    if "news anchor" in n:
        sub_themes.append("News Anchor")
    if "weird cam" in n:
        sub_themes.append("Weird Cam Angle")
    if "statics" in n or " static " in f" {n} " or n.endswith("static"):
        sub_themes.append("Static")
    if "ots" in n:
        if "OTS" not in sub_themes:
            sub_themes.append("OTS")
    if not sub_themes:
        sub_themes.append("Uncategorized")
    return top, sub, sub_themes

# Legacy entry point kept for backwards compat; not used by new code path
def classify_theme(name):
    top, sub, subs = classify(name)
    return [top, sub] + subs

# --- Aggregate ad-level data -------------------------------------------------
ads_clean = []
for a in ads:
    lang, price = parse_campaign(a["campaign_name"])
    top, sub, sub_themes = classify(a["ad_name"])
    themes = [top, sub] + sub_themes if sub else [top] + sub_themes
    spend = float(a["spend"])
    purchases = float(a["purchases"])
    installs = float(a["installs"])
    impressions = float(a["impressions"])
    clicks = float(a["clicks"])
    cac = (spend / purchases) if purchases > 0 else None
    cpi = (spend / installs) if installs > 0 else None
    cpm = (spend / impressions * 1000) if impressions > 0 else None
    ctr = (clicks / impressions * 100) if impressions > 0 else None
    ads_clean.append({
        "ad_name": a["ad_name"],
        "ad_id": a["ad_id"],
        "campaign_name": a["campaign_name"],
        "campaign_id": a["campaign_id"],
        "language": lang,
        "price_variant": price,
        "top_theme": top,        # 'AI' or 'Human'
        "sub_theme": sub,        # 'In-house' / 'In-house Influencer' (only meaningful when top=Human)
        "sub_themes": sub_themes, # e.g. ['Pattern Interrupt', 'Bhumi Replication']
        "themes": themes,        # backwards-compat: flat list
        "spend": round(spend, 2),
        "purchases": int(purchases),
        "installs": int(installs),
        "impressions": int(impressions),
        "clicks": int(clicks),
        "cac": round(cac, 2) if cac else None,
        "cpi": round(cpi, 2) if cpi else None,
        "cpm": round(cpm, 2) if cpm else None,
        "ctr": round(ctr, 3) if ctr else None,
    })

# --- Language summary --------------------------------------------------------
lang_summary = defaultdict(lambda: {"spend": 0, "purchases": 0, "installs": 0,
                                    "impressions": 0, "clicks": 0,
                                    "ads": 0, "ads_with_spend": 0,
                                    "ads_under_300_cac": 0,
                                    "campaign_ids": set()})
for a in ads_clean:
    L = a["language"]
    s = lang_summary[L]
    s["spend"] += a["spend"]
    s["purchases"] += a["purchases"]
    s["installs"] += a["installs"]
    s["impressions"] += a["impressions"]
    s["clicks"] += a["clicks"]
    s["ads"] += 1
    if a["spend"] > 0:
        s["ads_with_spend"] += 1
    if a["cac"] is not None and a["cac"] <= 300:
        s["ads_under_300_cac"] += 1
    s["campaign_ids"].add(a["campaign_id"])

language_data = []
for L, s in lang_summary.items():
    cac = s["spend"] / s["purchases"] if s["purchases"] > 0 else None
    cpi = s["spend"] / s["installs"] if s["installs"] > 0 else None
    cpm = s["spend"] / s["impressions"] * 1000 if s["impressions"] > 0 else None
    ctr = s["clicks"] / s["impressions"] * 100 if s["impressions"] > 0 else None
    language_data.append({
        "language": L,
        "spend": round(s["spend"], 2),
        "purchases": s["purchases"],
        "installs": s["installs"],
        "impressions": s["impressions"],
        "clicks": s["clicks"],
        "ads": s["ads"],
        "ads_with_spend": s["ads_with_spend"],
        "ads_under_300_cac": s["ads_under_300_cac"],
        "campaigns": len(s["campaign_ids"]),
        "cac": round(cac, 2) if cac else None,
        "cpi": round(cpi, 2) if cpi else None,
        "cpm": round(cpm, 2) if cpm else None,
        "ctr": round(ctr, 3) if ctr else None,
    })
language_data.sort(key=lambda x: x["spend"], reverse=True)

# --- Campaign-level summary (already have, recompute from daily) ------------
campaign_summary = defaultdict(lambda: {"spend":0,"purchases":0,"installs":0,
                                        "impressions":0,"clicks":0,
                                        "name":"","id":""})
for d in daily:
    cn = d["campaign_name"]
    c = campaign_summary[cn]
    c["name"] = cn
    c["id"] = d["campaign_id"]
    c["spend"] += float(d["spend"])
    c["purchases"] += float(d["purchases"])
    c["installs"] += float(d["installs"])
    c["impressions"] += float(d["impressions"])
    c["clicks"] += float(d["clicks"])

campaigns = []
for cn, c in campaign_summary.items():
    lang, price = parse_campaign(cn)
    cac = c["spend"] / c["purchases"] if c["purchases"] > 0 else None
    cpi = c["spend"] / c["installs"] if c["installs"] > 0 else None
    campaigns.append({
        "campaign_name": cn,
        "campaign_id": c["id"],
        "language": lang,
        "price_variant": price,
        "spend": round(c["spend"], 2),
        "purchases": int(c["purchases"]),
        "installs": int(c["installs"]),
        "impressions": int(c["impressions"]),
        "clicks": int(c["clicks"]),
        "cac": round(cac, 2) if cac else None,
        "cpi": round(cpi, 2) if cpi else None,
    })
campaigns.sort(key=lambda x: x["spend"], reverse=True)

# --- Daily trends per language ---------------------------------------------
daily_by_lang_date = defaultdict(lambda: defaultdict(lambda: {"spend":0,"purchases":0,"installs":0}))
for d in daily:
    lang, _ = parse_campaign(d["campaign_name"])
    date = d["date_start"]
    daily_by_lang_date[lang][date]["spend"] += float(d["spend"])
    daily_by_lang_date[lang][date]["purchases"] += float(d["purchases"])
    daily_by_lang_date[lang][date]["installs"] += float(d["installs"])

trends = {}
for lang, days in daily_by_lang_date.items():
    rows = []
    for date in sorted(days.keys()):
        v = days[date]
        rows.append({
            "date": date,
            "spend": round(v["spend"], 2),
            "purchases": int(v["purchases"]),
            "installs": int(v["installs"]),
            "cac": round(v["spend"]/v["purchases"], 2) if v["purchases"]>0 else None,
            "cpi": round(v["spend"]/v["installs"], 2) if v["installs"]>0 else None,
        })
    trends[lang] = rows

# --- Daily trends ACCOUNT level (all languages) -----------------------------
daily_total = defaultdict(lambda: {"spend":0,"purchases":0,"installs":0})
for d in daily:
    date = d["date_start"]
    daily_total[date]["spend"] += float(d["spend"])
    daily_total[date]["purchases"] += float(d["purchases"])
    daily_total[date]["installs"] += float(d["installs"])
account_trend = []
for date in sorted(daily_total.keys()):
    v = daily_total[date]
    account_trend.append({
        "date": date,
        "spend": round(v["spend"], 2),
        "purchases": int(v["purchases"]),
        "installs": int(v["installs"]),
        "cac": round(v["spend"]/v["purchases"], 2) if v["purchases"]>0 else None,
        "cpi": round(v["spend"]/v["installs"], 2) if v["installs"]>0 else None,
    })

# --- Theme summary ----------------------------------------------------------
theme_summary = defaultdict(lambda: {"spend":0,"purchases":0,"installs":0,
                                      "impressions":0,"ads":0,"ads_under_300":0})
for a in ads_clean:
    for t in a["themes"]:
        s = theme_summary[t]
        s["spend"] += a["spend"]
        s["purchases"] += a["purchases"]
        s["installs"] += a["installs"]
        s["impressions"] += a["impressions"]
        s["ads"] += 1
        if a["cac"] is not None and a["cac"] <= 300:
            s["ads_under_300"] += 1

themes = []
for t, s in theme_summary.items():
    cac = s["spend"]/s["purchases"] if s["purchases"]>0 else None
    cpi = s["spend"]/s["installs"] if s["installs"]>0 else None
    themes.append({
        "theme": t,
        "ads": s["ads"],
        "ads_under_300_cac": s["ads_under_300"],
        "spend": round(s["spend"], 2),
        "purchases": s["purchases"],
        "installs": s["installs"],
        "impressions": s["impressions"],
        "cac": round(cac, 2) if cac else None,
        "cpi": round(cpi, 2) if cpi else None,
    })
themes.sort(key=lambda x: x["spend"], reverse=True)

# --- Output -----------------------------------------------------------------
out = {
    "generated_at": datetime.now().isoformat(),
    "summary": {
        "total_spend":     sum(a["spend"] for a in ads_clean),
        "total_purchases": sum(a["purchases"] for a in ads_clean),
        "total_installs":  sum(a["installs"] for a in ads_clean),
        "total_ads":       len(ads_clean),
        "active_campaigns": len(campaigns),
    },
    "language_summary": language_data,
    "campaign_summary": campaigns,
    "ads": ads_clean,
    "trend_account": account_trend,
    "trend_by_language": trends,
    "theme_summary": themes,
}
out["summary"]["overall_cac"] = round(out["summary"]["total_spend"]/out["summary"]["total_purchases"], 2)
out["summary"]["overall_cpi"] = round(out["summary"]["total_spend"]/out["summary"]["total_installs"], 2)
out["summary"]["total_spend"] = round(out["summary"]["total_spend"], 2)

with open(os.path.join(BASE, "superflow_processed.json"), "w") as f:
    json.dump(out, f, indent=2)

# Print a quick summary
print(f"Total spend: ₹{out['summary']['total_spend']:,.0f}")
print(f"Total purchases: {out['summary']['total_purchases']:,}")
print(f"Total installs: {out['summary']['total_installs']:,}")
print(f"Overall CAC: ₹{out['summary']['overall_cac']}")
print(f"Overall CPI: ₹{out['summary']['overall_cpi']}")
print(f"\nLanguages:")
for L in language_data:
    print(f"  {L['language']:25s}  spend=₹{L['spend']:>10,.0f}  purchases={L['purchases']:>5d}  CAC=₹{L['cac'] if L['cac'] else 'N/A':>6}  ads={L['ads']:>3d}  under_300={L['ads_under_300_cac']:>3d}")

print(f"\nTop themes by spend:")
for T in themes[:10]:
    cac_str = f"₹{T['cac']}" if T['cac'] else "N/A"
    print(f"  {T['theme']:25s}  spend=₹{T['spend']:>10,.0f}  ads={T['ads']:>3d}  CAC={cac_str:>8}  under_300={T['ads_under_300_cac']:>3d}")

print(f"\nDate range: {account_trend[0]['date']} to {account_trend[-1]['date']}")
print(f"Days: {len(account_trend)}")
