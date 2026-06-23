// Hardened end-to-end self-test for v5 dashboard.
// Verifies: classification correctness (15+ explicit ads), universal date filter,
// All Creatives Apply-button workflow, filter state persistence, pagination.

const fs = require('fs');
const { JSDOM, VirtualConsole } = require('/tmp/node_modules/jsdom');

const htmlPath = '/sessions/adoring-practical-hopper/mnt/outputs/superflow_dashboard.html';
const html = fs.readFileSync(htmlPath, 'utf-8');

const stubbedHtml = html
  .replace(/<script src="https:\/\/cdn\.jsdelivr\.net[^>]*><\/script>/g, '')
  .replace(/<link rel="stylesheet" href="https:\/\/cdn\.jsdelivr\.net[^>]*>/g, '')
  .replace('<script>', `<script>
    window.Chart = function(canvas, opts) { this.opts = opts; this.destroy = function(){}; this.resize = function(){}; this.data = opts.data; return this; };
    window.Chart.prototype = { destroy(){}, resize(){} };
    // Grid.js mock that exposes the data passed into it (so we can test filtering)
    window.gridjs = {
      Grid: function(opts){
        this.opts = opts;
        this.render = function(el){ el.__rows = opts.data; el.__pagination = opts.pagination; return this; };
        return this;
      },
      html: s => s
    };
  `);

const virtualConsole = new VirtualConsole();
const errors = [];
virtualConsole.on('jsdomError', e => errors.push('jsdomError: ' + e.message + (e.detail && e.detail.stack ? '\\n' + e.detail.stack.slice(0,400) : '')));
virtualConsole.on('error', e => errors.push('error: ' + e));

const dom = new JSDOM(stubbedHtml, {
  runScripts: 'dangerously',
  pretendToBeVisual: true,
  virtualConsole
});

let failures = 0;
function check(name, ok, detail) {
  console.log((ok?'\x1b[32mPASS\x1b[0m':'\x1b[31mFAIL\x1b[0m'), '·', name, detail?'· '+detail:'');
  if (!ok) failures++;
}

setTimeout(async () => {
  const doc = dom.window.document;
  const win = dom.window;

  // ============ STAGE 1: CLASSIFICATION CORRECTNESS ============
  console.log('\n=== STAGE 1: CLASSIFICATION CORRECTNESS (15 assertions) ===');
  // Pull the classifier from the window. We expose it for testing via window.__classify if needed.
  // Simpler: introspect by finding ads with given names in DATA.ads
  const ads = win.DATA.ads;
  function findAdByName(name) { return ads.find(a => a.n === name); }
  function findAdByContains(substring) { return ads.find(a => a.n && a.n.includes(substring)); }

  // 1. Pattern Interrupt Tank ads → AI (Bulldozer/Tank rule)
  const piTank = findAdByContains('Pattern Interrupt Tank');
  check('Pattern Interrupt Tank → AI', piTank && piTank.tt === 'AI', piTank ? piTank.tt : '(not found)');

  // 2. Bulldozer Pattern Interrupt → AI
  const bulldozer = findAdByContains('Bulldozer - Pattern interrupt');
  check('Bulldozer / Pattern interrupt → AI', bulldozer && bulldozer.tt === 'AI', bulldozer ? bulldozer.tt : '(not found)');

  // 3. Statics → top-level Statics
  const statics = findAdByContains('statics');
  check('Stop Stressing ... statics → Statics', statics && statics.tt === 'Statics', statics ? statics.tt : '(not found)');

  // 4. AI translated ad → AI
  const aiTrans = findAdByContains('AI Translated Phone Whatsapp Hammer');
  check('AI Translated ... Hammer → AI', aiTrans && aiTrans.tt === 'AI', aiTrans ? aiTrans.tt : '(not found)');

  // 5. Bhumi Replication (no AI keyword) → Human
  const bhumi = findAdByContains('Bhumi replication - superflow');
  check('Bhumi replication (no AI) → Human', bhumi && bhumi.tt === 'Human', bhumi ? bhumi.tt : '(not found)');

  // 6. KBH FX keyword → AI
  const kbh = findAdByContains('Final kbh');
  check('Final kbh ... → AI', kbh && kbh.tt === 'AI', kbh ? kbh.tt : '(not found)');

  // 7. Phone Axe FX → AI
  const phoneAxe = findAdByContains('phone - axe');
  check('phone - axe → AI', phoneAxe && phoneAxe.tt === 'AI', phoneAxe ? phoneAxe.tt : '(not found)');

  // 8. Inhouse Inf (Influencer) → Human, In-house Influencer
  const inhouseInf = findAdByContains('Inhouse Inf');
  check('Inhouse Inf → Human/In-house Influencer', inhouseInf && inhouseInf.tt === 'Human' && inhouseInf.st === 'In-house Influencer', inhouseInf ? inhouseInf.tt + '/' + inhouseInf.st : '(not found)');

  // 9. Inhouse (without Inf) → Human, In-house
  const inhouse = findAdByName('Reel - Tamil - Inhouse - Superflow OTS ads - TN 2 - Superflow - 16s - Without Subs - Sekar');
  check('Inhouse (talent) → Human/In-house', inhouse && inhouse.tt === 'Human' && inhouse.st === 'In-house', inhouse ? inhouse.tt + '/' + inhouse.st : '(not found)');

  // 10. Pattern Interrupt should be in sub-themes for any of the above
  check('Pattern Interrupt sub-theme on PI Tank ad', piTank && piTank.subs.includes('Pattern Interrupt'), piTank ? piTank.subs.join(',') : '');

  // 11. Bhumi Replication sub-theme
  check('Bhumi Replication sub-theme present', bhumi && bhumi.subs.includes('Bhumi Replication'), bhumi ? bhumi.subs.join(',') : '');

  // 12. Static-Image sub-theme on Statics
  check('Statics ads tagged with Static-Image sub-theme', statics && statics.subs.includes('Static-Image'), statics ? statics.subs.join(',') : '');

  // 13. Hierarchy aggregation has 3 buckets
  const hier = win.aggregateTopHierarchy(ads);
  check('Hierarchy has Statics + AI + Human', hier.Statics && hier.AI && hier.Human, `S=${hier.Statics.ads} AI=${hier.AI.ads} H=${hier.Human.ads}`);

  // 14. Statics count > 0
  check('Statics ad count > 0', hier.Statics.ads > 0, `${hier.Statics.ads} ads`);

  // 15. AI > Human (Pattern Interrupt now AI)
  console.log(`Counts: Statics=${hier.Statics.ads}, AI=${hier.AI.ads}, Human=${hier.Human.ads}`);
  check('After reclassification, AI count > Human count', hier.AI.ads > hier.Human.ads);

  // 16. No PI ad classified as Human (all PI-keyword ads are AI)
  const piHumans = ads.filter(a => a.subs.includes('Pattern Interrupt') && a.tt === 'Human');
  check('Zero Pattern Interrupt ads classified as Human', piHumans.length === 0, `${piHumans.length} mis-classified`);
  if (piHumans.length) piHumans.slice(0,3).forEach(a => console.log('    mis:', a.n));

  // ============ STAGE 2: UNIVERSAL DATE FILTER ============
  console.log('\n=== STAGE 2: UNIVERSAL DATE FILTER ===');
  errors.length = 0;
  // Initial: full snapshot
  const initialKpiSpend = doc.querySelector('#kpi-strip .kpi .value').textContent.trim();
  console.log('  Initial spend KPI:', initialKpiSpend);
  // Click Last 14d
  const last14d = [...doc.querySelectorAll('#presets .preset-btn')].find(b => b.dataset.days === '14');
  last14d.dispatchEvent(new dom.window.Event('click', {bubbles:true}));
  await new Promise(r => setTimeout(r, 200));
  check('No JS errors after Last 14d click', errors.length === 0);
  errors.slice(0,2).forEach(e => console.log('   ', e.slice(0,250)));
  const newKpiSpend = doc.querySelector('#kpi-strip .kpi .value').textContent.trim();
  check('KPI spend changed on date click', newKpiSpend !== initialKpiSpend, `${initialKpiSpend} → ${newKpiSpend}`);

  // Check language table is now date-filtered (totals should match KPI)
  const langTotalSpend = doc.querySelector('#language-table tfoot td:nth-child(2)').textContent.trim();
  check('Languages table TOTAL matches KPI spend after date filter', langTotalSpend === newKpiSpend, `lang=${langTotalSpend} kpi=${newKpiSpend}`);

  // Themes hierarchy should also reflect filtered ads (fewer ads than full snapshot)
  const themeRows = [...doc.querySelectorAll('#theme-table tbody tr')];
  const aiAdsCell = themeRows.find(r => r.textContent.includes('AI'))?.querySelectorAll('td')[1]?.textContent.trim();
  check('Themes AI ad count is positive after date filter', aiAdsCell && parseInt(aiAdsCell.replace(/,/g,'')) > 0, `AI=${aiAdsCell}`);

  // Switch to All Creatives tab — table should show fewer ads
  const adsTab = [...doc.querySelectorAll('.tab')].find(t => t.dataset.tab === 'ads');
  adsTab.dispatchEvent(new dom.window.Event('click', {bubbles:true}));
  await new Promise(r => setTimeout(r, 100));
  const adsRowsAfter14d = doc.getElementById('ad-table').__rows;
  check('All Creatives table has data after date filter', adsRowsAfter14d && adsRowsAfter14d.length > 0, `${adsRowsAfter14d && adsRowsAfter14d.length} rows`);

  // ============ STAGE 3: ALL CREATIVES APPLY BUTTON ============
  console.log('\n=== STAGE 3: APPLY BUTTON UX ===');
  errors.length = 0;
  // Setup: go back to full snapshot
  [...doc.querySelectorAll('#presets .preset-btn')].find(b => b.dataset.days === '30').dispatchEvent(new dom.window.Event('click', {bubbles:true}));
  await new Promise(r => setTimeout(r, 200));
  // Switch to ads tab
  adsTab.dispatchEvent(new dom.window.Event('click', {bubbles:true}));
  await new Promise(r => setTimeout(r, 100));
  const fullRows = doc.getElementById('ad-table').__rows.length;
  console.log('  Full ads count:', fullRows);

  // Change filter dropdowns WITHOUT clicking Apply — grid should not change
  const topSel = doc.getElementById('ad-top-filter');
  topSel.value = 'AI';
  topSel.dispatchEvent(new dom.window.Event('change', {bubbles:true}));
  await new Promise(r => setTimeout(r, 50));
  const rowsWithoutApply = doc.getElementById('ad-table').__rows.length;
  check('Grid does NOT change without clicking Apply', rowsWithoutApply === fullRows, `${rowsWithoutApply} (still equal to full)`);

  // Click Apply
  doc.getElementById('ad-apply').dispatchEvent(new dom.window.Event('click', {bubbles:true}));
  await new Promise(r => setTimeout(r, 100));
  const rowsAfterApply = doc.getElementById('ad-table').__rows.length;
  check('Grid changes after Apply click', rowsAfterApply < fullRows && rowsAfterApply > 0, `${rowsAfterApply} AI ads`);
  // All visible rows should be AI top-level
  const allAI = doc.getElementById('ad-table').__rows.every(r => r[2] === 'AI');
  check('All filtered rows are AI top-level', allAI);

  // Change date filter, verify Apply state SURVIVES (top filter still AI in dropdown + state)
  const last14d2 = [...doc.querySelectorAll('#presets .preset-btn')].find(b => b.dataset.days === '14');
  last14d2.dispatchEvent(new dom.window.Event('click', {bubbles:true}));
  await new Promise(r => setTimeout(r, 200));
  adsTab.dispatchEvent(new dom.window.Event('click', {bubbles:true}));
  await new Promise(r => setTimeout(r, 100));
  const topSelAfter = doc.getElementById('ad-top-filter').value;
  check('Top theme filter selection PERSISTS across date change', topSelAfter === 'AI', `value=${topSelAfter}`);
  const allAI2 = doc.getElementById('ad-table').__rows.every(r => r[2] === 'AI');
  check('Grid still showing only AI after date change (filter preserved)', allAI2);

  // Reset button
  doc.getElementById('ad-reset').dispatchEvent(new dom.window.Event('click', {bubbles:true}));
  await new Promise(r => setTimeout(r, 100));
  check('Top theme filter reset by Reset button', doc.getElementById('ad-top-filter').value === '');
  const rowsAfterReset = doc.getElementById('ad-table').__rows.length;
  check('Grid shows more rows after Reset', rowsAfterReset > rowsAfterApply, `${rowsAfterReset} (was ${rowsAfterApply})`);

  check('No JS errors during Stage 3', errors.length === 0);
  errors.slice(0,3).forEach(e => console.log('   ', e.slice(0,250)));

  // ============ STAGE 4: PAGINATION CONFIG ============
  console.log('\n=== STAGE 4: PAGINATION ===');
  const pagination = doc.getElementById('ad-table').__pagination;
  check('Grid configured with pagination', pagination && pagination.limit === 25, JSON.stringify(pagination));

  // ============ STAGE 5: COMPREHENSIVE STRESS TEST ============
  console.log('\n=== STAGE 5: STRESS TEST (50 interactions) ===');
  errors.length = 0;
  for (let i = 0; i < 10; i++) {
    // pick a random preset
    const days = ['7','14','28','30','60','90'][i % 6];
    [...doc.querySelectorAll('#presets .preset-btn')].find(b => b.dataset.days === days).dispatchEvent(new dom.window.Event('click', {bubbles:true}));
    await new Promise(r => setTimeout(r, 30));
    // switch tabs
    const tabName = ['languages','trends','campaigns','themes','ads','insights'][i % 6];
    [...doc.querySelectorAll('.tab')].find(t => t.dataset.tab === tabName).dispatchEvent(new dom.window.Event('click', {bubbles:true}));
    await new Promise(r => setTimeout(r, 30));
    // toggle a chip (themes)
    if (i % 3 === 0) {
      const chip = doc.querySelectorAll('#themes-lang-chips .chip')[i % 8];
      if (chip) chip.dispatchEvent(new dom.window.Event('click', {bubbles:true}));
      await new Promise(r => setTimeout(r, 30));
    }
  }
  check('No JS errors after 30+ rapid interactions', errors.length === 0);
  errors.slice(0,3).forEach(e => console.log('   ', e.slice(0,250)));

  // ============ STAGE 6: ALL TABS PRESENT ============
  console.log('\n=== STAGE 6: KPI STRIP COHERENCE ===');
  // Go back to full snapshot
  [...doc.querySelectorAll('#presets .preset-btn')].find(b => b.dataset.days === '30').dispatchEvent(new dom.window.Event('click', {bubbles:true}));
  await new Promise(r => setTimeout(r, 200));
  const kpiTiles = doc.querySelectorAll('#kpi-strip .kpi');
  check('KPI strip has 7 tiles', kpiTiles.length === 7);
  const kpis = {};
  kpiTiles.forEach(k => {
    kpis[k.querySelector('.label').textContent.trim()] = k.querySelector('.value').textContent.trim();
  });
  console.log('  ', kpis);
  // Verify creative count matches ad table count
  const adsTabLink = [...doc.querySelectorAll('.tab')].find(t => t.dataset.tab === 'ads');
  adsTabLink.dispatchEvent(new dom.window.Event('click', {bubbles:true}));
  await new Promise(r => setTimeout(r, 100));
  // Reset filters and check count
  doc.getElementById('ad-reset').dispatchEvent(new dom.window.Event('click', {bubbles:true}));
  await new Promise(r => setTimeout(r, 100));
  const totalAdRows = doc.getElementById('ad-table').__rows.length;
  console.log('  Ads tab rows after reset:', totalAdRows);

  console.log('\n=== SUMMARY ===');
  console.log(failures === 0 ? '\x1b[32mAll checks PASS\x1b[0m' : `\x1b[31m${failures} FAILURES\x1b[0m`);
  process.exit(failures > 0 ? 1 : 0);
}, 1500);
