from grantflow.api.demo_ui import render_demo_ui_html


def test_demo_ui_contains_triage_power_controls_and_telemetry_hooks():
    html = render_demo_ui_html()

    assert 'id="runPrimaryQueueActionBtn"' in html
    assert 'id="undoLastBulkActionBtn"' in html
    assert 'id="reviewWorkflowTelemetryLine"' in html
    assert 'id="resetTriageTelemetryBtn"' in html

    # keyboard shortcuts and telemetry persistence hooks
    assert "function handleTriageShortcut(event)" in html
    assert 'document.addEventListener("keydown"' in html
    assert "grantflow_demo_triage_telemetry" in html
