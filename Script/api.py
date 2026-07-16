import os
import csv
import html
import sqlite3
import subprocess
import sys
import time
import re
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
import xlsxwriter

from db import get_conn
from system_MR_core import normalize_checknum, rebuild_edi_matchresults_core
from system_calendar_core import advance_current_work_day
from process_EFT_upload_part1 import load_selected_eft_report, preview_selected_eft_report
from process_EFT_upload_part4 import confirm_eft_import, prepare_eft_vetting
from process_Lockbox_upload_part1 import load_selected_lockbox_report, preview_selected_lockbox_report
from process_Lockbox_upload_part2 import stage_lockboxload_rows
from process_Lockbox_upload_part3 import prepare_lockbox_vetting
from process_Lockbox_upload_part4 import confirm_lockbox_import
from process_EDI_upload_part1 import load_selected_edi_archives, preview_selected_edi_archives
from process_EDI_upload_part2 import list_queued_trn_files, load_trn_queue_to_ediload
from process_EDI_upload_part3 import stage_ediload_rows
from process_EDI_upload_part4 import confirm_edi_import, prepare_edi_vetting, reset_edi_work_tables
from system_paths import DB_EXPORTS_FOLDER, FRONTEND_ROOT, SITES_FOLDER, WORKFLOW_ROOT
from site_snapshotgenerator import process_folder_pdfs

app = FastAPI()
FRONTEND_DIST = os.path.join(FRONTEND_ROOT, "dist")
FRONTEND_ASSETS = os.path.join(FRONTEND_DIST, "assets")
SCRIPT_EXTENSIONS = (".py", ".ts", ".tsx")
ROUTE_RE = re.compile(r"""["'`](\/[A-Za-z0-9_\-\/?=&.%]+)["'`]""")
BUTTON_BLOCK_RE = re.compile(r"<button\b[^>]*>(.*?)</button>", re.IGNORECASE | re.DOTALL)
USE_EFFECT_BLOCK_RE = re.compile(r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{(.*?)\}\s*,\s*\[\s*\]\s*\)", re.DOTALL)
NAVIGATE_RE = re.compile(r"""navigate\(\s*(?:`([^`]+)`|["']([^"']+)["'])""")
HREF_RE = re.compile(r"""window\.location\.href\s*=\s*(?:`([^`]+)`|["']([^"']+)["'])""")
PY_FILE_RE = re.compile(r"""([A-Za-z0-9_./\\-]+\.py)""")
WINDOWS_PATH_RE = re.compile(r"""(?i)(?:[A-Z]:\\(?:[^<>"|?*\r\n]+\\)*[^<>"|?*\r\n]+)""")
UNC_PATH_RE = re.compile(r"""(?:\\\\[^<>"|?*\r\n]+\\[^<>"|?*\r\n]+(?:\\[^<>"|?*\r\n]+)*)""")
URL_RE = re.compile(r"""https?://[^\s"'`<>]+""")
RELATIVE_PATH_RE = re.compile(r"""(?<![A-Za-z0-9_])(?:\.\.?[\\/][A-Za-z0-9_.-]+(?:[\\/][A-Za-z0-9_.-]+)+|[A-Za-z0-9_.-]+(?:[\\/][A-Za-z0-9_.-]+)+)""")
SQL_TABLE_RE = re.compile(
    r"(?:CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?|DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?|INSERT\s+INTO\s+|UPDATE\s+|FROM\s+|JOIN\s+|DELETE\s+FROM\s+)"
    r"([A-Za-z0-9_]+)",
    re.IGNORECASE,
)


class RestoreUndoRequest(BaseModel):
    ids: list[int]


class ApproveAttachmentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attachment_id: Optional[int] = Field(default=None, alias="attachmentId")
    day: Optional[str] = None
    site: Optional[str] = None
    keyproof_total: Optional[float] = Field(default=None, alias="keyproofTotal")
    itemization_total: Optional[float] = Field(default=None, alias="itemizationTotal")
    balsheet_total: Optional[float] = Field(default=None, alias="balsheetTotal")
    balanced: Optional[bool] = None


class EdiImportRequest(BaseModel):
    accept_non_duplicates: bool = False


class ApprovedKeyproofResponse(BaseModel):
    id: int
    filename: str
    date: Optional[str] = None
    site: Optional[str] = None
    keyproof_total: Optional[float] = None
    itemization_total: Optional[float] = None
    balsheet_total: Optional[float] = None
    balanced: Optional[bool] = None
    review_notes: str = ""


class KeyproofSaveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    imported_file_id: Optional[int] = Field(default=None, alias="importedFileId")
    posting_day: Optional[str] = Field(default=None, alias="postingDay")
    site: Optional[str] = None
    cash: Optional[float] = None
    check_amount: Optional[float] = Field(default=None, alias="checkAmount")
    credit_card: Optional[float] = Field(default=None, alias="creditCard")
    lockbox: Optional[float] = None
    eft: Optional[float] = None
    misc: Optional[float] = None
    misc_description: Optional[str] = Field(default=None, alias="miscDescription")
    foreign_check: Optional[float] = Field(default=None, alias="foreignCheck")
    wire_transfer: Optional[float] = Field(default=None, alias="wireTransfer")
    subtotal: Optional[float] = None
    balanced: Optional[bool] = None
    itemization_complete: Optional[bool] = Field(default=None, alias="itemizationComplete")


class CalendarUpdateRequest(BaseModel):
    bank_day: str
    is_closed: bool
    closure_reason: Optional[str] = ""
    paperwork_day: Optional[str] = None


class TableRowsRequest(BaseModel):
    sort_column: Optional[str] = None
    sort_direction: Optional[str] = "asc"
    limit: Optional[int] = 250
    offset: Optional[int] = 0


class TableRowUpdateRequest(BaseModel):
    values: dict[str, object]


class AdminTableFieldRequest(BaseModel):
    name: str
    type: str = "TEXT"
    notnull: bool = False
    default: Optional[str] = None
    pk: bool = False


class AdminTableCreateRequest(BaseModel):
    table_name: str
    columns: list[AdminTableFieldRequest]


class AdminTableAddFieldRequest(BaseModel):
    column: AdminTableFieldRequest


class AdminAuditInspectResponse(BaseModel):
    term: str
    kind: str
    matches: list[dict[str, object]]


class AdminSchemaTableColumn(BaseModel):
    name: str
    type: str
    notnull: bool
    default: Optional[str] = None
    pk: bool


class AdminSchemaTableResponse(BaseModel):
    name: str
    sql: Optional[str] = None
    columns: list[AdminSchemaTableColumn]


class AdminSchemaResponse(BaseModel):
    tables: list[AdminSchemaTableResponse]


class AdminElementsScreenInfo(BaseModel):
    name: str
    path: str
    buttons: list[str]
    on_load: list[str]
    tables: list[str]
    scripts: list[str]
    routes: list[str]


class AdminElementsResponse(BaseModel):
    screens: list[AdminElementsScreenInfo]


class AdminPathLocation(BaseModel):
    path: str
    line: int


class AdminPathEntry(BaseModel):
    value: str
    category: str
    count: int
    locations: list[AdminPathLocation]


class AdminPathsResponse(BaseModel):
    screens: list[dict[str, object]]


def _build_admin_table_sheet_name(table_name: str, existing_names: set[str]) -> str:
    cleaned = re.sub(r"[\[\]:*?/\\]", "_", table_name).strip() or "Table"
    cleaned = cleaned[:31]

    if cleaned not in existing_names:
        existing_names.add(cleaned)
        return cleaned

    suffix = 2
    while True:
        suffix_text = f"_{suffix}"
        candidate = f"{cleaned[: max(0, 31 - len(suffix_text))]}{suffix_text}"
        if candidate not in existing_names:
            existing_names.add(candidate)
            return candidate
        suffix += 1


def _validate_sql_identifier(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", cleaned):
        raise HTTPException(status_code=400, detail=f"{label} must use letters, numbers, and underscores only")
    return cleaned


def _validate_sql_type(value: str) -> str:
    cleaned = value.strip().upper()
    if not cleaned or not re.fullmatch(r"[A-Z0-9_(), ]+", cleaned):
        raise HTTPException(status_code=400, detail="Column type contains invalid characters")
    return cleaned


def _sqlite_literal(value: Optional[str]) -> str:
    if value is None:
        return "NULL"
    cleaned = str(value)
    if cleaned == "":
        return "''"
    if cleaned.lower() in {"null", "none"}:
        return "NULL"
    if cleaned.lower() in {"true", "false"}:
        return "1" if cleaned.lower() == "true" else "0"
    if re.fullmatch(r"-?\d+", cleaned):
        return cleaned
    if re.fullmatch(r"-?\d+\.\d+", cleaned):
        return cleaned
    return "'" + cleaned.replace("'", "''") + "'"


def _stringify_excel_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple, set)):
        return str(value)
    return str(value)


