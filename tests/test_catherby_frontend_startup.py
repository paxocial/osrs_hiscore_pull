from __future__ import annotations

import ast
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from web.routes.auth import router as auth_router
from web.routes.compare import router as compare_router
from web.routes.pages import router as pages_router


def create_public_page_test_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key")
    app.include_router(pages_router)
    app.include_router(auth_router)
    app.include_router(compare_router)
    return TestClient(app)


def test_catherby_homepage_renders_with_current_template_response_signature() -> None:
    response = create_public_page_test_client().get("/")

    assert response.status_code == 200
    assert "Catherby" in response.text


def test_catherby_public_pages_render_without_template_response_crash() -> None:
    client = create_public_page_test_client()

    for path in ("/auth/login", "/auth/register", "/compare"):
        response = client.get(path)

        assert response.status_code == 200
        assert "unhashable type" not in response.text


def test_catherby_route_templates_pass_request_to_template_response() -> None:
    route_dir = Path(__file__).resolve().parents[1] / "web" / "routes"

    offenders: list[str] = []
    for route_file in route_dir.glob("*.py"):
        tree = ast.parse(route_file.read_text(encoding="utf-8"), filename=str(route_file))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if not (
                isinstance(function, ast.Attribute)
                and function.attr == "TemplateResponse"
                and isinstance(function.value, ast.Name)
                and function.value.id == "templates"
            ):
                continue
            if not node.args or not (isinstance(node.args[0], ast.Name) and node.args[0].id == "request"):
                offenders.append(f"{route_file.name}:{node.lineno}")

    assert offenders == []
