from __future__ import annotations


def render_demo_ui_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GrantFlow Demo Console</title>
  <style>
    :root {
      --bg: #f3efe6;
      --paper: #fffaf1;
      --ink: #1f1d1a;
      --muted: #6d665d;
      --line: #d8cfbf;
      --accent: #0f766e;
      --accent-2: #b45309;
      --good: #166534;
      --warn: #b45309;
      --bad: #b91c1c;
      --shadow: 0 10px 30px rgba(31, 29, 26, 0.08);
      --radius: 14px;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      --sans: "Avenir Next", "Segoe UI", system-ui, sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--sans);
      color: var(--ink);
      background:
        radial-gradient(circle at 10% 10%, rgba(15,118,110,.10), transparent 45%),
        radial-gradient(circle at 90% 0%, rgba(180,83,9,.12), transparent 35%),
        linear-gradient(180deg, #f4f0e8 0%, #efe9dd 100%);
    }
    .wrap { max-width: 1320px; margin: 0 auto; padding: 22px 18px 40px; }
    .hero {
      background: linear-gradient(135deg, rgba(255,250,241,.92), rgba(250,242,228,.92));
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: var(--shadow);
      margin-bottom: 16px;
      backdrop-filter: blur(2px);
    }
    .hero h1 { margin: 0 0 4px; font-size: 1.4rem; letter-spacing: .02em; }
    .hero p { margin: 0; color: var(--muted); }
    .toolbar, .grid { display: grid; gap: 12px; }
    .toolbar { grid-template-columns: 1.6fr .8fr .7fr .7fr auto auto; margin: 12px 0 16px; }
    .grid { grid-template-columns: 1.1fr .9fr; }
    .stack { display: grid; gap: 12px; }
    .card {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .card h2 {
      margin: 0;
      padding: 12px 14px;
      font-size: .95rem;
      letter-spacing: .04em;
      text-transform: uppercase;
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,.55);
    }
    .card .body { padding: 12px 14px; }
    label { display: block; font-size: .75rem; color: var(--muted); margin-bottom: 4px; text-transform: uppercase; letter-spacing: .04em; }
    input, select, textarea, button {
      width: 100%;
      border-radius: 10px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      font: inherit;
      padding: 10px 11px;
    }
    textarea { min-height: 78px; resize: vertical; font-family: var(--mono); font-size: .86rem; }
    .json { min-height: 120px; }
    button {
      cursor: pointer;
      background: linear-gradient(180deg, #fff, #f5f0e5);
      transition: transform .08s ease, box-shadow .12s ease;
      box-shadow: 0 1px 0 rgba(31,29,26,.05);
    }
    button:hover { transform: translateY(-1px); }
    button.primary { background: linear-gradient(180deg, #117c73, #0f766e); color: #fff; border-color: #0f766e; }
    button.secondary { background: linear-gradient(180deg, #c96f1b, #b45309); color: #fff; border-color: #b45309; }
    button.ghost { background: transparent; }
    button.danger { background: linear-gradient(180deg, #dc2626, #b91c1c); color: #fff; border-color: #b91c1c; }
    .row { display: grid; gap: 10px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .row3 { display: grid; gap: 10px; grid-template-columns: 1fr 1fr 1fr; }
    .row4 { display: grid; gap: 10px; grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .mono { font-family: var(--mono); font-size: .84rem; }
    .pill {
      display: inline-flex; align-items: center; gap: 6px;
      border-radius: 999px; padding: 4px 10px; border: 1px solid var(--line);
      background: #fff; font-size: .82rem;
    }
    .pill .dot { width: 8px; height: 8px; border-radius: 999px; background: var(--muted); }
    .status-accepted .dot { background: #2563eb; }
    .status-running .dot { background: #0891b2; }
    .status-pending_hitl .dot { background: var(--warn); }
    .status-done .dot { background: var(--good); }
    .status-error .dot, .status-canceled .dot { background: var(--bad); }
    .readiness-level-high { border-color: rgba(185,28,28,.35); background: rgba(185,28,28,.08); color: #7f1d1d; }
    .readiness-level-medium { border-color: rgba(180,83,9,.35); background: rgba(180,83,9,.10); color: #7c2d12; }
    .readiness-level-low { border-color: rgba(22,101,52,.30); background: rgba(22,101,52,.08); color: #14532d; }
    .readiness-level-none { border-color: rgba(109,102,93,.30); background: rgba(109,102,93,.08); color: #57534e; }
    .readiness-level-high .dot { background: var(--bad); }
    .readiness-level-medium .dot { background: var(--warn); }
    .readiness-level-low .dot { background: var(--good); }
    .readiness-level-none .dot { background: var(--muted); }
    .kpis { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .kpi {
      border: 1px solid var(--line); border-radius: 12px; background: rgba(255,255,255,.8); padding: 10px;
    }
    .kpi .label { color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }
    .kpi .value { font-family: var(--mono); font-size: 1rem; }
    .kpi .value.risk-high { color: var(--bad); font-weight: 700; }
    .kpi .value.risk-medium { color: var(--warn); font-weight: 700; }
    .kpi .value.risk-low { color: var(--good); font-weight: 700; }
    .kpi .value.risk-none { color: var(--muted); font-weight: 600; }
    pre {
      margin: 0; white-space: pre-wrap; word-break: break-word;
      background: #1f2329; color: #e5e7eb; border-radius: 10px; padding: 12px;
      font-family: var(--mono); font-size: .79rem; line-height: 1.4;
      max-height: 360px; overflow: auto;
    }
    .list {
      display: grid; gap: 8px;
      max-height: 320px; overflow: auto;
    }
    .item {
      border: 1px solid var(--line); background: rgba(255,255,255,.78); border-radius: 12px; padding: 10px;
    }
    .item.severity-high { border-left: 4px solid var(--bad); }
    .item.severity-medium { border-left: 4px solid var(--warn); }
    .item.severity-low { border-left: 4px solid var(--good); }
    .item .title { font-weight: 600; margin-bottom: 4px; }
    .item .sub { color: var(--muted); font-size: .82rem; }
    .footer-note { color: var(--muted); font-size: .8rem; margin-top: 8px; }
    .preflight-alert { margin-top: 10px; }
    .preflight-alert .sub { color: inherit; }
    .hidden { display: none !important; }
    .blink-in { animation: fadeSlide .25s ease; }
    @keyframes fadeSlide { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
    @media (max-width: 1080px) {
      .toolbar { grid-template-columns: 1fr 1fr; }
      .grid { grid-template-columns: 1fr; }
      .row3, .row4, .kpis { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 640px) {
      .toolbar, .row, .row3, .row4, .kpis { grid-template-columns: 1fr; }
      .wrap { padding: 12px; }
      .hero h1 { font-size: 1.15rem; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>GrantFlow Demo Console</h1>
      <p>Minimal operator UI for generate → HITL → review traces (citations, versions, diff, critic findings, events, metrics).</p>
    </section>

    <section class="toolbar">
      <div>
        <label for="apiBase">API Base</label>
        <input id="apiBase" value="" placeholder="http://127.0.0.1:8000" />
      </div>
      <div>
        <label for="apiKey">X-API-Key (optional)</label>
        <input id="apiKey" value="" placeholder="server key if auth enabled" />
      </div>
      <div>
        <label for="jobIdInput">Job ID</label>
        <input id="jobIdInput" placeholder="Paste job id or generate new" />
      </div>
      <div>
        <label for="diffSection">Diff Section</label>
        <select id="diffSection">
          <option value="">auto</option>
          <option value="toc">toc</option>
          <option value="logframe">logframe</option>
        </select>
      </div>
      <div style="align-self:end;">
        <button id="refreshAllBtn" class="ghost">Refresh All</button>
      </div>
      <div style="align-self:end;">
        <button id="pollToggleBtn" class="secondary">Start Poll</button>
      </div>
      <div style="align-self:end;">
        <button id="clearFiltersBtn" class="ghost">Clear All Filters</button>
      </div>
    </section>

    <section class="grid">
      <div class="stack">
        <div class="card">
          <h2>Generate</h2>
          <div class="body">
            <div class="row4">
              <div><label for="donorId">Donor ID</label><input id="donorId" value="usaid" /></div>
              <div><label for="project">Project</label><input id="project" value="Water Sanitation" /></div>
              <div><label for="country">Country</label><input id="country" value="Kenya" /></div>
              <div><label for="hitlEnabled">HITL</label>
                <select id="hitlEnabled"><option value="false">false</option><option value="true">true</option></select>
              </div>
            </div>
            <div class="row4" style="margin-top:10px;">
              <div><label for="llmMode">LLM Mode</label><select id="llmMode"><option value="false">false</option><option value="true">true</option></select></div>
              <div><label for="strictPreflight">Strict Preflight</label><select id="strictPreflight"><option value="false">false</option><option value="true">true</option></select></div>
              <div><label for="webhookUrl">Webhook URL (optional)</label><input id="webhookUrl" placeholder="https://example.com/webhook" /></div>
              <div><label for="webhookSecret">Webhook Secret (optional)</label><input id="webhookSecret" placeholder="secret" /></div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <div>
                <label for="generatePresetSelect">Generate Preset</label>
                <select id="generatePresetSelect">
                  <option value="">none</option>
                  <option value="usaid_gov_ai_kazakhstan">USAID: AI civil service (KZ)</option>
                  <option value="eu_digital_governance_moldova">EU: digital governance (MD)</option>
                  <option value="worldbank_public_sector_uzbekistan">World Bank: public sector performance (UZ)</option>
                </select>
              </div>
              <div style="align-self:end;">
                <button id="applyPresetBtn" class="ghost">Apply Preset</button>
              </div>
              <div style="align-self:end;">
                <button id="clearPresetContextBtn" class="ghost">Clear Extra Context</button>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>RAG Readiness (for selected preset)</label>
                <div id="generatePresetReadinessPill" class="pill"><span class="dot"></span><span id="generatePresetReadinessText">No preset selected</span></div>
                <div id="generatePresetReadinessHint" class="sub" style="margin-top:6px;">Select a preset to see missing recommended document families.</div>
              </div>
              <div style="align-self:end;">
                <button id="syncGenerateReadinessBtn" class="ghost">Sync Readiness Now</button>
              </div>
            </div>
            <div class="row" style="margin-top:8px;">
              <label style="display:flex; align-items:center; gap:8px;">
                <input id="skipZeroReadinessWarningCheckbox" type="checkbox" />
                <span id="skipZeroReadinessWarningLabel">Don't ask again for this preset</span>
              </label>
            </div>
            <div id="generatePreflightAlert" class="item preflight-alert severity-low hidden">
              <div id="generatePreflightAlertTitle" class="title">Preflight alert</div>
              <div id="generatePreflightAlertBody" class="sub">-</div>
            </div>
            <div style="margin-top:10px;">
              <label for="inputContextJson">Extra Input Context JSON (optional)</label>
              <textarea id="inputContextJson" class="json" placeholder='{"problem":"...", "target_population":"...", "key_activities":["..."]}'></textarea>
            </div>
            <div style="margin-top:10px;">
              <button id="generateBtn" class="primary">Generate Draft</button>
            </div>
            <div class="footer-note">Tip: presets fill donor/project/country plus extra JSON context. You can edit the JSON before generating.</div>
            <div class="footer-note">Tip: when auth is enabled on the API, set <code>X-API-Key</code> above once and all actions will use it.</div>
          </div>
        </div>

        <div class="card">
          <h2>Ingest (RAG Prep)</h2>
          <div class="body">
            <div class="row3">
              <div>
                <label for="ingestPresetSelect">Ingest Preset</label>
                <select id="ingestPresetSelect">
                  <option value="">none</option>
                  <option value="usaid_gov_ai_kazakhstan">USAID: AI civil service (KZ)</option>
                  <option value="eu_digital_governance_moldova">EU: digital governance (MD)</option>
                  <option value="worldbank_public_sector_uzbekistan">World Bank: public sector performance (UZ)</option>
                </select>
              </div>
              <div style="align-self:end;">
                <button id="applyIngestPresetBtn" class="ghost">Apply Ingest Preset</button>
              </div>
              <div style="align-self:end;">
                <button id="syncIngestDonorBtn" class="ghost">Use Generate Donor</button>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div><label for="ingestDonorId">Ingest Donor ID</label><input id="ingestDonorId" value="usaid" /></div>
              <div><label for="ingestFileInput">PDF File</label><input id="ingestFileInput" type="file" accept="application/pdf,.pdf" /></div>
            </div>
            <div style="margin-top:10px;">
              <label for="ingestMetadataJson">Ingest Metadata JSON (optional)</label>
              <textarea id="ingestMetadataJson" class="json" placeholder='{"source_type":"donor_policy","doc_family":"usaid_guidance"}'></textarea>
            </div>
            <div style="margin-top:10px;">
              <button id="ingestBtn" class="secondary">Upload PDF to /ingest</button>
            </div>
            <div class="footer-note">Use this before generation to improve citation grounding and confidence. Presets list recommended document types to upload.</div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Checklist Progress</label>
                <div id="ingestChecklistSummary" class="pill"><span class="dot"></span><span>0/0 complete</span></div>
              </div>
              <div style="align-self:end; display:grid; gap:8px; grid-template-columns: 1fr 1fr;">
                <button id="syncIngestChecklistServerBtn" class="ghost">Sync from Server</button>
                <button id="resetIngestChecklistBtn" class="ghost">Reset Checklist Progress</button>
              </div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="copyIngestInventoryJsonBtn" class="ghost">Copy Inventory JSON</button>
              <button id="downloadIngestInventoryJsonBtn" class="ghost">Download Inventory JSON</button>
              <button id="downloadIngestInventoryCsvBtn" class="secondary">Download Inventory CSV</button>
            </div>
            <div class="list" id="ingestChecklistProgressList" style="margin-top:10px;"></div>
            <div class="list" id="ingestPresetGuidanceList" style="margin-top:10px;"></div>
            <pre id="ingestInventoryJson" style="margin-top:10px;">No ingest inventory loaded yet.</pre>
            <pre id="ingestResultJson" style="margin-top:10px;">No ingest upload yet.</pre>
          </div>
        </div>

        <div class="card">
          <h2>HITL Actions</h2>
          <div class="body">
            <div class="row3">
              <div>
                <label>Current Status</label>
                <div id="statusPill" class="pill status-unknown"><span class="dot"></span><span id="statusPillText">unknown</span></div>
              </div>
              <div>
                <label>Checkpoint ID</label>
                <input id="checkpointId" readonly />
              </div>
              <div>
                <label>Checkpoint Stage</label>
                <input id="checkpointStage" readonly />
              </div>
            </div>
            <div style="margin-top:10px;">
              <label for="hitlFeedback">Feedback</label>
              <textarea id="hitlFeedback" placeholder="Reviewer notes for approve/reject"></textarea>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="approveBtn" class="primary">Approve Checkpoint</button>
              <button id="rejectBtn" class="danger">Reject Checkpoint</button>
              <button id="resumeBtn" class="secondary">Resume Job</button>
            </div>
            <div class="row" style="margin-top:10px;">
              <button id="cancelBtn" class="danger">Cancel Job</button>
              <button id="openPendingBtn" class="ghost">Load /hitl/pending</button>
            </div>
          </div>
        </div>

        <div class="card">
          <h2>Status Snapshot</h2>
          <div class="body">
            <pre id="statusJson">No job selected.</pre>
          </div>
        </div>
      </div>

      <div class="stack">
        <div class="card">
          <h2>Metrics</h2>
          <div class="body">
            <div class="kpis" id="metricsCards">
              <div class="kpi"><div class="label">Time to first draft</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Time to terminal</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Time in pending HITL</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Pauses</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Resumes</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Terminal status</div><div class="value mono">-</div></div>
            </div>
            <div style="margin-top:10px;">
              <pre id="metricsJson">{}</pre>
            </div>
          </div>
        </div>

        <div class="card">
          <h2>Quality Summary</h2>
          <div class="body">
            <div class="row">
              <button id="qualityBtn" class="ghost">Load Quality Summary</button>
              <div class="sub" style="align-self:center;">Critic + citations + architect policy summary for reviewer triage.</div>
            </div>
            <div class="kpis" id="qualityCards" style="margin-top:10px;">
              <div class="kpi"><div class="label">Quality score</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Critic score</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Fatal flaws</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Open findings</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Avg citation conf</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Threshold hit-rate</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Claim-support</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Architect fallback</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Preflight risk</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Strict preflight</div><div class="value mono">-</div></div>
            </div>
            <div id="qualityPreflightMetaLine" class="footer-note mono">warning_count=- · coverage_rate=-</div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Citation Types (Job)</label>
                <div class="list" id="qualityCitationTypeCountsList"></div>
              </div>
              <div>
                <label>Architect Citation Types (Job)</label>
                <div class="list" id="qualityArchitectCitationTypeCountsList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Advisory Normalization (LLM Critic)</label>
                <div class="list" id="qualityAdvisoryBadgeList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>LLM Finding Labels (Job)</label>
                <div class="list" id="qualityLlmFindingLabelsList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>RAG Readiness Warnings</label>
                <div id="qualityReadinessWarningLevelPill" class="pill readiness-level-none" style="margin-bottom:8px;">
                  <span class="dot"></span><span>warning_level=none</span>
                </div>
                <div class="list" id="qualityReadinessWarningsList"></div>
              </div>
            </div>
            <div style="margin-top:10px;">
              <pre id="qualityJson">{}</pre>
            </div>
          </div>
        </div>

        <div class="card">
          <h2>Portfolio Metrics</h2>
          <div class="body">
            <div class="row4">
              <div>
                <label for="portfolioDonorFilter">Donor Filter</label>
                <input id="portfolioDonorFilter" placeholder="usaid" />
              </div>
              <div>
                <label for="portfolioStatusFilter">Status Filter</label>
                <select id="portfolioStatusFilter">
                  <option value="">all</option>
                  <option value="accepted">accepted</option>
                  <option value="running">running</option>
                  <option value="pending_hitl">pending_hitl</option>
                  <option value="done">done</option>
                  <option value="error">error</option>
                  <option value="canceled">canceled</option>
                </select>
              </div>
              <div>
                <label for="portfolioHitlFilter">HITL Filter</label>
                <select id="portfolioHitlFilter">
                  <option value="">all</option>
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              </div>
              <div>
                <label for="portfolioWarningLevelFilter">Warning Level</label>
                <select id="portfolioWarningLevelFilter">
                  <option value="">all</option>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                  <option value="none">none</option>
                </select>
              </div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <div>
                <label for="portfolioGroundingRiskLevelFilter">Grounding Risk</label>
                <select id="portfolioGroundingRiskLevelFilter">
                  <option value="">all</option>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                  <option value="unknown">unknown</option>
                </select>
              </div>
              <div>
                <label for="portfolioFindingStatusFilter">Finding Status</label>
                <select id="portfolioFindingStatusFilter">
                  <option value="">all</option>
                  <option value="open">open</option>
                  <option value="acknowledged">acknowledged</option>
                  <option value="resolved">resolved</option>
                </select>
              </div>
              <div>
                <label for="portfolioFindingSeverityFilter">Finding Severity</label>
                <select id="portfolioFindingSeverityFilter">
                  <option value="">all</option>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                </select>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <button id="portfolioBtn" class="ghost">Load Portfolio Metrics</button>
              <button id="portfolioClearBtn" class="ghost">Clear Portfolio Filters</button>
              <div class="sub" style="align-self:center;">Aggregates across jobs in current store.</div>
            </div>
            <div class="kpis" id="portfolioMetricsCards" style="margin-top:10px;">
              <div class="kpi"><div class="label">Jobs</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Terminal Jobs</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">HITL Jobs</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Total Pauses</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Total Resumes</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Avg TTFD</div><div class="value mono">-</div></div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Portfolio Status Counts</label>
                <div class="list" id="portfolioStatusCountsList"></div>
              </div>
              <div>
                <label>Top Donors</label>
                <div class="list" id="portfolioDonorCountsList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Preflight Warning Levels (Jobs)</label>
                <div class="list" id="portfolioMetricsWarningLevelsList"></div>
              </div>
              <div>
                <label>Grounding Risk Drilldown (Jobs)</label>
                <div class="list" id="portfolioMetricsGroundingRiskLevelsList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <button id="copyPortfolioMetricsJsonBtn" class="ghost">Copy Metrics JSON</button>
              <button id="downloadPortfolioMetricsJsonBtn" class="ghost">Export Metrics JSON</button>
              <button id="downloadPortfolioMetricsCsvBtn" class="secondary">Export Metrics CSV</button>
            </div>
            <div style="margin-top:10px;">
              <pre id="portfolioMetricsJson">{}</pre>
            </div>
            <div style="margin-top:14px;">
              <label>Portfolio Quality</label>
              <div class="sub" style="margin-top:4px;">Aggregated quality/critic/citation signals across the filtered portfolio.</div>
            </div>
            <div class="kpis" id="portfolioQualityCards" style="margin-top:10px;">
              <div class="kpi"><div class="label">Avg Quality</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Needs Revision</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Open Findings</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">High Severity</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Avg Citation Conf</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Threshold Hit-rate</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Claim-support Avg</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Weighted Risk</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">High-Priority Signals</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">% High-warning Jobs</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">% Medium-warning Jobs</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">% Low-warning Jobs</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">% No-warning Jobs</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Fallback Dominance</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">High-Risk Donors</div><div class="value mono">-</div></div>
            </div>
            <div id="portfolioWarningMetaLine" class="footer-note mono">high=- · medium=- · low=- · none=- · total=-</div>
            <div class="row" style="margin-top:10px;">
              <button id="copyPortfolioQualityJsonBtn" class="ghost">Copy Quality JSON</button>
              <button id="downloadPortfolioQualityJsonBtn" class="ghost">Export Quality JSON</button>
              <button id="downloadPortfolioQualityCsvBtn" class="secondary">Export Quality CSV</button>
            </div>
            <div style="margin-top:14px;">
              <label>Export (Server-side)</label>
              <div class="sub" style="margin-top:4px;">Uses current filters for portfolio endpoints and selected donor for inventory.</div>
            </div>
            <div class="row4" style="margin-top:10px;">
              <div>
                <label for="exportGzipEnabled">Gzip</label>
                <select id="exportGzipEnabled">
                  <option value="false">false</option>
                  <option value="true">true</option>
                </select>
              </div>
              <div style="align-self:end;">
                <button id="exportInventoryJsonBtn" class="ghost">Inventory JSON</button>
              </div>
              <div style="align-self:end;">
                <button id="exportInventoryCsvBtn" class="ghost">Inventory CSV</button>
              </div>
              <div style="align-self:end;"></div>
            </div>
            <div class="row4" style="margin-top:10px;">
              <div style="align-self:end;">
                <button id="exportPortfolioMetricsJsonBtn" class="ghost">Metrics JSON</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioMetricsCsvBtn" class="ghost">Metrics CSV</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioQualityJsonBtn" class="ghost">Quality JSON</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioQualityCsvBtn" class="secondary">Quality CSV</button>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Top Donors (Needs Revision)</label>
                <div class="list" id="portfolioQualityRiskList"></div>
              </div>
              <div>
                <label>Top Donors (Open Findings)</label>
                <div class="list" id="portfolioQualityOpenFindingsList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Preflight Warning Levels</label>
                <div class="list" id="portfolioQualityWarningLevelsList"></div>
              </div>
              <div>
                <label>Grounding Risk Levels</label>
                <div class="list" id="portfolioQualityGroundingRiskLevelsList"></div>
              </div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <div>
                <label>Citation Types (Portfolio)</label>
                <div class="list" id="portfolioQualityCitationTypeCountsList"></div>
              </div>
              <div>
                <label>Architect Citation Types</label>
                <div class="list" id="portfolioQualityArchitectCitationTypeCountsList"></div>
              </div>
              <div>
                <label>MEL Citation Types</label>
                <div class="list" id="portfolioQualityMelCitationTypeCountsList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Finding Status</label>
                <div class="list" id="portfolioQualityFindingStatusList"></div>
              </div>
              <div>
                <label>Finding Severity</label>
                <div class="list" id="portfolioQualityFindingSeverityList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Top Donors (Grounding Risk)</label>
                <div class="list" id="portfolioQualityGroundingRiskList"></div>
              </div>
              <div></div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Priority Signals (Weighted)</label>
                <div class="list" id="portfolioQualityPrioritySignalsList"></div>
              </div>
              <div>
                <label>Top Donors (Weighted Risk)</label>
                <div class="list" id="portfolioQualityWeightedDonorsList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>LLM Finding Labels (Portfolio)</label>
                <div class="list" id="portfolioQualityLlmLabelCountsList"></div>
              </div>
              <div>
                <label>Top Donor LLM Labels (Weighted Risk)</label>
                <div class="list" id="portfolioQualityTopDonorLlmLabelCountsList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Top Donor Advisory Rejected Reasons</label>
                <div class="list" id="portfolioQualityTopDonorAdvisoryRejectedReasonsList"></div>
              </div>
              <div>
                <label>Top Donor Advisory Applied (Jobs)</label>
                <div class="list" id="portfolioQualityTopDonorAdvisoryAppliedList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Focused Donor (Weighted Risk) Summary</label>
                <div id="portfolioQualityFocusedDonorAdvisoryPill" class="pill status-unknown" style="margin-bottom:8px;">
                  <span class="dot"></span><span id="portfolioQualityFocusedDonorAdvisoryPillText">advisory rate: -</span>
                </div>
                <div class="list" id="portfolioQualityFocusedDonorSummaryList"></div>
              </div>
              <div>
                <label>Focused Donor LLM Labels</label>
                <div class="list" id="portfolioQualityFocusedDonorLlmLabelCountsList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Focused Donor Advisory Rejected Reasons</label>
                <div class="list" id="portfolioQualityFocusedDonorAdvisoryRejectedReasonsList"></div>
              </div>
              <div>
                <label>Focused Donor Advisory Labels (Applied)</label>
                <div class="list" id="portfolioQualityFocusedDonorAdvisoryAppliedLabelCountsList"></div>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Focused Donor Advisory Labels (Rejected)</label>
                <div class="list" id="portfolioQualityFocusedDonorAdvisoryRejectedLabelCountsList"></div>
              </div>
              <div></div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>LLM Advisory Applied (Jobs)</label>
                <div class="list" id="portfolioQualityAdvisoryAppliedList"></div>
              </div>
              <div>
                <label>LLM Advisory Rejected Reasons</label>
                <div class="list" id="portfolioQualityAdvisoryRejectedReasonsList"></div>
              </div>
            </div>
            <div style="margin-top:10px;">
              <pre id="portfolioQualityJson">{}</pre>
            </div>
          </div>
        </div>

        <div class="card">
          <h2>Critic Findings</h2>
          <div class="body">
            <div class="row4">
              <button id="criticBtn" class="ghost">Load Critic</button>
              <div>
                <label for="criticSectionFilter">Filter Section</label>
                <select id="criticSectionFilter">
                  <option value="">all</option>
                  <option value="toc">toc</option>
                  <option value="logframe">logframe</option>
                  <option value="general">general</option>
                </select>
              </div>
              <div>
                <label for="criticSeverityFilter">Filter Severity</label>
                <select id="criticSeverityFilter">
                  <option value="">all</option>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                </select>
              </div>
              <div>
                <label for="criticFindingStatusFilter">Filter Finding Status</label>
                <select id="criticFindingStatusFilter">
                  <option value="">all</option>
                  <option value="open">open</option>
                  <option value="acknowledged">acknowledged</option>
                  <option value="resolved">resolved</option>
                </select>
              </div>
              <div>
                <label for="criticCitationConfidenceFilter">Citation Confidence</label>
                <select id="criticCitationConfidenceFilter">
                  <option value="">all</option>
                  <option value="low">low (&lt; 0.30)</option>
                  <option value="high">high (&ge; 0.70)</option>
                </select>
              </div>
            </div>
            <div class="row4" style="margin-top:10px;">
              <div>
                <label for="criticBulkTargetStatus">Bulk Target Status</label>
                <select id="criticBulkTargetStatus">
                  <option value="acknowledged">acknowledged</option>
                  <option value="resolved">resolved</option>
                  <option value="open">open</option>
                </select>
              </div>
              <div>
                <label for="criticBulkScope">Bulk Scope</label>
                <select id="criticBulkScope">
                  <option value="filtered">filtered (current critic filters)</option>
                  <option value="all">all findings in job</option>
                </select>
              </div>
              <div style="align-self:end;">
                <button id="criticBulkApplyBtn" class="secondary">Apply Bulk Status</button>
              </div>
              <div style="align-self:end;">
                <button id="criticBulkClearFiltersBtn" class="ghost">Clear Critic Filters</button>
              </div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <div>
                <label>Advisory Diagnostics</label>
                <div class="list" id="criticAdvisorySummaryList"></div>
              </div>
              <div>
                <label>Advisory Candidate Labels</label>
                <div class="list" id="criticAdvisoryLabelsList"></div>
              </div>
              <div>
                <label>Advisory Normalization</label>
                <div class="list" id="criticAdvisoryNormalizationList"></div>
              </div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <div>
                <label>Fatal Flaws</label>
                <div class="list" id="criticFlawsList"></div>
              </div>
              <div>
                <label>Rule Checks</label>
                <div class="list" id="criticChecksList"></div>
              </div>
              <div>
                <label>Citation Context</label>
                <div class="list" id="criticContextList"></div>
              </div>
            </div>
            <div style="margin-top:10px;">
              <pre id="criticBulkResultJson">{}</pre>
            </div>
            <div style="margin-top:10px;">
              <pre id="criticJson">{}</pre>
            </div>
          </div>
        </div>

        <div class="card">
          <h2>Versions & Diff</h2>
          <div class="body">
            <div class="row">
              <button id="versionsBtn" class="ghost">Load Versions</button>
              <button id="diffBtn" class="ghost">Load Diff</button>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label for="fromVersionId">from_version_id (optional)</label>
                <input id="fromVersionId" placeholder="toc_v1" />
              </div>
              <div>
                <label for="toVersionId">to_version_id (optional)</label>
                <input id="toVersionId" placeholder="toc_v2" />
              </div>
            </div>
            <div style="margin-top:10px;">
              <div class="list" id="versionsList"></div>
            </div>
            <div style="margin-top:10px;">
              <pre id="diffPre">No diff loaded.</pre>
            </div>
          </div>
        </div>

        <div class="card">
          <h2>Citations</h2>
          <div class="body">
            <div class="row">
              <button id="citationsBtn" class="ghost">Load Citations</button>
              <button id="eventsBtn" class="ghost">Load Events</button>
            </div>
            <div style="margin-top:10px;">
              <div class="list" id="citationsList"></div>
            </div>
          </div>
        </div>

        <div class="card">
          <h2>Export Payload</h2>
          <div class="body">
            <div class="row">
              <button id="exportPayloadBtn" class="ghost">Load Export Payload</button>
              <button id="copyExportPayloadBtn" class="ghost">Copy Payload JSON</button>
            </div>
            <div style="margin-top:10px;">
              <button id="exportZipFromPayloadBtn" class="secondary">Export ZIP from Payload</button>
            </div>
            <div class="footer-note">
              Review-ready payload for <code>POST /export</code> (<code>state</code> + <code>critic_findings</code> + <code>review_comments</code>).
            </div>
            <div style="margin-top:10px;">
              <pre id="exportPayloadJson">{}</pre>
            </div>
          </div>
        </div>

        <div class="card">
          <h2>Timeline Events</h2>
          <div class="body">
            <div class="list" id="eventsList"></div>
          </div>
        </div>

        <div class="card">
          <h2>Review Comments</h2>
          <div class="body">
            <div class="row3">
              <div>
                <label for="commentsFilterSection">List Filter: Section</label>
                <select id="commentsFilterSection">
                  <option value="">all</option>
                  <option value="general">general</option>
                  <option value="toc">toc</option>
                  <option value="logframe">logframe</option>
                </select>
              </div>
              <div>
                <label for="commentsFilterStatus">List Filter: Status</label>
                <select id="commentsFilterStatus">
                  <option value="">all</option>
                  <option value="open">open</option>
                  <option value="resolved">resolved</option>
                </select>
              </div>
              <div>
                <label for="commentsFilterVersionId">List Filter: Version ID</label>
                <input id="commentsFilterVersionId" placeholder="toc_v2" />
              </div>
            </div>
            <div class="row3">
              <div>
                <label for="commentSection">Section</label>
                <select id="commentSection">
                  <option value="general">general</option>
                  <option value="toc">toc</option>
                  <option value="logframe">logframe</option>
                </select>
              </div>
              <div>
                <label for="commentAuthor">Author (optional)</label>
                <input id="commentAuthor" placeholder="reviewer-1" />
              </div>
              <div>
                <label for="commentVersionId">Version ID (optional)</label>
                <input id="commentVersionId" placeholder="toc_v2" />
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label for="linkedFindingId">Linked Finding ID (optional)</label>
                <input id="linkedFindingId" placeholder="Auto-filled from Critic Findings" />
              </div>
              <div style="align-self:end;">
                <button id="clearLinkedFindingBtn" class="ghost">Clear Linked Finding</button>
              </div>
            </div>
            <div style="margin-top:10px;">
              <label for="commentMessage">Comment</label>
              <textarea id="commentMessage" placeholder="Reviewer note for ToC / LogFrame / general workflow issue"></textarea>
            </div>
            <div class="row4" style="margin-top:10px;">
              <button id="commentsBtn" class="ghost">Load Comments</button>
              <button id="reviewWorkflowBtn" class="ghost">Load Review Workflow</button>
              <button id="addCommentBtn" class="primary">Add Comment</button>
              <button id="resolveCommentBtn" class="secondary">Resolve Selected</button>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label for="selectedCommentId">Selected Comment ID</label>
                <input id="selectedCommentId" readonly />
              </div>
              <div style="align-self:end;">
                <button id="reopenCommentBtn" class="ghost">Reopen Selected</button>
              </div>
            </div>
            <div style="margin-top:10px;">
              <div class="list" id="commentsList"></div>
            </div>
            <div class="row4" style="margin-top:10px;">
              <div>
                <label for="reviewWorkflowEventTypeFilter">Workflow Filter: Event Type</label>
                <select id="reviewWorkflowEventTypeFilter">
                  <option value="">all</option>
                  <option value="critic_finding_status_changed">critic_finding_status_changed</option>
                  <option value="review_comment_added">review_comment_added</option>
                  <option value="review_comment_status_changed">review_comment_status_changed</option>
                </select>
              </div>
              <div>
                <label for="reviewWorkflowFindingIdFilter">Workflow Filter: Finding ID</label>
                <input id="reviewWorkflowFindingIdFilter" placeholder="finding-id" />
              </div>
              <div>
                <label for="reviewWorkflowCommentStatusFilter">Workflow Filter: Comment Status</label>
                <select id="reviewWorkflowCommentStatusFilter">
                  <option value="">all</option>
                  <option value="open">open</option>
                  <option value="resolved">resolved</option>
                </select>
              </div>
              <div>
                <label for="reviewWorkflowStateFilter">Workflow Filter: State</label>
                <select id="reviewWorkflowStateFilter">
                  <option value="">all</option>
                  <option value="pending">pending</option>
                  <option value="overdue">overdue</option>
                </select>
              </div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <div>
                <label for="reviewWorkflowOverdueHoursFilter">Workflow Filter: Overdue After (hours)</label>
                <input id="reviewWorkflowOverdueHoursFilter" type="number" min="1" step="1" value="48" />
              </div>
              <div class="sub" style="align-self:end;">
                Applied when `State=overdue` (also included in export queries).
              </div>
              <div style="align-self:end;">
                <button id="reviewWorkflowClearFiltersBtn" class="ghost">Clear Workflow Filters</button>
              </div>
            </div>
            <div id="reviewWorkflowSummaryLine" class="footer-note mono" style="margin-top:10px;">workflow: timeline=- · findings=- · comments=-</div>
            <div class="row3" style="margin-top:10px;">
              <button id="reviewWorkflowExportJsonBtn" class="ghost">Export Workflow JSON</button>
              <button id="reviewWorkflowExportCsvBtn" class="secondary">Export Workflow CSV</button>
              <div class="sub" style="align-self:center;">Export uses current workflow filters.</div>
            </div>
            <div style="margin-top:10px;">
              <label>Review Workflow Timeline</label>
              <div class="list" id="reviewWorkflowTimelineList"></div>
            </div>
            <div style="margin-top:10px;">
              <pre id="reviewWorkflowJson">{}</pre>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="reviewWorkflowSlaBtn" class="ghost">Load Workflow SLA</button>
              <button id="reviewWorkflowSlaProfileBtn" class="ghost">Load SLA Profile</button>
              <button id="reviewWorkflowSlaRecomputeBtn" class="secondary">Recompute SLA</button>
              <div id="reviewWorkflowSlaSummaryLine" class="footer-note mono" style="align-self:center;">
                sla: overdue=- · breach_rate=- · oldest=-
              </div>
            </div>
            <div class="row4" style="margin-top:10px;">
              <div>
                <label for="reviewWorkflowSlaHighHours">SLA High (h)</label>
                <input id="reviewWorkflowSlaHighHours" type="number" min="1" step="1" value="24" />
              </div>
              <div>
                <label for="reviewWorkflowSlaMediumHours">SLA Medium (h)</label>
                <input id="reviewWorkflowSlaMediumHours" type="number" min="1" step="1" value="72" />
              </div>
              <div>
                <label for="reviewWorkflowSlaLowHours">SLA Low (h)</label>
                <input id="reviewWorkflowSlaLowHours" type="number" min="1" step="1" value="120" />
              </div>
              <div>
                <label for="reviewWorkflowSlaCommentDefaultHours">Comment Default SLA (h)</label>
                <input id="reviewWorkflowSlaCommentDefaultHours" type="number" min="1" step="1" value="72" />
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label for="reviewWorkflowSlaUseSavedProfile">Use Saved Profile</label>
                <select id="reviewWorkflowSlaUseSavedProfile">
                  <option value="true">true</option>
                  <option value="false">false</option>
                </select>
              </div>
            </div>
            <div class="sub" style="margin-top:8px;">SLA hotspots for reviewer triage.</div>
            <div style="margin-top:10px;">
              <label>Top Overdue Items</label>
              <div class="list" id="reviewWorkflowSlaHotspotsList"></div>
            </div>
            <div style="margin-top:10px;">
              <pre id="reviewWorkflowSlaJson">{}</pre>
            </div>
            <div style="margin-top:10px;">
              <div id="reviewWorkflowSlaProfileSummaryLine" class="footer-note mono">profile: source=- · updated=-</div>
            </div>
            <div style="margin-top:10px;">
              <pre id="reviewWorkflowSlaProfileJson">{}</pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>

  <script>
    (() => {
      const $ = (id) => document.getElementById(id);
      const uiStateFields = [
        ["diffSection", "grantflow_demo_diff_section"],
        ["fromVersionId", "grantflow_demo_from_version_id"],
        ["toVersionId", "grantflow_demo_to_version_id"],
        ["criticSectionFilter", "grantflow_demo_critic_section"],
        ["criticSeverityFilter", "grantflow_demo_critic_severity"],
        ["criticFindingStatusFilter", "grantflow_demo_critic_finding_status"],
        ["criticCitationConfidenceFilter", "grantflow_demo_critic_confidence"],
        ["criticBulkTargetStatus", "grantflow_demo_critic_bulk_target_status"],
        ["criticBulkScope", "grantflow_demo_critic_bulk_scope"],
        ["portfolioDonorFilter", "grantflow_demo_portfolio_donor"],
        ["portfolioStatusFilter", "grantflow_demo_portfolio_status"],
        ["portfolioHitlFilter", "grantflow_demo_portfolio_hitl"],
        ["portfolioWarningLevelFilter", "grantflow_demo_portfolio_warning_level"],
        ["portfolioGroundingRiskLevelFilter", "grantflow_demo_portfolio_grounding_risk_level"],
        ["portfolioFindingStatusFilter", "grantflow_demo_portfolio_finding_status"],
        ["portfolioFindingSeverityFilter", "grantflow_demo_portfolio_finding_severity"],
        ["exportGzipEnabled", "grantflow_demo_export_gzip_enabled"],
        ["commentsFilterSection", "grantflow_demo_comments_filter_section"],
        ["commentsFilterStatus", "grantflow_demo_comments_filter_status"],
        ["commentsFilterVersionId", "grantflow_demo_comments_filter_version_id"],
        ["reviewWorkflowEventTypeFilter", "grantflow_demo_review_workflow_event_type"],
        ["reviewWorkflowFindingIdFilter", "grantflow_demo_review_workflow_finding_id"],
        ["reviewWorkflowCommentStatusFilter", "grantflow_demo_review_workflow_comment_status"],
        ["reviewWorkflowStateFilter", "grantflow_demo_review_workflow_state"],
        ["reviewWorkflowOverdueHoursFilter", "grantflow_demo_review_workflow_overdue_hours"],
        ["reviewWorkflowSlaHighHours", "grantflow_demo_review_workflow_sla_high_hours"],
        ["reviewWorkflowSlaMediumHours", "grantflow_demo_review_workflow_sla_medium_hours"],
        ["reviewWorkflowSlaLowHours", "grantflow_demo_review_workflow_sla_low_hours"],
        ["reviewWorkflowSlaCommentDefaultHours", "grantflow_demo_review_workflow_sla_comment_default_hours"],
        ["reviewWorkflowSlaUseSavedProfile", "grantflow_demo_review_workflow_sla_use_saved_profile"],
        ["selectedCommentId", "grantflow_demo_selected_comment_id"],
        ["linkedFindingId", "grantflow_demo_linked_finding_id"],
        ["generatePresetSelect", "grantflow_demo_generate_preset"],
        ["strictPreflight", "grantflow_demo_strict_preflight"],
        ["inputContextJson", "grantflow_demo_input_context_json"],
        ["ingestPresetSelect", "grantflow_demo_ingest_preset"],
        ["ingestDonorId", "grantflow_demo_ingest_donor_id"],
        ["ingestMetadataJson", "grantflow_demo_ingest_metadata_json"],
      ];
      const state = {
        pollTimer: null,
        polling: false,
        lastCritic: null,
        lastCitations: null,
        lastIngestInventory: null,
        ingestChecklistProgress: {},
        zeroReadinessWarningPrefs: {},
      };
      const GENERATE_PRESETS = {
        usaid_gov_ai_kazakhstan: {
          donor_id: "usaid",
          project: "Responsible AI Skills for Civil Service Modernization",
          country: "Kazakhstan",
          llm_mode: true,
          hitl_enabled: true,
          strict_preflight: false,
          input_context: {
            region: "National with pilot cohorts in Astana and Almaty",
            timeframe: "2026-2027 (24 months)",
            problem:
              "Civil servants have uneven practical skills in safe, ethical, and effective AI use for public administration.",
            target_population:
              "Mid-level and senior civil servants in policy, service delivery, and digital transformation units.",
            expected_change:
              "Agencies improve AI readiness, adopt governance guidance, and demonstrate early workflow efficiency gains.",
            key_activities: [
              "Needs assessment and baseline competency mapping",
              "Responsible AI curriculum design for public administration",
              "Cohort-based training and training-of-trainers",
              "Applied labs for policy and service workflows",
              "SOP and governance guidance drafting support",
            ],
          },
        },
        eu_digital_governance_moldova: {
          donor_id: "eu",
          project: "Digital Governance Service Quality and Administrative Capacity",
          country: "Moldova",
          llm_mode: true,
          hitl_enabled: true,
          strict_preflight: false,
          input_context: {
            region: "National and selected municipalities",
            timeframe: "2026-2028 (30 months)",
            problem:
              "Public institutions face uneven digital service management capacity and inconsistent service quality.",
            target_population:
              "Civil servants and municipal service managers in digital transformation and service delivery units.",
            expected_change:
              "Institutions adopt stronger service quality procedures and improve processing efficiency.",
            key_activities: [
              "Institutional workflow assessments",
              "Training on service design and process improvement",
              "Coaching for agency and municipal teams",
              "Support for SOPs and service quality dashboards",
            ],
          },
        },
        worldbank_public_sector_uzbekistan: {
          donor_id: "worldbank",
          project: "Public Sector Performance and Service Delivery Capacity Strengthening",
          country: "Uzbekistan",
          llm_mode: true,
          hitl_enabled: true,
          strict_preflight: false,
          input_context: {
            region: "National ministries and selected subnational administrations",
            timeframe: "2026-2028 (36 months)",
            problem:
              "Public agencies have uneven capabilities in performance management and evidence-based decision-making.",
            target_population:
              "Government managers and civil servants in reform, performance, and service delivery functions.",
            expected_change:
              "Participating institutions adopt stronger performance management practices and improve selected services.",
            key_activities: [
              "Institutional diagnostics and process mapping",
              "Capacity development for performance management and data use",
              "Technical assistance for service improvement plans",
              "Process optimization pilots and adaptive reviews",
            ],
          },
        },
      };
      const INGEST_PRESETS = {
        usaid_gov_ai_kazakhstan: {
          donor_id: "usaid",
          metadata: {
            source_type: "donor_guidance",
            sector: "governance",
            theme: "responsible_ai_public_sector",
            country_focus: "Kazakhstan",
            doc_family: "donor_policy",
          },
          checklist_items: [
            { id: "donor_policy", label: "USAID donor policy / ADS guidance", source_type: "donor_guidance" },
            { id: "responsible_ai_guidance", label: "Responsible AI / digital governance guidance", source_type: "reference_guidance" },
            { id: "country_context", label: "Kazakhstan public administration / digital government context", source_type: "country_context" },
            { id: "competency_framework", label: "Civil service competency / training framework", source_type: "training_framework" },
          ],
          recommended_docs: [
            "USAID ADS / policy guidance relevant to digital transformation, governance, or capacity strengthening",
            "Responsible AI / digital governance guidance approved for your organization",
            "Kazakhstan public administration or digital government policy/context documents",
            "Civil service training standards / competency frameworks (if available)",
          ],
        },
        eu_digital_governance_moldova: {
          donor_id: "eu",
          metadata: {
            source_type: "donor_guidance",
            sector: "governance",
            theme: "digital_service_delivery",
            country_focus: "Moldova",
            doc_family: "donor_results_guidance",
          },
          checklist_items: [
            { id: "donor_results_guidance", label: "EU intervention logic / results framework guidance", source_type: "donor_guidance" },
            { id: "digital_governance_guidance", label: "EU digital governance / service delivery references", source_type: "reference_guidance" },
            { id: "country_context", label: "Moldova digitization policy / service standards", source_type: "country_context" },
            { id: "municipal_process_guidance", label: "Municipal service process / quality guidance", source_type: "implementation_reference" },
          ],
          recommended_docs: [
            "EU intervention logic / results framework guidance relevant to governance and public administration reform",
            "EU digital governance or service delivery reform policy references",
            "Moldova public service digitization strategies / standards",
            "Municipal service quality standards or process management guidance",
          ],
        },
        worldbank_public_sector_uzbekistan: {
          donor_id: "worldbank",
          metadata: {
            source_type: "donor_guidance",
            sector: "public_sector_reform",
            theme: "performance_management_service_delivery",
            country_focus: "Uzbekistan",
            doc_family: "donor_results_guidance",
          },
          checklist_items: [
            { id: "donor_results_guidance", label: "World Bank RF / M&E guidance", source_type: "donor_guidance" },
            { id: "project_reference_docs", label: "World Bank public sector modernization project references", source_type: "reference_guidance" },
            { id: "country_context", label: "Uzbekistan public administration reform context", source_type: "country_context" },
            { id: "agency_process_docs", label: "Agency service standards / process maps", source_type: "implementation_reference" },
          ],
          recommended_docs: [
            "World Bank results framework / M&E guidance relevant to governance or public sector reform",
            "World Bank public sector modernization / service delivery project documents",
            "Uzbekistan public administration reform strategies / performance frameworks",
            "Agency service standards, process maps, or reform guidance used for pilots",
          ],
        },
      };

      const els = {
        apiBase: $("apiBase"),
        apiKey: $("apiKey"),
        jobIdInput: $("jobIdInput"),
        donorId: $("donorId"),
        project: $("project"),
        country: $("country"),
        hitlEnabled: $("hitlEnabled"),
        llmMode: $("llmMode"),
        strictPreflight: $("strictPreflight"),
        webhookUrl: $("webhookUrl"),
        webhookSecret: $("webhookSecret"),
        generatePresetSelect: $("generatePresetSelect"),
        applyPresetBtn: $("applyPresetBtn"),
        clearPresetContextBtn: $("clearPresetContextBtn"),
        inputContextJson: $("inputContextJson"),
        ingestPresetSelect: $("ingestPresetSelect"),
        applyIngestPresetBtn: $("applyIngestPresetBtn"),
        syncIngestDonorBtn: $("syncIngestDonorBtn"),
        ingestDonorId: $("ingestDonorId"),
        ingestFileInput: $("ingestFileInput"),
        ingestMetadataJson: $("ingestMetadataJson"),
        ingestChecklistSummary: $("ingestChecklistSummary"),
        ingestChecklistProgressList: $("ingestChecklistProgressList"),
        syncIngestChecklistServerBtn: $("syncIngestChecklistServerBtn"),
        resetIngestChecklistBtn: $("resetIngestChecklistBtn"),
        ingestPresetGuidanceList: $("ingestPresetGuidanceList"),
        ingestInventoryJson: $("ingestInventoryJson"),
        copyIngestInventoryJsonBtn: $("copyIngestInventoryJsonBtn"),
        downloadIngestInventoryJsonBtn: $("downloadIngestInventoryJsonBtn"),
        downloadIngestInventoryCsvBtn: $("downloadIngestInventoryCsvBtn"),
        ingestResultJson: $("ingestResultJson"),
        ingestBtn: $("ingestBtn"),
        generatePresetReadinessPill: $("generatePresetReadinessPill"),
        generatePresetReadinessText: $("generatePresetReadinessText"),
        generatePresetReadinessHint: $("generatePresetReadinessHint"),
        syncGenerateReadinessBtn: $("syncGenerateReadinessBtn"),
        skipZeroReadinessWarningCheckbox: $("skipZeroReadinessWarningCheckbox"),
        skipZeroReadinessWarningLabel: $("skipZeroReadinessWarningLabel"),
        generatePreflightAlert: $("generatePreflightAlert"),
        generatePreflightAlertTitle: $("generatePreflightAlertTitle"),
        generatePreflightAlertBody: $("generatePreflightAlertBody"),
        diffSection: $("diffSection"),
        fromVersionId: $("fromVersionId"),
        toVersionId: $("toVersionId"),
        hitlFeedback: $("hitlFeedback"),
        checkpointId: $("checkpointId"),
        checkpointStage: $("checkpointStage"),
        statusPill: $("statusPill"),
        statusPillText: $("statusPillText"),
        statusJson: $("statusJson"),
        metricsJson: $("metricsJson"),
        qualityJson: $("qualityJson"),
        qualityAdvisoryBadgeList: $("qualityAdvisoryBadgeList"),
        qualityLlmFindingLabelsList: $("qualityLlmFindingLabelsList"),
        qualityCitationTypeCountsList: $("qualityCitationTypeCountsList"),
        qualityArchitectCitationTypeCountsList: $("qualityArchitectCitationTypeCountsList"),
        qualityReadinessWarningsList: $("qualityReadinessWarningsList"),
        qualityReadinessWarningLevelPill: $("qualityReadinessWarningLevelPill"),
        qualityPreflightMetaLine: $("qualityPreflightMetaLine"),
        portfolioMetricsJson: $("portfolioMetricsJson"),
        portfolioQualityJson: $("portfolioQualityJson"),
        criticJson: $("criticJson"),
        exportPayloadJson: $("exportPayloadJson"),
        diffPre: $("diffPre"),
        versionsList: $("versionsList"),
        citationsList: $("citationsList"),
        eventsList: $("eventsList"),
        criticFlawsList: $("criticFlawsList"),
        criticChecksList: $("criticChecksList"),
        criticContextList: $("criticContextList"),
        criticBulkResultJson: $("criticBulkResultJson"),
        criticAdvisorySummaryList: $("criticAdvisorySummaryList"),
        criticAdvisoryLabelsList: $("criticAdvisoryLabelsList"),
        criticAdvisoryNormalizationList: $("criticAdvisoryNormalizationList"),
        commentsList: $("commentsList"),
        reviewWorkflowTimelineList: $("reviewWorkflowTimelineList"),
        reviewWorkflowSummaryLine: $("reviewWorkflowSummaryLine"),
        reviewWorkflowJson: $("reviewWorkflowJson"),
        reviewWorkflowEventTypeFilter: $("reviewWorkflowEventTypeFilter"),
        reviewWorkflowFindingIdFilter: $("reviewWorkflowFindingIdFilter"),
        reviewWorkflowCommentStatusFilter: $("reviewWorkflowCommentStatusFilter"),
        reviewWorkflowStateFilter: $("reviewWorkflowStateFilter"),
        reviewWorkflowOverdueHoursFilter: $("reviewWorkflowOverdueHoursFilter"),
        reviewWorkflowSlaHighHours: $("reviewWorkflowSlaHighHours"),
        reviewWorkflowSlaMediumHours: $("reviewWorkflowSlaMediumHours"),
        reviewWorkflowSlaLowHours: $("reviewWorkflowSlaLowHours"),
        reviewWorkflowSlaCommentDefaultHours: $("reviewWorkflowSlaCommentDefaultHours"),
        reviewWorkflowSlaUseSavedProfile: $("reviewWorkflowSlaUseSavedProfile"),
        reviewWorkflowClearFiltersBtn: $("reviewWorkflowClearFiltersBtn"),
        reviewWorkflowExportJsonBtn: $("reviewWorkflowExportJsonBtn"),
        reviewWorkflowExportCsvBtn: $("reviewWorkflowExportCsvBtn"),
        reviewWorkflowSlaBtn: $("reviewWorkflowSlaBtn"),
        reviewWorkflowSlaProfileBtn: $("reviewWorkflowSlaProfileBtn"),
        reviewWorkflowSlaRecomputeBtn: $("reviewWorkflowSlaRecomputeBtn"),
        reviewWorkflowSlaSummaryLine: $("reviewWorkflowSlaSummaryLine"),
        reviewWorkflowSlaHotspotsList: $("reviewWorkflowSlaHotspotsList"),
        reviewWorkflowSlaJson: $("reviewWorkflowSlaJson"),
        reviewWorkflowSlaProfileSummaryLine: $("reviewWorkflowSlaProfileSummaryLine"),
        reviewWorkflowSlaProfileJson: $("reviewWorkflowSlaProfileJson"),
        metricsCards: $("metricsCards"),
        qualityCards: $("qualityCards"),
        portfolioMetricsCards: $("portfolioMetricsCards"),
        portfolioQualityCards: $("portfolioQualityCards"),
        portfolioWarningMetaLine: $("portfolioWarningMetaLine"),
        portfolioStatusCountsList: $("portfolioStatusCountsList"),
        portfolioDonorCountsList: $("portfolioDonorCountsList"),
        portfolioMetricsWarningLevelsList: $("portfolioMetricsWarningLevelsList"),
        portfolioMetricsGroundingRiskLevelsList: $("portfolioMetricsGroundingRiskLevelsList"),
        portfolioQualityRiskList: $("portfolioQualityRiskList"),
        portfolioQualityOpenFindingsList: $("portfolioQualityOpenFindingsList"),
        portfolioQualityWarningLevelsList: $("portfolioQualityWarningLevelsList"),
        portfolioQualityGroundingRiskLevelsList: $("portfolioQualityGroundingRiskLevelsList"),
        portfolioQualityFindingStatusList: $("portfolioQualityFindingStatusList"),
        portfolioQualityFindingSeverityList: $("portfolioQualityFindingSeverityList"),
        portfolioQualityGroundingRiskList: $("portfolioQualityGroundingRiskList"),
        portfolioQualityCitationTypeCountsList: $("portfolioQualityCitationTypeCountsList"),
        portfolioQualityArchitectCitationTypeCountsList: $("portfolioQualityArchitectCitationTypeCountsList"),
        portfolioQualityMelCitationTypeCountsList: $("portfolioQualityMelCitationTypeCountsList"),
        portfolioQualityPrioritySignalsList: $("portfolioQualityPrioritySignalsList"),
        portfolioQualityWeightedDonorsList: $("portfolioQualityWeightedDonorsList"),
        portfolioQualityLlmLabelCountsList: $("portfolioQualityLlmLabelCountsList"),
        portfolioQualityTopDonorLlmLabelCountsList: $("portfolioQualityTopDonorLlmLabelCountsList"),
        portfolioQualityTopDonorAdvisoryRejectedReasonsList: $("portfolioQualityTopDonorAdvisoryRejectedReasonsList"),
        portfolioQualityTopDonorAdvisoryAppliedList: $("portfolioQualityTopDonorAdvisoryAppliedList"),
        portfolioQualityFocusedDonorSummaryList: $("portfolioQualityFocusedDonorSummaryList"),
        portfolioQualityFocusedDonorAdvisoryPill: $("portfolioQualityFocusedDonorAdvisoryPill"),
        portfolioQualityFocusedDonorAdvisoryPillText: $("portfolioQualityFocusedDonorAdvisoryPillText"),
        portfolioQualityFocusedDonorLlmLabelCountsList: $("portfolioQualityFocusedDonorLlmLabelCountsList"),
        portfolioQualityFocusedDonorAdvisoryRejectedReasonsList: $("portfolioQualityFocusedDonorAdvisoryRejectedReasonsList"),
        portfolioQualityFocusedDonorAdvisoryAppliedLabelCountsList: $("portfolioQualityFocusedDonorAdvisoryAppliedLabelCountsList"),
        portfolioQualityFocusedDonorAdvisoryRejectedLabelCountsList: $("portfolioQualityFocusedDonorAdvisoryRejectedLabelCountsList"),
        portfolioQualityAdvisoryAppliedList: $("portfolioQualityAdvisoryAppliedList"),
        portfolioQualityAdvisoryRejectedReasonsList: $("portfolioQualityAdvisoryRejectedReasonsList"),
        criticSectionFilter: $("criticSectionFilter"),
        criticSeverityFilter: $("criticSeverityFilter"),
        criticFindingStatusFilter: $("criticFindingStatusFilter"),
        criticCitationConfidenceFilter: $("criticCitationConfidenceFilter"),
        criticBulkTargetStatus: $("criticBulkTargetStatus"),
        criticBulkScope: $("criticBulkScope"),
        portfolioDonorFilter: $("portfolioDonorFilter"),
        portfolioStatusFilter: $("portfolioStatusFilter"),
        portfolioHitlFilter: $("portfolioHitlFilter"),
        portfolioWarningLevelFilter: $("portfolioWarningLevelFilter"),
        portfolioGroundingRiskLevelFilter: $("portfolioGroundingRiskLevelFilter"),
        portfolioFindingStatusFilter: $("portfolioFindingStatusFilter"),
        portfolioFindingSeverityFilter: $("portfolioFindingSeverityFilter"),
        exportGzipEnabled: $("exportGzipEnabled"),
        commentsFilterSection: $("commentsFilterSection"),
        commentsFilterStatus: $("commentsFilterStatus"),
        commentsFilterVersionId: $("commentsFilterVersionId"),
        commentSection: $("commentSection"),
        commentAuthor: $("commentAuthor"),
        commentVersionId: $("commentVersionId"),
        linkedFindingId: $("linkedFindingId"),
        commentMessage: $("commentMessage"),
        selectedCommentId: $("selectedCommentId"),
        generateBtn: $("generateBtn"),
        refreshAllBtn: $("refreshAllBtn"),
        pollToggleBtn: $("pollToggleBtn"),
        clearFiltersBtn: $("clearFiltersBtn"),
        approveBtn: $("approveBtn"),
        rejectBtn: $("rejectBtn"),
        resumeBtn: $("resumeBtn"),
        cancelBtn: $("cancelBtn"),
        versionsBtn: $("versionsBtn"),
        diffBtn: $("diffBtn"),
        citationsBtn: $("citationsBtn"),
        exportPayloadBtn: $("exportPayloadBtn"),
        copyExportPayloadBtn: $("copyExportPayloadBtn"),
        exportZipFromPayloadBtn: $("exportZipFromPayloadBtn"),
        eventsBtn: $("eventsBtn"),
        criticBtn: $("criticBtn"),
        criticBulkApplyBtn: $("criticBulkApplyBtn"),
        criticBulkClearFiltersBtn: $("criticBulkClearFiltersBtn"),
        qualityBtn: $("qualityBtn"),
        portfolioBtn: $("portfolioBtn"),
        portfolioClearBtn: $("portfolioClearBtn"),
        copyPortfolioMetricsJsonBtn: $("copyPortfolioMetricsJsonBtn"),
        downloadPortfolioMetricsJsonBtn: $("downloadPortfolioMetricsJsonBtn"),
        downloadPortfolioMetricsCsvBtn: $("downloadPortfolioMetricsCsvBtn"),
        copyPortfolioQualityJsonBtn: $("copyPortfolioQualityJsonBtn"),
        downloadPortfolioQualityJsonBtn: $("downloadPortfolioQualityJsonBtn"),
        downloadPortfolioQualityCsvBtn: $("downloadPortfolioQualityCsvBtn"),
        exportInventoryJsonBtn: $("exportInventoryJsonBtn"),
        exportInventoryCsvBtn: $("exportInventoryCsvBtn"),
        exportPortfolioMetricsJsonBtn: $("exportPortfolioMetricsJsonBtn"),
        exportPortfolioMetricsCsvBtn: $("exportPortfolioMetricsCsvBtn"),
        exportPortfolioQualityJsonBtn: $("exportPortfolioQualityJsonBtn"),
        exportPortfolioQualityCsvBtn: $("exportPortfolioQualityCsvBtn"),
        commentsBtn: $("commentsBtn"),
        reviewWorkflowBtn: $("reviewWorkflowBtn"),
        addCommentBtn: $("addCommentBtn"),
        resolveCommentBtn: $("resolveCommentBtn"),
        reopenCommentBtn: $("reopenCommentBtn"),
        clearLinkedFindingBtn: $("clearLinkedFindingBtn"),
        openPendingBtn: $("openPendingBtn"),
      };

      function initDefaults() {
        els.apiBase.value = localStorage.getItem("grantflow_demo_api_base") || window.location.origin;
        els.apiKey.value = localStorage.getItem("grantflow_demo_api_key") || "";
        els.jobIdInput.value = localStorage.getItem("grantflow_demo_job_id") || "";
        state.ingestChecklistProgress = loadIngestChecklistProgress();
        state.zeroReadinessWarningPrefs = loadZeroReadinessWarningPrefs();
        restoreUiState();
        if (!String(els.ingestDonorId.value || "").trim()) {
          els.ingestDonorId.value = String(els.donorId.value || "usaid");
        }
        renderIngestPresetGuidance();
        renderIngestChecklistProgress();
        renderGeneratePresetReadiness();
        renderZeroReadinessWarningPreference();
        renderGeneratePreflightAlert(null);
        if (String(els.ingestPresetSelect.value || "").trim()) {
          syncIngestChecklistFromServer().catch(() => {});
        }
      }

      function persistBasics() {
        localStorage.setItem("grantflow_demo_api_base", els.apiBase.value.trim());
        localStorage.setItem("grantflow_demo_api_key", els.apiKey.value.trim());
        localStorage.setItem("grantflow_demo_job_id", els.jobIdInput.value.trim());
      }

      function restoreUiState() {
        for (const [elKey, storageKey] of uiStateFields) {
          const el = els[elKey];
          if (!el) continue;
          const value = localStorage.getItem(storageKey);
          if (value != null) el.value = value;
        }
      }

      function persistUiState() {
        for (const [elKey, storageKey] of uiStateFields) {
          const el = els[elKey];
          if (!el) continue;
          localStorage.setItem(storageKey, String(el.value || ""));
        }
      }

      function clearPortfolioFilters() {
        els.portfolioDonorFilter.value = "";
        els.portfolioStatusFilter.value = "";
        els.portfolioHitlFilter.value = "";
        els.portfolioWarningLevelFilter.value = "";
        els.portfolioGroundingRiskLevelFilter.value = "";
        els.portfolioFindingStatusFilter.value = "";
        els.portfolioFindingSeverityFilter.value = "";
        persistUiState();
      }

      function clearCriticFilters() {
        els.criticSectionFilter.value = "";
        els.criticSeverityFilter.value = "";
        els.criticFindingStatusFilter.value = "";
        persistUiState();
      }

      function clearReviewWorkflowFilters() {
        els.reviewWorkflowEventTypeFilter.value = "";
        els.reviewWorkflowFindingIdFilter.value = "";
        els.reviewWorkflowCommentStatusFilter.value = "";
        els.reviewWorkflowStateFilter.value = "";
        els.reviewWorkflowOverdueHoursFilter.value = "48";
        els.reviewWorkflowSlaHighHours.value = "24";
        els.reviewWorkflowSlaMediumHours.value = "72";
        els.reviewWorkflowSlaLowHours.value = "120";
        els.reviewWorkflowSlaCommentDefaultHours.value = "72";
        els.reviewWorkflowSlaUseSavedProfile.value = "true";
        persistUiState();
      }

      function exportGzipEnabled() {
        return String(els.exportGzipEnabled.value || "").toLowerCase() === "true";
      }

      async function clearDemoFilters() {
        for (const [elKey] of uiStateFields) {
          const el = els[elKey];
          if (!el) continue;
          el.value = "";
        }
        persistUiState();
        if (state.lastCritic) renderCriticLists(state.lastCritic);
        if (state.lastCitations) renderCriticContextCitations();
        renderGeneratePreflightAlert(null);
        renderGeneratePresetReadiness();
        await Promise.allSettled([refreshPortfolioBundle(), refreshComments(), refreshReviewWorkflow(), refreshDiff()]);
      }

      function clearLinkedFindingSelection() {
        els.linkedFindingId.value = "";
        persistUiState();
      }

      function loadIngestChecklistProgress() {
        const raw = localStorage.getItem("grantflow_demo_ingest_checklist_progress");
        if (!raw) return {};
        try {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
        } catch (_err) {
          // ignore malformed local storage
        }
        return {};
      }

      function loadZeroReadinessWarningPrefs() {
        const raw = localStorage.getItem("grantflow_demo_zero_readiness_warning_prefs");
        if (!raw) return {};
        try {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
        } catch (_err) {
          // ignore malformed local storage
        }
        return {};
      }

      function persistIngestChecklistProgress() {
        localStorage.setItem(
          "grantflow_demo_ingest_checklist_progress",
          JSON.stringify(state.ingestChecklistProgress || {})
        );
      }

      function persistZeroReadinessWarningPrefs() {
        localStorage.setItem(
          "grantflow_demo_zero_readiness_warning_prefs",
          JSON.stringify(state.zeroReadinessWarningPrefs || {})
        );
      }

      function getIngestChecklistItemsForSelectedPreset() {
        const key = String(els.ingestPresetSelect.value || "").trim();
        const preset = key ? INGEST_PRESETS[key] : null;
        const items = Array.isArray(preset?.checklist_items) ? preset.checklist_items : [];
        return { presetKey: key, preset, items };
      }

      function getGeneratePresetReadinessStats() {
        const presetKey = String(els.generatePresetSelect.value || "").trim();
        if (!presetKey) return { presetKey: "", total: 0, completed: 0, missingIds: [], missingLabels: [] };
        const preset = INGEST_PRESETS[presetKey];
        const items = Array.isArray(preset?.checklist_items) ? preset.checklist_items : [];
        if (!items.length) return { presetKey, total: 0, completed: 0, missingIds: [], missingLabels: [] };

        const progressRoot = state.ingestChecklistProgress && typeof state.ingestChecklistProgress === "object"
          ? state.ingestChecklistProgress
          : {};
        const presetProgress =
          progressRoot[presetKey] && typeof progressRoot[presetKey] === "object" ? progressRoot[presetKey] : {};
        let completed = 0;
        const missingIds = [];
        const missingLabels = [];
        for (const item of items) {
          const itemId = String(item?.id || "").trim();
          const row = itemId && presetProgress[itemId] && typeof presetProgress[itemId] === "object"
            ? presetProgress[itemId]
            : null;
          if (row && row.completed) {
            completed += 1;
          } else {
            if (itemId) missingIds.push(itemId);
            missingLabels.push(String(item?.label || itemId || "Checklist item"));
          }
        }
        return { presetKey, total: items.length, completed, missingIds, missingLabels };
      }

      function isZeroReadinessWarningSkippedForPreset(presetKey) {
        const key = String(presetKey || "").trim();
        if (!key) return false;
        const prefs = state.zeroReadinessWarningPrefs && typeof state.zeroReadinessWarningPrefs === "object"
          ? state.zeroReadinessWarningPrefs
          : {};
        return Boolean(prefs[key]);
      }

      function renderZeroReadinessWarningPreference() {
        if (!els.skipZeroReadinessWarningCheckbox || !els.skipZeroReadinessWarningLabel) return;
        const presetKey = String(els.generatePresetSelect.value || "").trim();
        if (!presetKey) {
          els.skipZeroReadinessWarningCheckbox.checked = false;
          els.skipZeroReadinessWarningCheckbox.disabled = true;
          els.skipZeroReadinessWarningLabel.textContent = "Don't ask again for this preset";
          return;
        }
        els.skipZeroReadinessWarningCheckbox.disabled = false;
        els.skipZeroReadinessWarningCheckbox.checked = isZeroReadinessWarningSkippedForPreset(presetKey);
        els.skipZeroReadinessWarningLabel.textContent = "Don't ask again for this preset";
      }

      function renderGeneratePresetReadiness() {
        if (!els.generatePresetReadinessPill || !els.generatePresetReadinessText) return;
        const { presetKey, total, completed, missingIds, missingLabels } = getGeneratePresetReadinessStats();
        if (!presetKey) {
          els.generatePresetReadinessPill.className = "pill";
          els.generatePresetReadinessText.textContent = "No preset selected";
          els.generatePresetReadinessPill.title = "Select a preset to compute RAG readiness";
          if (els.generatePresetReadinessHint) {
            els.generatePresetReadinessHint.textContent = "Select a preset to see missing recommended document families.";
          }
          renderZeroReadinessWarningPreference();
          return;
        }
        if (!total) {
          els.generatePresetReadinessPill.className = "pill";
          els.generatePresetReadinessText.textContent = "No checklist for preset";
          els.generatePresetReadinessPill.title = "No ingest checklist is configured for this preset";
          if (els.generatePresetReadinessHint) {
            els.generatePresetReadinessHint.textContent = "This preset does not define recommended doc_family coverage.";
          }
          renderZeroReadinessWarningPreference();
          return;
        }
        let cls = "pill";
        if (total && completed === total) cls += " status-done";
        else if (completed > 0) cls += " status-running";
        els.generatePresetReadinessPill.className = cls;
        els.generatePresetReadinessText.textContent = `${completed}/${total} doc families loaded`;
        if (missingIds.length) {
          els.generatePresetReadinessPill.title = `Missing doc_family: ${missingIds.join(", ")}`;
          if (els.generatePresetReadinessHint) {
            const preview = missingIds.slice(0, 3).join(", ");
            const suffix = missingIds.length > 3 ? ` +${missingIds.length - 3} more` : "";
            els.generatePresetReadinessHint.textContent = `Missing: ${preview}${suffix}`;
          }
        } else {
          els.generatePresetReadinessPill.title = "All recommended doc_family checklist items are covered";
          if (els.generatePresetReadinessHint) {
            els.generatePresetReadinessHint.textContent = "All recommended doc families loaded.";
          }
        }
        renderZeroReadinessWarningPreference();
      }

      function renderIngestChecklistProgress() {
        const { presetKey, items } = getIngestChecklistItemsForSelectedPreset();
        els.ingestChecklistProgressList.innerHTML = "";
        const progressRoot = state.ingestChecklistProgress && typeof state.ingestChecklistProgress === "object"
          ? state.ingestChecklistProgress
          : {};
        const presetProgress = presetKey && progressRoot[presetKey] && typeof progressRoot[presetKey] === "object"
          ? progressRoot[presetKey]
          : {};

        if (!presetKey || !items.length) {
          els.ingestChecklistSummary.className = "pill";
          els.ingestChecklistSummary.innerHTML = `<span class="dot"></span><span>0/0 complete</span>`;
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `<div class="title">No checklist active</div><div class="sub">Select an ingest preset to track recommended document coverage.</div>`;
          els.ingestChecklistProgressList.appendChild(div);
          renderGeneratePresetReadiness();
          return;
        }

        let completed = 0;
        for (const item of items) {
          const itemId = String(item?.id || "").trim();
          const row = itemId && presetProgress[itemId] && typeof presetProgress[itemId] === "object"
            ? presetProgress[itemId]
            : null;
          const done = Boolean(row && row.completed);
          if (done) completed += 1;

          const div = document.createElement("div");
          div.className = `item${done ? " severity-low" : ""}`;
          const filename = row && row.filename ? ` · ${String(row.filename)}` : "";
          const ts = row && row.ts ? ` · ${String(row.ts)}` : "";
          div.innerHTML = `
            <div class="title">${done ? "✓" : "○"} ${escapeHtml(String(item?.label || itemId || "Checklist item"))}</div>
            <div class="sub mono">doc_family=${escapeHtml(itemId || "-")}${filename}</div>
            <div class="sub">${done ? "Uploaded and matched via metadata_json.doc_family" : "Pending"}${done ? ts : ""}</div>
          `;
          els.ingestChecklistProgressList.appendChild(div);
        }

        const total = items.length;
        const ratio = total ? completed / total : 0;
        let cls = "pill";
        if (total && completed === total) cls += " status-done";
        else if (completed > 0 || ratio > 0) cls += " status-running";
        els.ingestChecklistSummary.className = cls;
        els.ingestChecklistSummary.innerHTML = `<span class="dot"></span><span>${completed}/${total} complete</span>`;
        renderGeneratePresetReadiness();
      }

      function resetIngestChecklistProgressForCurrentPreset() {
        const { presetKey } = getIngestChecklistItemsForSelectedPreset();
        if (!presetKey) return;
        if (state.ingestChecklistProgress && typeof state.ingestChecklistProgress === "object") {
          delete state.ingestChecklistProgress[presetKey];
        }
        persistIngestChecklistProgress();
        renderIngestChecklistProgress();
      }

      async function syncIngestChecklistFromServer() {
        const { presetKey, preset, items } = getIngestChecklistItemsForSelectedPreset();
        if (!presetKey || !preset || !items.length) {
          renderIngestChecklistProgress();
          return null;
        }
        const donorId = String(els.ingestDonorId.value || preset.donor_id || "").trim();
        if (!donorId) throw new Error("Missing donor_id for ingest checklist sync");
        const query = new URLSearchParams({ donor_id: donorId });
        const body = await apiFetch(`/ingest/inventory?${query.toString()}`);
        state.lastIngestInventory = body;
        if (els.ingestInventoryJson) setJson(els.ingestInventoryJson, body);
        const familyRows = Array.isArray(body?.doc_families) ? body.doc_families : [];

        if (!state.ingestChecklistProgress || typeof state.ingestChecklistProgress !== "object") {
          state.ingestChecklistProgress = {};
        }
        const bucket =
          state.ingestChecklistProgress[presetKey] && typeof state.ingestChecklistProgress[presetKey] === "object"
            ? state.ingestChecklistProgress[presetKey]
            : {};
        state.ingestChecklistProgress[presetKey] = bucket;

        const allowedIds = new Set(items.map((it) => String(it?.id || "").trim()).filter(Boolean));
        for (const rec of familyRows) {
          if (!rec || typeof rec !== "object") continue;
          const recDonor = String(rec.donor_id || "").trim().toLowerCase();
          if (recDonor && recDonor !== donorId.toLowerCase()) continue;
          const docFamily = String(rec.doc_family || "").trim();
          if (!docFamily || !allowedIds.has(docFamily)) continue;
          bucket[docFamily] = {
            completed: true,
            filename: String(rec.latest_filename || bucket[docFamily]?.filename || ""),
            ts: String(rec.latest_ts || bucket[docFamily]?.ts || ""),
            donor_id: donorId,
            source: "server",
          };
        }
        persistIngestChecklistProgress();
        renderIngestChecklistProgress();
        return body;
      }

      function setGenerateContextJson(value) {
        if (value && typeof value === "object" && !Array.isArray(value)) {
          els.inputContextJson.value = JSON.stringify(value, null, 2);
        } else {
          els.inputContextJson.value = "";
        }
      }

      function applyGeneratePreset() {
        const key = String(els.generatePresetSelect.value || "").trim();
        if (!key) return;
        const preset = GENERATE_PRESETS[key];
        if (!preset) return;
        els.donorId.value = String(preset.donor_id || "");
        els.project.value = String(preset.project || "");
        els.country.value = String(preset.country || "");
        els.llmMode.value = preset.llm_mode ? "true" : "false";
        els.hitlEnabled.value = preset.hitl_enabled ? "true" : "false";
        els.strictPreflight.value = preset.strict_preflight ? "true" : "false";
        const extra = { ...(preset.input_context || {}) };
        delete extra.project;
        delete extra.country;
        setGenerateContextJson(extra);
        if (INGEST_PRESETS[key]) {
          els.ingestPresetSelect.value = key;
          applyIngestPreset();
        }
        persistUiState();
        renderGeneratePresetReadiness();
      }

      function clearGeneratePresetContext() {
        els.inputContextJson.value = "";
        persistUiState();
      }

      function renderIngestPresetGuidance() {
        const key = String(els.ingestPresetSelect.value || "").trim();
        const preset = key ? INGEST_PRESETS[key] : null;
        els.ingestPresetGuidanceList.innerHTML = "";
        if (!preset) {
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `<div class="title">No ingest preset selected</div><div class="sub">Choose a preset to see recommended donor/context PDFs to upload before generation.</div>`;
          els.ingestPresetGuidanceList.appendChild(div);
          return;
        }
        const docs = Array.isArray(preset.recommended_docs) ? preset.recommended_docs : [];
        const checklistItems = Array.isArray(preset.checklist_items) ? preset.checklist_items : [];
        docs.forEach((doc, idx) => {
          const checklist = checklistItems[idx] || {};
          const docFamily = checklist.id ? ` · doc_family=${String(checklist.id)}` : "";
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `<div class="title">Recommended upload ${idx + 1}</div><div class="sub">${escapeHtml(String(doc || ""))}</div><div class="sub mono">${escapeHtml(docFamily.replace(/^ · /, ""))}</div>`;
          els.ingestPresetGuidanceList.appendChild(div);
        });
      }

      function applyIngestPreset() {
        const key = String(els.ingestPresetSelect.value || "").trim();
        if (!key) {
          renderIngestPresetGuidance();
          return;
        }
        const preset = INGEST_PRESETS[key];
        if (!preset) {
          renderIngestPresetGuidance();
          return;
        }
        els.ingestDonorId.value = String(preset.donor_id || "");
        if (preset.metadata && typeof preset.metadata === "object" && !Array.isArray(preset.metadata)) {
          els.ingestMetadataJson.value = JSON.stringify(preset.metadata, null, 2);
        }
        persistUiState();
        renderIngestPresetGuidance();
        renderIngestChecklistProgress();
        syncIngestChecklistFromServer().catch(() => {});
      }

      function syncIngestDonorFromGenerate() {
        els.ingestDonorId.value = String(els.donorId.value || "").trim();
        persistUiState();
        syncIngestChecklistFromServer().catch(() => {});
      }

      async function syncGeneratePresetReadinessNow() {
        const generatePresetKey = String(els.generatePresetSelect.value || "").trim();
        if (!generatePresetKey) throw new Error("Select a Generate Preset first");
        if (INGEST_PRESETS[generatePresetKey]) {
          els.ingestPresetSelect.value = generatePresetKey;
          renderIngestPresetGuidance();
        }
        if (!String(els.ingestDonorId.value || "").trim()) {
          els.ingestDonorId.value = String(els.donorId.value || "").trim();
        }
        persistUiState();
        return syncIngestChecklistFromServer();
      }

      async function ingestPdfUpload() {
        const donorId = String(els.ingestDonorId.value || "").trim();
        if (!donorId) throw new Error("Missing ingest donor_id");
        const file = (els.ingestFileInput.files && els.ingestFileInput.files[0]) || null;
        if (!file) throw new Error("Select a PDF file first");
        const filename = String(file.name || "").toLowerCase();
        if (!filename.endsWith(".pdf")) throw new Error("Only PDF files are supported");
        let parsedMetadata = null;

        const form = new FormData();
        form.append("donor_id", donorId);
        form.append("file", file);

        const metadataText = String(els.ingestMetadataJson.value || "").trim();
        if (metadataText) {
          let parsed;
          try {
            parsed = JSON.parse(metadataText);
          } catch (err) {
            throw new Error(`Invalid Ingest Metadata JSON: ${err instanceof Error ? err.message : String(err)}`);
          }
          if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            throw new Error("Ingest Metadata JSON must be a JSON object");
          }
          parsedMetadata = parsed;
          form.append("metadata_json", JSON.stringify(parsed));
        }

        persistBasics();
        persistUiState();
        const res = await fetch(`${apiBase()}/ingest`, {
          method: "POST",
          headers: headers(),
          body: form,
        });
        const ct = res.headers.get("content-type") || "";
        const body = ct.includes("application/json") ? await res.json() : await res.text();
        if (!res.ok) {
          throw new Error(typeof body === "string" ? body : JSON.stringify(body, null, 2));
        }
        const { presetKey, preset } = getIngestChecklistItemsForSelectedPreset();
        const uploadedDocFamily = String(parsedMetadata?.doc_family || "").trim();
        if (
          presetKey &&
          preset &&
          donorId.toLowerCase() === String(preset.donor_id || "").toLowerCase() &&
          uploadedDocFamily
        ) {
          if (!state.ingestChecklistProgress || typeof state.ingestChecklistProgress !== "object") {
            state.ingestChecklistProgress = {};
          }
          if (!state.ingestChecklistProgress[presetKey] || typeof state.ingestChecklistProgress[presetKey] !== "object") {
            state.ingestChecklistProgress[presetKey] = {};
          }
          state.ingestChecklistProgress[presetKey][uploadedDocFamily] = {
            completed: true,
            filename: file.name || "",
            ts: new Date().toISOString(),
            donor_id: donorId,
          };
          persistIngestChecklistProgress();
          renderIngestChecklistProgress();
        }
        setJson(els.ingestResultJson, body);
        syncIngestChecklistFromServer().catch(() => {});
        return body;
      }

      function apiBase() {
        return (els.apiBase.value.trim() || window.location.origin).replace(/\\/$/, "");
      }

      function currentJobId() {
        return els.jobIdInput.value.trim();
      }

      function headers(extra = {}) {
        const h = { ...extra };
        const apiKey = els.apiKey.value.trim();
        if (apiKey) h["X-API-Key"] = apiKey;
        return h;
      }

      async function apiFetch(path, opts = {}) {
        persistBasics();
        const url = `${apiBase()}${path}`;
        const res = await fetch(url, {
          ...opts,
          headers: { ...(opts.headers || {}), ...headers() },
        });
        const ct = res.headers.get("content-type") || "";
        let body;
        if (ct.includes("application/json")) body = await res.json();
        else body = await res.text();
        if (!res.ok) {
          throw new Error(typeof body === "string" ? body : JSON.stringify(body, null, 2));
        }
        return body;
      }

      function setStatusPill(status) {
        const safe = (status || "unknown").toString();
        els.statusPill.className = `pill status-${safe}`;
        els.statusPillText.textContent = safe;
      }

      function setJson(el, value) {
        el.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
        el.classList.remove("blink-in");
        void el.offsetWidth;
        el.classList.add("blink-in");
      }

      function fmtSec(v) {
        if (typeof v !== "number") return "-";
        if (v < 60) return `${v.toFixed(1)}s`;
        const m = Math.floor(v / 60);
        const s = Math.round(v % 60);
        return `${m}m ${s}s`;
      }

      function computeArchitectThresholdHitRate(citations) {
        if (!Array.isArray(citations)) return null;
        let considered = 0;
        let hits = 0;
        for (const c of citations) {
          if (!c || String(c.stage || "") !== "architect") continue;
          const thresholdRaw = c.confidence_threshold;
          const confRaw = c.citation_confidence;
          const threshold = thresholdRaw == null ? null : Number(thresholdRaw);
          const conf = confRaw == null ? null : Number(confRaw);
          if (threshold == null || Number.isNaN(threshold)) continue;
          considered += 1;
          if (conf != null && !Number.isNaN(conf) && conf >= threshold) hits += 1;
        }
        if (!considered) return null;
        return { hits, considered, rate: hits / considered };
      }

      function renderMetricsCards(metrics) {
        const values = [
          fmtSec(metrics.time_to_first_draft_seconds),
          fmtSec(metrics.time_to_terminal_seconds),
          fmtSec(metrics.time_in_pending_hitl_seconds),
          String(metrics.pause_count ?? "-"),
          String(metrics.resume_count ?? "-"),
          String(metrics.terminal_status ?? metrics.status ?? "-"),
        ];
        [...els.metricsCards.querySelectorAll(".kpi .value")].forEach((node, i) => {
          node.textContent = values[i] ?? "-";
        });
      }

      function renderQualityAdvisoryBadge(advisoryDiagnostics) {
        if (!els.qualityAdvisoryBadgeList) return;
        const applies = advisoryDiagnostics && advisoryDiagnostics.advisory_applies === true;
        const rejectedReason = advisoryDiagnostics && advisoryDiagnostics.advisory_rejected_reason
          ? String(advisoryDiagnostics.advisory_rejected_reason)
          : "";
        const labelCounts =
          advisoryDiagnostics &&
          advisoryDiagnostics.candidate_label_counts &&
          typeof advisoryDiagnostics.candidate_label_counts === "object"
            ? advisoryDiagnostics.candidate_label_counts
            : {};
        const labelCountTotal = Object.values(labelCounts).reduce((acc, value) => acc + Number(value || 0), 0);
        const thrHit = advisoryDiagnostics && typeof advisoryDiagnostics.architect_threshold_hit_rate === "number"
          ? `thr_hit=${Number(advisoryDiagnostics.architect_threshold_hit_rate).toFixed(3)}`
          : null;
        const ratio = advisoryDiagnostics && typeof advisoryDiagnostics.architect_rag_low_ratio === "number"
          ? `arch_rag_low_ratio=${Number(advisoryDiagnostics.architect_rag_low_ratio).toFixed(3)}`
          : null;
        const rows = advisoryDiagnostics
          ? [
              `applies: ${applies ? "yes" : "no"}`,
              `candidates: ${labelCountTotal}`,
              thrHit,
              ratio,
              !applies && rejectedReason ? `reason: ${rejectedReason}` : null,
            ].filter(Boolean)
          : ["No LLM advisory diagnostics."];
        els.qualityAdvisoryBadgeList.innerHTML = "";
        for (let i = 0; i < rows.length; i += 1) {
          const row = rows[i];
          const div = document.createElement("div");
          div.className = "item";
          if (i === 0 && advisoryDiagnostics) {
            div.style.borderLeft = applies ? "4px solid #1f8f6b" : "4px solid #cc7a00";
          } else if (String(row).startsWith("reason:")) {
            div.style.borderLeft = "4px solid #cc7a00";
          }
          div.innerHTML = `<div class="sub mono">${escapeHtml(String(row))}</div>`;
          els.qualityAdvisoryBadgeList.appendChild(div);
        }
      }

      function renderQualityCards(summary) {
        const critic = summary?.critic || {};
        const citations = summary?.citations || {};
        const readiness = summary?.readiness || {};
        const preflight = summary?.preflight || {};
        renderGeneratePreflightAlert(preflight);
        const advisoryDiagnostics =
          critic && typeof critic.llm_advisory_diagnostics === "object" ? critic.llm_advisory_diagnostics : null;
        const strictPreflightValue =
          typeof summary?.strict_preflight === "boolean" ? String(summary.strict_preflight) : "-";
        const preflightRiskLevel = typeof preflight?.risk_level === "string" ? String(preflight.risk_level) : "-";
        const preflightWarningCount = Number(preflight?.warning_count ?? 0);
        const preflightRiskValue =
          preflightRiskLevel === "-"
            ? "-"
            : `${preflightRiskLevel}${preflightWarningCount > 0 ? ` (${preflightWarningCount})` : ""}`;
        const values = [
          typeof summary?.quality_score === "number" ? Number(summary.quality_score).toFixed(2) : "-",
          typeof summary?.critic_score === "number" ? Number(summary.critic_score).toFixed(2) : "-",
          String(critic.fatal_flaw_count ?? "-"),
          String(critic.open_finding_count ?? "-"),
          typeof citations.citation_confidence_avg === "number" ? Number(citations.citation_confidence_avg).toFixed(2) : "-",
          typeof citations.architect_threshold_hit_rate === "number"
            ? `${(Number(citations.architect_threshold_hit_rate) * 100).toFixed(1)}%`
            : "-",
          typeof citations.architect_claim_support_rate === "number"
            ? `${(Number(citations.architect_claim_support_rate) * 100).toFixed(1)}%`
            : "-",
          typeof citations.architect_fallback_namespace_citation_rate === "number"
            ? `${(Number(citations.architect_fallback_namespace_citation_rate) * 100).toFixed(1)}%`
            : "-",
          preflightRiskValue,
          strictPreflightValue,
        ];
        const qualityValueNodes = [...els.qualityCards.querySelectorAll(".kpi .value")];
        qualityValueNodes.forEach((node, i) => {
          node.textContent = values[i] ?? "-";
        });
        const claimSupportNode = qualityValueNodes[6];
        if (claimSupportNode) {
          const claimSupportRate = Number(citations?.architect_claim_support_rate ?? NaN);
          claimSupportNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (Number.isFinite(claimSupportRate)) {
            if (claimSupportRate < 0.5) claimSupportNode.classList.add("risk-high");
            else if (claimSupportRate < 0.7) claimSupportNode.classList.add("risk-medium");
            else claimSupportNode.classList.add("risk-low");
          } else {
            claimSupportNode.classList.add("risk-none");
          }
          const supportCount = Number(citations?.architect_claim_support_citation_count ?? 0);
          const architectCount = Number(citations?.architect_citation_count ?? 0);
          claimSupportNode.title =
            architectCount > 0
              ? `${supportCount}/${architectCount} architect claim-support citations`
              : "No architect citations";
        }
        const architectFallbackNode = qualityValueNodes[7];
        if (architectFallbackNode) {
          const fallbackRate = Number(citations?.architect_fallback_namespace_citation_rate ?? NaN);
          architectFallbackNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (Number.isFinite(fallbackRate)) {
            if (fallbackRate >= 0.8) architectFallbackNode.classList.add("risk-high");
            else if (fallbackRate >= 0.5) architectFallbackNode.classList.add("risk-medium");
            else architectFallbackNode.classList.add("risk-low");
          } else {
            architectFallbackNode.classList.add("risk-none");
          }
          const fallbackCount = Number(citations?.architect_fallback_namespace_citation_count ?? 0);
          const architectCount = Number(citations?.architect_citation_count ?? 0);
          architectFallbackNode.title =
            architectCount > 0
              ? `${fallbackCount}/${architectCount} architect fallback citations`
              : "No architect citations";
        }
        const preflightRiskNode = qualityValueNodes[8];
        if (preflightRiskNode) {
          const level = String(preflightRiskLevel || "").toLowerCase();
          preflightRiskNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (level === "high" || level === "medium" || level === "low" || level === "none") {
            preflightRiskNode.classList.add(`risk-${level}`);
          }
          const coverageRateLabel =
            typeof preflight?.coverage_rate === "number"
              ? `${(Number(preflight.coverage_rate) * 100).toFixed(1)}%`
              : "-";
          const warningCountLabel =
            typeof preflight?.warning_count === "number" ? String(preflight.warning_count) : "-";
          const groundingRiskLabel = String(
            preflight?.grounding_risk_level || preflight?.grounding_policy?.risk_level || "-"
          );
          const groundingPolicyMode = String(preflight?.grounding_policy?.mode || "-");
          const groundingPolicyBlocking = Boolean(preflight?.grounding_policy?.blocking);
          preflightRiskNode.title =
            preflightRiskLevel === "-"
              ? "No preflight summary in this job"
              : `warning_count=${warningCountLabel} · coverage_rate=${coverageRateLabel} · grounding=${groundingRiskLabel} · policy=${groundingPolicyMode} · policy_blocking=${groundingPolicyBlocking}`;
          if (els.qualityPreflightMetaLine) {
            els.qualityPreflightMetaLine.textContent =
              preflightRiskLevel === "-"
                ? "warning_count=- · coverage_rate=-"
                : `warning_count=${warningCountLabel} · coverage_rate=${coverageRateLabel} · grounding=${groundingRiskLabel}`;
          }
        }
        renderKeyValueList(
          els.qualityCitationTypeCountsList,
          citations.citation_type_counts,
          "No citation type breakdown for this job.",
          8
        );
        renderKeyValueList(
          els.qualityArchitectCitationTypeCountsList,
          citations.architect_citation_type_counts,
          "No architect citation type breakdown for this job.",
          8
        );
        renderQualityAdvisoryBadge(advisoryDiagnostics);
        renderKeyValueList(
          els.qualityLlmFindingLabelsList,
          critic.llm_finding_label_counts,
          "No LLM finding labels in this job.",
          8
        );
        renderQualityReadinessWarnings(readiness);
      }

      function renderQualityReadinessWarnings(readiness) {
        if (!els.qualityReadinessWarningsList) return;
        const warnings = Array.isArray(readiness?.warnings) ? readiness.warnings : [];
        const level = String(readiness?.warning_level || "none").toLowerCase();
        const warningCount = Number(readiness?.warning_count || warnings.length || 0);
        els.qualityReadinessWarningsList.innerHTML = "";
        if (els.qualityReadinessWarningLevelPill) {
          const pill = els.qualityReadinessWarningLevelPill;
          const normalizedLevel = ["high", "medium", "low", "none"].includes(level) ? level : "none";
          pill.className = `pill readiness-level-${normalizedLevel}`;
          const text = pill.querySelector("span:last-child");
          if (text) {
            text.textContent = `warning_level=${normalizedLevel} · warnings=${warningCount}`;
          }
        }
        if (!warnings.length) {
          const div = document.createElement("div");
          div.className = "item severity-low";
          div.innerHTML = `<div class="title">No readiness warnings</div><div class="sub">Coverage and retrieval look acceptable for this job context.</div>`;
          els.qualityReadinessWarningsList.appendChild(div);
          return;
        }
        const header = document.createElement("div");
        header.className = `item ${level === "high" ? "severity-high" : level === "medium" ? "severity-medium" : "severity-low"}`;
        header.innerHTML = `<div class="title">Warnings: ${warningCount}</div><div class="sub mono">level=${escapeHtml(level)}</div>`;
        els.qualityReadinessWarningsList.appendChild(header);
        for (const row of warnings) {
          if (!row || typeof row !== "object") continue;
          const severity = String(row.severity || "low").toLowerCase();
          const cls = severity === "high" ? "severity-high" : severity === "medium" ? "severity-medium" : "severity-low";
          const code = String(row.code || "READINESS_WARNING");
          const message = String(row.message || "");
          const div = document.createElement("div");
          div.className = `item ${cls}`;
          div.innerHTML = `<div class="title mono">${escapeHtml(code)}</div><div class="sub">${escapeHtml(message)}</div>`;
          els.qualityReadinessWarningsList.appendChild(div);
        }
      }

      function renderPortfolioMetricsCards(metrics) {
        const values = [
          String(metrics.job_count ?? "-"),
          String(metrics.terminal_job_count ?? "-"),
          String(metrics.hitl_job_count ?? "-"),
          String(metrics.total_pause_count ?? "-"),
          String(metrics.total_resume_count ?? "-"),
          fmtSec(metrics.avg_time_to_first_draft_seconds),
        ];
        [...els.portfolioMetricsCards.querySelectorAll(".kpi .value")].forEach((node, i) => {
          node.textContent = values[i] ?? "-";
        });
      }

      function getTopWeightedRiskDonorEntry(summary) {
        const donorRows =
          summary && summary.donor_weighted_risk_breakdown && typeof summary.donor_weighted_risk_breakdown === "object"
            ? summary.donor_weighted_risk_breakdown
            : {};
        return (
          Object.entries(donorRows)
            .map(([donorId, row]) => [
              String(donorId),
              row && typeof row === "object" && !Array.isArray(row) ? row : {},
            ])
            .sort(
              (a, b) =>
                Number((b[1] || {}).weighted_score || 0) - Number((a[1] || {}).weighted_score || 0) ||
                a[0].localeCompare(b[0])
            )[0] || null
        );
      }

      function getFocusedWeightedRiskDonorEntry(summary) {
        const donorRows =
          summary && summary.donor_weighted_risk_breakdown && typeof summary.donor_weighted_risk_breakdown === "object"
            ? summary.donor_weighted_risk_breakdown
            : {};
        const donorFilter = String((els.portfolioDonorFilter && els.portfolioDonorFilter.value) || "").trim();
        if (donorFilter && donorRows && Object.prototype.hasOwnProperty.call(donorRows, donorFilter)) {
          const row = donorRows[donorFilter];
          return [donorFilter, row && typeof row === "object" && !Array.isArray(row) ? row : {}];
        }
        return getTopWeightedRiskDonorEntry(summary);
      }

      function renderPortfolioQualityLlmLabelDrilldown(summary) {
        const critic = summary?.critic || {};
        renderKeyValueList(
          els.portfolioQualityLlmLabelCountsList,
          critic.llm_finding_label_counts,
          "No aggregated LLM finding labels.",
          10
        );

        const topDonor = getTopWeightedRiskDonorEntry(summary);
        if (topDonor) {
          const [donorId, donorRow] = topDonor;
          renderKeyValueList(
            els.portfolioQualityTopDonorLlmLabelCountsList,
            donorRow.llm_finding_label_counts,
            `No LLM finding labels for top donor (${donorId}).`,
            8
          );
          renderKeyValueList(
            els.portfolioQualityTopDonorAdvisoryRejectedReasonsList,
            donorRow.llm_advisory_rejected_reason_counts,
            `No advisory rejections for top donor (${donorId}).`,
            8
          );
          const topDonorAdvisorySummary = {
            jobs_with_diagnostics: Number(donorRow.llm_advisory_diagnostics_job_count || 0),
            advisory_applied_jobs: Number(donorRow.llm_advisory_applied_job_count || 0),
            advisory_applied_rate:
              typeof donorRow.llm_advisory_applied_rate === "number"
                ? `${(Number(donorRow.llm_advisory_applied_rate) * 100).toFixed(1)}%`
                : "-",
            advisory_candidate_findings: Number(donorRow.llm_advisory_candidate_finding_count || 0),
          };
          renderKeyValueList(
            els.portfolioQualityTopDonorAdvisoryAppliedList,
            topDonorAdvisorySummary,
            `No advisory diagnostics for top donor (${donorId}).`,
            8
          );
          return;
        }
        renderKeyValueList(
          els.portfolioQualityTopDonorLlmLabelCountsList,
          null,
          "No donor weighted risk rows yet.",
          8
        );
        renderKeyValueList(
          els.portfolioQualityTopDonorAdvisoryRejectedReasonsList,
          null,
          "No donor weighted risk rows yet.",
          8
        );
        renderKeyValueList(
          els.portfolioQualityTopDonorAdvisoryAppliedList,
          null,
          "No donor weighted risk rows yet.",
          8
        );
      }

      function renderPortfolioQualityAdvisoryDrilldown(summary) {
        const critic = summary?.critic || {};
        const appliedJobs = Number(critic.llm_advisory_applied_job_count || 0);
        const diagnosticsJobs = Number(critic.llm_advisory_diagnostics_job_count || 0);
        const appliedRate =
          typeof critic.llm_advisory_applied_rate === "number"
            ? `${(Number(critic.llm_advisory_applied_rate) * 100).toFixed(1)}%`
            : "-";
        const advisoryCandidates = Number(critic.llm_advisory_candidate_finding_count || 0);
        const appliedSummary = {
          "jobs_with_diagnostics": diagnosticsJobs,
          "advisory_applied_jobs": appliedJobs,
          "advisory_applied_rate": appliedRate,
          "advisory_candidate_findings": advisoryCandidates,
        };
        renderKeyValueList(
          els.portfolioQualityAdvisoryAppliedList,
          appliedSummary,
          "No advisory diagnostics aggregated yet.",
          8
        );
        renderKeyValueList(
          els.portfolioQualityAdvisoryRejectedReasonsList,
          critic.llm_advisory_rejected_reason_counts,
          "No advisory rejections recorded.",
          8
        );
      }

      function renderPortfolioQualityFocusedDonorCard(summary) {
        function setFocusedDonorAdvisoryPill(text, cls) {
          if (!els.portfolioQualityFocusedDonorAdvisoryPill || !els.portfolioQualityFocusedDonorAdvisoryPillText) return;
          els.portfolioQualityFocusedDonorAdvisoryPill.className = `pill ${cls || "status-unknown"}`;
          els.portfolioQualityFocusedDonorAdvisoryPillText.textContent = text;
        }
        const focused = getFocusedWeightedRiskDonorEntry(summary);
        if (!focused) {
          setFocusedDonorAdvisoryPill("advisory rate: -", "status-unknown");
          renderKeyValueList(
            els.portfolioQualityFocusedDonorSummaryList,
            null,
            "No donor weighted risk rows yet.",
            8
          );
          renderKeyValueList(
            els.portfolioQualityFocusedDonorLlmLabelCountsList,
            null,
            "No donor weighted risk rows yet.",
            8
          );
          renderKeyValueList(
            els.portfolioQualityFocusedDonorAdvisoryRejectedReasonsList,
            null,
            "No donor weighted risk rows yet.",
            8
          );
          renderKeyValueList(
            els.portfolioQualityFocusedDonorAdvisoryAppliedLabelCountsList,
            null,
            "No donor weighted risk rows yet.",
            8
          );
          renderKeyValueList(
            els.portfolioQualityFocusedDonorAdvisoryRejectedLabelCountsList,
            null,
            "No donor weighted risk rows yet.",
            8
          );
          return;
        }
        const [donorId, donorRow] = focused;
        const donorDiagJobs = Number(donorRow.llm_advisory_diagnostics_job_count || 0);
        const donorAppliedJobs = Number(donorRow.llm_advisory_applied_job_count || 0);
        const donorAppliedRate =
          typeof donorRow.llm_advisory_applied_rate === "number" ? Number(donorRow.llm_advisory_applied_rate) : null;
        let pillClass = "status-unknown";
        if (donorAppliedRate !== null) {
          if (donorAppliedRate >= 0.66) pillClass = "status-done";
          else if (donorAppliedRate >= 0.33) pillClass = "status-pending_hitl";
          else pillClass = "status-error";
        }
        setFocusedDonorAdvisoryPill(
          donorAppliedRate === null
            ? `advisory rate: - (${donorId})`
            : `advisory rate: ${(donorAppliedRate * 100).toFixed(1)}% (${donorAppliedJobs}/${donorDiagJobs || 0})`,
          pillClass
        );
        const summaryRows = {
          donor_id: donorId,
          weighted_score: Number(donorRow.weighted_score || 0),
          high_priority_signals: Number(donorRow.high_priority_signal_count || 0),
          open_findings: Number(donorRow.open_findings_total || 0),
          high_severity_findings: Number(donorRow.high_severity_findings_total || 0),
          advisory_applied_rate: donorAppliedRate !== null ? `${(donorAppliedRate * 100).toFixed(1)}%` : "-",
        };
        renderKeyValueList(
          els.portfolioQualityFocusedDonorSummaryList,
          summaryRows,
          `No focused donor summary for ${donorId}.`,
          8
        );
        renderKeyValueList(
          els.portfolioQualityFocusedDonorLlmLabelCountsList,
          donorRow.llm_finding_label_counts,
          `No LLM finding labels for ${donorId}.`,
          8
        );
        renderKeyValueList(
          els.portfolioQualityFocusedDonorAdvisoryRejectedReasonsList,
          donorRow.llm_advisory_rejected_reason_counts,
          `No advisory rejections for ${donorId}.`,
          8
        );
        renderKeyValueList(
          els.portfolioQualityFocusedDonorAdvisoryAppliedLabelCountsList,
          donorRow.llm_advisory_applied_label_counts,
          `No advisory-applied labels for ${donorId}.`,
          8
        );
        renderKeyValueList(
          els.portfolioQualityFocusedDonorAdvisoryRejectedLabelCountsList,
          donorRow.llm_advisory_rejected_label_counts,
          `No advisory-rejected labels for ${donorId}.`,
          8
        );
      }

      function renderPortfolioQualityCards(summary) {
        const critic = summary?.critic || {};
        const citations = summary?.citations || {};
        const portfolioJobCount = Number(summary?.job_count ?? 0);
        const warningCounts =
          summary?.warning_level_job_counts && typeof summary.warning_level_job_counts === "object"
            ? summary.warning_level_job_counts
            : (summary?.warning_level_counts || {});
        const warningRates =
          summary?.warning_level_job_rates && typeof summary.warning_level_job_rates === "object"
            ? summary.warning_level_job_rates
            : {};
        const highWarningCount = Number(warningCounts.high ?? summary?.warning_level_high_job_count ?? 0);
        const mediumWarningCount = Number(warningCounts.medium ?? summary?.warning_level_medium_job_count ?? 0);
        const lowWarningCount = Number(warningCounts.low ?? summary?.warning_level_low_job_count ?? 0);
        const noneWarningCount = Number(warningCounts.none ?? summary?.warning_level_none_job_count ?? 0);
        const needsRevisionRate =
          typeof critic.needs_revision_rate === "number"
            ? `${(Number(critic.needs_revision_rate) * 100).toFixed(1)}%`
            : "-";
        const thresholdHitRate =
          typeof citations.architect_threshold_hit_rate_avg === "number"
            ? `${(Number(citations.architect_threshold_hit_rate_avg) * 100).toFixed(1)}%`
            : "-";
        const claimSupportRate =
          typeof citations.architect_claim_support_rate_avg === "number"
            ? `${(Number(citations.architect_claim_support_rate_avg) * 100).toFixed(1)}%`
            : "-";
        const formatWarningRate = (explicitValue, fallbackValue) => {
          if (typeof explicitValue === "number") return `${(Number(explicitValue) * 100).toFixed(1)}%`;
          if (typeof fallbackValue === "number") return `${(Number(fallbackValue) * 100).toFixed(1)}%`;
          return "-";
        };
        const highWarningRate =
          formatWarningRate(summary?.warning_level_high_rate, warningRates.high);
        const mediumWarningRate =
          formatWarningRate(summary?.warning_level_medium_rate, warningRates.medium);
        const lowWarningRate =
          formatWarningRate(summary?.warning_level_low_rate, warningRates.low);
        const noneWarningRate =
          formatWarningRate(summary?.warning_level_none_rate, warningRates.none);
        const fallbackDominanceRate =
          typeof citations.fallback_namespace_citation_rate === "number"
            ? `${(Number(citations.fallback_namespace_citation_rate) * 100).toFixed(1)}%`
            : "-";
        const highGroundingRiskDonorCount = Number(
          summary?.high_grounding_risk_donor_count ??
          summary?.donor_grounding_risk_counts?.high ??
          0
        );
        const values = [
          typeof summary?.avg_quality_score === "number" ? Number(summary.avg_quality_score).toFixed(2) : "-",
          needsRevisionRate,
          String(critic.open_findings_total ?? "-"),
          String(critic.high_severity_findings_total ?? "-"),
          typeof citations.citation_confidence_avg === "number" ? Number(citations.citation_confidence_avg).toFixed(2) : "-",
          thresholdHitRate,
          claimSupportRate,
          String(summary?.severity_weighted_risk_score ?? "-"),
          String(summary?.high_priority_signal_count ?? "-"),
          highWarningRate,
          mediumWarningRate,
          lowWarningRate,
          noneWarningRate,
          fallbackDominanceRate,
          String(highGroundingRiskDonorCount),
        ];
        const portfolioQualityValueNodes = [...els.portfolioQualityCards.querySelectorAll(".kpi .value")];
        portfolioQualityValueNodes.forEach((node, i) => {
          node.textContent = values[i] ?? "-";
        });
        const claimSupportNode = portfolioQualityValueNodes[6];
        if (claimSupportNode) {
          const rate = Number(citations?.architect_claim_support_rate_avg ?? NaN);
          claimSupportNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (Number.isFinite(rate)) {
            if (rate < 0.5) claimSupportNode.classList.add("risk-high");
            else if (rate < 0.7) claimSupportNode.classList.add("risk-medium");
            else claimSupportNode.classList.add("risk-low");
          } else {
            claimSupportNode.classList.add("risk-none");
          }
          const support = Number(citations?.architect_claim_support_citation_count ?? 0);
          const total = Number(citations?.architect_citation_count_total ?? 0);
          claimSupportNode.title =
            total > 0
              ? `${support}/${total} architect claim-support citations`
              : "No architect citations in current filter";
        }
        const warningKpiConfig = [
          { index: 9, level: "high", count: highWarningCount, activeClass: "risk-high" },
          { index: 10, level: "medium", count: mediumWarningCount, activeClass: "risk-medium" },
          { index: 11, level: "low", count: lowWarningCount, activeClass: "risk-low" },
          { index: 12, level: "none", count: noneWarningCount, activeClass: "risk-low" },
        ];
        for (const cfg of warningKpiConfig) {
          const node = portfolioQualityValueNodes[cfg.index];
          if (!node) continue;
          node.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          node.classList.add(cfg.count > 0 ? cfg.activeClass : "risk-none");
          node.title =
            portfolioJobCount > 0
              ? `${cfg.count} jobs / ${portfolioJobCount} total · click to filter`
              : "No portfolio jobs in current filter";
          node.style.cursor = portfolioJobCount > 0 ? "pointer" : "default";
          node.onclick = portfolioJobCount > 0 ? () => applyPortfolioWarningLevelFilter(cfg.level) : null;
        }
        const fallbackNode = portfolioQualityValueNodes[13];
        if (fallbackNode) {
          const fallbackRate = Number(citations?.fallback_namespace_citation_rate ?? NaN);
          fallbackNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (Number.isFinite(fallbackRate)) {
            if (fallbackRate >= 0.8) fallbackNode.classList.add("risk-high");
            else if (fallbackRate >= 0.5) fallbackNode.classList.add("risk-medium");
            else fallbackNode.classList.add("risk-low");
          } else {
            fallbackNode.classList.add("risk-none");
          }
          const fallbackCount = Number(citations?.fallback_namespace_citation_count ?? 0);
          const citationCount = Number(citations?.citation_count_total ?? 0);
          fallbackNode.title =
            citationCount > 0 ? `${fallbackCount}/${citationCount} fallback citations` : "No citations in current filter";
        }
        const highGroundingNode = portfolioQualityValueNodes[14];
        if (highGroundingNode) {
          highGroundingNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          highGroundingNode.classList.add(highGroundingRiskDonorCount > 0 ? "risk-high" : "risk-none");
          const donorCount = Number(Object.keys(summary?.donor_counts || {}).length || 0);
          highGroundingNode.title =
            donorCount > 0
              ? `${highGroundingRiskDonorCount} of ${donorCount} donors are high grounding-risk`
              : "No donors in current filter";
        }
        if (els.portfolioWarningMetaLine) {
          els.portfolioWarningMetaLine.textContent =
            `high=${highWarningCount} · medium=${mediumWarningCount} · low=${lowWarningCount} · none=${noneWarningCount} · total=${portfolioJobCount}`;
        }
        renderKeyValueList(
          els.portfolioQualityCitationTypeCountsList,
          citations.citation_type_counts_total,
          "No portfolio citation type breakdown yet.",
          8
        );
        renderKeyValueList(
          els.portfolioQualityArchitectCitationTypeCountsList,
          citations.architect_citation_type_counts_total,
          "No portfolio architect citation type breakdown yet.",
          8
        );
        renderKeyValueList(
          els.portfolioQualityMelCitationTypeCountsList,
          citations.mel_citation_type_counts_total,
          "No portfolio MEL citation type breakdown yet.",
          8
        );
        renderPortfolioQualityLlmLabelDrilldown(summary);
        renderPortfolioQualityAdvisoryDrilldown(summary);
        renderPortfolioQualityFocusedDonorCard(summary);
      }

      function renderKeyValueList(container, mapping, emptyLabel, topN = 8, onSelect = null) {
        container.innerHTML = "";
        if (!mapping || typeof mapping !== "object" || Array.isArray(mapping)) {
          container.innerHTML = `<div class="item"><div class="sub">${escapeHtml(emptyLabel)}</div></div>`;
          return;
        }
        const entries = Object.entries(mapping)
          .map(([k, v]) => [String(k), Number(v || 0)])
          .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
          .slice(0, topN);
        if (entries.length === 0) {
          container.innerHTML = `<div class="item"><div class="sub">${escapeHtml(emptyLabel)}</div></div>`;
          return;
        }
        for (const [key, value] of entries) {
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(key)}</div>
            <div class="sub">count: ${escapeHtml(String(value))}</div>
          `;
          if (typeof onSelect === "function") {
            div.style.cursor = "pointer";
            div.title = "Click to filter";
            div.addEventListener("click", () => onSelect(key));
          }
          container.appendChild(div);
        }
      }

      function renderWarningLevelBreakdownList(
        container,
        countsMapping,
        ratesMapping,
        emptyLabel,
        onSelect = null,
        levels = ["high", "medium", "low", "none"]
      ) {
        container.innerHTML = "";
        if (!countsMapping || typeof countsMapping !== "object" || Array.isArray(countsMapping)) {
          container.innerHTML = `<div class="item"><div class="sub">${escapeHtml(emptyLabel)}</div></div>`;
          return;
        }
        const rows = levels.map((level) => {
          const count = Number(countsMapping[level] || 0);
          const rawRate =
            ratesMapping && typeof ratesMapping === "object" && !Array.isArray(ratesMapping)
              ? ratesMapping[level]
              : null;
          const rateLabel =
            typeof rawRate === "number" ? `${(Number(rawRate) * 100).toFixed(1)}%` : "-";
          return { level, count, rateLabel };
        });
        const hasAnyCounts = rows.some((row) => row.count > 0);
        if (!hasAnyCounts) {
          container.innerHTML = `<div class="item"><div class="sub">${escapeHtml(emptyLabel)}</div></div>`;
          return;
        }
        for (const row of rows) {
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(row.level)}</div>
            <div class="sub">count: ${escapeHtml(String(row.count))} · rate: ${escapeHtml(row.rateLabel)}</div>
          `;
          if (typeof onSelect === "function") {
            div.style.cursor = "pointer";
            div.title = "Click to filter";
            div.addEventListener("click", () => onSelect(row.level));
          }
          container.appendChild(div);
        }
      }

      function renderDonorGroundingRiskList(container, mapping, emptyLabel, topN = 8, onSelect = null) {
        container.innerHTML = "";
        if (!mapping || typeof mapping !== "object" || Array.isArray(mapping)) {
          container.innerHTML = `<div class="item"><div class="sub">${escapeHtml(emptyLabel)}</div></div>`;
          return;
        }
        const entries = Object.entries(mapping)
          .map(([donorId, row]) => {
            const rec = row && typeof row === "object" && !Array.isArray(row) ? row : {};
            const fallbackRate =
              typeof rec.fallback_namespace_citation_rate === "number"
                ? Number(rec.fallback_namespace_citation_rate)
                : -1;
            return [String(donorId), rec, fallbackRate];
          })
          .sort((a, b) => b[2] - a[2] || a[0].localeCompare(b[0]))
          .slice(0, topN);
        if (!entries.length) {
          container.innerHTML = `<div class="item"><div class="sub">${escapeHtml(emptyLabel)}</div></div>`;
          return;
        }
        for (const [donorId, row] of entries) {
          const level = String(row.grounding_risk_level || "unknown").toLowerCase();
          const fallbackCount = Number(row.fallback_namespace_citation_count || 0);
          const citationCount = Number(row.citation_count_total || 0);
          const rateLabel =
            typeof row.fallback_namespace_citation_rate === "number"
              ? `${(Number(row.fallback_namespace_citation_rate) * 100).toFixed(1)}%`
              : "-";
          const cls = level === "high" ? "severity-high" : level === "medium" ? "severity-medium" : "severity-low";
          const div = document.createElement("div");
          div.className = `item ${cls}`;
          div.innerHTML = `
            <div class="title mono">${escapeHtml(donorId)} · level=${escapeHtml(level)}</div>
            <div class="sub">fallback: ${escapeHtml(String(fallbackCount))}/${escapeHtml(String(citationCount))} · rate: ${escapeHtml(rateLabel)}</div>
          `;
          if (typeof onSelect === "function") {
            div.style.cursor = "pointer";
            div.title = "Click to filter donor";
            div.addEventListener("click", () => onSelect(donorId));
          }
          container.appendChild(div);
        }
      }

      function renderWeightedBreakdownList(
        container,
        mapping,
        emptyLabel,
        topN = 8,
        scoreKey = "weighted_score",
        onSelect = null
      ) {
        container.innerHTML = "";
        if (!mapping || typeof mapping !== "object" || Array.isArray(mapping)) {
          container.innerHTML = `<div class="item"><div class="sub">${escapeHtml(emptyLabel)}</div></div>`;
          return;
        }
        const entries = Object.entries(mapping)
          .map(([k, v]) => {
            const row = v && typeof v === "object" && !Array.isArray(v) ? v : {};
            return [String(k), row];
          })
          .sort((a, b) => {
            const aScore = Number((a[1] || {})[scoreKey] || 0);
            const bScore = Number((b[1] || {})[scoreKey] || 0);
            return bScore - aScore || a[0].localeCompare(b[0]);
          })
          .slice(0, topN);
        if (entries.length === 0) {
          container.innerHTML = `<div class="item"><div class="sub">${escapeHtml(emptyLabel)}</div></div>`;
          return;
        }
        for (const [key, row] of entries) {
          const count = Number(row.count || row.regression_count || 0);
          const weight = row.weight != null ? Number(row.weight || 0) : null;
          const weighted = Number(row[scoreKey] || 0);
          const highPriority = row.high_priority_signal_count != null ? Number(row.high_priority_signal_count || 0) : null;
          const details = [
            `weighted: ${weighted}`,
            `count: ${count}`,
            weight !== null ? `w: ${weight}` : null,
            highPriority !== null ? `high-priority: ${highPriority}` : null,
          ]
            .filter(Boolean)
            .join(" · ");
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(key)}</div>
            <div class="sub">${escapeHtml(details)}</div>
          `;
          if (typeof onSelect === "function") {
            div.style.cursor = "pointer";
            div.title = "Click to filter";
            div.addEventListener("click", () => onSelect(key, row));
          }
          container.appendChild(div);
        }
      }

      function renderCitations(list) {
        els.citationsList.innerHTML = "";
        if (!Array.isArray(list) || list.length === 0) {
          els.citationsList.innerHTML = `<div class="item"><div class="sub">No citations found.</div></div>`;
          return;
        }
        const thresholdSummary = computeArchitectThresholdHitRate(list);
        if (thresholdSummary) {
          const summary = document.createElement("div");
          summary.className = "item";
          summary.innerHTML = `
            <div class="title mono">architect_threshold_hit_rate</div>
            <div class="sub">${escapeHtml(
              `${(thresholdSummary.rate * 100).toFixed(1)}% (${thresholdSummary.hits}/${thresholdSummary.considered})`
            )} · client-side summary from architect citations</div>
          `;
          els.citationsList.appendChild(summary);
        }
        for (const c of list) {
          const div = document.createElement("div");
          div.className = "item";
          const label = c.label || c.source || c.namespace || "Citation";
          const meta = [c.stage, c.citation_type, c.used_for].filter(Boolean).join(" · ");
          const pageChunk = [c.page != null ? `p.${c.page}` : null, c.chunk != null ? `chunk ${c.chunk}` : null].filter(Boolean).join(" · ");
          const confidence =
            c.citation_confidence != null && !Number.isNaN(Number(c.citation_confidence))
              ? `conf ${Number(c.citation_confidence).toFixed(2)}`
              : "";
          const threshold =
            c.confidence_threshold != null && !Number.isNaN(Number(c.confidence_threshold))
              ? `thr ${Number(c.confidence_threshold).toFixed(2)}`
              : "";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(label)}</div>
            <div class="sub">${escapeHtml(meta || "trace")}${confidence ? ` · ${escapeHtml(confidence)}` : ""}${threshold ? ` · ${escapeHtml(threshold)}` : ""}${pageChunk ? ` · ${escapeHtml(pageChunk)}` : ""}</div>
            ${c.excerpt ? `<div class="sub" style="margin-top:6px;">${escapeHtml(String(c.excerpt).slice(0, 240))}</div>` : ""}
          `;
          els.citationsList.appendChild(div);
        }
      }

      function renderVersions(list) {
        els.versionsList.innerHTML = "";
        if (!Array.isArray(list) || list.length === 0) {
          els.versionsList.innerHTML = `<div class="item"><div class="sub">No versions found.</div></div>`;
          return;
        }
        for (const v of list) {
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(v.version_id || "version")}</div>
            <div class="sub">${escapeHtml([v.section, v.node, v.iteration != null ? `iter ${v.iteration}` : null].filter(Boolean).join(" · "))}</div>
          `;
          div.addEventListener("click", () => {
            if (!els.fromVersionId.value) els.fromVersionId.value = v.version_id || "";
            else els.toVersionId.value = v.version_id || "";
            persistUiState();
          });
          els.versionsList.appendChild(div);
        }
      }

      function renderEvents(list) {
        els.eventsList.innerHTML = "";
        if (!Array.isArray(list) || list.length === 0) {
          els.eventsList.innerHTML = `<div class="item"><div class="sub">No events found.</div></div>`;
          return;
        }
        for (const e of list) {
          const div = document.createElement("div");
          div.className = "item";
          const transition = e.type === "status_changed" ? [e.from_status || "∅", "→", e.to_status || "?"].join(" ") : "";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(e.type || "event")}</div>
            <div class="sub">${escapeHtml(e.ts || "")}${transition ? ` · ${escapeHtml(transition)}` : ""}</div>
          `;
          els.eventsList.appendChild(div);
        }
      }

      function renderComments(list) {
        els.commentsList.innerHTML = "";
        if (!Array.isArray(list) || list.length === 0) {
          els.commentsList.innerHTML = `<div class="item"><div class="sub">No comments found.</div></div>`;
          return;
        }
        for (const c of list) {
          const div = document.createElement("div");
          div.className = "item";
          const titleBits = [`[${c.status || "open"}]`, c.section || "general"];
          if (c.comment_id) titleBits.push(`#${String(c.comment_id).slice(0, 8)}`);
          const workflowMeta = [
            c.workflow_state ? `state ${c.workflow_state}` : null,
            c.is_overdue === true ? "overdue" : null,
            c.due_at ? `due ${c.due_at}` : null,
            Number.isFinite(Number(c.sla_hours)) ? `sla ${Number(c.sla_hours)}h` : null,
          ]
            .filter(Boolean)
            .join(" · ");
          const meta = [
            c.ts,
            c.author,
            c.version_id,
            c.linked_finding_id ? `finding ${String(c.linked_finding_id).slice(0, 8)}` : null,
            workflowMeta || null,
          ]
            .filter(Boolean)
            .join(" · ");
          div.innerHTML = `
            <div class="title mono">${escapeHtml(titleBits.join(" "))}</div>
            <div class="sub">${escapeHtml(c.message || "")}</div>
            <div class="sub" style="margin-top:6px;">${escapeHtml(meta || "")}</div>
          `;
          div.addEventListener("click", () => {
            els.selectedCommentId.value = c.comment_id || "";
            if (c.section) els.commentSection.value = c.section;
            if (c.version_id) els.commentVersionId.value = c.version_id;
            els.linkedFindingId.value = c.linked_finding_id || "";
            persistUiState();
          });
          els.commentsList.appendChild(div);
        }
      }

      function renderReviewWorkflowTimeline(body) {
        const timeline = Array.isArray(body?.timeline) ? body.timeline : [];
        els.reviewWorkflowTimelineList.innerHTML = "";
        if (!timeline.length) {
          els.reviewWorkflowTimelineList.innerHTML = `<div class="item"><div class="sub">No review workflow events.</div></div>`;
        } else {
          for (const item of timeline) {
            const findingId = String(item.finding_id || "").trim();
            const commentId = String(item.comment_id || "").trim();
            const parts = [item.type || "event", item.status || "-", item.section || "-"];
            if (findingId) parts.push(`finding ${findingId.slice(0, 8)}`);
            if (commentId) parts.push(`comment ${commentId.slice(0, 8)}`);
            const meta = [item.ts, item.actor || item.author, item.severity].filter(Boolean).join(" · ");
            const div = document.createElement("div");
            div.className = "item";
            div.innerHTML = `
              <div class="title mono">${escapeHtml(parts.join(" · "))}</div>
              <div class="sub">${escapeHtml(item.message || "")}</div>
              <div class="sub" style="margin-top:6px;">${escapeHtml(meta || "")}</div>
            `;
            if (findingId) {
              div.style.cursor = "pointer";
              div.title = "Click to link finding in comment form";
              div.addEventListener("click", () => {
                els.linkedFindingId.value = findingId;
                els.reviewWorkflowFindingIdFilter.value = findingId;
                persistUiState();
                refreshReviewWorkflow().catch(showError);
              });
            }
            els.reviewWorkflowTimelineList.appendChild(div);
          }
        }
        const summary = body?.summary && typeof body.summary === "object" ? body.summary : {};
        const timelineCount = Number(summary.timeline_event_count || timeline.length || 0);
        const findingCount = Number(summary.finding_count || 0);
        const commentCount = Number(summary.comment_count || 0);
        const pendingFindingCount = Number(summary.pending_finding_count || 0);
        const overdueFindingCount = Number(summary.overdue_finding_count || 0);
        const pendingCommentCount = Number(summary.pending_comment_count || 0);
        const overdueCommentCount = Number(summary.overdue_comment_count || 0);
        const orphanLinkedCount = Number(summary.orphan_linked_comment_count || 0);
        const lastActivity = String(summary.last_activity_at || "-");
        if (els.reviewWorkflowSummaryLine) {
          els.reviewWorkflowSummaryLine.textContent =
            `workflow: timeline=${timelineCount} · findings=${findingCount} (pending=${pendingFindingCount}, overdue=${overdueFindingCount}) · comments=${commentCount} (pending=${pendingCommentCount}, overdue=${overdueCommentCount}) · orphan_links=${orphanLinkedCount} · last=${lastActivity}`;
        }
      }

      function renderReviewWorkflowSla(body) {
        const hotspots = Array.isArray(body?.top_overdue) ? body.top_overdue : [];
        const oldest = body?.oldest_overdue && typeof body.oldest_overdue === "object" ? body.oldest_overdue : null;
        const overdueTotal = Number(body?.overdue_total || 0);
        const breachRateRaw = body?.breach_rate;
        const breachRate =
          breachRateRaw != null && Number.isFinite(Number(breachRateRaw))
            ? `${(Number(breachRateRaw) * 100).toFixed(1)}%`
            : "-";
        const oldestToken = oldest
          ? `${String(oldest.kind || "item")}#${String(oldest.id || "").slice(0, 8)}`
          : "-";
        if (els.reviewWorkflowSlaSummaryLine) {
          els.reviewWorkflowSlaSummaryLine.textContent =
            `sla: overdue=${overdueTotal} · breach_rate=${breachRate} · oldest=${oldestToken}`;
        }

        els.reviewWorkflowSlaHotspotsList.innerHTML = "";
        if (!hotspots.length) {
          els.reviewWorkflowSlaHotspotsList.innerHTML = `<div class="item"><div class="sub">No overdue SLA items.</div></div>`;
          return;
        }
        for (const item of hotspots) {
          const overdueHours =
            item?.overdue_hours != null && Number.isFinite(Number(item.overdue_hours))
              ? `${Number(item.overdue_hours).toFixed(2)}h overdue`
              : "overdue";
          const bits = [
            item.kind || "item",
            item.status || "-",
            item.section || "-",
            item.severity || "-",
            item.id ? `#${String(item.id).slice(0, 8)}` : null,
          ].filter(Boolean);
          const meta = [item.due_at ? `due ${item.due_at}` : null, overdueHours, item.linked_finding_id ? `finding ${String(item.linked_finding_id).slice(0, 8)}` : null]
            .filter(Boolean)
            .join(" · ");
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(bits.join(" · "))}</div>
            <div class="sub">${escapeHtml(item.message || "")}</div>
            <div class="sub" style="margin-top:6px;">${escapeHtml(meta)}</div>
          `;
          els.reviewWorkflowSlaHotspotsList.appendChild(div);
        }
      }

      function renderCriticLists(body) {
        const section = (els.criticSectionFilter.value || "").trim();
        const severity = (els.criticSeverityFilter.value || "").trim();
        const findingStatus = (els.criticFindingStatusFilter.value || "").trim();
        const flaws = Array.isArray(body?.fatal_flaws) ? body.fatal_flaws : [];
        const checks = Array.isArray(body?.rule_checks) ? body.rule_checks : [];
        renderCriticAdvisoryDiagnostics(body);
        const filteredFlaws = flaws.filter((f) => {
          if (section && String(f.section || "") !== section) return false;
          if (severity && String(f.severity || "") !== severity) return false;
          if (findingStatus && String(f.status || "") !== findingStatus) return false;
          return true;
        });
        const filteredChecks = section ? checks.filter((c) => String(c.section || "") === section) : checks;

        els.criticFlawsList.innerHTML = "";
        if (filteredFlaws.length === 0) {
          els.criticFlawsList.innerHTML = `<div class="item"><div class="sub">No fatal flaws${section ? ` for ${escapeHtml(section)}` : ""}.</div></div>`;
        } else {
          for (const flaw of filteredFlaws) {
            const flawId = String(flaw.id || flaw.finding_id || "").trim();
            const div = document.createElement("div");
            const flawSeverity = String(flaw.severity || "").toLowerCase();
            div.className = `item${flawSeverity ? ` severity-${flawSeverity}` : ""}`;
            const titleBits = [flaw.status || "open", flaw.severity || "severity", flaw.section || "section", flaw.code || "FLAW"];
            const meta = [
              flaw.version_id,
              flaw.source,
              flaw.due_at ? `due ${flaw.due_at}` : null,
              Number.isFinite(Number(flaw.sla_hours)) ? `sla ${Number(flaw.sla_hours)}h` : null,
              flaw.workflow_state ? `state ${flaw.workflow_state}` : null,
            ]
              .filter(Boolean)
              .join(" · ");
            const linkedComments = Array.isArray(flaw.linked_comment_ids) ? flaw.linked_comment_ids : [];
            div.innerHTML = `
              <div class="title mono">${escapeHtml(titleBits.join(" · "))}</div>
              <div class="sub">${escapeHtml(flaw.message || "")}</div>
              ${flaw.fix_hint ? `<div class="sub" style="margin-top:6px;">Fix: ${escapeHtml(flaw.fix_hint)}</div>` : ""}
              ${meta ? `<div class="sub" style="margin-top:6px;">${escapeHtml(meta)}</div>` : ""}
              ${flawId ? `<div class="sub" style="margin-top:6px;">finding_id: ${escapeHtml(String(flawId).slice(0, 12))}${linkedComments.length ? ` · linked comments: ${escapeHtml(String(linkedComments.length))}` : ""}</div>` : ""}
            `;
            const actionsRow = document.createElement("div");
            actionsRow.style.marginTop = "8px";
            actionsRow.style.display = "flex";
            actionsRow.style.gap = "8px";
            actionsRow.style.flexWrap = "wrap";

            if (flawId && flaw.status !== "acknowledged" && flaw.status !== "resolved") {
              const ackBtn = document.createElement("button");
              ackBtn.className = "ghost";
              ackBtn.textContent = "Acknowledge";
              ackBtn.addEventListener("click", (event) => {
                event.stopPropagation();
                setFindingStatus(flawId, "acknowledged").catch(showError);
              });
              actionsRow.appendChild(ackBtn);
            }
            if (flawId && flaw.status !== "resolved") {
              const resolveBtn = document.createElement("button");
              resolveBtn.className = "ghost";
              resolveBtn.textContent = "Resolve Finding";
              resolveBtn.addEventListener("click", (event) => {
                event.stopPropagation();
                setFindingStatus(flawId, "resolved").catch(showError);
              });
              actionsRow.appendChild(resolveBtn);
            }
            if (flawId && (flaw.status === "acknowledged" || flaw.status === "resolved")) {
              const reopenBtn = document.createElement("button");
              reopenBtn.className = "ghost";
              reopenBtn.textContent = "Reopen Finding";
              reopenBtn.addEventListener("click", (event) => {
                event.stopPropagation();
                setFindingStatus(flawId, "open").catch(showError);
              });
              actionsRow.appendChild(reopenBtn);
            }

            const commentBtn = document.createElement("button");
            commentBtn.className = "ghost";
            commentBtn.textContent = "Create Comment";
            commentBtn.addEventListener("click", (event) => {
              event.stopPropagation();
              prefillCommentFromFinding(flaw);
            });
            actionsRow.appendChild(commentBtn);

            if (flaw.section === "toc" || flaw.section === "logframe") {
              const jumpBtn = document.createElement("button");
              jumpBtn.className = "ghost";
              jumpBtn.textContent = "Jump to Diff";
              jumpBtn.addEventListener("click", (event) => {
                event.stopPropagation();
                jumpToDiffForFinding(flaw).catch(showError);
              });
              actionsRow.appendChild(jumpBtn);
            }

            div.appendChild(actionsRow);
            els.criticFlawsList.appendChild(div);
          }
        }

        els.criticChecksList.innerHTML = "";
        if (filteredChecks.length === 0) {
          els.criticChecksList.innerHTML = `<div class="item"><div class="sub">No rule checks${section ? ` for ${escapeHtml(section)}` : ""}.</div></div>`;
          return;
        }
        for (const check of filteredChecks) {
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml([check.status || "status", check.section || "section", check.code || "CHECK"].join(" · "))}</div>
            <div class="sub">${escapeHtml(check.detail || "")}</div>
          `;
          els.criticChecksList.appendChild(div);
        }

        renderCriticContextCitations();
      }

      function renderCriticAdvisoryDiagnostics(body) {
        const diagnostics = (body && typeof body === "object") ? body.llm_advisory_diagnostics : null;
        const normalization = (body && typeof body === "object") ? body.llm_advisory_normalization : null;
        const scoreCalibration = (body && typeof body === "object") ? body.llm_advisory_score_calibration : null;

        if (els.criticAdvisorySummaryList) els.criticAdvisorySummaryList.innerHTML = "";
        if (els.criticAdvisoryLabelsList) els.criticAdvisoryLabelsList.innerHTML = "";
        if (els.criticAdvisoryNormalizationList) els.criticAdvisoryNormalizationList.innerHTML = "";

        if (!diagnostics || typeof diagnostics !== "object") {
          if (els.criticAdvisorySummaryList) {
            els.criticAdvisorySummaryList.innerHTML = `<div class="item"><div class="sub">No LLM advisory diagnostics.</div></div>`;
          }
          if (els.criticAdvisoryLabelsList) {
            els.criticAdvisoryLabelsList.innerHTML = `<div class="item"><div class="sub">No candidate labels.</div></div>`;
          }
          if (els.criticAdvisoryNormalizationList) {
            els.criticAdvisoryNormalizationList.innerHTML = `<div class="item"><div class="sub">No advisory normalization metadata.</div></div>`;
          }
          return;
        }

        const summaryItems = [
          `applies: ${diagnostics.advisory_applies ? "yes" : "no"}`,
          `llm findings: ${diagnostics.llm_finding_count ?? 0}`,
          `advisory candidates: ${diagnostics.advisory_candidate_count ?? 0}`,
          diagnostics.architect_threshold_hit_rate != null ? `thr_hit: ${diagnostics.architect_threshold_hit_rate}` : null,
          diagnostics.architect_rag_low_ratio != null ? `arch_rag_low_ratio: ${diagnostics.architect_rag_low_ratio}` : null,
          diagnostics.advisory_rejected_reason ? `reason: ${diagnostics.advisory_rejected_reason}` : null,
        ].filter(Boolean);
        if (els.criticAdvisorySummaryList) {
          if (!summaryItems.length) {
            els.criticAdvisorySummaryList.innerHTML = `<div class="item"><div class="sub">No advisory diagnostics summary.</div></div>`;
          } else {
            for (const text of summaryItems) {
              const div = document.createElement("div");
              div.className = "item";
              div.innerHTML = `<div class="sub mono">${escapeHtml(String(text))}</div>`;
              els.criticAdvisorySummaryList.appendChild(div);
            }
          }
        }

        const labelCounts = (diagnostics.candidate_label_counts && typeof diagnostics.candidate_label_counts === "object")
          ? diagnostics.candidate_label_counts
          : {};
        const labelRows = Object.entries(labelCounts)
          .sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0) || String(a[0]).localeCompare(String(b[0])))
          .slice(0, 8);
        if (els.criticAdvisoryLabelsList) {
          if (!labelRows.length) {
            els.criticAdvisoryLabelsList.innerHTML = `<div class="item"><div class="sub">No candidate labels.</div></div>`;
          } else {
            for (const [label, count] of labelRows) {
              const div = document.createElement("div");
              div.className = "item";
              div.innerHTML = `<div class="title mono">${escapeHtml(String(label))}</div><div class="sub">count: ${escapeHtml(String(count))}</div>`;
              els.criticAdvisoryLabelsList.appendChild(div);
            }
          }
        }

        const normRows = [];
        if (normalization && typeof normalization === "object") {
          normRows.push(`normalization.applied: ${normalization.applied ? "yes" : "no"}`);
          if (normalization.downgraded_count != null) normRows.push(`downgraded: ${normalization.downgraded_count}`);
          if (normalization.policy_mode) normRows.push(`policy: ${normalization.policy_mode}`);
          if (Array.isArray(normalization.labels_downgraded) && normalization.labels_downgraded.length) {
            normRows.push(`labels: ${normalization.labels_downgraded.join(", ")}`);
          }
        }
        if (scoreCalibration && typeof scoreCalibration === "object") {
          normRows.push(`score_cap.applied: ${scoreCalibration.applied ? "yes" : "no"}`);
          if (scoreCalibration.combined_score_after != null) normRows.push(`score_after: ${scoreCalibration.combined_score_after}`);
        }
        if (els.criticAdvisoryNormalizationList) {
          if (!normRows.length) {
            els.criticAdvisoryNormalizationList.innerHTML = `<div class="item"><div class="sub">No advisory normalization metadata.</div></div>`;
          } else {
            for (const row of normRows) {
              const div = document.createElement("div");
              div.className = "item";
              div.innerHTML = `<div class="sub mono">${escapeHtml(String(row))}</div>`;
              els.criticAdvisoryNormalizationList.appendChild(div);
            }
          }
        }
      }

      function renderCriticContextCitations() {
        if (!els.criticContextList) return;
        const section = (els.criticSectionFilter.value || "").trim();
        const confidenceFilter = (els.criticCitationConfidenceFilter?.value || "").trim();
        const citations = Array.isArray(state.lastCitations) ? state.lastCitations : [];
        let filtered = citations;
        if (section) {
          filtered = citations.filter((c) => {
            const path = String(c.statement_path || "").toLowerCase();
            const usedFor = String(c.used_for || "").toLowerCase();
            const stage = String(c.stage || "").toLowerCase();
            if (section === "toc") {
              return path.startsWith("toc.") || stage === "architect";
            }
            if (section === "logframe") {
              return stage === "mel" || usedFor.includes("indicator") || usedFor.includes("logframe");
            }
            if (section === "general") {
              return !path && !["architect", "mel"].includes(stage);
            }
            return true;
          });
        }
        if (confidenceFilter) {
          filtered = filtered.filter((c) => {
            const raw = c?.citation_confidence;
            const conf = raw == null ? null : Number(raw);
            if (conf == null || Number.isNaN(conf)) return confidenceFilter === "low";
            if (confidenceFilter === "low") return conf < 0.3;
            if (confidenceFilter === "high") return conf >= 0.7;
            return true;
          });
        }
        filtered = filtered.slice(0, 8);

        els.criticContextList.innerHTML = "";
        if (filtered.length === 0) {
          els.criticContextList.innerHTML = `<div class="item"><div class="sub">No citation context${section ? ` for ${escapeHtml(section)}` : ""}.</div></div>`;
          return;
        }
        for (const c of filtered) {
          const div = document.createElement("div");
          div.className = "item";
          const label = c.label || c.source || c.namespace || "Citation";
          const meta = [c.stage, c.citation_type, c.statement_path || c.used_for].filter(Boolean).join(" · ");
          const pageChunk = [c.page != null ? `p.${c.page}` : null, c.chunk_id || null].filter(Boolean).join(" · ");
          const confidence =
            c.citation_confidence != null && !Number.isNaN(Number(c.citation_confidence))
              ? `conf ${Number(c.citation_confidence).toFixed(2)}`
              : "";
          const threshold =
            c.confidence_threshold != null && !Number.isNaN(Number(c.confidence_threshold))
              ? `thr ${Number(c.confidence_threshold).toFixed(2)}`
              : "";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(label)}</div>
            <div class="sub">${escapeHtml(meta || "trace")}${confidence ? ` · ${escapeHtml(confidence)}` : ""}${threshold ? ` · ${escapeHtml(threshold)}` : ""}</div>
            ${pageChunk ? `<div class="sub" style="margin-top:6px;">${escapeHtml(pageChunk)}</div>` : ""}
            ${c.excerpt ? `<div class="sub" style="margin-top:6px;">${escapeHtml(String(c.excerpt).slice(0, 180))}</div>` : ""}
          `;
          els.criticContextList.appendChild(div);
        }
      }

      function prefillCommentFromFinding(flaw) {
        const section = String(flaw?.section || "").trim();
        if (section && ["general", "toc", "logframe"].includes(section)) {
          els.commentSection.value = section;
        }
        const versionId = String(flaw?.version_id || "").trim();
        els.commentVersionId.value = versionId;
        els.linkedFindingId.value = String(flaw?.id || flaw?.finding_id || "").trim();
        const code = String(flaw?.code || "FINDING").trim();
        const msg = String(flaw?.message || "").trim();
        const hint = String(flaw?.fix_hint || "").trim();
        els.commentMessage.value = `[${code}] ${msg}${hint ? `\\nFix hint: ${hint}` : ""}`;
        persistUiState();
        els.commentMessage.focus();
      }

      async function jumpToDiffForFinding(flaw) {
        const section = String(flaw?.section || "").trim();
        if (section === "toc" || section === "logframe") {
          els.diffSection.value = section;
        }
        const versionId = String(flaw?.version_id || "").trim();
        if (versionId) {
          els.toVersionId.value = versionId;
          if (els.fromVersionId.value.trim() === versionId) els.fromVersionId.value = "";
        }
        persistUiState();
        await refreshDiff();
      }

      function escapeHtml(s) {
        return String(s)
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;");
      }

      function renderGeneratePreflightAlert(preflight) {
        if (!els.generatePreflightAlert || !els.generatePreflightAlertTitle || !els.generatePreflightAlertBody) return;
        const container = els.generatePreflightAlert;
        const title = els.generatePreflightAlertTitle;
        const body = els.generatePreflightAlertBody;

        if (!preflight || typeof preflight !== "object") {
          container.className = "item preflight-alert severity-low hidden";
          title.textContent = "Preflight alert";
          body.textContent = "-";
          return;
        }

        const riskLevel = String(preflight.risk_level || "none").toLowerCase();
        const groundingRiskLevel = String(
          preflight.grounding_risk_level || preflight?.grounding_policy?.risk_level || "low"
        ).toLowerCase();
        const warningCount = Number(preflight.warning_count || 0);
        const policy =
          preflight.grounding_policy && typeof preflight.grounding_policy === "object"
            ? preflight.grounding_policy
            : {};
        const policyMode = String(policy.mode || "warn").toLowerCase();
        const policyBlocking = Boolean(policy.blocking);
        const reasonTokens = Array.isArray(policy.reasons)
          ? policy.reasons.map((r) => String(r || "").trim()).filter(Boolean).slice(0, 3)
          : [];
        const coverageLabel =
          typeof preflight.coverage_rate === "number"
            ? `${Math.round(Number(preflight.coverage_rate) * 100)}%`
            : "-";

        const showAlert = policyBlocking || warningCount > 0 || riskLevel === "high" || groundingRiskLevel === "high";
        if (!showAlert) {
          container.className = "item preflight-alert severity-low hidden";
          title.textContent = "Preflight alert";
          body.textContent = "-";
          return;
        }

        let severity = "low";
        if (policyBlocking || riskLevel === "high" || groundingRiskLevel === "high") severity = "high";
        else if (riskLevel === "medium" || groundingRiskLevel === "medium") severity = "medium";

        container.className = `item preflight-alert severity-${severity} blink-in`;
        title.textContent =
          policyBlocking
            ? "Preflight blocked by grounding policy"
            : `Preflight advisory (${severity})`;
        body.textContent =
          `risk=${riskLevel} · grounding=${groundingRiskLevel} · policy=${policyMode}` +
          ` · coverage=${coverageLabel} · warnings=${warningCount}` +
          (reasonTokens.length ? ` · reasons=${reasonTokens.join(",")}` : "");
      }

      async function generateJob() {
        const readiness = getGeneratePresetReadinessStats();
        if (
          readiness.presetKey &&
          readiness.total > 0 &&
          readiness.completed === 0 &&
          !isZeroReadinessWarningSkippedForPreset(readiness.presetKey)
        ) {
          const ok = window.confirm(
            `RAG readiness is 0/${readiness.total} for the selected preset. Generate anyway?`
          );
          if (!ok) return;
        }
        let extraContext = {};
        const extraJsonText = String(els.inputContextJson.value || "").trim();
        if (extraJsonText) {
          let parsed;
          try {
            parsed = JSON.parse(extraJsonText);
          } catch (err) {
            throw new Error(
              `Invalid Extra Input Context JSON: ${err instanceof Error ? err.message : String(err)}`
            );
          }
          if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            throw new Error("Extra Input Context JSON must be a JSON object");
          }
          extraContext = parsed;
        }
        const payload = {
          donor_id: els.donorId.value.trim(),
          input_context: {
            ...extraContext,
            project: els.project.value.trim(),
            country: els.country.value.trim(),
          },
          llm_mode: els.llmMode.value === "true",
          hitl_enabled: els.hitlEnabled.value === "true",
          strict_preflight: els.strictPreflight.value === "true",
        };
        if (readiness.presetKey) {
          const ingestPreset = INGEST_PRESETS[readiness.presetKey];
          const checklistItems = Array.isArray(ingestPreset?.checklist_items) ? ingestPreset.checklist_items : [];
          const expectedDocFamilies = checklistItems
            .map((item) => String(item?.id || "").trim())
            .filter((itemId, idx, arr) => itemId && arr.indexOf(itemId) === idx);
          payload.client_metadata = {
            demo_generate_preset_key: readiness.presetKey,
            donor_id: String(els.donorId.value || "").trim() || null,
            rag_readiness: {
              expected_doc_families: expectedDocFamilies,
              donor_id: String(ingestPreset?.donor_id || els.donorId.value || "").trim() || null,
            },
          };
        }
        if (els.webhookUrl.value.trim()) payload.webhook_url = els.webhookUrl.value.trim();
        if (els.webhookSecret.value.trim()) payload.webhook_secret = els.webhookSecret.value.trim();

        const preflight = await apiFetch("/generate/preflight", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            donor_id: payload.donor_id,
            input_context: payload.input_context,
            client_metadata: payload.client_metadata || null,
          }),
        });
        renderGeneratePreflightAlert(preflight);
        const preflightRiskLevel = String(preflight?.risk_level || "").toLowerCase();
        const groundingRiskLevel = String(
          preflight?.grounding_risk_level || preflight?.grounding_policy?.risk_level || ""
        ).toLowerCase();
        const groundingPolicy =
          preflight?.grounding_policy && typeof preflight.grounding_policy === "object"
            ? preflight.grounding_policy
            : {};
        const groundingPolicyBlocking = Boolean(groundingPolicy.blocking);

        if (groundingPolicyBlocking) {
          const policyReasons = Array.isArray(groundingPolicy.reasons)
            ? groundingPolicy.reasons.map((r) => String(r || "").trim()).filter(Boolean).slice(0, 3).join(", ")
            : "n/a";
          throw new Error(
            `Server preflight blocked by strict grounding policy (mode=${String(groundingPolicy.mode || "strict")}, reasons=${policyReasons}).`
          );
        }

        if (payload.strict_preflight && (preflightRiskLevel === "high" || groundingRiskLevel === "high")) {
          const strictTriggers = [];
          if (preflightRiskLevel === "high") strictTriggers.push("readiness_risk_high");
          if (groundingRiskLevel === "high") strictTriggers.push("grounding_risk_high");
          throw new Error(
            `Strict preflight is enabled and server preflight is blocking (${strictTriggers.join(", ")}).`
          );
        }

        if (preflight && (preflightRiskLevel === "high" || groundingRiskLevel === "high")) {
          const warnings = Array.isArray(preflight.warnings) ? preflight.warnings : [];
          const warningPreview = warnings
            .slice(0, 3)
            .map((w) => String(w?.code || "WARNING"))
            .filter(Boolean)
            .join(", ");
          const policyReasons = Array.isArray(groundingPolicy.reasons)
            ? groundingPolicy.reasons.map((r) => String(r || "").trim()).filter(Boolean).slice(0, 3).join(", ")
            : "";
          const coverageLabel =
            typeof preflight.coverage_rate === "number"
              ? `${Math.round(Number(preflight.coverage_rate) * 100)}%`
              : "-";
          const ok = window.confirm(
            `Server preflight risk is elevated (risk=${preflightRiskLevel || "-"}, grounding=${groundingRiskLevel || "-"}, coverage=${coverageLabel}, warnings=${warningPreview || "n/a"}${policyReasons ? `, policy_reasons=${policyReasons}` : ""}). Generate anyway?`
          );
          if (!ok) return;
        }

        const body = await apiFetch("/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (body && body.job_id) {
          els.jobIdInput.value = body.job_id;
          persistBasics();
          await refreshAll();
        }
      }

      async function refreshStatus() {
        const jobId = currentJobId();
        if (!jobId) return;
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}`);
        setJson(els.statusJson, body);
        setStatusPill(body.status);
        els.checkpointId.value = body.checkpoint_id || "";
        els.checkpointStage.value = body.checkpoint_stage || "";
        return body;
      }

      async function refreshCitations() {
        const jobId = currentJobId();
        if (!jobId) return;
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/citations`);
        state.lastCitations = Array.isArray(body.citations) ? body.citations : [];
        renderCitations(body.citations || []);
        renderCriticContextCitations();
        return body;
      }

      async function refreshExportPayload() {
        const jobId = currentJobId();
        if (!jobId) return;
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/export-payload`);
        setJson(els.exportPayloadJson, body);
        return body;
      }

      async function refreshVersions() {
        const jobId = currentJobId();
        if (!jobId) return;
        const q = buildVersionsQueryString();
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/versions${q}`);
        renderVersions(body.versions || []);
        return body;
      }

      async function refreshDiff() {
        const jobId = currentJobId();
        if (!jobId) return;
        persistUiState();
        const q = buildDiffQueryString();
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/diff${q}`);
        setJson(els.diffPre, body.diff_text || body);
        return body;
      }

      async function refreshEvents() {
        const jobId = currentJobId();
        if (!jobId) return;
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/events`);
        renderEvents(body.events || []);
        return body;
      }

      async function refreshCritic() {
        const jobId = currentJobId();
        if (!jobId) return;
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/critic`);
        state.lastCritic = body;
        renderCriticLists(body);
        setJson(els.criticJson, body);
        return body;
      }

      async function refreshComments() {
        const jobId = currentJobId();
        if (!jobId) return;
        persistUiState();
        const q = buildCommentsFilterQueryString();
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/comments${q}`);
        renderComments(body.comments || []);
        return body;
      }

      async function refreshReviewWorkflow() {
        const jobId = currentJobId();
        if (!jobId) return;
        persistUiState();
        const q = buildReviewWorkflowFilterQueryString();
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/review/workflow${q}`);
        renderReviewWorkflowTimeline(body);
        setJson(els.reviewWorkflowJson, body);
        return body;
      }

      async function refreshReviewWorkflowSla() {
        const jobId = currentJobId();
        if (!jobId) return;
        persistUiState();
        const params = new URLSearchParams();
        const overdueHours = Number.parseInt(String(els.reviewWorkflowOverdueHoursFilter.value || "").trim(), 10);
        if (Number.isFinite(overdueHours) && overdueHours > 0) {
          params.set("overdue_after_hours", String(overdueHours));
        }
        const q = params.toString();
        const body = await apiFetch(
          `/status/${encodeURIComponent(jobId)}/review/workflow/sla${q ? `?${q}` : ""}`
        );
        renderReviewWorkflowSla(body);
        setJson(els.reviewWorkflowSlaJson, body);
        return body;
      }

      async function refreshReviewWorkflowSlaProfile() {
        const jobId = currentJobId();
        if (!jobId) return;
        persistUiState();
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/review/workflow/sla/profile`);
        const findingProfile = body?.finding_sla_hours && typeof body.finding_sla_hours === "object" ? body.finding_sla_hours : {};
        if (findingProfile.high != null) els.reviewWorkflowSlaHighHours.value = String(findingProfile.high);
        if (findingProfile.medium != null) els.reviewWorkflowSlaMediumHours.value = String(findingProfile.medium);
        if (findingProfile.low != null) els.reviewWorkflowSlaLowHours.value = String(findingProfile.low);
        if (body?.default_comment_sla_hours != null) {
          els.reviewWorkflowSlaCommentDefaultHours.value = String(body.default_comment_sla_hours);
        }
        if (body?.source) {
          els.reviewWorkflowSlaUseSavedProfile.value = body.source === "saved" ? "true" : "false";
        }
        persistUiState();
        const updatedMarker = String(body?.saved_profile_updated_at || "-");
        if (els.reviewWorkflowSlaProfileSummaryLine) {
          els.reviewWorkflowSlaProfileSummaryLine.textContent = `profile: source=${String(body?.source || "-")} · updated=${updatedMarker}`;
        }
        setJson(els.reviewWorkflowSlaProfileJson, body);
        return body;
      }

      async function recomputeReviewWorkflowSla() {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        persistUiState();
        const parseHours = (value, fallback) => {
          const parsed = Number.parseInt(String(value || "").trim(), 10);
          if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
          return parsed;
        };
        const payload = {
          finding_sla_hours: {
            high: parseHours(els.reviewWorkflowSlaHighHours.value, 24),
            medium: parseHours(els.reviewWorkflowSlaMediumHours.value, 72),
            low: parseHours(els.reviewWorkflowSlaLowHours.value, 120),
          },
          default_comment_sla_hours: parseHours(els.reviewWorkflowSlaCommentDefaultHours.value, 72),
          use_saved_profile: String(els.reviewWorkflowSlaUseSavedProfile.value || "").toLowerCase() === "true",
        };
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/review/workflow/sla/recompute`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const slaPayload = body?.sla && typeof body.sla === "object" ? body.sla : {};
        renderReviewWorkflowSla(slaPayload);
        setJson(els.reviewWorkflowSlaJson, body);
        await Promise.allSettled([refreshReviewWorkflow(), refreshComments(), refreshCritic(), refreshReviewWorkflowSlaProfile()]);
        return body;
      }

      async function refreshMetrics() {
        const jobId = currentJobId();
        if (!jobId) return;
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/metrics`);
        renderMetricsCards(body);
        setJson(els.metricsJson, body);
        return body;
      }

      async function refreshQuality() {
        const jobId = currentJobId();
        if (!jobId) return;
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/quality`);
        renderQualityCards(body);
        setJson(els.qualityJson, body);
        return body;
      }

      function applyPortfolioDonorFilter(donorKey) {
        els.portfolioDonorFilter.value = donorKey || "";
        persistUiState();
        refreshPortfolioBundle().catch(showError);
      }

      function applyPortfolioStatusFilter(statusKey) {
        els.portfolioStatusFilter.value = statusKey || "";
        persistUiState();
        refreshPortfolioBundle().catch(showError);
      }

      function applyPortfolioHitlFilter(hitlValue) {
        els.portfolioHitlFilter.value = hitlValue || "";
        persistUiState();
        refreshPortfolioBundle().catch(showError);
      }

      function applyPortfolioWarningLevelFilter(warningLevelValue) {
        els.portfolioWarningLevelFilter.value = warningLevelValue || "";
        persistUiState();
        refreshPortfolioBundle().catch(showError);
      }

      function applyPortfolioGroundingRiskLevelFilter(groundingRiskLevelValue) {
        els.portfolioGroundingRiskLevelFilter.value = groundingRiskLevelValue || "";
        persistUiState();
        refreshPortfolioBundle().catch(showError);
      }

      function applyPortfolioFindingStatusFilter(findingStatusValue) {
        els.portfolioFindingStatusFilter.value = findingStatusValue || "";
        persistUiState();
        refreshPortfolioBundle().catch(showError);
      }

      function applyPortfolioFindingSeverityFilter(findingSeverityValue) {
        els.portfolioFindingSeverityFilter.value = findingSeverityValue || "";
        persistUiState();
        refreshPortfolioBundle().catch(showError);
      }

      function buildPortfolioFilterQueryString() {
        const params = new URLSearchParams();
        if (els.portfolioDonorFilter.value.trim()) params.set("donor_id", els.portfolioDonorFilter.value.trim());
        if (els.portfolioStatusFilter.value) params.set("status", els.portfolioStatusFilter.value);
        if (els.portfolioHitlFilter.value) params.set("hitl_enabled", els.portfolioHitlFilter.value);
        if (els.portfolioWarningLevelFilter.value) params.set("warning_level", els.portfolioWarningLevelFilter.value);
        if (els.portfolioGroundingRiskLevelFilter.value) {
          params.set("grounding_risk_level", els.portfolioGroundingRiskLevelFilter.value);
        }
        if (els.portfolioFindingStatusFilter.value) {
          params.set("finding_status", els.portfolioFindingStatusFilter.value);
        }
        if (els.portfolioFindingSeverityFilter.value) {
          params.set("finding_severity", els.portfolioFindingSeverityFilter.value);
        }
        const q = params.toString();
        return q ? `?${q}` : "";
      }

      function buildCommentsFilterQueryString() {
        const params = new URLSearchParams();
        if (els.commentsFilterSection.value) params.set("section", els.commentsFilterSection.value);
        if (els.commentsFilterStatus.value) params.set("status", els.commentsFilterStatus.value);
        if (els.commentsFilterVersionId.value.trim()) params.set("version_id", els.commentsFilterVersionId.value.trim());
        const q = params.toString();
        return q ? `?${q}` : "";
      }

      function buildReviewWorkflowFilterQueryString() {
        const params = new URLSearchParams();
        if (els.reviewWorkflowEventTypeFilter.value) params.set("event_type", els.reviewWorkflowEventTypeFilter.value);
        if (els.reviewWorkflowFindingIdFilter.value.trim()) {
          params.set("finding_id", els.reviewWorkflowFindingIdFilter.value.trim());
        }
        if (els.reviewWorkflowCommentStatusFilter.value) {
          params.set("comment_status", els.reviewWorkflowCommentStatusFilter.value);
        }
        if (els.reviewWorkflowStateFilter.value) {
          params.set("workflow_state", els.reviewWorkflowStateFilter.value);
        }
        const overdueHours = Number.parseInt(String(els.reviewWorkflowOverdueHoursFilter.value || "").trim(), 10);
        if (Number.isFinite(overdueHours) && overdueHours > 0) {
          params.set("overdue_after_hours", String(overdueHours));
        }
        const q = params.toString();
        return q ? `?${q}` : "";
      }

      function buildDiffQueryString() {
        const params = new URLSearchParams();
        if (els.diffSection.value) params.set("section", els.diffSection.value);
        if (els.fromVersionId.value.trim()) params.set("from_version_id", els.fromVersionId.value.trim());
        if (els.toVersionId.value.trim()) params.set("to_version_id", els.toVersionId.value.trim());
        const q = params.toString();
        return q ? `?${q}` : "";
      }

      function buildVersionsQueryString() {
        const section = String(els.diffSection.value || "").trim();
        return section ? `?section=${encodeURIComponent(section)}` : "";
      }

      async function refreshPortfolioMetrics() {
        persistUiState();
        const q = buildPortfolioFilterQueryString();
        const body = await apiFetch(`/portfolio/metrics${q}`);
        renderPortfolioMetricsCards(body);
        renderKeyValueList(
          els.portfolioStatusCountsList,
          body.status_counts,
          "No status counts yet.",
          8,
          (statusKey) => applyPortfolioStatusFilter(statusKey)
        );
        renderKeyValueList(
          els.portfolioDonorCountsList,
          body.donor_counts,
          "No donor counts yet.",
          8,
          (donorKey) => applyPortfolioDonorFilter(donorKey)
        );
        renderWarningLevelBreakdownList(
          els.portfolioMetricsWarningLevelsList,
          body.warning_level_job_counts || body.warning_level_counts || {},
          body.warning_level_job_rates || {},
          "No warning-level data yet.",
          (warningLevel) => applyPortfolioWarningLevelFilter(warningLevel)
        );
        renderWarningLevelBreakdownList(
          els.portfolioMetricsGroundingRiskLevelsList,
          body.grounding_risk_job_counts || body.grounding_risk_counts || {},
          body.grounding_risk_job_rates || {},
          "No grounding-risk data yet.",
          (groundingRiskLevel) => applyPortfolioGroundingRiskLevelFilter(groundingRiskLevel),
          ["high", "medium", "low", "unknown"]
        );
        setJson(els.portfolioMetricsJson, body);
        return body;
      }

      async function refreshPortfolioQuality() {
        persistUiState();
        const q = buildPortfolioFilterQueryString();
        const body = await apiFetch(`/portfolio/quality${q}`);
        renderPortfolioQualityCards(body);
        renderKeyValueList(els.portfolioQualityRiskList, body.donor_needs_revision_counts, "No donor revision risks yet.", 8);
        renderKeyValueList(
          els.portfolioQualityOpenFindingsList,
          body.donor_open_findings_counts,
          "No donor open findings yet.",
          8
        );
        renderWeightedBreakdownList(
          els.portfolioQualityPrioritySignalsList,
          body.priority_signal_breakdown,
          "No priority signals yet.",
          8
        );
        renderWeightedBreakdownList(
          els.portfolioQualityWeightedDonorsList,
          body.donor_weighted_risk_breakdown,
          "No weighted donor risk yet.",
          8,
          "weighted_score",
          (donorKey) => applyPortfolioDonorFilter(donorKey)
        );
        renderWarningLevelBreakdownList(
          els.portfolioQualityWarningLevelsList,
          body.warning_level_job_counts || body.warning_level_counts,
          body.warning_level_job_rates || {},
          "No warning-level data yet.",
          (warningLevel) => applyPortfolioWarningLevelFilter(warningLevel)
        );
        renderWarningLevelBreakdownList(
          els.portfolioQualityGroundingRiskLevelsList,
          body.grounding_risk_job_counts || body.grounding_risk_counts || {},
          body.grounding_risk_job_rates || {},
          "No grounding-risk level data yet.",
          (groundingRiskLevel) => applyPortfolioGroundingRiskLevelFilter(groundingRiskLevel),
          ["high", "medium", "low", "unknown"]
        );
        renderKeyValueList(
          els.portfolioQualityFindingStatusList,
          body.finding_status_counts,
          "No finding-status data yet.",
          8,
          (statusKey) => applyPortfolioFindingStatusFilter(statusKey)
        );
        renderKeyValueList(
          els.portfolioQualityFindingSeverityList,
          body.finding_severity_counts,
          "No finding-severity data yet.",
          8,
          (severityKey) => applyPortfolioFindingSeverityFilter(severityKey)
        );
        renderDonorGroundingRiskList(
          els.portfolioQualityGroundingRiskList,
          body.donor_grounding_risk_breakdown,
          "No donor grounding-risk data yet.",
          8,
          (donorId) => applyPortfolioDonorFilter(donorId)
        );
        setJson(els.portfolioQualityJson, body);
        return body;
      }

      async function refreshPortfolioBundle() {
        const results = await Promise.allSettled([refreshPortfolioMetrics(), refreshPortfolioQuality()]);
        const rejected = results.find((result) => result.status === "rejected");
        if (rejected && rejected.status === "rejected") {
          throw rejected.reason;
        }
        return results;
      }

      async function refreshAll() {
        const jobId = currentJobId();
        if (!jobId) {
          throw new Error("Set or generate a job_id first");
        }
        await refreshStatus();
        await Promise.allSettled([
          refreshMetrics(),
          refreshQuality(),
          refreshPortfolioBundle(),
          refreshCritic(),
          refreshCitations(),
          refreshExportPayload(),
          refreshVersions(),
          refreshDiff(),
          refreshEvents(),
          refreshComments(),
          refreshReviewWorkflow(),
          refreshReviewWorkflowSla(),
          refreshReviewWorkflowSlaProfile(),
        ]);
      }

      async function copyExportPayloadJson() {
        const current = (els.exportPayloadJson?.textContent || "").trim();
        if (!current || current === "{}") {
          await refreshExportPayload();
        }
        const text = (els.exportPayloadJson?.textContent || "").trim();
        if (!text || text === "{}") throw new Error("Load export payload first");
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(text);
      }

      async function ensurePortfolioQualityLoaded() {
        let text = (els.portfolioQualityJson?.textContent || "").trim();
        if (!text || text === "{}") {
          await refreshPortfolioQuality();
          text = (els.portfolioQualityJson?.textContent || "").trim();
        }
        if (!text || text === "{}") throw new Error("Load portfolio quality first");
        return text;
      }

      async function ensurePortfolioMetricsLoaded() {
        let text = (els.portfolioMetricsJson?.textContent || "").trim();
        if (!text || text === "{}") {
          await refreshPortfolioMetrics();
          text = (els.portfolioMetricsJson?.textContent || "").trim();
        }
        if (!text || text === "{}") throw new Error("Load portfolio metrics first");
        return text;
      }

      function downloadBlob(blob, filename) {
        const objectUrl = URL.createObjectURL(blob);
        try {
          const a = document.createElement("a");
          a.href = objectUrl;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
        } finally {
          setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        }
      }

      function parseDownloadFilenameFromDisposition(contentDisposition, fallbackFilename) {
        const raw = String(contentDisposition || "");
        const filenameStarMatch = raw.match(/filename\\*=UTF-8''([^;]+)/i);
        if (filenameStarMatch && filenameStarMatch[1]) {
          try {
            return decodeURIComponent(String(filenameStarMatch[1]).trim());
          } catch (_err) {
            return String(filenameStarMatch[1]).trim();
          }
        }
        const filenameMatch = raw.match(/filename=\"?([^\";]+)\"?/i);
        if (filenameMatch && filenameMatch[1]) return String(filenameMatch[1]).trim();
        return fallbackFilename;
      }

      async function exportPortfolioAggregate(endpointPath, format, fallbackFilename) {
        persistUiState();
        persistBasics();
        const q = buildPortfolioFilterQueryString();
        const params = new URLSearchParams(q.startsWith("?") ? q.slice(1) : "");
        params.set("format", format);
        if (exportGzipEnabled()) params.set("gzip", "true");
        const query = params.toString();
        const res = await fetch(`${apiBase()}${endpointPath}?${query}`, {
          headers: { ...headers() },
        });
        if (!res.ok) {
          const ct = res.headers.get("content-type") || "";
          if (ct.includes("application/json")) {
            const body = await res.json();
            throw new Error(JSON.stringify(body, null, 2));
          }
          throw new Error(await res.text());
        }
        const filename = parseDownloadFilenameFromDisposition(
          res.headers.get("content-disposition"),
          fallbackFilename
        );
        const blob = await res.blob();
        downloadBlob(blob, filename);
      }

      async function exportReviewWorkflowAggregate(format) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        persistUiState();
        persistBasics();
        const q = buildReviewWorkflowFilterQueryString();
        const params = new URLSearchParams(q.startsWith("?") ? q.slice(1) : "");
        params.set("format", format);
        if (exportGzipEnabled()) params.set("gzip", "true");
        const query = params.toString();
        const endpointPath = `/status/${encodeURIComponent(jobId)}/review/workflow/export`;
        const res = await fetch(`${apiBase()}${endpointPath}?${query}`, {
          headers: { ...headers() },
        });
        if (!res.ok) {
          const ct = res.headers.get("content-type") || "";
          if (ct.includes("application/json")) {
            const body = await res.json();
            throw new Error(JSON.stringify(body, null, 2));
          }
          throw new Error(await res.text());
        }
        const fallbackFilename = `grantflow_review_workflow_${jobId}.${format}${exportGzipEnabled() ? ".gz" : ""}`;
        const filename = parseDownloadFilenameFromDisposition(
          res.headers.get("content-disposition"),
          fallbackFilename
        );
        const blob = await res.blob();
        downloadBlob(blob, filename);
      }

      async function copyPortfolioMetricsJson() {
        const text = await ensurePortfolioMetricsLoaded();
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(text);
      }

      function currentInventoryDonorIdForExport() {
        const ingestDonor = String(els.ingestDonorId?.value || "").trim();
        if (ingestDonor) return ingestDonor;
        const portfolioDonor = String(els.portfolioDonorFilter?.value || "").trim();
        if (portfolioDonor) return portfolioDonor;
        const generateDonor = String(els.donorId?.value || "").trim();
        if (generateDonor) return generateDonor;
        return "";
      }

      async function exportIngestInventory(format) {
        const donorId = currentInventoryDonorIdForExport();
        if (!donorId) throw new Error("Missing donor_id for inventory export");
        persistUiState();
        persistBasics();
        const query = new URLSearchParams({ donor_id: donorId, format });
        if (exportGzipEnabled()) query.set("gzip", "true");
        const res = await fetch(`${apiBase()}/ingest/inventory/export?${query.toString()}`, {
          headers: { ...headers() },
        });
        if (!res.ok) {
          throw new Error(await res.text());
        }
        const fallbackFilename = `grantflow_ingest_inventory_${donorId}.${format}${exportGzipEnabled() ? ".gz" : ""}`;
        const filename = parseDownloadFilenameFromDisposition(
          res.headers.get("content-disposition"),
          fallbackFilename
        );
        const blob = await res.blob();
        downloadBlob(blob, filename);
      }

      async function copyPortfolioQualityJson() {
        const text = await ensurePortfolioQualityLoaded();
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(text);
      }

      async function ensureIngestInventoryLoaded() {
        let text = (els.ingestInventoryJson?.textContent || "").trim();
        if (!text || text === "{}" || text === "No ingest inventory loaded yet.") {
          await syncIngestChecklistFromServer();
          text = (els.ingestInventoryJson?.textContent || "").trim();
        }
        if (!text || text === "No ingest inventory loaded yet.") {
          throw new Error("Load ingest inventory first");
        }
        return text;
      }

      async function copyIngestInventoryJson() {
        const text = await ensureIngestInventoryLoaded();
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(text);
      }

      async function downloadIngestInventoryJson() {
        await exportIngestInventory("json");
      }

      async function downloadIngestInventoryCsv() {
        await exportIngestInventory("csv");
      }

      async function downloadPortfolioQualityJson() {
        await ensurePortfolioQualityLoaded();
        await exportPortfolioAggregate("/portfolio/quality/export", "json", "grantflow_portfolio_quality.json");
      }

      async function downloadPortfolioQualityCsv() {
        await ensurePortfolioQualityLoaded();
        await exportPortfolioAggregate("/portfolio/quality/export", "csv", "grantflow_portfolio_quality.csv");
      }

      async function downloadPortfolioMetricsJson() {
        await ensurePortfolioMetricsLoaded();
        await exportPortfolioAggregate("/portfolio/metrics/export", "json", "grantflow_portfolio_metrics.json");
      }

      async function downloadPortfolioMetricsCsv() {
        await ensurePortfolioMetricsLoaded();
        await exportPortfolioAggregate("/portfolio/metrics/export", "csv", "grantflow_portfolio_metrics.csv");
      }

      async function downloadReviewWorkflowJson() {
        await refreshReviewWorkflow();
        await exportReviewWorkflowAggregate("json");
      }

      async function downloadReviewWorkflowCsv() {
        await refreshReviewWorkflow();
        await exportReviewWorkflowAggregate("csv");
      }

      async function exportZipFromPayload() {
        let currentText = (els.exportPayloadJson?.textContent || "").trim();
        if (!currentText || currentText === "{}") {
          await refreshExportPayload();
          currentText = (els.exportPayloadJson?.textContent || "").trim();
        }
        if (!currentText || currentText === "{}") throw new Error("Load export payload first");

        let parsed;
        try {
          parsed = JSON.parse(currentText);
        } catch (err) {
          throw new Error("Export payload JSON is invalid");
        }
        if (!parsed || typeof parsed !== "object" || !parsed.payload) {
          throw new Error("Export payload response is missing payload");
        }

        persistBasics();
        const res = await fetch(`${apiBase()}/export`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...headers() },
          body: JSON.stringify({ payload: parsed.payload, format: "both" }),
        });
        if (!res.ok) {
          const ct = res.headers.get("content-type") || "";
          let errText = "";
          if (ct.includes("application/json")) {
            const body = await res.json();
            errText = JSON.stringify(body, null, 2);
          } else {
            errText = await res.text();
          }
          throw new Error(errText || `Export failed (${res.status})`);
        }

        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        try {
          const a = document.createElement("a");
          a.href = objectUrl;
          a.download = "grantflow_export.zip";
          document.body.appendChild(a);
          a.click();
          a.remove();
        } finally {
          setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        }
      }

      async function approveOrReject(approved) {
        const checkpointId = els.checkpointId.value.trim();
        if (!checkpointId) throw new Error("No checkpoint_id in current status");
        const body = {
          checkpoint_id: checkpointId,
          approved,
          feedback: els.hitlFeedback.value.trim() || undefined,
        };
        await apiFetch("/hitl/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        await refreshAll();
      }

      async function resumeJob() {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        await apiFetch(`/resume/${encodeURIComponent(jobId)}`, { method: "POST" });
        await refreshAll();
      }

      async function cancelJob() {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        await apiFetch(`/cancel/${encodeURIComponent(jobId)}`, { method: "POST" });
        await refreshAll();
      }

      async function loadPendingList() {
        const body = await apiFetch("/hitl/pending");
        setJson(els.statusJson, { pending_only: body });
      }

      async function addComment() {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        const message = els.commentMessage.value.trim();
        if (!message) throw new Error("Comment message is required");
        const body = {
          section: els.commentSection.value || "general",
          message,
        };
        if (els.commentAuthor.value.trim()) body.author = els.commentAuthor.value.trim();
        if (els.commentVersionId.value.trim()) body.version_id = els.commentVersionId.value.trim();
        if (els.linkedFindingId.value.trim()) body.linked_finding_id = els.linkedFindingId.value.trim();
        const created = await apiFetch(`/status/${encodeURIComponent(jobId)}/comments`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        els.selectedCommentId.value = created.comment_id || "";
        els.commentMessage.value = "";
        persistUiState();
        await Promise.allSettled([refreshComments(), refreshReviewWorkflow()]);
        return created;
      }

      async function setFindingStatus(findingId, nextStatus) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        if (!findingId) throw new Error("No finding_id");
        const actionByStatus = {
          acknowledged: "ack",
          resolved: "resolve",
          open: "open",
        };
        const action = actionByStatus[nextStatus];
        if (!action) throw new Error(`Unsupported finding status: ${String(nextStatus)}`);
        const updated = await apiFetch(
          `/status/${encodeURIComponent(jobId)}/critic/findings/${encodeURIComponent(findingId)}/${action}`,
          { method: "POST" }
        );
        await Promise.allSettled([refreshCritic(), refreshReviewWorkflow()]);
        return updated;
      }

      async function applyCriticBulkStatus() {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        const nextStatus = String(els.criticBulkTargetStatus.value || "").trim();
        if (!nextStatus) throw new Error("Select bulk target status");
        const scope = String(els.criticBulkScope.value || "filtered").trim().toLowerCase();

        const payload = { next_status: nextStatus };
        if (scope === "all") {
          payload.apply_to_all = true;
        } else {
          const section = String(els.criticSectionFilter.value || "").trim();
          const severity = String(els.criticSeverityFilter.value || "").trim();
          const findingStatus = String(els.criticFindingStatusFilter.value || "").trim();
          if (section) payload.section = section;
          if (severity) payload.severity = severity;
          if (findingStatus) payload.finding_status = findingStatus;
          if (!payload.section && !payload.severity && !payload.finding_status) {
            throw new Error("For filtered bulk apply, set at least one critic filter or use scope=all");
          }
        }

        const result = await apiFetch(`/status/${encodeURIComponent(jobId)}/critic/findings/bulk-status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        setJson(els.criticBulkResultJson, result);
        await Promise.allSettled([refreshCritic(), refreshReviewWorkflow()]);
        return result;
      }

      async function setCommentStatus(nextStatus) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        const commentId = els.selectedCommentId.value.trim();
        if (!commentId) throw new Error("Select a comment first");
        const action = nextStatus === "resolved" ? "resolve" : "reopen";
        const updated = await apiFetch(
          `/status/${encodeURIComponent(jobId)}/comments/${encodeURIComponent(commentId)}/${action}`,
          { method: "POST" }
        );
        await Promise.allSettled([refreshComments(), refreshReviewWorkflow()]);
        return updated;
      }

      function togglePolling() {
        state.polling = !state.polling;
        els.pollToggleBtn.textContent = state.polling ? "Stop Poll" : "Start Poll";
        if (state.polling) {
          state.pollTimer = setInterval(() => {
            if (!currentJobId()) return;
            refreshAll().catch(showError);
          }, 3000);
          refreshAll().catch(showError);
        } else if (state.pollTimer) {
          clearInterval(state.pollTimer);
          state.pollTimer = null;
        }
      }

      function showError(err) {
        const msg = err instanceof Error ? err.message : String(err);
        setJson(els.statusJson, { error: msg });
      }

      function bind() {
        els.generateBtn.addEventListener("click", () => generateJob().catch(showError));
        els.applyPresetBtn.addEventListener("click", applyGeneratePreset);
        els.clearPresetContextBtn.addEventListener("click", clearGeneratePresetContext);
        els.ingestBtn.addEventListener("click", () => ingestPdfUpload().catch(showError));
        els.applyIngestPresetBtn.addEventListener("click", applyIngestPreset);
        els.syncIngestDonorBtn.addEventListener("click", syncIngestDonorFromGenerate);
        els.syncIngestChecklistServerBtn.addEventListener("click", () => syncIngestChecklistFromServer().catch(showError));
        els.resetIngestChecklistBtn.addEventListener("click", resetIngestChecklistProgressForCurrentPreset);
        els.copyIngestInventoryJsonBtn.addEventListener("click", () =>
          copyIngestInventoryJson().catch((err) => showError(err))
        );
        els.downloadIngestInventoryJsonBtn.addEventListener("click", () =>
          downloadIngestInventoryJson().catch((err) => showError(err))
        );
        els.downloadIngestInventoryCsvBtn.addEventListener("click", () =>
          downloadIngestInventoryCsv().catch((err) => showError(err))
        );
        els.refreshAllBtn.addEventListener("click", () => refreshAll().catch(showError));
        els.pollToggleBtn.addEventListener("click", togglePolling);
        els.clearFiltersBtn.addEventListener("click", () => clearDemoFilters().catch(showError));
        els.skipZeroReadinessWarningCheckbox.addEventListener("change", () => {
          const presetKey = String(els.generatePresetSelect.value || "").trim();
          if (!presetKey) return;
          if (!state.zeroReadinessWarningPrefs || typeof state.zeroReadinessWarningPrefs !== "object") {
            state.zeroReadinessWarningPrefs = {};
          }
          state.zeroReadinessWarningPrefs[presetKey] = Boolean(els.skipZeroReadinessWarningCheckbox.checked);
          persistZeroReadinessWarningPrefs();
          renderZeroReadinessWarningPreference();
        });
        els.syncGenerateReadinessBtn.addEventListener("click", () =>
          syncGeneratePresetReadinessNow().catch((err) => showError(err))
        );
        els.approveBtn.addEventListener("click", () => approveOrReject(true).catch(showError));
        els.rejectBtn.addEventListener("click", () => approveOrReject(false).catch(showError));
        els.resumeBtn.addEventListener("click", () => resumeJob().catch(showError));
        els.cancelBtn.addEventListener("click", () => cancelJob().catch(showError));
        els.versionsBtn.addEventListener("click", () => refreshVersions().catch(showError));
        els.diffBtn.addEventListener("click", () => refreshDiff().catch(showError));
        els.citationsBtn.addEventListener("click", () => refreshCitations().catch(showError));
        els.exportPayloadBtn.addEventListener("click", () => refreshExportPayload().catch(showError));
        els.copyExportPayloadBtn.addEventListener("click", () =>
          copyExportPayloadJson().catch((err) => showError(err))
        );
        els.exportZipFromPayloadBtn.addEventListener("click", () =>
          exportZipFromPayload().catch((err) => showError(err))
        );
        els.eventsBtn.addEventListener("click", () => refreshEvents().catch(showError));
        els.criticBtn.addEventListener("click", () => refreshCritic().catch(showError));
        els.criticBulkApplyBtn.addEventListener("click", () => applyCriticBulkStatus().catch(showError));
        els.criticBulkClearFiltersBtn.addEventListener("click", () => {
          clearCriticFilters();
          if (state.lastCritic) renderCriticLists(state.lastCritic);
          else refreshCritic().catch(showError);
        });
        els.qualityBtn.addEventListener("click", () => refreshQuality().catch(showError));
        els.portfolioBtn.addEventListener("click", () => {
          refreshPortfolioBundle().catch(showError);
        });
        els.portfolioClearBtn.addEventListener("click", () => {
          clearPortfolioFilters();
          refreshPortfolioBundle().catch(showError);
        });
        els.copyPortfolioMetricsJsonBtn.addEventListener("click", () =>
          copyPortfolioMetricsJson().catch((err) => showError(err))
        );
        els.downloadPortfolioMetricsJsonBtn.addEventListener("click", () =>
          downloadPortfolioMetricsJson().catch((err) => showError(err))
        );
        els.downloadPortfolioMetricsCsvBtn.addEventListener("click", () =>
          downloadPortfolioMetricsCsv().catch((err) => showError(err))
        );
        els.exportInventoryJsonBtn.addEventListener("click", () =>
          exportIngestInventory("json").catch((err) => showError(err))
        );
        els.exportInventoryCsvBtn.addEventListener("click", () =>
          exportIngestInventory("csv").catch((err) => showError(err))
        );
        els.exportPortfolioMetricsJsonBtn.addEventListener("click", () =>
          downloadPortfolioMetricsJson().catch((err) => showError(err))
        );
        els.exportPortfolioMetricsCsvBtn.addEventListener("click", () =>
          downloadPortfolioMetricsCsv().catch((err) => showError(err))
        );
        els.exportPortfolioQualityJsonBtn.addEventListener("click", () =>
          downloadPortfolioQualityJson().catch((err) => showError(err))
        );
        els.exportPortfolioQualityCsvBtn.addEventListener("click", () =>
          downloadPortfolioQualityCsv().catch((err) => showError(err))
        );
        els.copyPortfolioQualityJsonBtn.addEventListener("click", () =>
          copyPortfolioQualityJson().catch((err) => showError(err))
        );
        els.downloadPortfolioQualityJsonBtn.addEventListener("click", () =>
          downloadPortfolioQualityJson().catch((err) => showError(err))
        );
        els.downloadPortfolioQualityCsvBtn.addEventListener("click", () =>
          downloadPortfolioQualityCsv().catch((err) => showError(err))
        );
        els.commentsBtn.addEventListener("click", () => refreshComments().catch(showError));
        els.reviewWorkflowBtn.addEventListener("click", () => {
          Promise.allSettled([refreshReviewWorkflow(), refreshReviewWorkflowSla(), refreshReviewWorkflowSlaProfile()]).catch(showError);
        });
        els.reviewWorkflowSlaBtn.addEventListener("click", () => refreshReviewWorkflowSla().catch(showError));
        els.reviewWorkflowSlaProfileBtn.addEventListener("click", () => refreshReviewWorkflowSlaProfile().catch(showError));
        els.reviewWorkflowSlaRecomputeBtn.addEventListener("click", () => recomputeReviewWorkflowSla().catch(showError));
        els.reviewWorkflowClearFiltersBtn.addEventListener("click", () => {
          clearReviewWorkflowFilters();
          Promise.allSettled([refreshReviewWorkflow(), refreshReviewWorkflowSla(), refreshReviewWorkflowSlaProfile()]).catch(showError);
        });
        els.reviewWorkflowExportJsonBtn.addEventListener("click", () =>
          downloadReviewWorkflowJson().catch((err) => showError(err))
        );
        els.reviewWorkflowExportCsvBtn.addEventListener("click", () =>
          downloadReviewWorkflowCsv().catch((err) => showError(err))
        );
        els.addCommentBtn.addEventListener("click", () => addComment().catch(showError));
        els.resolveCommentBtn.addEventListener("click", () => setCommentStatus("resolved").catch(showError));
        els.reopenCommentBtn.addEventListener("click", () => setCommentStatus("open").catch(showError));
        els.clearLinkedFindingBtn.addEventListener("click", clearLinkedFindingSelection);
        els.openPendingBtn.addEventListener("click", () => loadPendingList().catch(showError));
        [els.apiBase, els.apiKey, els.jobIdInput].forEach((el) => el.addEventListener("change", persistBasics));
        [els.diffSection, els.fromVersionId, els.toVersionId].forEach((el) => el.addEventListener("change", persistUiState));
        els.portfolioStatusFilter.addEventListener("change", () => {
          applyPortfolioStatusFilter(els.portfolioStatusFilter.value);
        });
        els.portfolioHitlFilter.addEventListener("change", () => {
          applyPortfolioHitlFilter(els.portfolioHitlFilter.value);
        });
        els.portfolioWarningLevelFilter.addEventListener("change", () => {
          applyPortfolioWarningLevelFilter(els.portfolioWarningLevelFilter.value);
        });
        els.portfolioGroundingRiskLevelFilter.addEventListener("change", () => {
          applyPortfolioGroundingRiskLevelFilter(els.portfolioGroundingRiskLevelFilter.value);
        });
        els.portfolioFindingStatusFilter.addEventListener("change", () => {
          applyPortfolioFindingStatusFilter(els.portfolioFindingStatusFilter.value);
        });
        els.portfolioFindingSeverityFilter.addEventListener("change", () => {
          applyPortfolioFindingSeverityFilter(els.portfolioFindingSeverityFilter.value);
        });
        els.portfolioDonorFilter.addEventListener("change", () => {
          persistUiState();
          refreshPortfolioBundle().catch(showError);
        });
        [els.commentsFilterSection, els.commentsFilterStatus].forEach((el) =>
          el.addEventListener("change", () => {
            persistUiState();
            refreshComments().catch(showError);
          })
        );
        [els.reviewWorkflowEventTypeFilter, els.reviewWorkflowCommentStatusFilter, els.reviewWorkflowStateFilter].forEach((el) =>
          el.addEventListener("change", () => {
            persistUiState();
            refreshReviewWorkflow().catch(showError);
          })
        );
        els.reviewWorkflowFindingIdFilter.addEventListener("change", () => {
          persistUiState();
          refreshReviewWorkflow().catch(showError);
        });
        els.reviewWorkflowOverdueHoursFilter.addEventListener("change", () => {
          persistUiState();
          Promise.allSettled([refreshReviewWorkflow(), refreshReviewWorkflowSla()]).catch(showError);
        });
        [
          els.reviewWorkflowSlaHighHours,
          els.reviewWorkflowSlaMediumHours,
          els.reviewWorkflowSlaLowHours,
          els.reviewWorkflowSlaCommentDefaultHours,
          els.reviewWorkflowSlaUseSavedProfile,
        ].forEach((el) =>
          el.addEventListener("change", () => {
            persistUiState();
          })
        );
        els.commentsFilterVersionId.addEventListener("change", () => {
          persistUiState();
          refreshComments().catch(showError);
        });
        els.criticSectionFilter.addEventListener("change", () => {
          persistUiState();
          if (state.lastCritic) renderCriticLists(state.lastCritic);
          else refreshCritic().catch(showError);
        });
        els.criticSeverityFilter.addEventListener("change", () => {
          persistUiState();
          if (state.lastCritic) renderCriticLists(state.lastCritic);
          else refreshCritic().catch(showError);
        });
        els.criticFindingStatusFilter.addEventListener("change", () => {
          persistUiState();
          if (state.lastCritic) renderCriticLists(state.lastCritic);
          else refreshCritic().catch(showError);
        });
        els.criticCitationConfidenceFilter.addEventListener("change", () => {
          persistUiState();
          renderCriticContextCitations();
        });
        els.generatePresetSelect.addEventListener("change", () => {
          persistUiState();
          renderGeneratePresetReadiness();
          renderZeroReadinessWarningPreference();
        });
        els.exportGzipEnabled.addEventListener("change", persistUiState);
        els.inputContextJson.addEventListener("change", persistUiState);
        els.ingestPresetSelect.addEventListener("change", () => {
          persistUiState();
          renderIngestPresetGuidance();
          renderIngestChecklistProgress();
          syncIngestChecklistFromServer().catch(() => {});
        });
        els.ingestDonorId.addEventListener("change", persistUiState);
        els.ingestMetadataJson.addEventListener("change", persistUiState);
      }

      initDefaults();
      bind();
      if (currentJobId()) {
        refreshAll().catch(() => {});
      } else {
        setStatusPill("idle");
      }
    })();
  </script>
</body>
</html>
"""
