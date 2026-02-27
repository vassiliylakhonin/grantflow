from __future__ import annotations

import grantflow.swarm.graph as graph_module


def _stub_discovery(state: dict) -> dict:
    trail = list(state.get("_trail") or [])
    trail.append("discovery")
    state["_trail"] = trail
    return state


def _stub_architect(state: dict) -> dict:
    trail = list(state.get("_trail") or [])
    trail.append("architect")
    state["_trail"] = trail
    state.setdefault("toc_draft", {"toc": {"brief": "stub"}})
    return state


def _stub_mel(state: dict) -> dict:
    trail = list(state.get("_trail") or [])
    trail.append("mel")
    state["_trail"] = trail
    state.setdefault("logframe_draft", {"indicators": []})
    return state


def _stub_critic(state: dict) -> dict:
    trail = list(state.get("_trail") or [])
    trail.append("critic")
    state["_trail"] = trail
    state["needs_revision"] = bool(state.get("_critic_needs_revision", False))
    return state


def _patched_graph(monkeypatch):
    monkeypatch.setattr(graph_module, "validate_input_richness", _stub_discovery)
    monkeypatch.setattr(graph_module, "draft_toc", _stub_architect)
    monkeypatch.setattr(graph_module, "mel_assign_indicators", _stub_mel)
    monkeypatch.setattr(graph_module, "red_team_critic", _stub_critic)
    return graph_module.build_graph()


def test_graph_hitl_start_pauses_after_toc_gate(monkeypatch):
    graph = _patched_graph(monkeypatch)
    out = graph.invoke({"_start_at": "start", "hitl_enabled": True})
    assert out["hitl_pending"] is True
    assert out["hitl_checkpoint_stage"] == "toc"
    assert out["hitl_resume_from"] == "mel"
    assert out["_trail"] == ["discovery", "architect"]


def test_graph_hitl_resume_mel_pauses_after_logframe_gate(monkeypatch):
    graph = _patched_graph(monkeypatch)
    out = graph.invoke({"_start_at": "mel", "hitl_enabled": True})
    assert out["hitl_pending"] is True
    assert out["hitl_checkpoint_stage"] == "logframe"
    assert out["hitl_resume_from"] == "critic"
    assert out["_trail"] == ["mel"]


def test_graph_hitl_resume_critic_routes_revision_to_new_toc_pause(monkeypatch):
    graph = _patched_graph(monkeypatch)
    out = graph.invoke({"_start_at": "critic", "hitl_enabled": True, "_critic_needs_revision": True})
    assert out["hitl_pending"] is True
    assert out["hitl_checkpoint_stage"] == "toc"
    assert out["hitl_resume_from"] == "mel"
    assert out["_trail"] == ["critic", "architect"]


def test_graph_non_hitl_runs_full_pipeline_without_pause(monkeypatch):
    graph = _patched_graph(monkeypatch)
    out = graph.invoke({"_start_at": "start", "hitl_enabled": False})
    assert out.get("hitl_pending") is False
    assert "hitl_checkpoint_stage" not in out
    assert out["_trail"] == ["discovery", "architect", "mel", "critic"]
