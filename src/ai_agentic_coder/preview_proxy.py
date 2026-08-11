"""Proxy the generated demo app through the main Gradio Space."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import Request, Response
from starlette.responses import RedirectResponse


PREVIEW_PATH = os.getenv("AI_AGENTIC_CODER_PREVIEW_PATH", "/generated-app").rstrip("/") or "/generated-app"
DEFAULT_PREVIEW_PORT = int(os.getenv("AI_AGENTIC_CODER_PREVIEW_PORT", "8765"))
PREVIEW_PORT_FILE = "generated_preview_port.txt"
PREVIEW_API_PREFIXES = (
    "/gradio_api",
    "/queue",
    "/call",
    "/reset",
    "/heartbeat",
    "/component_server",
)


def _preview_port() -> int:
    port_file = Path(__file__).resolve().parent / "output" / PREVIEW_PORT_FILE
    try:
        return int(port_file.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, OSError, ValueError):
        return DEFAULT_PREVIEW_PORT


def _is_generated_app_request(request: Request) -> bool:
    referrer = request.headers.get("referer", "")
    return f"{PREVIEW_PATH}/" in referrer or referrer.rstrip("/").endswith(PREVIEW_PATH)


def _is_generated_app_api_request(request: Request) -> bool:
    return request.url.path.startswith(PREVIEW_API_PREFIXES) and _is_generated_app_request(request)


async def _proxy_to_preview(request: Request, target_path: str) -> Response:
    preview_port = _preview_port()
    target_path = target_path.lstrip("/")
    target = f"http://127.0.0.1:{preview_port}/{target_path}"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }

    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=300.0) as client:
            upstream = await client.request(
                request.method,
                target,
                headers=headers,
                content=await request.body(),
            )
    except httpx.RequestError:
        return Response(
            "The generated preview app is not running yet, or it has expired.",
            status_code=503,
            media_type="text/plain",
        )

    excluded_headers = {
        "connection",
        "content-encoding",
        "content-length",
        "transfer-encoding",
    }
    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in excluded_headers
    }

    location = response_headers.get("location")
    if location and location.startswith(f"http://127.0.0.1:{preview_port}/"):
        response_headers["location"] = location.replace(
            f"http://127.0.0.1:{preview_port}",
            PREVIEW_PATH,
            1,
        )

    return Response(
        upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


def register_preview_proxy(app) -> None:
    if getattr(app.state, "ai_agentic_coder_preview_proxy_registered", False):
        return
    app.state.ai_agentic_coder_preview_proxy_registered = True

    @app.middleware("http")
    async def generated_app_api_proxy(request: Request, call_next):
        if _is_generated_app_api_request(request):
            return await _proxy_to_preview(request, request.url.path)
        return await call_next(request)

    async def preview_root() -> RedirectResponse:
        return RedirectResponse(f"{PREVIEW_PATH}/")

    async def proxy(request: Request, path: str = "") -> Response:
        return await _proxy_to_preview(request, path)

    methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
    app.add_api_route(PREVIEW_PATH, preview_root, methods=["GET"], include_in_schema=False)
    app.add_api_route(f"{PREVIEW_PATH}/{{path:path}}", proxy, methods=methods, include_in_schema=False)


def install_preview_proxy() -> None:
    """Ensure every Gradio-created FastAPI app includes the preview proxy."""
    from gradio.routes import App

    create_app = App.create_app
    if getattr(create_app, "_ai_agentic_coder_preview_proxy", False):
        return

    def create_app_with_preview_proxy(*args, **kwargs):
        app = create_app(*args, **kwargs)
        register_preview_proxy(app)
        return app

    create_app_with_preview_proxy._ai_agentic_coder_preview_proxy = True
    App.create_app = staticmethod(create_app_with_preview_proxy)
