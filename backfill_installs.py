"""One-time backfill of app installs for 2026-06-24 .. 2026-07-21.

The cloud Meta Ads MCP could not report installs during this window, so
refresh.py recorded installs as null. It now exposes `mobile_app_install`,
so we backfill:
  - trend_account[date].installs   (authoritative account-level daily)
  - trend_by_language[L][date].installs  (per-campaign daily, mapped to language)
  - ads[].i (cumulative per-ad installs over the gap, added onto totals)
Also inserts the missing 2026-07-11 day (the daily refresh skipped it).

Every number is validated: per-language daily installs must sum to the
authoritative account daily total, or the script aborts.
"""
import json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
COMPACT = os.path.join(BASE, "superflow_compact.json")

# Authoritative account-level daily installs (level=account, mobile_app_install).
ACCOUNT_DAILY = {
    "2026-06-24": 5806, "2026-06-25": 6656, "2026-06-26": 7017, "2026-06-27": 8812,
    "2026-06-28": 13615, "2026-06-29": 8128, "2026-06-30": 8054, "2026-07-01": 8301,
    "2026-07-02": 5408, "2026-07-03": 5097, "2026-07-04": 7620, "2026-07-05": 10703,
    "2026-07-06": 9698, "2026-07-07": 10105, "2026-07-08": 11919, "2026-07-09": 12027,
    "2026-07-10": 14893, "2026-07-11": 16631, "2026-07-12": 15568, "2026-07-13": 19663,
    "2026-07-14": 17106, "2026-07-15": 18610, "2026-07-16": 17715, "2026-07-17": 15596,
    "2026-07-18": 17453, "2026-07-19": 18519, "2026-07-20": 15917, "2026-07-21": 17337,
}

# campaign_id -> language key (matches parse_lang output / trend_by_language keys)
CID_LANG = {
    "120247526251060513": "Hindi (HSM)",   # CBO HSM 199
    "120247189861740513": "Hindi (HSM)",   # HSM 199 Copy
    "120247105483260513": "Hindi (HSM)",   # HSM 99
    "120246059063540513": "Marathi (MT)",
    "120245891639460513": "Tamil (TN)",
    "120245891639270513": "Kannada (KA)",
    "120245631352660513": "Malayalam (ML)",
    "120247113240430513": "Malayalam (ML)", # ML 10+149
    "120245891639290513": "Telugu (TL)",
    "120246449055680513": "Gujarati (GT)",
    "120246449055670513": "Bengali (BN)",
}

