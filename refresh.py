"""Incremental refresh for Superflow dashboard.
Reads yesterday's raw API data (saved by the scheduled agent), merges with
the cached superflow_compact.json, and rebuilds the dashboard HTML.

Data is ACCUMULATED — older days are never removed. The timeline grows with
each refresh (e.g. May 24 → Jun 22 becomes May 24 → Jun 23 the next day).

Usage:
    python3 refresh.py                    # auto-detects yesterday
    python3 refresh.py 2026-06-22         # explicit date

Expected input files (written by the scheduled agent before calling this):
    daily_raw.json       — campaign-level insights for yesterday (time_increment=1)
    ads_raw.json         — ad-level insights for yesterday only (1 day, to accumulate)
    ads_created_raw.json — newly created ads (from get_ads_by_adaccount)
"""
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
COMPACT = os.path.join(BASE, "superflow_compact.json")

LANG_MAP = {
    "HSM": "Hindi (HSM)", "ML": "Malayalam (ML)", "TL": "Telugu (TL)",
    "KA": "Kannada (KA)", "BN": "Bengali (BN)", "MT": "Marathi (MT)",
    "TN": "Tamil (TN)", "GT": "Gujarati (GT)",
}
LANG_RE = re.compile(r"-(HSM|ML|TL|KA|BN|MT|TN|GT)-")
PRICE_RE = re.compile(r"-(10\+199|10\+149|199|99)-")

AI_FX_KEYWORDS = [
    "kbh", "tractor beam", "red marker", "phone axe", "axe",
    "keyboard hammer", "hammer", "wrecking", "drill", "pyro",
    "lightning", "blackhole", "black hole", "trex", "t-rex",
    "energy burst", "energy", "steamroller", "hydraulic", "nitrogen",
    "cosmic", "404", "chalkboard", "cursor trash", "camerazoom",
]

def parse_lang(campaign_name):
    m = LANG_RE.search(campaign_name or "")
    return LANG_MAP[m.group(1)] if m else "Other"

def parse_price(campaign_name):
    m = PRICE_RE.search(campaign_name or "")
    return m.group(1) if m else "Other"

def is_ai(name):
    n = (name or "").lower()
    if re.search(r" ai |-ai-| ai-|-ai ", " " + n + " "):
        return True
    if "translated" in n:
        return True
    return any(kw in n for kw in AI_FX_KEYWORDS)

def classify(name):
    n = (name or "").lower()
    if is_ai(name):
        top, sub = "AI", None
    else:
        top = "Human"
        if "inhouse inf" in n or "in-house inf" in n:
            sub = "In-house Influencer"
        else:
            sub = "In-house"
    subs = []
    pi_kw = AI_FX_KEYWORDS + ["bulldozer", "tank", "pattern interrupt", "pattern-interrupt"]
    if any(k in n for k in pi_kw): subs.append("Pattern Interrupt")
    if "bhumi" in n: subs.append("Bhumi Replication")
    if "how to say this" in n: subs.append("How-to-say-this")
    if any(k in n for k in ["wa chat", "whatsapp", "wp chat"]): subs.append("WhatsApp Chat")
    if "testimonial" in n: subs.append("Testimonial")
    if "ots ads" in n or "ots ad" in n: subs.append("OTS")
    if any(k in n for k in ["frustrated", "disappointed", "humiliation", "stressing"]): subs.append("Pain Point")
    if "game screen" in n or "game recording" in n: subs.append("Game/App Screen")
    if "news anchor" in n: subs.append("News Anchor")
    if "weird cam" in n: subs.append("Weird Cam Angle")
    if "statics" in n or " static " in f" {n} " or n.endswith("static"): subs.append("Static")
    if "ots" in n and "OTS" not in subs: subs.append("OTS")
    if not subs: subs.append("Uncategorized")
    return top, sub, subs

def extract_actions(actions_list, action_type):
    for a in (actions_list or []):
        if a.get("action_type") == action_type:
            return float(a.get("value", 0))
    return 0

