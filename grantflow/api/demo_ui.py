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
              <div class="kpi"><div class="label">Grounding risk</div><div class="value mono">-</div></div>
            </div>
            <div style="margin-top:10px;">
              <pre id="metricsJson">{}</pre>
            </div>
          </div>
        </div>

        <div class="card">
          <h2>Worker Heartbeat</h2>
          <div class="body">
            <div class="row3">
              <button id="workerHeartbeatBtn" class="ghost">Load Worker Heartbeat</button>
              <div>
                <label for="workerHeartbeatPollSeconds">HB Poll Interval (sec)</label>
                <select id="workerHeartbeatPollSeconds">
                  <option value="5">5</option>
                  <option value="10" selected>10</option>
                  <option value="15">15</option>
                  <option value="30">30</option>
                </select>
              </div>
              <button id="workerHeartbeatPollToggleBtn" class="secondary">Stop HB Poll</button>
            </div>
            <div class="row" style="margin-top:10px;">
              <div id="workerHeartbeatPill" class="pill status-unknown">
                <span class="dot"></span><span id="workerHeartbeatPillText">policy=- · healthy=-</span>
              </div>
            </div>
            <div id="workerHeartbeatMetaLine" class="footer-note mono">consumer_enabled=- · source=- · age=-</div>
            <div style="margin-top:10px;">
              <pre id="workerHeartbeatJson">{}</pre>
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
              <div class="kpi"><div class="label">MEL claim-support</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">MEL fallback</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Preflight risk</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Strict preflight</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Grounded gate</div><div class="value mono">-</div></div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div id="qualityGroundedGatePill" class="pill readiness-level-none">
                <span class="dot"></span><span>gate=unknown</span>
              </div>
              <button id="qualityGroundedGateExplainBtn" class="ghost">Why blocked?</button>
            </div>
            <div id="qualityGroundedGateReasonsWrap" style="margin-top:10px;" class="hidden">
              <label>Grounded Gate Evidence</label>
              <div class="list" id="qualityGroundedGateReasonsList"></div>
            </div>
            <div id="qualityPreflightMetaLine" class="footer-note mono">warning_count=- · coverage_rate=-</div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>MEL Generation</label>
                <div class="list" id="qualityMelSummaryList"></div>
              </div>
            </div>
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
          <h2>Grounding KPI</h2>
          <div class="body">
            <div class="sub">Grounding posture from citations, traceability, and preflight policy.</div>
            <div class="kpis" id="groundingKpiCards" style="margin-top:10px;">
              <div class="kpi"><div class="label">Grounding risk</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Preflight grounding</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Policy mode</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Policy blocking</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Citation count</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Fallback rate</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Traceability complete</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Traceability gap</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Architect claim-support</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Architect threshold hit</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">MEL claim-support</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">MEL fallback</div><div class="value mono">-</div></div>
            </div>
            <div id="groundingKpiMetaLine" class="footer-note mono">citation_count=- · non_retrieval=- · retrieval_grounded=- · traceability_gap=-</div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Grounding Counts</label>
                <div class="list" id="groundingKpiCountsList"></div>
              </div>
              <div>
                <label>Grounding Policy Reasons</label>
                <div class="list" id="groundingKpiPolicyReasonsList"></div>
              </div>
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
            <div class="row4" style="margin-top:10px;">
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
              <div>
                <label for="portfolioToCTextRiskLevelFilter">ToC Text Risk</label>
                <select id="portfolioToCTextRiskLevelFilter">
                  <option value="">all</option>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                  <option value="unknown">unknown</option>
                </select>
              </div>
            </div>
            <div class="row4" style="margin-top:10px;">
              <div>
                <label for="portfolioMelRiskLevelFilter">MEL Risk</label>
                <select id="portfolioMelRiskLevelFilter">
                  <option value="">all</option>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                  <option value="unknown">unknown</option>
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
              <div class="kpi"><div class="label">% High ToC-text Risk</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">ToC Text Issues</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">% Grounded Gate Block</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Grounded Gate Blocks</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">% Grounded Gate Pass (present)</div><div class="value mono">-</div></div>
            </div>
            <div id="portfolioWarningMetaLine" class="footer-note mono">high=- · medium=- · low=- · none=- · total=-</div>
            <div class="row" style="margin-top:8px;">
              <button id="clearPortfolioToCTextRiskBtn" class="ghost">Clear ToC Risk Filter</button>
              <div class="sub" style="align-self:center;">Quick reset for only <code>toc_text_risk_level</code>.</div>
            </div>
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
            <div class="row4" style="margin-top:10px;">
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowJsonBtn" class="ghost">Workflow JSON</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowCsvBtn" class="ghost">Workflow CSV</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowTrendsJsonBtn" class="ghost">Workflow Trends JSON</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowTrendsCsvBtn" class="ghost">Workflow Trends CSV</button>
              </div>
            </div>
            <div class="row4" style="margin-top:10px;">
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowSlaJsonBtn" class="ghost">Workflow SLA JSON</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowSlaCsvBtn" class="ghost">Workflow SLA CSV</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowSlaTrendsJsonBtn" class="ghost">Workflow SLA Trends JSON</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowSlaTrendsCsvBtn" class="ghost">Workflow SLA Trends CSV</button>
              </div>
            </div>
            <div class="row4" style="margin-top:10px;">
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowSlaHotspotsJsonBtn" class="ghost">SLA Hotspots JSON</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowSlaHotspotsCsvBtn" class="ghost">SLA Hotspots CSV</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn" class="ghost">SLA Hotspots Trends JSON</button>
              </div>
              <div style="align-self:end;">
                <button id="exportPortfolioReviewWorkflowSlaHotspotsTrendsCsvBtn" class="ghost">SLA Hotspots Trends CSV</button>
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
                <label>Portfolio MEL Summary</label>
                <div class="list" id="portfolioQualityMelSummaryList"></div>
              </div>
              <div></div>
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
                <label>ToC Text Risk Levels</label>
                <div class="list" id="portfolioQualityToCTextRiskList"></div>
              </div>
              <div></div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label>Top Donors (Grounding Risk)</label>
                <div class="list" id="portfolioQualityGroundingRiskList"></div>
              </div>
              <div></div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <div>
                <label>Grounded Gate Failed Sections</label>
                <div class="list" id="portfolioQualityGroundedGateSectionsList"></div>
              </div>
              <div>
                <label>Grounded Gate Reason Codes</label>
                <div class="list" id="portfolioQualityGroundedGateReasonsList"></div>
              </div>
              <div>
                <label>Top Donors (Grounded Gate Blocks)</label>
                <div class="list" id="portfolioQualityGroundedGateDonorsList"></div>
              </div>
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
            <div style="margin-top:14px;">
              <label>Portfolio Review Workflow Snapshot</label>
              <div class="sub" style="margin-top:4px;">Current workflow backlog, status mix, and latest timeline events across filtered jobs.</div>
            </div>
            <div class="row" style="margin-top:10px;">
              <button id="portfolioReviewWorkflowBtn" class="ghost">Load Portfolio Workflow</button>
              <button id="copyPortfolioReviewWorkflowJsonBtn" class="ghost">Copy Workflow JSON</button>
              <button id="downloadPortfolioReviewWorkflowJsonBtn" class="ghost">Export Workflow JSON</button>
              <button id="downloadPortfolioReviewWorkflowCsvBtn" class="secondary">Export Workflow CSV</button>
            </div>
            <div id="portfolioReviewWorkflowSummaryLine" class="footer-note mono">portfolio workflow: findings=- · comments=- · overdue=- · events=- · active_jobs=-/-</div>
            <div id="portfolioReviewWorkflowPolicyLine" class="footer-note mono">portfolio policy: status=- · go/no-go=- · send_class=- · next=-</div>
            <div class="list" id="portfolioReviewWorkflowList" style="margin-top:10px;"></div>
            <div style="margin-top:10px;">
              <pre id="portfolioReviewWorkflowJson">{}</pre>
            </div>
            <div style="margin-top:14px;">
              <label>Portfolio Review Workflow SLA Snapshot</label>
              <div class="sub" style="margin-top:4px;">Aggregated overdue backlog and hotspot rows for filtered portfolio review workflow.</div>
            </div>
            <div class="row" style="margin-top:10px;">
              <button id="portfolioReviewWorkflowSlaBtn" class="ghost">Load Portfolio Workflow SLA</button>
              <button id="copyPortfolioReviewWorkflowSlaJsonBtn" class="ghost">Copy Workflow SLA JSON</button>
              <button id="downloadPortfolioReviewWorkflowSlaJsonBtn" class="ghost">Export Workflow SLA JSON</button>
              <button id="downloadPortfolioReviewWorkflowSlaCsvBtn" class="secondary">Export Workflow SLA CSV</button>
            </div>
            <div id="portfolioReviewWorkflowSlaSummaryLine" class="footer-note mono">portfolio workflow sla: overdue=- · breach=- · top_donor=- · active_jobs=-/-</div>
            <div class="list" id="portfolioReviewWorkflowSlaList" style="margin-top:10px;"></div>
            <div style="margin-top:10px;">
              <pre id="portfolioReviewWorkflowSlaJson">{}</pre>
            </div>
            <div style="margin-top:14px;">
              <label>Portfolio SLA Hotspots Triage</label>
              <div class="sub" style="margin-top:4px;">Focused hotspot queue for reviewers with optional kind/severity/min-overdue filters.</div>
            </div>
            <div class="row4" style="margin-top:10px;">
              <div>
                <label for="portfolioSlaHotspotKindFilter">Hotspot Kind</label>
                <select id="portfolioSlaHotspotKindFilter">
                  <option value="">all</option>
                  <option value="finding">finding</option>
                  <option value="comment">comment</option>
                </select>
              </div>
              <div>
                <label for="portfolioSlaHotspotSeverityFilter">Hotspot Severity</label>
                <select id="portfolioSlaHotspotSeverityFilter">
                  <option value="">all</option>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                  <option value="unknown">unknown</option>
                </select>
              </div>
              <div>
                <label for="portfolioSlaMinOverdueHoursFilter">Min Overdue (hours)</label>
                <input id="portfolioSlaMinOverdueHoursFilter" type="number" min="0" step="0.5" value="" placeholder="0.0" />
              </div>
              <div>
                <label for="portfolioSlaTopLimitFilter">Top Limit</label>
                <input id="portfolioSlaTopLimitFilter" type="number" min="1" step="1" value="10" />
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <button id="portfolioReviewWorkflowSlaHotspotsBtn" class="ghost">Load Portfolio SLA Hotspots</button>
              <button id="copyPortfolioReviewWorkflowSlaHotspotsJsonBtn" class="ghost">Copy SLA Hotspots JSON</button>
              <button id="downloadPortfolioReviewWorkflowSlaHotspotsJsonBtn" class="ghost">Export SLA Hotspots JSON</button>
              <button id="downloadPortfolioReviewWorkflowSlaHotspotsCsvBtn" class="secondary">Export SLA Hotspots CSV</button>
            </div>
            <div id="portfolioReviewWorkflowSlaHotspotsSummaryLine" class="footer-note mono">portfolio sla hotspots: shown=-/- · max_overdue=- · avg_overdue=- · top_donor=-</div>
            <div class="list" id="portfolioReviewWorkflowSlaHotspotsList" style="margin-top:10px;"></div>
            <div style="margin-top:10px;">
              <pre id="portfolioReviewWorkflowSlaHotspotsJson">{}</pre>
            </div>
            <div style="margin-top:14px;">
              <label>Portfolio SLA Hotspots Trends</label>
              <div class="sub" style="margin-top:4px;">Trend buckets for filtered hotspot triage queue.</div>
            </div>
            <div class="row" style="margin-top:10px;">
              <button id="portfolioReviewWorkflowSlaHotspotsTrendsBtn" class="ghost">Load Portfolio SLA Hotspots Trends</button>
              <button id="copyPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn" class="ghost">Copy SLA Hotspots Trends JSON</button>
              <button id="downloadPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn" class="ghost">Export SLA Hotspots Trends JSON</button>
              <button id="downloadPortfolioReviewWorkflowSlaHotspotsTrendsCsvBtn" class="secondary">Export SLA Hotspots Trends CSV</button>
            </div>
            <div id="portfolioReviewWorkflowSlaHotspotsTrendsSummaryLine" class="footer-note mono">portfolio sla hotspots trends: buckets=- · window=-..- · hotspots=- · active_jobs=-/-</div>
            <div id="portfolioReviewWorkflowSlaHotspotsTrendSparkline" class="footer-note mono">trend: -</div>
            <div class="list" id="portfolioReviewWorkflowSlaHotspotsTrendsList" style="margin-top:10px;"></div>
            <div style="margin-top:10px;">
              <pre id="portfolioReviewWorkflowSlaHotspotsTrendsJson">{}</pre>
            </div>
            <div style="margin-top:14px;">
              <label>Portfolio Review Workflow Trends</label>
              <div class="sub" style="margin-top:4px;">Aggregated review-workflow event trends across the filtered portfolio.</div>
            </div>
            <div class="row" style="margin-top:10px;">
              <button id="portfolioReviewWorkflowTrendsBtn" class="ghost">Load Portfolio Workflow Trends</button>
              <button id="copyPortfolioReviewWorkflowTrendsJsonBtn" class="ghost">Copy Workflow Trends JSON</button>
              <button id="downloadPortfolioReviewWorkflowTrendsJsonBtn" class="ghost">Export Workflow Trends JSON</button>
              <button id="downloadPortfolioReviewWorkflowTrendsCsvBtn" class="secondary">Export Workflow Trends CSV</button>
            </div>
            <div id="portfolioReviewWorkflowTrendsSummaryLine" class="footer-note mono">portfolio workflow trends: buckets=- · window=-..- · events=- · active_jobs=-/-</div>
            <div id="portfolioReviewWorkflowTrendSparkline" class="footer-note mono">trend: -</div>
            <div class="list" id="portfolioReviewWorkflowTrendsList" style="margin-top:10px;"></div>
            <div style="margin-top:10px;">
              <pre id="portfolioReviewWorkflowTrendsJson">{}</pre>
            </div>
            <div style="margin-top:14px;">
              <label>Portfolio Review Workflow SLA Trends</label>
              <div class="sub" style="margin-top:4px;">Aggregated overdue SLA trend profile across the filtered portfolio review workflow.</div>
            </div>
            <div class="row" style="margin-top:10px;">
              <button id="portfolioReviewWorkflowSlaTrendsBtn" class="ghost">Load Portfolio Workflow SLA Trends</button>
              <button id="copyPortfolioReviewWorkflowSlaTrendsJsonBtn" class="ghost">Copy Workflow SLA Trends JSON</button>
              <button id="downloadPortfolioReviewWorkflowSlaTrendsJsonBtn" class="ghost">Export Workflow SLA Trends JSON</button>
              <button id="downloadPortfolioReviewWorkflowSlaTrendsCsvBtn" class="secondary">Export Workflow SLA Trends CSV</button>
            </div>
            <div id="portfolioReviewWorkflowSlaTrendsSummaryLine" class="footer-note mono">portfolio workflow sla trends: buckets=- · window=-..- · overdue=- · active_jobs=-/-</div>
            <div id="portfolioReviewWorkflowSlaTrendSparkline" class="footer-note mono">trend: -</div>
            <div class="list" id="portfolioReviewWorkflowSlaTrendsList" style="margin-top:10px;"></div>
            <div style="margin-top:10px;">
              <pre id="portfolioReviewWorkflowSlaTrendsJson">{}</pre>
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
                  <option value="selected">selected finding ids</option>
                  <option value="all">all findings in job</option>
                </select>
              </div>
              <div style="align-self:end;">
                <button id="criticBulkPreviewBtn" class="ghost">Preview Bulk Status</button>
              </div>
              <div style="align-self:end;">
                <button id="criticBulkApplyBtn" class="secondary">Apply Bulk Status</button>
              </div>
              <div style="align-self:end;">
                <button id="criticBulkClearFiltersBtn" class="ghost">Clear Critic Filters</button>
              </div>
              <div style="align-self:end;">
                <button id="criticSyncWorkflowFiltersBtn" class="ghost">Use Workflow Filters</button>
              </div>
            </div>
            <div id="criticBulkActionHint" class="footer-note mono" style="margin-top:10px;">
              finding bulk action: scope=filtered finding ids · queue=finding ack queue
            </div>
            <div id="criticWorkflowFilterSuggestion" class="footer-note mono" style="margin-top:6px;">
              workflow filter suggestion: -
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label for="criticSelectedFindingIds">Selected Finding IDs (comma/newline separated)</label>
                <textarea id="criticSelectedFindingIds" class="json" placeholder="finding-1&#10;finding-2"></textarea>
                <div class="row" style="margin-top:10px;">
                  <button id="criticCopySelectedFindingIdsBtn" class="ghost">Copy Selected IDs</button>
                  <button id="criticLoadFindingIdsFromWorkflowBtn" class="ghost">Fill From Workflow View</button>
                </div>
              </div>
              <div>
                <label for="criticSelectedFindingId">Latest Finding ID</label>
                <input id="criticSelectedFindingId" readonly />
                <div class="row" style="margin-top:10px;">
                  <button id="criticAddSelectedFindingBtn" class="ghost">Add Latest to Batch</button>
                  <button id="criticClearSelectedFindingIdsBtn" class="ghost">Clear Selected IDs</button>
                </div>
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
              <div class="list" id="criticBulkSummaryList"></div>
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
            <div class="row3" style="margin-top:10px;">
              <div>
                <label>Export Contract</label>
                <div id="exportContractPill" class="pill readiness-level-none">
                  <span class="dot"></span><span id="exportContractPillText">not loaded</span>
                </div>
              </div>
              <div>
                <label for="productionExportMode">Production Export</label>
                <select id="productionExportMode">
                  <option value="false">false</option>
                  <option value="true">true</option>
                </select>
              </div>
              <div>
                <label for="allowUnsafeExport">Allow Unsafe Override</label>
                <select id="allowUnsafeExport">
                  <option value="false">false</option>
                  <option value="true">true</option>
                </select>
              </div>
            </div>
            <div id="exportContractMetaLine" class="footer-note mono">mode=- · status=- · risk=- · missing=-</div>
            <div class="list" id="exportContractWarningsList" style="margin-top:10px;"></div>
            <div class="row3" style="margin-top:10px;">
              <div>
                <label>Send Gate</label>
                <div id="sendGatePill" class="pill readiness-level-none">
                  <span class="dot"></span><span id="sendGatePillText">not evaluated</span>
                </div>
              </div>
              <div class="sub mono" id="sendGateMetaLine" style="align-self:end;">
                policy=- · classification=- · next=-
              </div>
              <div class="sub mono" id="sendGateAdvisoryLine" style="align-self:end;">
                external send gate pending portfolio workflow snapshot
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <button id="exportZipFromPayloadBtn" class="secondary">Export ZIP from Payload</button>
              <button id="exportProductionZipFromPayloadBtn" class="danger">Production Export (enforced)</button>
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
                  <option value="acknowledged">acknowledged</option>
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
              <button id="ackCommentBtn" class="ghost">Acknowledge Selected</button>
            </div>
            <div class="row4" style="margin-top:10px;">
              <button id="resolveCommentBtn" class="secondary">Resolve Selected</button>
              <button id="reopenCommentBtn" class="ghost">Reopen Selected</button>
              <div>
                <label for="commentBulkTargetStatus">Bulk Comment Status</label>
                <select id="commentBulkTargetStatus">
                  <option value="acknowledged">acknowledged</option>
                  <option value="resolved">resolved</option>
                  <option value="open">open</option>
                </select>
              </div>
              <div>
                <label for="commentBulkScope">Bulk Scope</label>
                <select id="commentBulkScope">
                  <option value="filtered">filtered</option>
                  <option value="selected">selected comment ids</option>
                  <option value="all">all</option>
                </select>
              </div>
              <div style="align-self:end;">
                <button id="commentSyncWorkflowFiltersBtn" class="ghost">Use Workflow Filters</button>
              </div>
            </div>
            <div id="commentBulkActionHint" class="footer-note mono" style="margin-top:10px;">
              comment bulk action: scope=filtered comment ids · queue=comment ack queue
            </div>
            <div id="commentWorkflowFilterSuggestion" class="footer-note mono" style="margin-top:6px;">
              workflow filter suggestion: -
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label for="selectedCommentId">Selected Comment ID</label>
                <input id="selectedCommentId" readonly />
              </div>
              <div style="align-self:end;">
                <button id="commentBulkPreviewBtn" class="ghost">Preview Comment Bulk Status</button>
              </div>
              <div style="align-self:end;">
                <button id="commentBulkApplyBtn" class="secondary">Apply Comment Bulk Status</button>
              </div>
            </div>
            <div class="row" style="margin-top:10px;">
              <div>
                <label for="commentSelectedCommentIds">Selected Comment IDs (comma/newline separated)</label>
                <textarea id="commentSelectedCommentIds" class="json" placeholder="comment-1&#10;comment-2"></textarea>
                <div class="row" style="margin-top:10px;">
                  <button id="commentCopySelectedCommentIdsBtn" class="ghost">Copy Selected IDs</button>
                  <button id="commentLoadCommentIdsFromWorkflowBtn" class="ghost">Fill From Workflow View</button>
                </div>
              </div>
              <div style="align-self:end;">
                <div class="row" style="margin-top:10px;">
                  <button id="commentAddSelectedCommentBtn" class="ghost">Add Latest to Batch</button>
                  <button id="commentClearSelectedCommentIdsBtn" class="ghost">Clear Selected IDs</button>
                </div>
              </div>
            </div>
            <div style="margin-top:10px;">
              <div class="list" id="commentBulkSummaryList"></div>
            </div>
            <div style="margin-top:10px;">
              <pre id="commentBulkResultJson">{}</pre>
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
                <label for="reviewWorkflowFindingCodeFilter">Workflow Filter: Finding Code</label>
                <input id="reviewWorkflowFindingCodeFilter" placeholder="RUNTIME_GROUNDED_QUALITY_GATE_BLOCK" />
              </div>
              <div>
                <label for="reviewWorkflowFindingSectionFilter">Workflow Filter: Finding Section</label>
                <select id="reviewWorkflowFindingSectionFilter">
                  <option value="">all</option>
                  <option value="toc">toc</option>
                  <option value="logframe">logframe</option>
                  <option value="general">general</option>
                </select>
              </div>
              <div class="sub" style="align-self:end;">
                Server-side filters shared by workflow, SLA, and exports.
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
            <div id="reviewWorkflowPolicyLine" class="footer-note mono">workflow policy: status=- · go/no-go=- · next=-</div>
            <div class="kpis" id="reviewActionQueueCards" style="margin-top:10px;">
              <div class="kpi"><div class="label">Next Primary Action</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Finding Ack Queue</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Finding Resolve Queue</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Comment Ack Queue</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Comment Resolve Queue</div><div class="value mono">-</div></div>
              <div class="kpi"><div class="label">Comment Reopen Queue</div><div class="value mono">-</div></div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="reviewWorkflowExportJsonBtn" class="ghost">Export Workflow JSON</button>
              <button id="reviewWorkflowExportCsvBtn" class="secondary">Export Workflow CSV</button>
              <div class="sub" style="align-self:center;">Export uses current workflow filters.</div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="reviewWorkflowTrendsBtn" class="ghost">Load Workflow Trends</button>
              <div id="reviewWorkflowTrendsSummaryLine" class="footer-note mono" style="align-self:center;">
                workflow trends: buckets=- · window=- · events=-
              </div>
              <div></div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="reviewWorkflowTrendsExportJsonBtn" class="ghost">Export Workflow Trends JSON</button>
              <button id="reviewWorkflowTrendsExportCsvBtn" class="secondary">Export Workflow Trends CSV</button>
              <div class="sub" style="align-self:center;">Workflow trends export uses current workflow filters.</div>
            </div>
            <div style="margin-top:10px;">
              <label>Review Workflow Timeline</label>
              <div class="list" id="reviewWorkflowTimelineList"></div>
            </div>
            <div style="margin-top:10px;">
              <label>Review Workflow Trends</label>
              <div id="reviewWorkflowTrendSparkline" class="footer-note mono">trend: -</div>
              <div class="list" id="reviewWorkflowTrendsList"></div>
            </div>
            <div style="margin-top:10px;">
              <pre id="reviewWorkflowJson">{}</pre>
            </div>
            <div style="margin-top:10px;">
              <pre id="reviewWorkflowTrendsJson">{}</pre>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="reviewWorkflowSlaBtn" class="ghost">Load Workflow SLA</button>
              <button id="reviewWorkflowSlaTrendsBtn" class="ghost">Load SLA Trends</button>
              <button id="reviewWorkflowSlaHotspotsBtn" class="ghost">Load SLA Hotspots</button>
              <button id="reviewWorkflowSlaHotspotsTrendsBtn" class="ghost">Load SLA Hotspots Trends</button>
              <button id="reviewWorkflowSlaProfileBtn" class="ghost">Load SLA Profile</button>
              <div id="reviewWorkflowSlaSummaryLine" class="footer-note mono" style="align-self:center;">
                sla: overdue=- · breach_rate=- · oldest=-
              </div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="reviewWorkflowSlaRecomputeBtn" class="secondary">Recompute SLA</button>
              <div id="reviewWorkflowSlaTrendsSummaryLine" class="footer-note mono" style="align-self:center;">
                trends: buckets=- · window=- · overdue=-
              </div>
              <div></div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="reviewWorkflowSlaExportJsonBtn" class="ghost">Export SLA JSON</button>
              <button id="reviewWorkflowSlaExportCsvBtn" class="secondary">Export SLA CSV</button>
              <div class="sub" style="align-self:center;">SLA export uses current workflow filters.</div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="reviewWorkflowSlaTrendsExportJsonBtn" class="ghost">Export SLA Trends JSON</button>
              <button id="reviewWorkflowSlaTrendsExportCsvBtn" class="secondary">Export SLA Trends CSV</button>
              <div class="sub" style="align-self:center;">SLA trends export uses current workflow filters.</div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="reviewWorkflowSlaHotspotsExportJsonBtn" class="ghost">Export SLA Hotspots JSON</button>
              <button id="reviewWorkflowSlaHotspotsExportCsvBtn" class="secondary">Export SLA Hotspots CSV</button>
              <div id="reviewWorkflowSlaHotspotsSummaryLine" class="footer-note mono" style="align-self:center;">
                hotspots: shown=-/- · max_overdue=- · avg_overdue=-
              </div>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="reviewWorkflowSlaHotspotsTrendsExportJsonBtn" class="ghost">Export SLA Hotspots Trends JSON</button>
              <button id="reviewWorkflowSlaHotspotsTrendsExportCsvBtn" class="secondary">Export SLA Hotspots Trends CSV</button>
              <div id="reviewWorkflowSlaHotspotsTrendsSummaryLine" class="footer-note mono" style="align-self:center;">
                hotspots trends: buckets=- · window=-..- · hotspots=-
              </div>
            </div>
            <div class="row4" style="margin-top:10px;">
              <div>
                <label for="reviewWorkflowSlaHotspotKindFilter">Hotspot Kind</label>
                <select id="reviewWorkflowSlaHotspotKindFilter">
                  <option value="">all</option>
                  <option value="finding">finding</option>
                  <option value="comment">comment</option>
                </select>
              </div>
              <div>
                <label for="reviewWorkflowSlaHotspotSeverityFilter">Hotspot Severity</label>
                <select id="reviewWorkflowSlaHotspotSeverityFilter">
                  <option value="">all</option>
                  <option value="high">high</option>
                  <option value="medium">medium</option>
                  <option value="low">low</option>
                  <option value="unknown">unknown</option>
                </select>
              </div>
              <div>
                <label for="reviewWorkflowSlaMinOverdueHoursFilter">Min Overdue (h)</label>
                <input id="reviewWorkflowSlaMinOverdueHoursFilter" type="number" min="0" step="0.5" placeholder="0" />
              </div>
              <div>
                <label for="reviewWorkflowSlaTopLimitFilter">Top Limit</label>
                <input id="reviewWorkflowSlaTopLimitFilter" type="number" min="1" step="1" value="10" />
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
              <label>SLA Overdue Trends</label>
              <div id="reviewWorkflowSlaTrendSparkline" class="footer-note mono">trend: -</div>
              <div class="list" id="reviewWorkflowSlaTrendsList"></div>
            </div>
            <div style="margin-top:10px;">
              <label>SLA Hotspots Trends</label>
              <div id="reviewWorkflowSlaHotspotsTrendSparkline" class="footer-note mono">trend: -</div>
              <div class="list" id="reviewWorkflowSlaHotspotsTrendsList"></div>
            </div>
            <div style="margin-top:10px;">
              <pre id="reviewWorkflowSlaJson">{}</pre>
            </div>
            <div style="margin-top:10px;">
              <pre id="reviewWorkflowSlaTrendsJson">{}</pre>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="copyReviewWorkflowSlaHotspotsJsonBtn" class="ghost">Copy SLA Hotspots JSON</button>
              <button id="downloadReviewWorkflowSlaHotspotsJsonBtn" class="ghost">Download SLA Hotspots JSON</button>
              <button id="downloadReviewWorkflowSlaHotspotsCsvBtn" class="secondary">Download SLA Hotspots CSV</button>
            </div>
            <div style="margin-top:10px;">
              <pre id="reviewWorkflowSlaHotspotsJson">{}</pre>
            </div>
            <div class="row3" style="margin-top:10px;">
              <button id="copyReviewWorkflowSlaHotspotsTrendsJsonBtn" class="ghost">Copy SLA Hotspots Trends JSON</button>
              <button id="downloadReviewWorkflowSlaHotspotsTrendsJsonBtn" class="ghost">Download SLA Hotspots Trends JSON</button>
              <button id="downloadReviewWorkflowSlaHotspotsTrendsCsvBtn" class="secondary">Download SLA Hotspots Trends CSV</button>
            </div>
            <div style="margin-top:10px;">
              <pre id="reviewWorkflowSlaHotspotsTrendsJson">{}</pre>
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
        ["criticSelectedFindingIds", "grantflow_demo_critic_selected_finding_ids"],
        ["criticSelectedFindingId", "grantflow_demo_critic_selected_finding_id"],
        ["portfolioDonorFilter", "grantflow_demo_portfolio_donor"],
        ["portfolioStatusFilter", "grantflow_demo_portfolio_status"],
        ["portfolioHitlFilter", "grantflow_demo_portfolio_hitl"],
        ["portfolioWarningLevelFilter", "grantflow_demo_portfolio_warning_level"],
        ["portfolioGroundingRiskLevelFilter", "grantflow_demo_portfolio_grounding_risk_level"],
        ["portfolioFindingStatusFilter", "grantflow_demo_portfolio_finding_status"],
        ["portfolioFindingSeverityFilter", "grantflow_demo_portfolio_finding_severity"],
        ["portfolioToCTextRiskLevelFilter", "grantflow_demo_portfolio_toc_text_risk_level"],
        ["portfolioMelRiskLevelFilter", "grantflow_demo_portfolio_mel_risk_level"],
        ["portfolioSlaHotspotKindFilter", "grantflow_demo_portfolio_sla_hotspot_kind"],
        ["portfolioSlaHotspotSeverityFilter", "grantflow_demo_portfolio_sla_hotspot_severity"],
        ["portfolioSlaMinOverdueHoursFilter", "grantflow_demo_portfolio_sla_min_overdue_hours"],
        ["portfolioSlaTopLimitFilter", "grantflow_demo_portfolio_sla_top_limit"],
        ["exportGzipEnabled", "grantflow_demo_export_gzip_enabled"],
        ["productionExportMode", "grantflow_demo_production_export_mode"],
        ["allowUnsafeExport", "grantflow_demo_allow_unsafe_export"],
        ["commentsFilterSection", "grantflow_demo_comments_filter_section"],
        ["commentsFilterStatus", "grantflow_demo_comments_filter_status"],
        ["commentsFilterVersionId", "grantflow_demo_comments_filter_version_id"],
        ["reviewWorkflowEventTypeFilter", "grantflow_demo_review_workflow_event_type"],
        ["reviewWorkflowFindingIdFilter", "grantflow_demo_review_workflow_finding_id"],
        ["reviewWorkflowFindingCodeFilter", "grantflow_demo_review_workflow_finding_code"],
        ["reviewWorkflowFindingSectionFilter", "grantflow_demo_review_workflow_finding_section"],
        ["reviewWorkflowCommentStatusFilter", "grantflow_demo_review_workflow_comment_status"],
        ["reviewWorkflowStateFilter", "grantflow_demo_review_workflow_state"],
        ["reviewWorkflowOverdueHoursFilter", "grantflow_demo_review_workflow_overdue_hours"],
        ["reviewWorkflowSlaHotspotKindFilter", "grantflow_demo_review_workflow_sla_hotspot_kind"],
        ["reviewWorkflowSlaHotspotSeverityFilter", "grantflow_demo_review_workflow_sla_hotspot_severity"],
        ["reviewWorkflowSlaMinOverdueHoursFilter", "grantflow_demo_review_workflow_sla_min_overdue_hours"],
        ["reviewWorkflowSlaTopLimitFilter", "grantflow_demo_review_workflow_sla_top_limit"],
        ["reviewWorkflowSlaHighHours", "grantflow_demo_review_workflow_sla_high_hours"],
        ["reviewWorkflowSlaMediumHours", "grantflow_demo_review_workflow_sla_medium_hours"],
        ["reviewWorkflowSlaLowHours", "grantflow_demo_review_workflow_sla_low_hours"],
        ["reviewWorkflowSlaCommentDefaultHours", "grantflow_demo_review_workflow_sla_comment_default_hours"],
        ["reviewWorkflowSlaUseSavedProfile", "grantflow_demo_review_workflow_sla_use_saved_profile"],
        ["selectedCommentId", "grantflow_demo_selected_comment_id"],
        ["commentSelectedCommentIds", "grantflow_demo_selected_comment_ids"],
        ["linkedFindingId", "grantflow_demo_linked_finding_id"],
        ["generatePresetSelect", "grantflow_demo_generate_preset"],
        ["strictPreflight", "grantflow_demo_strict_preflight"],
        ["workerHeartbeatPollSeconds", "grantflow_demo_worker_heartbeat_poll_seconds"],
        ["inputContextJson", "grantflow_demo_input_context_json"],
        ["ingestPresetSelect", "grantflow_demo_ingest_preset"],
        ["ingestDonorId", "grantflow_demo_ingest_donor_id"],
        ["ingestMetadataJson", "grantflow_demo_ingest_metadata_json"],
      ];
      const state = {
        pollTimer: null,
        polling: false,
        workerHeartbeatPollTimer: null,
        workerHeartbeatPolling: true,
        lastCritic: null,
        lastCitations: null,
        lastIngestInventory: null,
        lastQualitySummary: null,
        lastPortfolioWorkflowPolicy: null,
        qualityGroundedGateExplainExpanded: false,
        ingestChecklistProgress: {},
        zeroReadinessWarningPrefs: {},
      };
      let GENERATE_PRESETS = {};
      const SERVER_GENERATE_PRESET_LABELS = {};
      let INGEST_PRESETS = {
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
      const LOCAL_INGEST_PRESET_LABELS = {
        usaid_gov_ai_kazakhstan: "USAID: AI civil service (KZ)",
        eu_digital_governance_moldova: "EU: digital governance (MD)",
        worldbank_public_sector_uzbekistan: "World Bank: public sector performance (UZ)",
      };
      const SERVER_INGEST_PRESET_LABELS = {};

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
        workerHeartbeatBtn: $("workerHeartbeatBtn"),
        workerHeartbeatPollSeconds: $("workerHeartbeatPollSeconds"),
        workerHeartbeatPollToggleBtn: $("workerHeartbeatPollToggleBtn"),
        workerHeartbeatPill: $("workerHeartbeatPill"),
        workerHeartbeatPillText: $("workerHeartbeatPillText"),
        workerHeartbeatMetaLine: $("workerHeartbeatMetaLine"),
        workerHeartbeatJson: $("workerHeartbeatJson"),
        qualityJson: $("qualityJson"),
        qualityAdvisoryBadgeList: $("qualityAdvisoryBadgeList"),
        qualityLlmFindingLabelsList: $("qualityLlmFindingLabelsList"),
        qualityMelSummaryList: $("qualityMelSummaryList"),
        qualityCitationTypeCountsList: $("qualityCitationTypeCountsList"),
        qualityArchitectCitationTypeCountsList: $("qualityArchitectCitationTypeCountsList"),
        qualityReadinessWarningsList: $("qualityReadinessWarningsList"),
        qualityReadinessWarningLevelPill: $("qualityReadinessWarningLevelPill"),
        qualityGroundedGatePill: $("qualityGroundedGatePill"),
        qualityGroundedGateExplainBtn: $("qualityGroundedGateExplainBtn"),
        qualityGroundedGateReasonsWrap: $("qualityGroundedGateReasonsWrap"),
        qualityGroundedGateReasonsList: $("qualityGroundedGateReasonsList"),
        qualityPreflightMetaLine: $("qualityPreflightMetaLine"),
        groundingKpiCards: $("groundingKpiCards"),
        groundingKpiMetaLine: $("groundingKpiMetaLine"),
        groundingKpiCountsList: $("groundingKpiCountsList"),
        groundingKpiPolicyReasonsList: $("groundingKpiPolicyReasonsList"),
        portfolioMetricsJson: $("portfolioMetricsJson"),
        portfolioQualityJson: $("portfolioQualityJson"),
        portfolioReviewWorkflowJson: $("portfolioReviewWorkflowJson"),
        portfolioReviewWorkflowSlaJson: $("portfolioReviewWorkflowSlaJson"),
        portfolioReviewWorkflowSlaHotspotsJson: $("portfolioReviewWorkflowSlaHotspotsJson"),
        portfolioReviewWorkflowSlaHotspotsTrendsJson: $("portfolioReviewWorkflowSlaHotspotsTrendsJson"),
        portfolioReviewWorkflowTrendsJson: $("portfolioReviewWorkflowTrendsJson"),
        portfolioReviewWorkflowSlaTrendsJson: $("portfolioReviewWorkflowSlaTrendsJson"),
        criticJson: $("criticJson"),
        exportPayloadJson: $("exportPayloadJson"),
        exportContractPill: $("exportContractPill"),
        exportContractPillText: $("exportContractPillText"),
        exportContractMetaLine: $("exportContractMetaLine"),
        exportContractWarningsList: $("exportContractWarningsList"),
        diffPre: $("diffPre"),
        versionsList: $("versionsList"),
        citationsList: $("citationsList"),
        eventsList: $("eventsList"),
        criticFlawsList: $("criticFlawsList"),
        criticChecksList: $("criticChecksList"),
        criticContextList: $("criticContextList"),
        criticBulkResultJson: $("criticBulkResultJson"),
        criticSelectedFindingIds: $("criticSelectedFindingIds"),
        criticSelectedFindingId: $("criticSelectedFindingId"),
        criticAdvisorySummaryList: $("criticAdvisorySummaryList"),
        criticAdvisoryLabelsList: $("criticAdvisoryLabelsList"),
        criticAdvisoryNormalizationList: $("criticAdvisoryNormalizationList"),
        commentsList: $("commentsList"),
        commentBulkResultJson: $("commentBulkResultJson"),
        commentSelectedCommentIds: $("commentSelectedCommentIds"),
        reviewWorkflowTimelineList: $("reviewWorkflowTimelineList"),
        reviewActionQueueCards: $("reviewActionQueueCards"),
        reviewWorkflowSummaryLine: $("reviewWorkflowSummaryLine"),
        reviewWorkflowPolicyLine: $("reviewWorkflowPolicyLine"),
        reviewWorkflowJson: $("reviewWorkflowJson"),
        reviewWorkflowTrendsBtn: $("reviewWorkflowTrendsBtn"),
        reviewWorkflowTrendsExportJsonBtn: $("reviewWorkflowTrendsExportJsonBtn"),
        reviewWorkflowTrendsExportCsvBtn: $("reviewWorkflowTrendsExportCsvBtn"),
        reviewWorkflowTrendsSummaryLine: $("reviewWorkflowTrendsSummaryLine"),
        reviewWorkflowTrendSparkline: $("reviewWorkflowTrendSparkline"),
        reviewWorkflowTrendsList: $("reviewWorkflowTrendsList"),
        reviewWorkflowTrendsJson: $("reviewWorkflowTrendsJson"),
        reviewWorkflowEventTypeFilter: $("reviewWorkflowEventTypeFilter"),
        reviewWorkflowFindingIdFilter: $("reviewWorkflowFindingIdFilter"),
        reviewWorkflowFindingCodeFilter: $("reviewWorkflowFindingCodeFilter"),
        reviewWorkflowFindingSectionFilter: $("reviewWorkflowFindingSectionFilter"),
        reviewWorkflowCommentStatusFilter: $("reviewWorkflowCommentStatusFilter"),
        reviewWorkflowStateFilter: $("reviewWorkflowStateFilter"),
        reviewWorkflowOverdueHoursFilter: $("reviewWorkflowOverdueHoursFilter"),
        reviewWorkflowSlaHotspotKindFilter: $("reviewWorkflowSlaHotspotKindFilter"),
        reviewWorkflowSlaHotspotSeverityFilter: $("reviewWorkflowSlaHotspotSeverityFilter"),
        reviewWorkflowSlaMinOverdueHoursFilter: $("reviewWorkflowSlaMinOverdueHoursFilter"),
        reviewWorkflowSlaTopLimitFilter: $("reviewWorkflowSlaTopLimitFilter"),
        reviewWorkflowSlaHighHours: $("reviewWorkflowSlaHighHours"),
        reviewWorkflowSlaMediumHours: $("reviewWorkflowSlaMediumHours"),
        reviewWorkflowSlaLowHours: $("reviewWorkflowSlaLowHours"),
        reviewWorkflowSlaCommentDefaultHours: $("reviewWorkflowSlaCommentDefaultHours"),
        reviewWorkflowSlaUseSavedProfile: $("reviewWorkflowSlaUseSavedProfile"),
        reviewWorkflowClearFiltersBtn: $("reviewWorkflowClearFiltersBtn"),
        reviewWorkflowExportJsonBtn: $("reviewWorkflowExportJsonBtn"),
        reviewWorkflowExportCsvBtn: $("reviewWorkflowExportCsvBtn"),
        reviewWorkflowSlaBtn: $("reviewWorkflowSlaBtn"),
        reviewWorkflowSlaTrendsBtn: $("reviewWorkflowSlaTrendsBtn"),
        reviewWorkflowSlaHotspotsBtn: $("reviewWorkflowSlaHotspotsBtn"),
        reviewWorkflowSlaHotspotsTrendsBtn: $("reviewWorkflowSlaHotspotsTrendsBtn"),
        reviewWorkflowSlaProfileBtn: $("reviewWorkflowSlaProfileBtn"),
        reviewWorkflowSlaRecomputeBtn: $("reviewWorkflowSlaRecomputeBtn"),
        reviewWorkflowSlaExportJsonBtn: $("reviewWorkflowSlaExportJsonBtn"),
        reviewWorkflowSlaExportCsvBtn: $("reviewWorkflowSlaExportCsvBtn"),
        reviewWorkflowSlaTrendsExportJsonBtn: $("reviewWorkflowSlaTrendsExportJsonBtn"),
        reviewWorkflowSlaTrendsExportCsvBtn: $("reviewWorkflowSlaTrendsExportCsvBtn"),
        reviewWorkflowSlaHotspotsExportJsonBtn: $("reviewWorkflowSlaHotspotsExportJsonBtn"),
        reviewWorkflowSlaHotspotsExportCsvBtn: $("reviewWorkflowSlaHotspotsExportCsvBtn"),
        reviewWorkflowSlaHotspotsTrendsExportJsonBtn: $("reviewWorkflowSlaHotspotsTrendsExportJsonBtn"),
        reviewWorkflowSlaHotspotsTrendsExportCsvBtn: $("reviewWorkflowSlaHotspotsTrendsExportCsvBtn"),
        copyReviewWorkflowSlaHotspotsJsonBtn: $("copyReviewWorkflowSlaHotspotsJsonBtn"),
        downloadReviewWorkflowSlaHotspotsJsonBtn: $("downloadReviewWorkflowSlaHotspotsJsonBtn"),
        downloadReviewWorkflowSlaHotspotsCsvBtn: $("downloadReviewWorkflowSlaHotspotsCsvBtn"),
        copyReviewWorkflowSlaHotspotsTrendsJsonBtn: $("copyReviewWorkflowSlaHotspotsTrendsJsonBtn"),
        downloadReviewWorkflowSlaHotspotsTrendsJsonBtn: $("downloadReviewWorkflowSlaHotspotsTrendsJsonBtn"),
        downloadReviewWorkflowSlaHotspotsTrendsCsvBtn: $("downloadReviewWorkflowSlaHotspotsTrendsCsvBtn"),
        reviewWorkflowSlaSummaryLine: $("reviewWorkflowSlaSummaryLine"),
        reviewWorkflowSlaTrendsSummaryLine: $("reviewWorkflowSlaTrendsSummaryLine"),
        reviewWorkflowSlaHotspotsSummaryLine: $("reviewWorkflowSlaHotspotsSummaryLine"),
        reviewWorkflowSlaHotspotsTrendsSummaryLine: $("reviewWorkflowSlaHotspotsTrendsSummaryLine"),
        reviewWorkflowSlaHotspotsList: $("reviewWorkflowSlaHotspotsList"),
        reviewWorkflowSlaTrendSparkline: $("reviewWorkflowSlaTrendSparkline"),
        reviewWorkflowSlaTrendsList: $("reviewWorkflowSlaTrendsList"),
        reviewWorkflowSlaHotspotsTrendSparkline: $("reviewWorkflowSlaHotspotsTrendSparkline"),
        reviewWorkflowSlaHotspotsTrendsList: $("reviewWorkflowSlaHotspotsTrendsList"),
        reviewWorkflowSlaJson: $("reviewWorkflowSlaJson"),
        reviewWorkflowSlaTrendsJson: $("reviewWorkflowSlaTrendsJson"),
        reviewWorkflowSlaHotspotsJson: $("reviewWorkflowSlaHotspotsJson"),
        reviewWorkflowSlaHotspotsTrendsJson: $("reviewWorkflowSlaHotspotsTrendsJson"),
        reviewWorkflowSlaProfileSummaryLine: $("reviewWorkflowSlaProfileSummaryLine"),
        reviewWorkflowSlaProfileJson: $("reviewWorkflowSlaProfileJson"),
        metricsCards: $("metricsCards"),
        qualityCards: $("qualityCards"),
        portfolioMetricsCards: $("portfolioMetricsCards"),
        portfolioQualityCards: $("portfolioQualityCards"),
        portfolioWarningMetaLine: $("portfolioWarningMetaLine"),
        portfolioReviewWorkflowSummaryLine: $("portfolioReviewWorkflowSummaryLine"),
        portfolioReviewWorkflowPolicyLine: $("portfolioReviewWorkflowPolicyLine"),
        portfolioReviewWorkflowList: $("portfolioReviewWorkflowList"),
        portfolioReviewWorkflowSlaSummaryLine: $("portfolioReviewWorkflowSlaSummaryLine"),
        portfolioReviewWorkflowSlaList: $("portfolioReviewWorkflowSlaList"),
        portfolioReviewWorkflowSlaHotspotsSummaryLine: $("portfolioReviewWorkflowSlaHotspotsSummaryLine"),
        portfolioReviewWorkflowSlaHotspotsList: $("portfolioReviewWorkflowSlaHotspotsList"),
        portfolioReviewWorkflowSlaHotspotsTrendsSummaryLine: $("portfolioReviewWorkflowSlaHotspotsTrendsSummaryLine"),
        portfolioReviewWorkflowSlaHotspotsTrendSparkline: $("portfolioReviewWorkflowSlaHotspotsTrendSparkline"),
        portfolioReviewWorkflowSlaHotspotsTrendsList: $("portfolioReviewWorkflowSlaHotspotsTrendsList"),
        portfolioReviewWorkflowTrendsSummaryLine: $("portfolioReviewWorkflowTrendsSummaryLine"),
        portfolioReviewWorkflowTrendSparkline: $("portfolioReviewWorkflowTrendSparkline"),
        portfolioReviewWorkflowTrendsList: $("portfolioReviewWorkflowTrendsList"),
        portfolioReviewWorkflowSlaTrendsSummaryLine: $("portfolioReviewWorkflowSlaTrendsSummaryLine"),
        portfolioReviewWorkflowSlaTrendSparkline: $("portfolioReviewWorkflowSlaTrendSparkline"),
        portfolioReviewWorkflowSlaTrendsList: $("portfolioReviewWorkflowSlaTrendsList"),
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
        portfolioQualityToCTextRiskList: $("portfolioQualityToCTextRiskList"),
        portfolioQualityGroundingRiskList: $("portfolioQualityGroundingRiskList"),
        portfolioQualityGroundedGateSectionsList: $("portfolioQualityGroundedGateSectionsList"),
        portfolioQualityGroundedGateReasonsList: $("portfolioQualityGroundedGateReasonsList"),
        portfolioQualityGroundedGateDonorsList: $("portfolioQualityGroundedGateDonorsList"),
        portfolioQualityCitationTypeCountsList: $("portfolioQualityCitationTypeCountsList"),
        portfolioQualityArchitectCitationTypeCountsList: $("portfolioQualityArchitectCitationTypeCountsList"),
        portfolioQualityMelCitationTypeCountsList: $("portfolioQualityMelCitationTypeCountsList"),
        portfolioQualityMelSummaryList: $("portfolioQualityMelSummaryList"),
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
        criticBulkPreviewBtn: $("criticBulkPreviewBtn"),
        criticBulkActionHint: $("criticBulkActionHint"),
        criticWorkflowFilterSuggestion: $("criticWorkflowFilterSuggestion"),
        criticSyncWorkflowFiltersBtn: $("criticSyncWorkflowFiltersBtn"),
        criticAddSelectedFindingBtn: $("criticAddSelectedFindingBtn"),
        criticClearSelectedFindingIdsBtn: $("criticClearSelectedFindingIdsBtn"),
        criticCopySelectedFindingIdsBtn: $("criticCopySelectedFindingIdsBtn"),
        criticLoadFindingIdsFromWorkflowBtn: $("criticLoadFindingIdsFromWorkflowBtn"),
        criticBulkSummaryList: $("criticBulkSummaryList"),
        portfolioDonorFilter: $("portfolioDonorFilter"),
        portfolioStatusFilter: $("portfolioStatusFilter"),
        portfolioHitlFilter: $("portfolioHitlFilter"),
        portfolioWarningLevelFilter: $("portfolioWarningLevelFilter"),
        portfolioGroundingRiskLevelFilter: $("portfolioGroundingRiskLevelFilter"),
        portfolioFindingStatusFilter: $("portfolioFindingStatusFilter"),
        portfolioFindingSeverityFilter: $("portfolioFindingSeverityFilter"),
        portfolioToCTextRiskLevelFilter: $("portfolioToCTextRiskLevelFilter"),
        portfolioMelRiskLevelFilter: $("portfolioMelRiskLevelFilter"),
        portfolioSlaHotspotKindFilter: $("portfolioSlaHotspotKindFilter"),
        portfolioSlaHotspotSeverityFilter: $("portfolioSlaHotspotSeverityFilter"),
        portfolioSlaMinOverdueHoursFilter: $("portfolioSlaMinOverdueHoursFilter"),
        portfolioSlaTopLimitFilter: $("portfolioSlaTopLimitFilter"),
        exportGzipEnabled: $("exportGzipEnabled"),
        productionExportMode: $("productionExportMode"),
        allowUnsafeExport: $("allowUnsafeExport"),
        sendGatePill: $("sendGatePill"),
        sendGatePillText: $("sendGatePillText"),
        sendGateMetaLine: $("sendGateMetaLine"),
        sendGateAdvisoryLine: $("sendGateAdvisoryLine"),
        commentsFilterSection: $("commentsFilterSection"),
        commentsFilterStatus: $("commentsFilterStatus"),
        commentsFilterVersionId: $("commentsFilterVersionId"),
        commentBulkPreviewBtn: $("commentBulkPreviewBtn"),
        commentBulkActionHint: $("commentBulkActionHint"),
        commentWorkflowFilterSuggestion: $("commentWorkflowFilterSuggestion"),
        commentSyncWorkflowFiltersBtn: $("commentSyncWorkflowFiltersBtn"),
        commentCopySelectedCommentIdsBtn: $("commentCopySelectedCommentIdsBtn"),
        commentLoadCommentIdsFromWorkflowBtn: $("commentLoadCommentIdsFromWorkflowBtn"),
        commentBulkSummaryList: $("commentBulkSummaryList"),
        commentSection: $("commentSection"),
        commentAuthor: $("commentAuthor"),
        commentVersionId: $("commentVersionId"),
        linkedFindingId: $("linkedFindingId"),
        commentMessage: $("commentMessage"),
        selectedCommentId: $("selectedCommentId"),
        commentAddSelectedCommentBtn: $("commentAddSelectedCommentBtn"),
        commentClearSelectedCommentIdsBtn: $("commentClearSelectedCommentIdsBtn"),
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
        exportProductionZipFromPayloadBtn: $("exportProductionZipFromPayloadBtn"),
        eventsBtn: $("eventsBtn"),
        criticBtn: $("criticBtn"),
        criticBulkApplyBtn: $("criticBulkApplyBtn"),
        criticBulkClearFiltersBtn: $("criticBulkClearFiltersBtn"),
        qualityBtn: $("qualityBtn"),
        portfolioBtn: $("portfolioBtn"),
        portfolioReviewWorkflowBtn: $("portfolioReviewWorkflowBtn"),
        portfolioReviewWorkflowSlaBtn: $("portfolioReviewWorkflowSlaBtn"),
        portfolioReviewWorkflowSlaHotspotsBtn: $("portfolioReviewWorkflowSlaHotspotsBtn"),
        portfolioReviewWorkflowSlaHotspotsTrendsBtn: $("portfolioReviewWorkflowSlaHotspotsTrendsBtn"),
        portfolioReviewWorkflowTrendsBtn: $("portfolioReviewWorkflowTrendsBtn"),
        portfolioReviewWorkflowSlaTrendsBtn: $("portfolioReviewWorkflowSlaTrendsBtn"),
        portfolioClearBtn: $("portfolioClearBtn"),
        clearPortfolioToCTextRiskBtn: $("clearPortfolioToCTextRiskBtn"),
        copyPortfolioMetricsJsonBtn: $("copyPortfolioMetricsJsonBtn"),
        downloadPortfolioMetricsJsonBtn: $("downloadPortfolioMetricsJsonBtn"),
        downloadPortfolioMetricsCsvBtn: $("downloadPortfolioMetricsCsvBtn"),
        copyPortfolioQualityJsonBtn: $("copyPortfolioQualityJsonBtn"),
        downloadPortfolioQualityJsonBtn: $("downloadPortfolioQualityJsonBtn"),
        downloadPortfolioQualityCsvBtn: $("downloadPortfolioQualityCsvBtn"),
        copyPortfolioReviewWorkflowJsonBtn: $("copyPortfolioReviewWorkflowJsonBtn"),
        downloadPortfolioReviewWorkflowJsonBtn: $("downloadPortfolioReviewWorkflowJsonBtn"),
        downloadPortfolioReviewWorkflowCsvBtn: $("downloadPortfolioReviewWorkflowCsvBtn"),
        copyPortfolioReviewWorkflowSlaJsonBtn: $("copyPortfolioReviewWorkflowSlaJsonBtn"),
        downloadPortfolioReviewWorkflowSlaJsonBtn: $("downloadPortfolioReviewWorkflowSlaJsonBtn"),
        downloadPortfolioReviewWorkflowSlaCsvBtn: $("downloadPortfolioReviewWorkflowSlaCsvBtn"),
        copyPortfolioReviewWorkflowSlaHotspotsJsonBtn: $("copyPortfolioReviewWorkflowSlaHotspotsJsonBtn"),
        downloadPortfolioReviewWorkflowSlaHotspotsJsonBtn: $("downloadPortfolioReviewWorkflowSlaHotspotsJsonBtn"),
        downloadPortfolioReviewWorkflowSlaHotspotsCsvBtn: $("downloadPortfolioReviewWorkflowSlaHotspotsCsvBtn"),
        copyPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn: $("copyPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn"),
        downloadPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn: $("downloadPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn"),
        downloadPortfolioReviewWorkflowSlaHotspotsTrendsCsvBtn: $("downloadPortfolioReviewWorkflowSlaHotspotsTrendsCsvBtn"),
        copyPortfolioReviewWorkflowTrendsJsonBtn: $("copyPortfolioReviewWorkflowTrendsJsonBtn"),
        downloadPortfolioReviewWorkflowTrendsJsonBtn: $("downloadPortfolioReviewWorkflowTrendsJsonBtn"),
        downloadPortfolioReviewWorkflowTrendsCsvBtn: $("downloadPortfolioReviewWorkflowTrendsCsvBtn"),
        copyPortfolioReviewWorkflowSlaTrendsJsonBtn: $("copyPortfolioReviewWorkflowSlaTrendsJsonBtn"),
        downloadPortfolioReviewWorkflowSlaTrendsJsonBtn: $("downloadPortfolioReviewWorkflowSlaTrendsJsonBtn"),
        downloadPortfolioReviewWorkflowSlaTrendsCsvBtn: $("downloadPortfolioReviewWorkflowSlaTrendsCsvBtn"),
        exportInventoryJsonBtn: $("exportInventoryJsonBtn"),
        exportInventoryCsvBtn: $("exportInventoryCsvBtn"),
        exportPortfolioMetricsJsonBtn: $("exportPortfolioMetricsJsonBtn"),
        exportPortfolioMetricsCsvBtn: $("exportPortfolioMetricsCsvBtn"),
        exportPortfolioQualityJsonBtn: $("exportPortfolioQualityJsonBtn"),
        exportPortfolioQualityCsvBtn: $("exportPortfolioQualityCsvBtn"),
        exportPortfolioReviewWorkflowJsonBtn: $("exportPortfolioReviewWorkflowJsonBtn"),
        exportPortfolioReviewWorkflowCsvBtn: $("exportPortfolioReviewWorkflowCsvBtn"),
        exportPortfolioReviewWorkflowSlaJsonBtn: $("exportPortfolioReviewWorkflowSlaJsonBtn"),
        exportPortfolioReviewWorkflowSlaCsvBtn: $("exportPortfolioReviewWorkflowSlaCsvBtn"),
        exportPortfolioReviewWorkflowSlaHotspotsJsonBtn: $("exportPortfolioReviewWorkflowSlaHotspotsJsonBtn"),
        exportPortfolioReviewWorkflowSlaHotspotsCsvBtn: $("exportPortfolioReviewWorkflowSlaHotspotsCsvBtn"),
        exportPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn: $("exportPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn"),
        exportPortfolioReviewWorkflowSlaHotspotsTrendsCsvBtn: $("exportPortfolioReviewWorkflowSlaHotspotsTrendsCsvBtn"),
        exportPortfolioReviewWorkflowTrendsJsonBtn: $("exportPortfolioReviewWorkflowTrendsJsonBtn"),
        exportPortfolioReviewWorkflowTrendsCsvBtn: $("exportPortfolioReviewWorkflowTrendsCsvBtn"),
        exportPortfolioReviewWorkflowSlaTrendsJsonBtn: $("exportPortfolioReviewWorkflowSlaTrendsJsonBtn"),
        exportPortfolioReviewWorkflowSlaTrendsCsvBtn: $("exportPortfolioReviewWorkflowSlaTrendsCsvBtn"),
        commentsBtn: $("commentsBtn"),
        reviewWorkflowBtn: $("reviewWorkflowBtn"),
        addCommentBtn: $("addCommentBtn"),
        ackCommentBtn: $("ackCommentBtn"),
        resolveCommentBtn: $("resolveCommentBtn"),
        reopenCommentBtn: $("reopenCommentBtn"),
        commentBulkTargetStatus: $("commentBulkTargetStatus"),
        commentBulkScope: $("commentBulkScope"),
        commentBulkApplyBtn: $("commentBulkApplyBtn"),
        clearLinkedFindingBtn: $("clearLinkedFindingBtn"),
        openPendingBtn: $("openPendingBtn"),
      };

      function initDefaults() {
        els.apiBase.value = localStorage.getItem("grantflow_demo_api_base") || window.location.origin;
        els.apiKey.value = localStorage.getItem("grantflow_demo_api_key") || "";
        els.jobIdInput.value = localStorage.getItem("grantflow_demo_job_id") || "";
        state.ingestChecklistProgress = loadIngestChecklistProgress();
        state.zeroReadinessWarningPrefs = loadZeroReadinessWarningPrefs();
        renderGeneratePresetOptions();
        renderIngestPresetOptions();
        restoreUiState();
        if (!String(els.productionExportMode?.value || "").trim()) {
          els.productionExportMode.value = "false";
        }
        if (!String(els.allowUnsafeExport?.value || "").trim()) {
          els.allowUnsafeExport.value = "false";
        }
        renderSendGate(state.lastPortfolioWorkflowPolicy);
        if (!String(els.ingestDonorId.value || "").trim()) {
          els.ingestDonorId.value = String(els.donorId.value || "usaid");
        }
        renderIngestPresetGuidance();
        renderIngestChecklistProgress();
        renderGeneratePresetReadiness();
        if (!String(els.workerHeartbeatPollSeconds?.value || "").trim()) {
          els.workerHeartbeatPollSeconds.value = "10";
        }
        renderWorkerHeartbeat(null);
        updateWorkerHeartbeatPollToggleLabel();
        startWorkerHeartbeatPolling();
        renderExportContract(null);
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

      function generatePresetLabel(key) {
        const token = String(key || "").trim();
        if (!token) return "Preset";
        if (SERVER_GENERATE_PRESET_LABELS[token]) return SERVER_GENERATE_PRESET_LABELS[token];
        return token;
      }

      function renderGeneratePresetOptions({ preferredValue = null } = {}) {
        if (!els.generatePresetSelect) return;
        const selected = preferredValue == null
          ? String(els.generatePresetSelect.value || "").trim()
          : String(preferredValue || "").trim();
        const keys = Object.keys(GENERATE_PRESETS || {});
        els.generatePresetSelect.innerHTML = "";
        const noneOption = document.createElement("option");
        noneOption.value = "";
        noneOption.textContent = "none";
        els.generatePresetSelect.appendChild(noneOption);
        for (const key of keys) {
          const option = document.createElement("option");
          option.value = key;
          option.textContent = generatePresetLabel(key);
          els.generatePresetSelect.appendChild(option);
        }
        if (selected && GENERATE_PRESETS[selected]) {
          els.generatePresetSelect.value = selected;
        } else {
          els.generatePresetSelect.value = "";
        }
      }

      function normalizeGeneratePresetRecord({
        presetKey,
        row,
        detail,
        prefix = "",
        sourceKind = "",
      }) {
        const generatePayload =
          detail && typeof detail.generate_payload === "object" && !Array.isArray(detail.generate_payload)
            ? detail.generate_payload
            : {};
        const inputContext =
          generatePayload.input_context &&
          typeof generatePayload.input_context === "object" &&
          !Array.isArray(generatePayload.input_context)
            ? { ...generatePayload.input_context }
            : {};
        const donorId = String(generatePayload.donor_id || row?.donor_id || "").trim();
        const project = String(inputContext.project || row?.title || presetKey).trim();
        const country = String(inputContext.country || row?.country || "").trim();
        const presetSourceKind = String(sourceKind || row?.source_kind || "").trim().toLowerCase();
        const donorLabel = donorId ? donorId.toUpperCase() : "RBM";
        const title = String(row?.title || project || presetKey).trim();
        const label = prefix ? `${prefix} (${donorLabel}): ${title}` : `${donorLabel}: ${title}`;
        return {
          preset: {
            preset_key: String(presetKey || "").trim(),
            source_kind: presetSourceKind || null,
            donor_id: donorId,
            project,
            country,
            llm_mode: Boolean(generatePayload.llm_mode),
            hitl_enabled: Boolean(generatePayload.hitl_enabled),
            architect_rag_enabled:
              generatePayload.architect_rag_enabled == null ? null : Boolean(generatePayload.architect_rag_enabled),
            strict_preflight: Boolean(generatePayload.strict_preflight),
            input_context: inputContext,
          },
          label,
        };
      }

      async function loadAllServerGeneratePresets() {
        const merged = {};
        const labels = {};

        try {
          const bundledGenerate = await apiFetch("/generate/presets");
          const rows = Array.isArray(bundledGenerate?.presets) ? bundledGenerate.presets : [];
          for (const row of rows) {
            if (!row || typeof row !== "object") continue;
            const presetKey = String(row.preset_key || "").trim();
            if (!presetKey) continue;
            const sourceKind = String(row.source_kind || "").trim().toLowerCase();
            const prefix = sourceKind === "rbm" ? "RBM" : "";
            const normalized = normalizeGeneratePresetRecord({
              presetKey,
              row,
              detail: { generate_payload: row.generate_payload || {} },
              prefix,
              sourceKind,
            });
            merged[presetKey] = normalized.preset;
            labels[presetKey] = String(row.label || "").trim() || normalized.label;
          }
        } catch (err) {
          return;
        }

        if (!Object.keys(merged).length) return;

        GENERATE_PRESETS = merged;
        for (const key of Object.keys(SERVER_GENERATE_PRESET_LABELS)) {
          delete SERVER_GENERATE_PRESET_LABELS[key];
        }
        for (const [key, value] of Object.entries(labels)) {
          SERVER_GENERATE_PRESET_LABELS[key] = value;
        }
        const storedPreset = localStorage.getItem("grantflow_demo_generate_preset") || "";
        const preferredValue = String(els.generatePresetSelect.value || "").trim() || String(storedPreset || "").trim();
        renderGeneratePresetOptions({ preferredValue });
        renderGeneratePresetReadiness();
        renderZeroReadinessWarningPreference();
      }

      function ingestPresetLabel(key) {
        const token = String(key || "").trim();
        if (!token) return "Preset";
        if (SERVER_INGEST_PRESET_LABELS[token]) return SERVER_INGEST_PRESET_LABELS[token];
        if (LOCAL_INGEST_PRESET_LABELS[token]) return LOCAL_INGEST_PRESET_LABELS[token];
        return token;
      }

      function renderIngestPresetOptions({ preferredValue = null } = {}) {
        if (!els.ingestPresetSelect) return;
        const selected = preferredValue == null
          ? String(els.ingestPresetSelect.value || "").trim()
          : String(preferredValue || "").trim();
        const keys = Object.keys(INGEST_PRESETS || {});
        els.ingestPresetSelect.innerHTML = "";
        const noneOption = document.createElement("option");
        noneOption.value = "";
        noneOption.textContent = "none";
        els.ingestPresetSelect.appendChild(noneOption);
        for (const key of keys) {
          const option = document.createElement("option");
          option.value = key;
          option.textContent = ingestPresetLabel(key);
          els.ingestPresetSelect.appendChild(option);
        }
        if (selected && INGEST_PRESETS[selected]) {
          els.ingestPresetSelect.value = selected;
        } else {
          els.ingestPresetSelect.value = "";
        }
      }

      function applyServerPresetBundle(bundle) {
        const generateRows = Array.isArray(bundle?.generate_presets) ? bundle.generate_presets : [];
        const ingestRows = Array.isArray(bundle?.ingest_presets) ? bundle.ingest_presets : [];
        let generateChanged = false;
        let ingestChanged = false;

        if (generateRows.length) {
          const mergedGenerate = {};
          const nextGenerateLabels = {};
          for (const row of generateRows) {
            if (!row || typeof row !== "object") continue;
            const presetKey = String(row.preset_key || "").trim();
            if (!presetKey) continue;
            const sourceKind = String(row.source_kind || "").trim().toLowerCase();
            const prefix = sourceKind === "rbm" ? "RBM" : "";
            const normalized = normalizeGeneratePresetRecord({
              presetKey,
              row,
              detail: { generate_payload: row.generate_payload || {} },
              prefix,
              sourceKind,
            });
            mergedGenerate[presetKey] = normalized.preset;
            nextGenerateLabels[presetKey] = String(row.label || "").trim() || normalized.label;
            generateChanged = true;
          }
          if (generateChanged) {
            GENERATE_PRESETS = mergedGenerate;
            for (const key of Object.keys(SERVER_GENERATE_PRESET_LABELS)) {
              delete SERVER_GENERATE_PRESET_LABELS[key];
            }
            for (const [key, value] of Object.entries(nextGenerateLabels)) {
              SERVER_GENERATE_PRESET_LABELS[key] = value;
            }
            const storedPreset = localStorage.getItem("grantflow_demo_generate_preset") || "";
            const preferredValue =
              String(els.generatePresetSelect.value || "").trim() || String(storedPreset || "").trim();
            renderGeneratePresetOptions({ preferredValue });
          }
        }

        if (ingestRows.length) {
          const mergedIngest = {};
          const nextIngestLabels = {};
          for (const row of ingestRows) {
            if (!row || typeof row !== "object") continue;
            const presetKey = String(row.preset_key || "").trim();
            if (!presetKey) continue;
            const donorId = String(row.donor_id || "").trim();
            mergedIngest[presetKey] = {
              donor_id: donorId,
              metadata:
                row.metadata && typeof row.metadata === "object" && !Array.isArray(row.metadata)
                  ? { ...row.metadata }
                  : {},
              checklist_items: Array.isArray(row.checklist_items) ? row.checklist_items : [],
              recommended_docs: Array.isArray(row.recommended_docs) ? row.recommended_docs : [],
            };
            const donorLabel = donorId ? donorId.toUpperCase() : "INGEST";
            const title = String(row.title || presetKey).trim();
            nextIngestLabels[presetKey] = String(row.label || "").trim() || `${donorLabel}: ${title}`;
            ingestChanged = true;
          }
          if (ingestChanged) {
            INGEST_PRESETS = mergedIngest;
            for (const key of Object.keys(SERVER_INGEST_PRESET_LABELS)) {
              delete SERVER_INGEST_PRESET_LABELS[key];
            }
            for (const [key, value] of Object.entries(nextIngestLabels)) {
              SERVER_INGEST_PRESET_LABELS[key] = value;
            }
            const storedPreset = localStorage.getItem("grantflow_demo_ingest_preset") || "";
            const preferredValue =
              String(els.ingestPresetSelect.value || "").trim() || String(storedPreset || "").trim();
            renderIngestPresetOptions({ preferredValue });
          }
        }

        if (generateChanged || ingestChanged) {
          renderGeneratePresetReadiness();
          renderZeroReadinessWarningPreference();
          renderIngestPresetGuidance();
          renderIngestChecklistProgress();
        }
        return generateChanged || ingestChanged;
      }

      async function loadServerPresetBundle() {
        try {
          const body = await apiFetch("/demo/presets");
          return applyServerPresetBundle(body);
        } catch (err) {
          return false;
        }
      }

      async function loadServerIngestPresets() {
        let listBody;
        try {
          listBody = await apiFetch("/ingest/presets");
        } catch (err) {
          return;
        }
        const rows = Array.isArray(listBody?.presets) ? listBody.presets : [];
        if (!rows.length) return;

        const merged = { ...(INGEST_PRESETS || {}) };
        let changed = false;
        for (const row of rows) {
          if (!row || typeof row !== "object") continue;
          const presetKey = String(row.preset_key || "").trim();
          if (!presetKey) continue;
          try {
            const detail = await apiFetch(`/ingest/presets/${encodeURIComponent(presetKey)}`);
            const metadata =
              detail && typeof detail.metadata === "object" && !Array.isArray(detail.metadata)
                ? { ...detail.metadata }
                : {};
            const checklistItems = Array.isArray(detail?.checklist_items) ? detail.checklist_items : [];
            const recommendedDocs = Array.isArray(detail?.recommended_docs) ? detail.recommended_docs : [];
            const donorId = String(detail?.donor_id || row.donor_id || "").trim();
            merged[presetKey] = {
              donor_id: donorId,
              metadata,
              checklist_items: checklistItems,
              recommended_docs: recommendedDocs,
            };
            const donorLabel = donorId ? donorId.toUpperCase() : "INGEST";
            const title = String(detail?.title || row.title || presetKey).trim();
            SERVER_INGEST_PRESET_LABELS[presetKey] = `${donorLabel}: ${title}`;
            changed = true;
          } catch (err) {
            // Keep local fallback presets when server detail lookup fails.
          }
        }

        if (changed) {
          INGEST_PRESETS = merged;
          const storedPreset = localStorage.getItem("grantflow_demo_ingest_preset") || "";
          const preferredValue = String(els.ingestPresetSelect.value || "").trim() || String(storedPreset || "").trim();
          renderIngestPresetOptions({ preferredValue });
          renderIngestPresetGuidance();
          renderIngestChecklistProgress();
          renderGeneratePresetReadiness();
          renderZeroReadinessWarningPreference();
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
        els.portfolioToCTextRiskLevelFilter.value = "";
        els.portfolioMelRiskLevelFilter.value = "";
        els.portfolioSlaHotspotKindFilter.value = "";
        els.portfolioSlaHotspotSeverityFilter.value = "";
        els.portfolioSlaMinOverdueHoursFilter.value = "";
        els.portfolioSlaTopLimitFilter.value = "10";
        persistUiState();
      }

      function clearPortfolioToCTextRiskFilter() {
        els.portfolioToCTextRiskLevelFilter.value = "";
        persistUiState();
        refreshPortfolioBundle().catch(showError);
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
        els.reviewWorkflowFindingCodeFilter.value = "";
        els.reviewWorkflowFindingSectionFilter.value = "";
        els.reviewWorkflowCommentStatusFilter.value = "";
        els.reviewWorkflowStateFilter.value = "";
        els.reviewWorkflowOverdueHoursFilter.value = "48";
        els.reviewWorkflowSlaHotspotKindFilter.value = "";
        els.reviewWorkflowSlaHotspotSeverityFilter.value = "";
        els.reviewWorkflowSlaMinOverdueHoursFilter.value = "";
        els.reviewWorkflowSlaTopLimitFilter.value = "10";
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

      function productionExportEnabled() {
        return String(els.productionExportMode?.value || "").toLowerCase() === "true";
      }

      function allowUnsafeExportEnabled() {
        return String(els.allowUnsafeExport?.value || "").toLowerCase() === "true";
      }

      function normalizeRiskLevel(raw) {
        const token = String(raw || "").trim().toLowerCase();
        if (["high", "medium", "low", "none"].includes(token)) return token;
        return "none";
      }

      function renderExportContract(contract) {
        if (!els.exportContractPill || !els.exportContractPillText) return;
        const gate = contract && typeof contract === "object" ? contract : null;
        const mode = gate ? String(gate.mode || "-") : "-";
        const status = gate ? String(gate.status || "unknown").toLowerCase() : "not_loaded";
        const summary = gate ? String(gate.summary || "-") : "-";
        const riskFromGate = gate ? String(gate.risk_level || "").toLowerCase() : "";
        const fallbackRisk = status === "pass" ? "low" : status === "warning" ? "medium" : "none";
        const risk = normalizeRiskLevel(riskFromGate || fallbackRisk);
        const missingSections = gate && Array.isArray(gate.missing_required_sections)
          ? gate.missing_required_sections.map((x) => String(x || "").trim()).filter(Boolean)
          : [];
        const missingSheets = gate && Array.isArray(gate.missing_required_sheets)
          ? gate.missing_required_sheets.map((x) => String(x || "").trim()).filter(Boolean)
          : [];
        const reasons = gate && Array.isArray(gate.reasons)
          ? gate.reasons.map((x) => String(x || "").trim()).filter(Boolean)
          : [];
        const warnings = gate && Array.isArray(gate.warnings)
          ? gate.warnings.map((x) => String(x || "").trim()).filter(Boolean)
          : [];
        const warningSet = Array.from(new Set([...reasons, ...warnings]));

        els.exportContractPill.className = `pill readiness-level-${risk}`;
        const displayStatus = status === "not_loaded" ? "not loaded" : status;
        els.exportContractPillText.textContent = `${displayStatus} (${mode})`;
        els.exportContractPill.title = `summary=${summary}`;

        if (els.exportContractMetaLine) {
          els.exportContractMetaLine.textContent =
            `mode=${mode} · status=${displayStatus} · risk=${risk} · missing_sections=${missingSections.length} · missing_sheets=${missingSheets.length}`;
        }

        if (!els.exportContractWarningsList) return;
        els.exportContractWarningsList.innerHTML = "";
        if (!gate) {
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `<div class="title">Export contract is not loaded</div><div class="sub">Click "Load Export Payload" to fetch current contract gate.</div>`;
          els.exportContractWarningsList.appendChild(div);
          return;
        }

        const severityClass = risk === "high" ? "severity-high" : risk === "medium" ? "severity-medium" : "severity-low";
        if (missingSections.length) {
          const div = document.createElement("div");
          div.className = `item ${severityClass}`.trim();
          div.innerHTML =
            `<div class="title">Missing required ToC sections</div><div class="sub mono">${missingSections.join(", ")}</div>`;
          els.exportContractWarningsList.appendChild(div);
        }
        if (missingSheets.length) {
          const div = document.createElement("div");
          div.className = `item ${severityClass}`.trim();
          div.innerHTML =
            `<div class="title">Missing required workbook sheets</div><div class="sub mono">${missingSheets.join(", ")}</div>`;
          els.exportContractWarningsList.appendChild(div);
        }
        if (warningSet.length) {
          const div = document.createElement("div");
          div.className = `item ${severityClass}`.trim();
          div.innerHTML =
            `<div class="title">Gate reasons</div><div class="sub mono">${warningSet.join(", ")}</div>`;
          els.exportContractWarningsList.appendChild(div);
        }
        if (!missingSections.length && !missingSheets.length && !warningSet.length) {
          const div = document.createElement("div");
          div.className = "item severity-low";
          div.innerHTML = `<div class="title">Export contract is clean</div><div class="sub">No missing required sections or sheets.</div>`;
          els.exportContractWarningsList.appendChild(div);
        }
      }

      async function clearDemoFilters() {
        for (const [elKey] of uiStateFields) {
          const el = els[elKey];
          if (!el) continue;
          el.value = "";
        }
        if (els.productionExportMode) els.productionExportMode.value = "false";
        if (els.allowUnsafeExport) els.allowUnsafeExport.value = "false";
        persistUiState();
        if (state.lastCritic) renderCriticLists(state.lastCritic);
        if (state.lastCitations) renderCriticContextCitations();
        renderExportContract(null);
        renderGeneratePreflightAlert(null);
        renderGeneratePresetReadiness();
        await Promise.allSettled([
          refreshPortfolioBundle(),
          refreshComments(),
          refreshReviewWorkflow(),
          refreshReviewWorkflowTrends(),
          refreshDiff(),
        ]);
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

      function buildPresetReadinessMetadata(presetKey, donorId) {
        const key = String(presetKey || "").trim();
        if (!key) return null;
        const ingestPreset = INGEST_PRESETS[key];
        const checklistItems = Array.isArray(ingestPreset?.checklist_items) ? ingestPreset.checklist_items : [];
        const expectedDocFamilies = checklistItems
          .map((item) => String(item?.id || "").trim())
          .filter((itemId, idx, arr) => itemId && arr.indexOf(itemId) === idx);
        return {
          demo_generate_preset_key: key,
          donor_id: String(donorId || "").trim() || null,
          rag_readiness: {
            expected_doc_families: expectedDocFamilies,
            donor_id: String(ingestPreset?.donor_id || donorId || "").trim() || null,
          },
        };
      }

      function parseExtraInputContext() {
        let extraContext = {};
        const extraJsonText = String(els.inputContextJson.value || "").trim();
        if (!extraJsonText) return extraContext;
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
        return extraContext;
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
        await syncIngestChecklistFromServer();

        const donorId = String(els.donorId.value || els.ingestDonorId.value || "").trim();
        if (!donorId) throw new Error("Missing donor_id for readiness sync");

        const extraContext = parseExtraInputContext();
        const inputContext = {
          ...extraContext,
          project: String(els.project.value || "").trim(),
          country: String(els.country.value || "").trim(),
        };
        const metadata = buildPresetReadinessMetadata(generatePresetKey, donorId);
        const expectedDocFamilies = Array.isArray(metadata?.rag_readiness?.expected_doc_families)
          ? metadata.rag_readiness.expected_doc_families
          : [];

        const readiness = await apiFetch("/ingest/readiness", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            donor_id: donorId,
            input_context: inputContext,
            expected_doc_families: expectedDocFamilies,
            client_metadata: metadata || null,
          }),
        });
        renderGeneratePreflightAlert(readiness);
        return readiness;
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
        const nonRetrievalRate = Number(metrics.non_retrieval_citation_rate ?? NaN);
        const retrievalGroundedRate = Number(metrics.retrieval_grounded_citation_rate ?? NaN);
        const citationCount = Number(metrics.citation_count ?? 0);
        const fallbackCount = Number(metrics.fallback_namespace_citation_count ?? 0);
        const strategyReferenceCount = Number(metrics.strategy_reference_citation_count ?? 0);
        const nonRetrievalCount = Number(metrics.non_retrieval_citation_count ?? 0);
        const retrievalGroundedCount = Number(metrics.retrieval_grounded_citation_count ?? 0);
        const retrievalExpected =
          typeof metrics.retrieval_expected === "boolean" ? String(metrics.retrieval_expected) : "-";
        const groundingRisk = String(metrics.grounding_risk_level || "unknown").toLowerCase();
        const groundingRiskValue = Number.isFinite(nonRetrievalRate)
          ? `${groundingRisk} (${(nonRetrievalRate * 100).toFixed(1)}%)`
          : groundingRisk;
        const values = [
          fmtSec(metrics.time_to_first_draft_seconds),
          fmtSec(metrics.time_to_terminal_seconds),
          fmtSec(metrics.time_in_pending_hitl_seconds),
          String(metrics.pause_count ?? "-"),
          String(metrics.resume_count ?? "-"),
          String(metrics.terminal_status ?? metrics.status ?? "-"),
          groundingRiskValue,
        ];
        const valueNodes = [...els.metricsCards.querySelectorAll(".kpi .value")];
        valueNodes.forEach((node, i) => {
          node.textContent = values[i] ?? "-";
        });
        const groundingRiskNode = valueNodes[6];
        if (groundingRiskNode) {
          setRiskClass(groundingRiskNode, groundingRisk);
          groundingRiskNode.title =
            citationCount > 0
              ? `non_retrieval=${nonRetrievalCount}/${citationCount} (${Number.isFinite(nonRetrievalRate) ? (nonRetrievalRate * 100).toFixed(1) + "%" : "-"})` +
                ` · retrieval_grounded=${retrievalGroundedCount}/${citationCount} (${Number.isFinite(retrievalGroundedRate) ? (retrievalGroundedRate * 100).toFixed(1) + "%" : "-"})` +
                ` · fallback=${fallbackCount} · strategy_ref=${strategyReferenceCount} · retrieval_expected=${retrievalExpected}`
              : `No citations · retrieval_expected=${retrievalExpected}`;
        }
      }

      function renderWorkerHeartbeat(payload) {
        const body = payload && typeof payload === "object" ? payload : {};
        const policy = String((body.policy && body.policy.mode) || "strict").toLowerCase();
        const heartbeat = body.heartbeat && typeof body.heartbeat === "object" ? body.heartbeat : {};
        const present = heartbeat.present === true;
        const healthy = heartbeat.healthy === true;
        const source = heartbeat.source ? String(heartbeat.source) : "-";
        const consumerEnabled = typeof body.consumer_enabled === "boolean" ? String(body.consumer_enabled) : "-";
        const ageRaw = Number(heartbeat.age_seconds);
        const ageText = Number.isFinite(ageRaw) ? `${ageRaw.toFixed(ageRaw >= 10 ? 1 : 2)}s` : "-";

        let pillClass = "pill status-unknown";
        if (healthy) pillClass = "pill status-done";
        else if (policy === "warn") pillClass = "pill status-pending_hitl";
        else if (policy === "off") pillClass = "pill status-accepted";
        else pillClass = "pill status-error";
        els.workerHeartbeatPill.className = pillClass;
        els.workerHeartbeatPillText.textContent = `policy=${policy} · healthy=${healthy ? "yes" : "no"} · present=${present ? "yes" : "no"}`;
        els.workerHeartbeatMetaLine.textContent = `consumer_enabled=${consumerEnabled} · source=${source} · age=${ageText}`;
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

      function setRiskClass(node, levelRaw) {
        if (!node) return;
        const level = normalizeRiskLevel(levelRaw);
        node.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
        node.classList.add(`risk-${level}`);
      }

      function groundingLevelFromSupportRate(rateRaw) {
        const rate = Number(rateRaw);
        if (!Number.isFinite(rate)) return "none";
        if (rate < 0.5) return "high";
        if (rate < 0.7) return "medium";
        return "low";
      }

      function groundingLevelFromFallbackRate(rateRaw) {
        const rate = Number(rateRaw);
        if (!Number.isFinite(rate)) return "none";
        if (rate >= 0.8) return "high";
        if (rate >= 0.5) return "medium";
        return "low";
      }

      function groundingLevelFromGapRate(rateRaw) {
        const rate = Number(rateRaw);
        if (!Number.isFinite(rate)) return "none";
        if (rate >= 0.6) return "high";
        if (rate >= 0.3) return "medium";
        return "low";
      }

      function renderGroundingKpiCards(summary) {
        if (!els.groundingKpiCards) return;
        const citations = summary?.citations || {};
        const preflight = summary?.preflight || {};
        const preflightPolicy =
          preflight && typeof preflight.grounding_policy === "object" && !Array.isArray(preflight.grounding_policy)
            ? preflight.grounding_policy
            : {};
        const melPolicy =
          summary?.mel_grounding_policy &&
          typeof summary.mel_grounding_policy === "object" &&
          !Array.isArray(summary.mel_grounding_policy)
            ? summary.mel_grounding_policy
            : {};
        const overallGroundingRisk = String(citations?.grounding_risk_level || "unknown").toLowerCase();
        const preflightGroundingRisk = String(
          preflight?.grounding_risk_level || preflightPolicy?.risk_level || "unknown"
        ).toLowerCase();
        const policyMode = String(preflightPolicy?.mode || "-");
        const policyBlockingRaw = preflightPolicy?.blocking;
        const policyBlocking =
          typeof policyBlockingRaw === "boolean" ? (policyBlockingRaw ? "true" : "false") : "-";
        const citationCount = Number(citations?.citation_count ?? 0);
        const fallbackCount = Number(citations?.fallback_namespace_citation_count ?? 0);
        const strategyReferenceCount = Number(citations?.strategy_reference_citation_count ?? 0);
        const retrievalGroundedCount = Number(citations?.retrieval_grounded_citation_count ?? 0);
        const nonRetrievalCount = Number(citations?.non_retrieval_citation_count ?? fallbackCount + strategyReferenceCount);
        const nonRetrievalRate = Number(citations?.non_retrieval_citation_rate ?? NaN);
        const retrievalGroundedRate = Number(citations?.retrieval_grounded_citation_rate ?? NaN);
        const traceabilityCompleteCount = Number(citations?.traceability_complete_citation_count ?? 0);
        const traceabilityGapCount = Number(citations?.traceability_gap_citation_count ?? 0);
        const traceabilityCompleteRate = citationCount > 0 ? traceabilityCompleteCount / citationCount : NaN;
        const traceabilityGapRate = Number(citations?.traceability_gap_citation_rate ?? NaN);
        const architectClaimSupportRate = Number(citations?.architect_claim_support_rate ?? NaN);
        const architectThresholdHitRate = Number(citations?.architect_threshold_hit_rate ?? NaN);
        const melClaimSupportRate = Number(citations?.mel_claim_support_rate ?? NaN);
        const melNonRetrievalRate = Number(citations?.mel_non_retrieval_citation_rate ?? NaN);
        const fmtRate = (rawRate) => {
          const rate = Number(rawRate);
          return Number.isFinite(rate) ? `${(rate * 100).toFixed(1)}%` : "-";
        };
        const values = [
          overallGroundingRisk || "-",
          preflightGroundingRisk || "-",
          policyMode || "-",
          policyBlocking,
          String(citationCount || 0),
          fmtRate(nonRetrievalRate),
          fmtRate(traceabilityCompleteRate),
          fmtRate(traceabilityGapRate),
          fmtRate(architectClaimSupportRate),
          fmtRate(architectThresholdHitRate),
          fmtRate(melClaimSupportRate),
          fmtRate(melNonRetrievalRate),
        ];
        const groundingValueNodes = [...els.groundingKpiCards.querySelectorAll(".kpi .value")];
        groundingValueNodes.forEach((node, i) => {
          node.textContent = values[i] ?? "-";
          node.title = "";
        });
        setRiskClass(groundingValueNodes[0], overallGroundingRisk);
        setRiskClass(groundingValueNodes[1], preflightGroundingRisk);
        setRiskClass(
          groundingValueNodes[3],
          policyBlocking === "true" ? "high" : policyBlocking === "false" ? "low" : "none"
        );
        setRiskClass(groundingValueNodes[5], groundingLevelFromFallbackRate(nonRetrievalRate));
        setRiskClass(groundingValueNodes[6], groundingLevelFromSupportRate(traceabilityCompleteRate));
        setRiskClass(groundingValueNodes[7], groundingLevelFromGapRate(traceabilityGapRate));
        setRiskClass(groundingValueNodes[8], groundingLevelFromSupportRate(architectClaimSupportRate));
        setRiskClass(groundingValueNodes[9], groundingLevelFromSupportRate(architectThresholdHitRate));
        setRiskClass(groundingValueNodes[10], groundingLevelFromSupportRate(melClaimSupportRate));
        setRiskClass(groundingValueNodes[11], groundingLevelFromFallbackRate(melNonRetrievalRate));

        if (groundingValueNodes[5]) {
          groundingValueNodes[5].title =
            citationCount > 0
              ? `${nonRetrievalCount}/${citationCount} non-retrieval citations (fallback=${fallbackCount}, strategy_ref=${strategyReferenceCount})`
              : "No citations";
        }
        if (groundingValueNodes[6]) {
          groundingValueNodes[6].title =
            citationCount > 0
              ? `${traceabilityCompleteCount}/${citationCount} complete traceability citations`
              : "No citations";
        }
        if (groundingValueNodes[7]) {
          groundingValueNodes[7].title =
            citationCount > 0
              ? `${traceabilityGapCount}/${citationCount} traceability gap citations`
              : "No citations";
        }
        if (els.groundingKpiMetaLine) {
          const nonRetrievalRateLabel = fmtRate(nonRetrievalRate);
          const retrievalGroundedRateLabel = fmtRate(retrievalGroundedRate);
          const traceabilityGapRateLabel = fmtRate(traceabilityGapRate);
          els.groundingKpiMetaLine.textContent =
            `citation_count=${citationCount} · non_retrieval=${nonRetrievalCount} (${nonRetrievalRateLabel})` +
            ` · retrieval_grounded=${retrievalGroundedCount} (${retrievalGroundedRateLabel})` +
            ` · traceability_gap=${traceabilityGapCount} (${traceabilityGapRateLabel})`;
        }

        renderKeyValueList(
          els.groundingKpiCountsList,
          {
            citation_count: citationCount,
            architect_citation_count: Number(citations?.architect_citation_count ?? 0),
            mel_citation_count: Number(citations?.mel_citation_count ?? 0),
            fallback_namespace_citation_count: fallbackCount,
            strategy_reference_citation_count: strategyReferenceCount,
            retrieval_grounded_citation_count: retrievalGroundedCount,
            non_retrieval_citation_count: nonRetrievalCount,
            rag_low_confidence_citation_count: Number(citations?.rag_low_confidence_citation_count ?? 0),
            traceability_complete_citation_count: traceabilityCompleteCount,
            traceability_partial_citation_count: Number(citations?.traceability_partial_citation_count ?? 0),
            traceability_missing_citation_count: Number(citations?.traceability_missing_citation_count ?? 0),
            traceability_gap_citation_count: traceabilityGapCount,
          },
          "No grounding counts for this job.",
          12
        );

        if (els.groundingKpiPolicyReasonsList) {
          const preflightReasons = Array.isArray(preflightPolicy?.reasons)
            ? preflightPolicy.reasons.map((item) => String(item || "").trim()).filter(Boolean)
            : [];
          const melReasons = Array.isArray(melPolicy?.reasons)
            ? melPolicy.reasons.map((item) => String(item || "").trim()).filter(Boolean)
            : [];
          const runtimeGate =
            summary?.grounded_gate && typeof summary.grounded_gate === "object" && !Array.isArray(summary.grounded_gate)
              ? summary.grounded_gate
              : {};
          const runtimeReasonDetails = Array.isArray(runtimeGate?.reason_details)
            ? runtimeGate.reason_details.filter((item) => item && typeof item === "object")
            : [];
          const runtimeReasons = Array.isArray(runtimeGate?.reasons)
            ? runtimeGate.reasons.map((item) => String(item || "").trim()).filter(Boolean)
            : [];
          const architectClaims =
            preflight?.architect_claims && typeof preflight.architect_claims === "object"
              ? preflight.architect_claims
              : null;
          let architectClaimsSummary = "";
          if (architectClaims && Object.keys(architectClaims).length > 0) {
            const available = Boolean(architectClaims.available);
            if (available) {
              const claimCount = Number(architectClaims.claim_citation_count ?? 0);
              const keyCoverage = Number(architectClaims.key_claim_coverage_ratio ?? NaN);
              const fallbackRatio = Number(architectClaims.fallback_claim_ratio ?? NaN);
              const thresholdHit = Number(architectClaims.threshold_hit_rate ?? NaN);
              const fmtRate = (rawRate) => {
                const rate = Number(rawRate);
                return Number.isFinite(rate) ? `${(rate * 100).toFixed(1)}%` : "-";
              };
              architectClaimsSummary =
                `claims=${claimCount}` +
                ` · key_cov=${fmtRate(keyCoverage)}` +
                ` · fallback=${fmtRate(fallbackRatio)}` +
                ` · threshold_hit=${fmtRate(thresholdHit)}`;
            } else {
              architectClaimsSummary = `claims=n/a · reason=${String(architectClaims.reason || "not_evaluated")}`;
            }
          }
          const rows = [
            ...(architectClaimsSummary ? [{ title: "architect_claims", value: architectClaimsSummary }] : []),
            ...runtimeReasonDetails.map((item) => ({
              title: "runtime_gate",
              value:
                `${String(item.message || item.code || "gate_reason")}` +
                ` · section=${String(item.section || "overall")}` +
                (item.observed !== undefined ? ` · observed=${String(item.observed)}` : "") +
                (item.threshold !== undefined ? ` · threshold=${String(item.threshold)}` : ""),
            })),
            ...(!runtimeReasonDetails.length ? runtimeReasons.map((reason) => ({ title: "runtime_gate", value: reason })) : []),
            ...preflightReasons.map((reason) => ({ title: "preflight", value: reason })),
            ...melReasons.map((reason) => ({ title: "mel", value: reason })),
          ];
          els.groundingKpiPolicyReasonsList.innerHTML = "";
          if (!rows.length) {
            const div = document.createElement("div");
            div.className = "item severity-low";
            div.innerHTML =
              `<div class="title">No policy reasons</div>` +
              `<div class="sub mono">preflight_mode=${escapeHtml(policyMode)} · preflight_blocking=${escapeHtml(policyBlocking)}</div>`;
            els.groundingKpiPolicyReasonsList.appendChild(div);
          } else {
            for (const row of rows) {
              const div = document.createElement("div");
              const severity = policyBlocking === "true" ? "high" : "medium";
              div.className = `item severity-${severity}`;
              div.innerHTML =
                `<div class="title mono">${escapeHtml(row.title)}</div>` +
                `<div class="sub mono">${escapeHtml(row.value)}</div>`;
              els.groundingKpiPolicyReasonsList.appendChild(div);
            }
          }
        }
      }

      function renderQualityCards(summary) {
        const critic = summary?.critic || {};
        const citations = summary?.citations || {};
        const mel = summary?.mel || {};
        const readiness = summary?.readiness || {};
        const preflight = summary?.preflight || {};
        const groundedGate =
          summary?.grounded_gate && typeof summary.grounded_gate === "object" && !Array.isArray(summary.grounded_gate)
            ? summary.grounded_gate
            : {};
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
        const groundedGateMode = String(groundedGate?.mode || "-");
        const groundedGatePassed = groundedGate?.passed;
        const groundedGateBlocking = groundedGate?.blocking;
        const groundedGateApplicable = groundedGate?.applicable;
        const groundedGateReasons = Array.isArray(groundedGate?.reasons)
          ? groundedGate.reasons.map((x) => String(x || "").trim()).filter(Boolean)
          : [];
        let groundedGateStatus = "-";
        if (groundedGateApplicable === false) groundedGateStatus = "n/a";
        else if (groundedGateBlocking === true) groundedGateStatus = "blocked";
        else if (groundedGatePassed === true) groundedGateStatus = "pass";
        else if (groundedGatePassed === false) groundedGateStatus = "warn";
        const groundedGateValue =
          groundedGateStatus === "-"
            ? "-"
            : `${groundedGateStatus} (${groundedGateMode}${groundedGateReasons.length ? `, ${groundedGateReasons.length} reasons` : ""})`;
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
          typeof citations.architect_non_retrieval_citation_rate === "number"
            ? `${(Number(citations.architect_non_retrieval_citation_rate) * 100).toFixed(1)}%`
            : "-",
          typeof citations.mel_claim_support_rate === "number"
            ? `${(Number(citations.mel_claim_support_rate) * 100).toFixed(1)}%`
            : "-",
          typeof citations.mel_non_retrieval_citation_rate === "number"
            ? `${(Number(citations.mel_non_retrieval_citation_rate) * 100).toFixed(1)}%`
            : "-",
          preflightRiskValue,
          strictPreflightValue,
          groundedGateValue,
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
          const fallbackRate = Number(citations?.architect_non_retrieval_citation_rate ?? NaN);
          architectFallbackNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (Number.isFinite(fallbackRate)) {
            if (fallbackRate >= 0.8) architectFallbackNode.classList.add("risk-high");
            else if (fallbackRate >= 0.5) architectFallbackNode.classList.add("risk-medium");
            else architectFallbackNode.classList.add("risk-low");
          } else {
            architectFallbackNode.classList.add("risk-none");
          }
          const fallbackCount = Number(citations?.architect_non_retrieval_citation_count ?? 0);
          const architectCount = Number(citations?.architect_citation_count ?? 0);
          architectFallbackNode.title =
            architectCount > 0
              ? `${fallbackCount}/${architectCount} architect non-retrieval citations`
              : "No architect citations";
        }
        const melClaimSupportNode = qualityValueNodes[8];
        if (melClaimSupportNode) {
          const melClaimSupportRate = Number(citations?.mel_claim_support_rate ?? NaN);
          melClaimSupportNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (Number.isFinite(melClaimSupportRate)) {
            if (melClaimSupportRate < 0.5) melClaimSupportNode.classList.add("risk-high");
            else if (melClaimSupportRate < 0.7) melClaimSupportNode.classList.add("risk-medium");
            else melClaimSupportNode.classList.add("risk-low");
          } else {
            melClaimSupportNode.classList.add("risk-none");
          }
          const supportCount = Number(citations?.mel_claim_support_citation_count ?? 0);
          const melCount = Number(citations?.mel_citation_count ?? 0);
          melClaimSupportNode.title =
            melCount > 0 ? `${supportCount}/${melCount} MEL claim-support citations` : "No MEL citations";
        }
        const melFallbackNode = qualityValueNodes[9];
        if (melFallbackNode) {
          const melFallbackRate = Number(citations?.mel_non_retrieval_citation_rate ?? NaN);
          melFallbackNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (Number.isFinite(melFallbackRate)) {
            if (melFallbackRate >= 0.8) melFallbackNode.classList.add("risk-high");
            else if (melFallbackRate >= 0.5) melFallbackNode.classList.add("risk-medium");
            else melFallbackNode.classList.add("risk-low");
          } else {
            melFallbackNode.classList.add("risk-none");
          }
          const fallbackCount = Number(citations?.mel_non_retrieval_citation_count ?? 0);
          const melCount = Number(citations?.mel_citation_count ?? 0);
          melFallbackNode.title =
            melCount > 0 ? `${fallbackCount}/${melCount} MEL non-retrieval citations` : "No MEL citations";
        }
        const preflightRiskNode = qualityValueNodes[10];
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
        const groundedGateNode = qualityValueNodes[12];
        if (groundedGateNode) {
          groundedGateNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (groundedGateApplicable === false) {
            groundedGateNode.classList.add("risk-none");
          } else if (groundedGateBlocking === true) {
            groundedGateNode.classList.add("risk-high");
          } else if (groundedGatePassed === true) {
            groundedGateNode.classList.add("risk-low");
          } else if (groundedGatePassed === false) {
            groundedGateNode.classList.add("risk-medium");
          } else {
            groundedGateNode.classList.add("risk-none");
          }
          const summaryText = String(groundedGate?.summary || "").trim();
          groundedGateNode.title = summaryText
            ? `${summaryText}${groundedGateReasons.length ? ` · reasons=${groundedGateReasons.join(", ")}` : ""}`
            : groundedGateReasons.length
              ? `reasons=${groundedGateReasons.join(", ")}`
              : "No grounded gate summary";
        }
        renderQualityGroundedGateExplain(groundedGate);
        renderKeyValueList(
          els.qualityMelSummaryList,
          {
            engine: mel.engine || "-",
            llm_used: mel.llm_used ?? "-",
            retrieval_used: mel.retrieval_used ?? "-",
            retrieval_hits_count: mel.retrieval_hits_count ?? "-",
            risk_level: mel.risk_level || "unknown",
            avg_retrieval_confidence:
              typeof mel.avg_retrieval_confidence === "number"
                ? Number(mel.avg_retrieval_confidence).toFixed(3)
                : "-",
            indicator_count: Number.isFinite(Number(mel.indicator_count))
              ? Number(mel.indicator_count)
              : "-",
            smart_field_coverage_rate:
              typeof mel.smart_field_coverage_rate === "number"
                ? `${(Number(mel.smart_field_coverage_rate) * 100).toFixed(1)}%`
                : "-",
            baseline_coverage_rate:
              typeof mel.baseline_coverage_rate === "number"
                ? `${(Number(mel.baseline_coverage_rate) * 100).toFixed(1)}%`
                : "-",
            target_coverage_rate:
              typeof mel.target_coverage_rate === "number"
                ? `${(Number(mel.target_coverage_rate) * 100).toFixed(1)}%`
                : "-",
          },
          "No MEL generation summary for this job.",
          10
        );
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
        renderGroundingKpiCards(summary);
        renderQualityReadinessWarnings(readiness);
        state.lastQualitySummary = summary && typeof summary === "object" ? summary : null;
      }

      function renderQualityGroundedGateExplain(groundedGate) {
        if (!els.qualityGroundedGatePill || !els.qualityGroundedGateExplainBtn || !els.qualityGroundedGateReasonsList) {
          return;
        }
        const mode = String(groundedGate?.mode || "-");
        const applicable = groundedGate?.applicable;
        const blocking = groundedGate?.blocking === true;
        const passed = groundedGate?.passed === true;
        const summary = String(groundedGate?.summary || "").trim();
        const reasons = Array.isArray(groundedGate?.reasons)
          ? groundedGate.reasons.map((item) => String(item || "").trim()).filter(Boolean)
          : [];
        const reasonDetails = Array.isArray(groundedGate?.reason_details)
          ? groundedGate.reason_details.filter((item) => item && typeof item === "object")
          : [];
        const evidenceBySection =
          groundedGate?.evidence &&
          groundedGate.evidence.sample_citations_by_section &&
          typeof groundedGate.evidence.sample_citations_by_section === "object"
            ? groundedGate.evidence.sample_citations_by_section
            : {};

        let gateLabel = "unknown";
        let level = "none";
        if (applicable === false) {
          gateLabel = "N/A";
          level = "none";
        } else if (blocking) {
          gateLabel = "BLOCK";
          level = "high";
        } else if (passed) {
          gateLabel = "PASS";
          level = "low";
        } else if (groundedGate?.passed === false) {
          gateLabel = "WARN";
          level = "medium";
        }
        els.qualityGroundedGatePill.className = `pill readiness-level-${level}`;
        const pillTextNode = els.qualityGroundedGatePill.querySelector("span:last-child");
        if (pillTextNode) {
          const reasonCount = reasonDetails.length || reasons.length;
          pillTextNode.textContent =
            `gate=${gateLabel} · mode=${mode}` + (reasonCount > 0 ? ` · reasons=${reasonCount}` : "");
        }
        els.qualityGroundedGateExplainBtn.disabled = !(blocking || reasonDetails.length || reasons.length);
        els.qualityGroundedGateExplainBtn.textContent = state.qualityGroundedGateExplainExpanded
          ? "Hide gate details"
          : "Why blocked?";

        els.qualityGroundedGateReasonsList.innerHTML = "";
        const rows = [];
        if (reasonDetails.length) {
          for (const item of reasonDetails) {
            const code = String(item.code || "gate_reason");
            const section = String(item.section || "overall");
            const observed = item.observed;
            const threshold = item.threshold;
            const detail = String(item.message || "").trim() || code;
            let meta = `section=${section} · code=${code}`;
            if (observed !== undefined) meta += ` · observed=${String(observed)}`;
            if (threshold !== undefined) meta += ` · threshold=${String(threshold)}`;
            rows.push({ title: detail, sub: meta, severity: blocking ? "high" : "medium" });
          }
        } else if (reasons.length) {
          for (const reason of reasons) {
            rows.push({ title: reason, sub: `mode=${mode}`, severity: blocking ? "high" : "medium" });
          }
        } else {
          rows.push({
            title: summary || "Grounded gate has no blocking reasons.",
            sub: `mode=${mode} · applicable=${String(applicable)}`,
            severity: passed ? "low" : "medium",
          });
        }

        for (const row of rows.slice(0, 10)) {
          const div = document.createElement("div");
          div.className = `item severity-${row.severity}`;
          div.innerHTML = `<div class="title">${escapeHtml(row.title)}</div><div class="sub mono">${escapeHtml(row.sub)}</div>`;
          els.qualityGroundedGateReasonsList.appendChild(div);
        }

        const evidenceEntries = Object.entries(evidenceBySection)
          .filter(([, items]) => Array.isArray(items))
          .slice(0, 2);
        for (const [section, itemsRaw] of evidenceEntries) {
          const items = itemsRaw.filter((item) => item && typeof item === "object").slice(0, 2);
          for (const item of items) {
            const citationType = String(item.citation_type || "unknown");
            const source = String(item.source || item.doc_id || "citation");
            const statementPath = String(item.statement_path || "");
            const confidence = item.retrieval_confidence;
            const confLabel =
              typeof confidence === "number" ? confidence.toFixed(3) : String(confidence || "-");
            const div = document.createElement("div");
            div.className = "item severity-low";
            div.innerHTML =
              `<div class="title mono">evidence:${escapeHtml(section)}:${escapeHtml(citationType)}</div>` +
              `<div class="sub mono">${escapeHtml(source)} · statement_path=${escapeHtml(statementPath || "-")} · retrieval_confidence=${escapeHtml(confLabel)}</div>`;
            els.qualityGroundedGateReasonsList.appendChild(div);
          }
        }

        if (els.qualityGroundedGateReasonsWrap) {
          els.qualityGroundedGateReasonsWrap.classList.toggle("hidden", !state.qualityGroundedGateExplainExpanded);
        }
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
        const tocTextQuality = summary?.toc_text_quality || {};
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
        const tocHighRiskRate =
          typeof tocTextQuality?.high_risk_job_rate === "number"
            ? Number(tocTextQuality.high_risk_job_rate)
            : (typeof tocTextQuality?.risk_job_rates?.high === "number" ? Number(tocTextQuality.risk_job_rates.high) : NaN);
        const tocHighRiskRateLabel = Number.isFinite(tocHighRiskRate) ? `${(tocHighRiskRate * 100).toFixed(1)}%` : "-";
        const tocTextIssuesTotal = Number(tocTextQuality?.issues_total ?? 0);
        const groundedGatePresentCount = Number(summary?.grounded_gate_present_job_count ?? 0);
        const groundedGateBlockedCount = Number(summary?.grounded_gate_blocked_job_count ?? 0);
        const groundedGatePassedCount = Number(summary?.grounded_gate_passed_job_count ?? 0);
        const groundedGateBlockRateRaw =
          typeof summary?.grounded_gate_block_rate === "number"
            ? Number(summary.grounded_gate_block_rate)
            : (
              portfolioJobCount > 0
                ? (groundedGateBlockedCount / portfolioJobCount)
                : NaN
            );
        const groundedGateBlockRateLabel = Number.isFinite(groundedGateBlockRateRaw)
          ? `${(groundedGateBlockRateRaw * 100).toFixed(1)}%`
          : "-";
        const groundedGatePassRatePresentRaw =
          typeof summary?.grounded_gate_pass_rate_among_present === "number"
            ? Number(summary.grounded_gate_pass_rate_among_present)
            : (
              groundedGatePresentCount > 0
                ? (groundedGatePassedCount / groundedGatePresentCount)
                : NaN
            );
        const groundedGatePassRatePresentLabel = Number.isFinite(groundedGatePassRatePresentRaw)
          ? `${(groundedGatePassRatePresentRaw * 100).toFixed(1)}%`
          : "-";
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
          tocHighRiskRateLabel,
          String(tocTextIssuesTotal),
          groundedGateBlockRateLabel,
          `${groundedGateBlockedCount}/${portfolioJobCount}`,
          groundedGatePassRatePresentLabel,
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
        const tocHighRiskNode = portfolioQualityValueNodes[15];
        if (tocHighRiskNode) {
          tocHighRiskNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (Number.isFinite(tocHighRiskRate)) {
            if (tocHighRiskRate >= 0.5) tocHighRiskNode.classList.add("risk-high");
            else if (tocHighRiskRate >= 0.2) tocHighRiskNode.classList.add("risk-medium");
            else tocHighRiskNode.classList.add("risk-low");
          } else {
            tocHighRiskNode.classList.add("risk-none");
          }
          const highRiskCount = Number(tocTextQuality?.high_risk_job_count ?? tocTextQuality?.risk_counts?.high ?? 0);
          tocHighRiskNode.title =
            portfolioJobCount > 0
              ? `${highRiskCount} jobs with high ToC text risk out of ${portfolioJobCount} · click to filter`
              : "No portfolio jobs in current filter";
          tocHighRiskNode.style.cursor = portfolioJobCount > 0 ? "pointer" : "default";
          tocHighRiskNode.onclick = portfolioJobCount > 0 ? () => applyPortfolioToCTextRiskLevelFilter("high") : null;
        }
        const tocIssuesNode = portfolioQualityValueNodes[16];
        if (tocIssuesNode) {
          tocIssuesNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (tocTextIssuesTotal > 0) tocIssuesNode.classList.add("risk-medium");
          else tocIssuesNode.classList.add("risk-none");
          const placeholderCount = Number(tocTextQuality?.placeholder_finding_count ?? 0);
          const repetitionCount = Number(tocTextQuality?.repetition_finding_count ?? 0);
          tocIssuesNode.title = `placeholder=${placeholderCount} · repetition=${repetitionCount}`;
        }
        const groundedGateBlockRateNode = portfolioQualityValueNodes[17];
        if (groundedGateBlockRateNode) {
          groundedGateBlockRateNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (Number.isFinite(groundedGateBlockRateRaw)) {
            if (groundedGateBlockRateRaw >= 0.5) groundedGateBlockRateNode.classList.add("risk-high");
            else if (groundedGateBlockRateRaw > 0.0) groundedGateBlockRateNode.classList.add("risk-medium");
            else groundedGateBlockRateNode.classList.add("risk-low");
          } else {
            groundedGateBlockRateNode.classList.add("risk-none");
          }
          groundedGateBlockRateNode.title =
            portfolioJobCount > 0
              ? `${groundedGateBlockedCount} blocked jobs out of ${portfolioJobCount}`
              : "No portfolio jobs in current filter";
        }
        const groundedGateBlockedCountNode = portfolioQualityValueNodes[18];
        if (groundedGateBlockedCountNode) {
          groundedGateBlockedCountNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (groundedGateBlockedCount > 0) groundedGateBlockedCountNode.classList.add("risk-high");
          else groundedGateBlockedCountNode.classList.add("risk-none");
          groundedGateBlockedCountNode.title = `present gate jobs: ${groundedGatePresentCount}`;
        }
        const groundedGatePassRateNode = portfolioQualityValueNodes[19];
        if (groundedGatePassRateNode) {
          groundedGatePassRateNode.classList.remove("risk-high", "risk-medium", "risk-low", "risk-none");
          if (Number.isFinite(groundedGatePassRatePresentRaw)) {
            if (groundedGatePassRatePresentRaw < 0.5) groundedGatePassRateNode.classList.add("risk-high");
            else if (groundedGatePassRatePresentRaw < 0.8) groundedGatePassRateNode.classList.add("risk-medium");
            else groundedGatePassRateNode.classList.add("risk-low");
          } else {
            groundedGatePassRateNode.classList.add("risk-none");
          }
          groundedGatePassRateNode.title =
            groundedGatePresentCount > 0
              ? `${groundedGatePassedCount}/${groundedGatePresentCount} grounded gate pass`
              : "No runtime grounded gate records in current filter";
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
        const melSummary = summary?.mel || {};
        renderKeyValueList(
          els.portfolioQualityMelSummaryList,
          {
            indicator_job_count: Number(melSummary.indicator_job_count ?? 0),
            indicator_count_total: Number(melSummary.indicator_count_total ?? 0),
            risk_level: melSummary.risk_level || "unknown",
            avg_indicator_count_per_job:
              typeof melSummary.avg_indicator_count_per_job === "number"
                ? Number(melSummary.avg_indicator_count_per_job).toFixed(2)
                : "-",
            smart_field_coverage_rate:
              typeof melSummary.smart_field_coverage_rate === "number"
                ? `${(Number(melSummary.smart_field_coverage_rate) * 100).toFixed(1)}%`
                : "-",
            baseline_coverage_rate:
              typeof melSummary.baseline_coverage_rate === "number"
                ? `${(Number(melSummary.baseline_coverage_rate) * 100).toFixed(1)}%`
                : "-",
            target_coverage_rate:
              typeof melSummary.target_coverage_rate === "number"
                ? `${(Number(melSummary.target_coverage_rate) * 100).toFixed(1)}%`
                : "-",
            formula_coverage_rate:
              typeof melSummary.formula_coverage_rate === "number"
                ? `${(Number(melSummary.formula_coverage_rate) * 100).toFixed(1)}%`
                : "-",
            data_source_coverage_rate:
              typeof melSummary.data_source_coverage_rate === "number"
                ? `${(Number(melSummary.data_source_coverage_rate) * 100).toFixed(1)}%`
                : "-",
          },
          "No portfolio MEL summary yet.",
          10
        );
        renderKeyValueList(
          els.portfolioQualityGroundedGateSectionsList,
          summary?.grounded_gate_section_fail_counts,
          "No grounded-gate failed sections yet.",
          8,
          (sectionKey) => {
            applyRuntimeGroundedGateReviewWorkflowDrilldown({ section: sectionKey }).catch(showError);
          }
        );
        renderKeyValueList(
          els.portfolioQualityGroundedGateReasonsList,
          summary?.grounded_gate_reason_counts,
          "No grounded-gate reason codes yet.",
          8,
          (reasonCode) => {
            applyRuntimeGroundedGateReviewWorkflowDrilldown({ reasonCode }).catch(showError);
          }
        );
        renderDonorGroundedGateList(
          els.portfolioQualityGroundedGateDonorsList,
          summary?.donor_grounded_gate_breakdown,
          "No donor grounded-gate block data yet.",
          8,
          (donorKey) => applyPortfolioDonorFilter(donorKey)
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
          .map(([k, v]) => {
            const key = String(k);
            const numericValue = Number(v);
            const isFiniteNumber = Number.isFinite(numericValue);
            return {
              key,
              displayValue:
                v === null || v === undefined
                  ? "-"
                  : typeof v === "object"
                    ? JSON.stringify(v)
                    : String(v),
              sortNumeric: isFiniteNumber ? numericValue : null,
            };
          })
          .sort((a, b) => {
            const aNum = a.sortNumeric;
            const bNum = b.sortNumeric;
            if (aNum !== null && bNum !== null) {
              return bNum - aNum || a.key.localeCompare(b.key);
            }
            if (aNum !== null) return -1;
            if (bNum !== null) return 1;
            return a.key.localeCompare(b.key);
          })
          .slice(0, topN);
        if (entries.length === 0) {
          container.innerHTML = `<div class="item"><div class="sub">${escapeHtml(emptyLabel)}</div></div>`;
          return;
        }
        for (const row of entries) {
          const key = row.key;
          const value = row.displayValue;
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

      function renderDonorGroundedGateList(container, mapping, emptyLabel, topN = 8, onSelect = null) {
        container.innerHTML = "";
        if (!mapping || typeof mapping !== "object" || Array.isArray(mapping)) {
          container.innerHTML = `<div class="item"><div class="sub">${escapeHtml(emptyLabel)}</div></div>`;
          return;
        }
        const entries = Object.entries(mapping)
          .map(([donorId, row]) => {
            const rec = row && typeof row === "object" && !Array.isArray(row) ? row : {};
            const blocked = Number(rec.blocked_job_count || 0);
            const present = Number(rec.present_job_count || 0);
            const blockRate = typeof rec.block_rate === "number" ? Number(rec.block_rate) : -1;
            return [String(donorId), rec, blocked, present, blockRate];
          })
          .sort((a, b) => b[2] - a[2] || b[4] - a[4] || a[0].localeCompare(b[0]))
          .slice(0, topN);
        if (!entries.length) {
          container.innerHTML = `<div class="item"><div class="sub">${escapeHtml(emptyLabel)}</div></div>`;
          return;
        }
        for (const [donorId, row, blocked, present, blockRate] of entries) {
          const cls = blocked > 0 ? "severity-high" : "severity-low";
          const passRateLabel =
            typeof row.pass_rate_among_present === "number"
              ? `${(Number(row.pass_rate_among_present) * 100).toFixed(1)}%`
              : "-";
          const blockRateLabel = blockRate >= 0 ? `${(blockRate * 100).toFixed(1)}%` : "-";
          const div = document.createElement("div");
          div.className = `item ${cls}`;
          div.innerHTML = `
            <div class="title mono">${escapeHtml(donorId)} · blocks=${escapeHtml(String(blocked))}</div>
            <div class="sub">present: ${escapeHtml(String(present))} · block_rate: ${escapeHtml(blockRateLabel)} · pass_rate: ${escapeHtml(passRateLabel)}</div>
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
            mergeIdsIntoTextarea(els.commentSelectedCommentIds, [c.comment_id || ""]);
            if (c.section) els.commentSection.value = c.section;
            if (c.version_id) els.commentVersionId.value = c.version_id;
            els.linkedFindingId.value = c.linked_finding_id || "";
            persistUiState();
          });
          els.commentsList.appendChild(div);
        }
      }

      function buildCriticFindingMetaById() {
        const critic = state.lastCritic && typeof state.lastCritic === "object" ? state.lastCritic : {};
        const flaws = Array.isArray(critic.fatal_flaws) ? critic.fatal_flaws : [];
        const byId = {};
        for (const flaw of flaws) {
          if (!flaw || typeof flaw !== "object") continue;
          const findingId = String(flaw.finding_id || flaw.id || "").trim();
          if (!findingId) continue;
          const relatedSections = Array.isArray(flaw.related_sections)
            ? flaw.related_sections.map((s) => String(s || "").trim().toLowerCase()).filter((s) => ["toc", "logframe", "general"].includes(s))
            : [];
          byId[findingId] = {
            findingId,
            code: String(flaw.code || "").trim(),
            section: String(flaw.section || "").trim().toLowerCase(),
            status: String(flaw.status || "").trim().toLowerCase(),
            rationale: String(flaw.rationale || ""),
            relatedSections,
          };
        }
        return byId;
      }

      function parseIdList(raw) {
        return Array.from(
          new Set(
            String(raw || "")
              .split(/[,\n]/)
              .map((token) => token.trim())
              .filter(Boolean)
          )
        );
      }

      function mergeIdsIntoTextarea(el, ids) {
        if (!el) return;
        const merged = Array.from(new Set([...parseIdList(el.value), ...parseIdList((ids || []).join("\n"))]));
        el.value = merged.join("\n");
        persistUiState();
      }

      function parseRenderedJson(el, label) {
        const text = String(el?.textContent || "").trim();
        if (!text || text === "{}") throw new Error(`Load ${label} first`);
        try {
          return JSON.parse(text);
        } catch (err) {
          throw new Error(`Unable to parse ${label}: ${err instanceof Error ? err.message : String(err)}`);
        }
      }

      async function copyTextToClipboard(text, emptyMessage) {
        const value = String(text || "").trim();
        if (!value) throw new Error(emptyMessage);
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(value);
      }

      function collectWorkflowFindingIds() {
        const payload = parseRenderedJson(els.reviewWorkflowJson, "review workflow");
        const findings = Array.isArray(payload.findings) ? payload.findings : [];
        return findings
          .map((finding) => String(finding?.finding_id || finding?.id || "").trim())
          .filter(Boolean);
      }

      function collectWorkflowCommentIds() {
        const payload = parseRenderedJson(els.reviewWorkflowJson, "review workflow");
        const comments = Array.isArray(payload.comments) ? payload.comments : [];
        return comments
          .map((comment) => String(comment?.comment_id || comment?.id || "").trim())
          .filter(Boolean);
      }

      function renderBulkPreviewSummary(
        el,
        result,
        {
          notFoundKey = "",
          updatedKey = "",
          itemLabel = "items",
          scopeLabel = "",
          queueLabel = "",
          filterBasis = "",
          statusTransition = "",
        } = {}
      ) {
        if (!el) return;
        el.innerHTML = "";
        if (!result || typeof result !== "object") {
          el.innerHTML = `<div class="item"><div class="sub">No bulk preview yet.</div></div>`;
          return;
        }
        const matchedCount = Number(result.matched_count || 0);
        const changedCount = Number(result.changed_count || 0);
        const unchangedCount = Number(result.unchanged_count || 0);
        const notFoundList = Array.isArray(result[notFoundKey]) ? result[notFoundKey] : [];
        const updatedItems = Array.isArray(result[updatedKey]) ? result[updatedKey] : [];
        const dryRun = result.dry_run === true;
        const persisted = result.persisted === true;
        const status = String(result.requested_status || "").trim() || "-";
        const cards = [
          { title: dryRun ? "Preview Mode" : "Apply Mode", sub: dryRun ? "dry_run=true" : persisted ? "persisted=true" : "persisted=false" },
          { title: "Scope", sub: String(scopeLabel || "-") },
          { title: "Filter Basis", sub: String(filterBasis || "-") },
          { title: "Status Transition", sub: String(statusTransition || "-") },
          { title: "Queue Impact", sub: String(queueLabel || "-") },
          { title: "Matched", sub: String(matchedCount) },
          { title: "Changed", sub: String(changedCount) },
          { title: "Unchanged", sub: String(unchangedCount) },
          { title: "Not Found", sub: String(notFoundList.length) },
          { title: "Target Status", sub: status },
        ];
        for (const card of cards) {
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(card.title)}</div>
            <div class="sub">${escapeHtml(card.sub)}</div>
          `;
          el.appendChild(div);
        }
        if (updatedItems.length) {
          const preview = updatedItems
            .slice(0, 3)
            .map((item) => String(item.finding_id || item.comment_id || item.id || "").trim())
            .filter(Boolean)
            .join(", ");
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">Preview ${escapeHtml(itemLabel)}</div>
            <div class="sub">${escapeHtml(preview || "-")}${updatedItems.length > 3 ? ` +${updatedItems.length - 3} more` : ""}</div>
          `;
          el.appendChild(div);
        }
        if (notFoundList.length) {
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">Missing IDs</div>
            <div class="sub">${escapeHtml(notFoundList.slice(0, 5).join(", "))}${notFoundList.length > 5 ? ` +${notFoundList.length - 5} more` : ""}</div>
          `;
          el.appendChild(div);
        }
      }

      function describeBulkScope(scope, selectedCount, itemLabel) {
        const normalized = String(scope || "filtered").trim().toLowerCase();
        if (normalized === "all") return `all ${itemLabel} in job`;
        if (normalized === "selected") return `selected ${itemLabel} (${selectedCount})`;
        return `filtered ${itemLabel}`;
      }

      function describeCriticFilterBasis(scope) {
        const normalized = String(scope || "filtered").trim().toLowerCase();
        if (normalized === "all") return "apply_to_all=true";
        if (normalized === "selected") return "selected ids only";
        const parts = [];
        const section = String(els.criticSectionFilter?.value || "").trim();
        const severity = String(els.criticSeverityFilter?.value || "").trim();
        const findingStatus = String(els.criticFindingStatusFilter?.value || "").trim();
        if (section) parts.push(`section=${section}`);
        if (severity) parts.push(`severity=${severity}`);
        if (findingStatus) parts.push(`status=${findingStatus}`);
        return parts.join(" · ") || "current critic filters";
      }

      function describeCommentFilterBasis(scope) {
        const normalized = String(scope || "filtered").trim().toLowerCase();
        if (normalized === "all") return "apply_to_all=true";
        if (normalized === "selected") return "selected ids only";
        const parts = [];
        const section = String(els.commentsFilterSection?.value || "").trim();
        const commentStatus = String(els.commentsFilterStatus?.value || "").trim();
        const versionId = String(els.commentsFilterVersionId?.value || "").trim();
        if (section) parts.push(`section=${section}`);
        if (commentStatus) parts.push(`status=${commentStatus}`);
        if (versionId) parts.push(`version=${versionId}`);
        return parts.join(" · ") || "current comment filters";
      }

      function describeStatusTransition(result, fallbackFromStatus, targetStatus) {
        const filters = result && typeof result === "object" && result.filters && typeof result.filters === "object" ? result.filters : {};
        const explicitFrom =
          String(filters.finding_status || filters.comment_status || filters.if_match_status || fallbackFromStatus || "").trim().toLowerCase();
        const fromStatus = explicitFrom || "mixed";
        const toStatus = String(targetStatus || result?.requested_status || "").trim().toLowerCase() || "-";
        return `${fromStatus} -> ${toStatus}`;
      }

      function describeBulkAction(targetStatus, itemKind) {
        const normalizedStatus = String(targetStatus || "").trim().toLowerCase();
        const normalizedKind = String(itemKind || "finding").trim().toLowerCase();
        const plural = normalizedKind === "comment" ? "Comments" : "Findings";
        const base = normalizedKind === "comment" ? "comment" : "finding";
        if (normalizedStatus === "resolved") {
          return {
            previewLabel: `Preview Resolve ${plural}`,
            applyLabel: `Apply Resolve ${plural}`,
            queueLabel: `${base} resolve queue`,
          };
        }
        if (normalizedStatus === "open") {
          return {
            previewLabel: `Preview Reopen ${plural}`,
            applyLabel: `Apply Reopen ${plural}`,
            queueLabel: normalizedKind === "comment" ? "comment reopen queue" : "finding reopen path",
          };
        }
        return {
          previewLabel: `Preview Acknowledge ${plural}`,
          applyLabel: `Apply Acknowledge ${plural}`,
          queueLabel: `${base} ack queue`,
        };
      }

      function updateCriticBulkActionUi() {
        const targetStatus = String(els.criticBulkTargetStatus?.value || "acknowledged").trim();
        const scope = String(els.criticBulkScope?.value || "filtered").trim();
        const selectedCount = parseIdList(els.criticSelectedFindingIds?.value || "").length;
        const action = describeBulkAction(targetStatus, "finding");
        if (els.criticBulkPreviewBtn) els.criticBulkPreviewBtn.textContent = action.previewLabel;
        if (els.criticBulkApplyBtn) els.criticBulkApplyBtn.textContent = action.applyLabel;
        if (els.criticBulkActionHint) {
          els.criticBulkActionHint.textContent = `finding bulk action: scope=${describeBulkScope(scope, selectedCount, "finding ids")} · queue=${action.queueLabel}`;
        }
        const workflowSection = String(els.reviewWorkflowFindingSectionFilter?.value || "").trim();
        const workflowStatus = String(els.reviewWorkflowCommentStatusFilter?.value || "").trim();
        const criticSection = String(els.criticSectionFilter?.value || "").trim();
        const criticStatus = String(els.criticFindingStatusFilter?.value || "").trim();
        if (els.criticWorkflowFilterSuggestion) {
          if ((workflowSection || workflowStatus) && !criticSection && !criticStatus) {
            const parts = [];
            if (workflowSection) parts.push(`section=${workflowSection}`);
            if (workflowStatus) parts.push(`status=${workflowStatus}`);
            els.criticWorkflowFilterSuggestion.textContent =
              `workflow filter suggestion: bulk critic filters are empty; use workflow filters (${parts.join(" · ")})`;
            els.criticWorkflowFilterSuggestion.className = "item severity-medium mono";
          } else {
            els.criticWorkflowFilterSuggestion.textContent = "workflow filter suggestion: -";
            els.criticWorkflowFilterSuggestion.className = "footer-note mono";
          }
        }
      }

      function updateCommentBulkActionUi() {
        const targetStatus = String(els.commentBulkTargetStatus?.value || "acknowledged").trim();
        const scope = String(els.commentBulkScope?.value || "filtered").trim();
        const selectedCount = parseIdList(els.commentSelectedCommentIds?.value || "").length;
        const action = describeBulkAction(targetStatus, "comment");
        if (els.commentBulkPreviewBtn) els.commentBulkPreviewBtn.textContent = action.previewLabel;
        if (els.commentBulkApplyBtn) els.commentBulkApplyBtn.textContent = action.applyLabel;
        if (els.commentBulkActionHint) {
          els.commentBulkActionHint.textContent = `comment bulk action: scope=${describeBulkScope(scope, selectedCount, "comment ids")} · queue=${action.queueLabel}`;
        }
        const workflowSection = String(els.reviewWorkflowFindingSectionFilter?.value || "").trim();
        const workflowStatus = String(els.reviewWorkflowCommentStatusFilter?.value || "").trim();
        const commentSection = String(els.commentsFilterSection?.value || "").trim();
        const commentStatus = String(els.commentsFilterStatus?.value || "").trim();
        if (els.commentWorkflowFilterSuggestion) {
          if ((workflowSection || workflowStatus) && !commentSection && !commentStatus) {
            const parts = [];
            if (workflowSection) parts.push(`section=${workflowSection}`);
            if (workflowStatus) parts.push(`status=${workflowStatus}`);
            els.commentWorkflowFilterSuggestion.textContent =
              `workflow filter suggestion: bulk comment filters are empty; use workflow filters (${parts.join(" · ")})`;
            els.commentWorkflowFilterSuggestion.className = "item severity-medium mono";
          } else {
            els.commentWorkflowFilterSuggestion.textContent = "workflow filter suggestion: -";
            els.commentWorkflowFilterSuggestion.className = "footer-note mono";
          }
        }
      }

      function syncCriticFiltersFromWorkflow() {
        const section = String(els.reviewWorkflowFindingSectionFilter?.value || "").trim();
        const findingStatus = String(els.reviewWorkflowCommentStatusFilter?.value || "").trim();
        if (section) els.criticSectionFilter.value = section;
        if (["open", "acknowledged", "resolved"].includes(findingStatus)) {
          els.criticFindingStatusFilter.value = findingStatus;
        }
        els.criticBulkScope.value = "filtered";
        persistUiState();
        updateCriticBulkActionUi();
      }

      function syncCommentFiltersFromWorkflow() {
        const section = String(els.reviewWorkflowFindingSectionFilter?.value || "").trim();
        const commentStatus = String(els.reviewWorkflowCommentStatusFilter?.value || "").trim();
        if (["toc", "logframe", "general"].includes(section)) {
          els.commentsFilterSection.value = section;
        }
        if (["open", "resolved", "acknowledged"].includes(commentStatus)) {
          els.commentsFilterStatus.value = commentStatus;
        }
        els.commentBulkScope.value = "filtered";
        persistUiState();
        updateCommentBulkActionUi();
      }

      async function applyRuntimeGroundedGateReviewWorkflowDrilldown({ section = "", reasonCode = "" } = {}) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("Set or generate a job_id first");
        const normalizedSection = String(section || "").trim().toLowerCase();
        const normalizedReasonCode = String(reasonCode || "").trim();

        if (!state.lastCritic) {
          await refreshCritic();
        }
        const findingMetaById = buildCriticFindingMetaById();
        const candidateFindings = Object.values(findingMetaById)
          .filter((meta) => String(meta.code || "").toUpperCase() === "RUNTIME_GROUNDED_QUALITY_GATE_BLOCK")
          .filter((meta) => {
            if (!normalizedSection) return true;
            return (
              String(meta.section || "").toLowerCase() === normalizedSection ||
              (Array.isArray(meta.relatedSections) && meta.relatedSections.includes(normalizedSection))
            );
          })
          .filter((meta) => {
            if (!normalizedReasonCode) return true;
            return String(meta.rationale || "").includes(normalizedReasonCode);
          })
          .sort((a, b) => {
            const rank = (status) => {
              if (status === "open") return 0;
              if (status === "acknowledged") return 1;
              if (status === "resolved") return 2;
              return 3;
            };
            return rank(a.status) - rank(b.status) || String(a.findingId).localeCompare(String(b.findingId));
          });

        const selectedFinding = candidateFindings.length ? candidateFindings[0] : null;
        els.reviewWorkflowEventTypeFilter.value = "critic_finding_status_changed";
        els.reviewWorkflowFindingCodeFilter.value = "RUNTIME_GROUNDED_QUALITY_GATE_BLOCK";
        if (normalizedSection && ["toc", "logframe", "general"].includes(normalizedSection)) {
          els.reviewWorkflowFindingSectionFilter.value = normalizedSection;
        }
        els.reviewWorkflowFindingIdFilter.value = selectedFinding ? String(selectedFinding.findingId || "") : "";
        persistUiState();
        await Promise.allSettled([
          refreshReviewWorkflow(),
          refreshReviewWorkflowTrends(),
          refreshReviewWorkflowSla(),
          refreshReviewWorkflowSlaTrends(),
          refreshPortfolioReviewWorkflow(),
          refreshPortfolioReviewWorkflowSla(),
          refreshPortfolioReviewWorkflowSlaHotspots(),
          refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflowTrends(),
          refreshPortfolioReviewWorkflowSlaTrends(),
        ]);
      }

      function renderReviewWorkflowTimeline(body) {
        const timeline = Array.isArray(body?.timeline) ? body.timeline : [];
        const findingMetaById = buildCriticFindingMetaById();
        els.reviewWorkflowTimelineList.innerHTML = "";
        if (!timeline.length) {
          els.reviewWorkflowTimelineList.innerHTML = `<div class="item"><div class="sub">No review workflow events for current filters.</div></div>`;
        } else {
          for (const item of timeline) {
            const findingId = String(item.finding_id || "").trim();
            const commentId = String(item.comment_id || "").trim();
            const findingMeta = findingId ? findingMetaById[findingId] : null;
            const findingCode = findingMeta ? String(findingMeta.code || "").trim() : "";
            const parts = [item.type || "event", item.status || "-", item.section || findingMeta?.section || "-"];
            if (findingCode) parts.push(findingCode);
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
        const workflowPolicy = summary?.review_workflow_policy_summary && typeof summary.review_workflow_policy_summary === "object"
          ? summary.review_workflow_policy_summary
          : {};
        if (els.reviewWorkflowPolicyLine) {
          els.reviewWorkflowPolicyLine.textContent =
            `workflow policy: status=${String(workflowPolicy?.status || "-")} · go/no-go=${String(workflowPolicy?.go_no_go_flag || "-")} · next=${String(workflowPolicy?.next_operational_action || "-")}`;
        }
        const actionQueue = summary?.action_queue_summary && typeof summary.action_queue_summary === "object"
          ? summary.action_queue_summary
          : {};
        renderReviewActionQueueCards(actionQueue);
      }

      function sendClassificationForGoNoGo(goNoGo) {
        const normalized = String(goNoGo || "").trim().toLowerCase();
        if (normalized === "go") return "send-safe";
        if (normalized === "go_with_conditions") return "send-with-conditions";
        if (normalized === "hold") return "internal-only";
        return "-";
      }

      function renderSendGate(policySummary) {
        const summary = policySummary && typeof policySummary === "object" ? policySummary : {};
        const status = String(summary?.status || "-").trim().toLowerCase() || "-";
        const goNoGo = String(summary?.go_no_go_flag || "-").trim().toLowerCase() || "-";
        const nextAction = String(summary?.next_operational_action || "-").trim() || "-";
        const sendClassification = sendClassificationForGoNoGo(goNoGo);
        const risk =
          status === "breach"
            ? "high"
            : status === "attention"
              ? "medium"
              : status === "healthy"
                ? "low"
                : "none";
        const unsafeOverride = allowUnsafeExportEnabled();
        const blocked = sendClassification === "internal-only" && !unsafeOverride;
        state.lastPortfolioWorkflowPolicy = Object.keys(summary).length ? summary : null;

        if (els.sendGatePill && els.sendGatePillText) {
          els.sendGatePill.className = `pill readiness-level-${risk}`;
          const headline =
            sendClassification === "internal-only"
              ? blocked
                ? "external send blocked"
                : "internal-only override"
              : sendClassification === "send-with-conditions"
                ? "send with conditions"
                : sendClassification === "send-safe"
                  ? "send safe"
                  : "not evaluated";
          els.sendGatePillText.textContent = `${headline} (${status === "-" ? "policy pending" : status})`;
        }
        if (els.sendGateMetaLine) {
          els.sendGateMetaLine.textContent =
            `policy=${status} · go/no-go=${goNoGo} · classification=${sendClassification} · next=${nextAction}`;
        }
        if (els.sendGateAdvisoryLine) {
          els.sendGateAdvisoryLine.textContent = blocked
            ? "external send blocked until workflow policy moves out of hold; use Allow Unsafe Override only for internal review proofing"
            : sendClassification === "send-with-conditions"
              ? "external send allowed with conditions; review next operational action before sharing"
              : sendClassification === "send-safe"
                ? "external send path is clear under current workflow policy"
                : unsafeOverride
                  ? "unsafe override enabled; policy gate is advisory"
                  : "external send gate pending portfolio workflow snapshot";
        }
        if (els.exportProductionZipFromPayloadBtn) {
          els.exportProductionZipFromPayloadBtn.disabled = blocked;
          els.exportProductionZipFromPayloadBtn.textContent = blocked
            ? "Production Export Blocked"
            : "Production Export (enforced)";
          els.exportProductionZipFromPayloadBtn.title = blocked
            ? "Portfolio workflow policy is hold/internal-only. Clear workflow issues or enable unsafe override for internal review proofing."
            : "Enforced production export using current payload and gating settings.";
        }
      }

      function renderReviewActionQueueCards(summary) {
        const cards = Array.isArray(els.reviewActionQueueCards?.children)
          ? Array.from(els.reviewActionQueueCards.children)
          : [];
        const values = [
          String(summary?.next_primary_action || "-"),
          String(summary?.finding_ack_queue_count ?? "-"),
          String(summary?.finding_resolve_queue_count ?? "-"),
          String(summary?.comment_ack_queue_count ?? "-"),
          String(summary?.comment_resolve_queue_count ?? "-"),
          String(summary?.comment_reopen_queue_count ?? "-"),
        ];
        cards.forEach((card, index) => {
          const valueEl = card && typeof card.querySelector === "function" ? card.querySelector(".value") : null;
          if (valueEl) valueEl.textContent = values[index] ?? "-";
        });
      }

      function renderReviewWorkflowTrends(body) {
        const totalSeries = Array.isArray(body?.total_series) ? body.total_series : [];
        const eventTypeSeriesRaw = body?.event_type_series && typeof body.event_type_series === "object"
          ? body.event_type_series
          : {};
        const kindSeriesRaw = body?.kind_series && typeof body.kind_series === "object"
          ? body.kind_series
          : {};
        const statusSeriesRaw = body?.status_series && typeof body.status_series === "object"
          ? body.status_series
          : {};
        const windowStart = String(body?.time_window_start || "-");
        const windowEnd = String(body?.time_window_end || "-");
        const bucketCount = Number(body?.bucket_count || totalSeries.length || 0);
        const timelineEventCount = Number(body?.timeline_event_count || 0);
        if (els.reviewWorkflowTrendsSummaryLine) {
          els.reviewWorkflowTrendsSummaryLine.textContent =
            `workflow trends: buckets=${bucketCount} · window=${windowStart}..${windowEnd} · events=${timelineEventCount}`;
        }

        const sparklinePalette = " .:-=+*#%@";
        const seriesCounts = totalSeries.map((point) => Number(point?.count || 0));
        const maxCount = seriesCounts.length ? Math.max(...seriesCounts) : 0;
        const sparkline = seriesCounts.length
          ? seriesCounts
              .map((count) => {
                if (maxCount <= 0) return ".";
                const idx = Math.min(
                  sparklinePalette.length - 1,
                  Math.max(0, Math.round((count / maxCount) * (sparklinePalette.length - 1)))
                );
                return sparklinePalette.charAt(idx);
              })
              .join("")
          : "-";
        if (els.reviewWorkflowTrendSparkline) {
          els.reviewWorkflowTrendSparkline.textContent = `trend: ${sparkline} (max=${maxCount})`;
        }

        const buildBucketMap = (rawSeries) => {
          const out = {};
          for (const [key, series] of Object.entries(rawSeries || {})) {
            if (!Array.isArray(series)) continue;
            const bucketMap = {};
            for (const row of series) {
              const bucket = String(row?.bucket || "").trim();
              if (!bucket) continue;
              bucketMap[bucket] = Number(row?.count || 0);
            }
            out[String(key)] = bucketMap;
          }
          return out;
        };
        const eventTypeBucketMap = buildBucketMap(eventTypeSeriesRaw);
        const kindBucketMap = buildBucketMap(kindSeriesRaw);
        const statusBucketMap = buildBucketMap(statusSeriesRaw);

        els.reviewWorkflowTrendsList.innerHTML = "";
        if (!totalSeries.length) {
          els.reviewWorkflowTrendsList.innerHTML = `<div class="item"><div class="sub">No workflow trend buckets for current filters.</div></div>`;
          return;
        }

        const topTokenForBucket = (bucket, bucketMap) => {
          let topKey = "-";
          let topCount = -1;
          for (const [key, countsByBucket] of Object.entries(bucketMap)) {
            const count = Number(countsByBucket?.[bucket] || 0);
            if (count > topCount) {
              topKey = key;
              topCount = count;
            }
          }
          return `${topKey}${topCount >= 0 ? ` (${topCount})` : ""}`;
        };

        for (const point of totalSeries) {
          const bucket = String(point?.bucket || "").trim() || "unknown";
          const total = Number(point?.count || 0);
          const topEventType = topTokenForBucket(bucket, eventTypeBucketMap);
          const topKind = topTokenForBucket(bucket, kindBucketMap);
          const topStatus = topTokenForBucket(bucket, statusBucketMap);
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(`${bucket} · events=${total}`)}</div>
            <div class="sub">${escapeHtml(`top_type=${topEventType} · top_kind=${topKind}`)}</div>
            <div class="sub" style="margin-top:6px;">${escapeHtml(`top_status=${topStatus}`)}</div>
          `;
          els.reviewWorkflowTrendsList.appendChild(div);
        }
      }

      function renderPortfolioReviewWorkflow(body) {
        const summary = body?.summary && typeof body.summary === "object" ? body.summary : {};
        const findingCount = Number(summary?.finding_count || 0);
        const commentCount = Number(summary?.comment_count || 0);
        const overdueTotal = Number(summary?.overdue_finding_count || 0) + Number(summary?.overdue_comment_count || 0);
        const timelineEventCount = Number(summary?.timeline_event_count || 0);
        const jobsWithActivity = Number(body?.jobs_with_activity || 0);
        const jobCount = Number(body?.job_count || 0);
        const topEventType = String(body?.top_event_type || "-");
        const topDonor = String(body?.top_donor_id || "-");
        if (els.portfolioReviewWorkflowSummaryLine) {
          els.portfolioReviewWorkflowSummaryLine.textContent =
            `portfolio workflow: findings=${findingCount} · comments=${commentCount} · overdue=${overdueTotal} · events=${timelineEventCount} · active_jobs=${jobsWithActivity}/${jobCount}`;
        }
        const workflowPolicy = summary?.review_workflow_policy_summary && typeof summary.review_workflow_policy_summary === "object"
          ? summary.review_workflow_policy_summary
          : {};
        if (els.portfolioReviewWorkflowPolicyLine) {
          const goNoGo = String(workflowPolicy?.go_no_go_flag || "-");
          els.portfolioReviewWorkflowPolicyLine.textContent =
            `portfolio policy: status=${String(workflowPolicy?.status || "-")} · go/no-go=${goNoGo} · send_class=${sendClassificationForGoNoGo(goNoGo)} · next=${String(workflowPolicy?.next_operational_action || "-")}`;
        }
        renderSendGate(workflowPolicy);

        const listEl = els.portfolioReviewWorkflowList;
        if (!listEl) return;
        listEl.innerHTML = "";

        const typeCounts = body?.timeline_event_type_counts && typeof body.timeline_event_type_counts === "object"
          ? body.timeline_event_type_counts
          : {};
        const donorCounts = body?.donor_event_counts && typeof body.donor_event_counts === "object"
          ? body.donor_event_counts
          : {};
        const latestTimeline = Array.isArray(body?.latest_timeline) ? body.latest_timeline : [];

        const summaryCard = document.createElement("div");
        summaryCard.className = "item";
        summaryCard.innerHTML = `
          <div class="title mono">${escapeHtml(`top_type=${topEventType} · top_donor=${topDonor}`)}</div>
          <div class="sub">${escapeHtml(`open_findings=${Number(summary?.open_finding_count || 0)} · ack=${Number(summary?.acknowledged_finding_count || 0)} · resolved=${Number(summary?.resolved_finding_count || 0)}`)}</div>
          <div class="sub" style="margin-top:6px;">${escapeHtml(`open_comments=${Number(summary?.open_comment_count || 0)} · resolved_comments=${Number(summary?.resolved_comment_count || 0)}`)}</div>
        `;
        listEl.appendChild(summaryCard);

        const topTypeRows = Object.entries(typeCounts)
          .map(([key, count]) => ({ key: String(key || "-"), count: Number(count || 0) }))
          .sort((a, b) => b.count - a.count)
          .slice(0, 4);
        const topDonorRows = Object.entries(donorCounts)
          .map(([key, count]) => ({ key: String(key || "-"), count: Number(count || 0) }))
          .sort((a, b) => b.count - a.count)
          .slice(0, 4);

        const typesCard = document.createElement("div");
        typesCard.className = "item";
        const typeTokens = topTypeRows.length
          ? topTypeRows.map((row) => `${row.key}=${row.count}`).join(" · ")
          : "none";
        const donorTokens = topDonorRows.length
          ? topDonorRows.map((row) => `${row.key}=${row.count}`).join(" · ")
          : "none";
        typesCard.innerHTML = `
          <div class="title mono">${escapeHtml(`event_types: ${typeTokens}`)}</div>
          <div class="sub">${escapeHtml(`donors: ${donorTokens}`)}</div>
        `;
        listEl.appendChild(typesCard);

        const latestRows = latestTimeline.slice(0, 5);
        if (!latestRows.length) {
          const empty = document.createElement("div");
          empty.className = "item";
          empty.innerHTML = `<div class="sub">No workflow timeline rows for current filters.</div>`;
          listEl.appendChild(empty);
          return;
        }
        for (const row of latestRows) {
          const ts = String(row?.ts || "-");
          const type = String(row?.type || "-");
          const kind = String(row?.kind || "-");
          const section = String(row?.section || "-");
          const status = String(row?.status || "-");
          const donorId = String(row?.donor_id || "-");
          const jobId = String(row?.job_id || "-");
          const item = document.createElement("div");
          item.className = "item";
          item.innerHTML = `
            <div class="title mono">${escapeHtml(`${ts} · ${type} · ${kind}`)}</div>
            <div class="sub">${escapeHtml(`donor=${donorId} · job=${jobId} · section=${section} · status=${status}`)}</div>
          `;
          listEl.appendChild(item);
        }
      }

      function renderPortfolioReviewWorkflowSla(body) {
        const hotspots = Array.isArray(body?.top_overdue) ? body.top_overdue : [];
        const oldest = body?.oldest_overdue && typeof body.oldest_overdue === "object" ? body.oldest_overdue : null;
        const overdueTotal = Number(body?.overdue_total || 0);
        const jobsWithOverdue = Number(body?.jobs_with_overdue || 0);
        const jobCount = Number(body?.job_count || 0);
        const topDonor = String(body?.top_donor_id || "-");
        const breachRateRaw = body?.breach_rate;
        const breachRate =
          breachRateRaw != null && Number.isFinite(Number(breachRateRaw))
            ? `${(Number(breachRateRaw) * 100).toFixed(1)}%`
            : "-";
        if (els.portfolioReviewWorkflowSlaSummaryLine) {
          els.portfolioReviewWorkflowSlaSummaryLine.textContent =
            `portfolio workflow sla: overdue=${overdueTotal} · breach=${breachRate} · top_donor=${topDonor} · active_jobs=${jobsWithOverdue}/${jobCount}`;
        }

        const listEl = els.portfolioReviewWorkflowSlaList;
        if (!listEl) return;
        listEl.innerHTML = "";
        if (!hotspots.length) {
          listEl.innerHTML = `<div class="item"><div class="sub">No overdue SLA items for current filters.</div></div>`;
          return;
        }
        const oldestToken = oldest
          ? `${String(oldest.kind || "item")}#${String(oldest.id || "").slice(0, 8)}`
          : "-";
        const header = document.createElement("div");
        header.className = "item";
        header.innerHTML = `
          <div class="title mono">${escapeHtml(`oldest=${oldestToken}`)}</div>
          <div class="sub">${escapeHtml(`overdue_findings=${Number(body?.overdue_finding_count || 0)} · overdue_comments=${Number(body?.overdue_comment_count || 0)}`)}</div>
        `;
        listEl.appendChild(header);

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
          const meta = [
            item.job_id ? `job ${String(item.job_id).slice(0, 8)}` : null,
            item.donor_id ? `donor ${String(item.donor_id)}` : null,
            item.due_at ? `due ${item.due_at}` : null,
            overdueHours,
            item.linked_finding_id ? `finding ${String(item.linked_finding_id).slice(0, 8)}` : null,
          ]
            .filter(Boolean)
            .join(" · ");
          const row = document.createElement("div");
          row.className = "item";
          row.innerHTML = `
            <div class="title mono">${escapeHtml(bits.join(" · "))}</div>
            <div class="sub">${escapeHtml(item.message || "")}</div>
            <div class="sub" style="margin-top:6px;">${escapeHtml(meta)}</div>
          `;
          listEl.appendChild(row);
        }
      }

      function renderPortfolioReviewWorkflowSlaHotspots(body) {
        const hotspots = Array.isArray(body?.top_overdue) ? body.top_overdue : [];
        const total = Number(body?.total_overdue_items || 0);
        const shown = Number(body?.hotspot_count || hotspots.length || 0);
        const jobCount = Number(body?.job_count || 0);
        const jobsWithOverdue = Number(body?.jobs_with_overdue || 0);
        const topDonor = String(body?.top_donor_id || "-");
        const maxOverdue =
          body?.max_overdue_hours != null && Number.isFinite(Number(body.max_overdue_hours))
            ? `${Number(body.max_overdue_hours).toFixed(2)}h`
            : "-";
        const avgOverdue =
          body?.avg_overdue_hours != null && Number.isFinite(Number(body.avg_overdue_hours))
            ? `${Number(body.avg_overdue_hours).toFixed(2)}h`
            : "-";
        if (els.portfolioReviewWorkflowSlaHotspotsSummaryLine) {
          els.portfolioReviewWorkflowSlaHotspotsSummaryLine.textContent =
            `portfolio sla hotspots: shown=${shown}/${total} · max_overdue=${maxOverdue} · avg_overdue=${avgOverdue} · top_donor=${topDonor} · active_jobs=${jobsWithOverdue}/${jobCount}`;
        }

        const listEl = els.portfolioReviewWorkflowSlaHotspotsList;
        if (!listEl) return;
        listEl.innerHTML = "";
        if (!hotspots.length) {
          listEl.innerHTML = `<div class="item"><div class="sub">No SLA hotspots for current triage filters.</div></div>`;
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
          const meta = [
            item.job_id ? `job ${String(item.job_id).slice(0, 8)}` : null,
            item.donor_id ? `donor ${String(item.donor_id)}` : null,
            item.due_at ? `due ${item.due_at}` : null,
            overdueHours,
            item.linked_finding_id ? `finding ${String(item.linked_finding_id).slice(0, 8)}` : null,
          ]
            .filter(Boolean)
            .join(" · ");
          const row = document.createElement("div");
          row.className = "item";
          row.innerHTML = `
            <div class="title mono">${escapeHtml(bits.join(" · "))}</div>
            <div class="sub">${escapeHtml(item.message || "")}</div>
            <div class="sub" style="margin-top:6px;">${escapeHtml(meta)}</div>
          `;
          listEl.appendChild(row);
        }
      }

      function renderPortfolioReviewWorkflowSlaHotspotsTrends(body) {
        const totalSeries = Array.isArray(body?.total_series) ? body.total_series : [];
        const kindSeriesRaw = body?.kind_series && typeof body.kind_series === "object"
          ? body.kind_series
          : {};
        const donorSeriesRaw = body?.donor_series && typeof body.donor_series === "object"
          ? body.donor_series
          : {};
        const windowStart = String(body?.time_window_start || "-");
        const windowEnd = String(body?.time_window_end || "-");
        const bucketCount = Number(body?.bucket_count || totalSeries.length || 0);
        const hotspotTotal = Number(body?.hotspot_count_total || 0);
        const jobsWithOverdue = Number(body?.jobs_with_overdue || 0);
        const jobCount = Number(body?.job_count || 0);
        if (els.portfolioReviewWorkflowSlaHotspotsTrendsSummaryLine) {
          els.portfolioReviewWorkflowSlaHotspotsTrendsSummaryLine.textContent =
            `portfolio sla hotspots trends: buckets=${bucketCount} · window=${windowStart}..${windowEnd} · hotspots=${hotspotTotal} · active_jobs=${jobsWithOverdue}/${jobCount}`;
        }

        const sparklinePalette = " .:-=+*#%@";
        const seriesCounts = totalSeries.map((point) => Number(point?.count || 0));
        const maxCount = seriesCounts.length ? Math.max(...seriesCounts) : 0;
        const sparkline = seriesCounts.length
          ? seriesCounts
              .map((count) => {
                if (maxCount <= 0) return ".";
                const idx = Math.min(
                  sparklinePalette.length - 1,
                  Math.max(0, Math.round((count / maxCount) * (sparklinePalette.length - 1)))
                );
                return sparklinePalette.charAt(idx);
              })
              .join("")
          : "-";
        if (els.portfolioReviewWorkflowSlaHotspotsTrendSparkline) {
          els.portfolioReviewWorkflowSlaHotspotsTrendSparkline.textContent = `trend: ${sparkline} (max=${maxCount})`;
        }

        const buildBucketMap = (rawSeries) => {
          const out = {};
          for (const [key, series] of Object.entries(rawSeries || {})) {
            if (!Array.isArray(series)) continue;
            const bucketMap = {};
            for (const row of series) {
              const bucket = String(row?.bucket || "").trim();
              if (!bucket) continue;
              bucketMap[bucket] = Number(row?.count || 0);
            }
            out[String(key)] = bucketMap;
          }
          return out;
        };
        const kindBucketMap = buildBucketMap(kindSeriesRaw);
        const donorBucketMap = buildBucketMap(donorSeriesRaw);

        const listEl = els.portfolioReviewWorkflowSlaHotspotsTrendsList;
        if (!listEl) return;
        listEl.innerHTML = "";
        if (!totalSeries.length) {
          listEl.innerHTML = `<div class="item"><div class="sub">No hotspot trend buckets for current filters.</div></div>`;
          return;
        }

        const topTokenForBucket = (bucket, bucketMap) => {
          let topKey = "-";
          let topCount = -1;
          for (const [key, countsByBucket] of Object.entries(bucketMap)) {
            const count = Number(countsByBucket?.[bucket] || 0);
            if (count > topCount) {
              topKey = key;
              topCount = count;
            }
          }
          return `${topKey}${topCount >= 0 ? ` (${topCount})` : ""}`;
        };

        for (const point of totalSeries) {
          const bucket = String(point?.bucket || "").trim() || "unknown";
          const total = Number(point?.count || 0);
          const topKind = topTokenForBucket(bucket, kindBucketMap);
          const topDonor = topTokenForBucket(bucket, donorBucketMap);
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(`${bucket} · hotspots=${total}`)}</div>
            <div class="sub">${escapeHtml(`top_kind=${topKind}`)}</div>
            <div class="sub" style="margin-top:6px;">${escapeHtml(`top_donor=${topDonor}`)}</div>
          `;
          listEl.appendChild(div);
        }
      }

      function renderPortfolioReviewWorkflowTrends(body) {
        const totalSeries = Array.isArray(body?.total_series) ? body.total_series : [];
        const eventTypeSeriesRaw = body?.event_type_series && typeof body.event_type_series === "object"
          ? body.event_type_series
          : {};
        const donorSeriesRaw = body?.donor_series && typeof body.donor_series === "object"
          ? body.donor_series
          : {};
        const windowStart = String(body?.time_window_start || "-");
        const windowEnd = String(body?.time_window_end || "-");
        const bucketCount = Number(body?.bucket_count || totalSeries.length || 0);
        const timelineEventCount = Number(body?.timeline_event_count_total || 0);
        const jobsWithEvents = Number(body?.jobs_with_events || 0);
        const jobCount = Number(body?.job_count || 0);
        if (els.portfolioReviewWorkflowTrendsSummaryLine) {
          els.portfolioReviewWorkflowTrendsSummaryLine.textContent =
            `portfolio workflow trends: buckets=${bucketCount} · window=${windowStart}..${windowEnd} · events=${timelineEventCount} · active_jobs=${jobsWithEvents}/${jobCount}`;
        }

        const sparklinePalette = " .:-=+*#%@";
        const seriesCounts = totalSeries.map((point) => Number(point?.count || 0));
        const maxCount = seriesCounts.length ? Math.max(...seriesCounts) : 0;
        const sparkline = seriesCounts.length
          ? seriesCounts
              .map((count) => {
                if (maxCount <= 0) return ".";
                const idx = Math.min(
                  sparklinePalette.length - 1,
                  Math.max(0, Math.round((count / maxCount) * (sparklinePalette.length - 1)))
                );
                return sparklinePalette.charAt(idx);
              })
              .join("")
          : "-";
        if (els.portfolioReviewWorkflowTrendSparkline) {
          els.portfolioReviewWorkflowTrendSparkline.textContent = `trend: ${sparkline} (max=${maxCount})`;
        }

        const buildBucketMap = (rawSeries) => {
          const out = {};
          for (const [key, series] of Object.entries(rawSeries || {})) {
            if (!Array.isArray(series)) continue;
            const bucketMap = {};
            for (const row of series) {
              const bucket = String(row?.bucket || "").trim();
              if (!bucket) continue;
              bucketMap[bucket] = Number(row?.count || 0);
            }
            out[String(key)] = bucketMap;
          }
          return out;
        };
        const eventTypeBucketMap = buildBucketMap(eventTypeSeriesRaw);
        const donorBucketMap = buildBucketMap(donorSeriesRaw);

        els.portfolioReviewWorkflowTrendsList.innerHTML = "";
        if (!totalSeries.length) {
          els.portfolioReviewWorkflowTrendsList.innerHTML =
            `<div class="item"><div class="sub">No portfolio workflow trend buckets for current filters.</div></div>`;
          return;
        }

        const topTokenForBucket = (bucket, bucketMap) => {
          let topKey = "-";
          let topCount = -1;
          for (const [key, countsByBucket] of Object.entries(bucketMap)) {
            const count = Number(countsByBucket?.[bucket] || 0);
            if (count > topCount) {
              topKey = key;
              topCount = count;
            }
          }
          return `${topKey}${topCount >= 0 ? ` (${topCount})` : ""}`;
        };

        for (const point of totalSeries) {
          const bucket = String(point?.bucket || "").trim() || "unknown";
          const total = Number(point?.count || 0);
          const topEventType = topTokenForBucket(bucket, eventTypeBucketMap);
          const topDonor = topTokenForBucket(bucket, donorBucketMap);
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(`${bucket} · events=${total}`)}</div>
            <div class="sub">${escapeHtml(`top_type=${topEventType}`)}</div>
            <div class="sub" style="margin-top:6px;">${escapeHtml(`top_donor=${topDonor}`)}</div>
          `;
          els.portfolioReviewWorkflowTrendsList.appendChild(div);
        }
      }

      function renderPortfolioReviewWorkflowSlaTrends(body) {
        const totalSeries = Array.isArray(body?.total_series) ? body.total_series : [];
        const severitySeriesRaw = body?.severity_series && typeof body.severity_series === "object"
          ? body.severity_series
          : {};
        const donorSeriesRaw = body?.donor_series && typeof body.donor_series === "object"
          ? body.donor_series
          : {};
        const sectionSeriesRaw = body?.section_series && typeof body.section_series === "object"
          ? body.section_series
          : {};
        const windowStart = String(body?.time_window_start || "-");
        const windowEnd = String(body?.time_window_end || "-");
        const bucketCount = Number(body?.bucket_count || totalSeries.length || 0);
        const overdueTotal = Number(body?.overdue_total || 0);
        const jobsWithOverdue = Number(body?.jobs_with_overdue || 0);
        const jobCount = Number(body?.job_count || 0);
        if (els.portfolioReviewWorkflowSlaTrendsSummaryLine) {
          els.portfolioReviewWorkflowSlaTrendsSummaryLine.textContent =
            `portfolio workflow sla trends: buckets=${bucketCount} · window=${windowStart}..${windowEnd} · overdue=${overdueTotal} · active_jobs=${jobsWithOverdue}/${jobCount}`;
        }
        const sparklinePalette = " .:-=+*#%@";
        const seriesCounts = totalSeries.map((point) => Number(point?.count || 0));
        const maxCount = seriesCounts.length ? Math.max(...seriesCounts) : 0;
        const sparkline = seriesCounts.length
          ? seriesCounts
              .map((count) => {
                if (maxCount <= 0) return ".";
                const idx = Math.min(
                  sparklinePalette.length - 1,
                  Math.max(0, Math.round((count / maxCount) * (sparklinePalette.length - 1)))
                );
                return sparklinePalette.charAt(idx);
              })
              .join("")
          : "-";
        if (els.portfolioReviewWorkflowSlaTrendSparkline) {
          els.portfolioReviewWorkflowSlaTrendSparkline.textContent = `trend: ${sparkline} (max=${maxCount})`;
        }

        const buildBucketMap = (rawSeries) => {
          const out = {};
          for (const [key, series] of Object.entries(rawSeries || {})) {
            if (!Array.isArray(series)) continue;
            const bucketMap = {};
            for (const row of series) {
              const bucket = String(row?.bucket || "").trim();
              if (!bucket) continue;
              bucketMap[bucket] = Number(row?.count || 0);
            }
            out[String(key)] = bucketMap;
          }
          return out;
        };
        const severityBucketMap = buildBucketMap(severitySeriesRaw);
        const donorBucketMap = buildBucketMap(donorSeriesRaw);
        const sectionBucketMap = buildBucketMap(sectionSeriesRaw);

        els.portfolioReviewWorkflowSlaTrendsList.innerHTML = "";
        if (!totalSeries.length) {
          els.portfolioReviewWorkflowSlaTrendsList.innerHTML =
            `<div class="item"><div class="sub">No portfolio workflow SLA trend buckets for current filters.</div></div>`;
          return;
        }

        const topTokenForBucket = (bucket, bucketMap) => {
          let topKey = "-";
          let topCount = -1;
          for (const [key, countsByBucket] of Object.entries(bucketMap)) {
            const count = Number(countsByBucket?.[bucket] || 0);
            if (count > topCount) {
              topKey = key;
              topCount = count;
            }
          }
          return `${topKey}${topCount >= 0 ? ` (${topCount})` : ""}`;
        };

        for (const point of totalSeries) {
          const bucket = String(point?.bucket || "").trim() || "unknown";
          const total = Number(point?.count || 0);
          const highCount = Number(severityBucketMap.high?.[bucket] || 0);
          const mediumCount = Number(severityBucketMap.medium?.[bucket] || 0);
          const lowCount = Number(severityBucketMap.low?.[bucket] || 0);
          const unknownCount = Number(severityBucketMap.unknown?.[bucket] || 0);
          const topDonor = topTokenForBucket(bucket, donorBucketMap);
          const topSection = topTokenForBucket(bucket, sectionBucketMap);
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(`${bucket} · overdue=${total}`)}</div>
            <div class="sub">${escapeHtml(`sev(h/m/l/u)=${highCount}/${mediumCount}/${lowCount}/${unknownCount}`)}</div>
            <div class="sub" style="margin-top:6px;">${escapeHtml(`top_donor=${topDonor} · top_section=${topSection}`)}</div>
          `;
          els.portfolioReviewWorkflowSlaTrendsList.appendChild(div);
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

      function renderReviewWorkflowSlaTrends(body) {
        const totalSeries = Array.isArray(body?.total_series) ? body.total_series : [];
        const sectionSeriesRaw = body?.section_series && typeof body.section_series === "object"
          ? body.section_series
          : {};
        const severitySeriesRaw = body?.severity_series && typeof body.severity_series === "object"
          ? body.severity_series
          : {};

        const severityBucketMap = {};
        for (const [severity, series] of Object.entries(severitySeriesRaw)) {
          if (!Array.isArray(series)) continue;
          const bucketMap = {};
          for (const row of series) {
            const bucket = String(row?.bucket || "").trim();
            if (!bucket) continue;
            bucketMap[bucket] = Number(row?.count || 0);
          }
          severityBucketMap[String(severity)] = bucketMap;
        }

        const windowStart = String(body?.time_window_start || "-");
        const windowEnd = String(body?.time_window_end || "-");
        const bucketCount = Number(body?.bucket_count || totalSeries.length || 0);
        const overdueTotal = Number(body?.overdue_total || 0);
        if (els.reviewWorkflowSlaTrendsSummaryLine) {
          els.reviewWorkflowSlaTrendsSummaryLine.textContent =
            `trends: buckets=${bucketCount} · window=${windowStart}..${windowEnd} · overdue=${overdueTotal}`;
        }
        const sparklinePalette = " .:-=+*#%@";
        const seriesCounts = totalSeries.map((point) => Number(point?.count || 0));
        const maxCount = seriesCounts.length ? Math.max(...seriesCounts) : 0;
        const sparkline = seriesCounts.length
          ? seriesCounts
              .map((count) => {
                if (maxCount <= 0) return ".";
                const idx = Math.min(
                  sparklinePalette.length - 1,
                  Math.max(0, Math.round((count / maxCount) * (sparklinePalette.length - 1)))
                );
                return sparklinePalette.charAt(idx);
              })
              .join("")
          : "-";
        if (els.reviewWorkflowSlaTrendSparkline) {
          els.reviewWorkflowSlaTrendSparkline.textContent = `trend: ${sparkline} (max=${maxCount})`;
        }

        els.reviewWorkflowSlaTrendsList.innerHTML = "";
        if (!totalSeries.length) {
          els.reviewWorkflowSlaTrendsList.innerHTML = `<div class="item"><div class="sub">No overdue trend buckets for current filters.</div></div>`;
          return;
        }

        const sectionTotals = {};
        for (const [section, series] of Object.entries(sectionSeriesRaw)) {
          if (!Array.isArray(series)) continue;
          sectionTotals[String(section)] = series.reduce((acc, row) => acc + Number(row?.count || 0), 0);
        }
        let topSection = "-";
        let topSectionCount = -1;
        for (const [section, count] of Object.entries(sectionTotals)) {
          if (Number(count) > topSectionCount) {
            topSection = section;
            topSectionCount = Number(count);
          }
        }

        for (const point of totalSeries) {
          const bucket = String(point?.bucket || "").trim() || "unknown";
          const total = Number(point?.count || 0);
          const highCount = Number(severityBucketMap.high?.[bucket] || 0);
          const mediumCount = Number(severityBucketMap.medium?.[bucket] || 0);
          const lowCount = Number(severityBucketMap.low?.[bucket] || 0);
          const unknownCount = Number(severityBucketMap.unknown?.[bucket] || 0);
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(`${bucket} · overdue=${total}`)}</div>
            <div class="sub">${escapeHtml(`sev(h/m/l/u)=${highCount}/${mediumCount}/${lowCount}/${unknownCount}`)}</div>
            <div class="sub" style="margin-top:6px;">${escapeHtml(`top_section=${topSection}${topSectionCount >= 0 ? ` (${topSectionCount})` : ""}`)}</div>
          `;
          els.reviewWorkflowSlaTrendsList.appendChild(div);
        }
      }

      function renderReviewWorkflowSlaHotspots(body) {
        const hotspots = Array.isArray(body?.top_overdue) ? body.top_overdue : [];
        const shown = Number(body?.hotspot_count || hotspots.length || 0);
        const total = Number(body?.total_overdue_items || hotspots.length || 0);
        const maxOverdue =
          body?.max_overdue_hours != null && Number.isFinite(Number(body.max_overdue_hours))
            ? `${Number(body.max_overdue_hours).toFixed(2)}h`
            : "-";
        const avgOverdue =
          body?.avg_overdue_hours != null && Number.isFinite(Number(body.avg_overdue_hours))
            ? `${Number(body.avg_overdue_hours).toFixed(2)}h`
            : "-";
        if (els.reviewWorkflowSlaHotspotsSummaryLine) {
          els.reviewWorkflowSlaHotspotsSummaryLine.textContent =
            `hotspots: shown=${shown}/${total} · max_overdue=${maxOverdue} · avg_overdue=${avgOverdue}`;
        }

        els.reviewWorkflowSlaHotspotsList.innerHTML = "";
        if (!hotspots.length) {
          els.reviewWorkflowSlaHotspotsList.innerHTML = `<div class="item"><div class="sub">No SLA hotspots for current filters.</div></div>`;
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
          const meta = [
            item.due_at ? `due ${item.due_at}` : null,
            overdueHours,
            item.linked_finding_id ? `finding ${String(item.linked_finding_id).slice(0, 8)}` : null,
          ]
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

      function renderReviewWorkflowSlaHotspotsTrends(body) {
        const totalSeries = Array.isArray(body?.total_series) ? body.total_series : [];
        const kindSeriesRaw = body?.kind_series && typeof body.kind_series === "object" ? body.kind_series : {};
        const severitySeriesRaw = body?.severity_series && typeof body.severity_series === "object"
          ? body.severity_series
          : {};
        const hotspotTotal = Number(body?.hotspot_count_total || 0);
        const bucketCount = Number(body?.bucket_count || totalSeries.length || 0);
        const windowStart = String(body?.time_window_start || "-");
        const windowEnd = String(body?.time_window_end || "-");
        if (els.reviewWorkflowSlaHotspotsTrendsSummaryLine) {
          els.reviewWorkflowSlaHotspotsTrendsSummaryLine.textContent =
            `hotspots trends: buckets=${bucketCount} · window=${windowStart}..${windowEnd} · hotspots=${hotspotTotal}`;
        }

        const sparklinePalette = " .:-=+*#%@";
        const seriesCounts = totalSeries.map((point) => Number(point?.count || 0));
        const maxCount = seriesCounts.length ? Math.max(...seriesCounts) : 0;
        const sparkline = seriesCounts.length
          ? seriesCounts
              .map((count) => {
                if (maxCount <= 0) return ".";
                const idx = Math.min(
                  sparklinePalette.length - 1,
                  Math.max(0, Math.round((count / maxCount) * (sparklinePalette.length - 1)))
                );
                return sparklinePalette.charAt(idx);
              })
              .join("")
          : "-";
        if (els.reviewWorkflowSlaHotspotsTrendSparkline) {
          els.reviewWorkflowSlaHotspotsTrendSparkline.textContent = `trend: ${sparkline} (max=${maxCount})`;
        }

        const kindBucketMap = {};
        for (const [kind, series] of Object.entries(kindSeriesRaw)) {
          if (!Array.isArray(series)) continue;
          const bucketMap = {};
          for (const row of series) {
            const bucket = String(row?.bucket || "").trim();
            if (!bucket) continue;
            bucketMap[bucket] = Number(row?.count || 0);
          }
          kindBucketMap[String(kind)] = bucketMap;
        }
        const severityBucketMap = {};
        for (const [severity, series] of Object.entries(severitySeriesRaw)) {
          if (!Array.isArray(series)) continue;
          const bucketMap = {};
          for (const row of series) {
            const bucket = String(row?.bucket || "").trim();
            if (!bucket) continue;
            bucketMap[bucket] = Number(row?.count || 0);
          }
          severityBucketMap[String(severity)] = bucketMap;
        }

        els.reviewWorkflowSlaHotspotsTrendsList.innerHTML = "";
        if (!totalSeries.length) {
          els.reviewWorkflowSlaHotspotsTrendsList.innerHTML = `<div class="item"><div class="sub">No hotspot trend buckets for current filters.</div></div>`;
          return;
        }
        for (const point of totalSeries) {
          const bucket = String(point?.bucket || "").trim() || "unknown";
          const total = Number(point?.count || 0);
          const findingCount = Number(kindBucketMap.finding?.[bucket] || 0);
          const commentCount = Number(kindBucketMap.comment?.[bucket] || 0);
          const highCount = Number(severityBucketMap.high?.[bucket] || 0);
          const mediumCount = Number(severityBucketMap.medium?.[bucket] || 0);
          const lowCount = Number(severityBucketMap.low?.[bucket] || 0);
          const unknownCount = Number(severityBucketMap.unknown?.[bucket] || 0);
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div class="title mono">${escapeHtml(`${bucket} · hotspots=${total}`)}</div>
            <div class="sub">${escapeHtml(`kind(f/c)=${findingCount}/${commentCount}`)}</div>
            <div class="sub" style="margin-top:6px;">${escapeHtml(`sev(h/m/l/u)=${highCount}/${mediumCount}/${lowCount}/${unknownCount}`)}</div>
          `;
          els.reviewWorkflowSlaHotspotsTrendsList.appendChild(div);
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
            div.addEventListener("click", () => {
              if (flawId) {
                els.criticSelectedFindingId.value = flawId;
                mergeIdsIntoTextarea(els.criticSelectedFindingIds, [flawId]);
                persistUiState();
              }
            });
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
        const architectClaims =
          preflight.architect_claims && typeof preflight.architect_claims === "object"
            ? preflight.architect_claims
            : {};
        const architectClaimsAvailable = Boolean(architectClaims.available);
        const architectClaimCount = Number(architectClaims.claim_citation_count ?? 0);
        const architectKeyCoverage = Number(architectClaims.key_claim_coverage_ratio ?? NaN);
        const architectFallbackRatio = Number(architectClaims.fallback_claim_ratio ?? NaN);
        const architectTraceabilityGap = Number(architectClaims.traceability_gap_rate ?? NaN);
        const architectThresholdHit = Number(architectClaims.threshold_hit_rate ?? NaN);
        const fmtRate = (rawRate) => {
          const rate = Number(rawRate);
          return Number.isFinite(rate) ? `${Math.round(rate * 100)}%` : "-";
        };
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
        const gateStatus = policyBlocking ? "block" : severity === "high" || severity === "medium" ? "warn" : "pass";
        const architectClaimsLabel = architectClaimsAvailable
          ? `claims=${architectClaimCount} · key_cov=${fmtRate(architectKeyCoverage)} · fallback=${fmtRate(architectFallbackRatio)} · trace_gap=${fmtRate(architectTraceabilityGap)} · threshold_hit=${fmtRate(architectThresholdHit)}`
          : `claims=n/a (${String(architectClaims.reason || "not_evaluated")})`;

        container.className = `item preflight-alert severity-${severity} blink-in`;
        title.textContent = `Preflight gate: ${gateStatus}`;
        body.textContent =
          `risk=${riskLevel} · grounding=${groundingRiskLevel} · policy=${policyMode}` +
          ` · coverage=${coverageLabel} · warnings=${warningCount}` +
          (reasonTokens.length ? ` · reasons=${reasonTokens.join(",")}` : "") +
          ` · ${architectClaimsLabel}`;
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
        const extraContext = parseExtraInputContext();
        const presetKey = String(els.generatePresetSelect.value || "").trim();
        const selectedPreset =
          presetKey && GENERATE_PRESETS && typeof GENERATE_PRESETS[presetKey] === "object"
            ? GENERATE_PRESETS[presetKey]
            : null;
        const usePresetFlow = Boolean(presetKey && selectedPreset);
        const effectiveDonorId = usePresetFlow
          ? String(selectedPreset.donor_id || els.donorId.value || "").trim()
          : String(els.donorId.value || "").trim();
        const payload = {
          donor_id: effectiveDonorId,
          input_context: {
            ...extraContext,
            project: els.project.value.trim(),
            country: els.country.value.trim(),
          },
          llm_mode: els.llmMode.value === "true",
          hitl_enabled: els.hitlEnabled.value === "true",
          strict_preflight: els.strictPreflight.value === "true",
        };
        if (usePresetFlow && selectedPreset.architect_rag_enabled != null) {
          payload.architect_rag_enabled = Boolean(selectedPreset.architect_rag_enabled);
        }
        if (readiness.presetKey) {
          payload.client_metadata = buildPresetReadinessMetadata(readiness.presetKey, payload.donor_id);
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

        let body = null;
        if (usePresetFlow) {
          const sourceKind = String(selectedPreset.source_kind || "").trim().toLowerCase();
          const presetType = sourceKind === "legacy" || sourceKind === "rbm" ? sourceKind : "auto";
          const fromPresetPayload = {
            preset_key: presetKey,
            preset_type: presetType,
            llm_mode: payload.llm_mode,
            hitl_enabled: payload.hitl_enabled,
            strict_preflight: payload.strict_preflight,
            input_context_patch: payload.input_context,
            client_metadata_patch: payload.client_metadata || {},
          };
          if (payload.architect_rag_enabled != null) {
            fromPresetPayload.architect_rag_enabled = Boolean(payload.architect_rag_enabled);
          }
          if (payload.webhook_url) fromPresetPayload.webhook_url = payload.webhook_url;
          if (payload.webhook_secret) fromPresetPayload.webhook_secret = payload.webhook_secret;
          try {
            body = await apiFetch("/generate/from-preset", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(fromPresetPayload),
            });
          } catch (err) {
            const msg = String(err?.message || "");
            if (!(msg.includes("404") || msg.includes("405"))) throw err;
            body = await apiFetch("/generate", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });
          }
        } else {
          body = await apiFetch("/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
        }
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
        if (!jobId) {
          renderExportContract(null);
          return;
        }
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/export-payload`);
        setJson(els.exportPayloadJson, body);
        const payload = body && typeof body === "object" ? body.payload : null;
        const exportContract = payload && typeof payload === "object"
          ? (payload.export_contract || ((payload.state && typeof payload.state === "object") ? payload.state.export_contract_gate : null))
          : null;
        renderExportContract(exportContract && typeof exportContract === "object" ? exportContract : null);
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

      async function refreshReviewWorkflowTrends() {
        const jobId = currentJobId();
        if (!jobId) return;
        persistUiState();
        const q = buildReviewWorkflowFilterQueryString();
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/review/workflow/trends${q}`);
        renderReviewWorkflowTrends(body);
        setJson(els.reviewWorkflowTrendsJson, body);
        return body;
      }

      async function refreshReviewWorkflowSla() {
        const jobId = currentJobId();
        if (!jobId) return;
        persistUiState();
        const q = buildReviewWorkflowSlaFilterQueryString();
        const body = await apiFetch(
          `/status/${encodeURIComponent(jobId)}/review/workflow/sla${q}`
        );
        renderReviewWorkflowSla(body);
        setJson(els.reviewWorkflowSlaJson, body);
        return body;
      }

      async function refreshReviewWorkflowSlaTrends() {
        const jobId = currentJobId();
        if (!jobId) return;
        persistUiState();
        const q = buildReviewWorkflowSlaFilterQueryString();
        const body = await apiFetch(
          `/status/${encodeURIComponent(jobId)}/review/workflow/sla/trends${q}`
        );
        renderReviewWorkflowSlaTrends(body);
        setJson(els.reviewWorkflowSlaTrendsJson, body);
        return body;
      }

      async function refreshReviewWorkflowSlaHotspots() {
        const jobId = currentJobId();
        if (!jobId) return;
        persistUiState();
        const q = buildReviewWorkflowSlaHotspotsQueryString();
        const body = await apiFetch(
          `/status/${encodeURIComponent(jobId)}/review/workflow/sla/hotspots${q}`
        );
        renderReviewWorkflowSlaHotspots(body);
        setJson(els.reviewWorkflowSlaHotspotsJson, body);
        return body;
      }

      async function refreshReviewWorkflowSlaHotspotsTrends() {
        const jobId = currentJobId();
        if (!jobId) return;
        persistUiState();
        const q = buildReviewWorkflowSlaHotspotsTrendsQueryString();
        const body = await apiFetch(
          `/status/${encodeURIComponent(jobId)}/review/workflow/sla/hotspots/trends${q}`
        );
        renderReviewWorkflowSlaHotspotsTrends(body);
        setJson(els.reviewWorkflowSlaHotspotsTrendsJson, body);
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
        await Promise.allSettled([
          refreshReviewWorkflow(),
          refreshComments(),
          refreshCritic(),
          refreshReviewWorkflowSlaProfile(),
          refreshReviewWorkflowSlaTrends(),
          refreshReviewWorkflowSlaHotspots(),
          refreshReviewWorkflowSlaHotspotsTrends(),
        ]);
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

      async function refreshWorkerHeartbeat() {
        try {
          const body = await apiFetch("/queue/worker-heartbeat");
          renderWorkerHeartbeat(body);
          setJson(els.workerHeartbeatJson, body);
          return body;
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          const fallback = {
            mode: "unknown",
            policy: { mode: "strict" },
            consumer_enabled: null,
            heartbeat: { present: false, healthy: false },
            error: message,
          };
          renderWorkerHeartbeat(fallback);
          setJson(els.workerHeartbeatJson, fallback);
          return fallback;
        }
      }

      function workerHeartbeatPollIntervalMs() {
        const raw = Number.parseInt(String(els.workerHeartbeatPollSeconds?.value || "10"), 10);
        if (!Number.isFinite(raw) || raw <= 0) return 10000;
        return Math.max(2000, raw * 1000);
      }

      function updateWorkerHeartbeatPollToggleLabel() {
        if (!els.workerHeartbeatPollToggleBtn) return;
        els.workerHeartbeatPollToggleBtn.textContent = state.workerHeartbeatPolling ? "Stop HB Poll" : "Start HB Poll";
      }

      function stopWorkerHeartbeatPolling() {
        if (state.workerHeartbeatPollTimer) {
          clearInterval(state.workerHeartbeatPollTimer);
          state.workerHeartbeatPollTimer = null;
        }
      }

      function startWorkerHeartbeatPolling() {
        stopWorkerHeartbeatPolling();
        if (!state.workerHeartbeatPolling) {
          updateWorkerHeartbeatPollToggleLabel();
          return;
        }
        refreshWorkerHeartbeat().catch(showError);
        state.workerHeartbeatPollTimer = setInterval(() => {
          refreshWorkerHeartbeat().catch(showError);
        }, workerHeartbeatPollIntervalMs());
        updateWorkerHeartbeatPollToggleLabel();
      }

      function toggleWorkerHeartbeatPolling() {
        state.workerHeartbeatPolling = !state.workerHeartbeatPolling;
        persistUiState();
        startWorkerHeartbeatPolling();
      }

      function onWorkerHeartbeatPollIntervalChange() {
        persistUiState();
        if (state.workerHeartbeatPolling) {
          startWorkerHeartbeatPolling();
        }
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

      function applyPortfolioToCTextRiskLevelFilter(tocTextRiskLevelValue) {
        els.portfolioToCTextRiskLevelFilter.value = tocTextRiskLevelValue || "";
        persistUiState();
        refreshPortfolioBundle().catch(showError);
      }

      function applyPortfolioMelRiskLevelFilter(melRiskLevelValue) {
        els.portfolioMelRiskLevelFilter.value = melRiskLevelValue || "";
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
        if (els.portfolioToCTextRiskLevelFilter.value) {
          params.set("toc_text_risk_level", els.portfolioToCTextRiskLevelFilter.value);
        }
        if (els.portfolioMelRiskLevelFilter.value) {
          params.set("mel_risk_level", els.portfolioMelRiskLevelFilter.value);
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
        if (els.reviewWorkflowFindingCodeFilter.value.trim()) {
          params.set("finding_code", els.reviewWorkflowFindingCodeFilter.value.trim());
        }
        if (els.reviewWorkflowFindingSectionFilter.value) {
          params.set("finding_section", els.reviewWorkflowFindingSectionFilter.value);
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

      function buildReviewWorkflowSlaFilterQueryString() {
        const params = new URLSearchParams();
        if (els.reviewWorkflowFindingIdFilter.value.trim()) {
          params.set("finding_id", els.reviewWorkflowFindingIdFilter.value.trim());
        }
        if (els.reviewWorkflowFindingCodeFilter.value.trim()) {
          params.set("finding_code", els.reviewWorkflowFindingCodeFilter.value.trim());
        }
        if (els.reviewWorkflowFindingSectionFilter.value) {
          params.set("finding_section", els.reviewWorkflowFindingSectionFilter.value);
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

      function buildReviewWorkflowSlaHotspotsQueryString() {
        const baseQuery = buildReviewWorkflowSlaFilterQueryString();
        const params = new URLSearchParams(baseQuery.startsWith("?") ? baseQuery.slice(1) : "");
        const topLimit = Number.parseInt(String(els.reviewWorkflowSlaTopLimitFilter.value || "").trim(), 10);
        if (Number.isFinite(topLimit) && topLimit > 0) {
          params.set("top_limit", String(topLimit));
        }
        if (els.reviewWorkflowSlaHotspotKindFilter.value) {
          params.set("hotspot_kind", els.reviewWorkflowSlaHotspotKindFilter.value);
        }
        if (els.reviewWorkflowSlaHotspotSeverityFilter.value) {
          params.set("hotspot_severity", els.reviewWorkflowSlaHotspotSeverityFilter.value);
        }
        const minOverdueHours = Number.parseFloat(String(els.reviewWorkflowSlaMinOverdueHoursFilter.value || "").trim());
        if (Number.isFinite(minOverdueHours) && minOverdueHours >= 0) {
          params.set("min_overdue_hours", String(minOverdueHours));
        }
        const q = params.toString();
        return q ? `?${q}` : "";
      }

      function buildReviewWorkflowSlaHotspotsTrendsQueryString() {
        return buildReviewWorkflowSlaHotspotsQueryString();
      }

      function buildPortfolioReviewWorkflowQueryString() {
        const baseQuery = buildPortfolioFilterQueryString();
        const params = new URLSearchParams(baseQuery.startsWith("?") ? baseQuery.slice(1) : "");
        if (els.reviewWorkflowEventTypeFilter.value) params.set("event_type", els.reviewWorkflowEventTypeFilter.value);
        if (els.reviewWorkflowFindingIdFilter.value.trim()) {
          params.set("finding_id", els.reviewWorkflowFindingIdFilter.value.trim());
        }
        if (els.reviewWorkflowFindingCodeFilter.value.trim()) {
          params.set("finding_code", els.reviewWorkflowFindingCodeFilter.value.trim());
        }
        if (els.reviewWorkflowFindingSectionFilter.value) {
          params.set("finding_section", els.reviewWorkflowFindingSectionFilter.value);
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

      function buildPortfolioReviewWorkflowTrendsQueryString() {
        return buildPortfolioReviewWorkflowQueryString();
      }

      function buildPortfolioReviewWorkflowSlaQueryString() {
        const baseQuery = buildPortfolioFilterQueryString();
        const params = new URLSearchParams(baseQuery.startsWith("?") ? baseQuery.slice(1) : "");
        if (els.reviewWorkflowFindingIdFilter.value.trim()) {
          params.set("finding_id", els.reviewWorkflowFindingIdFilter.value.trim());
        }
        if (els.reviewWorkflowFindingCodeFilter.value.trim()) {
          params.set("finding_code", els.reviewWorkflowFindingCodeFilter.value.trim());
        }
        if (els.reviewWorkflowFindingSectionFilter.value) {
          params.set("finding_section", els.reviewWorkflowFindingSectionFilter.value);
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
        const topLimit = Number.parseInt(String(els.portfolioSlaTopLimitFilter.value || "").trim(), 10);
        if (Number.isFinite(topLimit) && topLimit > 0) {
          params.set("top_limit", String(topLimit));
        }
        const q = params.toString();
        return q ? `?${q}` : "";
      }

      function buildPortfolioReviewWorkflowSlaHotspotsQueryString() {
        const baseQuery = buildPortfolioReviewWorkflowSlaQueryString();
        const params = new URLSearchParams(baseQuery.startsWith("?") ? baseQuery.slice(1) : "");
        if (els.portfolioSlaHotspotKindFilter.value) {
          params.set("hotspot_kind", els.portfolioSlaHotspotKindFilter.value);
        }
        if (els.portfolioSlaHotspotSeverityFilter.value) {
          params.set("hotspot_severity", els.portfolioSlaHotspotSeverityFilter.value);
        }
        const minOverdueHours = Number.parseFloat(String(els.portfolioSlaMinOverdueHoursFilter.value || "").trim());
        if (Number.isFinite(minOverdueHours) && minOverdueHours >= 0) {
          params.set("min_overdue_hours", String(minOverdueHours));
        }
        const q = params.toString();
        return q ? `?${q}` : "";
      }

      function buildPortfolioReviewWorkflowSlaHotspotsTrendsQueryString() {
        return buildPortfolioReviewWorkflowSlaHotspotsQueryString();
      }

      function buildPortfolioReviewWorkflowSlaTrendsQueryString() {
        return buildPortfolioReviewWorkflowSlaQueryString();
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
        renderKeyValueList(
          els.portfolioQualityToCTextRiskList,
          body.toc_text_quality?.risk_counts,
          "No ToC text-risk data yet.",
          8,
          (riskLevel) => applyPortfolioToCTextRiskLevelFilter(riskLevel)
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

      async function refreshPortfolioReviewWorkflow() {
        persistUiState();
        const q = buildPortfolioReviewWorkflowQueryString();
        const body = await apiFetch(`/portfolio/review-workflow${q}`);
        renderPortfolioReviewWorkflow(body);
        setJson(els.portfolioReviewWorkflowJson, body);
        return body;
      }

      async function refreshPortfolioReviewWorkflowSla() {
        persistUiState();
        const q = buildPortfolioReviewWorkflowSlaQueryString();
        const body = await apiFetch(`/portfolio/review-workflow/sla${q}`);
        renderPortfolioReviewWorkflowSla(body);
        setJson(els.portfolioReviewWorkflowSlaJson, body);
        return body;
      }

      async function refreshPortfolioReviewWorkflowSlaHotspots() {
        persistUiState();
        const q = buildPortfolioReviewWorkflowSlaHotspotsQueryString();
        const body = await apiFetch(`/portfolio/review-workflow/sla/hotspots${q}`);
        renderPortfolioReviewWorkflowSlaHotspots(body);
        setJson(els.portfolioReviewWorkflowSlaHotspotsJson, body);
        return body;
      }

      async function refreshPortfolioReviewWorkflowSlaHotspotsTrends() {
        persistUiState();
        const q = buildPortfolioReviewWorkflowSlaHotspotsTrendsQueryString();
        const body = await apiFetch(`/portfolio/review-workflow/sla/hotspots/trends${q}`);
        renderPortfolioReviewWorkflowSlaHotspotsTrends(body);
        setJson(els.portfolioReviewWorkflowSlaHotspotsTrendsJson, body);
        return body;
      }

      async function refreshPortfolioReviewWorkflowTrends() {
        persistUiState();
        const q = buildPortfolioReviewWorkflowTrendsQueryString();
        const body = await apiFetch(`/portfolio/review-workflow/trends${q}`);
        renderPortfolioReviewWorkflowTrends(body);
        setJson(els.portfolioReviewWorkflowTrendsJson, body);
        return body;
      }

      async function refreshPortfolioReviewWorkflowSlaTrends() {
        persistUiState();
        const q = buildPortfolioReviewWorkflowSlaTrendsQueryString();
        const body = await apiFetch(`/portfolio/review-workflow/sla/trends${q}`);
        renderPortfolioReviewWorkflowSlaTrends(body);
        setJson(els.portfolioReviewWorkflowSlaTrendsJson, body);
        return body;
      }

      async function refreshPortfolioBundle() {
        const results = await Promise.allSettled([
          refreshPortfolioMetrics(),
          refreshPortfolioQuality(),
          refreshPortfolioReviewWorkflow(),
          refreshPortfolioReviewWorkflowSla(),
          refreshPortfolioReviewWorkflowSlaHotspots(),
          refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflowTrends(),
          refreshPortfolioReviewWorkflowSlaTrends(),
        ]);
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
          refreshWorkerHeartbeat(),
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
          refreshReviewWorkflowTrends(),
          refreshReviewWorkflowSla(),
          refreshReviewWorkflowSlaTrends(),
          refreshReviewWorkflowSlaHotspots(),
          refreshReviewWorkflowSlaHotspotsTrends(),
          refreshReviewWorkflowSlaProfile(),
        ]);
      }

      async function copyExportPayloadJson() {
        const current = (els.exportPayloadJson?.textContent || "").trim();
        if (!current || current === "{}") {
          await refreshExportPayload();
        }
        const text = (els.exportPayloadJson?.textContent || "").trim();
        await copyTextToClipboard(text === "{}" ? "" : text, "Load export payload first");
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

      async function ensurePortfolioReviewWorkflowLoaded() {
        let text = (els.portfolioReviewWorkflowJson?.textContent || "").trim();
        if (!text || text === "{}") {
          await refreshPortfolioReviewWorkflow();
          text = (els.portfolioReviewWorkflowJson?.textContent || "").trim();
        }
        if (!text || text === "{}") throw new Error("Load portfolio workflow first");
        return text;
      }

      async function ensurePortfolioReviewWorkflowSlaLoaded() {
        let text = (els.portfolioReviewWorkflowSlaJson?.textContent || "").trim();
        if (!text || text === "{}") {
          await refreshPortfolioReviewWorkflowSla();
          text = (els.portfolioReviewWorkflowSlaJson?.textContent || "").trim();
        }
        if (!text || text === "{}") throw new Error("Load portfolio workflow SLA first");
        return text;
      }

      async function ensurePortfolioReviewWorkflowSlaHotspotsLoaded() {
        let text = (els.portfolioReviewWorkflowSlaHotspotsJson?.textContent || "").trim();
        if (!text || text === "{}") {
          await refreshPortfolioReviewWorkflowSlaHotspots();
          text = (els.portfolioReviewWorkflowSlaHotspotsJson?.textContent || "").trim();
        }
        if (!text || text === "{}") throw new Error("Load portfolio workflow SLA hotspots first");
        return text;
      }

      async function ensurePortfolioReviewWorkflowSlaHotspotsTrendsLoaded() {
        let text = (els.portfolioReviewWorkflowSlaHotspotsTrendsJson?.textContent || "").trim();
        if (!text || text === "{}") {
          await refreshPortfolioReviewWorkflowSlaHotspotsTrends();
          text = (els.portfolioReviewWorkflowSlaHotspotsTrendsJson?.textContent || "").trim();
        }
        if (!text || text === "{}") throw new Error("Load portfolio workflow SLA hotspots trends first");
        return text;
      }

      async function ensurePortfolioReviewWorkflowTrendsLoaded() {
        let text = (els.portfolioReviewWorkflowTrendsJson?.textContent || "").trim();
        if (!text || text === "{}") {
          await refreshPortfolioReviewWorkflowTrends();
          text = (els.portfolioReviewWorkflowTrendsJson?.textContent || "").trim();
        }
        if (!text || text === "{}") throw new Error("Load portfolio workflow trends first");
        return text;
      }

      async function ensurePortfolioReviewWorkflowSlaTrendsLoaded() {
        let text = (els.portfolioReviewWorkflowSlaTrendsJson?.textContent || "").trim();
        if (!text || text === "{}") {
          await refreshPortfolioReviewWorkflowSlaTrends();
          text = (els.portfolioReviewWorkflowSlaTrendsJson?.textContent || "").trim();
        }
        if (!text || text === "{}") throw new Error("Load portfolio workflow SLA trends first");
        return text;
      }

      async function ensureReviewWorkflowSlaHotspotsLoaded() {
        let text = (els.reviewWorkflowSlaHotspotsJson?.textContent || "").trim();
        if (!text || text === "{}") {
          await refreshReviewWorkflowSlaHotspots();
          text = (els.reviewWorkflowSlaHotspotsJson?.textContent || "").trim();
        }
        if (!text || text === "{}") throw new Error("Load workflow SLA hotspots first");
        return text;
      }

      async function ensureReviewWorkflowSlaHotspotsTrendsLoaded() {
        let text = (els.reviewWorkflowSlaHotspotsTrendsJson?.textContent || "").trim();
        if (!text || text === "{}") {
          await refreshReviewWorkflowSlaHotspotsTrends();
          text = (els.reviewWorkflowSlaHotspotsTrendsJson?.textContent || "").trim();
        }
        if (!text || text === "{}") throw new Error("Load workflow SLA hotspots trends first");
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

      async function exportPortfolioAggregate(
        endpointPath,
        format,
        fallbackFilename,
        queryBuilder = buildPortfolioFilterQueryString
      ) {
        persistUiState();
        persistBasics();
        const q = typeof queryBuilder === "function" ? queryBuilder() : buildPortfolioFilterQueryString();
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

      async function exportReviewWorkflowTrendsAggregate(format) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        persistUiState();
        persistBasics();
        const q = buildReviewWorkflowFilterQueryString();
        const params = new URLSearchParams(q.startsWith("?") ? q.slice(1) : "");
        params.set("format", format);
        if (exportGzipEnabled()) params.set("gzip", "true");
        const query = params.toString();
        const endpointPath = `/status/${encodeURIComponent(jobId)}/review/workflow/trends/export`;
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
        const fallbackFilename = `grantflow_review_workflow_trends_${jobId}.${format}${exportGzipEnabled() ? ".gz" : ""}`;
        const filename = parseDownloadFilenameFromDisposition(
          res.headers.get("content-disposition"),
          fallbackFilename
        );
        const blob = await res.blob();
        downloadBlob(blob, filename);
      }

      async function exportReviewWorkflowSlaAggregate(format) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        persistUiState();
        persistBasics();
        const q = buildReviewWorkflowSlaFilterQueryString();
        const params = new URLSearchParams(q.startsWith("?") ? q.slice(1) : "");
        params.set("format", format);
        if (exportGzipEnabled()) params.set("gzip", "true");
        const query = params.toString();
        const endpointPath = `/status/${encodeURIComponent(jobId)}/review/workflow/sla/export`;
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
        const fallbackFilename = `grantflow_review_workflow_sla_${jobId}.${format}${exportGzipEnabled() ? ".gz" : ""}`;
        const filename = parseDownloadFilenameFromDisposition(
          res.headers.get("content-disposition"),
          fallbackFilename
        );
        const blob = await res.blob();
        downloadBlob(blob, filename);
      }

      async function exportReviewWorkflowSlaTrendsAggregate(format) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        persistUiState();
        persistBasics();
        const q = buildReviewWorkflowSlaFilterQueryString();
        const params = new URLSearchParams(q.startsWith("?") ? q.slice(1) : "");
        params.set("format", format);
        if (exportGzipEnabled()) params.set("gzip", "true");
        const query = params.toString();
        const endpointPath = `/status/${encodeURIComponent(jobId)}/review/workflow/sla/trends/export`;
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
        const fallbackFilename = `grantflow_review_workflow_sla_trends_${jobId}.${format}${exportGzipEnabled() ? ".gz" : ""}`;
        const filename = parseDownloadFilenameFromDisposition(
          res.headers.get("content-disposition"),
          fallbackFilename
        );
        const blob = await res.blob();
        downloadBlob(blob, filename);
      }

      async function exportReviewWorkflowSlaHotspotsAggregate(format) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        persistUiState();
        persistBasics();
        const q = buildReviewWorkflowSlaHotspotsQueryString();
        const params = new URLSearchParams(q.startsWith("?") ? q.slice(1) : "");
        params.set("format", format);
        if (exportGzipEnabled()) params.set("gzip", "true");
        const query = params.toString();
        const endpointPath = `/status/${encodeURIComponent(jobId)}/review/workflow/sla/hotspots/export`;
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
        const fallbackFilename = `grantflow_review_workflow_sla_hotspots_${jobId}.${format}${exportGzipEnabled() ? ".gz" : ""}`;
        const filename = parseDownloadFilenameFromDisposition(
          res.headers.get("content-disposition"),
          fallbackFilename
        );
        const blob = await res.blob();
        downloadBlob(blob, filename);
      }

      async function exportReviewWorkflowSlaHotspotsTrendsAggregate(format) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        persistUiState();
        persistBasics();
        const q = buildReviewWorkflowSlaHotspotsTrendsQueryString();
        const params = new URLSearchParams(q.startsWith("?") ? q.slice(1) : "");
        params.set("format", format);
        if (exportGzipEnabled()) params.set("gzip", "true");
        const query = params.toString();
        const endpointPath = `/status/${encodeURIComponent(jobId)}/review/workflow/sla/hotspots/trends/export`;
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
        const fallbackFilename = `grantflow_review_workflow_sla_hotspots_trends_${jobId}.${format}${exportGzipEnabled() ? ".gz" : ""}`;
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

      async function copyPortfolioReviewWorkflowJson() {
        const text = await ensurePortfolioReviewWorkflowLoaded();
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(text);
      }

      async function copyPortfolioReviewWorkflowSlaJson() {
        const text = await ensurePortfolioReviewWorkflowSlaLoaded();
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(text);
      }

      async function copyPortfolioReviewWorkflowSlaHotspotsJson() {
        const text = await ensurePortfolioReviewWorkflowSlaHotspotsLoaded();
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(text);
      }

      async function copyPortfolioReviewWorkflowSlaHotspotsTrendsJson() {
        const text = await ensurePortfolioReviewWorkflowSlaHotspotsTrendsLoaded();
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(text);
      }

      async function copyPortfolioReviewWorkflowTrendsJson() {
        const text = await ensurePortfolioReviewWorkflowTrendsLoaded();
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(text);
      }

      async function copyPortfolioReviewWorkflowSlaTrendsJson() {
        const text = await ensurePortfolioReviewWorkflowSlaTrendsLoaded();
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(text);
      }

      async function copyReviewWorkflowSlaHotspotsJson() {
        const text = await ensureReviewWorkflowSlaHotspotsLoaded();
        if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
          throw new Error("Clipboard API is not available in this browser");
        }
        await navigator.clipboard.writeText(text);
      }

      async function copyReviewWorkflowSlaHotspotsTrendsJson() {
        const text = await ensureReviewWorkflowSlaHotspotsTrendsLoaded();
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

      async function downloadPortfolioReviewWorkflowJson() {
        await ensurePortfolioReviewWorkflowLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/export",
          "json",
          "grantflow_portfolio_review_workflow.json",
          buildPortfolioReviewWorkflowQueryString
        );
      }

      async function downloadPortfolioReviewWorkflowCsv() {
        await ensurePortfolioReviewWorkflowLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/export",
          "csv",
          "grantflow_portfolio_review_workflow.csv",
          buildPortfolioReviewWorkflowQueryString
        );
      }

      async function downloadPortfolioReviewWorkflowSlaJson() {
        await ensurePortfolioReviewWorkflowSlaLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/sla/export",
          "json",
          "grantflow_portfolio_review_workflow_sla.json",
          buildPortfolioReviewWorkflowSlaQueryString
        );
      }

      async function downloadPortfolioReviewWorkflowSlaCsv() {
        await ensurePortfolioReviewWorkflowSlaLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/sla/export",
          "csv",
          "grantflow_portfolio_review_workflow_sla.csv",
          buildPortfolioReviewWorkflowSlaQueryString
        );
      }

      async function downloadPortfolioReviewWorkflowSlaHotspotsJson() {
        await ensurePortfolioReviewWorkflowSlaHotspotsLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/sla/hotspots/export",
          "json",
          "grantflow_portfolio_review_workflow_sla_hotspots.json",
          buildPortfolioReviewWorkflowSlaHotspotsQueryString
        );
      }

      async function downloadPortfolioReviewWorkflowSlaHotspotsCsv() {
        await ensurePortfolioReviewWorkflowSlaHotspotsLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/sla/hotspots/export",
          "csv",
          "grantflow_portfolio_review_workflow_sla_hotspots.csv",
          buildPortfolioReviewWorkflowSlaHotspotsQueryString
        );
      }

      async function downloadPortfolioReviewWorkflowSlaHotspotsTrendsJson() {
        await ensurePortfolioReviewWorkflowSlaHotspotsTrendsLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/sla/hotspots/trends/export",
          "json",
          "grantflow_portfolio_review_workflow_sla_hotspots_trends.json",
          buildPortfolioReviewWorkflowSlaHotspotsTrendsQueryString
        );
      }

      async function downloadPortfolioReviewWorkflowSlaHotspotsTrendsCsv() {
        await ensurePortfolioReviewWorkflowSlaHotspotsTrendsLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/sla/hotspots/trends/export",
          "csv",
          "grantflow_portfolio_review_workflow_sla_hotspots_trends.csv",
          buildPortfolioReviewWorkflowSlaHotspotsTrendsQueryString
        );
      }

      async function downloadPortfolioReviewWorkflowTrendsJson() {
        await ensurePortfolioReviewWorkflowTrendsLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/trends/export",
          "json",
          "grantflow_portfolio_review_workflow_trends.json",
          buildPortfolioReviewWorkflowTrendsQueryString
        );
      }

      async function downloadPortfolioReviewWorkflowTrendsCsv() {
        await ensurePortfolioReviewWorkflowTrendsLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/trends/export",
          "csv",
          "grantflow_portfolio_review_workflow_trends.csv",
          buildPortfolioReviewWorkflowTrendsQueryString
        );
      }

      async function downloadPortfolioReviewWorkflowSlaTrendsJson() {
        await ensurePortfolioReviewWorkflowSlaTrendsLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/sla/trends/export",
          "json",
          "grantflow_portfolio_review_workflow_sla_trends.json",
          buildPortfolioReviewWorkflowSlaTrendsQueryString
        );
      }

      async function downloadPortfolioReviewWorkflowSlaTrendsCsv() {
        await ensurePortfolioReviewWorkflowSlaTrendsLoaded();
        await exportPortfolioAggregate(
          "/portfolio/review-workflow/sla/trends/export",
          "csv",
          "grantflow_portfolio_review_workflow_sla_trends.csv",
          buildPortfolioReviewWorkflowSlaTrendsQueryString
        );
      }

      async function downloadReviewWorkflowJson() {
        await refreshReviewWorkflow();
        await exportReviewWorkflowAggregate("json");
      }

      async function downloadReviewWorkflowCsv() {
        await refreshReviewWorkflow();
        await exportReviewWorkflowAggregate("csv");
      }

      async function downloadReviewWorkflowTrendsJson() {
        await refreshReviewWorkflowTrends();
        await exportReviewWorkflowTrendsAggregate("json");
      }

      async function downloadReviewWorkflowTrendsCsv() {
        await refreshReviewWorkflowTrends();
        await exportReviewWorkflowTrendsAggregate("csv");
      }

      async function downloadReviewWorkflowSlaJson() {
        await refreshReviewWorkflowSla();
        await exportReviewWorkflowSlaAggregate("json");
      }

      async function downloadReviewWorkflowSlaCsv() {
        await refreshReviewWorkflowSla();
        await exportReviewWorkflowSlaAggregate("csv");
      }

      async function downloadReviewWorkflowSlaTrendsJson() {
        await refreshReviewWorkflowSlaTrends();
        await exportReviewWorkflowSlaTrendsAggregate("json");
      }

      async function downloadReviewWorkflowSlaTrendsCsv() {
        await refreshReviewWorkflowSlaTrends();
        await exportReviewWorkflowSlaTrendsAggregate("csv");
      }

      async function downloadReviewWorkflowSlaHotspotsJson() {
        await ensureReviewWorkflowSlaHotspotsLoaded();
        await exportReviewWorkflowSlaHotspotsAggregate("json");
      }

      async function downloadReviewWorkflowSlaHotspotsCsv() {
        await ensureReviewWorkflowSlaHotspotsLoaded();
        await exportReviewWorkflowSlaHotspotsAggregate("csv");
      }

      async function downloadReviewWorkflowSlaHotspotsTrendsJson() {
        await ensureReviewWorkflowSlaHotspotsTrendsLoaded();
        await exportReviewWorkflowSlaHotspotsTrendsAggregate("json");
      }

      async function downloadReviewWorkflowSlaHotspotsTrendsCsv() {
        await ensureReviewWorkflowSlaHotspotsTrendsLoaded();
        await exportReviewWorkflowSlaHotspotsTrendsAggregate("csv");
      }

      function formatExportPolicyError(statusCode, detail, rawBody) {
        if (Number(statusCode) !== 409 || !detail || typeof detail !== "object") return "";
        const reason = String(detail.reason || "").trim();
        if (reason === "export_contract_policy_block") {
          const gate = detail.export_contract_gate && typeof detail.export_contract_gate === "object"
            ? detail.export_contract_gate
            : {};
          const mode = String(gate.mode || "strict");
          const status = String(gate.status || "warning");
          const missingSections = Array.isArray(gate.missing_required_sections)
            ? gate.missing_required_sections.map((x) => String(x || "").trim()).filter(Boolean)
            : [];
          const missingSheets = Array.isArray(gate.missing_required_sheets)
            ? gate.missing_required_sheets.map((x) => String(x || "").trim()).filter(Boolean)
            : [];
          const reasons = Array.isArray(gate.reasons)
            ? gate.reasons.map((x) => String(x || "").trim()).filter(Boolean)
            : [];
          const parts = [
            `Production export blocked by export contract policy (mode=${mode}, status=${status}).`,
          ];
          if (missingSections.length) parts.push(`Missing ToC sections: ${missingSections.join(", ")}.`);
          if (missingSheets.length) parts.push(`Missing workbook sheets: ${missingSheets.join(", ")}.`);
          if (reasons.length) parts.push(`Reasons: ${reasons.join(", ")}.`);
          parts.push("Use non-production export, fix missing sections/sheets, or set allow_unsafe_export=true.");
          return parts.join(" ");
        }
        if (reason === "export_grounding_policy_block") {
          const policy = detail.export_grounding_policy && typeof detail.export_grounding_policy === "object"
            ? detail.export_grounding_policy
            : {};
          const summary = String(policy.summary || "").trim();
          const reasons = Array.isArray(policy.reasons)
            ? policy.reasons.map((x) => String(x || "").trim()).filter(Boolean)
            : [];
          const mode = String(policy.mode || "strict");
          return `Export blocked by grounding policy (mode=${mode})${summary ? `: ${summary}` : ""}${reasons.length ? `. Reasons: ${reasons.join(", ")}.` : "."}`;
        }
        if (reason === "grounding_gate_strict_block") {
          const gate = detail.grounding_gate && typeof detail.grounding_gate === "object" ? detail.grounding_gate : {};
          const summary = String(gate.summary || "").trim() || "strict grounding gate failed";
          return `Export blocked by strict grounding gate: ${summary}.`;
        }
        return typeof rawBody === "object" ? "" : String(rawBody || "");
      }

      async function exportZipFromPayload(opts = {}) {
        const enforcedProduction = Boolean(opts && opts.enforcedProduction);
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
        persistUiState();
        const requestBody = {
          payload: parsed.payload,
          format: "both",
          production_export: enforcedProduction ? true : productionExportEnabled(),
          allow_unsafe_export: enforcedProduction ? false : allowUnsafeExportEnabled(),
        };
        const res = await fetch(`${apiBase()}/export`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...headers() },
          body: JSON.stringify(requestBody),
        });
        if (!res.ok) {
          const ct = res.headers.get("content-type") || "";
          let body = null;
          let errText = "";
          if (ct.includes("application/json")) {
            body = await res.json();
            const detail = body && typeof body === "object" ? body.detail : null;
            const pretty = formatExportPolicyError(res.status, detail, body);
            errText = pretty || JSON.stringify(body, null, 2);
          } else {
            errText = await res.text();
          }
          throw new Error(errText || `Export failed (${res.status})`);
        }

        const payloadRoot = parsed && typeof parsed.payload === "object" ? parsed.payload : {};
        const stateRoot = payloadRoot && typeof payloadRoot.state === "object" ? payloadRoot.state : {};
        const payloadContract = payloadRoot.export_contract || stateRoot.export_contract_gate || null;
        if (payloadContract && typeof payloadContract === "object") {
          const headerMode = String(res.headers.get("x-grantflow-export-contract-mode") || "").trim();
          const headerStatus = String(res.headers.get("x-grantflow-export-contract-status") || "").trim();
          const headerSummary = String(res.headers.get("x-grantflow-export-contract-summary") || "").trim();
          const mergedContract = { ...payloadContract };
          if (headerMode) mergedContract.mode = headerMode;
          if (headerStatus) mergedContract.status = headerStatus;
          if (headerSummary) mergedContract.summary = headerSummary;
          renderExportContract(mergedContract);
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
        await Promise.allSettled([
          refreshComments(),
          refreshReviewWorkflow(),
          refreshReviewWorkflowTrends(),
          refreshReviewWorkflowSlaHotspots(),
          refreshReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflow(),
          refreshPortfolioReviewWorkflowSla(),
          refreshPortfolioReviewWorkflowSlaHotspots(),
          refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflowTrends(),
          refreshPortfolioReviewWorkflowSlaTrends(),
        ]);
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
        await Promise.allSettled([
          refreshCritic(),
          refreshReviewWorkflow(),
          refreshReviewWorkflowTrends(),
          refreshReviewWorkflowSlaHotspots(),
          refreshReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflow(),
          refreshPortfolioReviewWorkflowSla(),
          refreshPortfolioReviewWorkflowSlaHotspots(),
          refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflowTrends(),
          refreshPortfolioReviewWorkflowSlaTrends(),
        ]);
        return updated;
      }

      async function applyCriticBulkStatus({ dryRun = false } = {}) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        const nextStatus = String(els.criticBulkTargetStatus.value || "").trim();
        if (!nextStatus) throw new Error("Select bulk target status");
        const scope = String(els.criticBulkScope.value || "filtered").trim().toLowerCase();

        const payload = { next_status: nextStatus };
        if (dryRun) payload.dry_run = true;
        if (scope === "all") {
          payload.apply_to_all = true;
        } else if (scope === "selected") {
          const findingIds = parseIdList(els.criticSelectedFindingIds.value);
          if (!findingIds.length) throw new Error("Add at least one finding id for selected bulk apply");
          payload.finding_ids = findingIds;
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
        const action = describeBulkAction(nextStatus, "finding");
        setJson(els.criticBulkResultJson, result);
        renderBulkPreviewSummary(els.criticBulkSummaryList, result, {
          notFoundKey: "not_found_finding_ids",
          updatedKey: "updated_findings",
          itemLabel: "findings",
          scopeLabel: describeBulkScope(scope, parseIdList(els.criticSelectedFindingIds.value).length, "finding ids"),
          filterBasis: describeCriticFilterBasis(scope),
          statusTransition: describeStatusTransition(result, payload.finding_status, nextStatus),
          queueLabel: action.queueLabel,
        });
        await Promise.allSettled([
          refreshCritic(),
          refreshReviewWorkflow(),
          refreshReviewWorkflowTrends(),
          refreshReviewWorkflowSlaHotspots(),
          refreshReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflow(),
          refreshPortfolioReviewWorkflowSla(),
          refreshPortfolioReviewWorkflowSlaHotspots(),
          refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflowTrends(),
          refreshPortfolioReviewWorkflowSlaTrends(),
        ]);
        return result;
      }

      async function setCommentStatus(nextStatus) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        const commentId = els.selectedCommentId.value.trim();
        if (!commentId) throw new Error("Select a comment first");
        const actionByStatus = {
          acknowledged: "ack",
          resolved: "resolve",
          open: "reopen",
        };
        const action = actionByStatus[nextStatus];
        if (!action) throw new Error(`Unsupported comment status: ${String(nextStatus)}`);
        const updated = await apiFetch(
          `/status/${encodeURIComponent(jobId)}/comments/${encodeURIComponent(commentId)}/${action}`,
          { method: "POST" }
        );
        await Promise.allSettled([
          refreshComments(),
          refreshReviewWorkflow(),
          refreshReviewWorkflowTrends(),
          refreshReviewWorkflowSlaHotspots(),
          refreshReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflow(),
          refreshPortfolioReviewWorkflowSla(),
          refreshPortfolioReviewWorkflowSlaHotspots(),
          refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflowTrends(),
          refreshPortfolioReviewWorkflowSlaTrends(),
        ]);
        return updated;
      }

      async function applyCommentBulkStatus({ dryRun = false } = {}) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        const nextStatus = String(els.commentBulkTargetStatus.value || "").trim();
        if (!nextStatus) throw new Error("Select bulk comment target status");
        const scope = String(els.commentBulkScope.value || "filtered").trim().toLowerCase();
        const payload = { next_status: nextStatus };
        if (dryRun) payload.dry_run = true;
        if (scope === "all") {
          payload.apply_to_all = true;
        } else if (scope === "selected") {
          const commentIds = parseIdList(els.commentSelectedCommentIds.value);
          if (!commentIds.length) throw new Error("Add at least one comment id for selected bulk apply");
          payload.comment_ids = commentIds;
        } else {
          const section = String(els.commentsFilterSection.value || "").trim();
          const commentStatus = String(els.commentsFilterStatus.value || "").trim();
          const versionId = String(els.commentsFilterVersionId.value || "").trim();
          if (section) payload.section = section;
          if (commentStatus) payload.comment_status = commentStatus;
          if (versionId) payload.version_id = versionId;
          if (!payload.section && !payload.comment_status && !payload.version_id) {
            throw new Error("For filtered bulk apply, set at least one comment filter or use scope=all");
          }
        }
        const result = await apiFetch(`/status/${encodeURIComponent(jobId)}/comments/bulk-status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const action = describeBulkAction(nextStatus, "comment");
        setJson(els.commentBulkResultJson, result);
        renderBulkPreviewSummary(els.commentBulkSummaryList, result, {
          notFoundKey: "not_found_comment_ids",
          updatedKey: "updated_comments",
          itemLabel: "comments",
          scopeLabel: describeBulkScope(scope, parseIdList(els.commentSelectedCommentIds.value).length, "comment ids"),
          filterBasis: describeCommentFilterBasis(scope),
          statusTransition: describeStatusTransition(result, payload.comment_status, nextStatus),
          queueLabel: action.queueLabel,
        });
        await Promise.allSettled([
          refreshComments(),
          refreshReviewWorkflow(),
          refreshReviewWorkflowTrends(),
          refreshReviewWorkflowSlaHotspots(),
          refreshReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflow(),
          refreshPortfolioReviewWorkflowSla(),
          refreshPortfolioReviewWorkflowSlaHotspots(),
          refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
          refreshPortfolioReviewWorkflowTrends(),
          refreshPortfolioReviewWorkflowSlaTrends(),
        ]);
        return result;
      }

      async function copySelectedFindingIds() {
        await copyTextToClipboard(els.criticSelectedFindingIds.value, "No selected finding ids to copy");
      }

      async function copySelectedCommentIds() {
        await copyTextToClipboard(els.commentSelectedCommentIds.value, "No selected comment ids to copy");
      }

      function loadFindingIdsFromWorkflow() {
        const ids = collectWorkflowFindingIds();
        if (!ids.length) throw new Error("No finding ids found in current workflow view");
        mergeIdsIntoTextarea(els.criticSelectedFindingIds, ids);
      }

      function loadCommentIdsFromWorkflow() {
        const ids = collectWorkflowCommentIds();
        if (!ids.length) throw new Error("No comment ids found in current workflow view");
        mergeIdsIntoTextarea(els.commentSelectedCommentIds, ids);
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

      function toggleQualityGroundedGateExplain() {
        state.qualityGroundedGateExplainExpanded = !state.qualityGroundedGateExplainExpanded;
        const summary = state.lastQualitySummary && typeof state.lastQualitySummary === "object" ? state.lastQualitySummary : {};
        const groundedGate =
          summary.grounded_gate && typeof summary.grounded_gate === "object" && !Array.isArray(summary.grounded_gate)
            ? summary.grounded_gate
            : {};
        renderQualityGroundedGateExplain(groundedGate);
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
        els.exportProductionZipFromPayloadBtn.addEventListener("click", () =>
          exportZipFromPayload({ enforcedProduction: true }).catch((err) => showError(err))
        );
        els.eventsBtn.addEventListener("click", () => refreshEvents().catch(showError));
        els.criticBtn.addEventListener("click", () => refreshCritic().catch(showError));
        els.criticBulkApplyBtn.addEventListener("click", () => applyCriticBulkStatus().catch(showError));
        els.criticBulkPreviewBtn.addEventListener("click", () => applyCriticBulkStatus({ dryRun: true }).catch(showError));
        els.criticAddSelectedFindingBtn.addEventListener("click", () => {
          try {
            const findingId = String(els.criticSelectedFindingId.value || "").trim();
            if (!findingId) throw new Error("No latest finding id selected");
            mergeIdsIntoTextarea(els.criticSelectedFindingIds, [findingId]);
            updateCriticBulkActionUi();
          } catch (err) {
            showError(err);
          }
        });
        els.criticClearSelectedFindingIdsBtn.addEventListener("click", () => {
          els.criticSelectedFindingIds.value = "";
          persistUiState();
          updateCriticBulkActionUi();
        });
        renderBulkPreviewSummary(els.criticBulkSummaryList, null, {
          notFoundKey: "not_found_finding_ids",
          updatedKey: "updated_findings",
          itemLabel: "findings",
          scopeLabel: "-",
          filterBasis: "-",
          statusTransition: "-",
          queueLabel: "-",
        });
        els.criticCopySelectedFindingIdsBtn.addEventListener("click", () =>
          copySelectedFindingIds().catch((err) => showError(err))
        );
        els.criticLoadFindingIdsFromWorkflowBtn.addEventListener("click", () => {
          try {
            loadFindingIdsFromWorkflow();
            updateCriticBulkActionUi();
          } catch (err) {
            showError(err);
          }
        });
        [els.criticBulkTargetStatus, els.criticBulkScope, els.criticSelectedFindingIds].forEach((el) => {
          el?.addEventListener("change", updateCriticBulkActionUi);
          el?.addEventListener("input", updateCriticBulkActionUi);
        });
        els.criticBulkClearFiltersBtn.addEventListener("click", () => {
          clearCriticFilters();
          if (state.lastCritic) renderCriticLists(state.lastCritic);
          else refreshCritic().catch(showError);
        });
        els.criticSyncWorkflowFiltersBtn.addEventListener("click", () => {
          try {
            syncCriticFiltersFromWorkflow();
          } catch (err) {
            showError(err);
          }
        });
        els.qualityBtn.addEventListener("click", () => refreshQuality().catch(showError));
        els.workerHeartbeatBtn.addEventListener("click", () => refreshWorkerHeartbeat().catch(showError));
        els.workerHeartbeatPollToggleBtn.addEventListener("click", toggleWorkerHeartbeatPolling);
        els.workerHeartbeatPollSeconds.addEventListener("change", onWorkerHeartbeatPollIntervalChange);
        if (els.qualityGroundedGateExplainBtn) {
          els.qualityGroundedGateExplainBtn.addEventListener("click", toggleQualityGroundedGateExplain);
        }
        els.portfolioBtn.addEventListener("click", () => {
          refreshPortfolioBundle().catch(showError);
        });
        els.portfolioReviewWorkflowBtn.addEventListener("click", () => {
          refreshPortfolioReviewWorkflow().catch(showError);
        });
        els.portfolioReviewWorkflowSlaBtn.addEventListener("click", () => {
          refreshPortfolioReviewWorkflowSla().catch(showError);
        });
        els.portfolioReviewWorkflowSlaHotspotsBtn.addEventListener("click", () => {
          refreshPortfolioReviewWorkflowSlaHotspots().catch(showError);
        });
        els.portfolioReviewWorkflowSlaHotspotsTrendsBtn.addEventListener("click", () => {
          refreshPortfolioReviewWorkflowSlaHotspotsTrends().catch(showError);
        });
        els.portfolioReviewWorkflowTrendsBtn.addEventListener("click", () => {
          refreshPortfolioReviewWorkflowTrends().catch(showError);
        });
        els.portfolioReviewWorkflowSlaTrendsBtn.addEventListener("click", () => {
          refreshPortfolioReviewWorkflowSlaTrends().catch(showError);
        });
        els.portfolioClearBtn.addEventListener("click", () => {
          clearPortfolioFilters();
          refreshPortfolioBundle().catch(showError);
        });
        els.clearPortfolioToCTextRiskBtn.addEventListener("click", () => {
          clearPortfolioToCTextRiskFilter();
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
        els.exportPortfolioReviewWorkflowJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowJson().catch((err) => showError(err))
        );
        els.exportPortfolioReviewWorkflowCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowCsv().catch((err) => showError(err))
        );
        els.exportPortfolioReviewWorkflowSlaJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaJson().catch((err) => showError(err))
        );
        els.exportPortfolioReviewWorkflowSlaCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaCsv().catch((err) => showError(err))
        );
        els.exportPortfolioReviewWorkflowSlaHotspotsJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaHotspotsJson().catch((err) => showError(err))
        );
        els.exportPortfolioReviewWorkflowSlaHotspotsCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaHotspotsCsv().catch((err) => showError(err))
        );
        els.exportPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaHotspotsTrendsJson().catch((err) => showError(err))
        );
        els.exportPortfolioReviewWorkflowSlaHotspotsTrendsCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaHotspotsTrendsCsv().catch((err) => showError(err))
        );
        els.exportPortfolioReviewWorkflowTrendsJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowTrendsJson().catch((err) => showError(err))
        );
        els.exportPortfolioReviewWorkflowTrendsCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowTrendsCsv().catch((err) => showError(err))
        );
        els.exportPortfolioReviewWorkflowSlaTrendsJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaTrendsJson().catch((err) => showError(err))
        );
        els.exportPortfolioReviewWorkflowSlaTrendsCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaTrendsCsv().catch((err) => showError(err))
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
        els.copyPortfolioReviewWorkflowJsonBtn.addEventListener("click", () =>
          copyPortfolioReviewWorkflowJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowCsv().catch((err) => showError(err))
        );
        els.copyPortfolioReviewWorkflowSlaJsonBtn.addEventListener("click", () =>
          copyPortfolioReviewWorkflowSlaJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowSlaJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowSlaCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaCsv().catch((err) => showError(err))
        );
        els.copyPortfolioReviewWorkflowSlaHotspotsJsonBtn.addEventListener("click", () =>
          copyPortfolioReviewWorkflowSlaHotspotsJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowSlaHotspotsJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaHotspotsJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowSlaHotspotsCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaHotspotsCsv().catch((err) => showError(err))
        );
        els.copyPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn.addEventListener("click", () =>
          copyPortfolioReviewWorkflowSlaHotspotsTrendsJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowSlaHotspotsTrendsJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaHotspotsTrendsJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowSlaHotspotsTrendsCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaHotspotsTrendsCsv().catch((err) => showError(err))
        );
        els.copyPortfolioReviewWorkflowTrendsJsonBtn.addEventListener("click", () =>
          copyPortfolioReviewWorkflowTrendsJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowTrendsJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowTrendsJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowTrendsCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowTrendsCsv().catch((err) => showError(err))
        );
        els.copyPortfolioReviewWorkflowSlaTrendsJsonBtn.addEventListener("click", () =>
          copyPortfolioReviewWorkflowSlaTrendsJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowSlaTrendsJsonBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaTrendsJson().catch((err) => showError(err))
        );
        els.downloadPortfolioReviewWorkflowSlaTrendsCsvBtn.addEventListener("click", () =>
          downloadPortfolioReviewWorkflowSlaTrendsCsv().catch((err) => showError(err))
        );
        els.commentsBtn.addEventListener("click", () => refreshComments().catch(showError));
        els.reviewWorkflowBtn.addEventListener("click", () => {
          Promise.allSettled([
            refreshReviewWorkflow(),
            refreshReviewWorkflowTrends(),
            refreshReviewWorkflowSla(),
            refreshReviewWorkflowSlaTrends(),
            refreshReviewWorkflowSlaHotspots(),
            refreshReviewWorkflowSlaHotspotsTrends(),
            refreshReviewWorkflowSlaProfile(),
            refreshPortfolioReviewWorkflow(),
            refreshPortfolioReviewWorkflowSla(),
            refreshPortfolioReviewWorkflowSlaHotspots(),
            refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
            refreshPortfolioReviewWorkflowTrends(),
            refreshPortfolioReviewWorkflowSlaTrends(),
          ]).catch(showError);
        });
        els.reviewWorkflowTrendsBtn.addEventListener("click", () => refreshReviewWorkflowTrends().catch(showError));
        els.reviewWorkflowSlaBtn.addEventListener("click", () => refreshReviewWorkflowSla().catch(showError));
        els.reviewWorkflowSlaHotspotsBtn.addEventListener("click", () => refreshReviewWorkflowSlaHotspots().catch(showError));
        els.reviewWorkflowSlaHotspotsTrendsBtn.addEventListener("click", () =>
          refreshReviewWorkflowSlaHotspotsTrends().catch(showError)
        );
        els.reviewWorkflowSlaTrendsBtn.addEventListener("click", () => refreshReviewWorkflowSlaTrends().catch(showError));
        els.reviewWorkflowSlaProfileBtn.addEventListener("click", () => refreshReviewWorkflowSlaProfile().catch(showError));
        els.reviewWorkflowSlaRecomputeBtn.addEventListener("click", () => recomputeReviewWorkflowSla().catch(showError));
        els.reviewWorkflowTrendsExportJsonBtn.addEventListener("click", () =>
          downloadReviewWorkflowTrendsJson().catch((err) => showError(err))
        );
        els.reviewWorkflowTrendsExportCsvBtn.addEventListener("click", () =>
          downloadReviewWorkflowTrendsCsv().catch((err) => showError(err))
        );
        els.reviewWorkflowSlaExportJsonBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaJson().catch((err) => showError(err))
        );
        els.reviewWorkflowSlaExportCsvBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaCsv().catch((err) => showError(err))
        );
        els.reviewWorkflowSlaTrendsExportJsonBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaTrendsJson().catch((err) => showError(err))
        );
        els.reviewWorkflowSlaTrendsExportCsvBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaTrendsCsv().catch((err) => showError(err))
        );
        els.reviewWorkflowSlaHotspotsExportJsonBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaHotspotsJson().catch((err) => showError(err))
        );
        els.reviewWorkflowSlaHotspotsExportCsvBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaHotspotsCsv().catch((err) => showError(err))
        );
        els.reviewWorkflowSlaHotspotsTrendsExportJsonBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaHotspotsTrendsJson().catch((err) => showError(err))
        );
        els.reviewWorkflowSlaHotspotsTrendsExportCsvBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaHotspotsTrendsCsv().catch((err) => showError(err))
        );
        els.copyReviewWorkflowSlaHotspotsJsonBtn.addEventListener("click", () =>
          copyReviewWorkflowSlaHotspotsJson().catch((err) => showError(err))
        );
        els.downloadReviewWorkflowSlaHotspotsJsonBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaHotspotsJson().catch((err) => showError(err))
        );
        els.downloadReviewWorkflowSlaHotspotsCsvBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaHotspotsCsv().catch((err) => showError(err))
        );
        els.copyReviewWorkflowSlaHotspotsTrendsJsonBtn.addEventListener("click", () =>
          copyReviewWorkflowSlaHotspotsTrendsJson().catch((err) => showError(err))
        );
        els.downloadReviewWorkflowSlaHotspotsTrendsJsonBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaHotspotsTrendsJson().catch((err) => showError(err))
        );
        els.downloadReviewWorkflowSlaHotspotsTrendsCsvBtn.addEventListener("click", () =>
          downloadReviewWorkflowSlaHotspotsTrendsCsv().catch((err) => showError(err))
        );
        els.reviewWorkflowClearFiltersBtn.addEventListener("click", () => {
          clearReviewWorkflowFilters();
          Promise.allSettled([
            refreshReviewWorkflow(),
            refreshReviewWorkflowTrends(),
            refreshReviewWorkflowSla(),
            refreshReviewWorkflowSlaTrends(),
            refreshReviewWorkflowSlaHotspots(),
            refreshReviewWorkflowSlaHotspotsTrends(),
            refreshReviewWorkflowSlaProfile(),
            refreshPortfolioReviewWorkflow(),
            refreshPortfolioReviewWorkflowSla(),
            refreshPortfolioReviewWorkflowSlaHotspots(),
            refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
            refreshPortfolioReviewWorkflowTrends(),
            refreshPortfolioReviewWorkflowSlaTrends(),
          ]).catch(showError);
        });
        els.reviewWorkflowExportJsonBtn.addEventListener("click", () =>
          downloadReviewWorkflowJson().catch((err) => showError(err))
        );
        els.reviewWorkflowExportCsvBtn.addEventListener("click", () =>
          downloadReviewWorkflowCsv().catch((err) => showError(err))
        );
        els.addCommentBtn.addEventListener("click", () => addComment().catch(showError));
        els.ackCommentBtn.addEventListener("click", () => setCommentStatus("acknowledged").catch(showError));
        els.resolveCommentBtn.addEventListener("click", () => setCommentStatus("resolved").catch(showError));
        els.reopenCommentBtn.addEventListener("click", () => setCommentStatus("open").catch(showError));
        els.commentAddSelectedCommentBtn.addEventListener("click", () => {
          try {
            const commentId = String(els.selectedCommentId.value || "").trim();
            if (!commentId) throw new Error("No latest comment id selected");
            mergeIdsIntoTextarea(els.commentSelectedCommentIds, [commentId]);
            updateCommentBulkActionUi();
          } catch (err) {
            showError(err);
          }
        });
        els.commentClearSelectedCommentIdsBtn.addEventListener("click", () => {
          els.commentSelectedCommentIds.value = "";
          persistUiState();
          updateCommentBulkActionUi();
        });
        renderBulkPreviewSummary(els.commentBulkSummaryList, null, {
          notFoundKey: "not_found_comment_ids",
          updatedKey: "updated_comments",
          itemLabel: "comments",
          scopeLabel: "-",
          filterBasis: "-",
          statusTransition: "-",
          queueLabel: "-",
        });
        els.commentCopySelectedCommentIdsBtn.addEventListener("click", () =>
          copySelectedCommentIds().catch((err) => showError(err))
        );
        els.commentLoadCommentIdsFromWorkflowBtn.addEventListener("click", () => {
          try {
            loadCommentIdsFromWorkflow();
            updateCommentBulkActionUi();
          } catch (err) {
            showError(err);
          }
        });
        els.commentBulkPreviewBtn.addEventListener("click", () => applyCommentBulkStatus({ dryRun: true }).catch(showError));
        els.commentBulkApplyBtn.addEventListener("click", () => applyCommentBulkStatus().catch(showError));
        els.commentSyncWorkflowFiltersBtn.addEventListener("click", () => {
          try {
            syncCommentFiltersFromWorkflow();
          } catch (err) {
            showError(err);
          }
        });
        [els.commentBulkTargetStatus, els.commentBulkScope, els.commentSelectedCommentIds].forEach((el) => {
          el?.addEventListener("change", updateCommentBulkActionUi);
          el?.addEventListener("input", updateCommentBulkActionUi);
        });
        [els.reviewWorkflowFindingSectionFilter, els.reviewWorkflowCommentStatusFilter].forEach((el) => {
          el?.addEventListener("change", () => {
            updateCriticBulkActionUi();
            updateCommentBulkActionUi();
          });
          el?.addEventListener("input", () => {
            updateCriticBulkActionUi();
            updateCommentBulkActionUi();
          });
        });
        updateCriticBulkActionUi();
        updateCommentBulkActionUi();
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
        els.portfolioToCTextRiskLevelFilter.addEventListener("change", () => {
          applyPortfolioToCTextRiskLevelFilter(els.portfolioToCTextRiskLevelFilter.value);
        });
        els.portfolioMelRiskLevelFilter.addEventListener("change", () => {
          applyPortfolioMelRiskLevelFilter(els.portfolioMelRiskLevelFilter.value);
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
        [
          els.reviewWorkflowEventTypeFilter,
          els.reviewWorkflowCommentStatusFilter,
          els.reviewWorkflowStateFilter,
          els.reviewWorkflowFindingCodeFilter,
          els.reviewWorkflowFindingSectionFilter,
        ].forEach((el) =>
          el.addEventListener("change", () => {
            persistUiState();
            Promise.allSettled([
              refreshReviewWorkflow(),
              refreshReviewWorkflowTrends(),
              refreshReviewWorkflowSla(),
              refreshReviewWorkflowSlaTrends(),
              refreshReviewWorkflowSlaHotspots(),
              refreshReviewWorkflowSlaHotspotsTrends(),
              refreshPortfolioReviewWorkflow(),
              refreshPortfolioReviewWorkflowSla(),
              refreshPortfolioReviewWorkflowSlaHotspots(),
              refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
              refreshPortfolioReviewWorkflowTrends(),
              refreshPortfolioReviewWorkflowSlaTrends(),
            ]).catch(showError);
          })
        );
        [els.reviewWorkflowFindingIdFilter].forEach((el) => el.addEventListener("change", () => {
          persistUiState();
          Promise.allSettled([
            refreshReviewWorkflow(),
            refreshReviewWorkflowTrends(),
            refreshReviewWorkflowSla(),
            refreshReviewWorkflowSlaTrends(),
            refreshReviewWorkflowSlaHotspots(),
            refreshReviewWorkflowSlaHotspotsTrends(),
            refreshPortfolioReviewWorkflow(),
            refreshPortfolioReviewWorkflowSla(),
            refreshPortfolioReviewWorkflowSlaHotspots(),
            refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
            refreshPortfolioReviewWorkflowTrends(),
            refreshPortfolioReviewWorkflowSlaTrends(),
          ]).catch(showError);
        }));
        els.reviewWorkflowOverdueHoursFilter.addEventListener("change", () => {
          persistUiState();
          Promise.allSettled([
            refreshReviewWorkflow(),
            refreshReviewWorkflowTrends(),
            refreshReviewWorkflowSla(),
            refreshReviewWorkflowSlaTrends(),
            refreshReviewWorkflowSlaHotspots(),
            refreshReviewWorkflowSlaHotspotsTrends(),
            refreshPortfolioReviewWorkflow(),
            refreshPortfolioReviewWorkflowSla(),
            refreshPortfolioReviewWorkflowSlaHotspots(),
            refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
            refreshPortfolioReviewWorkflowTrends(),
            refreshPortfolioReviewWorkflowSlaTrends(),
          ]).catch(showError);
        });
        [
          els.reviewWorkflowSlaHotspotKindFilter,
          els.reviewWorkflowSlaHotspotSeverityFilter,
          els.reviewWorkflowSlaMinOverdueHoursFilter,
          els.reviewWorkflowSlaTopLimitFilter,
        ].forEach((el) =>
          el.addEventListener("change", () => {
            persistUiState();
            Promise.allSettled([
              refreshReviewWorkflowSlaHotspots(),
              refreshReviewWorkflowSlaHotspotsTrends(),
            ]).catch(showError);
          })
        );
        [
          els.portfolioSlaHotspotKindFilter,
          els.portfolioSlaHotspotSeverityFilter,
          els.portfolioSlaMinOverdueHoursFilter,
          els.portfolioSlaTopLimitFilter,
        ].forEach((el) =>
          el.addEventListener("change", () => {
            persistUiState();
            Promise.allSettled([
              refreshPortfolioReviewWorkflowSla(),
              refreshPortfolioReviewWorkflowSlaHotspots(),
              refreshPortfolioReviewWorkflowSlaHotspotsTrends(),
            ]).catch(showError);
          })
        );
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
        els.productionExportMode.addEventListener("change", persistUiState);
        els.allowUnsafeExport.addEventListener("change", () => {
          persistUiState();
          renderSendGate(state.lastPortfolioWorkflowPolicy);
        });
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
      loadServerPresetBundle()
        .then((loaded) => {
          if (!loaded) {
            loadAllServerGeneratePresets().catch(() => {});
            loadServerIngestPresets().catch(() => {});
          }
        })
        .catch(() => {
          loadAllServerGeneratePresets().catch(() => {});
          loadServerIngestPresets().catch(() => {});
        });
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