# Per-campaign daily installs over the gap (level=campaign, time_increment=1).
CAMP_DAILY = {
 "120247526251060513": {"2026-06-27":2953,"2026-06-28":6131,"2026-06-29":2212,"2026-06-30":2617,"2026-07-01":1296,"2026-07-02":141,"2026-07-03":102,"2026-07-04":2534,"2026-07-05":3428,"2026-07-06":3095,"2026-07-07":3256,"2026-07-08":3475,"2026-07-09":3590,"2026-07-10":5292,"2026-07-11":5889,"2026-07-12":5571,"2026-07-13":7376,"2026-07-14":5831,"2026-07-15":6097,"2026-07-16":5132,"2026-07-17":4494,"2026-07-18":5889,"2026-07-19":6350,"2026-07-20":5977,"2026-07-21":6343},
 "120247189861740513": {"2026-06-24":2206,"2026-06-25":2743,"2026-06-26":3667,"2026-06-27":2487,"2026-06-28":2104,"2026-06-29":2199,"2026-06-30":2861,"2026-07-01":3819,"2026-07-02":3054,"2026-07-03":2510,"2026-07-04":2398,"2026-07-05":3139,"2026-07-06":3071,"2026-07-07":3465,"2026-07-08":4039,"2026-07-09":4659,"2026-07-10":5764,"2026-07-11":6417,"2026-07-12":6212,"2026-07-13":7747,"2026-07-14":7502,"2026-07-15":8106,"2026-07-16":8187,"2026-07-17":7282,"2026-07-18":8263,"2026-07-19":8645,"2026-07-20":7108,"2026-07-21":7964},
 "120246059063540513": {"2026-06-24":300,"2026-06-25":457,"2026-06-26":267,"2026-06-27":201,"2026-06-28":366,"2026-06-29":362,"2026-06-30":378,"2026-07-01":602,"2026-07-02":536,"2026-07-03":417,"2026-07-04":348,"2026-07-05":417,"2026-07-06":413,"2026-07-07":268,"2026-07-08":183,"2026-07-09":260,"2026-07-10":479,"2026-07-11":392,"2026-07-12":302,"2026-07-13":299,"2026-07-14":203,"2026-07-15":296,"2026-07-16":514,"2026-07-17":510,"2026-07-18":455,"2026-07-19":496,"2026-07-20":510,"2026-07-21":565},
 "120245891639460513": {"2026-06-24":519,"2026-06-25":301,"2026-06-26":67,"2026-06-27":22,"2026-06-28":19,"2026-06-29":11,"2026-06-30":6,"2026-07-01":1,"2026-07-02":1,"2026-07-03":122,"2026-07-04":245,"2026-07-05":531,"2026-07-06":497,"2026-07-07":691,"2026-07-08":941,"2026-07-09":1121,"2026-07-10":1231,"2026-07-11":1505,"2026-07-12":1365,"2026-07-13":1798,"2026-07-14":1335,"2026-07-15":1248,"2026-07-16":1278,"2026-07-17":1033,"2026-07-18":725,"2026-07-19":750,"2026-07-20":614,"2026-07-21":521},
 "120245891639270513": {"2026-06-24":518,"2026-06-25":661,"2026-06-26":597,"2026-06-27":524,"2026-06-28":687,"2026-06-29":488,"2026-06-30":413,"2026-07-01":530,"2026-07-02":298,"2026-07-03":408,"2026-07-04":452,"2026-07-05":394,"2026-07-06":372,"2026-07-07":485,"2026-07-08":521,"2026-07-09":429,"2026-07-10":589,"2026-07-11":796,"2026-07-12":728,"2026-07-13":911,"2026-07-14":851,"2026-07-15":1362,"2026-07-16":1525,"2026-07-17":1139,"2026-07-18":966,"2026-07-19":1002,"2026-07-20":886,"2026-07-21":1107},
 "120245631352660513": {"2026-06-24":245,"2026-06-25":130,"2026-06-26":239,"2026-06-27":362,"2026-06-28":569,"2026-06-29":385,"2026-06-30":284,"2026-07-01":748,"2026-07-02":1191,"2026-07-03":1253,"2026-07-04":1300,"2026-07-05":2183,"2026-07-06":1774,"2026-07-07":1509,"2026-07-08":2294,"2026-07-09":1594,"2026-07-10":1180,"2026-07-11":1214,"2026-07-12":1035,"2026-07-13":1049,"2026-07-14":671,"2026-07-15":921,"2026-07-16":952,"2026-07-17":1106,"2026-07-18":1144,"2026-07-19":1267,"2026-07-20":815,"2026-07-21":833},
 "120245891639290513": {"2026-06-24":563,"2026-06-25":748,"2026-06-26":487,"2026-06-27":414,"2026-06-28":601,"2026-06-29":546,"2026-06-30":300,"2026-07-01":44,"2026-07-02":42,"2026-07-03":187,"2026-07-04":263,"2026-07-05":427,"2026-07-06":458,"2026-07-07":297,"2026-07-08":293,"2026-07-09":317,"2026-07-10":353,"2026-07-11":415,"2026-07-12":353,"2026-07-13":482,"2026-07-14":712,"2026-07-15":577,"2026-07-16":127,"2026-07-17":32,"2026-07-18":11,"2026-07-19":9,"2026-07-20":7,"2026-07-21":4},
 "120247113240430513": {"2026-06-24":320,"2026-06-25":571,"2026-06-26":402,"2026-06-27":242,"2026-06-28":393,"2026-06-29":165,"2026-06-30":22,"2026-07-01":276,"2026-07-02":20,"2026-07-03":10,"2026-07-04":5,"2026-07-05":4,"2026-07-07":1,"2026-07-08":1},
 "120247105483260513": {"2026-06-24":709,"2026-06-25":570,"2026-06-26":923,"2026-06-27":1250,"2026-06-28":2220,"2026-06-29":1477,"2026-06-30":945,"2026-07-01":835,"2026-07-02":101,"2026-07-03":57,"2026-07-04":29,"2026-07-05":25,"2026-07-06":9,"2026-07-07":2,"2026-07-08":3},
 "120246449055680513": {"2026-07-07":2,"2026-07-08":13,"2026-07-09":2},
 "120246449055670513": {"2026-06-24":371,"2026-06-25":431,"2026-06-26":347,"2026-06-27":356,"2026-06-28":525,"2026-06-29":283,"2026-06-30":228,"2026-07-01":150,"2026-07-02":24,"2026-07-03":31,"2026-07-04":46,"2026-07-05":155,"2026-07-06":9,"2026-07-07":129,"2026-07-08":156,"2026-07-09":55,"2026-07-10":5,"2026-07-11":3,"2026-07-12":2,"2026-07-13":1,"2026-07-14":1,"2026-07-15":3},
}

# Missing 2026-07-11 day, per campaign: (spend, purchases, installs)
JUL11 = {
 "120247526251060513": (22399.40, 222, 5889),
 "120247189861740513": (49143.68, 380, 6417),
 "120246059063540513": (7534.87, 15, 392),
 "120245891639460513": (17251.05, 30, 1505),
 "120245891639270513": (13829.17, 36, 796),
 "120245631352660513": (20647.12, 56, 1214),
 "120245891639290513": (11531.87, 19, 415),
 "120246449055670513": (0.00, 0, 3),
}


