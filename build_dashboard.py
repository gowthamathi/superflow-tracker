"""Build the Superflow dashboard HTML v3.
Adds: creative cadence charts (Chart A), active-pool charts with CPI overlay (Chart B),
themes-tab cadence chart with filters, KPI-bug fix with live data banner & diagnostics."""
import json

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, 'superflow_compact.json')) as f:
    snapshot_obj = json.load(f)

# Keep only what JS needs (ads + trends + ads_created + ad_weekly)
slim_snapshot = {
    "ads": snapshot_obj["ads"],
    "trend_account": snapshot_obj["trend_account"],
    "trend_by_language": snapshot_obj["trend_by_language"],
    "ads_created": snapshot_obj.get("ads_created", []),
    "ad_weekly": snapshot_obj.get("ad_weekly", []),
    "generated_at": snapshot_obj.get("generated_at"),
}
slim_str = json.dumps(slim_snapshot, separators=(",", ":"))
print(f"slim snapshot: {len(slim_str):,} bytes")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Superflow Performance Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.js" integrity="sha384-iU8HYtnGQ8Cy4zl7gbNMOhsDTTKX02BTXptVP/vqAWIaTfM7isw76iyZCsjL2eVi" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/gridjs.umd.js" integrity="sha384-/XXDzxe4FsGiAe50i/u9pY/Vy/uX654MHB1xoc1BJNnH1WXHhqHga9g3q5tF4gj7" crossorigin="anonymous"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/theme/mermaid.min.css" integrity="sha384-jZvDSsmGB9oGGT/4l9bHXGoAv1OxvG/cFmSo0dZaSqmBgvQTKDBFAMftlXTmMbNW" crossorigin="anonymous">
<style>
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #fafafa; color: #1a1a1a; font-size: 14px; line-height: 1.5; }
.wrap { max-width: 1320px; margin: 0 auto; padding: 24px; }
h1 { font-size: 22px; margin: 0 0 4px 0; font-weight: 700; letter-spacing: -0.02em; }
h2 { font-size: 16px; margin: 24px 0 12px 0; font-weight: 600; padding-bottom: 6px; border-bottom: 1px solid #e5e5e5;}
h3 { font-size: 12px; margin: 0 0 8px 0; font-weight: 600; color: #525252; text-transform: uppercase; letter-spacing: 0.05em; }
.subtitle { color: #737373; font-size: 13px; margin-bottom: 12px; }
.subtitle span.period { color: #1a1a1a; font-weight: 500; }
.header-row { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }

.date-bar { background: white; border: 1px solid #e5e5e5; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.date-bar .presets { display: flex; gap: 4px; flex-wrap: wrap; }
.date-bar .preset-btn { padding: 5px 10px; border-radius: 4px; background: #f5f5f5; border: 1px solid transparent; font-size: 12px; cursor: pointer; color: #404040; font-weight: 500; }
.date-bar .preset-btn:hover { background: #ebebeb; }
.date-bar .preset-btn.active { background: #1a1a1a; color: white; }
.date-bar .custom { display: flex; gap: 6px; align-items: center; font-size: 12px; color: #525252; margin-left: 8px; }
.date-bar input[type=date] { padding: 4px 8px; border: 1px solid #d4d4d4; border-radius: 4px; font-size: 12px; background: white; }
.date-bar .apply { padding: 5px 10px; border-radius: 4px; background: #1a1a1a; color: white; border: 0; font-size: 12px; font-weight: 500; cursor: pointer; }
.date-bar .apply:hover { background: #404040; }
.data-source-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.data-source-badge.snapshot { background: #fef3c7; color: #92400e; }
.data-source-badge.live { background: #dcfce7; color: #166534; }
.data-source-badge.fetching { background: #dbeafe; color: #1e40af; }
.data-source-badge.error { background: #fee2e2; color: #991b1b; }
.error-banner { background: #fee2e2; color: #991b1b; padding: 10px 14px; border-radius: 6px; border: 1px solid #fecaca; margin-bottom: 12px; font-size: 13px; display: none; }
.error-banner.visible { display: block; }
.error-banner pre { font-size: 11px; margin: 4px 0 0; padding: 6px 8px; background: rgba(255,255,255,0.5); border-radius: 4px; overflow-x: auto; max-height: 100px; }

.kpi-strip { display: grid; grid-template-columns: repeat(8, 1fr); gap: 10px; margin: 8px 0 16px; }
.kpi { background: white; border-radius: 8px; padding: 12px 14px; border: 1px solid #e5e5e5; }
.kpi .label { font-size: 10px; color: #737373; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi .value { font-size: 20px; font-weight: 700; margin-top: 3px; letter-spacing: -0.02em; }
.kpi .sub { font-size: 10px; color: #737373; margin-top: 2px; }
.kpi.target-ok .value { color: #15803d; }
.kpi.target-warn .value { color: #b45309; }
.kpi.target-bad .value { color: #b91c1c; }
@media (max-width: 1100px) { .kpi-strip { grid-template-columns: repeat(4, 1fr); } }

.tabs { display: flex; gap: 4px; border-bottom: 1px solid #e5e5e5; margin: 16px 0 0 0; flex-wrap: wrap; }
.tab { padding: 10px 16px; cursor: pointer; font-size: 13px; font-weight: 500; color: #525252; border-bottom: 2px solid transparent; margin-bottom: -1px; user-select: none; }
.tab:hover { color: #1a1a1a; }
.tab.active { color: #1a1a1a; border-bottom-color: #1a1a1a; }
.tab-content { display: none; padding: 16px 0; }
.tab-content.active { display: block; }

.card { background: white; border: 1px solid #e5e5e5; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
.card.no-pad { padding: 0; overflow: hidden; }
.card-row { display: grid; gap: 12px; }
.card-row.cols-2 { grid-template-columns: 1fr 1fr; }
.card-row.cols-4 { grid-template-columns: repeat(4, 1fr); }
@media (max-width: 1100px) { .card-row.cols-4 { grid-template-columns: repeat(2, 1fr); } }

.chart-wrap { position: relative; height: 220px; }
.chart-wrap.short { height: 150px; }
.chart-wrap.tall { height: 380px; }

table.metrics { width: 100%; border-collapse: collapse; font-size: 13px; }
table.metrics th { text-align: left; padding: 8px 10px; font-weight: 600; color: #525252; background: #fafafa; border-bottom: 1px solid #e5e5e5; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap; }
table.metrics td { padding: 8px 10px; border-bottom: 1px solid #f1f1f1; }
table.metrics td.r, table.metrics th.r { text-align: right; }
table.metrics tr:last-child td { border-bottom: 0; }
table.metrics .name { font-weight: 500; }
table.metrics tr.indent-1 td:first-child { padding-left: 28px; font-weight: 400; color: #404040; }
table.metrics tfoot tr { background: #fafafa; font-weight: 700; }

.cell { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 11px; font-weight: 600; font-variant-numeric: tabular-nums; min-width: 40px; text-align: center; }
.cell.bg-green-strong { background: #bbf7d0; color: #14532d; }
.cell.bg-green { background: #dcfce7; color: #15803d; }
.cell.bg-yellow { background: #fef3c7; color: #b45309; }
.cell.bg-red { background: #fee2e2; color: #b91c1c; }
.cell.bg-red-strong { background: #fecaca; color: #7f1d1d; }
.cell.bg-grey { background: #f5f5f5; color: #525252; }
.cell.bg-purple { background: #ede9fe; color: #6d28d9; }
.cell.bg-cyan { background: #cffafe; color: #155e75; }
.row-bg-ai { background: #faf5ff; }
.row-bg-human { background: #ecfeff; }
.row-bg-statics { background: #f5f5f5; }
.row-bg-ai td:first-child, .row-bg-human td:first-child, .row-bg-statics td:first-child { font-weight: 700; }
.cell.bg-statics { background: #e5e5e5; color: #525252; }

.btn { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 6px; background: #1a1a1a; color: white; border: 0; font-size: 12px; font-weight: 500; cursor: pointer; }
.btn:hover { background: #404040; }
.btn.secondary { background: white; color: #1a1a1a; border: 1px solid #d4d4d4; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.note { font-size: 12px; color: #525252; padding: 8px 12px; background: #fafafa; border-left: 3px solid #d4d4d4; border-radius: 0 4px 4px 0; margin: 6px 0; }
.note b { color: #1a1a1a; }

.filter-row { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; padding: 10px 14px; background: white; border-radius: 6px; border: 1px solid #e5e5e5; }
.filter-row label { font-size: 12px; color: #525252; }
.filter-row select, .filter-row input { padding: 5px 8px; border: 1px solid #d4d4d4; border-radius: 5px; font-size: 12px; background: white; }
.granularity { display: inline-flex; border: 1px solid #d4d4d4; border-radius: 5px; overflow: hidden; }
.granularity button { padding: 5px 12px; border: 0; background: white; font-size: 12px; cursor: pointer; color: #525252; }
.granularity button.active { background: #1a1a1a; color: white; }
.threshold-toggle { display: inline-flex; border: 1px solid #d4d4d4; border-radius: 5px; overflow: hidden; }
.threshold-toggle button { padding: 5px 12px; border: 0; background: white; font-size: 12px; cursor: pointer; color: #525252; }
.threshold-toggle button.active { background: #1a1a1a; color: white; }

.gridjs-wrapper { box-shadow: none; border-radius: 6px; border: 1px solid #e5e5e5; }
.gridjs-table { font-size: 12px; }
.gridjs-th { font-size: 11px; }

.insight-card { display: flex; gap: 12px; margin-bottom: 10px; padding: 12px 14px; background: white; border: 1px solid #e5e5e5; border-radius: 6px; }
.insight-card .marker { width: 4px; flex-shrink: 0; border-radius: 2px; }
.insight-card.good .marker { background: #15803d; }
.insight-card.warn .marker { background: #b45309; }
.insight-card.bad .marker { background: #b91c1c; }
.insight-card .title { font-size: 13px; font-weight: 600; }
.insight-card .desc { font-size: 12px; color: #525252; margin-top: 3px; line-height: 1.5; }

.spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid #d4d4d4; border-top-color: #1a1a1a; border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: middle; }
@keyframes spin { to { transform: rotate(360deg); } }

.lang-chips { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.lang-chips .chip { padding: 4px 10px; border-radius: 14px; background: #f5f5f5; color: #525252; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid transparent; user-select: none; }
.lang-chips .chip:hover { background: #ebebeb; }
.lang-chips .chip.active { background: #1a1a1a; color: white; border-color: #1a1a1a; }
.lang-chips .chip-action { padding: 4px 10px; border-radius: 4px; background: white; border: 1px solid #d4d4d4; color: #525252; font-size: 11px; cursor: pointer; }
.lang-chips .chip-action:hover { background: #f5f5f5; }
.themes-filter-row { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; padding: 10px 14px; background: white; border-radius: 6px; border: 1px solid #e5e5e5; }
.themes-filter-row .label { font-size: 12px; color: #525252; font-weight: 500; }
.variant-section { background: white; border: 1px solid #e5e5e5; border-radius: 8px; overflow: hidden; margin-bottom: 12px; }
.variant-section h4 { margin: 0; font-size: 13px; font-weight: 700; padding: 12px 16px; background: #fafafa; border-bottom: 1px solid #e5e5e5; }
.variant-section table.metrics { margin: 0; }

.small-mult-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
@media (max-width: 1100px) { .small-mult-grid { grid-template-columns: repeat(2, 1fr); } }
.small-mult-card { background: white; border: 1px solid #e5e5e5; border-radius: 6px; padding: 10px; }
.small-mult-card .title { font-size: 12px; font-weight: 600; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }
.small-mult-card .title .val { font-size: 11px; color: #525252; font-variant-numeric: tabular-nums; }

.deep-dive-card { background: white; border: 1px solid #e5e5e5; border-radius: 8px; padding: 14px; margin-bottom: 12px; }
.deep-dive-card .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #f0f0f0; }
.deep-dive-card .header h3 { margin: 0; font-size: 14px; text-transform: none; letter-spacing: 0; }
.deep-dive-card .header .stats { font-size: 12px; color: #525252; font-variant-numeric: tabular-nums; }
.deep-dive-card .chart-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
@media (max-width: 1000px) { .deep-dive-card .chart-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 660px) { .deep-dive-card .chart-grid { grid-template-columns: 1fr; } }
.deep-dive-card .chart-cell h3 { font-weight: 600; font-size: 11px; color: #525252; margin-bottom: 6px; }
</style>
</head>
<body>
<div class="wrap">
  <div class="header-row">
    <div>
      <h1>Superflow — Meta Ads Performance</h1>
      <div class="subtitle">Account <code>act_939306131915438</code> · CAC target <span class="period">≤ ₹300</span></div>
    </div>
  </div>

  <div class="date-bar">
    <div class="presets" id="presets">
      <button class="preset-btn" data-days="7">Last 7d</button>
      <button class="preset-btn" data-days="14">Last 14d</button>
      <button class="preset-btn" data-days="28">Last 28d</button>
      <button class="preset-btn active" data-days="30">Last 30d</button>
      <button class="preset-btn" data-days="60">Last 60d</button>
      <button class="preset-btn" data-days="90">Last 90d</button>
    </div>
    <div class="custom">
      <label>Custom:</label>
      <input id="date-since" type="date">
      <span>→</span>
      <input id="date-until" type="date">
      <button class="apply" id="date-apply">Apply</button>
    </div>
    <span class="data-source-badge live" id="data-badge">Cache · May 24 → Jun 22</span>
  </div>

  <div class="note" style="margin-bottom: 12px;">
    <b>Cached dashboard.</b> Snapshot covers May 24 → Jun 22, 2026. Date selector filters this cached data client-side — no live API calls, no fetch errors. Headline KPIs, Languages table and Trends charts respect the selected date range. Campaigns, Themes, Variants and Creatives tabs always show the full 30-day aggregate (per-ad daily data isn't in the cache). To refresh: ask Claude to rebuild the snapshot. Production deploy will refresh automatically at 10am IST daily.
  </div>

  <div class="error-banner" id="error-banner"></div>

  <div class="kpi-strip" id="kpi-strip"></div>

  <div class="tabs">
    <div class="tab active" data-tab="languages">Languages</div>
    <div class="tab" data-tab="trends">Trends</div>
    <div class="tab" data-tab="campaigns">Campaigns & Variants</div>
    <div class="tab" data-tab="themes">Creative Themes</div>
    <div class="tab" data-tab="ads">All Creatives</div>
    <div class="tab" data-tab="insights">Insights</div>
  </div>

  <!-- LANGUAGES -->
  <div class="tab-content active" data-tab="languages">
    <div class="card no-pad">
      <table class="metrics" id="language-table">
        <thead><tr>
          <th>Language</th>
          <th class="r">Spend</th><th class="r">Spend %</th>
          <th class="r">Purchases</th><th class="r">Purch %</th>
          <th class="r">Installs</th>
          <th class="r">C2I %</th>
          <th class="r">Pay %</th>
          <th class="r">CAC</th>
          <th class="r">CPI</th>
          <th class="r">CTR</th>
          <th class="r">Creatives</th>
          <th class="r">≤₹300</th>
          <th class="r">Win Rate</th>
        </tr></thead>
        <tbody></tbody>
        <tfoot></tfoot>
      </table>
    </div>
    <div class="note">
      <b>C2I %</b> = installs ÷ clicks · <b>Pay %</b> = purchases ÷ installs · <b>CAC</b> = spend ÷ purchases · cells color-coded vs account baseline; green = better than average, red = worse.
    </div>
  </div>

  <!-- TRENDS -->
  <div class="tab-content" data-tab="trends">
    <div class="filter-row">
      <label>Granularity:</label>
      <div class="granularity" id="gran-toggle">
        <button data-gran="day" class="active">Daily (7-day rolling)</button>
        <button data-gran="week">Weekly</button>
      </div>
      <label style="margin-left: 16px;">Active threshold (Chart B):</label>
      <div class="threshold-toggle" id="thr-toggle">
        <button data-thr="500">₹500</button>
        <button data-thr="1000" class="active">₹1,000</button>
        <button data-thr="2000">₹2,000</button>
      </div>
    </div>

    <h2>Overall account trends</h2>
    <div class="card-row cols-4">
      <div class="card"><h3>CAC over time</h3><div class="chart-wrap"><canvas id="t-overall-cac"></canvas></div></div>
      <div class="card"><h3>CPI over time</h3><div class="chart-wrap"><canvas id="t-overall-cpi"></canvas></div></div>
      <div class="card"><h3>Pay % over time</h3><div class="chart-wrap"><canvas id="t-overall-pay"></canvas></div></div>
      <div class="card"><h3>Spend over time</h3><div class="chart-wrap"><canvas id="t-overall-spend"></canvas></div></div>
    </div>

    <h2>Per-language small multiples</h2>
    <div class="filter-row">
      <label>Metric:</label>
      <select id="sm-metric">
        <option value="cac">CAC</option>
        <option value="cpi">CPI</option>
        <option value="pay">Pay %</option>
        <option value="spend">Spend</option>
        <option value="purchases">Purchases</option>
      </select>
    </div>
    <div class="small-mult-grid" id="sm-grid"></div>

    <h2>Per-language deep-dive — incl. creative volume vs CPI</h2>
    <div class="note" style="margin-bottom:10px;">
      <b>Cadence chart</b> = new creatives launched per day (Total / AI / Human). <b>Active pool chart</b> = unique creatives with spend ≥ threshold in each week (Total / AI / Human) with CPI line overlay. If active count goes up and CPI goes down on the same chart, that's the correlation you're hunting for.
    </div>
    <div id="deep-dive"></div>
  </div>

  <!-- CAMPAIGNS -->
  <div class="tab-content" data-tab="campaigns">
    <h2>Price-variant split</h2>
    <div id="variant-cards"></div>
    <h2>All campaigns</h2>
    <div class="card no-pad">
      <table class="metrics" id="campaign-table">
        <thead><tr>
          <th>Campaign</th><th>Lang</th><th>Variant</th>
          <th class="r">Spend</th><th class="r">Purchases</th><th class="r">Installs</th><th class="r">Clicks</th>
          <th class="r">C2I %</th><th class="r">Pay %</th><th class="r">CAC</th><th class="r">CPI</th>
        </tr></thead>
        <tbody></tbody>
        <tfoot></tfoot>
      </table>
    </div>
  </div>

  <!-- THEMES -->
  <div class="tab-content" data-tab="themes">
    <div class="themes-filter-row">
      <span class="label">Filter by language:</span>
      <div class="lang-chips" id="themes-lang-chips"></div>
      <button class="chip-action" id="themes-lang-all">All</button>
      <button class="chip-action" id="themes-lang-none">None</button>
      <span class="label" id="themes-filter-status" style="margin-left:auto;color:#737373;font-weight:400;"></span>
    </div>
    <h2>Hierarchical breakdown — AI vs Human</h2>
    <div class="card no-pad">
      <table class="metrics" id="theme-table">
        <thead><tr>
          <th>Category</th>
          <th class="r">Ads</th><th class="r">≤₹300</th><th class="r">Win Rate</th>
          <th class="r">Spend</th><th class="r">Spend %</th>
          <th class="r">Purchases</th><th class="r">Installs</th><th class="r">Clicks</th>
          <th class="r">C2I %</th><th class="r">Pay %</th>
          <th class="r">CAC</th><th class="r">CPI</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="note"><b>AI</b> = name has "AI", "translated", or any FX keyword (KBH, Tractor Beam, Red Marker, Phone Axe, Keyboard Hammer, Wrecking, Drill, Pyro, Lightning, Blackhole, T-Rex, Energy, Steamroller, Hydraulic, Nitrogen, Cosmic, 404, Chalkboard, Camerazoom). <b>Human</b> = everything else. <b>In-house Influencer</b> = "Inhouse Inf" in name; <b>In-house</b> = default (incl. Bhumi/Akshara/AKS/Leka talent).</div>

    <h2>Sub-themes</h2>
    <div class="card no-pad">
      <table class="metrics" id="subtheme-table">
        <thead><tr>
          <th>Sub-theme</th>
          <th class="r">Ads</th><th class="r">AI/Human mix</th><th class="r">≤₹300</th><th class="r">Win Rate</th>
          <th class="r">Spend</th><th class="r">Spend %</th>
          <th class="r">Purchases</th><th class="r">Installs</th><th class="r">Clicks</th>
          <th class="r">C2I %</th><th class="r">Pay %</th>
          <th class="r">CAC</th><th class="r">CPI</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>

    <h2>Creative launch cadence — AI vs Human over time</h2>
    <div class="filter-row">
      <label>Language:</label>
      <select id="cad-lang"><option value="">All languages</option></select>
      <label>Granularity:</label>
      <div class="granularity" id="cad-gran">
        <button data-gran="day" class="active">Daily</button>
        <button data-gran="week">Weekly</button>
      </div>
      <label>Start date:</label>
      <input id="cad-start" type="date">
      <button class="btn secondary" id="cad-reset">Reset</button>
    </div>
    <div class="card">
      <div class="chart-wrap tall"><canvas id="chart-cadence"></canvas></div>
    </div>
    <div class="note">Stacked bars show count of new ads created per day (or week). Filters: pick a language to drill down, set a start date to scope the view.</div>
  </div>

  <!-- ADS -->
  <div class="tab-content" data-tab="ads">
    <div class="card">
      <div class="filter-row">
        <label>Language:</label><select id="ad-lang-filter"><option value="">All</option></select>
        <label>Top theme:</label><select id="ad-top-filter"><option value="">All</option><option value="AI">AI</option><option value="Human">Human</option><option value="Statics">Statics</option></select>
        <label>Bucket:</label><select id="ad-sub-filter"><option value="">All</option><option value="In-house">In-house</option><option value="In-house Influencer">In-house Influencer</option></select>
        <label>Sub-theme:</label><select id="ad-subtheme-filter"><option value="">All</option></select>
        <label>CAC band:</label><select id="ad-cac-filter">
          <option value="">All</option>
          <option value="under300">≤ ₹300</option>
          <option value="300_500">₹300–500</option>
          <option value="over500">Over ₹500</option>
          <option value="no_purchase">No purchase</option>
        </select>
        <label>Status:</label><select id="ad-status-filter">
          <option value="">All</option>
          <option value="ACTIVE">Live</option>
          <option value="PAUSED">Not live</option>
        </select>
        <label>Min spend ₹:</label><input id="ad-min-spend" type="number" value="0" step="500" style="width:90px;">
        <button class="btn" id="ad-apply">Apply filters</button>
        <button class="btn secondary" id="ad-reset">Reset</button>
        <span style="font-size:12px;color:#737373;" id="ad-count"></span>
      </div>
      <div id="ad-table"></div>
    </div>
  </div>

  <!-- INSIGHTS -->
  <div class="tab-content" data-tab="insights">
    <div id="insights-container"></div>
  </div>
</div>

<script>
// ============================== CONSTANTS ==============================
const ACT_ID = 'act_939306131915438';
const TARGET_CAC = 300;
const LANG_MAP = {HSM:'Hindi (HSM)', ML:'Malayalam (ML)', TL:'Telugu (TL)', KA:'Kannada (KA)', BN:'Bengali (BN)', MT:'Marathi (MT)', TN:'Tamil (TN)', GT:'Gujarati (GT)'};
const LANG_ORDER = ['Hindi (HSM)','Malayalam (ML)','Tamil (TN)','Kannada (KA)','Telugu (TL)','Marathi (MT)','Bengali (BN)','Gujarati (GT)','Other'];
const LANG_RE = /-(HSM|ML|TL|KA|BN|MT|TN|GT)-/;
const PRICE_RE = /-(10\+199|10\+149|199|99)-/;
const LANG_COLORS = {
  'Hindi (HSM)':'#6366f1','Malayalam (ML)':'#0891b2','Telugu (TL)':'#0d9488',
  'Kannada (KA)':'#65a30d','Bengali (BN)':'#dc2626','Marathi (MT)':'#ea580c',
  'Tamil (TN)':'#a855f7','Gujarati (GT)':'#db2777','Other':'#737373'
};
const AI_FX_KEYWORDS = ["kbh","tractor beam","red marker","phone axe"," axe","keyboard hammer"," hammer","wrecking","drill","pyro","lightning","blackhole","black hole","trex","t-rex","energy burst"," energy","steamroller","hydraulic","nitrogen","cosmic"," 404","chalkboard","cursor trash","camerazoom"];
// Pattern Interrupt tokens: anything with these → AI top-level (PI ads are AI per user rule)
const PI_TOKENS = ["pattern interrupt","pattern-interrupt","bulldozer","tank"];
const CAMPAIGN_ID_TO_LANG = {
  "120247189861740513":"Hindi (HSM)","120247113240430513":"Malayalam (ML)",
  "120247105483260513":"Hindi (HSM)","120246449055680513":"Gujarati (GT)",
  "120246449055670513":"Bengali (BN)","120246059063540513":"Marathi (MT)",
  "120245891639460513":"Tamil (TN)","120245891639290513":"Telugu (TL)",
  "120245891639270513":"Kannada (KA)","120245631352660513":"Malayalam (ML)",
  "120244070909170513":"Hindi (HSM)","120243754517490513":"Hindi (HSM)"
};
const AI_COLOR = '#a855f7', HUMAN_COLOR = '#0891b2', TOTAL_COLOR = '#1a1a1a';

// ============================== FORMATTERS ==============================
const fINR = n => '₹' + (n == null ? '—' : Number(n).toLocaleString('en-IN', {maximumFractionDigits: 0}));
const fNum = n => (n == null ? '—' : Number(n).toLocaleString('en-IN'));
const fPct = v => v == null ? '—' : v.toFixed(2) + '%';
const fPctOf = (a, b) => b ? (100*a/b).toFixed(1) + '%' : '—';

// ============================== CLASSIFIER ==============================
function parseCampaign(name) {
  const lm = (name||'').match(LANG_RE);
  const pm = (name||'').match(PRICE_RE);
  return { language: lm ? (LANG_MAP[lm[1]] || 'Other') : 'Other',
           price_variant: pm ? pm[1] : 'Other' };
}
// Word-bounded match for short tokens like PI / PAI (avoids matching "pitch" or "fapil")
function hasWordToken(name, tokens) {
  const n = ' ' + (name||'').toLowerCase().replace(/[^a-z0-9]+/g, ' ') + ' ';
  return tokens.some(t => n.includes(' ' + t.toLowerCase() + ' '));
}
function isStatic(name) {
  const n = (name||'').toLowerCase();
  // "statics" (plural) or "static" as standalone/end-of-string
  if (/\bstatics?\b/.test(n)) return true;
  return false;
}
function isAI(name) {
  const n = (name||'').toLowerCase();
  // "AI" word-bounded
  if (hasWordToken(name, ['ai'])) return true;
  // "translated" anywhere
  if (n.includes('translated')) return true;
  // FX keyword names (these are all AI b-roll effects)
  for (const k of AI_FX_KEYWORDS) if (n.includes(k)) return true;
  // Pattern Interrupt variants (user explicit rule: all PI ads are AI)
  for (const k of PI_TOKENS) if (n.includes(k)) return true;
  // PI / PAI tokens (word-bounded so we don't match "pitch")
  if (hasWordToken(name, ['pi', 'pai'])) return true;
  return false;
}
function classify(name) {
  const n = (name||'').toLowerCase();
  let top, sub;
  // Top-level priority: Statics > AI > Human
  if (isStatic(name)) { top = 'Statics'; sub = null; }
  else if (isAI(name)) { top = 'AI'; sub = null; }
  else {
    top = 'Human';
    if (n.includes('inhouse inf') || n.includes('in-house inf')) sub = 'In-house Influencer';
    else sub = 'In-house';
  }

  // Sub-themes (independent multi-tags)
  const subs = [];
  // Pattern Interrupt sub-theme: PI tokens + FX keywords (these are visually pattern-interrupting)
  if (PI_TOKENS.some(k => n.includes(k))) subs.push('Pattern Interrupt');
  else if (hasWordToken(name, ['pi', 'pai'])) subs.push('Pattern Interrupt');
  else if (AI_FX_KEYWORDS.some(k => n.includes(k))) subs.push('Pattern Interrupt');
  if (n.includes('bhumi')) subs.push('Bhumi Replication');
  if (n.includes('how to say this')) subs.push('How-to-say-this');
  if (n.includes('wa chat') || n.includes('whatsapp') || n.includes('wp chat')) subs.push('WhatsApp Chat');
  if (n.includes('testimonial')) subs.push('Testimonial');
  if (n.includes('ots ad')) subs.push('OTS');
  if (/frustrated|disappointed|humiliation|stressing/.test(n)) subs.push('Pain Point');
  if (n.includes('game screen') || n.includes('game recording')) subs.push('Game/App Screen');
  if (n.includes('news anchor')) subs.push('News Anchor');
  if (n.includes('weird cam')) subs.push('Weird Cam Angle');
  if (top === 'Statics') subs.push('Static-Image');
  if (!subs.length) subs.push('Uncategorized');
  return {top, sub, subs};
}
function metricsFor(spend, purchases, installs, impressions, clicks) {
  return { spend, purchases, installs, impressions: impressions||0, clicks: clicks||0,
    cac: purchases > 0 ? spend / purchases : null,
    cpi: installs > 0 ? spend / installs : null,
    pay: installs > 0 ? 100 * purchases / installs : null,
    c2i: clicks > 0 ? 100 * installs / clicks : null,
    ctr: impressions > 0 ? 100 * clicks / impressions : null };
}

// ============================== STATE ==============================
const SNAPSHOT_RAW = __SNAPSHOT__;
// Re-classify all ads at load time so the classifier is the single source of truth
function classifyAd(a) {
  const cls = classify(a.n);
  return Object.assign({}, a, {tt: cls.top, st: cls.sub, subs: cls.subs});
}
// Build lookup from ads_created for start date + live status
const _createdMap = {};
(SNAPSHOT_RAW.ads_created || []).forEach(ac => { _createdMap[ac.id] = ac; });

const SNAPSHOT = Object.assign({}, SNAPSHOT_RAW, {
  ads: (SNAPSHOT_RAW.ads || []).map(a => {
    const ad = classifyAd(a);
    const cr = _createdMap[a.id];
    ad.cd = cr ? cr.cd : null;
    ad.status = cr ? cr.status : 'UNKNOWN';
    return ad;
  }),
  ad_weekly: (SNAPSHOT_RAW.ad_weekly || []).map(classifyAd),
  ads_created: (SNAPSHOT_RAW.ads_created || []).map(a => {
    const cls = classify(a.n);
    return Object.assign({}, a, {tt: cls.top, st: cls.sub});
  })
});
let DATA = SNAPSHOT;
let GRAN = 'day';
let CAD_GRAN = 'day';
let ACTIVE_THRESHOLD = 1000;
let THEMES_LANG_FILTER = null;  // null = all languages; otherwise array of language names
window._charts = {};

// ============================== AGGREGATIONS ==============================
function aggregateLanguages(ads) {
  const m = {};
  ads.forEach(a => {
    const L = a.l;
    if (!m[L]) m[L] = {language:L, spend:0, purchases:0, installs:0, impressions:0, clicks:0, ads:0, ads_under_300_cac:0};
    const x = m[L];
    x.spend += a.s; x.purchases += a.pu; x.installs += a.i;
    x.impressions += a.im; x.clicks += a.cl;
    x.ads++;
    if (a.cac != null && a.cac <= 300) x.ads_under_300_cac++;
  });
  return Object.values(m).map(x => {
    const mt = metricsFor(x.spend, x.purchases, x.installs, x.impressions, x.clicks);
    return {language: x.language, ...mt, ads: x.ads, ads_under_300_cac: x.ads_under_300_cac};
  }).sort((a,b) => {
    const ai = LANG_ORDER.indexOf(a.language), bi = LANG_ORDER.indexOf(b.language);
    return (ai<0?99:ai) - (bi<0?99:bi);
  });
}
function aggregateCampaigns(ads) {
  const m = {};
  ads.forEach(a => {
    const k = a.c;
    if (!m[k]) {
      const p = parseCampaign(a.c);
      m[k] = {campaign_name: a.c, language: p.language, price_variant: p.price_variant,
              spend:0, purchases:0, installs:0, impressions:0, clicks:0};
    }
    m[k].spend += a.s; m[k].purchases += a.pu; m[k].installs += a.i;
    m[k].impressions += a.im || 0; m[k].clicks += a.cl || 0;
  });
  return Object.values(m).map(c => ({...c, ...metricsFor(c.spend, c.purchases, c.installs, c.impressions, c.clicks)}))
    .sort((a,b) => b.spend - a.spend);
}
function aggregateSubthemes(ads) {
  const m = {};
  ads.forEach(a => {
    for (const sub of a.subs) {
      if (!m[sub]) m[sub] = {theme:sub, ads:0, ai_ads:0, human_ads:0, spend:0, purchases:0, installs:0, impressions:0, clicks:0, ads_under_300:0};
      const x = m[sub];
      x.ads++; x.spend += a.s; x.purchases += a.pu; x.installs += a.i;
      x.impressions += a.im || 0; x.clicks += a.cl || 0;
      if (a.tt === 'AI') x.ai_ads++; else x.human_ads++;
      if (a.cac != null && a.cac <= 300) x.ads_under_300++;
    }
  });
  return Object.values(m).map(t => ({...t, ...metricsFor(t.spend, t.purchases, t.installs, t.impressions, t.clicks)}))
    .sort((a,b) => b.spend - a.spend);
}
function aggregateTopHierarchy(ads) {
  const empty = () => ({spend:0, purchases:0, installs:0, impressions:0, clicks:0, ads:0, ads_under_300:0});
  const acc = {Statics: empty(), AI: empty(), Human: empty()};
  acc.Human.subs = {'In-house': empty(), 'In-house Influencer': empty()};
  ads.forEach(a => {
    const node = acc[a.tt]; if (!node) return;
    node.spend += a.s; node.purchases += a.pu; node.installs += a.i;
    node.impressions += a.im || 0; node.clicks += a.cl || 0;
    node.ads++; if (a.cac != null && a.cac <= 300) node.ads_under_300++;
    if (a.tt === 'Human' && a.st) {
      const sn = acc.Human.subs[a.st] || (acc.Human.subs[a.st] = empty());
      sn.spend += a.s; sn.purchases += a.pu; sn.installs += a.i;
      sn.impressions += a.im || 0; sn.clicks += a.cl || 0;
      sn.ads++; if (a.cac != null && a.cac <= 300) sn.ads_under_300++;
    }
  });
  for (const top of ['Statics','AI','Human'])
    Object.assign(acc[top], metricsFor(acc[top].spend, acc[top].purchases, acc[top].installs, acc[top].impressions, acc[top].clicks));
  for (const sub of Object.keys(acc.Human.subs))
    Object.assign(acc.Human.subs[sub], metricsFor(acc.Human.subs[sub].spend, acc.Human.subs[sub].purchases, acc.Human.subs[sub].installs, acc.Human.subs[sub].impressions, acc.Human.subs[sub].clicks));
  return acc;
}
function computeSummary(ads) {
  const t = ads.reduce((a, x) => ({
    spend: a.spend + x.s, purchases: a.purchases + x.pu,
    installs: a.installs + x.i, impressions: a.impressions + (x.im||0), clicks: a.clicks + (x.cl||0)
  }), {spend:0, purchases:0, installs:0, impressions:0, clicks:0});
  return {
    total_spend: t.spend, total_purchases: t.purchases, total_installs: t.installs,
    total_impressions: t.impressions, total_clicks: t.clicks, total_ads: ads.length,
    overall_cac: t.purchases ? t.spend/t.purchases : null,
    overall_cpi: t.installs ? t.spend/t.installs : null,
    overall_pay: t.installs ? 100*t.purchases/t.installs : null,
    overall_c2i: t.clicks ? 100*t.installs/t.clicks : null,
    overall_ctr: t.impressions ? 100*t.clicks/t.impressions : null
  };
}

// =================== TIME AGG ===================
function weekStartDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00Z');
  const dayNum = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - dayNum);
  return d.toISOString().slice(0,10);
}
function aggregateTrend(rows, gran) {
  if (gran === 'day') {
    return rows.map(r => ({...r,
      cac: r.purchases ? r.spend/r.purchases : null,
      cpi: r.installs ? r.spend/r.installs : null,
      pay: r.installs ? 100*r.purchases/r.installs : null}));
  }
  const m = {};
  rows.forEach(r => {
    const k = weekStartDate(r.date);
    if (!m[k]) m[k] = {date: k, spend:0, purchases:0, installs:0};
    m[k].spend += r.spend; m[k].purchases += r.purchases; m[k].installs += r.installs;
  });
  return Object.values(m).sort((a,b) => a.date.localeCompare(b.date)).map(r => ({...r,
    cac: r.purchases ? r.spend/r.purchases : null,
    cpi: r.installs ? r.spend/r.installs : null,
    pay: r.installs ? 100*r.purchases/r.installs : null}));
}
function rollingRatio(rows, key, win=7) {
  const out = [];
  for (let i = 0; i < rows.length; i++) {
    let n = 0, d = 0;
    for (let j = Math.max(0, i-win+1); j <= i; j++) {
      const r = rows[j];
      if (key === 'cac') { n += r.spend||0; d += r.purchases||0; }
      else if (key === 'cpi') { n += r.spend||0; d += r.installs||0; }
      else if (key === 'pay') { n += (r.purchases||0)*100; d += r.installs||0; }
    }
    out.push(d > 0 ? n/d : null);
  }
  return out;
}

// =================== CADENCE (Chart A) ===================
function buildCadenceData(ads_created, langFilter, granForCad, startDate) {
  // Group by date → {total, ai, human}
  const filtered = ads_created.filter(a => {
    if (langFilter && a.l !== langFilter) return false;
    if (startDate && a.cd < startDate) return false;
    return true;
  });
  const byKey = {};
  filtered.forEach(a => {
    const key = granForCad === 'week' ? weekStartDate(a.cd) : a.cd;
    if (!byKey[key]) byKey[key] = {date: key, total: 0, ai: 0, human: 0};
    byKey[key].total++;
    if (a.tt === 'AI') byKey[key].ai++; else byKey[key].human++;
  });
  return Object.values(byKey).sort((a,b) => a.date.localeCompare(b.date));
}

// =================== ACTIVE POOL (Chart B) ===================
function buildActivePoolData(ad_weekly, langFilter, threshold) {
  // For each week: count unique ad_id with spend ≥ threshold, split by AI/Human
  const byWeek = {};
  ad_weekly.forEach(r => {
    if (langFilter && r.l !== langFilter) return;
    if (r.s < threshold) return;
    const wk = r.week_start;
    if (!byWeek[wk]) byWeek[wk] = {date: wk, total: new Set(), ai: new Set(), human: new Set()};
    byWeek[wk].total.add(r.ad_id);
    if (r.tt === 'AI') byWeek[wk].ai.add(r.ad_id);
    else byWeek[wk].human.add(r.ad_id);
  });
  return Object.values(byWeek).sort((a,b) => a.date.localeCompare(b.date)).map(w => ({
    date: w.date, total: w.total.size, ai: w.ai.size, human: w.human.size
  }));
}

// =================== COLOR ===================
function cellClass(v, baseline, metricType) {
  if (v == null) return 'cell bg-grey';
  if (metricType === 'cac') {
    if (v <= TARGET_CAC) return 'cell bg-green-strong';
    if (v <= TARGET_CAC * 1.1) return 'cell bg-green';
    if (v <= TARGET_CAC * 1.35) return 'cell bg-yellow';
    if (v <= TARGET_CAC * 1.7) return 'cell bg-red';
    return 'cell bg-red-strong';
  }
  if (metricType === 'cpi') {
    if (baseline == null) return 'cell bg-grey';
    if (v <= baseline * 0.85) return 'cell bg-green-strong';
    if (v <= baseline) return 'cell bg-green';
    if (v <= baseline * 1.2) return 'cell bg-yellow';
    return 'cell bg-red';
  }
  if (metricType === 'pay' || metricType === 'c2i' || metricType === 'ctr') {
    if (baseline == null) return 'cell bg-grey';
    if (v >= baseline * 1.15) return 'cell bg-green-strong';
    if (v >= baseline) return 'cell bg-green';
    if (v >= baseline * 0.85) return 'cell bg-yellow';
    if (v >= baseline * 0.7) return 'cell bg-red';
    return 'cell bg-red-strong';
  }
  return 'cell bg-grey';
}

// =================== RENDER ===================
function destroyChart(key) {
  if (window._charts[key]) { try { window._charts[key].destroy(); } catch(e) {} delete window._charts[key]; }
}
function destroyAllCharts() { Object.keys(window._charts).forEach(destroyChart); }

// Compute summary from filtered trend_account daily rows (cache-driven)
function computeTrendSummary(trendRows) {
  const t = (trendRows || []).reduce((a, r) => ({
    spend: a.spend + (r.spend || 0),
    purchases: a.purchases + (r.purchases || 0),
    installs: a.installs + (r.installs || 0)
  }), {spend:0, purchases:0, installs:0});
  return {
    total_spend: t.spend, total_purchases: t.purchases, total_installs: t.installs,
    overall_cac: t.purchases ? t.spend/t.purchases : null,
    overall_cpi: t.installs ? t.spend/t.installs : null,
    overall_pay: t.installs ? 100*t.purchases/t.installs : null
  };
}

function renderKPIs(summary, periodLabel) {
  const periodSub = periodLabel || 'Selected period';
  const winCount = CURRENT_ADS.filter(a => a.cac != null && a.cac <= 300).length;
  const winRate = CURRENT_ADS.length > 0 ? (100 * winCount / CURRENT_ADS.length).toFixed(1) + '%' : '—';
  const kpis = [
    {label:'Spend', value:fINR(summary.total_spend), sub:periodSub},
    {label:'Purchases', value:fNum(summary.total_purchases), sub:'Meta-reported'},
    {label:'Installs', value:fNum(summary.total_installs), sub:'Mobile app installs'},
    {label:'Pay %', value:fPct(summary.overall_pay), sub:'Install → purchase'},
    {label:'CAC', value:fINR(summary.overall_cac), sub:'Target ≤ ₹300',
     cls: summary.overall_cac==null?'':(summary.overall_cac<=300?'target-ok':(summary.overall_cac<=400?'target-warn':'target-bad'))},
    {label:'CPI', value:fINR(summary.overall_cpi), sub:'Spend ÷ installs'},
    {label:'Win Rate', value:winRate, sub:winCount+'/'+CURRENT_ADS.length+' ≤₹300',
     cls: parseFloat(winRate)>=30?'target-ok':(parseFloat(winRate)>=15?'target-warn':'target-bad')},
    {label:'Creatives', value:fNum(CURRENT_ADS.length), sub:'Active period'}
  ];
  document.getElementById('kpi-strip').innerHTML = kpis.map(k =>
    `<div class="kpi ${k.cls||''}"><div class="label">${k.label}</div><div class="value">${k.value}</div><div class="sub">${k.sub}</div></div>`
  ).join('');
}

function renderLanguageTable(langs, summary) {
  const tbody = document.querySelector('#language-table tbody');
  const tfoot = document.querySelector('#language-table tfoot');
  const totalSpend = summary.total_spend, totalPurch = summary.total_purchases;
  const baseCpi = summary.overall_cpi, basePay = summary.overall_pay, baseC2i = summary.overall_c2i;
  tbody.innerHTML = langs.map(L => `<tr>
    <td class="name">${L.language}</td>
    <td class="r">${fINR(L.spend)}</td>
    <td class="r"><span class="cell bg-grey">${fPctOf(L.spend, totalSpend)}</span></td>
    <td class="r">${fNum(L.purchases)}</td>
    <td class="r"><span class="cell bg-grey">${fPctOf(L.purchases, totalPurch)}</span></td>
    <td class="r">${fNum(L.installs)}</td>
    <td class="r"><span class="${cellClass(L.c2i, baseC2i, 'c2i')}">${fPct(L.c2i)}</span></td>
    <td class="r"><span class="${cellClass(L.pay, basePay, 'pay')}">${fPct(L.pay)}</span></td>
    <td class="r"><span class="${cellClass(L.cac, null, 'cac')}">${fINR(L.cac)}</span></td>
    <td class="r"><span class="${cellClass(L.cpi, baseCpi, 'cpi')}">${fINR(L.cpi)}</span></td>
    <td class="r">${L.ctr ? L.ctr.toFixed(2)+'%' : '—'}</td>
    <td class="r">${L.ads}</td>
    <td class="r">${L.ads_under_300_cac}</td>
    <td class="r">${L.ads > 0 ? (100*L.ads_under_300_cac/L.ads).toFixed(1)+'%' : '—'}</td>
  </tr>`).join('');
  tfoot.innerHTML = `<tr>
    <td>TOTAL</td>
    <td class="r">${fINR(totalSpend)}</td>
    <td class="r">100%</td>
    <td class="r">${fNum(totalPurch)}</td>
    <td class="r">100%</td>
    <td class="r">${fNum(summary.total_installs)}</td>
    <td class="r"><span class="cell bg-grey">${fPct(baseC2i)}</span></td>
    <td class="r"><span class="cell bg-grey">${fPct(basePay)}</span></td>
    <td class="r"><span class="${cellClass(summary.overall_cac, null, 'cac')}">${fINR(summary.overall_cac)}</span></td>
    <td class="r"><span class="cell bg-grey">${fINR(summary.overall_cpi)}</span></td>
    <td class="r">${summary.overall_ctr ? summary.overall_ctr.toFixed(2)+'%' : '—'}</td>
    <td class="r">${summary.total_ads}</td>
    <td class="r">${langs.reduce((s,L)=>s+L.ads_under_300_cac,0)}</td>
    <td class="r">${summary.total_ads > 0 ? (100*langs.reduce((s,L)=>s+L.ads_under_300_cac,0)/summary.total_ads).toFixed(1)+'%' : '—'}</td>
  </tr>`;
}

function renderCampaignTable(camps, summary) {
  const tbody = document.querySelector('#campaign-table tbody');
  const tfoot = document.querySelector('#campaign-table tfoot');
  const baseCpi = summary.overall_cpi, basePay = summary.overall_pay, baseC2i = summary.overall_c2i;
  tbody.innerHTML = camps.map(c => `<tr>
    <td title="${c.campaign_name}" style="max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${c.campaign_name}</td>
    <td>${c.language.replace(/ \(.*\)/,'')}</td>
    <td>₹${c.price_variant}</td>
    <td class="r">${fINR(c.spend)}</td>
    <td class="r">${fNum(c.purchases)}</td>
    <td class="r">${fNum(c.installs)}</td>
    <td class="r">${fNum(c.clicks)}</td>
    <td class="r"><span class="${cellClass(c.c2i, baseC2i, 'c2i')}">${fPct(c.c2i)}</span></td>
    <td class="r"><span class="${cellClass(c.pay, basePay, 'pay')}">${fPct(c.pay)}</span></td>
    <td class="r"><span class="${cellClass(c.cac, null, 'cac')}">${fINR(c.cac)}</span></td>
    <td class="r"><span class="${cellClass(c.cpi, baseCpi, 'cpi')}">${fINR(c.cpi)}</span></td>
  </tr>`).join('');
  tfoot.innerHTML = `<tr>
    <td>TOTAL</td><td></td><td></td>
    <td class="r">${fINR(summary.total_spend)}</td>
    <td class="r">${fNum(summary.total_purchases)}</td>
    <td class="r">${fNum(summary.total_installs)}</td>
    <td class="r">${fNum(summary.total_clicks)}</td>
    <td class="r">${fPct(baseC2i)}</td>
    <td class="r">${fPct(basePay)}</td>
    <td class="r"><span class="${cellClass(summary.overall_cac, null, 'cac')}">${fINR(summary.overall_cac)}</span></td>
    <td class="r">${fINR(summary.overall_cpi)}</td>
  </tr>`;
}

function renderVariantCards(camps, summary) {
  const byLang = {};
  camps.forEach(c => {
    if (!byLang[c.language]) byLang[c.language] = {};
    if (!byLang[c.language][c.price_variant]) byLang[c.language][c.price_variant] = [];
    byLang[c.language][c.price_variant].push(c);
  });
  const langsWithSplit = Object.keys(byLang).filter(L => Object.keys(byLang[L]).length >= 2)
    .sort((a,b) => LANG_ORDER.indexOf(a) - LANG_ORDER.indexOf(b));
  const variantOrder = ['199','99','10+199','10+149'];
  const basePay = summary.overall_pay, baseC2i = summary.overall_c2i, baseCpi = summary.overall_cpi;

  const cards = langsWithSplit.map(L => {
    const variants = byLang[L];
    const variantKeys = Object.keys(variants).sort((a,b) => {
      const ai = variantOrder.indexOf(a), bi = variantOrder.indexOf(b);
      return (ai<0?99:ai) - (bi<0?99:bi);
    });
    const rows = variantKeys.map(v => {
      const x = variants[v];
      const spend = x.reduce((s,c)=>s+c.spend,0);
      const purch = x.reduce((s,c)=>s+c.purchases,0);
      const inst = x.reduce((s,c)=>s+c.installs,0);
      const clicks = x.reduce((s,c)=>s+(c.clicks||0),0);
      const m = metricsFor(spend, purch, inst, 0, clicks);
      return `<tr>
        <td class="name">₹${v}</td>
        <td class="r">${x.length}</td>
        <td class="r">${fINR(spend)}</td>
        <td class="r">${fNum(purch)}</td>
        <td class="r">${fNum(inst)}</td>
        <td class="r">${fNum(clicks)}</td>
        <td class="r"><span class="${cellClass(m.c2i, baseC2i, 'c2i')}">${fPct(m.c2i)}</span></td>
        <td class="r"><span class="${cellClass(m.pay, basePay, 'pay')}">${fPct(m.pay)}</span></td>
        <td class="r"><span class="${cellClass(m.cac, null, 'cac')}">${fINR(m.cac)}</span></td>
        <td class="r"><span class="${cellClass(m.cpi, baseCpi, 'cpi')}">${fINR(m.cpi)}</span></td>
      </tr>`;
    }).join('');
    return `<div class="variant-section">
      <h4>${L} — ${variantKeys.length} price variants</h4>
      <table class="metrics">
        <thead><tr>
          <th>Variant</th>
          <th class="r">Campaigns</th>
          <th class="r">Spend</th>
          <th class="r">Purchases</th>
          <th class="r">Installs</th>
          <th class="r">Clicks</th>
          <th class="r">C2I %</th>
          <th class="r">Pay %</th>
          <th class="r">CAC</th>
          <th class="r">CPI</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  }).join('');
  document.getElementById('variant-cards').innerHTML = cards || '<div class="card" style="color:#737373;">No language has multiple price variants in this period.</div>';
}

function renderThemes(adsAll, summaryAll) {
  // Apply themes-tab language filter
  const ads = (THEMES_LANG_FILTER && THEMES_LANG_FILTER.length > 0)
    ? adsAll.filter(a => THEMES_LANG_FILTER.includes(a.l))
    : adsAll;
  const summary = computeSummary(ads);
  const hier = aggregateTopHierarchy(ads);
  const totalSpend = summary.total_spend;
  const basePay = summary.overall_pay, baseC2i = summary.overall_c2i, baseCpi = summary.overall_cpi;

  // Update status text
  const statusEl = document.getElementById('themes-filter-status');
  if (statusEl) {
    if (!THEMES_LANG_FILTER || THEMES_LANG_FILTER.length === 0) {
      statusEl.textContent = `All languages · ${fNum(ads.length)} ads · ${fINR(summary.total_spend)} spend`;
    } else {
      statusEl.textContent = `${THEMES_LANG_FILTER.length} languages selected · ${fNum(ads.length)} ads · ${fINR(summary.total_spend)} spend`;
    }
  }
  const tbody = document.querySelector('#theme-table tbody');

  function row(label, x, depth, bgClass) {
    const cls = depth === 0 ? bgClass : ('indent-' + depth);
    const wr = x.ads > 0 ? (100*x.ads_under_300/x.ads).toFixed(1)+'%' : '—';
    return `<tr class="${cls}">
      <td>${label}</td>
      <td class="r">${fNum(x.ads)}</td>
      <td class="r">${fNum(x.ads_under_300)}</td>
      <td class="r">${wr}</td>
      <td class="r">${fINR(x.spend)}</td>
      <td class="r">${fPctOf(x.spend, totalSpend)}</td>
      <td class="r">${fNum(x.purchases)}</td>
      <td class="r">${fNum(x.installs)}</td>
      <td class="r">${fNum(x.clicks)}</td>
      <td class="r"><span class="${cellClass(x.c2i, baseC2i, 'c2i')}">${fPct(x.c2i)}</span></td>
      <td class="r"><span class="${cellClass(x.pay, basePay, 'pay')}">${fPct(x.pay)}</span></td>
      <td class="r"><span class="${cellClass(x.cac, null, 'cac')}">${fINR(x.cac)}</span></td>
      <td class="r"><span class="${cellClass(x.cpi, baseCpi, 'cpi')}">${fINR(x.cpi)}</span></td>
    </tr>`;
  }
  let html = '';
  if (hier.Statics && hier.Statics.ads > 0) html += row('Statics (image ads)', hier.Statics, 0, 'row-bg-statics');
  html += row('AI (top-level)', hier.AI, 0, 'row-bg-ai');
  html += row('Human (top-level)', hier.Human, 0, 'row-bg-human');
  ['In-house','In-house Influencer'].forEach(s => {
    if (hier.Human.subs[s] && hier.Human.subs[s].ads > 0)
      html += row(s + ' (within Human)', hier.Human.subs[s], 1, '');
  });
  tbody.innerHTML = html;

  const subs = aggregateSubthemes(ads).filter(s => s.theme !== 'Uncategorized');
  const subTbody = document.querySelector('#subtheme-table tbody');
  subTbody.innerHTML = subs.map(s => `<tr>
    <td class="name">${s.theme}</td>
    <td class="r">${fNum(s.ads)}</td>
    <td class="r"><span class="cell bg-purple">${s.ai_ads} AI</span> / <span class="cell bg-cyan">${s.human_ads} H</span></td>
    <td class="r">${fNum(s.ads_under_300)}</td>
    <td class="r">${s.ads > 0 ? (100*s.ads_under_300/s.ads).toFixed(1)+'%' : '—'}</td>
    <td class="r">${fINR(s.spend)}</td>
    <td class="r">${fPctOf(s.spend, totalSpend)}</td>
    <td class="r">${fNum(s.purchases)}</td>
    <td class="r">${fNum(s.installs)}</td>
    <td class="r">${fNum(s.clicks)}</td>
    <td class="r"><span class="${cellClass(s.c2i, baseC2i, 'c2i')}">${fPct(s.c2i)}</span></td>
    <td class="r"><span class="${cellClass(s.pay, basePay, 'pay')}">${fPct(s.pay)}</span></td>
    <td class="r"><span class="${cellClass(s.cac, null, 'cac')}">${fINR(s.cac)}</span></td>
    <td class="r"><span class="${cellClass(s.cpi, baseCpi, 'cpi')}">${fINR(s.cpi)}</span></td>
  </tr>`).join('');
}

// =================== TRENDS ===================
function chartOptsBase(extra) {
  return Object.assign({
    responsive: true, maintainAspectRatio: false,
    interaction: {mode:'index', intersect:false},
    plugins: {legend: {display: false}, tooltip: {enabled: true}},
    scales: {
      x: {grid: {display:false}, ticks: {maxRotation:0, autoSkip:true, maxTicksLimit:7, font:{size:10}}, border: {display:false}},
      y: {grid: {color:'#f0f0f0'}, ticks: {font:{size:10}}, border:{display:false}}
    }
  }, extra||{});
}

function drawSimpleTrend(canvasId, rows, metric, color, gran) {
  destroyChart(canvasId);
  if (!rows || rows.length === 0) return;
  const labels = rows.map(r => gran==='week' ? 'wk ' + r.date.slice(5) : r.date.slice(5));
  const useRolling = (gran === 'day');
  let data, label, isCurrency = false, isPct = false;
  if (metric === 'spend')     { data = rows.map(r=>r.spend);     label='Spend';     isCurrency=true; }
  else if (metric === 'purchases') { data = rows.map(r=>r.purchases); label='Purchases'; }
  else if (metric === 'cac') { data = useRolling ? rollingRatio(rows,'cac') : rows.map(r=>r.cac); label = useRolling?'CAC (7d roll)':'CAC'; isCurrency=true; }
  else if (metric === 'cpi') { data = useRolling ? rollingRatio(rows,'cpi') : rows.map(r=>r.cpi); label = useRolling?'CPI (7d roll)':'CPI'; isCurrency=true; }
  else if (metric === 'pay') { data = useRolling ? rollingRatio(rows,'pay') : rows.map(r=>r.pay); label = useRolling?'Pay % (7d roll)':'Pay %'; isPct=true; }
  else { data = []; label=''; }

  const datasets = [{
    type: (metric==='spend'||metric==='purchases') ? 'bar' : 'line',
    label, data,
    borderColor: color, backgroundColor: (metric==='spend'||metric==='purchases')?color+'88':color,
    tension: 0.3, borderWidth: 2, pointRadius: gran==='week'?2:0, fill: false
  }];
  if (metric === 'cac') {
    datasets.push({type:'line', label:'Target', data: labels.map(()=>300), borderColor:'#15803d', borderWidth:1, borderDash:[4,4], pointRadius:0});
  }

  window._charts[canvasId] = new Chart(document.getElementById(canvasId), {
    data: {labels, datasets},
    options: chartOptsBase({
      plugins: {legend:{display:false}, tooltip:{callbacks:{label: c => `${c.dataset.label}: ${isCurrency?fINR(c.parsed.y):(isPct?fPct(c.parsed.y):fNum(c.parsed.y))}`}}},
      scales: {
        x: {grid:{display:false}, ticks:{maxRotation:0, autoSkip:true, maxTicksLimit:7, font:{size:10}}, border:{display:false}},
        y: {grid:{color:'#f0f0f0'}, ticks:{font:{size:10}, callback: v => isCurrency?fINR(v):(isPct?v.toFixed(1)+'%':fNum(v))}, border:{display:false}, beginAtZero: !(metric==='cac'||metric==='cpi'||metric==='pay')}
      }
    })
  });
}

function drawCombinedSpendPurchases(canvasId, rows, color, gran) {
  destroyChart(canvasId);
  if (!rows || rows.length === 0) return;
  const labels = rows.map(r => gran==='week' ? 'wk ' + r.date.slice(5) : r.date.slice(5));
  window._charts[canvasId] = new Chart(document.getElementById(canvasId), {
    data: {labels, datasets: [
      {type:'bar', label:'Spend', data: rows.map(r=>r.spend), backgroundColor: color+'55', yAxisID:'y1', order:2},
      {type:'line', label:'Purchases', data: rows.map(r=>r.purchases), borderColor:'#1a1a1a', tension:0.3, borderWidth:1.5, pointRadius: gran==='week'?2:0, yAxisID:'y2', order:1, fill:false}
    ]},
    options: chartOptsBase({
      plugins: {legend:{display:true, position:'top', labels:{boxWidth:10, font:{size:10}}},
                tooltip:{callbacks:{label: c => `${c.dataset.label}: ${c.dataset.label==='Spend'?fINR(c.parsed.y):fNum(c.parsed.y)}`}}},
      scales: {
        x: {grid:{display:false}, ticks:{maxRotation:0, autoSkip:true, maxTicksLimit:7, font:{size:10}}, border:{display:false}},
        y1: {position:'left', ticks:{font:{size:10}, callback:v=>fINR(v)}, grid:{color:'#f0f0f0'}, border:{display:false}, beginAtZero:true},
        y2: {position:'right', ticks:{font:{size:10}, callback:v=>fNum(v)}, grid:{display:false}, border:{display:false}, beginAtZero:true}
      }
    })
  });
}

function drawCadenceChart(canvasId, ads_created, langFilter, granForCad) {
  destroyChart(canvasId);
  const rows = buildCadenceData(ads_created, langFilter, granForCad);
  if (rows.length === 0) {
    // Still render an empty canvas
    window._charts[canvasId] = new Chart(document.getElementById(canvasId), {
      data: {labels: [], datasets: []}, options: chartOptsBase({})
    });
    return;
  }
  const labels = rows.map(r => granForCad==='week' ? 'wk ' + r.date.slice(5) : r.date.slice(5));
  window._charts[canvasId] = new Chart(document.getElementById(canvasId), {
    data: {labels, datasets: [
      {type:'line', label:'Total', data: rows.map(r=>r.total), borderColor: TOTAL_COLOR, backgroundColor: TOTAL_COLOR, borderWidth: 2.5, pointRadius: 2, tension: 0.2, fill: false},
      {type:'line', label:'AI', data: rows.map(r=>r.ai), borderColor: AI_COLOR, backgroundColor: AI_COLOR, borderWidth: 2, pointRadius: 2, tension: 0.2, fill: false},
      {type:'line', label:'Human', data: rows.map(r=>r.human), borderColor: HUMAN_COLOR, backgroundColor: HUMAN_COLOR, borderWidth: 2, pointRadius: 2, tension: 0.2, fill: false},
    ]},
    options: chartOptsBase({
      plugins: {legend: {display:true, position:'top', labels:{boxWidth:10, font:{size:10}}}, tooltip:{callbacks:{label: c => `${c.dataset.label}: ${fNum(c.parsed.y)}`}}},
      scales: {
        x: {grid:{display:false}, ticks:{maxRotation:0, autoSkip:true, maxTicksLimit:7, font:{size:10}}, border:{display:false}},
        y: {grid:{color:'#f0f0f0'}, ticks:{font:{size:10}, callback:v=>fNum(v)}, border:{display:false}, beginAtZero:true}
      }
    })
  });
}

function drawActivePoolChart(canvasId, ad_weekly, langFilter, threshold) {
  destroyChart(canvasId);
  const rows = buildActivePoolData(ad_weekly, langFilter, threshold);
  if (rows.length === 0) {
    window._charts[canvasId] = new Chart(document.getElementById(canvasId), {
      data: {labels: [], datasets: []}, options: chartOptsBase({})
    });
    return;
  }
  const labels = rows.map(r => 'wk ' + r.date.slice(5));
  window._charts[canvasId] = new Chart(document.getElementById(canvasId), {
    data: {labels, datasets: [
      {type:'line', label:'Total active', data: rows.map(r=>r.total), borderColor: TOTAL_COLOR, backgroundColor: TOTAL_COLOR, borderWidth: 2.5, pointRadius: 3, tension: 0.2, fill: false},
      {type:'line', label:'AI active', data: rows.map(r=>r.ai), borderColor: AI_COLOR, backgroundColor: AI_COLOR, borderWidth: 2, pointRadius: 2, tension: 0.2, fill: false},
      {type:'line', label:'Human active', data: rows.map(r=>r.human), borderColor: HUMAN_COLOR, backgroundColor: HUMAN_COLOR, borderWidth: 2, pointRadius: 2, tension: 0.2, fill: false},
    ]},
    options: chartOptsBase({
      plugins: {legend: {display:true, position:'top', labels:{boxWidth:10, font:{size:10}}},
                tooltip:{callbacks:{label: c => `${c.dataset.label}: ${fNum(c.parsed.y)}`}}},
      scales: {
        x: {grid:{display:false}, ticks:{maxRotation:0, autoSkip:true, font:{size:10}}, border:{display:false}},
        y: {ticks:{font:{size:10}, callback:v=>fNum(v)}, grid:{color:'#f0f0f0'}, border:{display:false}, beginAtZero:true, title:{display:true, text:'Active creatives', font:{size:10}}}
      }
    })
  });
}

function drawCadenceStackedBars(canvasId, ads_created, langFilter, granForCad, startDate) {
  destroyChart(canvasId);
  const rows = buildCadenceData(ads_created, langFilter, granForCad, startDate);
  if (rows.length === 0) {
    window._charts[canvasId] = new Chart(document.getElementById(canvasId), {
      data: {labels: [], datasets: []}, options: chartOptsBase({})
    });
    return;
  }
  const labels = rows.map(r => granForCad==='week' ? 'wk ' + r.date.slice(5) : r.date);
  window._charts[canvasId] = new Chart(document.getElementById(canvasId), {
    data: {labels, datasets: [
      {type:'bar', label:'AI', data: rows.map(r=>r.ai), backgroundColor: AI_COLOR, stack: 'creatives'},
      {type:'bar', label:'Human', data: rows.map(r=>r.human), backgroundColor: HUMAN_COLOR, stack: 'creatives'},
    ]},
    options: chartOptsBase({
      plugins: {legend: {display:true, position:'top', labels:{boxWidth:12, font:{size:11}}},
                tooltip:{callbacks:{label: c => `${c.dataset.label}: ${fNum(c.parsed.y)}`}}},
      scales: {
        x: {stacked:true, grid:{display:false}, ticks:{maxRotation:45, autoSkip:true, maxTicksLimit:18, font:{size:10}}, border:{display:false}},
        y: {stacked:true, ticks:{font:{size:10}, callback:v=>fNum(v)}, grid:{color:'#f0f0f0'}, border:{display:false}, beginAtZero:true, title:{display:true, text:'New creatives', font:{size:10}}}
      }
    })
  });
}

function renderTrends(summary) {
  const filtered = filterTrend(DATA.trend_account, DATE_FILTER.since, DATE_FILTER.until);
  const acct = aggregateTrend(filtered, GRAN);
  drawSimpleTrend('t-overall-cac', acct, 'cac', '#1a1a1a', GRAN);
  drawSimpleTrend('t-overall-cpi', acct, 'cpi', '#1a1a1a', GRAN);
  drawSimpleTrend('t-overall-pay', acct, 'pay', '#1a1a1a', GRAN);
  drawSimpleTrend('t-overall-spend', acct, 'spend', '#6366f1', GRAN);
  renderSmallMultiples();
  renderDeepDive();
}

function renderSmallMultiples() {
  const grid = document.getElementById('sm-grid');
  const metric = document.getElementById('sm-metric').value;
  const langs = Object.keys(DATA.trend_by_language).filter(L => L !== 'Other').sort((a,b) => LANG_ORDER.indexOf(a) - LANG_ORDER.indexOf(b));
  const lsMap = Object.fromEntries(aggregateLanguages(DATA.ads).map(L => [L.language, L]));
  grid.innerHTML = langs.map(L => {
    const tileId = 'sm-' + L.replace(/[^A-Za-z0-9]/g,'');
    const ls = lsMap[L] || {};
    let headerVal = '';
    if (metric === 'cac') headerVal = fINR(ls.cac);
    else if (metric === 'cpi') headerVal = fINR(ls.cpi);
    else if (metric === 'pay') headerVal = fPct(ls.pay);
    else if (metric === 'spend') headerVal = fINR(ls.spend);
    else if (metric === 'purchases') headerVal = fNum(ls.purchases);
    return `<div class="small-mult-card">
      <div class="title"><span>${L}</span><span class="val">${headerVal}</span></div>
      <div class="chart-wrap short"><canvas id="${tileId}"></canvas></div>
    </div>`;
  }).join('');
  langs.forEach(L => {
    const tileId = 'sm-' + L.replace(/[^A-Za-z0-9]/g,'');
    const filtered = filterTrend(DATA.trend_by_language[L] || [], DATE_FILTER.since, DATE_FILTER.until);
    const rows = aggregateTrend(filtered, GRAN);
    drawSimpleTrend(tileId, rows, metric, LANG_COLORS[L] || '#737373', GRAN);
  });
}

function renderDeepDive() {
  const dd = document.getElementById('deep-dive');
  const langs = Object.keys(DATA.trend_by_language).filter(L => L !== 'Other').sort((a,b) => LANG_ORDER.indexOf(a) - LANG_ORDER.indexOf(b));
  const lsMap = Object.fromEntries(aggregateLanguages(DATA.ads).map(L => [L.language, L]));
  dd.innerHTML = langs.map(L => {
    const ls = lsMap[L] || {};
    const idBase = L.replace(/[^A-Za-z0-9]/g,'');
    return `<div class="deep-dive-card">
      <div class="header">
        <h3>${L}</h3>
        <div class="stats">Spend ${fINR(ls.spend)} · Purch ${fNum(ls.purchases)} · CAC ${fINR(ls.cac)} · CPI ${fINR(ls.cpi)} · Pay % ${fPct(ls.pay)} · C2I % ${fPct(ls.c2i)} · Win ${ls.ads > 0 ? (100*ls.ads_under_300_cac/ls.ads).toFixed(1)+'%' : '—'}</div>
      </div>
      <div class="chart-grid">
        <div class="chart-cell"><h3>CAC trend</h3><div class="chart-wrap"><canvas id="dd-cac-${idBase}"></canvas></div></div>
        <div class="chart-cell"><h3>CPI trend</h3><div class="chart-wrap"><canvas id="dd-cpi-${idBase}"></canvas></div></div>
        <div class="chart-cell"><h3>Pay % trend</h3><div class="chart-wrap"><canvas id="dd-pay-${idBase}"></canvas></div></div>
        <div class="chart-cell"><h3>Spend & Purchases</h3><div class="chart-wrap"><canvas id="dd-sp-${idBase}"></canvas></div></div>
        <div class="chart-cell"><h3>Creative launch cadence</h3><div class="chart-wrap"><canvas id="dd-cad-${idBase}"></canvas></div></div>
        <div class="chart-cell"><h3>Active creative pool (spend ≥ ₹${ACTIVE_THRESHOLD.toLocaleString()})</h3><div class="chart-wrap"><canvas id="dd-pool-${idBase}"></canvas></div></div>
      </div>
    </div>`;
  }).join('');

  langs.forEach(L => {
    const idBase = L.replace(/[^A-Za-z0-9]/g,'');
    const filtered = filterTrend(DATA.trend_by_language[L] || [], DATE_FILTER.since, DATE_FILTER.until);
    const rows = aggregateTrend(filtered, GRAN);
    const c = LANG_COLORS[L] || '#1a1a1a';
    drawSimpleTrend('dd-cac-' + idBase, rows, 'cac', c, GRAN);
    drawSimpleTrend('dd-cpi-' + idBase, rows, 'cpi', c, GRAN);
    drawSimpleTrend('dd-pay-' + idBase, rows, 'pay', c, GRAN);
    drawCombinedSpendPurchases('dd-sp-' + idBase, rows, c, GRAN);
    drawCadenceChart('dd-cad-' + idBase, DATA.ads_created || [], L, GRAN);
    drawActivePoolChart('dd-pool-' + idBase, DATA.ad_weekly || [], L, ACTIVE_THRESHOLD);
  });
}

function renderCadenceTab() {
  const langSel = document.getElementById('cad-lang');
  if (langSel.options.length <= 1) {
    [...new Set((DATA.ads_created||[]).map(a => a.l))].sort((a,b) => LANG_ORDER.indexOf(a) - LANG_ORDER.indexOf(b)).forEach(L => {
      const o = document.createElement('option'); o.value = L; o.textContent = L; langSel.appendChild(o);
    });
  }
  const startDate = document.getElementById('cad-start').value || null;
  const lang = langSel.value || null;
  drawCadenceStackedBars('chart-cadence', DATA.ads_created || [], lang, CAD_GRAN, startDate);
}

// =================== ADS TABLE ===================
let adGrid = null;
let adFiltersWired = false;  // wire event handlers only once across renders

// Filter state (preserved across renders so date changes don't wipe selection)
const AD_FILTER = {lang:'', top:'', sub:'', subTheme:'', cacBand:'', minSpend: 0, status: ''};

function adsTableRows(summary) {
  const baseCpi = summary.overall_cpi, basePay = summary.overall_pay, baseC2i = summary.overall_c2i;
  return CURRENT_ADS.filter(a => {
    if (AD_FILTER.lang && a.l !== AD_FILTER.lang) return false;
    if (AD_FILTER.top && a.tt !== AD_FILTER.top) return false;
    if (AD_FILTER.sub && a.st !== AD_FILTER.sub) return false;
    if (AD_FILTER.subTheme && !a.subs.includes(AD_FILTER.subTheme)) return false;
    if (AD_FILTER.status) {
      if (AD_FILTER.status === 'ACTIVE' && a.status !== 'ACTIVE') return false;
      if (AD_FILTER.status === 'PAUSED' && a.status !== 'PAUSED' && a.status !== 'CAMPAIGN_PAUSED') return false;
    }
    if (a.s < AD_FILTER.minSpend) return false;
    if (AD_FILTER.cacBand === 'under300') return a.cac != null && a.cac <= 300;
    if (AD_FILTER.cacBand === '300_500') return a.cac != null && a.cac > 300 && a.cac <= 500;
    if (AD_FILTER.cacBand === 'over500') return a.cac != null && a.cac > 500;
    if (AD_FILTER.cacBand === 'no_purchase') return a.cac == null;
    return true;
  });
}

function drawAdsGrid(summary) {
  const baseCpi = summary.overall_cpi, basePay = summary.overall_pay, baseC2i = summary.overall_c2i;
  const filtered = adsTableRows(summary);
  const winCount = filtered.filter(a => a.cac != null && a.cac <= 300).length;
  const winRate = filtered.length > 0 ? (100 * winCount / filtered.length).toFixed(1) : '0.0';
  document.getElementById('ad-count').textContent = filtered.length + ' creatives · ' + fINR(filtered.reduce((s,a)=>s+a.s,0)) + ' spend · Win rate: ' + winRate + '% (' + winCount + '/' + filtered.length + ')';
  const rows = filtered.map(a => {
    const c2i = a.cl ? 100*a.i/a.cl : null;
    const pay = a.i ? 100*a.pu/a.i : null;
    const isLive = a.status === 'ACTIVE';
    return [a.n, a.l.replace(/ \(.*\)/,''), a.tt, a.st || '—', a.subs.join(', '),
      a.cd || '—', isLive ? 'Live' : 'Off',
      a.s, a.pu, a.i, c2i, pay, a.cac, a.cpi];
  });
  const columns = [
    {name:'Creative name', width:'20%'},
    {name:'Lang', width:'5%'},
    {name:'Top', width:'5%', formatter: v => gridjs.html(`<span class="cell ${v==='AI'?'bg-purple':(v==='Human'?'bg-cyan':'bg-statics')}">${v}</span>`)},
    {name:'Bucket', width:'7%'},
    {name:'Sub-themes', width:'10%'},
    {name:'Started', width:'7%', sort:{compare:(a,b)=>a<b?-1:a>b?1:0}},
    {name:'Status', width:'4%', formatter: v => gridjs.html(v==='Live'?'<span class="cell bg-green">● Live</span>':'<span class="cell bg-grey">○ Off</span>')},
    {name:'Spend', width:'6%', formatter:v=>fINR(v), sort:{compare:(a,b)=>a-b}},
    {name:'Purch', width:'5%', formatter:v=>fNum(v), sort:{compare:(a,b)=>a-b}},
    {name:'Installs', width:'5%', formatter:v=>fNum(v), sort:{compare:(a,b)=>a-b}},
    {name:'C2I %', width:'5%', formatter:v=>v==null?gridjs.html('<span class="cell bg-grey">—</span>'):gridjs.html(`<span class="${cellClass(v, baseC2i, 'c2i')}">${fPct(v)}</span>`), sort:{compare:(a,b)=>(a||-1)-(b||-1)}},
    {name:'Pay %', width:'5%', formatter:v=>v==null?gridjs.html('<span class="cell bg-grey">—</span>'):gridjs.html(`<span class="${cellClass(v, basePay, 'pay')}">${fPct(v)}</span>`), sort:{compare:(a,b)=>(a||-1)-(b||-1)}},
    {name:'CAC', width:'6%', formatter:v=>v==null?gridjs.html('<span class="cell bg-grey">—</span>'):gridjs.html(`<span class="${cellClass(v, null, 'cac')}">${fINR(v)}</span>`), sort:{compare:(a,b)=>(a||1e9)-(b||1e9)}},
    {name:'CPI', width:'5%', formatter:v=>v==null?gridjs.html('<span class="cell bg-grey">—</span>'):gridjs.html(`<span class="${cellClass(v, baseCpi, 'cpi')}">${fINR(v)}</span>`), sort:{compare:(a,b)=>(a||1e9)-(b||1e9)}}
  ];
  if (adGrid) {
    adGrid.updateConfig({data: rows, columns: columns}).forceRender();
  } else {
    const adTableEl = document.getElementById('ad-table');
    adGrid = new gridjs.Grid({
      columns: columns,
      data: rows, pagination: {limit:25, summary:true}, sort:true, search:true,
      style: {table: {'font-size': '12px'}}
    }).render(adTableEl);
  }
}

function renderAdsTable(summary) {
  const langSel = document.getElementById('ad-lang-filter');
  const topSel = document.getElementById('ad-top-filter');
  const subSel = document.getElementById('ad-sub-filter');
  const subThemeSel = document.getElementById('ad-subtheme-filter');
  const cacSel = document.getElementById('ad-cac-filter');
  const statusSel = document.getElementById('ad-status-filter');
  const minSpend = document.getElementById('ad-min-spend');

  const existingLangs = new Set([...langSel.options].map(o => o.value));
  [...new Set(CURRENT_ADS.map(a=>a.l))].sort().forEach(L => {
    if (!existingLangs.has(L)) {
      const o = document.createElement('option'); o.value = L; o.textContent = L; langSel.appendChild(o);
    }
  });
  const existingSubs = new Set([...subThemeSel.options].map(o => o.value));
  [...new Set(CURRENT_ADS.flatMap(a=>a.subs))].sort().forEach(T => {
    if (!existingSubs.has(T)) {
      const o = document.createElement('option'); o.value = T; o.textContent = T; subThemeSel.appendChild(o);
    }
  });
  langSel.value = AD_FILTER.lang || '';
  topSel.value = AD_FILTER.top || '';
  subSel.value = AD_FILTER.sub || '';
  subThemeSel.value = AD_FILTER.subTheme || '';
  cacSel.value = AD_FILTER.cacBand || '';
  statusSel.value = AD_FILTER.status || '';
  minSpend.value = AD_FILTER.minSpend || 0;

  if (!adFiltersWired) {
    document.getElementById('ad-apply').onclick = () => {
      AD_FILTER.lang = langSel.value;
      AD_FILTER.top = topSel.value;
      AD_FILTER.sub = subSel.value;
      AD_FILTER.subTheme = subThemeSel.value;
      AD_FILTER.cacBand = cacSel.value;
      AD_FILTER.status = statusSel.value;
      AD_FILTER.minSpend = parseFloat(minSpend.value) || 0;
      drawAdsGrid(CURRENT_SUMMARY);
    };
    document.getElementById('ad-reset').onclick = () => {
      AD_FILTER.lang = ''; AD_FILTER.top = ''; AD_FILTER.sub = '';
      AD_FILTER.subTheme = ''; AD_FILTER.cacBand = ''; AD_FILTER.minSpend = 0;
      AD_FILTER.status = '';
      langSel.value = ''; topSel.value = ''; subSel.value = '';
      subThemeSel.value = ''; cacSel.value = ''; minSpend.value = 0;
      statusSel.value = '';
      drawAdsGrid(CURRENT_SUMMARY);
    };
    adFiltersWired = true;
  }
  drawAdsGrid(summary);
}

function renderInsights(langs, summary) {
  const c = document.getElementById('insights-container');
  const subs = aggregateSubthemes(CURRENT_ADS).filter(s => s.theme !== 'Uncategorized' && s.spend > 30000);
  const ads = CURRENT_ADS.filter(a => a.cac != null && a.s > 1000);
  const hier = aggregateTopHierarchy(CURRENT_ADS);
  const bestLang = [...langs].sort((a,b) => (a.cac||999)-(b.cac||999))[0];
  const worstLang = [...langs].sort((a,b) => (b.cac||0)-(a.cac||0))[0];
  const bestSub = [...subs].sort((a,b) => (a.cac||999)-(b.cac||999))[0];
  const worstSub = [...subs].sort((a,b) => (b.cac||0)-(a.cac||0))[0];
  const topAd = [...ads].sort((a,b) => a.cac - b.cac)[0];
  const bottomAd = [...ads].sort((a,b) => b.cac - a.cac)[0];
  const scalers = ads.filter(a => a.cac <= 300 && a.s > 20000).sort((a,b) => b.s - a.s);

  const insights = [
    {cls: bestLang && bestLang.cac<=300?'good':'warn',
     title: bestLang ? `Best language: ${bestLang.language} — CAC ${fINR(bestLang.cac)} · Pay % ${fPct(bestLang.pay)} · C2I % ${fPct(bestLang.c2i)}` : 'No language data',
     desc: bestLang ? `${fNum(bestLang.purchases)} purchases on ${fINR(bestLang.spend)}. Win rate: ${bestLang.ads > 0 ? (100*bestLang.ads_under_300_cac/bestLang.ads).toFixed(1) : 0}% (${bestLang.ads_under_300_cac}/${bestLang.ads}).` : ''},
    {cls: 'bad',
     title: worstLang ? `Worst language: ${worstLang.language} — CAC ${fINR(worstLang.cac)} · Pay % ${fPct(worstLang.pay)}` : '',
     desc: worstLang ? `${fNum(worstLang.purchases)} purchases, ${fINR(worstLang.spend)}.` : ''},
    {cls: hier.AI.cac && hier.Human.cac && hier.AI.cac < hier.Human.cac ? 'good' : 'warn',
     title: `AI vs Human: AI CAC ${fINR(hier.AI.cac)} (${hier.AI.ads} ads, Pay % ${fPct(hier.AI.pay)}) vs Human CAC ${fINR(hier.Human.cac)} (${hier.Human.ads} ads, Pay % ${fPct(hier.Human.pay)})`,
     desc: `Within Human: In-house ${hier.Human.subs['In-house']?fINR(hier.Human.subs['In-house'].cac):'—'} vs In-house Influencer ${hier.Human.subs['In-house Influencer']?fINR(hier.Human.subs['In-house Influencer'].cac):'—'}.`},
    bestSub ? {cls: bestSub.cac<=300?'good':'warn',
     title: `Best sub-theme: ${bestSub.theme} — CAC ${fINR(bestSub.cac)} · Pay % ${fPct(bestSub.pay)}`,
     desc: `${bestSub.ads} creatives (${bestSub.ai_ads} AI / ${bestSub.human_ads} Human), ${fINR(bestSub.spend)} spend.`} : null,
    worstSub ? {cls:'bad', title: `Weakest sub-theme: ${worstSub.theme} — CAC ${fINR(worstSub.cac)}`, desc: `${worstSub.ads} creatives, ${fINR(worstSub.spend)}.`} : null,
    topAd ? {cls:'good', title: `Top scaler: "${topAd.n}"`, desc: `${topAd.l} · ${topAd.tt}${topAd.st?'/'+topAd.st:''} · spend ${fINR(topAd.s)} · ${topAd.pu} purchases · CAC ${fINR(topAd.cac)}`} : null,
    bottomAd ? {cls:'bad', title: `Worst spender: "${bottomAd.n}"`, desc: `${bottomAd.l} · ${bottomAd.tt}${bottomAd.st?'/'+bottomAd.st:''} · spend ${fINR(bottomAd.s)} · ${bottomAd.pu} purchases · CAC ${fINR(bottomAd.cac)}`} : null,
    {cls:'good',
     title: `${scalers.length} creatives scaling under target (spend > ₹20k, CAC ≤ ₹300)`,
     desc: scalers.slice(0,6).map(a => `• ${a.n} — ${a.l.replace(/ \(.*\)/,'')} · ${a.tt}${a.st?'/'+a.st:''} · ${fINR(a.s)} · CAC ${fINR(a.cac)}`).join('<br>')},
    (() => {
      const total = CURRENT_ADS.length;
      const wins = CURRENT_ADS.filter(a => a.cac != null && a.cac <= 300).length;
      const wr = total > 0 ? (100*wins/total).toFixed(1) : 0;
      return {cls: wr >= 25 ? 'good' : (wr >= 10 ? 'warn' : 'bad'),
        title: `Overall Win Rate: ${wr}% (${wins} of ${total} creatives with CAC ≤ ₹300)`,
        desc: `By type: AI ${(() => { const ai = CURRENT_ADS.filter(a=>a.tt==='AI'); const aiW = ai.filter(a=>a.cac!=null&&a.cac<=300).length; return ai.length?((100*aiW/ai.length).toFixed(1)+'% ('+aiW+'/'+ai.length+')'):'—'; })()} · Human ${(() => { const h = CURRENT_ADS.filter(a=>a.tt==='Human'); const hW = h.filter(a=>a.cac!=null&&a.cac<=300).length; return h.length?((100*hW/h.length).toFixed(1)+'% ('+hW+'/'+h.length+')'):'—'; })()}`};
    })()
  ].filter(Boolean);
  c.innerHTML = insights.map(i => `<div class="insight-card ${i.cls}"><div class="marker"></div><div><div class="title">${i.title}</div><div class="desc">${i.desc}</div></div></div>`).join('');
}

// Build language summary from filtered trend data (cache-driven, date-aware).
// Falls back to ad-level snapshot for metrics that aren't in trend data (clicks, C2I, CTR, creatives).
function buildLanguagesFromTrend(since, until) {
  const adsLangs = aggregateLanguages(DATA.ads);  // 30d totals — used for click-derived metrics
  const adMap = Object.fromEntries(adsLangs.map(L => [L.language, L]));
  const out = [];
  Object.keys(DATA.trend_by_language || {}).forEach(L => {
    if (L === 'Other') return;
    const trendRows = filterTrend(DATA.trend_by_language[L], since, until);
    const t = trendRows.reduce((a, r) => ({
      spend: a.spend + (r.spend||0),
      purchases: a.purchases + (r.purchases||0),
      installs: a.installs + (r.installs||0)
    }), {spend:0, purchases:0, installs:0});
    const ad = adMap[L] || {};
    out.push({
      language: L,
      spend: t.spend, purchases: t.purchases, installs: t.installs,
      cac: t.purchases ? t.spend/t.purchases : null,
      cpi: t.installs ? t.spend/t.installs : null,
      pay: t.installs ? 100*t.purchases/t.installs : null,
      // C2I, CTR, creatives counts come from full snapshot (no daily click data in cache)
      c2i: ad.c2i || null,
      ctr: ad.ctr || null,
      ads: ad.ads || 0,
      ads_under_300_cac: ad.ads_under_300_cac || 0
    });
  });
  return out.sort((a,b) => LANG_ORDER.indexOf(a.language) - LANG_ORDER.indexOf(b.language));
}

// Holds the currently displayed (date-filtered) ad-level data; recomputed on every renderAll
let CURRENT_ADS = DATA.ads;
let CURRENT_SUMMARY = computeSummary(DATA.ads);

function renderAll() {
  destroyAllCharts();
  // Universal date filter: derive ads from ad_weekly for the picked range
  CURRENT_ADS = getAdsForDateRange(DATE_FILTER.since, DATE_FILTER.until);
  CURRENT_SUMMARY = computeSummary(CURRENT_ADS);

  const periodLabel = (DATE_FILTER.since === SNAP_FIRST && DATE_FILTER.until === SNAP_LAST)
    ? 'Full snapshot' : (DATE_FILTER.since + ' → ' + DATE_FILTER.until);
  renderKPIs(CURRENT_SUMMARY, periodLabel);

  const langs = aggregateLanguages(CURRENT_ADS);
  renderLanguageTable(langs, CURRENT_SUMMARY);

  const camps = aggregateCampaigns(CURRENT_ADS);
  renderCampaignTable(camps, CURRENT_SUMMARY);
  renderVariantCards(camps, CURRENT_SUMMARY);
  renderThemesLangChips();
  renderThemes(CURRENT_ADS, CURRENT_SUMMARY);
  // Trend charts retain daily granularity from trend_account
  renderTrends(CURRENT_SUMMARY);
  renderCadenceTab();
  renderAdsTable(CURRENT_SUMMARY);
  renderInsights(langs, CURRENT_SUMMARY);
}

// =================== UI BINDINGS ===================
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(x => x.classList.remove('active'));
  t.classList.add('active');
  document.querySelector('.tab-content[data-tab="'+t.dataset.tab+'"]').classList.add('active');
  setTimeout(() => Object.values(window._charts||{}).forEach(c => c && c.resize && c.resize()), 50);
}));

document.querySelectorAll('#gran-toggle button').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#gran-toggle button').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  GRAN = b.dataset.gran;
  renderTrends(computeSummary(DATA.ads));
}));
document.querySelectorAll('#thr-toggle button').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#thr-toggle button').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  ACTIVE_THRESHOLD = parseInt(b.dataset.thr);
  renderDeepDive();
}));
document.getElementById('sm-metric').addEventListener('change', () => renderSmallMultiples());
document.querySelectorAll('#cad-gran button').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#cad-gran button').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  CAD_GRAN = b.dataset.gran;
  renderCadenceTab();
}));
document.getElementById('cad-lang').addEventListener('change', renderCadenceTab);
document.getElementById('cad-start').addEventListener('change', renderCadenceTab);
document.getElementById('cad-reset').addEventListener('click', () => {
  document.getElementById('cad-lang').value = '';
  document.getElementById('cad-start').value = '';
  renderCadenceTab();
});

function renderThemesLangChips() {
  const chips = document.getElementById('themes-lang-chips');
  if (!chips) return;
  const langs = [...new Set(DATA.ads.map(a => a.l))]
    .sort((a,b) => LANG_ORDER.indexOf(a) - LANG_ORDER.indexOf(b));
  const isActive = L => THEMES_LANG_FILTER == null || THEMES_LANG_FILTER.length === 0 || THEMES_LANG_FILTER.includes(L);
  chips.innerHTML = langs.map(L => `<span class="chip ${isActive(L) ? 'active' : ''}" data-lang="${L}">${L}</span>`).join('');
  chips.querySelectorAll('.chip').forEach(c => c.addEventListener('click', () => {
    const L = c.dataset.lang;
    if (THEMES_LANG_FILTER == null) {
      // currently "all" — clicking a chip means user wants only this language; deselect rest
      THEMES_LANG_FILTER = [L];
    } else {
      const idx = THEMES_LANG_FILTER.indexOf(L);
      if (idx >= 0) THEMES_LANG_FILTER.splice(idx, 1);
      else THEMES_LANG_FILTER.push(L);
      // If all languages selected, switch back to "all" mode
      if (THEMES_LANG_FILTER.length === langs.length) THEMES_LANG_FILTER = null;
    }
    renderThemesLangChips();
    renderThemes(DATA.ads, computeSummary(DATA.ads));
  }));
}
document.getElementById('themes-lang-all').addEventListener('click', () => {
  THEMES_LANG_FILTER = null;
  renderThemesLangChips();
  renderThemes(DATA.ads, computeSummary(DATA.ads));
});
document.getElementById('themes-lang-none').addEventListener('click', () => {
  THEMES_LANG_FILTER = [];
  renderThemesLangChips();
  renderThemes(DATA.ads, computeSummary(DATA.ads));
});

// =================== DATE PICKER (client-side filter only — no live fetch) ===================
function setBadge(text, kind) {
  const b = document.getElementById('data-badge');
  b.textContent = text;
  b.className = 'data-source-badge ' + kind;
}
function showError(msg) {
  const el = document.getElementById('error-banner');
  el.innerHTML = '<b>Warning.</b> ' + msg;
  el.classList.add('visible');
}
function clearError() { document.getElementById('error-banner').classList.remove('visible'); }
function daysAgoStr(d) {
  const x = new Date(); x.setDate(x.getDate() - d); return x.toISOString().slice(0,10);
}

// Snapshot date range (first to last day in trend_account)
const SNAP_FIRST = (SNAPSHOT.trend_account && SNAPSHOT.trend_account.length) ? SNAPSHOT.trend_account[0].date : null;
const SNAP_LAST  = (SNAPSHOT.trend_account && SNAPSHOT.trend_account.length) ? SNAPSHOT.trend_account[SNAPSHOT.trend_account.length-1].date : null;

// Current applied date filter
let DATE_FILTER = {since: SNAP_FIRST, until: SNAP_LAST};

function applyDateFilter(since, until) {
  clearError();
  // Clamp to snapshot range
  let clampedSince = since, clampedUntil = until;
  let clamped = false;
  if (SNAP_FIRST && since < SNAP_FIRST) { clampedSince = SNAP_FIRST; clamped = true; }
  if (SNAP_LAST && until > SNAP_LAST) { clampedUntil = SNAP_LAST; clamped = true; }
  if (clampedSince > clampedUntil) {
    showError(`Selected range ${since} → ${until} is entirely outside the cached snapshot (${SNAP_FIRST} → ${SNAP_LAST}).`);
    return;
  }
  if (clamped) {
    showError(`Snapshot covers ${SNAP_FIRST} → ${SNAP_LAST}. Showing intersection: ${clampedSince} → ${clampedUntil}. For older data, ask Claude to rebuild the snapshot or wait for the daily refresh.`);
  }
  DATE_FILTER = {since: clampedSince, until: clampedUntil};
  // Update the date inputs to reflect the clamped range
  document.getElementById('date-since').value = clampedSince;
  document.getElementById('date-until').value = clampedUntil;
  // Update badge
  const label = (clampedSince === SNAP_FIRST && clampedUntil === SNAP_LAST)
    ? `Cache · ${SNAP_FIRST} → ${SNAP_LAST} (full snapshot)`
    : `Cache · ${clampedSince} → ${clampedUntil}`;
  setBadge(label, 'live');
  renderAll();
}

function filterTrend(trendRows, since, until) {
  return (trendRows || []).filter(r => r.date >= since && r.date <= until);
}

// Date-filtered ads, derived from ad_weekly. Weekly granularity: any week that
// intersects [since, until] is included in full (weekly bins don't split mid-week).
function getAdsForDateRange(since, until) {
  if (since === SNAP_FIRST && until === SNAP_LAST) return DATA.ads;  // full snapshot
  const byAd = {};
  (DATA.ad_weekly || []).forEach(r => {
    // include if week intersects [since, until]
    if (r.week_end < since || r.week_start > until) return;
    if (!byAd[r.ad_id]) {
      byAd[r.ad_id] = {
        id: r.ad_id, n: r.n, c: r.c, l: r.l, p: r.p,
        tt: r.tt, st: r.st, subs: r.subs,
        s: 0, pu: 0, i: 0, im: 0, cl: 0
      };
    }
    const x = byAd[r.ad_id];
    x.s += r.s || 0;
    x.pu += r.pu || 0;
    x.i += r.i || 0;
    x.im += r.im || 0;
    x.cl += r.cl || 0;
  });
  return Object.values(byAd).map(a => ({
    ...a,
    cac: a.pu > 0 ? a.s / a.pu : null,
    cpi: a.i > 0 ? a.s / a.i : null,
    ctr: a.im > 0 ? 100*a.cl/a.im : null,
  }));
}

document.querySelectorAll('#presets .preset-btn').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#presets .preset-btn').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  const days = parseInt(b.dataset.days);
  // For presets, calculate dates relative to SNAP_LAST (the most recent day in the cache)
  // rather than today, so presets always land inside the snapshot range.
  const lastDate = new Date(SNAP_LAST + 'T00:00:00Z');
  const sinceD = new Date(lastDate); sinceD.setUTCDate(sinceD.getUTCDate() - (days - 1));
  applyDateFilter(sinceD.toISOString().slice(0,10), SNAP_LAST);
}));
document.getElementById('date-apply').addEventListener('click', () => {
  const s = document.getElementById('date-since').value;
  const u = document.getElementById('date-until').value;
  if (!s || !u) { showError('Pick both since and until dates'); return; }
  if (s > u) { showError('Since must be ≤ Until'); return; }
  document.querySelectorAll('#presets .preset-btn').forEach(x => x.classList.remove('active'));
  applyDateFilter(s, u);
});

(function initDates() {
  if (SNAPSHOT.trend_account && SNAPSHOT.trend_account.length) {
    document.getElementById('date-since').value = SNAPSHOT.trend_account[0].date;
    document.getElementById('date-until').value = SNAPSHOT.trend_account[SNAPSHOT.trend_account.length-1].date;
    document.getElementById('cad-start').value = SNAPSHOT.trend_account[0].date;
  }
})();

renderAll();

// Exposed for self-tests and debugging in devtools.
window.DATA = DATA;
window.SNAPSHOT = SNAPSHOT;
window.classify = classify;
window.aggregateTopHierarchy = aggregateTopHierarchy;
window.aggregateLanguages = aggregateLanguages;
window.aggregateSubthemes = aggregateSubthemes;
window.getAdsForDateRange = getAdsForDateRange;
</script>
</body>
</html>
"""

html = TEMPLATE.replace('__SNAPSHOT__', slim_str)
for fname in ['superflow_dashboard.html', 'index.html']:
    with open(os.path.join(BASE_DIR, fname), 'w') as f:
        f.write(html)
print(f'Wrote {len(html):,} bytes to superflow_dashboard.html + index.html')
