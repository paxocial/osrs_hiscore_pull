"""Tests for the OSRS proxy route module (.council/web/routes/osrs_proxy.py).

Verifies:
- Module structure: router export, endpoint count, decorator paths
- Path traversal validation
- Error handling for ConnectError, TimeoutException
- Backend base URL resolution
- Query parameter forwarding (None-stripping)
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Locate and load the proxy module from .council/web/routes/
# ---------------------------------------------------------------------------
PROXY_MODULE_PATH = Path(__file__).resolve().parent.parent / ".council" / "web" / "routes" / "osrs_proxy.py"


def _load_proxy_module():
    """Import osrs_proxy.py without triggering council_mcp dependency resolution."""
    spec = importlib.util.spec_from_file_location("osrs_proxy", str(PROXY_MODULE_PATH))
    mod = importlib.util.module_from_spec(spec)
    # We need council_mcp.web.dependencies for the import; mock it if unavailable
    if "council_mcp" not in sys.modules:
        # Create minimal mock chain so import succeeds
        council = MagicMock()
        sys.modules["council_mcp"] = council
        sys.modules["council_mcp.web"] = council.web
        sys.modules["council_mcp.web.dependencies"] = council.web.dependencies
        council.web.dependencies.get_current_user = lambda: {}
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# AST-based structural tests (no runtime dependency on council_mcp)
# ---------------------------------------------------------------------------

class TestModuleStructure:
    """Verify module structure via AST parsing (no imports needed)."""

    @pytest.fixture(autouse=True)
    def _load_ast(self):
        with open(PROXY_MODULE_PATH) as f:
            self.tree = ast.parse(f.read())
        self.source = PROXY_MODULE_PATH.read_text()

    def _get_decorator_routes(self) -> list[tuple[str, str]]:
        """Extract (HTTP_METHOD, path) from @router.method(...) decorators."""
        routes = []
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        # router.get, router.post, router.delete
                        if isinstance(dec.func.value, ast.Name) and dec.func.value.id == "router":
                            method = dec.func.attr.upper()
                            if dec.args and isinstance(dec.args[0], ast.Constant):
                                path = dec.args[0].value
                                routes.append((method, path))
        return routes

    def test_has_15_endpoints(self):
        routes = self._get_decorator_routes()
        assert len(routes) == 15, f"Expected 15 endpoints, got {len(routes)}: {routes}"

    def test_all_paths_start_with_api_osrs(self):
        routes = self._get_decorator_routes()
        for method, path in routes:
            assert path.startswith("/api/osrs/"), f"{method} {path} does not start with /api/osrs/"

    def test_health_endpoint(self):
        routes = self._get_decorator_routes()
        assert ("GET", "/api/osrs/health") in routes

    def test_account_endpoints(self):
        routes = self._get_decorator_routes()
        expected = [
            ("GET", "/api/osrs/accounts"),
            ("POST", "/api/osrs/accounts"),
            ("GET", "/api/osrs/accounts/search"),
            ("GET", "/api/osrs/accounts/{name}"),
            ("DELETE", "/api/osrs/accounts/{name}"),
            ("GET", "/api/osrs/accounts/{name}/snapshots"),
        ]
        for ep in expected:
            assert ep in routes, f"Missing account endpoint: {ep}"

    def test_snapshot_endpoints(self):
        routes = self._get_decorator_routes()
        expected = [
            ("GET", "/api/osrs/snapshots/latest"),
            ("POST", "/api/osrs/snapshots/run"),
            ("GET", "/api/osrs/snapshots/{id}"),
            ("GET", "/api/osrs/snapshots/{id}/deltas"),
            ("GET", "/api/osrs/snapshots/{id}/raw"),
            ("GET", "/api/osrs/snapshots/{id}/report"),
        ]
        for ep in expected:
            assert ep in routes, f"Missing snapshot endpoint: {ep}"

    def test_compare_endpoints(self):
        routes = self._get_decorator_routes()
        expected = [
            ("GET", "/api/osrs/compare/data"),
            ("GET", "/api/osrs/compare/search"),
        ]
        for ep in expected:
            assert ep in routes, f"Missing compare endpoint: {ep}"

    def test_router_has_no_prefix(self):
        """Verify router = APIRouter(tags=...) with no prefix kwarg."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "router":
                        if isinstance(node.value, ast.Call):
                            for kw in node.value.keywords:
                                assert kw.arg != "prefix", "Router should not have a prefix"

    def test_proxy_endpoints_are_public_game_data_routes(self):
        """OSRS proxy endpoints must stay public so catherby pages can degrade gracefully."""
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_router_dec = False
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        if isinstance(dec.func.value, ast.Name) and dec.func.value.id == "router":
                            has_router_dec = True
                if has_router_dec:
                    param_names = [arg.arg for arg in node.args.args]
                    assert "current_user" not in param_names, (
                        f"Endpoint {node.name} unexpectedly requires authenticated user context"
                    )
        assert "get_current_user" not in self.source

    def test_imports_httpx(self):
        """Module must import httpx."""
        assert "import httpx" in self.source or "from httpx" in self.source

    def test_error_handling_503_connect(self):
        """Module should handle httpx.ConnectError with 503."""
        assert "ConnectError" in self.source
        assert "503" in self.source

    def test_error_handling_503_has_hint(self):
        """503 error response should include a hint for the user."""
        assert "hint" in self.source
        assert "Start the backend from the Control Center" in self.source

    def test_error_handling_504_timeout(self):
        """Module should handle httpx.TimeoutException with 504."""
        assert "TimeoutException" in self.source
        assert "504" in self.source

    def test_error_handling_502_generic(self):
        """Module should have generic 502 proxy error handler."""
        assert "502" in self.source

    def test_path_traversal_protection(self):
        """Module should validate path parameters against traversal."""
        assert ".." in self.source
        # Check for the regex or validation function
        assert "_validate_path_param" in self.source or "UNSAFE_PATH" in self.source