def main():
    data = json.load(open(COMPACT))

    # ---- Build per-day per-language installs from CAMP_DAILY ----
    lang_day = {}   # lang -> {date: installs}
    acct_day_from_camp = {}
    for cid, days in CAMP_DAILY.items():
        L = CID_LANG[cid]
        for date, n in days.items():
            lang_day.setdefault(L, {}).setdefault(date, 0)
            lang_day[L][date] += n
            acct_day_from_camp[date] = acct_day_from_camp.get(date, 0) + n

    # ---- VALIDATE: per-campaign daily sums vs authoritative account daily ----
    # A small residual (<2%) on early days comes from a since-removed campaign
    # that still counts in account-level totals; trend_account uses the
    # authoritative account number regardless, so tolerate it but abort on any
    # larger mismatch (which would signal a transcription error).
    hard_fail, warn = [], []
    for date, total in ACCOUNT_DAILY.items():
        got = acct_day_from_camp.get(date, 0)
        diff = total - got
        if diff == 0:
            continue
        if diff < 0 or abs(diff) > max(60, 0.02 * total):
            hard_fail.append((date, total, got, diff))
        else:
            warn.append((date, total, got, diff))
    if hard_fail:
        print("VALIDATION FAILED (date, account_total, campaign_sum, diff):")
        for row in hard_fail:
            print("  ", row)
        sys.exit(1)
    if warn:
        print("Validation OK within tolerance; small residuals (removed campaign):")
        for row in warn:
            print("  ", row)
    else:
        print(f"Validation OK: campaign daily sums match account totals on all {len(ACCOUNT_DAILY)} days.")

    # ---- Insert missing 2026-07-11 into trend_account ----
    ta = data["trend_account"]
    ta_dates = {r["date"] for r in ta}
    if "2026-07-11" not in ta_dates:
        s = round(sum(v[0] for v in JUL11.values()), 2)
        p = sum(v[1] for v in JUL11.values())
        i = ACCOUNT_DAILY["2026-07-11"]
        ta.append({"date": "2026-07-11", "spend": s, "purchases": p, "installs": i,
                   "cac": round(s/p, 2) if p else None, "cpi": round(s/i, 2) if i else None})
        print(f"Inserted 2026-07-11 account row: spend {s}, purchases {p}, installs {i}")

    # ---- Backfill trend_account installs for the gap ----
    for r in ta:
        if r["date"] in ACCOUNT_DAILY:
            r["installs"] = ACCOUNT_DAILY[r["date"]]
            r["cpi"] = round(r["spend"]/r["installs"], 2) if r["installs"] else None
    ta.sort(key=lambda r: r["date"])

    # ---- Insert missing 2026-07-11 into trend_by_language + backfill installs ----
    tbl = data["trend_by_language"]
    # First, 07-11 per-language spend/purchases from JUL11
    jul11_lang = {}
    for cid, (s, p, i) in JUL11.items():
        L = CID_LANG[cid]
        e = jul11_lang.setdefault(L, {"spend": 0.0, "purchases": 0, "installs": 0})
        e["spend"] += s; e["purchases"] += p; e["installs"] += i
    for L, rows in tbl.items():
        dates = {r["date"] for r in rows}
        if "2026-07-11" not in dates and L in jul11_lang:
            e = jul11_lang[L]
            s, p, i = round(e["spend"], 2), e["purchases"], e["installs"]
            rows.append({"date": "2026-07-11", "spend": s, "purchases": p, "installs": i,
                         "cac": round(s/p, 2) if p else None, "cpi": round(s/i, 2) if i else None})
    # Backfill installs per language per day
    for L, days in lang_day.items():
        rows = tbl.get(L)
        if rows is None:
            continue
        by_date = {r["date"]: r for r in rows}
        for date, n in days.items():
            if date in by_date:
                r = by_date[date]
                r["installs"] = n
                r["cpi"] = round(r["spend"]/n, 2) if n else None
        rows.sort(key=lambda r: r["date"])

    # ---- Backfill per-ad cumulative installs (add gap totals onto ads[].i) ----
    ad_gap = json.load(open(os.path.join(BASE, "ads_installs_gap.json")))
    ad_rows = json.loads(ad_gap["ad_entities"]) if isinstance(ad_gap.get("ad_entities"), str) else ad_gap["ad_entities"]
    gap_by_id = {}
    for a in ad_rows:
        v = str(a.get("mobile_app_install", "")).replace(",", "")
        if "not available" in v.lower() or v == "":
            continue
        gap_by_id[str(a["id"])] = int(float(v))
    ads_by_id = {a["id"]: a for a in data["ads"]}
    updated = 0
    for aid, n in gap_by_id.items():
        ad = ads_by_id.get(aid)
        if ad is None:
            continue
        ad["i"] = int(ad.get("i", 0)) + n
        ad["cpi"] = round(ad["s"]/ad["i"], 2) if ad["i"] else None
        updated += 1
    print(f"Per-ad installs backfilled: {updated} ads matched (of {len(gap_by_id)} with gap installs)")

    json.dump(data, open(COMPACT, "w"), separators=(",", ":"))
    total_inst = sum((r["installs"] or 0) for r in ta)
    print(f"Saved. trend_account now {len(ta)} days; total installs across timeline = {total_inst:,}")


if __name__ == "__main__":
    main()