def _strip_html_tags(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def _extract_button_summaries(text: str) -> list[str]:
    summaries: list[str] = []
    for button_block in BUTTON_BLOCK_RE.findall(text):
        label = _strip_html_tags(button_block)
        nav_targets = []
        for route_match in NAVIGATE_RE.findall(button_block):
            nav_targets.extend(target for target in route_match if target)
        for href_match in HREF_RE.findall(button_block):
            nav_targets.extend(target for target in href_match if target)

        if label and nav_targets:
            summaries.append(f"{label} -> {nav_targets[0]}")
        elif label:
            summaries.append(label)
        elif nav_targets:
            summaries.append(nav_targets[0])

    return sorted(dict.fromkeys(summaries))


def _extract_on_load_summaries(text: str) -> list[str]:
    summaries: list[str] = []
    for effect_body in USE_EFFECT_BLOCK_RE.findall(text):
        effect_hits: list[str] = []
        for route_match in NAVIGATE_RE.findall(effect_body):
            effect_hits.extend(target for target in route_match if target)
        for href_match in HREF_RE.findall(effect_body):
            effect_hits.extend(target for target in href_match if target)

        call_candidates = []
        for call_name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", effect_body):
            if call_name in {
                "useEffect",
                "setState",
                "setLoading",
                "setError",
                "setColumns",
                "setRows",
                "setSearch",
                "setSelectedTable",
                "setEditRow",
                "setEditDraft",
                "setCompiledAt",
            }:
                continue
            if call_name.startswith(("fetch", "load", "run", "refresh", "build", "compile", "update", "delete", "save", "reset")):
                call_candidates.append(f"{call_name}()")

        if effect_hits:
            summaries.extend(effect_hits)
        if call_candidates:
            summaries.extend(call_candidates)
        if not effect_hits and not call_candidates:
            summaries.append("useEffect([])")

    return sorted(dict.fromkeys(summaries))


def _normalize_path_literal(value: str) -> str:
    return value.replace("\\\\", "\\").strip()


def _classify_path_literal(value: str) -> str:
    lower = value.lower()
    if lower.startswith(("http://", "https://")):
        return "url"
    if re.match(r"(?i)^[a-z]:\\", value) or value.startswith("\\\\"):
        return "filesystem"
    if value.startswith("/"):
        return "route"
    if "\\" in value or "/" in value:
        return "relative"
    return "other"


def _collect_path_literals(text: str) -> list[tuple[str, int]]:
    hits: list[tuple[str, int]] = []
    patterns = [WINDOWS_PATH_RE, UNC_PATH_RE, URL_RE, RELATIVE_PATH_RE, ROUTE_RE]
    for line_number, line in enumerate(text.splitlines(), start=1):
        seen_on_line: set[tuple[str, str]] = set()
        for pattern in patterns:
            for match in pattern.finditer(line):
                raw_value = match.group(1) if pattern is ROUTE_RE else match.group(0)
                normalized = _normalize_path_literal(raw_value)
                category = _classify_path_literal(normalized)
                key = (normalized, category)
                if key in seen_on_line:
                    continue
                seen_on_line.add(key)
                hits.append((normalized, line_number))
    return hits


def _scan_text_references(full_path: str, text: str, tables: list[str]):
    rel_path = os.path.relpath(full_path, WORKFLOW_ROOT)
    lower_text = text.lower()
    route_hits = sorted(set(ROUTE_RE.findall(text)))
    sql_hits = set(SQL_TABLE_RE.findall(text))
    table_hits = [table for table in tables if re.search(rf"\b{re.escape(table)}\b", text, re.IGNORECASE)]
    return rel_path, route_hits, sql_hits, lower_text, table_hits


def build_admin_audit_map():
    conn = get_conn()
    cur = conn.cursor()
    tables = [
        row[0]
        for row in cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    ]
    conn.close()

    usage = {
        table: {"screens": set(), "scripts": set(), "routes": set(), "sql_hits": set()}
        for table in tables
    }

    scan_roots = [
        os.path.join(WORKFLOW_ROOT, "Frontend", "src"),
        os.path.join(WORKFLOW_ROOT, "Script"),
    ]

    for root_dir in scan_roots:
        if not os.path.isdir(root_dir):
            continue
        for current_root, _, files in os.walk(root_dir):
            for filename in files:
                if not filename.lower().endswith(SCRIPT_EXTENSIONS):
                    continue
                full_path = os.path.join(current_root, filename)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as handle:
                        text = handle.read()
                except OSError:
                    continue

                rel_path = os.path.relpath(full_path, WORKFLOW_ROOT)
                route_hits = sorted(set(ROUTE_RE.findall(text)))
                sql_hits = set(SQL_TABLE_RE.findall(text))
                lower_text = text.lower()

                for table in tables:
                    table_lower = table.lower()
                    if re.search(rf"\b{re.escape(table)}\b", text, re.IGNORECASE):
                        if full_path.lower().endswith(".tsx"):
                            usage[table]["screens"].add(rel_path)
                        else:
                            usage[table]["scripts"].add(rel_path)

                    if table in sql_hits:
                        usage[table]["sql_hits"].add(rel_path)

                    if route_hits and table_lower in lower_text:
                        usage[table]["routes"].update(route_hits)

    result = []
    for table, info in usage.items():
        screens = sorted(info["screens"])
        scripts = sorted(info["scripts"])
        routes = sorted(info["routes"])
        sql_hits = sorted(info["sql_hits"])
        read_count = len(screens) + len(scripts) + len(routes) + len(sql_hits)
        status = []
        if not scripts and not sql_hits:
            status.append("unmanaged")
        if not screens:
            status.append("no screen")
        if read_count >= 5:
            status.append("shared")
        if len(scripts) >= 4:
            status.append("possible redundancy")

        result.append(
            {
                "name": table,
                "screens": screens,
                "scripts": scripts,
                "routes": routes,
                "sql_hits": sql_hits,
                "read_count": read_count,
                "status": status,
            }
        )

    result.sort(key=lambda item: (-item["read_count"], len(item["status"]), item["name"].lower()))
    summary = {
        "table_count": len(result),
        "shared_count": sum(1 for item in result if "shared" in item["status"]),
        "no_screen_count": sum(1 for item in result if "no screen" in item["status"]),
        "unmanaged_count": sum(1 for item in result if "unmanaged" in item["status"]),
        "redundant_count": sum(1 for item in result if "possible redundancy" in item["status"]),
    }
    return {"summary": summary, "tables": result}


def build_admin_report_catalog():
    conn = get_conn()
    cur = conn.cursor()
    tables = [
        row[0]
        for row in cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    ]
    conn.close()

    table_usage = {table: {"screens": set(), "scripts": set(), "routes": set(), "sql_hits": set()} for table in tables}
    screen_usage: dict[str, dict[str, set[str]]] = {}
    script_usage: dict[str, dict[str, set[str]]] = {}

    scan_roots = [
        os.path.join(WORKFLOW_ROOT, "Frontend", "src"),
        os.path.join(WORKFLOW_ROOT, "Script"),
    ]
    for root_dir in scan_roots:
        if not os.path.isdir(root_dir):
            continue
        for current_root, _, files in os.walk(root_dir):
            for filename in files:
                if not filename.lower().endswith(SCRIPT_EXTENSIONS):
                    continue
                full_path = os.path.join(current_root, filename)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as handle:
                        text = handle.read()
                except OSError:
                    continue

                rel_path, route_hits, sql_hits, _lower_text, table_hits = _scan_text_references(full_path, text, tables)
                is_screen = full_path.lower().endswith(".tsx")
                entry = screen_usage if is_screen else script_usage
                entry.setdefault(rel_path, {"tables": set(), "routes": set(), "sql_hits": set(), "related": set()})

                for table in table_hits:
                    if is_screen:
                        table_usage[table]["screens"].add(rel_path)
                    else:
                        table_usage[table]["scripts"].add(rel_path)
                    if route_hits:
                        table_usage[table]["routes"].update(route_hits)
                    if sql_hits:
                        table_usage[table]["sql_hits"].add(rel_path)
                    entry[rel_path]["tables"].add(table)
                    entry[rel_path]["related"].update(route_hits)

                if route_hits:
                    entry[rel_path]["routes"].update(route_hits)
                if sql_hits:
                    entry[rel_path]["sql_hits"].update(sql_hits)

    table_report = []
    for table, info in table_usage.items():
        screens = sorted(info["screens"])
        scripts = sorted(info["scripts"])
        routes = sorted(info["routes"])
        sql_hits = sorted(info["sql_hits"])
        table_report.append(
            {
                "name": table,
                "kind": "table",
                "screens": screens,
                "scripts": scripts,
                "routes": routes,
                "sql_hits": sql_hits,
                "precedents": scripts,
                "dependants": screens + routes,
                "status": [
                    *("unmanaged" if not info["scripts"] and not info["sql_hits"] else []),
                ],
            }
        )
    table_report.sort(key=lambda item: item["name"].lower())

    screen_paths = sorted(screen_usage.keys())
    screen_report = []
    for path, info in screen_usage.items():
        tables = sorted(info["tables"])
        routes = sorted(info["routes"])
        sql_hits = sorted(info["sql_hits"])
        related = sorted(info["related"])
        accessible_screens = []
        route_blob = " ".join(routes).lower()
        for other_path in screen_paths:
            if other_path == path:
                continue
            screen_name = os.path.splitext(os.path.basename(other_path))[0].lower()
            other_path_lower = other_path.lower()
            if screen_name and (screen_name in route_blob or other_path_lower in route_blob):
                accessible_screens.append(other_path)
        screen_report.append(
            {
                "name": path,
                "kind": "screen",
                "tables": tables,
                "routes": routes,
                "sql_hits": sql_hits,
                "related": related,
                "accessible_screens": sorted(accessible_screens),
                "precedents": tables,
                "dependants": routes,
            }
        )
    screen_report.sort(key=lambda item: item["name"].lower())

    script_report = []
    for path, info in script_usage.items():
        tables = sorted(info["tables"])
        routes = sorted(info["routes"])
        sql_hits = sorted(info["sql_hits"])
        related = sorted(info["related"])
        script_report.append(
            {
                "name": path,
                "kind": "script",
                "tables": tables,
                "routes": routes,
                "sql_hits": sql_hits,
                "related": related,
                "precedents": tables,
                "dependants": routes,
            }
        )
    script_report.sort(key=lambda item: item["name"].lower())

    return {
        "tables": table_report,
        "screens": screen_report,
        "scripts": script_report,
    }


def build_admin_schema_report():
    conn = get_conn()
    cur = conn.cursor()
    tables: list[dict[str, object]] = []
    rows = cur.execute(
        """
        SELECT name, sql
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    for name, sql in rows:
        column_rows = cur.execute(f"PRAGMA table_info({name})").fetchall()
        columns = []
        for _, col_name, col_type, notnull, default_value, pk in column_rows:
            columns.append(
                {
                    "name": col_name,
                    "type": col_type or "",
                    "notnull": bool(notnull),
                    "default": default_value,
                    "pk": bool(pk),
                }
            )
        tables.append({"name": name, "sql": sql, "columns": columns})
    conn.close()
    return {"tables": tables}


def build_admin_elements_report():
    conn = get_conn()
    cur = conn.cursor()
    tables = [
        row[0]
        for row in cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    ]
    conn.close()

    screen_rows: list[dict[str, object]] = []
    scan_roots = [
        os.path.join(WORKFLOW_ROOT, "Frontend", "src", "Screens"),
        os.path.join(WORKFLOW_ROOT, "Script"),
    ]

    for root_dir in scan_roots:
        if not os.path.isdir(root_dir):
            continue
        for current_root, _, files in os.walk(root_dir):
            for filename in files:
                if not filename.lower().endswith(SCRIPT_EXTENSIONS):
                    continue

                full_path = os.path.join(current_root, filename)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as handle:
                        text = handle.read()
                except OSError:
                    continue

                rel_path = os.path.relpath(full_path, WORKFLOW_ROOT)
                display_name = os.path.splitext(filename)[0]
                button_summaries = _extract_button_summaries(text) if filename.lower().endswith(".tsx") else []
                on_load_summaries = _extract_on_load_summaries(text) if filename.lower().endswith(".tsx") else []
                route_hits = sorted(set(ROUTE_RE.findall(text)))
                sql_hits = sorted(set(SQL_TABLE_RE.findall(text)))
                table_hits = sorted({table for table in tables if re.search(rf"\b{re.escape(table)}\b", text, re.IGNORECASE)})
                script_hits = sorted(set(PY_FILE_RE.findall(text)))

                if not (button_summaries or on_load_summaries or route_hits or sql_hits or table_hits or script_hits):
                    continue

                screen_rows.append(
                    {
                        "name": display_name,
                        "path": rel_path,
                        "buttons": button_summaries,
                        "on_load": on_load_summaries,
                        "tables": table_hits,
                        "scripts": script_hits,
                        "routes": route_hits,
                    }
                )

    screen_rows.sort(key=lambda item: (item["name"].lower(), item["path"].lower()))
    return {"screens": screen_rows}


def build_admin_paths_report():
    screen_rows: list[dict[str, object]] = []
    scan_root = os.path.join(WORKFLOW_ROOT, "Frontend", "src", "Screens")

    if os.path.isdir(scan_root):
        for current_root, _, files in os.walk(scan_root):
            for filename in files:
                if not filename.lower().endswith(SCRIPT_EXTENSIONS):
                    continue

                full_path = os.path.join(current_root, filename)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as handle:
                        text = handle.read()
                except OSError:
                    continue

                rel_path = os.path.relpath(full_path, WORKFLOW_ROOT)
                path_map: dict[tuple[str, str], list[int]] = {}
                for value, line_number in _collect_path_literals(text):
                    category = _classify_path_literal(value)
                    path_map.setdefault((value, category), []).append(line_number)

                if not path_map:
                    continue

                paths = [
                    {
                        "value": value,
                        "category": category,
                        "count": len(line_numbers),
                        "lines": sorted(set(line_numbers)),
                    }
                    for (value, category), line_numbers in path_map.items()
                ]
                paths.sort(key=lambda item: (item["category"], item["value"].lower()))
                screen_rows.append(
                    {
                        "name": os.path.splitext(filename)[0],
                        "path": rel_path,
                        "path_count": len(paths),
                        "paths": paths,
                    }
                )

    screen_rows.sort(key=lambda item: item["path"].lower())
    return {"screens": screen_rows}


@app.get("/admin/audit/map")
def get_admin_audit_map():
    return build_admin_audit_map()


@app.get("/admin/reports/catalog")
def get_admin_report_catalog():
    return build_admin_report_catalog()


@app.get("/admin/schema")
def get_admin_schema_report():
    return build_admin_schema_report()


@app.get("/admin/elements/catalog")
def get_admin_elements_catalog():
    return build_admin_elements_report()


@app.get("/admin/paths/catalog")
def get_admin_paths_catalog():
    return build_admin_paths_report()


@app.get("/admin/audit/inspect")
def get_admin_audit_inspect(term: str, kind: str = "table"):
    safe_term = term.strip()
    if not safe_term:
        raise HTTPException(status_code=400, detail="term is required")

    root_terms = {safe_term}
    base_term = os.path.splitext(os.path.basename(safe_term))[0]
    if base_term:
        root_terms.add(base_term)
    kind_lower = kind.lower()
    if kind_lower in {"screen", "dependant", "contextual"}:
        root_terms.add(safe_term.replace(".tsx", "").replace(".ts", ""))
    if kind_lower in {"dependant", "contextual"}:
        parent = os.path.dirname(safe_term.replace("/", os.sep).replace("\\", os.sep))
        if parent:
            root_terms.add(parent)
            root_terms.add(os.path.basename(parent))
    if kind_lower == "contextual":
        pieces = re.split(r"[\\/_.-]+", safe_term)
        root_terms.update(piece for piece in pieces if len(piece) > 2)

    matches: list[dict[str, object]] = []
    exact_paths: list[dict[str, object]] = []
    roots = [
        os.path.join(WORKFLOW_ROOT, "Frontend", "src"),
        os.path.join(WORKFLOW_ROOT, "Script"),
    ]
    for root_dir in roots:
        if not os.path.isdir(root_dir):
            continue
        for current_root, _, files in os.walk(root_dir):
            for filename in files:
                if not filename.lower().endswith(SCRIPT_EXTENSIONS):
                    continue
                full_path = os.path.join(current_root, filename)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as handle:
                        lines = handle.readlines()
                except OSError:
                    continue

                rel_path = os.path.relpath(full_path, WORKFLOW_ROOT)
                screen_basename = os.path.splitext(os.path.basename(rel_path))[0].lower()
                path_lower = rel_path.lower()
                is_exact_screen = kind_lower == "screen" and (
                    screen_basename == safe_term.lower()
                    or screen_basename == base_term.lower()
                    or path_lower.endswith(f"{safe_term.lower()}.tsx")
                    or path_lower.endswith(f"{base_term.lower()}.tsx")
                )

                hits = []
                for index, line in enumerate(lines, start=1):
                    line_lower = line.lower()
                    if any(term.lower() in line_lower for term in root_terms):
                        hits.append({"line": index, "text": line.rstrip("\n")})
                if hits or is_exact_screen:
                    first_line = hits[0]["line"] if hits else 0
                    item = {
                        "path": rel_path,
                        "kind": "screen" if full_path.lower().endswith(".tsx") else "script",
                        "hits": hits[:50],
                        "first_line": first_line,
                    }
                    if is_exact_screen:
                        exact_paths.append(item)
                    elif kind_lower == "screen":
                        matches.append(item)
                    else:
                        matches.append(item)

    matches.sort(key=lambda item: (item["path"], item["first_line"]))
    if exact_paths:
        exact_paths.sort(key=lambda item: (item["path"], item["first_line"]))
        exact_paths_set = {exact["path"] for exact in exact_paths}
        matches = exact_paths + [item for item in matches if item["path"] not in exact_paths_set]
    return {"term": safe_term, "kind": kind, "matches": matches}


def ensure_keyproof_columns(conn):
    cur = conn.cursor()
    existing = {row[1] for row in cur.execute("PRAGMA table_info(keyproof)").fetchall()}
    additions = [
        ("posting_day", "TEXT"),
        ("imported_file_id", "INTEGER"),
    ]

    for column, sql_type in additions:
        if column not in existing:
            cur.execute(f"ALTER TABLE keyproof ADD COLUMN {column} {sql_type}")


def ensure_approved_keyproof_columns(conn):
    cur = conn.cursor()
    existing = {row[1] for row in cur.execute("PRAGMA table_info(import_files)").fetchall()}
    additions = [
        ("keyproof_total", "REAL"),
        ("itemization_total", "REAL"),
        ("balsheet_total", "REAL"),
        ("balanced", "INTEGER"),
    ]

    for column, sql_type in additions:
        if column not in existing:
            cur.execute(f"ALTER TABLE import_files ADD COLUMN {column} {sql_type}")


def ensure_balsheet_daynotes_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Balsheet_daynotes (
            posting_date TEXT PRIMARY KEY,
            notes TEXT NOT NULL DEFAULT '',
            message TEXT NOT NULL DEFAULT ''
        )
        """
    )
    existing = {row[1] for row in cur.execute("PRAGMA table_info(Balsheet_daynotes)").fetchall()}
    if "message" not in existing:
        cur.execute("ALTER TABLE Balsheet_daynotes ADD COLUMN message TEXT NOT NULL DEFAULT ''")
    conn.commit()


def get_balsheet_day_note(conn, posting_date: str):
    row = conn.execute(
        "SELECT notes, message FROM Balsheet_daynotes WHERE posting_date = ?",
        (posting_date,),
    ).fetchone()
    return {"notes": row[0], "message": row[1]} if row else {"notes": "", "message": ""}


def save_balsheet_day_note(conn, posting_date: str, notes: str, message: str = ""):
    conn.execute(
        """
        INSERT INTO Balsheet_daynotes (posting_date, notes, message)
        VALUES (?, ?, ?)
        ON CONFLICT(posting_date) DO UPDATE SET notes = excluded.notes, message = excluded.message
        """,
        (posting_date, notes or "", message or ""),
    )


def ensure_site_cc_report_batch_columns(conn):
    cur = conn.cursor()
    existing = {row[1] for row in cur.execute("PRAGMA table_info(site_cc_reports)").fetchall()}
    additions = [
        ("batch_id", "INTEGER"),
        ("batch_number", "TEXT"),
    ]

    for column, sql_type in additions:
        if column not in existing:
            cur.execute(f"ALTER TABLE site_cc_reports ADD COLUMN {column} {sql_type}")


def _save_keyproof_once(payload: KeyproofSaveRequest, posting_day: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        ensure_keyproof_columns(conn)
        conn.execute("BEGIN IMMEDIATE")

        if payload.imported_file_id is not None:
            cur.execute(
                """
                SELECT id FROM keyproof
                WHERE imported_file_id = ? AND posting_day = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (payload.imported_file_id, posting_day),
            )
        else:
            cur.execute(
                """
                SELECT id FROM keyproof
                WHERE posting_day = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (posting_day,),
            )

        existing = cur.fetchone()
        values = (
            payload.imported_file_id,
            posting_day,
            payload.site,
            payload.cash,
            payload.check_amount,
            payload.credit_card,
            payload.lockbox,
            payload.eft,
            payload.misc,
            payload.misc_description,
            payload.foreign_check,
            payload.wire_transfer,
            payload.subtotal,
            int(payload.balanced) if payload.balanced is not None else None,
            int(payload.itemization_complete) if payload.itemization_complete is not None else None,
        )

        if existing:
            cur.execute(
                """
                UPDATE keyproof
                SET imported_file_id = COALESCE(?, imported_file_id),
                    posting_day = ?,
                    site = COALESCE(?, site),
                    cash = COALESCE(?, cash),
                    check_amount = COALESCE(?, check_amount),
                    credit_card = COALESCE(?, credit_card),
                    lockbox = COALESCE(?, lockbox),
                    eft = COALESCE(?, eft),
                    misc = COALESCE(?, misc),
                    misc_description = COALESCE(?, misc_description),
                    foreign_check = COALESCE(?, foreign_check),
                    wire_transfer = COALESCE(?, wire_transfer),
                    subtotal = COALESCE(?, subtotal),
                    balanced = COALESCE(?, balanced),
                    itemization_complete = COALESCE(?, itemization_complete),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (*values, existing[0]),
            )
            keyproof_id = existing[0]
        else:
            cur.execute(
                """
                INSERT INTO keyproof (
                    imported_file_id, posting_day, site, cash, check_amount, credit_card, lockbox, eft,
                    misc, misc_description, foreign_check, wire_transfer, subtotal, balanced, itemization_complete
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            keyproof_id = cur.lastrowid

        conn.commit()
        return {"status": "ok", "id": keyproof_id, "posting_day": posting_day}
    except sqlite3.OperationalError:
        conn.rollback()
        raise
    finally:
        conn.close()


class BalsheetEntryRequest(BaseModel):
    posting_date: Optional[str] = None
    type: str
    amount: float
    payer: str = ""
    check_number: str = ""
    edi: str = "N"
    poster: str = ""
    eob: str = ""
    unposted: float = 0
    misc: float = 0
    misc_type: str = ""
    notes: str = ""
    nick: Optional[float] = None
    raul: Optional[float] = None
    needs: str = ""
    from_date: str = ""
    to_date: str = ""


class BalsheetBulkRequest(BaseModel):
    entries: list[BalsheetEntryRequest]
    source_attachment_id: Optional[int] = None


class BalsheetEftLockboxImportRequest(BaseModel):
    override_existing: bool = False
    posting_date: Optional[str] = None


class SiteUploadRequest(BaseModel):
    generate_snapshots: bool = True
    import_cc_reports: bool = True


class LaunchSiteEmailDownloaderRequest(BaseModel):
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def day_filter(day: Optional[str]):
    if not day:
        return "", []

    if day == "Unknown":
        return " AND (processed_at IS NULL OR processed_at = '')", []

    return " AND processed_at = ?", [day]


# ------------------------------------------------------------
# GET FIRST PENDING IMPORTED FILE
# ------------------------------------------------------------
@app.get("/attachments/pending")
def get_first_pending(day: Optional[str] = None):
    conn = get_conn()
    cur = conn.cursor()
    day_sql, params = day_filter(day)

    cur.execute(f"""
        SELECT id, filename, snapshot_path, review_status
        FROM import_files
        WHERE review_status = 'Pending'
        {day_sql}
        ORDER BY id ASC
        LIMIT 1
    """, params)

    row = cur.fetchone()
    conn.close()

    if not row:
        return {"done": True}

    return {
        "id": row[0],
        "filename": row[1],
        "snapshot": row[2],
        "status": row[3],
        "done": False,
    }


# ------------------------------------------------------------
# NEXT PENDING FILE
# ------------------------------------------------------------
@app.get("/attachments/{attachment_id}/next")
def get_next(attachment_id: int, day: Optional[str] = None):
    conn = get_conn()
    cur = conn.cursor()
    day_sql, params = day_filter(day)

    cur.execute(f"""
        SELECT id, filename, snapshot_path, review_status
        FROM import_files
        WHERE review_status = 'Pending' AND id > ?
        {day_sql}
        ORDER BY id ASC
        LIMIT 1
    """, [attachment_id, *params])

    row = cur.fetchone()
    conn.close()

    if not row:
        return {"done": True}

    return {
        "id": row[0],
        "filename": row[1],
        "snapshot": row[2],
        "status": row[3],
        "done": False,
    }


# ------------------------------------------------------------
# PREVIOUS PENDING FILE
# ------------------------------------------------------------
@app.get("/attachments/{attachment_id}/prev")
def get_prev(attachment_id: int, day: Optional[str] = None):
    conn = get_conn()
    cur = conn.cursor()
    day_sql, params = day_filter(day)

    cur.execute(f"""
        SELECT id, filename, snapshot_path, review_status
        FROM import_files
        WHERE review_status = 'Pending' AND id < ?
        {day_sql}
        ORDER BY id DESC
        LIMIT 1
    """, [attachment_id, *params])

    row = cur.fetchone()
    conn.close()

    if not row:
        return {"done": True}

    return {
        "id": row[0],
        "filename": row[1],
        "snapshot": row[2],
        "status": row[3],
        "done": False,
    }


@app.get("/attachments/{attachment_id}/current")
def get_pending_attachment_by_id(attachment_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, snapshot_path, review_status
        FROM import_files
        WHERE id = ? AND review_status = 'Pending'
        LIMIT 1
    """, (attachment_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return {"done": True}

    return {
        "id": row[0],
        "filename": row[1],
        "snapshot": row[2],
        "status": row[3],
        "done": False,
    }


@app.get("/attachments/{attachment_id}/batch")
def get_attachment_batch(attachment_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT batch_id, batch_number
        FROM import_files
        WHERE id = ?
        """,
        (attachment_id,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Attachment not found")

    return {
        "batch_id": row["batch_id"],
        "batch_number": row["batch_number"],
    }


# ------------------------------------------------------------
# SNAPSHOT IMAGE
# ------------------------------------------------------------
@app.get("/attachments/{attachment_id}/snapshot")
def get_snapshot(attachment_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT snapshot_path FROM import_files WHERE id = ?", (attachment_id,))
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    snapshot_path = row[0]

    if not os.path.exists(snapshot_path):
        raise HTTPException(status_code=404, detail="Snapshot file missing")

    return FileResponse(snapshot_path)


# ------------------------------------------------------------
# ORIGINAL PDF
# ------------------------------------------------------------
@app.get("/attachments/{attachment_id}/original")
def get_original_pdf(attachment_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            f.filename,
            (
                SELECT h.moved_to
                FROM import_EmailAttachmentHistory h
                WHERE h.original_filename = f.filename
                  AND h.moved_to IS NOT NULL
                  AND h.moved_to != ''
                ORDER BY h.id DESC
                LIMIT 1
            ) AS moved_to
        FROM import_files f
        WHERE f.id = ?
        """,
        (attachment_id,),
    )
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Original PDF not found")

    filename = os.path.basename(row[0])
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=404, detail="Original attachment is not a PDF")

    sites_root = os.path.abspath(SITES_FOLDER)
    candidates = []
    moved_to = row[1] if len(row) > 1 else None

    if moved_to:
        candidates.append(os.path.abspath(moved_to))

    if os.path.isabs(row[0]):
        candidates.append(os.path.abspath(row[0]))

    candidates.append(os.path.abspath(os.path.join(sites_root, filename)))
    pdf_path = next(
        (
            candidate
            for candidate in candidates
            if os.path.basename(candidate) == filename
            and candidate.lower().endswith(".pdf")
            and os.path.exists(candidate)
        ),
        None,
    )

    if not pdf_path:
        raise HTTPException(status_code=404, detail="Original PDF file missing")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="inline",
    )


# ------------------------------------------------------------
# APPROVE FILE
# ------------------------------------------------------------
@app.post("/attachments/{attachment_id}/approve")
def approve_attachment(attachment_id: int, payload: Optional[ApproveAttachmentRequest] = None):
    conn = get_conn()
    cur = conn.cursor()
    ensure_approved_keyproof_columns(conn)

    review_notes = None
    if payload:
        note_parts = []
        if payload.day:
            note_parts.append(f"day={normalize_balsheet_date(payload.day) or payload.day}")
        if payload.site:
            note_parts.append(f"site={payload.site}")
        if payload.keyproof_total is not None:
            note_parts.append(f"keyproof_total={round(payload.keyproof_total, 2):.2f}")
        if payload.itemization_total is not None:
            note_parts.append(f"itemization_total={round(payload.itemization_total, 2):.2f}")
        if payload.balsheet_total is not None:
            note_parts.append(f"balsheet_total={round(payload.balsheet_total, 2):.2f}")
        if payload.balanced is not None:
            note_parts.append(f"balanced={'true' if payload.balanced else 'false'}")
        if note_parts:
            review_notes = "Keyproof reconciliation: " + ", ".join(note_parts)

    cur.execute("""
        UPDATE import_files
        SET review_status = 'Approved',
            review_notes = COALESCE(?, review_notes),
            site = COALESCE(?, site),
            keyproof_total = COALESCE(?, keyproof_total),
            itemization_total = COALESCE(?, itemization_total),
            balsheet_total = COALESCE(?, balsheet_total),
            balanced = COALESCE(?, balanced)
        WHERE id = ?
    """, (
        review_notes,
        payload.site if payload else None,
        payload.keyproof_total if payload else None,
        payload.itemization_total if payload else None,
        payload.balsheet_total if payload else None,
        int(payload.balanced) if payload and payload.balanced is not None else None,
        attachment_id,
    ))

    conn.commit()
    conn.close()

    return {"status": "approved", "id": attachment_id}


# ------------------------------------------------------------
# APPROVED FILES
# ------------------------------------------------------------
@app.get("/approved")
def get_approved_files():
    conn = get_conn()
    cur = conn.cursor()
    ensure_approved_keyproof_columns(conn)

    cur.execute("""
        SELECT import_files.id, import_files.filename, import_files.processed_at, import_files.site, import_files.detail, import_files.amount, import_files.review_notes,
               import_files.keyproof_total, import_files.itemization_total, import_files.balsheet_total, import_files.balanced,
               k.site, k.misc_description, k.subtotal
        FROM import_files
        LEFT JOIN keyproof k
            ON k.id = (
                SELECT kp.id
                FROM keyproof kp
                WHERE kp.imported_file_id = import_files.id
                ORDER BY kp.id DESC
                LIMIT 1
            )
        WHERE review_status = 'Approved'
        ORDER BY import_files.processed_at DESC, import_files.id DESC
    """)
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "filename": row[1],
            "date": row[2],
            "site": row[3],
            "detail": row[4],
            "total": row[5] or 0,
            "review_notes": row[6] or "",
            "keyproof_total": row[7],
            "itemization_total": row[8],
            "balsheet_total": row[9],
            "balanced": bool(row[10]) if row[10] is not None else None,
            "keyproof_site": row[11],
            "keyproof_detail": row[12],
            "keyproof_total_from_keyproof": row[13],
        }
        for row in rows
    ]


@app.get("/approved/by-day")
def get_approved_by_day(day: Optional[str] = None):
    if not day:
        raise HTTPException(status_code=400, detail="day is required")

    normalized_day = normalize_balsheet_date(day) or day
    conn = get_conn()
    cur = conn.cursor()
    ensure_approved_keyproof_columns(conn)

    cur.execute(
        """
        SELECT import_files.id, import_files.filename, import_files.processed_at, import_files.site, import_files.review_notes,
               import_files.keyproof_total, import_files.itemization_total, import_files.balsheet_total, import_files.balanced,
               k.site, k.misc_description, k.subtotal
        FROM import_files
        LEFT JOIN keyproof k
            ON k.id = (
                SELECT kp.id
                FROM keyproof kp
                WHERE kp.imported_file_id = import_files.id
                ORDER BY kp.id DESC
                LIMIT 1
            )
        WHERE review_status = 'Approved'
        ORDER BY import_files.id DESC
        """,
    )
    rows = cur.fetchall()
    conn.close()

    for row in rows:
        row_day = normalize_balsheet_date(row[2]) or row[2]
        note = row[4] or ""

        if row_day != normalized_day:
            continue

        parsed = {
            "keyproof_total": None,
            "itemization_total": None,
            "balsheet_total": None,
            "balanced": None,
        }
        payload = note.replace("Keyproof reconciliation:", "").strip()
        for part in payload.split(","):
            key, _, value = part.partition("=")
            key = key.strip().lower()
            value = value.strip()
            if key == "keyproof_total":
                parsed["keyproof_total"] = float(value) if value else None
            elif key == "itemization_total":
                parsed["itemization_total"] = float(value) if value else None
            elif key == "balsheet_total":
                parsed["balsheet_total"] = float(value) if value else None
            elif key == "balanced":
                parsed["balanced"] = value.lower() == "true"
            elif key == "site" and not row[3]:
                pass

        return {
            "id": row[0],
            "filename": row[1],
            "date": row_day,
            "site": row[3] or row[9],
            "detail": row[4] or row[10],
            "review_notes": note,
            "keyproof_total": row[5] if row[5] is not None else parsed["keyproof_total"],
            "itemization_total": row[6] if row[6] is not None else parsed["itemization_total"],
            "balsheet_total": row[7] if row[7] is not None else parsed["balsheet_total"],
            "balanced": bool(row[8]) if row[8] is not None else parsed["balanced"],
            "keyproof_total_from_keyproof": row[11],
        }

    raise HTTPException(status_code=404, detail="Approved keyproof for day not found")


# ------------------------------------------------------------
# RESTORE APPROVED DAY TO PENDING
# ------------------------------------------------------------
@app.post("/approved/restore")
def restore_approved_day(day: Optional[str] = None):
    if not day:
        raise HTTPException(status_code=400, detail="Day is required")

    conn = get_conn()
    cur = conn.cursor()
    day_sql, params = day_filter(day)

    cur.execute(f"""
        SELECT id
        FROM import_files
        WHERE review_status = 'Approved'
        {day_sql}
        ORDER BY id ASC
    """, params)
    restored_ids = [row[0] for row in cur.fetchall()]

    cur.execute(f"""
        UPDATE import_files
        SET review_status = 'Pending'
        WHERE review_status = 'Approved'
        {day_sql}
    """, params)

    restored = cur.rowcount
    conn.commit()
    conn.close()

    return {
        "status": "restored",
        "day": day,
        "count": restored,
        "previous_status": "Approved",
        "ids": restored_ids,
    }


# ------------------------------------------------------------
# UNDO APPROVED DAY RESTORE
# ------------------------------------------------------------
@app.post("/approved/restore/undo")
def undo_restore_approved_day(payload: RestoreUndoRequest):
    ids = sorted(set(payload.ids))
    if not ids:
        raise HTTPException(status_code=400, detail="At least one id is required")

    placeholders = ",".join("?" for _ in ids)
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(f"""
        UPDATE import_files
        SET review_status = 'Approved'
        WHERE review_status = 'Pending'
        AND id IN ({placeholders})
    """, ids)

    restored = cur.rowcount
    conn.commit()
    conn.close()

    return {
        "status": "restored",
        "previous_status": "Pending",
        "restored_status": "Approved",
        "count": restored,
        "ids": ids,
    }


# ------------------------------------------------------------
# REJECTED FILES
# ------------------------------------------------------------
@app.get("/rejected")
def get_rejected_files():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, processed_at, site, detail, amount
        FROM import_files
        WHERE review_status = 'Rejected'
        ORDER BY processed_at DESC, id DESC
    """)
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "filename": row[1],
            "date": row[2],
            "site": row[3],
            "detail": row[4],
            "total": row[5] or 0,
        }
        for row in rows
    ]


# ------------------------------------------------------------
# RESTORE REJECTED DAY TO PENDING
# ------------------------------------------------------------
@app.post("/rejected/restore")
def restore_rejected_day(day: Optional[str] = None):
    if not day:
        raise HTTPException(status_code=400, detail="Day is required")

    conn = get_conn()
    cur = conn.cursor()
    day_sql, params = day_filter(day)

    cur.execute(f"""
        SELECT id
        FROM import_files
        WHERE review_status = 'Rejected'
        {day_sql}
        ORDER BY id ASC
    """, params)
    restored_ids = [row[0] for row in cur.fetchall()]

    cur.execute(f"""
        UPDATE import_files
        SET review_status = 'Pending'
        WHERE review_status = 'Rejected'
        {day_sql}
    """, params)

    restored = cur.rowcount
    conn.commit()
    conn.close()

    return {
        "status": "restored",
        "day": day,
        "count": restored,
        "previous_status": "Rejected",
        "ids": restored_ids,
    }


# ------------------------------------------------------------
# UNDO REJECTED DAY RESTORE
# ------------------------------------------------------------
@app.post("/rejected/restore/undo")
def undo_restore_rejected_day(payload: RestoreUndoRequest):
    ids = sorted(set(payload.ids))
    if not ids:
        raise HTTPException(status_code=400, detail="At least one id is required")

    placeholders = ",".join("?" for _ in ids)
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(f"""
        UPDATE import_files
        SET review_status = 'Rejected'
        WHERE review_status = 'Pending'
        AND id IN ({placeholders})
    """, ids)

    restored = cur.rowcount
    conn.commit()
    conn.close()

    return {
        "status": "restored",
        "previous_status": "Pending",
        "restored_status": "Rejected",
        "count": restored,
        "ids": ids,
    }


def _latest_keyproof_join_sql():
    return """
        LEFT JOIN keyproof k
            ON k.id = (
                SELECT kp.id
                FROM keyproof kp
                WHERE kp.imported_file_id = import_files.id
                ORDER BY kp.id DESC
                LIMIT 1
            )
    """


def _site_batch_item_rows(cur, batch_number: str):
    cur.execute(
        f"""
        SELECT import_files.id,
               import_files.filename,
               import_files.processed_at,
               import_files.snapshot_path,
               import_files.review_status,
               import_files.review_notes,
               import_files.site,
               import_files.detail,
               import_files.amount,
               import_files.keyproof_total,
               import_files.itemization_total,
               import_files.balsheet_total,
               import_files.balanced,
               import_files.batch_id,
               b.batch_number AS batch_number,
               k.site AS keyproof_site,
               k.misc_description AS keyproof_detail,
               k.subtotal AS keyproof_subtotal,
                (
                    SELECT h.moved_to
                    FROM import_EmailAttachmentHistory h
                   WHERE h.original_filename = import_files.filename
                     AND h.moved_to IS NOT NULL
                     AND h.moved_to != ''
                   ORDER BY h.id DESC
                   LIMIT 1
               ) AS original_path
        FROM import_files
        LEFT JOIN import_batches b
            ON b.id = import_files.batch_id
        {_latest_keyproof_join_sql()}
        WHERE b.batch_number = ?
        ORDER BY import_files.id ASC
        """,
        (batch_number,),
    )
    return cur.fetchall()


@app.get("/site/batches")
def get_site_batches():
    conn = get_conn()
    cur = conn.cursor()
    ensure_approved_keyproof_columns(conn)

    cur.execute(
        f"""
        SELECT import_files.batch_id,
               COALESCE(b.batch_number, 'Unknown') AS batch_number,
               COUNT(*) AS item_count,
               SUM(CASE WHEN import_files.review_status = 'Approved' THEN 1 ELSE 0 END) AS approved_count,
               SUM(CASE WHEN import_files.review_status = 'Rejected' THEN 1 ELSE 0 END) AS rejected_count,
               SUM(CASE WHEN import_files.review_status = 'Pending' THEN 1 ELSE 0 END) AS pending_count,
               MIN(import_files.processed_at) AS first_day,
               MAX(import_files.processed_at) AS last_day,
               SUM(COALESCE(import_files.amount, 0)) AS amount_total,
               SUM(COALESCE(import_files.balsheet_total, 0)) AS balsheet_total,
               SUM(COALESCE(import_files.keyproof_total, 0)) AS keyproof_total,
                MAX(import_files.site) AS site,
                MAX(k.site) AS keyproof_site,
                MAX(k.misc_description) AS keyproof_detail
        FROM import_files
        LEFT JOIN import_batches b
            ON b.id = import_files.batch_id
        {_latest_keyproof_join_sql()}
        GROUP BY import_files.batch_id, COALESCE(b.batch_number, 'Unknown')
        ORDER BY last_day DESC, batch_number DESC
        """
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "batch_id": row["batch_id"],
            "batch_number": row["batch_number"],
            "item_count": row["item_count"] or 0,
            "approved_count": row["approved_count"] or 0,
            "rejected_count": row["rejected_count"] or 0,
            "pending_count": row["pending_count"] or 0,
            "first_day": row["first_day"],
            "last_day": row["last_day"],
            "amount_total": row["amount_total"] or 0,
            "balsheet_total": row["balsheet_total"] or 0,
            "keyproof_total": row["keyproof_total"] or 0,
            "site": row["site"],
            "keyproof_site": row["keyproof_site"],
            "keyproof_detail": row["keyproof_detail"],
            "outcome": "Rejected"
            if (row["rejected_count"] or 0) > 0
            else ("Approved" if (row["approved_count"] or 0) > 0 and (row["pending_count"] or 0) == 0 else "Pending"),
        }
        for row in rows
    ]


@app.get("/site/batches/{batch_number}")
def get_site_batch(batch_number: str):
    conn = get_conn()
    cur = conn.cursor()
    ensure_approved_keyproof_columns(conn)

    rows = _site_batch_item_rows(cur, batch_number)
    if not rows:
        conn.close()
        raise HTTPException(status_code=404, detail="Site batch not found")

    cur.execute(
        """
        SELECT id, source_filename, batch_id, batch_number, batch_day, location, total_amount,
               payment_plans_amount, ar_collections_amount, imported_at
        FROM site_cc_reports
        WHERE batch_number = ?
        ORDER BY imported_at DESC, id DESC
        LIMIT 1
        """,
        (batch_number,),
    )
    flywire_report = cur.fetchone()
    flywire_rows = []
    if flywire_report:
        cur.execute(
            """
            SELECT row_number, location, department, payment_method, payment_type, payment_time, amount,
                   transaction_id, account_number, guarantor_name, billing_name, application
            FROM site_cc_report_rows
            WHERE report_id = ?
            ORDER BY row_number ASC
            """,
            (flywire_report["id"],),
        )
        flywire_rows = cur.fetchall()
    conn.close()

    items = []
    for row in rows:
        review_status = row["review_status"] or "Pending"
        outcome = "rejected" if review_status == "Rejected" else ("accepted" if review_status == "Approved" else "pending")
        items.append(
            {
                "id": row["id"],
                "filename": row["filename"],
                "processed_at": row["processed_at"],
                "snapshot_path": row["snapshot_path"],
                "review_status": review_status,
                "review_notes": row["review_notes"] or "",
                "site": row["site"] or row["keyproof_site"],
                "detail": row["detail"] or row["keyproof_detail"] or "",
                "amount": row["amount"] or row["keyproof_subtotal"] or 0,
                "keyproof_site": row["keyproof_site"] or row["site"],
                "keyproof_detail": row["keyproof_detail"] or "",
                "keyproof_total": row["keyproof_total"] or row["keyproof_subtotal"] or 0,
                "itemization_total": row["itemization_total"] or 0,
                "balsheet_total": row["balsheet_total"] or 0,
                "balanced": bool(row["balanced"]) if row["balanced"] is not None else None,
                "batch_id": row["batch_id"],
                "batch_number": row["batch_number"],
                "original_path": row["original_path"] or "",
                "outcome": outcome,
            }
        )

    return {
        "batch_number": batch_number,
        "batch_id": items[0]["batch_id"],
        "item_count": len(items),
        "approved_count": sum(1 for item in items if item["review_status"] == "Approved"),
        "rejected_count": sum(1 for item in items if item["review_status"] == "Rejected"),
        "pending_count": sum(1 for item in items if item["review_status"] == "Pending"),
        "items": items,
        "flywire_report": None
        if not flywire_report
        else {
            "id": flywire_report["id"],
            "source_filename": flywire_report["source_filename"],
            "batch_day": flywire_report["batch_day"],
            "location": flywire_report["location"],
            "total_amount": flywire_report["total_amount"] or 0,
            "payment_plans_amount": flywire_report["payment_plans_amount"] or 0,
            "ar_collections_amount": flywire_report["ar_collections_amount"] or 0,
            "rows": [
                {
                    "row_number": row["row_number"],
                    "location": row["location"],
                    "department": row["department"],
                    "payment_method": row["payment_method"],
                    "payment_type": row["payment_type"],
                    "payment_time": row["payment_time"],
                    "amount": row["amount"] or 0,
                    "transaction_id": row["transaction_id"],
                    "account_number": row["account_number"],
                    "guarantor_name": row["guarantor_name"],
                    "billing_name": row["billing_name"],
                    "application": row["application"],
                }
                for row in flywire_rows
            ],
        },
    }


@app.get("/site/batches/{batch_number}/flywire")
def get_site_batch_flywire(batch_number: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source_filename
        FROM site_cc_reports
        WHERE batch_number = ?
        ORDER BY imported_at DESC, id DESC
        LIMIT 1
        """,
        (batch_number,),
    )
    report = cur.fetchone()
    conn.close()

    if not report or not report[0]:
        raise HTTPException(status_code=404, detail="Flywire report not found for batch")

    filename = report[0]
    path = os.path.join(SITES_FOLDER, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Flywire report file missing")

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
        content_disposition_type="inline",
    )


# ------------------------------------------------------------
# REJECT FILE
# ------------------------------------------------------------
@app.post("/attachments/{attachment_id}/reject")
def reject_attachment(attachment_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE import_files
        SET review_status = 'Rejected'
        WHERE id = ?
    """, (attachment_id,))

    conn.commit()
    conn.close()

    return {"status": "rejected", "id": attachment_id}


# ------------------------------------------------------------
# RESET ALL TO PENDING
# ------------------------------------------------------------
@app.post("/reset")
def reset_all():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE import_files
        SET review_status = 'Pending'
    """)

    conn.commit()
    conn.close()

    return {"status": "reset_all"}


# ------------------------------------------------------------
# PENDING FILES GROUPED BY PROCESSED_AT
# ------------------------------------------------------------
@app.get("/pending/by-day")
def get_pending_by_day():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, processed_at, snapshot_path, site, detail, amount
        FROM import_files
        WHERE review_status = 'Pending'
        ORDER BY processed_at ASC, id ASC
    """)
    rows = cur.fetchall()
    conn.close()

    grouped = {}

    for (
        file_id,
        filename,
        processed_at,
        snapshot_path,
        site,
        detail,
        amount,
    ) in rows:
        day = processed_at or "Unknown"

        if day not in grouped:
            grouped[day] = []

        grouped[day].append({
            "id": file_id,
            "filename": filename,
            "snapshot_path": snapshot_path,
            "site": site,
            "detail": detail,
            "amount": amount,
        })

    return grouped


# ------------------------------------------------------------
# SITES
# ------------------------------------------------------------
@app.get("/sites")
def get_sites():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, name, description, active FROM sites ORDER BY name;")
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "active": r[3],
        }
        for r in rows
    ]


@app.post("/sites")
def add_site(site: dict):
    name = site.get("name")
    description = site.get("description", "")

    if not name:
        raise HTTPException(status_code=400, detail="Site name is required")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO sites (name, description, active) VALUES (?, ?, 1);",
            (name, description),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Site already exists")

    conn.close()
    return {"status": "ok", "message": "Site added"}


@app.put("/sites/{site_id}")
def update_site(site_id: int, site: dict):
    name = site.get("name")
    description = site.get("description")
    active = site.get("active")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM sites WHERE id = ?;", (site_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Site not found")

    cur.execute(
        "UPDATE sites SET name = ?, description = ?, active = ? WHERE id = ?;",
        (name, description, active, site_id),
    )

    conn.commit()
    conn.close()

    return {"status": "ok", "message": "Site updated"}