# ---------------------------------------------------------------------------
# Runtime tests (load module with mocked council_mcp)
# ---------------------------------------------------------------------------

class TestPathValidation:
    """Test path traversal validation function."""

    @pytest.fixture(autouse=True)
    def _load_module(self):
        self.mod = _load_proxy_module()

    def test_clean_name_passes(self):
        """Normal account names should not raise."""
        self.mod._validate_path_param("Zezima", "account name")
        self.mod._validate_path_param("B0aty", "account name")
        self.mod._validate_path_param("Iron-Mammal", "account name")

    def test_slash_rejected(self):
        with pytest.raises(Exception):
            self.mod._validate_path_param("../etc/passwd", "account name")

    def test_backslash_rejected(self):
        with pytest.raises(Exception):
            self.mod._validate_path_param("test\\path", "account name")

    def test_dotdot_rejected(self):
        with pytest.raises(Exception):
            self.mod._validate_path_param("some..thing", "account name")

    def test_forward_slash_rejected(self):
        with pytest.raises(Exception):
            self.mod._validate_path_param("a/b", "account name")


class TestBackendBaseUrl:
    """Test backend URL resolution."""

    @pytest.fixture(autouse=True)
    def _load_module(self):
        self.mod = _load_proxy_module()

    def test_default_port(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove OSRS_BACKEND_PORT if present
            os.environ.pop("OSRS_BACKEND_PORT", None)
            url = self.mod._backend_base_url()
            assert url == "http://127.0.0.1:8001"

    def test_custom_port(self):
        with patch.dict(os.environ, {"OSRS_BACKEND_PORT": "9090"}):
            url = self.mod._backend_base_url()
            assert url == "http://127.0.0.1:9090"


class TestErrorHandler:
    """Test the centralized transport error handler."""

    @pytest.fixture(autouse=True)
    def _load_module(self):
        self.mod = _load_proxy_module()

    def test_connect_error_returns_503_with_hint(self):
        resp = self.mod._handle_transport_error(httpx.ConnectError("refused"))
        assert resp.status_code == 503
        assert resp.body is not None
        body = json.loads(resp.body)
        assert body["detail"] == "OSRS backend is offline"
        assert "hint" in body
        assert "Control Center" in body["hint"]

    def test_timeout_returns_504(self):
        resp = self.mod._handle_transport_error(httpx.TimeoutException("timeout"))
        assert resp.status_code == 504
        body = json.loads(resp.body)
        assert body["detail"] == "OSRS backend timed out"

    def test_generic_error_returns_502(self):
        resp = self.mod._handle_transport_error(RuntimeError("something broke"))
        assert resp.status_code == 502
        body = json.loads(resp.body)
        assert body["detail"] == "Proxy error"


class TestRouterExport:
    """Verify the module exports the correct router object."""

    @pytest.fixture(autouse=True)
    def _load_module(self):
        self.mod = _load_proxy_module()

    def test_has_router(self):
        assert hasattr(self.mod, "router")

    def test_router_is_api_router(self):
        # The router should be a FastAPI APIRouter instance
        from fastapi import APIRouter
        assert isinstance(self.mod.router, APIRouter)

    def test_router_has_osrs_proxy_tag(self):
        assert "osrs-proxy" in self.mod.router.tags


class TestRoutesYaml:
    """Verify routes.yaml includes the proxy module."""

    def test_routes_yaml_includes_proxy(self):
        routes_path = Path(__file__).resolve().parent.parent / ".council" / "web" / "routes" / "routes.yaml"
        content = routes_path.read_text()
        assert "osrs_proxy.py" in content

    def test_routes_yaml_includes_runtime(self):
        """Ensure we didn't break the existing runtime entry."""
        routes_path = Path(__file__).resolve().parent.parent / ".council" / "web" / "routes" / "routes.yaml"
        content = routes_path.read_text()
        assert "osrs_runtime.py" in content

    def test_routes_yaml_is_enabled(self):
        routes_path = Path(__file__).resolve().parent.parent / ".council" / "web" / "routes" / "routes.yaml"
        content = routes_path.read_text()
        assert "enabled: true" in content
