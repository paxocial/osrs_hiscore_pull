from __future__ import annotations

import importlib

from fastapi.testclient import TestClient


def _load_public_mode_apps(monkeypatch):
    monkeypatch.setenv("CATHERBY_PUBLIC_HOST_MODE", "true")
    import api.main as api_main_module
    import web.main as web_main_module

    api_main_module = importlib.reload(api_main_module)
    web_main_module = importlib.reload(web_main_module)
    return api_main_module.app, web_main_module.app


def test_api_public_mode_hides_private_and_legacy_routes(monkeypatch) -> None:
    api_app, _ = _load_public_mode_apps(monkeypatch)
    client = TestClient(api_app)

    denied_paths = (
        "/docs",
        "/redoc",
        "/openapi.json",
        "/test/accounts",
        "/accounts",
        "/snapshots",
        "/analytics",
        "/api/v1/plugin/status",
    )
    for path in denied_paths:
        response = client.get(path)
        assert response.status_code == 404

    ledger_status = client.get("/api/v1/ledger/osrs/status")
    assert ledger_status.status_code in (401, 403)


def test_web_public_mode_blocks_private_surfaces_and_keeps_ledger_auth(monkeypatch) -> None:
    _, web_app = _load_public_mode_apps(monkeypatch)
    client = TestClient(web_app)

    denied_paths = (
        "/api/docs",
        "/api/openapi.json",
        "/api/test/accounts",
        "/api/accounts",
        "/api/snapshots",
        "/api/analytics",
        "/api/api/v1/plugin/status",
        "/admin",
        "/jobs/status",
        "/operator",
        "/runtime",
        "/council",
    )
    for path in denied_paths:
        response = client.get(path)
        assert response.status_code == 404

    ledger_status = client.get("/api/api/v1/ledger/osrs/status")
    assert ledger_status.status_code in (401, 403)