@app.delete("/sites/{site_id}")
def delete_site(site_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM sites WHERE id = ?;", (site_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Site not found")

    cur.execute("DELETE FROM sites WHERE id = ?;", (site_id,))
    conn.commit()
    conn.close()

    return {"status": "ok", "message": "Site deleted"}


# ------------------------------------------------------------
# KEYPROOF
# ------------------------------------------------------------
@app.get("/keyproof")
def get_keyproof_records(posting_day: Optional[str] = None):
    conn = get_conn()
    cur = conn.cursor()
    ensure_keyproof_columns(conn)

    if posting_day:
        cur.execute(
            """
            SELECT id, imported_file_id, posting_day, site, cash, check_amount, credit_card, lockbox, eft,
                   misc, misc_description, foreign_check, wire_transfer, subtotal, balanced, itemization_complete,
                   created_at, updated_at
            FROM keyproof
            WHERE posting_day = ?
            ORDER BY id DESC
            """,
            (normalize_balsheet_date(posting_day) or posting_day,),
        )
    else:
        cur.execute(
            """
            SELECT id, imported_file_id, posting_day, site, cash, check_amount, credit_card, lockbox, eft,
                   misc, misc_description, foreign_check, wire_transfer, subtotal, balanced, itemization_complete,
                   created_at, updated_at
            FROM keyproof
            ORDER BY id DESC
            """
        )

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "imported_file_id": row[1],
            "posting_day": row[2],
            "site": row[3],
            "cash": row[4] or 0,
            "check_amount": row[5] or 0,
            "credit_card": row[6] or 0,
            "lockbox": row[7] or 0,
            "eft": row[8] or 0,
            "misc": row[9] or 0,
            "misc_description": row[10] or "",
            "foreign_check": row[11] or 0,
            "wire_transfer": row[12] or 0,
            "subtotal": row[13] or 0,
            "balanced": bool(row[14]) if row[14] is not None else None,
            "itemization_complete": bool(row[15]) if row[15] is not None else None,
            "created_at": row[16],
            "updated_at": row[17],
        }
        for row in rows
    ]