def load_json(path):
    with open(path) as f:
        return json.load(f)

def save_json(path, data, compact=True):
    with open(path, "w") as f:
        if compact:
            json.dump(data, f, separators=(",", ":"))
        else:
            json.dump(data, f, indent=2)

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"Refreshing for date: {target_date}")

    data = load_json(COMPACT)

    # ── 1. Update trend_account (append yesterday's daily row) ──────────
    daily_raw_path = os.path.join(BASE, "daily_raw.json")
    if os.path.exists(daily_raw_path):
        daily_rows = load_json(daily_raw_path)
        if isinstance(daily_rows, dict) and "data" in daily_rows:
            daily_rows = daily_rows["data"]

        existing_dates = {r["date"] for r in data["trend_account"]}

        # Account-level totals for the day
        day_total = defaultdict(lambda: {"spend": 0, "purchases": 0, "installs": 0})
        day_by_lang = defaultdict(lambda: defaultdict(lambda: {"spend": 0, "purchases": 0, "installs": 0}))

        for row in daily_rows:
            date = row.get("date_start", "")[:10]
            spend = float(row.get("spend", 0))
            purchases = extract_actions(row.get("actions"), "purchase")
            installs = extract_actions(row.get("actions"), "mobile_app_install")
            lang = parse_lang(row.get("campaign_name", ""))

            day_total[date]["spend"] += spend
            day_total[date]["purchases"] += purchases
            day_total[date]["installs"] += installs
            day_by_lang[lang][date]["spend"] += spend
            day_by_lang[lang][date]["purchases"] += purchases
            day_by_lang[lang][date]["installs"] += installs

        for date in sorted(day_total.keys()):
            if date in existing_dates:
                for r in data["trend_account"]:
                    if r["date"] == date:
                        r["spend"] = round(day_total[date]["spend"], 2)
                        r["purchases"] = int(day_total[date]["purchases"])
                        r["installs"] = int(day_total[date]["installs"])
                        r["cac"] = round(r["spend"] / r["purchases"], 2) if r["purchases"] > 0 else None
                        r["cpi"] = round(r["spend"] / r["installs"], 2) if r["installs"] > 0 else None
                        break
            else:
                v = day_total[date]
                s, p, i = round(v["spend"], 2), int(v["purchases"]), int(v["installs"])
                data["trend_account"].append({
                    "date": date, "spend": s, "purchases": p, "installs": i,
                    "cac": round(s / p, 2) if p > 0 else None,
                    "cpi": round(s / i, 2) if i > 0 else None,
                })

        data["trend_account"].sort(key=lambda r: r["date"])

        # Per-language trends
        if "trend_by_language" not in data:
            data["trend_by_language"] = {}
        for lang, dates in day_by_lang.items():
            if lang not in data["trend_by_language"]:
                data["trend_by_language"][lang] = []
            existing_lang_dates = {r["date"] for r in data["trend_by_language"][lang]}
            for date in sorted(dates.keys()):
                v = dates[date]
                s, p, i = round(v["spend"], 2), int(v["purchases"]), int(v["installs"])
                row = {
                    "date": date, "spend": s, "purchases": p, "installs": i,
                    "cac": round(s / p, 2) if p > 0 else None,
                    "cpi": round(s / i, 2) if i > 0 else None,
                }
                if date in existing_lang_dates:
                    for r in data["trend_by_language"][lang]:
                        if r["date"] == date:
                            r.update(row)
                            break
                else:
                    data["trend_by_language"][lang].append(row)
            data["trend_by_language"][lang].sort(key=lambda r: r["date"])

        print(f"  Trends updated: {len(day_total)} day(s), {len(day_by_lang)} language(s)")
    else:
        print("  No daily_raw.json — skipping trend update")

    # ── 2. Update ads (accumulate yesterday's per-ad spend onto totals) ──
    ads_raw_path = os.path.join(BASE, "ads_raw.json")
    if os.path.exists(ads_raw_path):
        ads_raw = load_json(ads_raw_path)
        if isinstance(ads_raw, dict) and "data" in ads_raw:
            ads_raw = ads_raw["data"]

        existing_by_id = {a["id"]: a for a in data.get("ads", [])}
        updated = 0
        added = 0
        for a in ads_raw:
            aid = a.get("ad_id", "")
            name = a.get("ad_name", "")
            campaign = a.get("campaign_name", "")
            lang = parse_lang(campaign)
            price = parse_price(campaign)
            top, sub, subs = classify(name)
            spend = float(a.get("spend", 0))
            purchases = extract_actions(a.get("actions"), "purchase")
            installs = extract_actions(a.get("actions"), "mobile_app_install")
            impressions = float(a.get("impressions", 0))
            clicks = float(a.get("clicks", 0))

            if aid in existing_by_id:
                ad = existing_by_id[aid]
                ad["s"] = round(ad["s"] + spend, 2)
                ad["pu"] += int(purchases)
                ad["i"] += int(installs)
                ad["im"] += int(impressions)
                ad["cl"] += int(clicks)
                ad["cac"] = round(ad["s"] / ad["pu"], 2) if ad["pu"] > 0 else None
                ad["cpi"] = round(ad["s"] / ad["i"], 2) if ad["i"] > 0 else None
                ad["ctr"] = round(ad["cl"] / ad["im"] * 100, 3) if ad["im"] > 0 else None
                updated += 1
            else:
                data["ads"].append({
                    "id": aid, "n": name, "c": campaign, "l": lang, "p": price,
                    "s": round(spend, 2), "pu": int(purchases), "i": int(installs),
                    "im": int(impressions), "cl": int(clicks),
                    "cac": round(spend / purchases, 2) if purchases > 0 else None,
                    "cpi": round(spend / installs, 2) if installs > 0 else None,
                    "ctr": round(clicks / impressions * 100, 3) if impressions > 0 else None,
                    "tt": top, "st": sub, "subs": subs,
                })
                added += 1
        print(f"  Ads: {updated} updated, {added} new, {len(data['ads'])} total")
    else:
        print("  No ads_raw.json — keeping cached ads")

    # ── 3. Update ads_created (newly created ads) ───────────────────────
    created_raw_path = os.path.join(BASE, "ads_created_raw.json")
    if os.path.exists(created_raw_path):
        created_raw = load_json(created_raw_path)
        if isinstance(created_raw, dict) and "data" in created_raw:
            created_raw = created_raw["data"]

        existing_ids = {a["id"] for a in data.get("ads_created", [])}
        added = 0
        for a in created_raw:
            aid = a.get("id", "")
            if aid in existing_ids:
                continue
            name = a.get("name", "")
            campaign = a.get("campaign", {}).get("name", "") if isinstance(a.get("campaign"), dict) else ""
            lang = parse_lang(campaign) if campaign else "Other"
            created = (a.get("created_time", "") or "")[:10]
            data.setdefault("ads_created", []).append({
                "id": aid,
                "n": name,
                "c": campaign,
                "l": lang,
                "cd": created,
                "status": a.get("effective_status", ""),
            })
            added += 1
        print(f"  Ads created: {added} new, {len(data.get('ads_created', []))} total")
    else:
        print("  No ads_created_raw.json — keeping cached")

    # ── 4. Save and rebuild ─────────────────────────────────────────────
    data["generated_at"] = datetime.now().isoformat()
    save_json(COMPACT, data)
    print(f"  Saved {os.path.getsize(COMPACT):,} bytes to superflow_compact.json")

    print("  Rebuilding dashboard HTML...")
    result = subprocess.run(
        [sys.executable, os.path.join(BASE, "build_dashboard.py")],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  {result.stdout.strip()}")
    else:
        print(f"  BUILD ERROR: {result.stderr}")
        sys.exit(1)

    # Clean up raw files
    for f in ["daily_raw.json", "ads_raw.json", "ads_created_raw.json"]:
        path = os.path.join(BASE, f)
        if os.path.exists(path):
            os.remove(path)

    print("Done.")

if __name__ == "__main__":
    main()
