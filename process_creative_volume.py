"""Process ads_with_created.json + ad_weekly_spend.json into compact datasets
for the dashboard's creative-volume charts."""
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

import os as _os
BASE = _os.path.dirname(_os.path.abspath(__file__))

# Campaign_id → language mapping (derived from campaign names earlier in this session)
CAMPAIGN_ID_TO_LANG = {
    "120247189861740513": "Hindi (HSM)",         # Superflow-HSM-199 – Copy
    "120247113240430513": "Malayalam (ML)",      # Superflow-ML-10+149
    "120247105483260513": "Hindi (HSM)",         # Superflow-HSM-99
    "120246449055680513": "Gujarati (GT)",       # Superflow-GT-199
    "120246449055670513": "Bengali (BN)",        # Superflow-BN-199
    "120246059063540513": "Marathi (MT)",        # Superflow-MT-199
    "120245891639460513": "Tamil (TN)",          # Superflow-TN-199
    "120245891639290513": "Telugu (TL)",         # Superflow-TL-199
    "120245891639270513": "Kannada (KA)",        # Superflow-KA-199
    "120245631352660513": "Malayalam (ML)",      # Superflow-ML-199
    "120244070909170513": "Hindi (HSM)",         # Superflow-HSM-10+199 (paused)
    "120243754517490513": "Hindi (HSM)",         # Superflow-HSM-199 (original)
}

# Same classifier as elsewhere
AI_FX_KEYWORDS = ["kbh","tractor beam","red marker","phone axe"," axe","keyboard hammer"," hammer","wrecking","drill","pyro","lightning","blackhole","black hole","trex","t-rex","energy burst"," energy","steamroller","hydraulic","nitrogen","cosmic"," 404","chalkboard","cursor trash","camerazoom"]

def is_ai(name):
    n = (name or "").lower()
    if re.search(r" ai |-ai-| ai-|-ai ", " " + n + " "):
        return True
    if "translated" in n:
        return True
    for k in AI_FX_KEYWORDS:
        if k in n:
            return True
    return False

def top_theme(name):
    return "AI" if is_ai(name) else "Human"

def sub_bucket(name):
    n = (name or "").lower()
    if is_ai(name):
        return None
    if "inhouse inf" in n or "in-house inf" in n:
        return "In-house Influencer"
    return "In-house"

# ============== Process ads_with_created.json ==============
with open(_os.path.join(BASE, "ads_with_created.json")) as f:
    ads_raw = json.load(f)

ads_created = []
unmatched_campaigns = set()
for a in ads_raw:
    cid = a.get("campaign_id")
    lang = CAMPAIGN_ID_TO_LANG.get(cid, None)
    if lang is None:
        unmatched_campaigns.add(cid)
        lang = "Other"
    name = a.get("name", "")
    created = a.get("created_time", "").split("T")[0]  # YYYY-MM-DD
    ads_created.append({
        "id": a["id"],
        "name": name,
        "cd": created,           # creation date
        "l": lang,               # language
        "tt": top_theme(name),   # AI or Human
        "st": sub_bucket(name),  # In-house / In-house Influencer / null
        "status": a.get("effective_status"),
    })

print(f"Processed {len(ads_created)} ads with created_time.")
if unmatched_campaigns:
    print(f"WARNING: {len(unmatched_campaigns)} unmatched campaign_ids: {unmatched_campaigns}")

# Save the slim version
with open(_os.path.join(BASE, "ads_created_compact.json"), "w") as f:
    json.dump(ads_created, f, separators=(",", ":"))

# Quick stats
by_date_total = defaultdict(int)
by_date_ai = defaultdict(int)
by_date_hum = defaultdict(int)
for a in ads_created:
    by_date_total[a["cd"]] += 1
    if a["tt"] == "AI":
        by_date_ai[a["cd"]] += 1
    else:
        by_date_hum[a["cd"]] += 1

print(f"\nNew creatives per day (last 10 dates):")
for d in sorted(by_date_total.keys())[-10:]:
    print(f"  {d}: total={by_date_total[d]}  AI={by_date_ai[d]}  Human={by_date_hum[d]}")

# ============== Process ad_weekly_spend.json ==============
with open(_os.path.join(BASE, "ad_weekly_spend.json")) as f:
    weekly_raw = json.load(f)

# Re-parse language from ad's campaign_name (which IS in this file)
LANG_RE = re.compile(r"-(HSM|ML|TL|KA|BN|MT|TN|GT)-")
LANG_MAP = {"HSM":"Hindi (HSM)","ML":"Malayalam (ML)","TL":"Telugu (TL)","KA":"Kannada (KA)",
            "BN":"Bengali (BN)","MT":"Marathi (MT)","TN":"Tamil (TN)","GT":"Gujarati (GT)"}

def parse_lang_from_campaign(cn):
    m = LANG_RE.search(cn or "")
    return LANG_MAP[m.group(1)] if m else "Other"

ad_weekly = []
for r in weekly_raw:
    spend = float(r.get("spend", 0))
    impressions = float(r.get("impressions", 0))
    clicks = float(r.get("clicks", 0))
    purchases = 0
    installs = 0
    for action in r.get("actions", []):
        if action.get("action_type") == "purchase":
            purchases = float(action.get("value", 0))
        elif action.get("action_type") == "mobile_app_install":
            installs = float(action.get("value", 0))
    name = r.get("ad_name", "")
    ad_weekly.append({
        "ad_id": r.get("ad_id"),
        "ad_name": name,
        "l": parse_lang_from_campaign(r.get("campaign_name", "")),
        "tt": top_theme(name),
        "st": sub_bucket(name),
        "week_start": r.get("date_start"),
        "week_end": r.get("date_stop"),
        "s": round(spend, 2),
        "pu": int(purchases),
        "i": int(installs),
        "im": int(impressions),
        "cl": int(clicks),
    })
print(f"\nProcessed {len(ad_weekly)} weekly ad rows.")

# Quick stats: active creatives per week (threshold ₹1,000)
THRESHOLDS = [500, 1000, 2000]
weeks = sorted({r["week_start"] for r in ad_weekly})
print(f"Weeks present: {weeks}")
for wk in weeks:
    print(f"\nWeek {wk}:")
    for thr in THRESHOLDS:
        rows = [r for r in ad_weekly if r["week_start"] == wk and r["s"] >= thr]
        ai = len({r["ad_id"] for r in rows if r["tt"] == "AI"})
        hu = len({r["ad_id"] for r in rows if r["tt"] == "Human"})
        print(f"  spend≥₹{thr:>5}: total={ai+hu:>3d}  AI={ai:>3d}  Human={hu:>3d}")

# Save compact
with open(_os.path.join(BASE, "ad_weekly_compact.json"), "w") as f:
    json.dump(ad_weekly, f, separators=(",", ":"))

# ============== Merge into superflow_compact.json ==============
with open(_os.path.join(BASE, "superflow_compact.json")) as f:
    data = json.load(f)
data["ads_created"] = ads_created
data["ad_weekly"] = ad_weekly
with open(_os.path.join(BASE, "superflow_compact.json"), "w") as f:
    f.write(json.dumps(data, separators=(",", ":")))

print(f"\nMerged into superflow_compact.json. Total size: {len(json.dumps(data)):,} bytes")
