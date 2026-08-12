from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from .. import reports

router = APIRouter()


@router.get("/api/reports/json")
def report_json():
    return reports.build_report()


@router.get("/api/reports/markdown", response_class=PlainTextResponse)
def report_markdown():
    return reports.render_markdown(reports.build_report())


@router.get("/api/reports/html", response_class=HTMLResponse)
def report_html():
    return reports.render_html(reports.build_report())
