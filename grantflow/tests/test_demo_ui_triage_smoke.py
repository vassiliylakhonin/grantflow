from grantflow.api.demo_ui import render_demo_ui_html


def test_demo_ui_contains_triage_power_controls_and_telemetry_hooks():
    html = render_demo_ui_html()

    assert 'id="runPrimaryQueueActionBtn"' in html
    assert 'id="undoLastBulkActionBtn"' in html
    assert 'id="reviewWorkflowTelemetryLine"' in html
    assert 'id="resetTriageTelemetryBtn"' in html
    assert 'id="reviewWorkflowKpiLine"' in html
    assert 'id="reviewWorkflowSloLine"' in html
    assert 'id="downloadTriageOpsReportBtn"' in html
    assert 'id="qualityOpenExportPayloadBtn"' in html
    assert 'id="downloadPilotQuickReportBtn"' in html
    assert 'id="exportPayloadCard"' in html
    assert 'Export readiness' in html
    assert 'Export score' in html
    assert 'Export top gap' in html

    # keyboard shortcuts, telemetry persistence, KPI/SLO/report hooks
    assert "function handleTriageShortcut(event)" in html
    assert 'document.addEventListener("keydown"' in html
    assert "grantflow_demo_triage_telemetry" in html
    assert "function computeTriageKpiFromTimeline(timeline)" in html
    assert "function evaluateTriageSlo(snapshot, summary)" in html
    assert "function buildTriageOpsReportText()" in html