@app.post("/keyproof")
def save_keyproof(payload: KeyproofSaveRequest):
    posting_day = normalize_balsheet_date(payload.posting_day) or payload.posting_day or get_current_workday()

    for attempt in range(3):
        try:
            return _save_keyproof_once(payload, posting_day)
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "locked" not in message and "busy" not in message:
                raise
            if attempt == 2:
                raise HTTPException(
                    status_code=503,
                    detail="Keyproof save is temporarily busy. Please try again in a moment.",
                ) from exc
            time.sleep(0.15 * (attempt + 1))


# ------------------------------------------------------------
# BALSHEET
# ------------------------------------------------------------
def get_current_workday():
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT current_work_day FROM work_state WHERE id = 1").fetchone()
    conn.close()

    if row and row[0]:
        return normalize_balsheet_date(row[0]) or row[0]

    return datetime.now().strftime("%m/%d/%Y")


def normalize_balsheet_date(value: str):
    if not value:
        return None

    cleaned = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d", "%m-%d-%Y", "%m-%d-%y"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%m/%d/%Y")
        except ValueError:
            pass

    return cleaned


def parse_mmddyyyy(value):
    normalized = normalize_balsheet_date(value)
    if not normalized:
        return None

    try:
        return datetime.strptime(normalized, "%m/%d/%Y")
    except ValueError:
        return None


def max_mmddyyyy(values):
    dated = [(parse_mmddyyyy(value), normalize_balsheet_date(value)) for value in values if value]
    dated = [(parsed, normalized) for parsed, normalized in dated if parsed and normalized]

    if not dated:
        return None

    dated.sort(key=lambda item: item[0], reverse=True)
    return dated[0][1]


