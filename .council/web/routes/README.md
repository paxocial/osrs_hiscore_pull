# Custom Routes

Place downstream route modules here as `*.py` files.
Council loads these modules at web startup when `custom_routes_enabled` is true.

## Supported Module Contracts

1. Export `router` (FastAPI `APIRouter`)
2. Or export `register(app, council_name=None, repo_path=None)` for advanced setup

Optional:
- `ROUTE_PREFIX = "/api/my-service"` to mount router under a prefix

## Example

```python
from fastapi import APIRouter, Depends, Request
from council_mcp.web.dependencies import get_current_user

router = APIRouter(tags=["my-service-runtime"])

@router.get("/api/my-service/runtime/ping")
async def ping(request: Request, current_user: dict = Depends(get_current_user)):
    del request, current_user
    return {"ok": True}
```

## Optional Manifest (`routes.yaml`)

```yaml
enabled: true
routes:
  - module: my_service_runtime.py
    prefix: ""
```

If `routes.yaml` is absent, all `*.py` modules (except `_*.py`) are auto-discovered.

## Runtime Process Management (ProcessManager)

For service runtime routes, use `ProcessManager` (`ProcessType.PLUGIN`) and include
`metadata.service` + `metadata.repo_path` in `ProcessConfig` so status/stop actions
can resolve the right process for the active council.
