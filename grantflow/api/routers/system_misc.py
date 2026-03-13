from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from grantflow.api.demo_ui import render_demo_ui_html
from grantflow.core.strategies.factory import DonorFactory

router = APIRouter(tags=["system"])


@router.get("/donors")
def list_donors():
    return {"donors": DonorFactory.list_supported()}


@router.get("/demo", response_class=HTMLResponse, include_in_schema=False)
def demo_console():
    return HTMLResponse(render_demo_ui_html())