def month_bounds_from_yyyy_mm(value: Optional[str]):
    if not value:
        return None

    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError:
        return None

    next_month = (parsed.replace(day=28) + timedelta(days=4)).replace(day=1)
    return parsed.replace(day=1), next_month - timedelta(days=1)


def parse_amount(value):
    try:
        if value is None or value == "":
            return 0.0
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def get_daily_bank_balances(conn, start=None, end=None):
    start_date = parse_mmddyyyy(start) if start else None
    end_date = parse_mmddyyyy(end) if end else None
    balances = {}

    def include_date(value):
        parsed = parse_mmddyyyy(value)
        if not parsed:
            return True
        if start_date and parsed < start_date:
            return False
        if end_date and parsed > end_date:
            return False
        return True

    def ensure_row(date):
        if date not in balances:
            balances[date] = {"date": date, "eft": 0.0, "lockbox": 0.0}
        return balances[date]

    eft_rows = conn.execute("""
        SELECT Date AS balance_date,
               Amount AS amount
        FROM EFT
    """).fetchall()

    for row in eft_rows:
        date = normalize_balsheet_date(row["balance_date"]) or row["balance_date"] or "Unknown"
        if not include_date(date):
            continue
        ensure_row(date)["eft"] += parse_amount(row["amount"])

    lockbox_rows = conn.execute("""
        SELECT [Deposit Date] AS balance_date,
               [Transaction Total] AS amount
        FROM Lockbox
    """).fetchall()

    for row in lockbox_rows:
        date = normalize_balsheet_date(row["balance_date"]) or row["balance_date"] or "Unknown"
        if not include_date(date):
            continue
        ensure_row(date)["lockbox"] += parse_amount(row["amount"])

    rows = []
    for balance in balances.values():
        eft_total = round(balance["eft"], 2)
        lockbox_total = round(balance["lockbox"], 2)
        rows.append({
            "date": balance["date"],
            "eft": eft_total,
            "lockbox": lockbox_total,
            "total": round(lockbox_total + eft_total, 2),
        })

    rows.sort(key=lambda row: parse_mmddyyyy(row["date"]) or datetime.max)
    return rows


def get_posting_items_summary(conn, workday):
    posting_date = normalize_balsheet_date(workday)
    if not posting_date:
        return None

    bank_row = conn.execute(
        "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
        (posting_date,),
    ).fetchone()
    if not bank_row or not bank_row[0]:
        return {
            "posting_date": posting_date,
            "bank_day": None,
            "lockbox": {"total": 0, "count": 0, "edi_count": 0},
            "eft": {"total": 0, "count": 0, "edi_count": 0},
            "edi_match": {"total": 0, "count": 0},
            "matched": False,
            "difference": 0,
        }

    bank_day = normalize_balsheet_date(bank_row[0]) or bank_row[0]

    edi_checks = set()
    try:
        rows = conn.execute("""
            SELECT edi_check
            FROM MatchResults
            WHERE match_date = ?
              AND (eft_amount > 0 OR lockbox_amount > 0)
        """, (bank_day,)).fetchall()
        edi_checks = {str(row[0]).strip() for row in rows if row[0]}
    except sqlite3.Error:
        edi_checks = set()

    lockbox_total = 0.0
    lockbox_count = 0
    lockbox_edi_count = 0
    try:
        rows = conn.execute("""
            SELECT [Check Number] AS check_number,
                   [Transaction Total] AS amount,
                   [Deposit Date] AS deposit_date
            FROM Lockbox
        """).fetchall()
        for row in rows:
            if normalize_balsheet_date(row["deposit_date"]) != bank_day:
                continue
            amount = parse_amount(row["amount"])
            check_number = str(row["check_number"]).strip() if row["check_number"] else ""
            lockbox_total += amount
            lockbox_count += 1
            if check_number in edi_checks:
                lockbox_edi_count += 1
    except sqlite3.Error:
        pass

    eft_total = 0.0
    eft_count = 0
    eft_edi_count = 0
    try:
        rows = conn.execute("""
            SELECT Date AS as_of_date,
                   Amount AS credit_amt,
                   CheckNumber AS check_number
            FROM EFT
        """).fetchall()
        for row in rows:
            if normalize_balsheet_date(row["as_of_date"]) != bank_day:
                continue
            amount = parse_amount(row["credit_amt"])
            check_number = str(row["check_number"]).strip() if row["check_number"] else ""
            eft_total += amount
            eft_count += 1
            if check_number in edi_checks:
                eft_edi_count += 1
    except sqlite3.Error:
        pass

    edi_match_total = 0.0
    edi_match_count = 0
    try:
        rows = conn.execute("""
            SELECT edi_amount
            FROM MatchResults
            WHERE match_date = ?
              AND (COALESCE(lockbox_amount, 0) != 0 OR COALESCE(eft_amount, 0) != 0)
        """, (bank_day,)).fetchall()
        for row in rows:
            edi_match_total += parse_amount(row["edi_amount"])
            edi_match_count += 1
    except sqlite3.Error:
        pass

    difference = lockbox_total - eft_total

    return {
        "posting_date": posting_date,
        "bank_day": bank_day,
        "lockbox": {
            "total": round(lockbox_total, 2),
            "count": lockbox_count,
            "edi_count": lockbox_edi_count,
        },
        "eft": {
            "total": round(eft_total, 2),
            "count": eft_count,
            "edi_count": eft_edi_count,
        },
        "edi_match": {
            "total": round(edi_match_total, 2),
            "count": edi_match_count,
        },
        "matched": abs(difference) < 0.005,
        "difference": round(difference, 2),
    }


def get_posting_items_detail(conn, workday):
    summary = get_posting_items_summary(conn, workday)
    if not summary or not summary["bank_day"]:
        return summary

    bank_day = summary["bank_day"]

    edi_checks = set()
    try:
        rows = conn.execute("""
            SELECT edi_check
            FROM MatchResults
            WHERE match_date = ?
              AND (eft_amount > 0 OR lockbox_amount > 0)
        """, (bank_day,)).fetchall()
        edi_checks = {str(row[0]).strip() for row in rows if row[0]}
    except sqlite3.Error:
        edi_checks = set()

    lockbox_rows = []
    try:
        rows = conn.execute("""
            SELECT id,
                   [Transaction Number] AS transaction_number,
                   Status AS status,
                   Note AS note,
                   [Transaction Total] AS amount,
                   [Deposit Date] AS deposit_date,
                   [Batch Number] AS batch_number,
                   [Check Number] AS check_number,
                   [Check Amount] AS check_amount,
                   Site AS site,
                   Lockbox AS lockbox,
                   Payor AS payor,
                   Sequence AS sequence,
                   [Number of Items] AS number_of_items
            FROM Lockbox
        """).fetchall()
        for row in rows:
            if normalize_balsheet_date(row["deposit_date"]) != bank_day:
                continue
            check_number = str(row["check_number"]).strip() if row["check_number"] else ""
            lockbox_rows.append({
                "row_key": f"lockbox:{row['id']}",
                "id": row["id"],
                "transaction_number": row["transaction_number"] or "",
                "status": row["status"] or "",
                "note": row["note"] or "",
                "amount": parse_amount(row["amount"]),
                "deposit_date": normalize_balsheet_date(row["deposit_date"]) or row["deposit_date"] or "",
                "batch_number": row["batch_number"] or "",
                "check_number": check_number,
                "check_amount": row["check_amount"] or "",
                "site": row["site"] or "",
                "lockbox": row["lockbox"] or "",
                "payor": row["payor"] or "",
                "sequence": row["sequence"] or "",
                "number_of_items": row["number_of_items"] or "",
                "edi": check_number in edi_checks,
            })
    except sqlite3.Error:
        lockbox_rows = []

    eft_rows = []
    try:
        rows = conn.execute("""
            SELECT rowid AS row_id,
                   Date AS as_of_date,
                   Amount AS credit_amt,
                   CheckNumber AS check_number,
                   Payer AS payer_name
            FROM EFT
        """).fetchall()
        for row in rows:
            if normalize_balsheet_date(row["as_of_date"]) != bank_day:
                continue
            check_number = str(row["check_number"]).strip() if row["check_number"] else ""
            payer = str(row["payer_name"]).strip() if row["payer_name"] else ""
            eft_rows.append({
                "row_key": f"eft:{row['row_id']}",
                "row_id": row["row_id"],
                "date": normalize_balsheet_date(row["as_of_date"]) or row["as_of_date"] or "",
                "amount": parse_amount(row["credit_amt"]),
                "check_number": check_number,
                "payer": payer,
                "edi": check_number in edi_checks,
            })
    except sqlite3.Error:
        eft_rows = []

    edi_match_rows = []
    try:
        rows = conn.execute("""
            SELECT id, edi_check, edi_amount, lockbox_amount, eft_amount, match_date, created_at
            FROM MatchResults
            WHERE match_date = ?
              AND (COALESCE(lockbox_amount, 0) != 0 OR COALESCE(eft_amount, 0) != 0)
        """, (bank_day,)).fetchall()
        for row in rows:
            edi_match_rows.append({
                "row_key": f"edi-match:{row['id']}",
                "id": row["id"],
                "amount": parse_amount(row["edi_amount"]),
                "check_number": str(row["edi_check"]).strip() if row["edi_check"] else "",
                "edi_check": str(row["edi_check"]).strip() if row["edi_check"] else "",
                "edi_amount": parse_amount(row["edi_amount"]),
                "lockbox_amount": parse_amount(row["lockbox_amount"]),
                "eft_amount": parse_amount(row["eft_amount"]),
                "match_date": normalize_balsheet_date(row["match_date"]) if row["match_date"] else "",
                "created_at": row["created_at"] or "",
            })
    except sqlite3.Error:
        edi_match_rows = []

    lockbox_rows.sort(key=lambda row: row["amount"], reverse=True)
    eft_rows.sort(key=lambda row: row["payer"].lower())
    edi_match_rows.sort(key=lambda row: row["amount"], reverse=True)

    return {
        **summary,
        "rows": {
            "lockbox": lockbox_rows,
            "eft": eft_rows,
            "edi_match": edi_match_rows,
        },
    }


def next_balsheet_entry_id(conn, posting_date: str):
    date_key = "".join(ch for ch in posting_date if ch.isdigit())
    row = conn.execute("SELECT GenID FROM ControlsTools WHERE id = 1").fetchone()

    if row is None:
        current_seq = 0
        conn.execute("INSERT INTO ControlsTools (id, GenID) VALUES (1, 0)")
    else:
        current_seq = row["GenID"]

    next_seq = current_seq + 1
    conn.execute("UPDATE ControlsTools SET GenID = ? WHERE id = 1", (next_seq,))

    return f"{date_key}-{next_seq}"


def normalize_yes_no(value: str):
    cleaned = (value or "").strip().upper()
    if cleaned in ("Y", "YES", "TRUE", "1"):
        return "Y"
    if cleaned in ("N", "NO", "FALSE", "0"):
        return "N"
    return cleaned


def normalize_poster(value: str):
    cleaned = (value or "").strip().upper()
    if cleaned in ("N", "NICK"):
        return "N"
    if cleaned in ("R", "RAUL"):
        return "R"
    return cleaned


def balsheet_payload(entry: BalsheetEntryRequest, entry_id: str, posting_date: str):
    amount = float(entry.amount or 0)
    unposted = float(entry.unposted or 0)
    misc = float(entry.misc or 0)
    poster = normalize_poster(entry.poster)
    edi = normalize_yes_no(entry.edi)
    base = amount - unposted - misc

    nick = entry.nick
    raul = entry.raul

    if nick is None or raul is None:
        if poster == "R":
            nick = 0
            raul = base
        else:
            nick = base
            raul = 0

    return (
        entry_id,
        posting_date,
        entry.type,
        amount,
        entry.payer,
        entry.check_number,
        edi,
        poster,
        entry.eob,
        unposted,
        misc,
        entry.misc_type,
        entry.notes,
        nick,
        raul,
        entry.needs,
        entry.from_date,
        entry.to_date,
    )


def get_bank_day_for_workday(conn, workday: str):
    posting_date = normalize_balsheet_date(workday)
    if not posting_date:
        return None

    row = conn.execute(
        "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
        (posting_date,),
    ).fetchone()

    if row and row[0]:
        return normalize_balsheet_date(row[0]) or row[0]

    return None


def balsheet_day_has_entries(conn, posting_date: str):
    row = conn.execute(
        "SELECT COUNT(*) FROM Balsheet WHERE PostingDate = ?",
        (posting_date,),
    ).fetchone()
    return bool(row and row[0] > 0)


