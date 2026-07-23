"""Normalize cloud Meta Ads MCP output into refresh.py's raw input format.

The scheduled agent saves the raw responses from the cloud Meta Ads MCP
(`ads_get_ad_entities`) to three files, then runs this script, then runs
refresh.py. This isolates all the cloud-format parsing in one place so
refresh.py's proven merge logic stays untouched.

Cloud MCP quirks this handles:
  - money strings like "₹12,726.10 INR"  -> 12726.10
  - int strings like "8,035"                        -> 8035
  - "Not available"                                 -> 0
  - omni_purchase is the purchase count (action_type "purchase")
  - app installs: the cloud MCP now exposes `mobile_app_install` directly on
    campaign/ad rows — when present it is used. An optional cloud_installs.json
    (from the fb-ads MCP) still overrides if provided. If NO installs source is
    available at all, a ".installs_missing" marker is written so refresh.py
    records installs as null (blank) for the day rather than a misleading 0.
  - campaign name is resolved from campaign_id via the campaign-level dump
    (ad-level rows only carry campaign_id).
  - dates come back formatted ("June 25, 2026"); we stamp every row with the
    target_date passed on the CLI instead.

Input files (in this dir), each either a bare list, or the MCP wrapper
{"ad_entities": "<json-string>"} / {"ad_entities": [...]}:
    cloud_campaigns.json    campaign-level daily insights (id, name, amount_spent, actions:omni_purchase)
    cloud_ads.json          ad-level daily insights (id, name, campaign_id, amount_spent, impressions, clicks, actions:omni_purchase)
    cloud_ads_created.json  recent ads (id, name, campaign_id, created_time, effective_status)
    cloud_installs.json     OPTIONAL {"campaigns": {campaign_id: installs}, "ads": {ad_id: installs}} from fb-ads MCP

Usage:
    python3 normalize_cloud.py 2026-06-25
"""
import json
import os
import re
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))


def _unwrap(raw):
    """Accept a bare list or the MCP {"ad_entities": ...} wrapper."""
    if isinstance(raw, dict) and "ad_entities" in raw:
        raw = raw["ad_entities"]
    if isinstance(raw, str):
        raw = json.loads(raw)
    return raw or []


def load_entities(name):
    path = os.path.join(BASE, name)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return _unwrap(json.load(f))


def parse_money(v):
    if v is None:
        return 0.0
    s = str(v)
    if "not available" in s.lower():
        return 0.0
    s = s.replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else 0.0


def parse_int(v):
    if v is None:
        return 0
    s = str(v)
    if "not available" in s.lower():
        return 0
    s = s.replace(",", "")
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else 0


def to_iso(date_str):
    """'June 25, 2026' -> '2026-06-25'. Pass through anything already ISO."""
    if not date_str:
        return ""
    s = str(date_str).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s


def main():
    if len(sys.argv) < 2:
        print("usage: normalize_cloud.py YYYY-MM-DD")
        sys.exit(1)
    target_date = sys.argv[1]

    campaigns = load_entities("cloud_campaigns.json")
    ads = load_entities("cloud_ads.json")
    created = load_entities("cloud_ads_created.json")

    # Optional installs source (fb-ads MCP). Absent => installs not collected.
    installs_path = os.path.join(BASE, "cloud_installs.json")
    inst_campaigns, inst_ads, installs_collected = {}, {}, False
    if os.path.exists(installs_path):
        with open(installs_path) as f:
            inst = json.load(f)
        inst_campaigns = {str(k): parse_int(v) for k, v in inst.get("campaigns", {}).items()}
        inst_ads = {str(k): parse_int(v) for k, v in inst.get("ads", {}).items()}
        installs_collected = True

    # The cloud Meta Ads MCP now exposes `mobile_app_install` directly on
    # campaign/ad rows. If the field is present in the dumps, installs are
    # collected from the cloud (no separate cloud_installs.json needed).
    cloud_has_installs = (any("mobile_app_install" in c for c in campaigns)
                          or any("mobile_app_install" in a for a in ads))
    if cloud_has_installs:
        installs_collected = True

    # campaign_id -> campaign name (from campaign-level dump)
    cid_to_name = {str(c.get("id")): c.get("name", "") for c in campaigns}

    # ---- daily_raw.json (campaign-level, per day) ----
    daily_raw = []
    for c in campaigns:
        cid = str(c.get("id"))
        actions = [{"action_type": "purchase", "value": parse_int(c.get("actions:omni_purchase"))}]
        if cid in inst_campaigns:
            actions.append({"action_type": "mobile_app_install", "value": inst_campaigns[cid]})
        elif "mobile_app_install" in c:
            actions.append({"action_type": "mobile_app_install", "value": parse_int(c.get("mobile_app_install"))})
        daily_raw.append({
            "date_start": target_date,
            "campaign_name": c.get("name", ""),
            "spend": parse_money(c.get("amount_spent")),
            "actions": actions,
        })

    # ---- ads_raw.json (ad-level, per day) ----
    ads_raw = []
    for a in ads:
        aid = str(a.get("id"))
        cid = str(a.get("campaign_id"))
        actions = [{"action_type": "purchase", "value": parse_int(a.get("actions:omni_purchase"))}]
        if aid in inst_ads:
            actions.append({"action_type": "mobile_app_install", "value": inst_ads[aid]})
        elif "mobile_app_install" in a:
            actions.append({"action_type": "mobile_app_install", "value": parse_int(a.get("mobile_app_install"))})
        ads_raw.append({
            "ad_id": aid,
            "ad_name": a.get("name", ""),
            "campaign_name": cid_to_name.get(cid, ""),
            "spend": parse_money(a.get("amount_spent")),
            "impressions": parse_int(a.get("impressions")),
            "clicks": parse_int(a.get("clicks")),
            "actions": actions,
        })

    # ---- ads_created_raw.json ----
    ads_created_raw = []
    for a in created:
        cid = str(a.get("campaign_id"))
        ads_created_raw.append({
            "id": str(a.get("id")),
            "name": a.get("name", ""),
            "campaign": {"name": cid_to_name.get(cid, "")},
            "created_time": to_iso(a.get("created_time")),
            "effective_status": a.get("effective_status", ""),
        })

    with open(os.path.join(BASE, "daily_raw.json"), "w") as f:
        json.dump(daily_raw, f)
    with open(os.path.join(BASE, "ads_raw.json"), "w") as f:
        json.dump(ads_raw, f)
    with open(os.path.join(BASE, "ads_created_raw.json"), "w") as f:
        json.dump(ads_created_raw, f)

    marker = os.path.join(BASE, ".installs_missing")
    if installs_collected:
        if os.path.exists(marker):
            os.remove(marker)
    else:
        open(marker, "w").close()

    print(f"normalize_cloud: {len(daily_raw)} campaigns, {len(ads_raw)} ads, "
          f"{len(ads_created_raw)} created ads, installs_collected={installs_collected}")


if __name__ == "__main__":
    main()
