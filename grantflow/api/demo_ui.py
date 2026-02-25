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
    .kpis { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .kpi {
      border: 1px solid var(--line); border-radius: 12px; background: rgba(255,255,255,.8); padding: 10px;
    }
    .kpi .label { color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }
    .kpi .value { font-family: var(--mono); font-size: 1rem; }
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
            <div class="row3" style="margin-top:10px;">
              <div><label for="llmMode">LLM Mode</label><select id="llmMode"><option value="false">false</option><option value="true">true</option></select></div>
              <div><label for="webhookUrl">Webhook URL (optional)</label><input id="webhookUrl" placeholder="https://example.com/webhook" /></div>
              <div><label for="webhookSecret">Webhook Secret (optional)</label><input id="webhookSecret" placeholder="secret" /></div>
            </div>
            <div style="margin-top:10px;">
              <button id="generateBtn" class="primary">Generate Draft</button>
            </div>
            <div class="footer-note">Tip: when auth is enabled on the API, set <code>X-API-Key</code> above once and all actions will use it.</div>
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
          <h2>Portfolio Metrics</h2>
          <div class="body">
            <div class="row3">
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
            <div style="margin-top:10px;">
              <pre id="portfolioMetricsJson">{}</pre>
            </div>
          </div>
        </div>

        <div class="card">
          <h2>Critic Findings</h2>
          <div class="body">
            <div class="row3">
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
                <label for="criticCitationConfidenceFilter">Citation Confidence</label>
                <select id="criticCitationConfidenceFilter">
                  <option value="">all</option>
                  <option value="low">low (&lt; 0.30)</option>
                  <option value="high">high (&ge; 0.70)</option>
                </select>
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
            <div class="row3" style="margin-top:10px;">
              <button id="commentsBtn" class="ghost">Load Comments</button>
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
        ["criticCitationConfidenceFilter", "grantflow_demo_critic_confidence"],
        ["portfolioDonorFilter", "grantflow_demo_portfolio_donor"],
        ["portfolioStatusFilter", "grantflow_demo_portfolio_status"],
        ["portfolioHitlFilter", "grantflow_demo_portfolio_hitl"],
        ["commentsFilterSection", "grantflow_demo_comments_filter_section"],
        ["commentsFilterStatus", "grantflow_demo_comments_filter_status"],
        ["commentsFilterVersionId", "grantflow_demo_comments_filter_version_id"],
        ["selectedCommentId", "grantflow_demo_selected_comment_id"],
        ["linkedFindingId", "grantflow_demo_linked_finding_id"],
      ];
      const state = {
        pollTimer: null,
        polling: false,
        lastCritic: null,
        lastCitations: null,
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
        webhookUrl: $("webhookUrl"),
        webhookSecret: $("webhookSecret"),
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
        portfolioMetricsJson: $("portfolioMetricsJson"),
        criticJson: $("criticJson"),
        exportPayloadJson: $("exportPayloadJson"),
        diffPre: $("diffPre"),
        versionsList: $("versionsList"),
        citationsList: $("citationsList"),
        eventsList: $("eventsList"),
        criticFlawsList: $("criticFlawsList"),
        criticChecksList: $("criticChecksList"),
        criticContextList: $("criticContextList"),
        commentsList: $("commentsList"),
        metricsCards: $("metricsCards"),
        portfolioMetricsCards: $("portfolioMetricsCards"),
        portfolioStatusCountsList: $("portfolioStatusCountsList"),
        portfolioDonorCountsList: $("portfolioDonorCountsList"),
        criticSectionFilter: $("criticSectionFilter"),
        criticSeverityFilter: $("criticSeverityFilter"),
        criticCitationConfidenceFilter: $("criticCitationConfidenceFilter"),
        portfolioDonorFilter: $("portfolioDonorFilter"),
        portfolioStatusFilter: $("portfolioStatusFilter"),
        portfolioHitlFilter: $("portfolioHitlFilter"),
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
        portfolioBtn: $("portfolioBtn"),
        portfolioClearBtn: $("portfolioClearBtn"),
        commentsBtn: $("commentsBtn"),
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
        restoreUiState();
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
        persistUiState();
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
        await Promise.allSettled([refreshPortfolioMetrics(), refreshComments(), refreshDiff()]);
      }

      function clearLinkedFindingSelection() {
        els.linkedFindingId.value = "";
        persistUiState();
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

      function renderCitations(list) {
        els.citationsList.innerHTML = "";
        if (!Array.isArray(list) || list.length === 0) {
          els.citationsList.innerHTML = `<div class="item"><div class="sub">No citations found.</div></div>`;
          return;
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
          div.innerHTML = `
            <div class="title mono">${escapeHtml(label)}</div>
            <div class="sub">${escapeHtml(meta || "trace")}${confidence ? ` · ${escapeHtml(confidence)}` : ""}${pageChunk ? ` · ${escapeHtml(pageChunk)}` : ""}</div>
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
          const meta = [c.ts, c.author, c.version_id, c.linked_finding_id ? `finding ${String(c.linked_finding_id).slice(0, 8)}` : null].filter(Boolean).join(" · ");
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

      function renderCriticLists(body) {
        const section = (els.criticSectionFilter.value || "").trim();
        const severity = (els.criticSeverityFilter.value || "").trim();
        const flaws = Array.isArray(body?.fatal_flaws) ? body.fatal_flaws : [];
        const checks = Array.isArray(body?.rule_checks) ? body.rule_checks : [];
        const filteredFlaws = flaws.filter((f) => {
          if (section && String(f.section || "") !== section) return false;
          if (severity && String(f.severity || "") !== severity) return false;
          return true;
        });
        const filteredChecks = section ? checks.filter((c) => String(c.section || "") === section) : checks;

        els.criticFlawsList.innerHTML = "";
        if (filteredFlaws.length === 0) {
          els.criticFlawsList.innerHTML = `<div class="item"><div class="sub">No fatal flaws${section ? ` for ${escapeHtml(section)}` : ""}.</div></div>`;
        } else {
          for (const flaw of filteredFlaws) {
            const div = document.createElement("div");
            const flawSeverity = String(flaw.severity || "").toLowerCase();
            div.className = `item${flawSeverity ? ` severity-${flawSeverity}` : ""}`;
            const titleBits = [flaw.status || "open", flaw.severity || "severity", flaw.section || "section", flaw.code || "FLAW"];
            const meta = [flaw.version_id, flaw.source].filter(Boolean).join(" · ");
            const linkedComments = Array.isArray(flaw.linked_comment_ids) ? flaw.linked_comment_ids : [];
            div.innerHTML = `
              <div class="title mono">${escapeHtml(titleBits.join(" · "))}</div>
              <div class="sub">${escapeHtml(flaw.message || "")}</div>
              ${flaw.fix_hint ? `<div class="sub" style="margin-top:6px;">Fix: ${escapeHtml(flaw.fix_hint)}</div>` : ""}
              ${meta ? `<div class="sub" style="margin-top:6px;">${escapeHtml(meta)}</div>` : ""}
              ${flaw.finding_id ? `<div class="sub" style="margin-top:6px;">finding_id: ${escapeHtml(String(flaw.finding_id).slice(0, 12))}${linkedComments.length ? ` · linked comments: ${escapeHtml(String(linkedComments.length))}` : ""}</div>` : ""}
            `;
            const actionsRow = document.createElement("div");
            actionsRow.style.marginTop = "8px";
            actionsRow.style.display = "flex";
            actionsRow.style.gap = "8px";
            actionsRow.style.flexWrap = "wrap";

            if (flaw.finding_id && flaw.status !== "acknowledged" && flaw.status !== "resolved") {
              const ackBtn = document.createElement("button");
              ackBtn.className = "ghost";
              ackBtn.textContent = "Acknowledge";
              ackBtn.addEventListener("click", (event) => {
                event.stopPropagation();
                setFindingStatus(flaw.finding_id, "acknowledged").catch(showError);
              });
              actionsRow.appendChild(ackBtn);
            }
            if (flaw.finding_id && flaw.status !== "resolved") {
              const resolveBtn = document.createElement("button");
              resolveBtn.className = "ghost";
              resolveBtn.textContent = "Resolve Finding";
              resolveBtn.addEventListener("click", (event) => {
                event.stopPropagation();
                setFindingStatus(flaw.finding_id, "resolved").catch(showError);
              });
              actionsRow.appendChild(resolveBtn);
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
          div.innerHTML = `
            <div class="title mono">${escapeHtml(label)}</div>
            <div class="sub">${escapeHtml(meta || "trace")}${confidence ? ` · ${escapeHtml(confidence)}` : ""}</div>
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
        els.linkedFindingId.value = String(flaw?.finding_id || "").trim();
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

      async function generateJob() {
        const payload = {
          donor_id: els.donorId.value.trim(),
          input_context: {
            project: els.project.value.trim(),
            country: els.country.value.trim(),
          },
          llm_mode: els.llmMode.value === "true",
          hitl_enabled: els.hitlEnabled.value === "true",
        };
        if (els.webhookUrl.value.trim()) payload.webhook_url = els.webhookUrl.value.trim();
        if (els.webhookSecret.value.trim()) payload.webhook_secret = els.webhookSecret.value.trim();

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
        const section = els.diffSection.value;
        const q = section ? `?section=${encodeURIComponent(section)}` : "";
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/versions${q}`);
        renderVersions(body.versions || []);
        return body;
      }

      async function refreshDiff() {
        const jobId = currentJobId();
        if (!jobId) return;
        persistUiState();
        const params = new URLSearchParams();
        if (els.diffSection.value) params.set("section", els.diffSection.value);
        if (els.fromVersionId.value.trim()) params.set("from_version_id", els.fromVersionId.value.trim());
        if (els.toVersionId.value.trim()) params.set("to_version_id", els.toVersionId.value.trim());
        const q = params.toString() ? `?${params.toString()}` : "";
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
        const params = new URLSearchParams();
        if (els.commentsFilterSection.value) params.set("section", els.commentsFilterSection.value);
        if (els.commentsFilterStatus.value) params.set("status", els.commentsFilterStatus.value);
        if (els.commentsFilterVersionId.value.trim()) params.set("version_id", els.commentsFilterVersionId.value.trim());
        const q = params.toString() ? `?${params.toString()}` : "";
        const body = await apiFetch(`/status/${encodeURIComponent(jobId)}/comments${q}`);
        renderComments(body.comments || []);
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

      async function refreshPortfolioMetrics() {
        persistUiState();
        const params = new URLSearchParams();
        if (els.portfolioDonorFilter.value.trim()) params.set("donor_id", els.portfolioDonorFilter.value.trim());
        if (els.portfolioStatusFilter.value) params.set("status", els.portfolioStatusFilter.value);
        if (els.portfolioHitlFilter.value) params.set("hitl_enabled", els.portfolioHitlFilter.value);
        const q = params.toString() ? `?${params.toString()}` : "";
        const body = await apiFetch(`/portfolio/metrics${q}`);
        renderPortfolioMetricsCards(body);
        renderKeyValueList(
          els.portfolioStatusCountsList,
          body.status_counts,
          "No status counts yet.",
          8,
          (statusKey) => {
            els.portfolioStatusFilter.value = statusKey || "";
            persistUiState();
            refreshPortfolioMetrics().catch(showError);
          }
        );
        renderKeyValueList(
          els.portfolioDonorCountsList,
          body.donor_counts,
          "No donor counts yet.",
          8,
          (donorKey) => {
            els.portfolioDonorFilter.value = donorKey || "";
            persistUiState();
            refreshPortfolioMetrics().catch(showError);
          }
        );
        setJson(els.portfolioMetricsJson, body);
        return body;
      }

      async function refreshAll() {
        const jobId = currentJobId();
        if (!jobId) {
          throw new Error("Set or generate a job_id first");
        }
        await refreshStatus();
        await Promise.allSettled([
          refreshMetrics(),
          refreshPortfolioMetrics(),
          refreshCritic(),
          refreshCitations(),
          refreshExportPayload(),
          refreshVersions(),
          refreshDiff(),
          refreshEvents(),
          refreshComments(),
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
        await refreshComments();
        return created;
      }

      async function setFindingStatus(findingId, nextStatus) {
        const jobId = currentJobId();
        if (!jobId) throw new Error("No job_id");
        if (!findingId) throw new Error("No finding_id");
        const action = nextStatus === "acknowledged" ? "ack" : "resolve";
        const updated = await apiFetch(
          `/status/${encodeURIComponent(jobId)}/critic/findings/${encodeURIComponent(findingId)}/${action}`,
          { method: "POST" }
        );
        await refreshCritic();
        return updated;
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
        await refreshComments();
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
        els.refreshAllBtn.addEventListener("click", () => refreshAll().catch(showError));
        els.pollToggleBtn.addEventListener("click", togglePolling);
        els.clearFiltersBtn.addEventListener("click", () => clearDemoFilters().catch(showError));
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
        els.portfolioBtn.addEventListener("click", () => refreshPortfolioMetrics().catch(showError));
        els.portfolioClearBtn.addEventListener("click", () => {
          clearPortfolioFilters();
          refreshPortfolioMetrics().catch(showError);
        });
        els.commentsBtn.addEventListener("click", () => refreshComments().catch(showError));
        els.addCommentBtn.addEventListener("click", () => addComment().catch(showError));
        els.resolveCommentBtn.addEventListener("click", () => setCommentStatus("resolved").catch(showError));
        els.reopenCommentBtn.addEventListener("click", () => setCommentStatus("open").catch(showError));
        els.clearLinkedFindingBtn.addEventListener("click", clearLinkedFindingSelection);
        els.openPendingBtn.addEventListener("click", () => loadPendingList().catch(showError));
        [els.apiBase, els.apiKey, els.jobIdInput].forEach((el) => el.addEventListener("change", persistBasics));
        [els.diffSection, els.fromVersionId, els.toVersionId].forEach((el) => el.addEventListener("change", persistUiState));
        [els.portfolioStatusFilter, els.portfolioHitlFilter].forEach((el) =>
          el.addEventListener("change", () => {
            persistUiState();
            refreshPortfolioMetrics().catch(showError);
          })
        );
        els.portfolioDonorFilter.addEventListener("change", () => {
          persistUiState();
          refreshPortfolioMetrics().catch(showError);
        });
        [els.commentsFilterSection, els.commentsFilterStatus].forEach((el) =>
          el.addEventListener("change", () => {
            persistUiState();
            refreshComments().catch(showError);
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
        els.criticCitationConfidenceFilter.addEventListener("change", () => {
          persistUiState();
          renderCriticContextCitations();
        });
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