def import_eft_lockbox_rows(
    conn,
    bank_day: str,
    posting_date: Optional[str] = None,
    override_existing: bool = False,
):
    target_posting_date = normalize_balsheet_date(posting_date) or bank_day
    edi_rows = conn.execute("""
        SELECT edi_check
        FROM MatchResults
        WHERE match_date = ?
          AND (eft_amount > 0 OR lockbox_amount > 0)
    """, (bank_day,)).fetchall()
    edi_checks = {normalize_checknum(row["edi_check"]) for row in edi_rows if row["edi_check"]}

    source_rows = []

    lockbox_rows = conn.execute("""
        SELECT [Check Number] AS check_number,
               [Transaction Total] AS amount,
               [Deposit Date] AS deposit_date
        FROM Lockbox
    """).fetchall()
    for row in lockbox_rows:
        if normalize_balsheet_date(row["deposit_date"]) != bank_day:
            continue

        check_number = str(row["check_number"]).strip() if row["check_number"] else ""
        source_rows.append({
            "source": "Lockbox",
            "type": "L",
            "payer": "",
            "check_number": check_number,
            "amount": parse_amount(row["amount"]),
            "edi": normalize_checknum(check_number) in edi_checks,
        })

    eft_rows = conn.execute("""
        SELECT Date AS eft_date,
               Amount AS amount,
               CheckNumber AS check_number,
               Payer AS payer
        FROM EFT
    """).fetchall()
    for row in eft_rows:
        if normalize_balsheet_date(row["eft_date"]) != bank_day:
            continue

        check_number = str(row["check_number"]).strip() if row["check_number"] else ""
        source_rows.append({
            "source": "EFT",
            "type": "E",
            "payer": str(row["payer"]).strip() if row["payer"] else "",
            "check_number": check_number,
            "amount": parse_amount(row["amount"]),
            "edi": normalize_checknum(check_number) in edi_checks,
        })

    posted = []
    skipped = []

    for source in source_rows:
        existing = conn.execute("""
            SELECT EntryID
            FROM Balsheet
            WHERE Amount = ?
              AND Payer = ?
              AND "Check Number" = ?
              AND PostingDate = ?
        """, (
            source["amount"],
            source["payer"],
            source["check_number"],
            target_posting_date,
        )).fetchone()

        if existing and not override_existing:
            skipped.append({
                "source": source["source"],
                "payer": source["payer"],
                "check_number": source["check_number"],
                "amount": source["amount"],
                "reason": "duplicate",
            })
            continue

        entry_id = next_balsheet_entry_id(conn, target_posting_date)
        edi = "Y" if source["edi"] else "N"
        poster = "R" if source["edi"] else "N"
        nick = 0 if source["edi"] else source["amount"]
        raul = source["amount"] if source["edi"] else 0

        conn.execute("""
            INSERT INTO Balsheet (
                EntryID, PostingDate, Type, Amount, Payer, "Check Number",
                EDI, Poster, EOB, UnPosted, Misc, "Misc-Type", Notes,
                Nick, Raul, Needs, "From", "To"
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id,
            target_posting_date,
            source["type"],
            source["amount"],
            source["payer"],
            source["check_number"],
            edi,
            poster,
            "",
            0.0,
            0.0,
            "",
            (
                f"Imported from EFT/Lockbox override for bank day {bank_day}"
                if override_existing
                else f"Imported from EFT/Lockbox for bank day {bank_day}"
            ),
            nick,
            raul,
            "",
            "",
            "",
        ))
        posted.append({
            "entry_id": entry_id,
            "posting_date": target_posting_date,
            "source": source["source"],
            "payer": source["payer"],
            "check_number": source["check_number"],
            "amount": source["amount"],
            "edi": edi,
            "poster": poster,
        })

    return posted, skipped


@app.get("/balsheet/workday")
def get_balsheet_workday():
    return {"posting_date": get_current_workday()}


@app.get("/balsheet/notes")
def get_balsheet_notes(posting_date: Optional[str] = None):
    day = normalize_balsheet_date(posting_date) or get_current_workday()
    conn = get_conn()
    ensure_balsheet_daynotes_table(conn)
    notes = get_balsheet_day_note(conn, day)
    conn.close()
    return {"posting_date": day, **notes}


@app.post("/balsheet/notes")
def save_balsheet_notes(payload: dict):
    day = normalize_balsheet_date(payload.get("posting_date")) or get_current_workday()
    notes = str(payload.get("notes") or "")
    message = str(payload.get("message") or "")
    conn = get_conn()
    ensure_balsheet_daynotes_table(conn)
    save_balsheet_day_note(conn, day, notes, message)
    conn.commit()
    conn.close()
    return {"status": "ok", "posting_date": day, "has_notes": bool(notes.strip()), "has_message": bool(message.strip())}


@app.post("/dashboard/advance-workday")
def advance_dashboard_workday():
    before = get_current_workday()
    advance_current_work_day()
    after = get_current_workday()

    if before == after:
        raise HTTPException(status_code=404, detail=f"No open work day found after {before}")

    return {
        "status": "advanced",
        "previous_workday": before,
        "posting_date": after,
    }


@app.get("/dashboard/posting-items")
def get_dashboard_posting_items(workday: Optional[str] = None):
    conn = get_conn()
    summary = get_posting_items_summary(conn, workday or get_current_workday())
    conn.close()

    if not summary:
        raise HTTPException(status_code=404, detail="Posting day not found")

    return summary


@app.get("/dashboard/posting-items/details")
def get_dashboard_posting_items_details(workday: Optional[str] = None):
    conn = get_conn()
    detail = get_posting_items_detail(conn, workday or get_current_workday())
    conn.close()

    if not detail:
        raise HTTPException(status_code=404, detail="Posting day not found")

    return detail


@app.get("/dashboard/daily-bank-balances")
def get_dashboard_daily_bank_balances(start: Optional[str] = None, end: Optional[str] = None):
    if start and not parse_mmddyyyy(start):
        raise HTTPException(status_code=400, detail="Start date must be MM/DD/YYYY")
    if end and not parse_mmddyyyy(end):
        raise HTTPException(status_code=400, detail="End date must be MM/DD/YYYY")

    conn = get_conn()
    rows = get_daily_bank_balances(conn, start=start, end=end)
    conn.close()

    return {
        "start": normalize_balsheet_date(start) if start else None,
        "end": normalize_balsheet_date(end) if end else None,
        "count": len(rows),
        "rows": rows,
    }


@app.get("/dashboard/monthly-summary")
def get_dashboard_monthly_summary(month: Optional[str] = None):
    conn = get_conn()
    cur = conn.cursor()

    current_workday = get_current_workday()
    current_date = parse_mmddyyyy(current_workday) or datetime.now()
    month_bounds = month_bounds_from_yyyy_mm(month) or (
        current_date.replace(day=1),
        (current_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
    )
    month_start, month_end = month_bounds
    month_key = month_start.strftime("%Y-%m")
    month_label = month_start.strftime("%B %Y")
    is_current_month = month_start.year == current_date.year and month_start.month == current_date.month

    open_days = []
    calendar_rows = cur.execute(
        """
        SELECT bank_day, paperwork_day, is_closed
        FROM calendar
        WHERE bank_day IS NOT NULL AND bank_day != ''
        """
    ).fetchall()
    for row in calendar_rows:
        bank_day = parse_mmddyyyy(row[0])
        if not bank_day:
            continue
        if bank_day < month_start or bank_day > month_end:
            continue
        if str(row[2]).lower() in {"1", "true", "yes"}:
            continue
        open_days.append(bank_day)

    current_day = parse_mmddyyyy(current_workday) or current_date
    posting_days_left = sum(1 for day in open_days if day > current_day) if is_current_month else len(open_days)

    received_total = 0.0
    try:
        balance_rows = get_daily_bank_balances(
            conn,
            start=month_start.strftime("%m/%d/%Y"),
            end=month_end.strftime("%m/%d/%Y"),
        )
        for row in balance_rows:
            received_total += parse_amount(row.get("total"))
    except Exception:
        received_total = 0.0

    balsheet_total = 0.0
    try:
        rows = cur.execute(
            """
            SELECT Amount
            FROM Balsheet
            WHERE PostingDate >= ? AND PostingDate <= ?
            """,
            (month_start.strftime("%m/%d/%Y"), month_end.strftime("%m/%d/%Y")),
        ).fetchall()
        balsheet_total = sum(parse_amount(row[0]) for row in rows)
    except sqlite3.Error:
        balsheet_total = 0.0

    projected_collections = received_total
    if is_current_month and posting_days_left > 0:
        completed_posting_days = max(1, len(open_days) - posting_days_left)
        projected_collections = round(received_total / completed_posting_days * len(open_days), 2) if completed_posting_days else received_total

    conn.close()

    return {
        "month": month_key,
        "month_label": month_label,
        "is_current_month": is_current_month,
        "received_total": round(received_total, 2),
        "balsheet_total": round(balsheet_total, 2),
        "posting_days_left": posting_days_left,
        "projected_collections": round(projected_collections, 2),
        "open_days": len(open_days),
    }


@app.get("/dashboard/status")
def get_dashboard_status():
    conn = get_conn()
    cur = conn.cursor()

    current_work_row = cur.execute(
        "SELECT current_work_day FROM work_state WHERE id = 1"
    ).fetchone()
    posting_date = normalize_balsheet_date(current_work_row[0]) if current_work_row and current_work_row[0] else None

    bank_day = None
    if posting_date:
        bank_row = cur.execute(
            "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
            (posting_date,),
        ).fetchone()
        bank_day = normalize_balsheet_date(bank_row[0]) if bank_row and bank_row[0] else None

    calendar_dates = [
        row[0]
        for row in cur.execute("SELECT bank_day FROM calendar WHERE bank_day IS NOT NULL AND bank_day != ''").fetchall()
    ]
    highest_calendar_date = max_mmddyyyy(calendar_dates)

    def table_stat(table_name, date_column):
        try:
            rows = cur.execute(
                f'SELECT "{date_column}" FROM "{table_name}" WHERE "{date_column}" IS NOT NULL AND "{date_column}" != ""'
            ).fetchall()
            count = cur.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
            return {
                "last_date": max_mmddyyyy([row[0] for row in rows]),
                "row_count": count,
            }
        except sqlite3.Error:
            return {
                "last_date": None,
                "row_count": 0,
            }

    edi = table_stat("EDI", "check_date")
    lockbox = table_stat("Lockbox", "Deposit Date")
    eft = table_stat("EFT", "Date")
    posting_items = get_posting_items_summary(conn, posting_date)

    conn.close()

    return {
        "posting_date": posting_date,
        "bank_day": bank_day,
        "highest_calendar_date": highest_calendar_date,
        "uploads": {
            "edi": edi,
            "lockbox": lockbox,
            "eft": eft,
        },
        "posting_items": posting_items,
    }


@app.get("/eft/latest-date")
def get_eft_latest_date():
    conn = get_conn()
    cur = conn.cursor()
    try:
        rows = cur.execute(
            'SELECT "Date" FROM "EFT" WHERE "Date" IS NOT NULL AND "Date" != ""'
        ).fetchall()
        latest_date = max_mmddyyyy([row[0] for row in rows])
        return {"latest_date": latest_date}
    finally:
        conn.close()


@app.get("/lockbox/latest-date")
def get_lockbox_latest_date():
    conn = get_conn()
    cur = conn.cursor()
    try:
        rows = cur.execute(
            'SELECT "Deposit Date" FROM "Lockbox" WHERE "Deposit Date" IS NOT NULL AND "Deposit Date" != ""'
        ).fetchall()
        latest_date = max_mmddyyyy([row[0] for row in rows])
        return {"latest_date": latest_date}
    finally:
        conn.close()


@app.get("/edi/latest-date")
def get_edi_latest_date():
    conn = get_conn()
    cur = conn.cursor()
    try:
        rows = cur.execute(
            'SELECT "check_date" FROM "EDI" WHERE "check_date" IS NOT NULL AND "check_date" != ""'
        ).fetchall()
        latest_date = max_mmddyyyy([row[0] for row in rows])
        return {"latest_date": latest_date}
    finally:
        conn.close()


@app.post("/edi/preview-selected")
async def preview_selected_edi_archives_endpoint(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Please select one or more zip files")

    temp_files: list[tuple[str, str]] = []
    try:
        for file in files:
            file_name = file.filename or ""
            if not file_name.lower().endswith(".zip"):
                raise HTTPException(status_code=400, detail="Please select zip files only")

            suffix = os.path.splitext(file_name)[1] or ".zip"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                shutil.copyfileobj(file.file, temp_file)
                temp_files.append((temp_file.name, file_name))

        result = preview_selected_edi_archives(
            [temp_path for temp_path, _ in temp_files],
            [file_name for _, file_name in temp_files],
        )
        return result
    finally:
        for file in files:
            await file.close()
        for temp_path, _ in temp_files:
            if os.path.exists(temp_path):
                os.remove(temp_path)


@app.post("/edi/upload-selected")
async def upload_selected_edi_archives_endpoint(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Please select one or more zip files")

    temp_files: list[tuple[str, str]] = []
    try:
        for file in files:
            file_name = file.filename or ""
            if not file_name.lower().endswith(".zip"):
                raise HTTPException(status_code=400, detail="Please select zip files only")

            suffix = os.path.splitext(file_name)[1] or ".zip"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                shutil.copyfileobj(file.file, temp_file)
                temp_files.append((temp_file.name, file_name))

        result = load_selected_edi_archives(
            [temp_path for temp_path, _ in temp_files],
            [file_name for _, file_name in temp_files],
        )
        return {
            "message": f"Processed {result['totals']['archives']} zip file(s) into the workflow folders.",
            "totals": result["totals"],
            "archives": result["archives"],
        }
    finally:
        for file in files:
            await file.close()
        for temp_path, _ in temp_files:
            if os.path.exists(temp_path):
                os.remove(temp_path)


@app.get("/edi/trn-queue")
def get_edi_trn_queue():
    files = list_queued_trn_files()
    return {"count": len(files), "files": files}


@app.post("/edi/load-trn-queue")
def load_edi_trn_queue_endpoint():
    result = load_trn_queue_to_ediload()
    return {
        "message": f"Loaded {result['row_count']} TRN row(s) into EDILoad from {len(result['loaded_files'])} file(s).",
        "file_count": result["file_count"],
        "row_count": result["row_count"],
        "loaded_files": result["loaded_files"],
        "skipped_files": result["skipped_files"],
        "duplicate_rows": result["duplicate_rows"],
        "batchnum": result["batchnum"],
        "first_transnum": result["first_transnum"],
        "last_transnum": result["last_transnum"],
        "timestamp": result["timestamp"],
    }


@app.post("/edi/stage")
def stage_edi_rows():
    return stage_ediload_rows()


@app.post("/edi/prepare-vetting")
def prepare_edi_vetting_endpoint():
    return prepare_edi_vetting()


@app.post("/edi/confirm-import")
def confirm_edi_import_endpoint(payload: EdiImportRequest | None = None):
    result = confirm_edi_import(accept_non_duplicates=bool(payload.accept_non_duplicates) if payload else False)
    if not result.get("can_import", False):
        raise HTTPException(status_code=400, detail=result)
    return result


@app.post("/edi/reset-working-tables")
def reset_edi_work_tables_endpoint():
    return reset_edi_work_tables()


@app.post("/lockbox/upload-selected")
async def upload_selected_lockbox_report(file: UploadFile = File(...)):
    file_name = file.filename or ""
    if not file_name.lower().startswith("searchresults"):
        raise HTTPException(status_code=400, detail="Please select a file that starts with SearchResults")

    suffix = os.path.splitext(file_name)[1] or ".xls"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        result = load_selected_lockbox_report(temp_path, file_name)
        return {
            "message": f"Loaded {result['row_count']} row(s) into LockboxLoad from {result['file_name']}.",
            "file_name": result["file_name"],
            "row_count": result["row_count"],
        }
    finally:
        await file.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/lockbox/stage")
def stage_lockbox_rows():
    return stage_lockboxload_rows()


@app.post("/lockbox/prepare-vetting")
def prepare_lockbox_vetting_endpoint():
    return prepare_lockbox_vetting()


@app.post("/lockbox/confirm-import")
def confirm_lockbox_import_endpoint():
    result = confirm_lockbox_import()
    if not result.get("can_import", False):
        raise HTTPException(status_code=400, detail=result)
    return result


@app.post("/lockbox/preview-selected")
async def preview_selected_lockbox_report_endpoint(file: UploadFile = File(...)):
    file_name = file.filename or ""
    if not file_name.lower().startswith("searchresults"):
        raise HTTPException(status_code=400, detail="Please select a file that starts with SearchResults")

    suffix = os.path.splitext(file_name)[1] or ".xls"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        result = preview_selected_lockbox_report(temp_path, file_name)
        return {
            "file_name": result["file_name"],
            "row_count": result["row_count"],
        }
    finally:
        await file.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/eft/upload-selected")
async def upload_selected_eft_report(file: UploadFile = File(...)):
    file_name = file.filename or ""
    if not file_name.lower().startswith("dep_1101_tran"):
        raise HTTPException(status_code=400, detail="Please select a file that starts with Dep_1101_TRAN")

    suffix = os.path.splitext(file_name)[1] or ".xlsx"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        result = load_selected_eft_report(temp_path, file_name)
        return {
            "message": f"Loaded {result['row_count']} row(s) into EFTload from {result['file_name']}.",
            "file_name": result["file_name"],
            "row_count": result["row_count"],
            "first_date": result["first_date"],
            "last_date": result["last_date"],
        }
    finally:
        await file.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/eft/preview-selected")
async def preview_selected_eft_report_endpoint(file: UploadFile = File(...)):
    file_name = file.filename or ""
    if not file_name.lower().startswith("dep_1101_tran"):
        raise HTTPException(status_code=400, detail="Please select a file that starts with Dep_1101_TRAN")

    suffix = os.path.splitext(file_name)[1] or ".xlsx"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        result = preview_selected_eft_report(temp_path, file_name)
        return {
            "file_name": result["file_name"],
            "row_count": result["row_count"],
            "first_date": result["first_date"],
            "last_date": result["last_date"],
        }
    finally:
        await file.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/eft/prepare-vetting")
def prepare_eft_vetting_endpoint():
    return prepare_eft_vetting()


@app.post("/eft/confirm-import")
def confirm_eft_import_endpoint():
    result = confirm_eft_import()
    if not result.get("can_import", False):
        raise HTTPException(status_code=400, detail=result)
    return result


@app.get("/calendar/range")
def get_calendar_range(start: Optional[str] = None, end: Optional[str] = None):
    conn = get_conn()
    cur = conn.cursor()

    current_work_row = cur.execute(
        "SELECT current_work_day FROM work_state WHERE id = 1"
    ).fetchone()
    current_work_day = normalize_balsheet_date(current_work_row[0]) if current_work_row and current_work_row[0] else None
    start_date = parse_mmddyyyy(start) if start else None
    end_date = parse_mmddyyyy(end) if end else None

    if start and not start_date:
        conn.close()
        raise HTTPException(status_code=400, detail="Start date must be MM/DD/YYYY")

    if end and not end_date:
        conn.close()
        raise HTTPException(status_code=400, detail="End date must be MM/DD/YYYY")

    rows = cur.execute("""
        SELECT bank_day, weekday, is_closed, closure_reason, paperwork_day
        FROM calendar
    """).fetchall()
    conn.close()

    normalized_rows = []
    for row in rows:
        bank_day = normalize_balsheet_date(row[0])
        bank_date = parse_mmddyyyy(bank_day)
        if not bank_day or not bank_date:
            continue

        if start_date and bank_date < start_date:
            continue

        if end_date and bank_date > end_date:
            continue

        paperwork_day = normalize_balsheet_date(row[4]) if row[4] else None
        normalized_rows.append({
            "bank_day": bank_day,
            "weekday": row[1] or "",
            "is_closed": bool(row[2]),
            "closure_reason": row[3] or "",
            "paperwork_day": paperwork_day,
            "is_current_work_day": bool(current_work_day and paperwork_day == current_work_day),
        })

    normalized_rows.sort(key=lambda item: parse_mmddyyyy(item["bank_day"]) or datetime.min)

    if not start_date and not end_date:
        normalized_rows = normalized_rows[:30]

    return {
        "start": normalize_balsheet_date(start) if start else None,
        "end": normalize_balsheet_date(end) if end else None,
        "current_work_day": current_work_day,
        "rows": normalized_rows,
    }


@app.put("/calendar/range")
def update_calendar_row(payload: CalendarUpdateRequest):
    bank_day = normalize_balsheet_date(payload.bank_day)
    if not bank_day:
        raise HTTPException(status_code=400, detail="Bank day must be MM/DD/YYYY")

    paperwork_day = normalize_balsheet_date(payload.paperwork_day) if payload.paperwork_day else None
    closure_reason = (payload.closure_reason or "").strip()
    if not payload.is_closed:
        closure_reason = ""

    conn = get_conn()
    try:
        cur = conn.cursor()
        existing = cur.execute(
            "SELECT bank_day FROM calendar WHERE bank_day = ?",
            (bank_day,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Calendar day not found")

        cur.execute(
            """
            UPDATE calendar
            SET is_closed = ?, closure_reason = ?, paperwork_day = ?
            WHERE bank_day = ?
            """,
            (1 if payload.is_closed else 0, closure_reason, paperwork_day, bank_day),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "status": "ok",
        "bank_day": bank_day,
        "is_closed": payload.is_closed,
        "closure_reason": closure_reason,
        "paperwork_day": paperwork_day,
    }


@app.get("/exports/edi-match-results")
def get_edi_match_results(match_date: Optional[str] = None, limit: int = 500):
    conn = get_conn()
    cur = conn.cursor()
    where_clauses = ["(COALESCE(lockbox_amount, 0) != 0 OR COALESCE(eft_amount, 0) != 0)"]
    params = []

    if match_date:
        normalized_date = normalize_balsheet_date(match_date)
        if not normalized_date:
            conn.close()
            raise HTTPException(status_code=400, detail="Match date must be MM/DD/YYYY")
        where_clauses.append("match_date = ?")
        params.append(normalized_date)

    where_sql = "WHERE " + " AND ".join(where_clauses)

    try:
        rows = cur.execute(f"""
            SELECT id, edi_check, edi_amount, lockbox_amount, eft_amount, match_date, created_at
            FROM MatchResults
            {where_sql}
            ORDER BY match_date DESC, id DESC
            LIMIT ?
        """, [*params, limit]).fetchall()

        total_row = cur.execute(f"""
            SELECT COUNT(*), COALESCE(SUM(edi_amount), 0), COALESCE(SUM(lockbox_amount), 0), COALESCE(SUM(eft_amount), 0)
            FROM MatchResults
            {where_sql}
        """, params).fetchone()
    except sqlite3.OperationalError as exc:
        conn.close()
        raise HTTPException(status_code=404, detail="MatchResults table is not available. Run rebuild-edi first.") from exc

    conn.close()

    return {
        "match_date": normalize_balsheet_date(match_date) if match_date else None,
        "limit": limit,
        "count": total_row[0] if total_row else 0,
        "totals": {
            "edi_amount": total_row[1] if total_row else 0,
            "lockbox_amount": total_row[2] if total_row else 0,
            "eft_amount": total_row[3] if total_row else 0,
        },
        "rows": [
            {
                "id": row[0],
                "edi_check": row[1] or "",
                "edi_amount": row[2] or 0,
                "lockbox_amount": row[3] or 0,
                "eft_amount": row[4] or 0,
                "match_date": normalize_balsheet_date(row[5]) if row[5] else None,
                "created_at": row[6] or "",
            }
            for row in rows
        ],
    }


@app.get("/exports/edi-match-results/file")
def export_edi_match_results(match_date: Optional[str] = None):
    os.makedirs(DB_EXPORTS_FOLDER, exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()
    where_clauses = ["(COALESCE(lockbox_amount, 0) != 0 OR COALESCE(eft_amount, 0) != 0)"]
    params = []
    normalized_date = normalize_balsheet_date(match_date) if match_date else None

    if match_date:
        if not normalized_date:
            conn.close()
            raise HTTPException(status_code=400, detail="Match date must be MM/DD/YYYY")
        where_clauses.append("match_date = ?")
        params.append(normalized_date)

    where_sql = "WHERE " + " AND ".join(where_clauses)

    try:
        rows = cur.execute(f"""
            SELECT id, edi_check, edi_amount, lockbox_amount, eft_amount, match_date, created_at
            FROM MatchResults
            {where_sql}
            ORDER BY match_date DESC, id DESC
        """, params).fetchall()
    except sqlite3.OperationalError as exc:
        conn.close()
        raise HTTPException(status_code=404, detail="MatchResults table is not available. Run rebuild-edi first.") from exc

    conn.close()

    suffix = normalized_date.replace("/", "-") if normalized_date else "all"
    out_path = os.path.join(DB_EXPORTS_FOLDER, f"MatchResults_{suffix}.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["ID", "EDI_Check", "EDI_Amount", "Lockbox_Amount", "EFT_Amount", "Match_Date", "Created_At"])
        writer.writerows(rows)

    return FileResponse(
        out_path,
        media_type="text/csv",
        filename=os.path.basename(out_path),
    )


@app.get("/balsheet")
def get_balsheet_entries(posting_date: Optional[str] = None, limit: int = 250):
    conn = get_conn()
    cur = conn.cursor()

    where_sql = ""
    params = []
    if posting_date:
        where_sql = "WHERE PostingDate = ?"
        params.append(normalize_balsheet_date(posting_date) or posting_date)

    params.append(max(1, min(limit, 1000)))
    cur.execute(f"""
        SELECT
            EntryID,
            PostingDate,
            Type,
            Amount,
            Payer,
            "Check Number",
            EDI,
            Poster,
            EOB,
            UnPosted,
            Misc,
            "Misc-Type",
            Notes,
            Nick,
            Raul,
            Needs,
            "From",
            "To"
        FROM Balsheet
        {where_sql}
        ORDER BY
            PostingDate DESC,
            CAST(substr(EntryID, instr(EntryID, '-') + 1) AS INTEGER) DESC
        LIMIT ?
    """, params)
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "entry_id": row["EntryID"],
            "posting_date": row["PostingDate"],
            "type": row["Type"],
            "amount": row["Amount"] or 0,
            "payer": row["Payer"] or "",
            "check_number": row["Check Number"] or "",
            "edi": row["EDI"] or "",
            "poster": row["Poster"] or "",
            "eob": row["EOB"] or "",
            "unposted": row["UnPosted"] or 0,
            "misc": row["Misc"] or 0,
            "misc_type": row["Misc-Type"] or "",
            "notes": row["Notes"] or "",
            "nick": row["Nick"] or 0,
            "raul": row["Raul"] or 0,
            "needs": row["Needs"] or "",
            "from_date": row["From"] or "",
            "to_date": row["To"] or "",
        }
        for row in rows
    ]


@app.get("/admin/tables")
def list_admin_tables():
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()
    table_info = []
    for row in rows:
        table_name = row[0]
        safe_table = table_name.replace('"', '""')
        column_count = len(cur.execute(f'PRAGMA table_info("{safe_table}")').fetchall())
        row_count = cur.execute(f'SELECT COUNT(*) FROM "{safe_table}"').fetchone()[0]
        table_info.append({"name": table_name, "columns": column_count, "rows": row_count})
    conn.close()
    return {"tables": table_info}


@app.get("/admin/tables/export.xlsx")
def export_admin_tables_excel():
    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    os.makedirs(DB_EXPORTS_FOLDER, exist_ok=True)
    out_path = os.path.join(DB_EXPORTS_FOLDER, "Renfrew_Tables.xlsx")

    workbook = xlsxwriter.Workbook(out_path)
    try:
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#f6d9e8", "font_color": "#8f315f"})
        summary_sheet = workbook.add_worksheet("Tables")
        summary_headers = ["Table", "Rows", "Columns", "Headers"]

        for col_index, header in enumerate(summary_headers):
            summary_sheet.write(0, col_index, header, header_fmt)

        summary_sheet.freeze_panes(1, 0)
        summary_sheet.autofilter(0, 0, 0, len(summary_headers) - 1)

        existing_sheet_names = {"Tables"}

        for row_index, row in enumerate(rows, start=1):
            table_name = row[0]
            safe_table = table_name.replace('"', '""')

            column_rows = cur.execute(f'PRAGMA table_info("{safe_table}")').fetchall()
            header_names = [column_row[1] for column_row in column_rows]
            row_count = cur.execute(f'SELECT COUNT(*) FROM "{safe_table}"').fetchone()[0]

            summary_sheet.write(row_index, 0, table_name)
            summary_sheet.write_number(row_index, 1, row_count)
            summary_sheet.write_number(row_index, 2, len(header_names))
            summary_sheet.write(row_index, 3, ", ".join(header_names))

            sheet_name = _build_admin_table_sheet_name(table_name, existing_sheet_names)
            table_sheet = workbook.add_worksheet(sheet_name)
            table_sheet.freeze_panes(1, 0)

            if header_names:
                for col_index, header in enumerate(header_names):
                    table_sheet.write(0, col_index, header, header_fmt)
                    table_sheet.set_column(col_index, col_index, min(max(len(header) + 2, 12), 36))
                table_sheet.autofilter(0, 0, 0, len(header_names) - 1)
            else:
                table_sheet.write(0, 0, "No columns found", header_fmt)
                table_sheet.set_column(0, 0, 24)

        summary_sheet.set_column(0, 0, 30)
        summary_sheet.set_column(1, 2, 12)
        summary_sheet.set_column(3, 3, 120)
    finally:
        try:
            workbook.close()
        finally:
            conn.close()

    return FileResponse(
        out_path,
        filename="Renfrew_Tables.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post("/admin/tables")
def create_admin_table(payload: AdminTableCreateRequest):
    table_name = _validate_sql_identifier(payload.table_name, "Table name")
    if not payload.columns:
        raise HTTPException(status_code=400, detail="At least one column is required")

    conn = get_conn()
    cur = conn.cursor()
    try:
        existing = cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Table already exists")

        column_defs = []
        pk_columns = [column for column in payload.columns if column.pk]
        if len(pk_columns) > 1:
            raise HTTPException(status_code=400, detail="Only one primary key column is allowed")

        for column in payload.columns:
            column_name = _validate_sql_identifier(column.name, "Column name")
            column_type = _validate_sql_type(column.type)
            definition = f'"{column_name}" {column_type}'
            if column.notnull:
                definition += " NOT NULL"
            if column.default not in (None, ""):
                definition += f" DEFAULT {_sqlite_literal(column.default)}"
            if column.pk:
                definition += " PRIMARY KEY"
            column_defs.append(definition)

        cur.execute(f'CREATE TABLE "{table_name}" ({", ".join(column_defs)})')
        conn.commit()
    finally:
        conn.close()

    return {"status": "created", "table": table_name}


@app.get("/admin/tables/{table_name}/columns")
def get_admin_table_columns(table_name: str):
    conn = get_conn()
    cur = conn.cursor()
    safe_table = table_name.replace('"', '""')
    rows = cur.execute(f'PRAGMA table_info("{safe_table}")').fetchall()
    conn.close()

    return {
        "table": table_name,
        "columns": [
            {"name": row[1], "type": row[2] or "", "notnull": bool(row[3]), "default": row[4], "pk": bool(row[5])}
            for row in rows
        ],
    }


@app.post("/admin/tables/{table_name}/columns")
def add_admin_table_column(table_name: str, payload: AdminTableAddFieldRequest):
    column = payload.column
    column_name = _validate_sql_identifier(column.name, "Column name")
    column_type = _validate_sql_type(column.type)

    if column.pk:
        raise HTTPException(status_code=400, detail="SQLite cannot add a primary key column to an existing table")
    if column.notnull and column.default in (None, ""):
        raise HTTPException(status_code=400, detail="A new NOT NULL column needs a default value")

    conn = get_conn()
    cur = conn.cursor()
    safe_table = table_name.replace('"', '""')
    try:
        existing = cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Table not found")

        existing_column = cur.execute(f'PRAGMA table_info("{safe_table}")').fetchall()
        if any(row[1] == column_name for row in existing_column):
            raise HTTPException(status_code=400, detail="Column already exists")

        sql = f'ALTER TABLE "{safe_table}" ADD COLUMN "{column_name}" {column_type}'
        if column.notnull:
            sql += " NOT NULL"
        if column.default not in (None, ""):
            sql += f" DEFAULT {_sqlite_literal(column.default)}"
        cur.execute(sql)
        conn.commit()
    finally:
        conn.close()

    return {"status": "added", "table": table_name, "column": column_name}


@app.post("/admin/tables/{table_name}/rows")
def get_admin_table_rows(table_name: str, payload: TableRowsRequest):
    conn = get_conn()
    cur = conn.cursor()

    safe_table = table_name.replace('"', '""')
    columns = cur.execute(f'PRAGMA table_info("{safe_table}")').fetchall()
    column_names = [row[1] for row in columns]

    if not column_names:
        conn.close()
        raise HTTPException(status_code=404, detail="Table not found")

    limit = max(1, min(payload.limit or 250, 1000))
    offset = max(0, payload.offset or 0)
    sort_column = payload.sort_column if payload.sort_column in column_names else None
    sort_direction = "DESC" if str(payload.sort_direction).lower() == "desc" else "ASC"

    order_sql = ""
    if sort_column:
        order_sql = f' ORDER BY "{sort_column}" {sort_direction}'
    elif "rowid" not in column_names:
        order_sql = ""

    try:
        rows = cur.execute(
            f'SELECT rowid, * FROM "{safe_table}"{order_sql} LIMIT ? OFFSET ?',
            (limit, offset),
        ).fetchall()
    finally:
        conn.close()

    return {
        "table": table_name,
        "columns": ["rowid", *column_names],
        "rows": [
            {column: row[idx] for idx, column in enumerate(["rowid", *column_names])}
            for row in rows
        ],
    }


@app.post("/admin/tables/{table_name}/rows/{rowid}/update")
def update_admin_table_row(table_name: str, rowid: int, payload: TableRowUpdateRequest):
    conn = get_conn()
    cur = conn.cursor()

    safe_table = table_name.replace('"', '""')
    columns = cur.execute(f'PRAGMA table_info("{safe_table}")').fetchall()
    column_names = [row[1] for row in columns if row[1] != "rowid"]
    updates = {key: payload.values.get(key) for key in column_names if key in payload.values}

    if not updates:
        conn.close()
        raise HTTPException(status_code=400, detail="No editable values provided")

    set_sql = ", ".join(f'"{key}" = ?' for key in updates.keys())
    params = list(updates.values()) + [rowid]

    try:
        cur.execute(f'UPDATE "{safe_table}" SET {set_sql} WHERE rowid = ?', params)
        conn.commit()
    finally:
        conn.close()

    return {"status": "ok", "rowid": rowid}


@app.delete("/admin/tables/{table_name}/rows/{rowid}")
def delete_admin_table_row(table_name: str, rowid: int):
    conn = get_conn()
    cur = conn.cursor()

    safe_table = table_name.replace('"', '""')
    try:
        cur.execute(f'DELETE FROM "{safe_table}" WHERE rowid = ?', (rowid,))
        conn.commit()
    finally:
        conn.close()

    return {"status": "ok", "rowid": rowid}


@app.post("/balsheet")
def add_balsheet_entry(entry: BalsheetEntryRequest):
    posting_date = normalize_balsheet_date(entry.posting_date) or get_current_workday()
    conn = get_conn()
    entry_id = next_balsheet_entry_id(conn, posting_date)

    conn.execute("""
        INSERT INTO Balsheet (
            EntryID, PostingDate, Type, Amount, Payer, "Check Number",
            EDI, Poster, EOB, UnPosted, Misc, "Misc-Type", Notes,
            Nick, Raul, Needs, "From", "To"
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, balsheet_payload(entry, entry_id, posting_date))

    conn.commit()
    conn.close()

    return {"status": "posted", "entry_id": entry_id, "posting_date": posting_date}


@app.post("/balsheet/bulk")
def add_balsheet_entries(payload: BalsheetBulkRequest):
    if not payload.entries:
        raise HTTPException(status_code=400, detail="At least one Balsheet entry is required")

    default_posting_date = get_current_workday()
    conn = get_conn()
    posted = []
    batch_note = f"Source batch attachment ID: {payload.source_attachment_id}" if payload.source_attachment_id else ""

    for entry in payload.entries:
        posting_date = normalize_balsheet_date(entry.posting_date) or default_posting_date
        entry_id = next_balsheet_entry_id(conn, posting_date)
        entry_note = entry.notes or ""
        if batch_note:
            entry_note = f"{entry_note} | {batch_note}".strip(" |") if entry_note else batch_note
        if hasattr(entry, "model_copy"):
            entry_for_db = entry.model_copy(update={"notes": entry_note})
        else:
            entry_for_db = entry.copy(update={"notes": entry_note})
        conn.execute("""
            INSERT INTO Balsheet (
                EntryID, PostingDate, Type, Amount, Payer, "Check Number",
                EDI, Poster, EOB, UnPosted, Misc, "Misc-Type", Notes,
                Nick, Raul, Needs, "From", "To"
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, balsheet_payload(entry_for_db, entry_id, posting_date))
        posted.append({"entry_id": entry_id, "posting_date": posting_date})

    conn.commit()
    conn.close()

    return {
        "status": "posted",
        "count": len(posted),
        "source_attachment_id": payload.source_attachment_id,
        "entries": posted,
    }


@app.post("/balsheet/import-eft-lockbox")
def import_eft_lockbox_to_balsheet(payload: Optional[BalsheetEftLockboxImportRequest] = None):
    rebuild_edi_matchresults_core()

    conn = get_conn()
    try:
        workday = get_current_workday()
        bank_day = get_bank_day_for_workday(conn, workday)
        override_existing = bool(payload and payload.override_existing)
        target_posting_date = normalize_balsheet_date(payload.posting_date) if payload else None
        target_posting_date = target_posting_date or workday

        if not bank_day:
            raise HTTPException(
                status_code=404,
                detail=f"No bank day found in calendar for workday {workday}",
            )

        if balsheet_day_has_entries(conn, target_posting_date) and not override_existing:
            raise HTTPException(
                status_code=409,
                detail=f"Posting date {target_posting_date} already has Balsheet entries. Import blocked to prevent duplicates.",
            )

        posted, skipped = import_eft_lockbox_rows(conn, bank_day, target_posting_date, override_existing)
        conn.commit()

        return {
            "status": "posted",
            "workday": workday,
            "bank_day": bank_day,
            "posting_date": target_posting_date,
            "override_existing": override_existing,
            "inserted": len(posted),
            "skipped": len(skipped),
            "entries": posted,
            "skipped_rows": skipped,
        }
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        conn.close()


@app.put("/balsheet/{entry_id}")
def update_balsheet_entry(entry_id: str, entry: BalsheetEntryRequest):
    posting_date = normalize_balsheet_date(entry.posting_date) or get_current_workday()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT EntryID FROM Balsheet WHERE EntryID = ?", (entry_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Balsheet entry not found")

    values = balsheet_payload(entry, entry_id, posting_date)[1:]
    cur.execute("""
        UPDATE Balsheet
        SET PostingDate = ?,
            Type = ?,
            Amount = ?,
            Payer = ?,
            "Check Number" = ?,
            EDI = ?,
            Poster = ?,
            EOB = ?,
            UnPosted = ?,
            Misc = ?,
            "Misc-Type" = ?,
            Notes = ?,
            Nick = ?,
            Raul = ?,
            Needs = ?,
            "From" = ?,
            "To" = ?
        WHERE EntryID = ?
    """, (*values, entry_id))

    conn.commit()
    conn.close()

    return {"status": "updated", "entry_id": entry_id, "posting_date": posting_date}


@app.delete("/balsheet/clear")
def clear_balsheet_entries(posting_date: str):
    normalized_posting_date = normalize_balsheet_date(posting_date)
    if not normalized_posting_date:
        raise HTTPException(status_code=400, detail="Posting date is required")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM Balsheet WHERE PostingDate = ?", (normalized_posting_date,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()

    return {
        "status": "deleted",
        "posting_date": normalized_posting_date,
        "deleted": deleted,
    }


@app.delete("/balsheet/{entry_id}")
def delete_balsheet_entry(entry_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM Balsheet WHERE EntryID = ?", (entry_id,))

    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Balsheet entry not found")

    conn.commit()
    conn.close()

    return {"status": "deleted", "entry_id": entry_id}


@app.post("/site/upload")
def run_site_upload(request: SiteUploadRequest):
    actions = []

    if request.generate_snapshots or request.import_cc_reports:
        process_folder_pdfs()
        actions.append({"step": "process_folder_pdfs", "ran": True})

    return {
        "status": "ok",
        "actions": actions,
        "note": "site_emaildownloader interactive download mode was not run; this button runs the noninteractive site refresh flow.",
    }


@app.post("/site/email-downloader/launch")
def launch_site_email_downloader(request: LaunchSiteEmailDownloaderRequest | None = None):
    script_path = os.path.join(os.path.dirname(__file__), "site_emaildownloader.py")
    subprocess.Popen([sys.executable, script_path], cwd=os.path.dirname(__file__))
    return {
        "status": "launched",
        "script": "site_emaildownloader.py",
    }


# ------------------------------------------------------------
# KEYPROOF SITE CREDIT-CARD REPORT
# ------------------------------------------------------------
@app.get("/keyproof/cc-report")
def get_keyproof_cc_report(
    day: Optional[str] = None,
    batch_number: Optional[str] = None,
    batch_id: Optional[int] = None,
    report_id: Optional[int] = None,
):
    conn = get_conn()
    cur = conn.cursor()
    ensure_site_cc_report_batch_columns(conn)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS site_cc_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_filename TEXT NOT NULL UNIQUE,
            batch_id INTEGER,
            batch_number TEXT,
            batch_day TEXT,
            location TEXT,
            total_amount REAL DEFAULT 0,
            payment_plans_amount REAL DEFAULT 0,
            ar_collections_amount REAL DEFAULT 0,
            imported_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS site_cc_report_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            row_number INTEGER,
            location TEXT,
            department TEXT,
            payment_method TEXT,
            payment_type TEXT,
            payment_time TEXT,
            amount REAL DEFAULT 0,
            transaction_id TEXT,
            account_number TEXT,
            guarantor_name TEXT,
            billing_name TEXT,
            application TEXT,
            FOREIGN KEY (report_id) REFERENCES site_cc_reports(id)
        )
    """)

    if report_id is not None:
        cur.execute("""
            SELECT id, source_filename, batch_id, batch_number, batch_day, location, total_amount,
                   payment_plans_amount, ar_collections_amount
            FROM site_cc_reports
            WHERE id = ?
            LIMIT 1
        """, (report_id,))
    elif batch_number:
        cur.execute("""
            SELECT id, source_filename, batch_id, batch_number, batch_day, location, total_amount,
                   payment_plans_amount, ar_collections_amount
            FROM site_cc_reports
            WHERE batch_number = ?
            ORDER BY imported_at DESC, id DESC
            LIMIT 1
        """, (batch_number,))
    elif batch_id is not None:
        cur.execute("""
            SELECT id, source_filename, batch_id, batch_number, batch_day, location, total_amount,
                   payment_plans_amount, ar_collections_amount
            FROM site_cc_reports
            WHERE batch_id = ?
            ORDER BY imported_at DESC, id DESC
            LIMIT 1
        """, (batch_id,))
    elif day and day != "Unknown":
        cur.execute("""
            SELECT id, source_filename, batch_id, batch_number, batch_day, location, total_amount,
                   payment_plans_amount, ar_collections_amount
            FROM site_cc_reports
            WHERE batch_day = ?
            ORDER BY imported_at DESC, id DESC
            LIMIT 1
        """, (day,))
    elif day == "Unknown":
        cur.execute("""
            SELECT id, source_filename, batch_id, batch_number, batch_day, location, total_amount,
                   payment_plans_amount, ar_collections_amount
            FROM site_cc_reports
            WHERE batch_day IS NULL OR batch_day = ''
            ORDER BY imported_at DESC, id DESC
            LIMIT 1
        """)
    else:
        cur.execute("""
            SELECT id, source_filename, batch_id, batch_number, batch_day, location, total_amount,
                   payment_plans_amount, ar_collections_amount
            FROM site_cc_reports
            ORDER BY imported_at DESC, id DESC
            LIMIT 1
        """)

    report = cur.fetchone()
    if not report:
        conn.close()
        return {"found": False}

    cur.execute("""
        SELECT row_number, location, department, payment_method, payment_type,
               payment_time, amount, transaction_id, account_number,
               guarantor_name, billing_name, application
        FROM site_cc_report_rows
        WHERE report_id = ?
        ORDER BY row_number ASC
    """, (report["id"],))
    rows = cur.fetchall()
    conn.close()

    return {
        "found": True,
        "id": report["id"],
        "source_filename": report["source_filename"],
        "batch_id": report["batch_id"],
        "batch_number": report["batch_number"],
        "batch_day": report["batch_day"],
        "location": report["location"],
        "total_amount": report["total_amount"] or 0,
        "payment_plans_amount": report["payment_plans_amount"] or 0,
        "ar_collections_amount": report["ar_collections_amount"] or 0,
        "rows": [
            {
                "row_number": row["row_number"],
                "location": row["location"],
                "department": row["department"],
                "payment_method": row["payment_method"],
                "payment_type": row["payment_type"],
                "payment_time": row["payment_time"],
                "amount": row["amount"] or 0,
                "transaction_id": row["transaction_id"],
                "account_number": row["account_number"],
                "guarantor_name": row["guarantor_name"],
                "billing_name": row["billing_name"],
                "application": row["application"],
            }
            for row in rows
        ],
    }


@app.get("/keyproof/cc-reports")
def get_keyproof_cc_reports(day: Optional[str] = None, batch_id: Optional[int] = None):
    conn = get_conn()
    cur = conn.cursor()
    ensure_site_cc_report_batch_columns(conn)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS site_cc_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_filename TEXT NOT NULL UNIQUE,
            batch_id INTEGER,
            batch_number TEXT,
            batch_day TEXT,
            location TEXT,
            total_amount REAL DEFAULT 0,
            payment_plans_amount REAL DEFAULT 0,
            ar_collections_amount REAL DEFAULT 0,
            imported_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    if batch_id is not None:
        cur.execute("""
            SELECT id, source_filename, batch_id, batch_number, batch_day, location, total_amount,
                   payment_plans_amount, ar_collections_amount, imported_at
            FROM site_cc_reports
            WHERE batch_id = ?
            ORDER BY imported_at DESC, id DESC
        """, (batch_id,))
    elif day and day != "Unknown":
        cur.execute("""
            SELECT id, source_filename, batch_id, batch_number, batch_day, location, total_amount,
                   payment_plans_amount, ar_collections_amount, imported_at
            FROM site_cc_reports
            WHERE batch_day = ?
            ORDER BY imported_at DESC, id DESC
        """, (day,))
    elif day == "Unknown":
        cur.execute("""
            SELECT id, source_filename, batch_id, batch_number, batch_day, location, total_amount,
                   payment_plans_amount, ar_collections_amount, imported_at
            FROM site_cc_reports
            WHERE batch_day IS NULL OR batch_day = ''
            ORDER BY imported_at DESC, id DESC
        """)
    else:
        cur.execute("""
            SELECT id, source_filename, batch_id, batch_number, batch_day, location, total_amount,
                   payment_plans_amount, ar_collections_amount, imported_at
            FROM site_cc_reports
            ORDER BY imported_at DESC, id DESC
        """)

    rows = cur.fetchall()
    conn.close()

    return {
        "found": bool(rows),
        "count": len(rows),
        "reports": [
            {
                "id": row["id"],
                "source_filename": row["source_filename"],
                "batch_id": row["batch_id"],
                "batch_number": row["batch_number"],
                "batch_day": row["batch_day"],
                "location": row["location"],
                "total_amount": row["total_amount"] or 0,
                "payment_plans_amount": row["payment_plans_amount"] or 0,
                "ar_collections_amount": row["ar_collections_amount"] or 0,
                "imported_at": row["imported_at"],
            }
            for row in rows
        ],
    }


if os.path.isdir(FRONTEND_ASSETS):
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="frontend-assets")


@app.get("/")
def serve_frontend_home():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend build not found. Run npm run build.")
    return FileResponse(index_path)


@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    file_path = os.path.join(FRONTEND_DIST, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)

    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend build not found. Run npm run build.")
    return FileResponse(index_path)


