"""
Workflow Toolkit (WFT) - business logic helpers
Covers: invoice generation, client tracker, workhour analytics, proposal templates.
"""

import json
import logging
import os
import calendar
import tempfile
import io
import zipfile
import csv
from datetime import date, datetime, timedelta, timezone

log = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
CLIENT_NOTES_FILE = "client_notes.json"
CONTRACT_FILE = "contracts.json"
EXPENSES_FILE = "expenses.json"
QUOTE_FILE = "quotes.json"
TIMER_FILE = "timer_sessions.json"
CALENDAR_FILE = "calendar_blocks.json"
MILESTONE_FILE = "milestones.json"
CHANGE_ORDER_FILE = "change_orders.json"
INVOICE_VIEWS_FILE = "invoice_views.json"
ATTACHMENT_META_FILE = "attachments.json"

CONTRACT_TYPES = [
    "Service Agreement",
    "Non-Disclosure Agreement (NDA)",
    "Fixed-Price Contract",
    "Retainer Agreement",
    "Maintenance & Support Contract",
]

QUOTE_STATUS_OPTIONS = ["draft", "sent", "accepted", "rejected", "expired"]
BLOCK_TYPES = ["blocked", "vacation", "meeting", "holiday"]

AUDIT_FILE = "audit_log.json"
BACKUP_INDEX_FILE = "backup_index.json"
BACKUP_RETENTION = 20


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "snapshot"


def _safe_load_path(path: str, fallback):
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def _write_json_atomic_path(path: str, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _request_audit_meta() -> dict:
    try:
        from flask import has_request_context, request
    except Exception:
        return {
            "actor": "system",
            "source": "local",
            "endpoint": "",
            "method": "",
        }

    if not has_request_context():
        return {
            "actor": "system",
            "source": "local",
            "endpoint": "",
            "method": "",
        }

    return {
        "actor": "local-user",
        "source": request.remote_addr or "local",
        "endpoint": request.endpoint or "",
        "method": request.method,
    }


def _append_audit_event(action: str, target: str, details: dict | None = None):
    path = os.path.join(DATA_DIR, AUDIT_FILE)
    entries = _safe_load_path(path, [])
    if not isinstance(entries, list):
        entries = []
    entry = {
        "id": int(datetime.now(timezone.utc).timestamp() * 1000),
        "timestamp": _now_utc(),
        "action": action,
        "target": target,
        "details": details or {},
    }
    entry.update(_request_audit_meta())
    entries.append(entry)
    # Keep latest 5k events to avoid unbounded growth.
    if len(entries) > 5000:
        entries = entries[-5000:]
    _write_json_atomic_path(path, entries)


def get_audit_trail(limit: int = 200) -> list:
    entries = _safe_load_path(os.path.join(DATA_DIR, AUDIT_FILE), [])
    if not isinstance(entries, list):
        entries = []
    if limit <= 0:
        return list(reversed(entries))
    return list(reversed(entries[-limit:]))


def _load(filename: str) -> list:
    """Load a JSON list from *filename* inside DATA_DIR.

    Returns an empty list when the file does not exist or is empty.
    Raises ``ValueError`` if the file exists but contains invalid JSON so the
    caller knows data may be corrupt rather than silently getting an empty list.
    """
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            log.warning("_load: %s contained non-list JSON — treating as []", filename)
            return []
        return data
    except json.JSONDecodeError as exc:
        log.error(
            "_load: corrupt JSON in '%s': %s — file NOT overwritten, fix manually.",
            path, exc,
        )
        raise ValueError(
            f"Data file '{filename}' is corrupt. "
            "Please restore from a backup or delete the file to reset."
        ) from exc
    except IOError as exc:
        log.warning("_load: cannot read '%s': %s", path, exc)
        return []


def _save(filename: str, data: list):
    """Atomically write *data* as JSON to *filename* inside DATA_DIR.

    Writes to a temporary file first, then renames it over the target so a
    crash or disk-full error never leaves the target file truncated/empty.
    """
    path = os.path.join(DATA_DIR, filename)
    before_count = None
    if os.path.exists(path):
        existing = _safe_load_path(path, [])
        if isinstance(existing, list):
            before_count = len(existing)
    os.makedirs(DATA_DIR, exist_ok=True)
    dir_ = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)  # atomic on POSIX and Windows
        if filename != AUDIT_FILE:
            _append_audit_event(
                "data.write",
                filename,
                {
                    "records_before": before_count,
                    "records_after": len(data),
                },
            )
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ── Settings ──────────────────────────────────────────────────────────────────

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "name": "Your Name",
    "business": "Freelancer",
    "currency": "USD",
    "currency_symbol": "$",
    "default_rate": 50.0,
    "working_hours_per_day": 8.0,
    "late_fee_rate": 1.5,
}

CURRENCY_OPTIONS = {
    "USD": "$", "EUR": "€", "GBP": "£", "INR": "₹",
    "JPY": "¥", "CAD": "C$", "AUD": "A$", "CHF": "CHF",
}

SDLC_TEMPLATE_FILE = "sdlc_templates.json"
SCOPED_PROJECT_FILE = "scoped_projects.json"

PROJECT_STATUS_OPTIONS = ["draft", "active", "on_hold", "completed"]

DEFAULT_SDLC_TEMPLATES = [
    {
        "name": "Waterfall Model",
        "slug": "waterfall-model",
        "summary": "A sequential delivery model with fixed stages and strong upfront scope definition.",
        "best_for": "Stable requirements, fixed budgets, regulated delivery, and clearly approved handoffs.",
        "phases": [
            "Requirements and stakeholder sign-off",
            "System and UI design",
            "Implementation",
            "Testing and acceptance",
            "Deployment and handover",
        ],
        "deliverables": [
            "Signed requirements document",
            "Architecture and design pack",
            "Milestone plan",
            "Test report and acceptance checklist",
        ],
        "scope_controls": [
            "Changes require written approval before entering a new phase",
            "Late changes affect timeline and budget",
            "Client approvals close each phase before the next starts",
        ],
        "strengths": [
            "Clear scope boundary",
            "Predictable milestones",
            "Easy to document and price",
        ],
        "risks": [
            "Weak fit for changing requirements",
            "Feedback arrives late",
            "Rework can become expensive",
        ],
        "revision_policy": "One review window per milestone, with change requests estimated separately after sign-off.",
        "testing_strategy": "Formal QA after implementation plus milestone acceptance review.",
        "client_fit": "Clients who want certainty, strong documentation, and strict control over scope.",
        "tags": ["fixed-scope", "documentation", "sequential"],
    },
    {
        "name": "Prototyping Model",
        "slug": "prototyping-model",
        "summary": "An iterative model focused on validating unclear requirements through quick prototypes.",
        "best_for": "UI-heavy work, discovery projects, and clients who need to see the concept before approving build scope.",
        "phases": [
            "Requirement discovery",
            "Prototype planning",
            "Prototype build",
            "Client feedback and revision",
            "Final scope freeze and production build",
        ],
        "deliverables": [
            "Prototype brief",
            "Interactive wireframe or mockup",
            "Feedback summary",
            "Approved build scope",
        ],
        "scope_controls": [
            "Prototype feedback is limited to concept validation before production",
            "Production scope is frozen after prototype approval",
            "New feature requests after approval move to a change backlog",
        ],
        "strengths": [
            "Clarifies vague requirements early",
            "Reduces approval risk",
            "Improves stakeholder confidence",
        ],
        "risks": [
            "Clients may confuse prototype with final product",
            "Extra revisions can stretch discovery",
            "Scope freeze must be explicit",
        ],
        "revision_policy": "Prototype includes defined feedback rounds; production revisions are governed by the approved scope.",
        "testing_strategy": "Prototype usability review followed by production QA after final build.",
        "client_fit": "Clients with evolving ideas who need visual validation before committing budget.",
        "tags": ["discovery", "ui", "validation"],
    },
    {
        "name": "Spiral Model",
        "slug": "spiral-model",
        "summary": "A risk-driven model combining iteration, planning, and validation in controlled cycles.",
        "best_for": "Complex systems, high-risk technical work, and projects with repeated assessment needs.",
        "phases": [
            "Objective and risk planning",
            "Risk analysis",
            "Build or prototype cycle",
            "Review and next-cycle planning",
        ],
        "deliverables": [
            "Risk register",
            "Cycle plan",
            "Iteration output",
            "Review notes and decision log",
        ],
        "scope_controls": [
            "Each cycle must define goals, risks, and approval criteria",
            "Scope changes are evaluated against risk and cost impact",
            "No new cycle starts without retrospective review",
        ],
        "strengths": [
            "Strong risk management",
            "Flexible planning",
            "Good for large unknowns",
        ],
        "risks": [
            "Can be process-heavy for small projects",
            "Requires disciplined client involvement",
            "Budget can expand without cycle control",
        ],
        "revision_policy": "Revisions are captured inside cycle planning and estimated before the next cycle begins.",
        "testing_strategy": "Validation at the end of each spiral cycle with updated risk review.",
        "client_fit": "Clients handling uncertainty, integration risk, or complex stakeholder demands.",
        "tags": ["risk-driven", "complex", "iterative"],
    },
    {
        "name": "Agile Model",
        "slug": "agile-model",
        "summary": "A sprint-based model that prioritizes incremental delivery, collaboration, and adaptation.",
        "best_for": "Fast-moving product work, evolving requirements, and clients open to backlog-based prioritization.",
        "phases": [
            "Backlog setup and prioritization",
            "Sprint planning",
            "Sprint execution",
            "Sprint review and retrospective",
            "Release planning",
        ],
        "deliverables": [
            "Prioritized backlog",
            "Sprint goal",
            "Demo-ready increment",
            "Retrospective notes",
        ],
        "scope_controls": [
            "Scope is controlled at sprint level, not through unlimited requests",
            "Changes enter the backlog and compete for priority",
            "Sprint commitments are protected until review",
        ],
        "strengths": [
            "Adapts to feedback quickly",
            "Frequent delivery and visibility",
            "Strong client collaboration",
        ],
        "risks": [
            "Requires disciplined backlog ownership",
            "Clients may expect unlimited flexibility",
            "Scope creep occurs without sprint boundaries",
        ],
        "revision_policy": "New requests are backlog items and do not interrupt the current sprint unless explicitly re-scoped.",
        "testing_strategy": "Continuous QA during each sprint, with acceptance review during demo.",
        "client_fit": "Clients comfortable with incremental releases and priority-based decision making.",
        "tags": ["sprints", "collaboration", "adaptive"],
    },
    {
        "name": "V-Model",
        "slug": "v-model",
        "summary": "A verification and validation model pairing each delivery stage with a matching test stage.",
        "best_for": "Quality-sensitive work, structured specifications, and clients who want traceability from requirement to test.",
        "phases": [
            "Requirements definition",
            "System and detailed design",
            "Implementation",
            "Unit, integration, system, and acceptance testing",
        ],
        "deliverables": [
            "Requirement traceability matrix",
            "Test plan mapped to requirements",
            "Design artifacts",
            "Validation evidence",
        ],
        "scope_controls": [
            "Every requirement must map to a test outcome",
            "Change requests update both specification and test coverage",
            "Acceptance criteria must be signed before build begins",
        ],
        "strengths": [
            "High traceability",
            "Strong quality discipline",
            "Clear acceptance checkpoints",
        ],
        "risks": [
            "Rigid for rapidly changing scope",
            "Documentation overhead",
            "Feedback loop is slower than agile delivery",
        ],
        "revision_policy": "Any requirement update must revise the paired validation plan before implementation continues.",
        "testing_strategy": "Formal verification at every mapped test level with signed acceptance.",
        "client_fit": "Clients with compliance, QA, or contractual acceptance constraints.",
        "tags": ["quality", "traceability", "validation"],
    },
    {
        "name": "Incremental Model",
        "slug": "incremental-model",
        "summary": "A phased delivery model that releases the product in smaller functional increments.",
        "best_for": "Projects that need faster partial value without waiting for the whole system to finish.",
        "phases": [
            "Core scope planning",
            "Increment definition",
            "Build and test increment",
            "Release and feedback",
            "Next increment planning",
        ],
        "deliverables": [
            "Increment roadmap",
            "Release list by phase",
            "Tested increment deliverables",
            "Release notes",
        ],
        "scope_controls": [
            "Each increment has its own approved scope",
            "New requests are assigned to future increments",
            "Current increment changes require re-estimation",
        ],
        "strengths": [
            "Faster business value",
            "Lower delivery risk per release",
            "Simpler prioritization",
        ],
        "risks": [
            "Architecture can suffer without a core plan",
            "Integration issues may accumulate",
            "Clients may over-compress later increments",
        ],
        "revision_policy": "Changes after an increment is approved are moved into the next increment unless a re-scope is approved.",
        "testing_strategy": "Test each increment independently and confirm regression coverage before release.",
        "client_fit": "Clients who want staged delivery and phased payments.",
        "tags": ["phased", "roadmap", "delivery"],
    },
    {
        "name": "Big Bang Model",
        "slug": "big-bang-model",
        "summary": "A lightweight model with minimal formal planning, suitable only for very small or experimental work.",
        "best_for": "Short experiments, proofs of concept, and low-risk internal ideas with flexible outcomes.",
        "phases": [
            "Idea and rough goal setting",
            "Direct build",
            "Review and refine",
        ],
        "deliverables": [
            "Experiment summary",
            "Prototype or proof of concept",
            "Outcome notes",
        ],
        "scope_controls": [
            "Use only on low-risk, low-dependency work",
            "Set an explicit effort cap before starting",
            "Do not convert into production work without re-scoping",
        ],
        "strengths": [
            "Very fast start",
            "Low process overhead",
            "Good for experimentation",
        ],
        "risks": [
            "High uncertainty",
            "Weak predictability",
            "Easy path to uncontrolled scope",
        ],
        "revision_policy": "Revisions are handled informally but must stay inside the agreed effort cap.",
        "testing_strategy": "Ad hoc validation appropriate for prototype or concept-level work only.",
        "client_fit": "Clients explicitly accepting exploration and uncertainty.",
        "tags": ["experimental", "prototype", "lightweight"],
    },
    {
        "name": "Iterative Model",
        "slug": "iterative-model",
        "summary": "A repeated refinement model where the solution evolves through planned cycles.",
        "best_for": "Projects where the product is expected to mature through feedback and repeated improvement.",
        "phases": [
            "Baseline scope and success criteria",
            "Iteration planning",
            "Build and evaluate iteration",
            "Refinement and next iteration planning",
        ],
        "deliverables": [
            "Iteration objectives",
            "Updated feature set",
            "Feedback summary",
            "Iteration comparison notes",
        ],
        "scope_controls": [
            "Each iteration must have a defined objective",
            "Feedback is prioritized for the next loop instead of expanding the current one",
            "Iteration count or time cap should be agreed upfront",
        ],
        "strengths": [
            "Continuous improvement",
            "Good learning loop",
            "Works well for product refinement",
        ],
        "risks": [
            "Can drift without strong iteration goals",
            "Clients may expect endless refinement",
            "Budget control must be explicit",
        ],
        "revision_policy": "Feedback is consolidated into the next iteration plan; extra iterations require approval.",
        "testing_strategy": "Test at the end of each cycle and compare against prior iteration outcomes.",
        "client_fit": "Clients who want progressive refinement instead of a single final reveal.",
        "tags": ["refinement", "feedback", "cycles"],
    },
    {
        "name": "Rapid Application Development Model",
        "slug": "rapid-application-development-model",
        "summary": "A fast, collaborative model built around quick prototyping and time-boxed delivery.",
        "best_for": "Short timelines, app-like interfaces, and clients ready to provide rapid feedback.",
        "phases": [
            "Requirements workshop",
            "Rapid prototype and component planning",
            "Construction in short cycles",
            "Cutover and acceptance",
        ],
        "deliverables": [
            "Workshop outcomes",
            "Time-boxed release plan",
            "Prototype or low-code components",
            "Acceptance-ready build",
        ],
        "scope_controls": [
            "Timeline is fixed; lower-priority requests move out of the time box",
            "Client feedback windows are scheduled and limited",
            "Scope is pruned to protect delivery date",
        ],
        "strengths": [
            "Fast turnaround",
            "Early visibility",
            "Good for UI-heavy delivery",
        ],
        "risks": [
            "Needs strong client availability",
            "Can sacrifice architecture quality if rushed",
            "Scope discipline must be strict",
        ],
        "revision_policy": "Requests are prioritized into the current time box only if they fit the agreed release window.",
        "testing_strategy": "Frequent functional checks during rapid builds and final acceptance review before cutover.",
        "client_fit": "Clients prioritizing speed and collaboration over heavy documentation.",
        "tags": ["fast", "time-boxed", "collaborative"],
    },
]


def get_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Fill missing keys with defaults
            for k, v in DEFAULT_SETTINGS.items():
                data.setdefault(k, v)
            return data
    except (json.JSONDecodeError, IOError):
        return DEFAULT_SETTINGS.copy()


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "item"


def _text_to_list(value: str | list | None) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [line.strip(" -\t") for line in str(value).splitlines() if line.strip()]


def _normalize_tags(value: str | list | None) -> list[str]:
    if isinstance(value, list):
        return [str(tag).strip() for tag in value if str(tag).strip()]
    if not value:
        return []
    return [tag.strip() for tag in str(value).split(",") if tag.strip()]


def _client_lookup() -> dict:
    return {client["id"]: client for client in get_clients()}


def _template_lookup() -> dict:
    return {template["id"]: template for template in get_sdlc_templates()}


def _normalize_sdlc_template(raw: dict, *, template_id: int | None = None,
                             built_in: bool | None = None) -> dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    name = (raw.get("name") or "Untitled Template").strip()
    return {
        "id": template_id if template_id is not None else raw.get("id"),
        "name": name,
        "slug": _slugify(raw.get("slug") or name),
        "summary": (raw.get("summary") or "").strip(),
        "best_for": (raw.get("best_for") or "").strip(),
        "phases": _text_to_list(raw.get("phases")),
        "deliverables": _text_to_list(raw.get("deliverables")),
        "scope_controls": _text_to_list(raw.get("scope_controls")),
        "strengths": _text_to_list(raw.get("strengths")),
        "risks": _text_to_list(raw.get("risks")),
        "revision_policy": (raw.get("revision_policy") or "").strip(),
        "testing_strategy": (raw.get("testing_strategy") or "").strip(),
        "client_fit": (raw.get("client_fit") or "").strip(),
        "tags": _normalize_tags(raw.get("tags")),
        "built_in": raw.get("built_in") if built_in is None else built_in,
        "created": raw.get("created") or date.today().isoformat(),
        "updated": now,
    }


def _seed_sdlc_templates() -> list:
    templates = []
    for index, template in enumerate(DEFAULT_SDLC_TEMPLATES, start=1):
        templates.append(_normalize_sdlc_template(
            template,
            template_id=index,
            built_in=True,
        ))
    _save(SDLC_TEMPLATE_FILE, templates)
    return templates


def get_sdlc_templates() -> list:
    templates = _load(SDLC_TEMPLATE_FILE)
    if not templates:
        return _seed_sdlc_templates()
    return sorted(templates, key=lambda item: item.get("name", "").lower())


def get_sdlc_template(template_id: int) -> dict | None:
    templates = get_sdlc_templates()
    return next((template for template in templates if template.get("id") == template_id), None)


def add_sdlc_template(name: str, summary: str = "", best_for: str = "",
                      phases: str | list | None = None,
                      deliverables: str | list | None = None,
                      scope_controls: str | list | None = None,
                      strengths: str | list | None = None,
                      risks: str | list | None = None,
                      revision_policy: str = "",
                      testing_strategy: str = "",
                      client_fit: str = "",
                      tags: str | list | None = None) -> dict:
    templates = get_sdlc_templates()
    template = _normalize_sdlc_template({
        "name": name,
        "summary": summary,
        "best_for": best_for,
        "phases": phases,
        "deliverables": deliverables,
        "scope_controls": scope_controls,
        "strengths": strengths,
        "risks": risks,
        "revision_policy": revision_policy,
        "testing_strategy": testing_strategy,
        "client_fit": client_fit,
        "tags": tags,
        "created": date.today().isoformat(),
    }, template_id=max((item["id"] for item in templates), default=0) + 1, built_in=False)
    templates.append(template)
    _save(SDLC_TEMPLATE_FILE, templates)
    return template


def update_sdlc_template(template_id: int, name: str, summary: str = "",
                         best_for: str = "",
                         phases: str | list | None = None,
                         deliverables: str | list | None = None,
                         scope_controls: str | list | None = None,
                         strengths: str | list | None = None,
                         risks: str | list | None = None,
                         revision_policy: str = "",
                         testing_strategy: str = "",
                         client_fit: str = "",
                         tags: str | list | None = None):
    templates = get_sdlc_templates()
    for index, template in enumerate(templates):
        if template.get("id") == template_id:
            built_in = bool(template.get("built_in"))
            created = template.get("created")
            templates[index] = _normalize_sdlc_template({
                "id": template_id,
                "name": name,
                "summary": summary,
                "best_for": best_for,
                "phases": phases,
                "deliverables": deliverables,
                "scope_controls": scope_controls,
                "strengths": strengths,
                "risks": risks,
                "revision_policy": revision_policy,
                "testing_strategy": testing_strategy,
                "client_fit": client_fit,
                "tags": tags,
                "created": created,
            }, template_id=template_id, built_in=built_in)
            break
    _save(SDLC_TEMPLATE_FILE, templates)


def delete_sdlc_template(template_id: int):
    templates = [template for template in get_sdlc_templates() if template.get("id") != template_id]
    _save(SDLC_TEMPLATE_FILE, templates)


def _normalize_scoped_project(raw: dict, *, project_id: int | None = None) -> dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        total_value = round(float(raw.get("total_value") or 0.0), 2)
    except (TypeError, ValueError):
        total_value = 0.0
    return {
        "id": project_id if project_id is not None else raw.get("id"),
        "client_id": raw.get("client_id"),
        "template_id": raw.get("template_id"),
        "project_name": (raw.get("project_name") or "Untitled Project").strip(),
        "summary": (raw.get("summary") or "").strip(),
        "objectives": _text_to_list(raw.get("objectives")),
        "scope_in": _text_to_list(raw.get("scope_in")),
        "scope_out": _text_to_list(raw.get("scope_out")),
        "deliverables": _text_to_list(raw.get("deliverables")),
        "milestones": _text_to_list(raw.get("milestones")),
        "change_control": (raw.get("change_control") or "").strip(),
        "revision_policy": (raw.get("revision_policy") or "").strip(),
        "communication_plan": (raw.get("communication_plan") or "").strip(),
        "acceptance_criteria": _text_to_list(raw.get("acceptance_criteria")),
        "notes": (raw.get("notes") or "").strip(),
        "status": raw.get("status") if raw.get("status") in PROJECT_STATUS_OPTIONS else "draft",
        "start_date": (raw.get("start_date") or "").strip(),
        "target_date": (raw.get("target_date") or "").strip(),
        "total_value": total_value,
        "created": raw.get("created") or date.today().isoformat(),
        "updated": now,
    }


def _attach_project_context(project: dict) -> dict:
    clients = _client_lookup()
    templates = _template_lookup()
    client = clients.get(project.get("client_id"))
    template = templates.get(project.get("template_id"))
    return {
        **project,
        "client_name": client.get("name") if client else "Unknown",
        "template_name": template.get("name") if template else "Unknown",
    }


def get_scoped_projects() -> list:
    projects = _load(SCOPED_PROJECT_FILE)
    hydrated = [_attach_project_context(project) for project in projects]
    return sorted(hydrated, key=lambda item: item.get("updated", ""), reverse=True)


def get_scoped_project(project_id: int) -> dict | None:
    projects = _load(SCOPED_PROJECT_FILE)
    project = next((item for item in projects if item.get("id") == project_id), None)
    return _attach_project_context(project) if project else None


def get_client_scoped_projects(client_id: int) -> list:
    return [project for project in get_scoped_projects() if project.get("client_id") == client_id]


def add_scoped_project(client_id: int, template_id: int, project_name: str,
                       summary: str = "",
                       objectives: str | list | None = None,
                       scope_in: str | list | None = None,
                       scope_out: str | list | None = None,
                       deliverables: str | list | None = None,
                       milestones: str | list | None = None,
                       change_control: str = "",
                       revision_policy: str = "",
                       communication_plan: str = "",
                       acceptance_criteria: str | list | None = None,
                       notes: str = "",
                       status: str = "draft",
                       start_date: str = "",
                       target_date: str = "",
                       total_value: float = 0.0) -> dict:
    projects = _load(SCOPED_PROJECT_FILE)
    project = _normalize_scoped_project({
        "client_id": client_id,
        "template_id": template_id,
        "project_name": project_name,
        "summary": summary,
        "objectives": objectives,
        "scope_in": scope_in,
        "scope_out": scope_out,
        "deliverables": deliverables,
        "milestones": milestones,
        "change_control": change_control,
        "revision_policy": revision_policy,
        "communication_plan": communication_plan,
        "acceptance_criteria": acceptance_criteria,
        "notes": notes,
        "status": status,
        "start_date": start_date,
        "target_date": target_date,
        "total_value": total_value,
        "created": date.today().isoformat(),
    }, project_id=max((item["id"] for item in projects), default=0) + 1)
    projects.append(project)
    _save(SCOPED_PROJECT_FILE, projects)
    return _attach_project_context(project)


def update_scoped_project(project_id: int, client_id: int, template_id: int,
                          project_name: str, summary: str = "",
                          objectives: str | list | None = None,
                          scope_in: str | list | None = None,
                          scope_out: str | list | None = None,
                          deliverables: str | list | None = None,
                          milestones: str | list | None = None,
                          change_control: str = "",
                          revision_policy: str = "",
                          communication_plan: str = "",
                          acceptance_criteria: str | list | None = None,
                          notes: str = "",
                          status: str = "draft",
                          start_date: str = "",
                          target_date: str = "",
                          total_value: float = 0.0):
    projects = _load(SCOPED_PROJECT_FILE)
    for index, project in enumerate(projects):
        if project.get("id") == project_id:
            projects[index] = _normalize_scoped_project({
                "id": project_id,
                "client_id": client_id,
                "template_id": template_id,
                "project_name": project_name,
                "summary": summary,
                "objectives": objectives,
                "scope_in": scope_in,
                "scope_out": scope_out,
                "deliverables": deliverables,
                "milestones": milestones,
                "change_control": change_control,
                "revision_policy": revision_policy,
                "communication_plan": communication_plan,
                "acceptance_criteria": acceptance_criteria,
                "notes": notes,
                "status": status,
                "start_date": start_date,
                "target_date": target_date,
                "total_value": total_value,
                "created": project.get("created"),
            }, project_id=project_id)
            break
    _save(SCOPED_PROJECT_FILE, projects)


def delete_scoped_project(project_id: int):
    projects = [project for project in _load(SCOPED_PROJECT_FILE) if project.get("id") != project_id]
    _save(SCOPED_PROJECT_FILE, projects)


def scoped_project_stats() -> dict:
    projects = get_scoped_projects()
    by_status: dict = {}
    by_model: dict = {}
    for project in projects:
        status = project.get("status", "draft")
        by_status[status] = by_status.get(status, 0) + 1
        model = project.get("template_name", "Unknown")
        by_model[model] = by_model.get(model, 0) + 1
    return {
        "total_projects": len(projects),
        "by_status": by_status,
        "by_model": by_model,
    }


def get_milestones(project_id: int) -> list:
    milestones = [m for m in _load(MILESTONE_FILE) if m.get("project_id") == project_id]
    return sorted(milestones, key=lambda m: m.get("due_date", ""))


def get_milestone(milestone_id: int) -> dict | None:
    return next((m for m in _load(MILESTONE_FILE) if m.get("id") == milestone_id), None)


def _project_total_value(project_id: int) -> float:
    project = get_scoped_project(project_id)
    if not project:
        raise ValueError("Project not found.")
    try:
        return float(project.get("total_value", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def add_milestone(project_id: int, name: str, due_date: str, percent: float, notes: str = "") -> dict:
    if not name.strip():
        raise ValueError("Milestone name is required.")
    try:
        pct = float(percent)
    except (TypeError, ValueError) as exc:
        raise ValueError("Percent must be a number.") from exc
    if pct <= 0:
        raise ValueError("Percent must be greater than zero.")
    try:
        due = date.fromisoformat((due_date or "").strip()).isoformat()
    except ValueError as exc:
        raise ValueError("Invalid due date.") from exc

    milestones = _load(MILESTONE_FILE)
    used_pct = sum(float(m.get("percent", 0) or 0) for m in milestones if m.get("project_id") == project_id)
    if used_pct + pct > 100.0 + 1e-9:
        raise ValueError("Milestone percentages exceed 100% for this project.")

    total_value = _project_total_value(project_id)
    amount = round(total_value * pct / 100.0, 2)
    milestone = {
        "id": max((m.get("id", 0) for m in milestones), default=0) + 1,
        "project_id": project_id,
        "name": name.strip(),
        "due_date": due,
        "percent": round(pct, 2),
        "amount": amount,
        "status": "pending",
        "invoice_id": None,
        "notes": notes.strip(),
    }
    milestones.append(milestone)
    _save(MILESTONE_FILE, milestones)
    return milestone


def update_milestone(milestone_id: int, **fields) -> dict | None:
    milestones = _load(MILESTONE_FILE)
    target = next((m for m in milestones if m.get("id") == milestone_id), None)
    if not target:
        return None

    project_id = target.get("project_id")
    if "name" in fields:
        target["name"] = (fields.get("name") or target.get("name", "")).strip()
    if "due_date" in fields and fields.get("due_date"):
        target["due_date"] = date.fromisoformat(fields.get("due_date")).isoformat()
    if "notes" in fields:
        target["notes"] = (fields.get("notes") or "").strip()
    if "status" in fields and fields.get("status"):
        target["status"] = fields.get("status")
    if "invoice_id" in fields:
        target["invoice_id"] = fields.get("invoice_id")

    if "percent" in fields and fields.get("percent") is not None:
        pct = float(fields.get("percent"))
        if pct <= 0:
            raise ValueError("Percent must be greater than zero.")
        used_pct = sum(
            float(m.get("percent", 0) or 0)
            for m in milestones
            if m.get("project_id") == project_id and m.get("id") != milestone_id
        )
        if used_pct + pct > 100.0 + 1e-9:
            raise ValueError("Milestone percentages exceed 100% for this project.")
        target["percent"] = round(pct, 2)
        target["amount"] = round(_project_total_value(project_id) * pct / 100.0, 2)

    _save(MILESTONE_FILE, milestones)
    return target


def update_milestone_status(milestone_id: int, status: str) -> dict | None:
    allowed = {"pending", "delivered", "invoiced", "paid"}
    if status not in allowed:
        raise ValueError("Invalid milestone status.")
    return update_milestone(milestone_id, status=status)


def delete_milestone(milestone_id: int) -> bool:
    milestones = _load(MILESTONE_FILE)
    target = next((m for m in milestones if m.get("id") == milestone_id), None)
    if not target or target.get("status") != "pending":
        return False
    kept = [m for m in milestones if m.get("id") != milestone_id]
    _save(MILESTONE_FILE, kept)
    return True


def create_invoice_from_milestone(milestone_id: int) -> dict:
    milestone = get_milestone(milestone_id)
    if not milestone:
        raise ValueError("Milestone not found.")
    if milestone.get("invoice_id"):
        raise ValueError("Milestone already invoiced.")

    project = get_scoped_project(milestone.get("project_id"))
    if not project:
        raise ValueError("Project not found.")

    amount = float(milestone.get("amount", 0) or 0)
    invoice = create_invoice(
        client_name=project.get("client_name", "Unknown"),
        items=[{"description": milestone.get("name", "Milestone"), "hours": 1.0, "rate": amount}],
        due_date=milestone.get("due_date") or date.today().isoformat(),
        notes=f"Milestone invoice for project: {project.get('project_name', '')}",
    )

    update_milestone(
        milestone_id,
        status="invoiced",
        invoice_id=invoice.get("id"),
    )
    return invoice


def get_upcoming_milestones(days: int = 14) -> list:
    today = date.today()
    horizon = today + timedelta(days=max(days, 0))
    project_map = {p.get("id"): p for p in get_scoped_projects()}
    out = []
    for milestone in _load(MILESTONE_FILE):
        if milestone.get("status") not in {"pending", "delivered"}:
            continue
        try:
            due = date.fromisoformat(milestone.get("due_date", ""))
        except ValueError:
            continue
        if due > horizon:
            continue
        project = project_map.get(milestone.get("project_id"), {})
        out.append({
            **milestone,
            "project_name": project.get("project_name", "Unknown"),
            "client_name": project.get("client_name", "Unknown"),
        })
    return sorted(out, key=lambda m: m.get("due_date", ""))


def save_settings(settings: dict):
    _write_json_atomic_path(SETTINGS_FILE, settings)
    _append_audit_event("settings.write", "settings.json", {"keys": sorted(settings.keys())})


# ── Clients ──────────────────────────────────────────────────────────────────

def get_clients() -> list:
    return _load("clients.json")


def get_client(client_id: int) -> dict | None:
    return next((client for client in get_clients() if client.get("id") == client_id), None)


def add_client(name: str, email: str, phone: str = "", notes: str = "",
               default_rate: float = 0.0, company: str = "",
               currency: str = "", currency_symbol: str = "",
               status: str = "active", website: str = "") -> dict:
    clients = _load("clients.json")
    client = {
        "id": (max((c["id"] for c in clients), default=0) + 1),
        "name": name,
        "email": email,
        "phone": phone,
        "notes": notes,
        "default_rate": default_rate,
        "company": company,
        "currency": currency,
        "currency_symbol": currency_symbol,
        "status": status,
        "website": website,
        "rate_history": [],
        "created": date.today().isoformat(),
    }
    clients.append(client)
    _save("clients.json", clients)
    return client


def update_client(client_id: int, name: str, email: str, phone: str = "",
                  notes: str = "", default_rate: float = 0.0,
                  company: str = "", currency: str = "",
                  currency_symbol: str = "", status: str = "active",
                  website: str = ""):
    clients = _load("clients.json")
    for c in clients:
        if c["id"] == client_id:
            c["name"] = name
            c["email"] = email
            c["phone"] = phone
            c["notes"] = notes
            c["default_rate"] = default_rate
            c["company"] = company
            c["currency"] = currency
            c["currency_symbol"] = currency_symbol
            c["status"] = status
            c["website"] = website
            break
    _save("clients.json", clients)


def delete_client(client_id: int):
    clients = [c for c in _load("clients.json") if c["id"] != client_id]
    _save("clients.json", clients)


# ── Invoices ─────────────────────────────────────────────────────────────────

def get_invoices() -> list:
    return [_enrich_invoice_finance(inv) for inv in _load("invoices.json")]


def _invoice_adjusted_total(inv: dict) -> float:
    base_total = float(inv.get("total", 0.0) or 0.0)
    adjustments = inv.get("adjustments") or []
    adj_sum = sum(float(a.get("amount", 0.0) or 0.0) for a in adjustments if isinstance(a, dict))
    return round(base_total + adj_sum, 2)


def _invoice_paid_total(inv: dict) -> float:
    payments = inv.get("payments") or []
    return round(sum(float(p.get("amount", 0.0) or 0.0) for p in payments if isinstance(p, dict)), 2)


def _enrich_invoice_finance(inv: dict) -> dict:
    out = dict(inv)
    out.setdefault("payments", [])
    out.setdefault("adjustments", [])
    out["adjusted_total"] = _invoice_adjusted_total(out)
    out["total_paid"] = _invoice_paid_total(out)
    out["balance_due"] = round(max(0.0, out["adjusted_total"] - out["total_paid"]), 2)
    legacy_status = str(out.get("payment_status") or out.get("status") or "").lower()

    # Backward compatibility: old datasets may mark invoice paid without storing
    # explicit payment rows. Keep those invoices paid rather than downgrading.
    if legacy_status == "paid" and not out.get("payments") and out["total_paid"] <= 0.001:
        out["total_paid"] = out["adjusted_total"]
        out["balance_due"] = 0.0
        out["payment_status"] = "paid"
    elif out["balance_due"] <= 0.001:
        out["payment_status"] = "paid"
    elif out["total_paid"] > 0:
        out["payment_status"] = "partial"
    else:
        out["payment_status"] = "unpaid"

    # Keep legacy `status` in sync for existing views/tests.
    out["status"] = out["payment_status"]
    return out


def create_invoice(client_name: str, items: list[dict], due_date: str,
                   notes: str = "", currency: str = "USD",
                   currency_symbol: str = "$", tax_rate: float = 0.0,
                   exchange_rate: float = 1.0, base_currency: str = "",
                   sdlc_model_id: int | None = None, project_type: str = "",
                   sprint_number: int | None = None) -> dict:
    """
    items: [{"description": str, "hours": float, "rate": float}, ...]
    Optional: sdlc_model_id (links to SDLC template), project_type, sprint_number
    """
    invoices = _load("invoices.json")
    inv_id = max((i["id"] for i in invoices), default=0) + 1

    for item in items:
        item["amount"] = round(item["hours"] * item["rate"], 2)
    subtotal = round(sum(i["amount"] for i in items), 2)
    tax_amount = round(subtotal * tax_rate / 100, 2)
    total = round(subtotal + tax_amount, 2)
    cfg = get_settings()
    base_currency = (base_currency or cfg.get("currency", "USD")).upper()
    exchange_rate = float(exchange_rate or 1.0)
    total_base = round(total * exchange_rate, 2)

    invoice = {
        "id": inv_id,
        "invoice_number": f"INV-{inv_id:04d}",
        "client_name": client_name,
        "issue_date": date.today().isoformat(),
        "due_date": due_date,
        "items": items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": total,
        "currency": currency,
        "currency_symbol": currency_symbol,
        "exchange_rate": exchange_rate,
        "base_currency": base_currency,
        "total_base": total_base,
        "status": "unpaid",
        "payment_status": "unpaid",
        "payments": [],
        "adjustments": [],
        "notes": notes,
    }
    
    # Add optional SDLC and project metadata
    if sdlc_model_id:
        invoice["sdlc_model_id"] = sdlc_model_id
    if project_type:
        invoice["project_type"] = project_type
    if sprint_number:
        invoice["sprint_number"] = sprint_number
    
    invoices.append(invoice)
    _save("invoices.json", invoices)
    return _enrich_invoice_finance(invoice)


def mark_invoice_paid(inv_id: int):
    invoice = get_invoice(inv_id)
    if not invoice:
        raise ValueError(f"Invoice #{inv_id} not found.")
    remaining = round(float(invoice.get("balance_due", 0.0) or 0.0), 2)
    if remaining <= 0:
        return
    add_invoice_payment(inv_id, amount=remaining, note="Marked paid")


def get_invoice(inv_id: int) -> dict | None:
    return next((inv for inv in get_invoices() if inv.get("id") == inv_id), None)


def _update_invoice_record(inv_id: int, mutate_fn):
    invoices = _load("invoices.json")
    for idx, inv in enumerate(invoices):
        if inv.get("id") != inv_id:
            continue
        mutate_fn(inv)
        invoices[idx] = inv
        _save("invoices.json", invoices)
        return _enrich_invoice_finance(inv)
    raise ValueError(f"Invoice #{inv_id} not found.")


def add_invoice_payment(inv_id: int, amount: float, paid_date: str = "", method: str = "manual", note: str = "") -> dict:
    value = round(float(amount or 0.0), 2)
    if value <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    def _mutate(inv: dict):
        payments = inv.get("payments") or []
        pay_id = max((p.get("id", 0) for p in payments if isinstance(p, dict)), default=0) + 1
        payments.append({
            "id": pay_id,
            "date": (paid_date or date.today().isoformat()),
            "amount": value,
            "method": method or "manual",
            "note": (note or "").strip(),
            "created_at": _now_utc(),
        })
        inv["payments"] = payments
        enriched = _enrich_invoice_finance(inv)
        inv["status"] = enriched["payment_status"]
        inv["payment_status"] = enriched["payment_status"]

    return _update_invoice_record(inv_id, _mutate)


def add_invoice_adjustment(inv_id: int, amount: float, reason: str = "") -> dict:
    value = round(float(amount or 0.0), 2)
    if value == 0:
        raise ValueError("Adjustment amount cannot be zero.")

    def _mutate(inv: dict):
        adjustments = inv.get("adjustments") or []
        adj_id = max((a.get("id", 0) for a in adjustments if isinstance(a, dict)), default=0) + 1
        adjustments.append({
            "id": adj_id,
            "date": date.today().isoformat(),
            "amount": value,
            "reason": (reason or "Adjustment").strip(),
            "created_at": _now_utc(),
        })
        inv["adjustments"] = adjustments
        enriched = _enrich_invoice_finance(inv)
        inv["status"] = enriched["payment_status"]
        inv["payment_status"] = enriched["payment_status"]

    return _update_invoice_record(inv_id, _mutate)


def get_invoice_ledger(inv_id: int) -> list:
    inv = get_invoice(inv_id)
    if not inv:
        return []
    rows = [{
        "date": inv.get("issue_date"),
        "type": "invoice",
        "amount": float(inv.get("total", 0.0) or 0.0),
        "note": "Invoice issued",
    }]
    for adj in inv.get("adjustments", []):
        rows.append({
            "date": adj.get("date"),
            "type": "adjustment",
            "amount": float(adj.get("amount", 0.0) or 0.0),
            "note": adj.get("reason", "Adjustment"),
        })
    for pay in inv.get("payments", []):
        rows.append({
            "date": pay.get("date"),
            "type": "payment",
            "amount": float(pay.get("amount", 0.0) or 0.0),
            "note": pay.get("note") or pay.get("method", "Payment"),
        })
    rows.sort(key=lambda r: (r.get("date") or "", r.get("type") or ""))
    running = 0.0
    out = []
    for row in rows:
        if row["type"] in {"invoice", "adjustment"}:
            running += row["amount"]
            delta = row["amount"]
        else:
            running -= row["amount"]
            delta = -row["amount"]
        out.append({**row, "delta": round(delta, 2), "running_balance": round(running, 2)})
    return out


def get_recurring_templates() -> list:
    """Return invoices marked as recurring templates."""
    return [inv for inv in get_invoices() if bool(inv.get("recurring", False))]


def _start_of_quarter(d: date) -> date:
    q_month = ((d.month - 1) // 3) * 3 + 1
    return date(d.year, q_month, 1)


def _is_recurring_due(invoice: dict, today: date | None = None) -> bool:
    if not bool(invoice.get("recurring", False)):
        return False
    interval = (invoice.get("recur_interval") or "").lower()
    if interval not in {"weekly", "monthly", "quarterly"}:
        return False

    today = today or date.today()
    last_generated = invoice.get("last_generated") or invoice.get("issue_date")
    if not last_generated:
        return True
    try:
        last = date.fromisoformat(last_generated)
    except ValueError:
        return True

    if interval == "weekly":
        anchor = today - timedelta(days=today.weekday())
    elif interval == "monthly":
        anchor = today.replace(day=1)
    else:
        anchor = _start_of_quarter(today)
    return last < anchor


def get_due_recurring_invoices() -> list:
    """Return recurring templates that should generate a new invoice now."""
    due = [inv for inv in get_recurring_templates() if _is_recurring_due(inv)]
    return sorted(due, key=lambda x: x.get("last_generated") or x.get("issue_date") or "")


def toggle_invoice_recurring(inv_id: int) -> dict:
    invoices = _load("invoices.json")
    for inv in invoices:
        if inv.get("id") == inv_id:
            enabled = not bool(inv.get("recurring", False))
            inv["recurring"] = enabled
            if enabled:
                inv["recur_interval"] = inv.get("recur_interval") or "monthly"
                inv["last_generated"] = inv.get("last_generated") or inv.get("issue_date")
            else:
                inv["recur_interval"] = None
                inv["last_generated"] = None
            _save("invoices.json", invoices)
            return inv
    raise ValueError("Invoice not found.")


def set_invoice_recurring_interval(inv_id: int, interval: str) -> dict:
    interval = (interval or "").lower().strip()
    if interval not in {"weekly", "monthly", "quarterly"}:
        raise ValueError("Invalid recurring interval.")

    invoices = _load("invoices.json")
    for inv in invoices:
        if inv.get("id") == inv_id:
            inv["recurring"] = True
            inv["recur_interval"] = interval
            inv["last_generated"] = inv.get("last_generated") or inv.get("issue_date") or date.today().isoformat()
            _save("invoices.json", invoices)
            return inv
    raise ValueError("Invoice not found.")


def generate_recurring_invoice(source_id: int) -> dict:
    """Generate one unpaid invoice from a recurring template."""
    source = next((inv for inv in get_invoices() if inv.get("id") == source_id), None)
    if not source:
        raise ValueError("Source invoice not found.")
    if not bool(source.get("recurring", False)):
        raise ValueError("Source invoice is not recurring.")

    today = date.today()
    try:
        source_issue = date.fromisoformat(source.get("issue_date", ""))
        source_due = date.fromisoformat(source.get("due_date", ""))
        delta_days = max((source_due - source_issue).days, 0)
    except ValueError:
        delta_days = 14
    new_due = (today + timedelta(days=delta_days)).isoformat()

    line_items = []
    for item in source.get("items", []):
        line_items.append({
            "description": item.get("description", ""),
            "hours": float(item.get("hours", 0) or 0),
            "rate": float(item.get("rate", 0) or 0),
        })

    generated = create_invoice(
        client_name=source.get("client_name", "Unknown"),
        items=line_items,
        due_date=new_due,
        notes=source.get("notes", ""),
        currency=source.get("currency", "USD"),
        currency_symbol=source.get("currency_symbol", "$"),
        tax_rate=float(source.get("tax_rate", 0) or 0),
        exchange_rate=float(source.get("exchange_rate", 1.0) or 1.0),
        base_currency=source.get("base_currency", ""),
        sdlc_model_id=source.get("sdlc_model_id"),
        project_type=source.get("project_type", ""),
        sprint_number=source.get("sprint_number"),
    )

    invoices = _load("invoices.json")
    for inv in invoices:
        if inv.get("id") == source_id:
            inv["last_generated"] = today.isoformat()
        if inv.get("id") == generated.get("id"):
            inv["source_recurring_id"] = source_id
            inv["recurring"] = False
            inv["recur_interval"] = None
            inv["last_generated"] = None
            generated = inv
    _save("invoices.json", invoices)
    return generated


def generate_all_due_recurring() -> list:
    """Generate invoices for all due recurring templates."""
    created = []
    for template in get_due_recurring_invoices():
        created.append(generate_recurring_invoice(template["id"]))
    return created


def delete_invoice(inv_id: int):
    invoices = [i for i in _load("invoices.json") if i["id"] != inv_id]
    _save("invoices.json", invoices)


def cashflow_forecast(days: int = 90) -> dict:
    horizon = date.today() + timedelta(days=max(days, 1))
    invoices = [inv for inv in get_invoices() if inv.get("payment_status") != "paid"]
    due_recurring = get_due_recurring_invoices()
    projects = {p.get("id"): p for p in get_scoped_projects()}
    milestones = get_upcoming_milestones(days=max(days, 1))

    items = []
    for inv in invoices:
        try:
            due = date.fromisoformat(inv.get("due_date", ""))
        except ValueError:
            continue
        if due > horizon:
            continue
        amount = float(inv.get("balance_due", inv.get("total", 0.0)) or 0.0)
        best = amount
        likely = amount * (0.85 if due >= date.today() else 0.7)
        worst = amount * (0.6 if due >= date.today() else 0.35)
        items.append({
            "date": due.isoformat(),
            "type": "invoice",
            "label": inv.get("invoice_number"),
            "amount": round(amount, 2),
            "best": round(best, 2),
            "likely": round(likely, 2),
            "worst": round(worst, 2),
        })

    for template in due_recurring:
        amount = float(template.get("total", 0.0) or 0.0)
        due = date.today() + timedelta(days=14)
        if due > horizon:
            continue
        items.append({
            "date": due.isoformat(),
            "type": "recurring",
            "label": f"Recurring {template.get('invoice_number', template.get('id'))}",
            "amount": round(amount, 2),
            "best": round(amount * 0.9, 2),
            "likely": round(amount * 0.7, 2),
            "worst": round(amount * 0.45, 2),
        })

    for milestone in milestones:
        try:
            due = date.fromisoformat(milestone.get("due_date", ""))
        except ValueError:
            continue
        if due > horizon:
            continue
        project = projects.get(milestone.get("project_id"), {})
        total_value = float(project.get("total_value", 0.0) or 0.0)
        percent = float(milestone.get("percent", 0.0) or 0.0) / 100.0
        amount = round(total_value * percent, 2)
        if amount <= 0:
            continue
        items.append({
            "date": due.isoformat(),
            "type": "milestone",
            "label": f"{project.get('project_name', 'Project')} - {milestone.get('name', 'Milestone')}",
            "amount": amount,
            "best": round(amount * 0.95, 2),
            "likely": round(amount * 0.75, 2),
            "worst": round(amount * 0.5, 2),
        })

    items.sort(key=lambda x: x.get("date", ""))
    return {
        "horizon_days": days,
        "items": items,
        "totals": {
            "best": round(sum(i["best"] for i in items), 2),
            "likely": round(sum(i["likely"] for i in items), 2),
            "worst": round(sum(i["worst"] for i in items), 2),
        },
    }


def margin_intelligence(target_rate: float | None = None) -> dict:
    cfg = get_settings()
    target = float(target_rate or cfg.get("default_rate", 50.0) or 50.0)
    rows = profitability_report()
    alerts = [
        {
            "client": row.get("client"),
            "effective_rate": row.get("effective_rate", 0.0),
            "target_rate": target,
        }
        for row in rows
        if float(row.get("effective_rate", 0.0) or 0.0) > 0 and float(row.get("effective_rate", 0.0) or 0.0) < target
    ]

    invoices = [inv for inv in get_invoices() if inv.get("payment_status") == "paid"]
    hours = get_workhours()

    by_month = {}
    for inv in invoices:
        month = (inv.get("issue_date") or "")[:7]
        if not month:
            continue
        by_month.setdefault(month, {"paid": 0.0, "hours": 0.0})
        by_month[month]["paid"] += float(inv.get("total", 0.0) or 0.0)
    for entry in hours:
        month = (entry.get("date") or "")[:7]
        if not month:
            continue
        by_month.setdefault(month, {"paid": 0.0, "hours": 0.0})
        by_month[month]["hours"] += float(entry.get("hours", 0.0) or 0.0)

    month_rows = []
    for month in sorted(by_month.keys()):
        paid = round(by_month[month]["paid"], 2)
        hrs = round(by_month[month]["hours"], 2)
        eff = round(paid / hrs, 2) if hrs > 0 else 0.0
        month_rows.append({"month": month, "paid": paid, "hours": hrs, "effective_rate": eff})

    service_rollup = {}
    for entry in hours:
        key = (entry.get("tag") or "general").strip().lower() or "general"
        service_rollup.setdefault(key, {"hours": 0.0, "paid": 0.0})
        service_rollup[key]["hours"] += float(entry.get("hours", 0.0) or 0.0)
    for inv in invoices:
        key = (inv.get("project_type") or "general").strip().lower() or "general"
        service_rollup.setdefault(key, {"hours": 0.0, "paid": 0.0})
        service_rollup[key]["paid"] += float(inv.get("total", 0.0) or 0.0)

    service_rows = []
    for service, stats in sorted(service_rollup.items()):
        hrs = round(stats["hours"], 2)
        paid = round(stats["paid"], 2)
        eff = round(paid / hrs, 2) if hrs > 0 else 0.0
        service_rows.append({"service": service, "hours": hrs, "paid": paid, "effective_rate": eff})

    return {
        "target_rate": target,
        "alerts": alerts,
        "by_client": rows,
        "by_month": month_rows,
        "by_service": service_rows,
    }


def get_change_orders() -> list:
    return sorted(_load(CHANGE_ORDER_FILE), key=lambda x: x.get("created_date", ""), reverse=True)


def add_change_order(client_name: str, description: str, amount_delta: float,
                     hours_delta: float = 0.0, quote_id: int | None = None,
                     invoice_id: int | None = None, status: str = "draft") -> dict:
    orders = _load(CHANGE_ORDER_FILE)
    allowed = {"draft", "submitted", "approved", "rejected", "invoiced"}
    status = status if status in allowed else "draft"
    order = {
        "id": max((o.get("id", 0) for o in orders), default=0) + 1,
        "client_name": (client_name or "Unknown").strip(),
        "description": (description or "").strip(),
        "amount_delta": round(float(amount_delta or 0.0), 2),
        "hours_delta": round(float(hours_delta or 0.0), 2),
        "quote_id": quote_id,
        "invoice_id": invoice_id,
        "status": status,
        "created_date": date.today().isoformat(),
    }
    orders.append(order)
    _save(CHANGE_ORDER_FILE, orders)
    return order


def update_change_order_status(order_id: int, status: str, apply_to_invoice: bool = False) -> dict:
    allowed = {"draft", "submitted", "approved", "rejected", "invoiced"}
    if status not in allowed:
        raise ValueError("Invalid change-order status.")

    orders = _load(CHANGE_ORDER_FILE)
    for order in orders:
        if order.get("id") != order_id:
            continue
        order["status"] = status
        if status == "approved" and apply_to_invoice and order.get("invoice_id") and float(order.get("amount_delta", 0.0) or 0.0) != 0:
            add_invoice_adjustment(
                int(order["invoice_id"]),
                amount=float(order.get("amount_delta", 0.0) or 0.0),
                reason=f"Change Order #{order_id}: {order.get('description', '')}"[:160],
            )
            order["status"] = "invoiced"
        _save(CHANGE_ORDER_FILE, orders)
        return order
    raise ValueError("Change order not found.")


def get_ar_risk_scores() -> list:
    today = date.today()
    invoices = get_invoices()
    unpaid = [inv for inv in invoices if inv.get("payment_status") != "paid"]

    # Client payment behavior: average delay on paid invoices.
    behavior = {}
    for inv in invoices:
        if inv.get("payment_status") != "paid":
            continue
        client = inv.get("client_name", "Unknown")
        due = inv.get("due_date")
        payments = inv.get("payments") or []
        if not due or not payments:
            continue
        try:
            due_d = date.fromisoformat(due)
        except ValueError:
            continue
        paid_dates = []
        for p in payments:
            try:
                paid_dates.append(date.fromisoformat(p.get("date", "")))
            except ValueError:
                continue
        if not paid_dates:
            continue
        delay = (min(paid_dates) - due_d).days
        behavior.setdefault(client, []).append(delay)

    out = []
    for inv in unpaid:
        client = inv.get("client_name", "Unknown")
        amount = float(inv.get("balance_due", inv.get("total", 0.0)) or 0.0)
        try:
            due_d = date.fromisoformat(inv.get("due_date", ""))
            days_overdue = max(0, (today - due_d).days)
        except ValueError:
            days_overdue = 0

        avg_delay = 0.0
        if behavior.get(client):
            avg_delay = sum(behavior[client]) / len(behavior[client])

        amount_score = min(30.0, (amount / 5000.0) * 30.0)
        age_score = min(40.0, (days_overdue / 60.0) * 40.0)
        behavior_score = min(30.0, max(0.0, ((avg_delay + 30) / 60.0) * 30.0))
        score = round(amount_score + age_score + behavior_score, 1)

        if score >= 75:
            band = "high"
        elif score >= 45:
            band = "medium"
        else:
            band = "low"

        out.append({
            "invoice_id": inv.get("id"),
            "invoice_number": inv.get("invoice_number"),
            "client_name": client,
            "balance_due": round(amount, 2),
            "days_overdue": days_overdue,
            "avg_client_delay": round(avg_delay, 1),
            "risk_score": score,
            "risk_band": band,
        })

    return sorted(out, key=lambda r: r.get("risk_score", 0.0), reverse=True)


# ── Contracts ───────────────────────────────────────────────────────────────

def get_contracts() -> list:
    contracts = _load(CONTRACT_FILE)
    return sorted(contracts, key=lambda item: item.get("created_date", ""), reverse=True)


def get_contract(contract_id: int) -> dict | None:
    return next((contract for contract in _load(CONTRACT_FILE) if contract.get("id") == contract_id), None)


def add_contract(**fields) -> dict:
    contracts = _load(CONTRACT_FILE)
    cfg = get_settings()
    client_id = fields.get("client_id")
    client = get_client(client_id) if client_id else None
    contract_type = fields.get("contract_type") or CONTRACT_TYPES[0]
    if contract_type not in CONTRACT_TYPES:
        contract_type = CONTRACT_TYPES[0]

    created_date = fields.get("created_date") or date.today().isoformat()
    status = (fields.get("status") or "draft").lower()
    if status not in {"draft", "sent", "signed"}:
        status = "draft"

    contract = {
        "id": max((item.get("id", 0) for item in contracts), default=0) + 1,
        "title": (fields.get("title") or "Untitled Contract").strip(),
        "contract_type": contract_type,
        "client_id": client_id,
        "client_name": (fields.get("client_name") or (client.get("name") if client else "")).strip(),
        "client_email": (fields.get("client_email") or (client.get("email") if client else "")).strip(),
        "project_description": (fields.get("project_description") or "").strip(),
        "payment_terms": (fields.get("payment_terms") or "").strip(),
        "project_value": round(float(fields.get("project_value") or 0.0), 2),
        "currency_symbol": (fields.get("currency_symbol") or cfg.get("currency_symbol", "$")),
        "start_date": (fields.get("start_date") or "").strip(),
        "end_date": (fields.get("end_date") or "").strip(),
        "revision_limit": int(fields.get("revision_limit") or 0),
        "late_fee_percent": float(fields.get("late_fee_percent") or 0.0),
        "ip_ownership": (fields.get("ip_ownership") or "client").strip(),
        "confidentiality": bool(fields.get("confidentiality")),
        "governing_law": (fields.get("governing_law") or "").strip(),
        "freelancer_name": (fields.get("freelancer_name") or cfg.get("name", "")).strip(),
        "freelancer_business": (fields.get("freelancer_business") or cfg.get("business", "")).strip(),
        "custom_clauses": (fields.get("custom_clauses") or "").strip(),
        "status": status,
        "created_date": created_date,
        "notes": (fields.get("notes") or "").strip(),
    }
    contracts.append(contract)
    _save(CONTRACT_FILE, contracts)
    return contract


def update_contract(contract_id: int, **fields):
    contracts = _load(CONTRACT_FILE)
    for contract in contracts:
        if contract.get("id") != contract_id:
            continue
        for key in [
            "title", "contract_type", "client_id", "client_name", "client_email",
            "project_description", "payment_terms", "currency_symbol", "start_date",
            "end_date", "ip_ownership", "governing_law", "freelancer_name",
            "freelancer_business", "custom_clauses", "notes",
        ]:
            if key in fields:
                value = fields.get(key)
                contract[key] = value.strip() if isinstance(value, str) else value

        if "project_value" in fields:
            contract["project_value"] = round(float(fields.get("project_value") or 0.0), 2)
        if "revision_limit" in fields:
            contract["revision_limit"] = int(fields.get("revision_limit") or 0)
        if "late_fee_percent" in fields:
            contract["late_fee_percent"] = float(fields.get("late_fee_percent") or 0.0)
        if "confidentiality" in fields:
            contract["confidentiality"] = bool(fields.get("confidentiality"))
        if "status" in fields:
            status = str(fields.get("status") or contract.get("status", "draft")).lower()
            if status in {"draft", "sent", "signed"}:
                contract["status"] = status
        break
    _save(CONTRACT_FILE, contracts)


def delete_contract(contract_id: int):
    contracts = [contract for contract in _load(CONTRACT_FILE) if contract.get("id") != contract_id]
    _save(CONTRACT_FILE, contracts)


def get_contract_stats() -> dict:
    contracts = _load(CONTRACT_FILE)
    return {
        "total": len(contracts),
        "draft": sum(1 for item in contracts if item.get("status") == "draft"),
        "sent": sum(1 for item in contracts if item.get("status") == "sent"),
        "signed": sum(1 for item in contracts if item.get("status") == "signed"),
    }


# ── Quotes ──────────────────────────────────────────────────────────────────

def _normalize_quote_items(items: list[dict]) -> list[dict]:
    normalized = []
    for item in items:
        description = str(item.get("description", "")).strip()
        if not description:
            continue
        qty = float(item.get("qty", 0) or 0)
        rate = float(item.get("rate", 0) or 0)
        amount = round(qty * rate, 2)
        normalized.append({
            "description": description,
            "qty": qty,
            "rate": rate,
            "amount": amount,
        })
    return normalized


def get_quotes() -> list:
    quotes = _load(QUOTE_FILE)
    return sorted(quotes, key=lambda item: item.get("issue_date", ""), reverse=True)


def get_quote(quote_id: int) -> dict | None:
    return next((quote for quote in _load(QUOTE_FILE) if quote.get("id") == quote_id), None)


def add_quote(client_id: int | None, client_name: str, title: str, items: list[dict], tax_rate: float,
              currency: str, currency_symbol: str, expiry_date: str, notes: str) -> dict:
    quotes = _load(QUOTE_FILE)
    cfg = get_settings()
    client = get_client(client_id) if client_id else None
    quote_id = max((item.get("id", 0) for item in quotes), default=0) + 1
    parsed_items = _normalize_quote_items(items)
    subtotal = round(sum(item["amount"] for item in parsed_items), 2)
    tax_rate = float(tax_rate or 0.0)
    tax_amount = round(subtotal * tax_rate / 100, 2)
    total = round(subtotal + tax_amount, 2)

    quote = {
        "id": quote_id,
        "quote_number": f"QT-{quote_id:03d}",
        "client_id": client_id,
        "client_name": (client_name or (client.get("name") if client else "")).strip(),
        "title": title.strip() or "Untitled Quote",
        "items": parsed_items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": total,
        "currency": (currency or cfg.get("currency", "USD")).upper(),
        "currency_symbol": currency_symbol or cfg.get("currency_symbol", "$"),
        "status": "draft",
        "issue_date": date.today().isoformat(),
        "expiry_date": (expiry_date or "").strip(),
        "notes": (notes or "").strip(),
        "converted_invoice_id": None,
    }
    quotes.append(quote)
    _save(QUOTE_FILE, quotes)
    return quote


def update_quote(quote_id: int, **fields):
    quotes = _load(QUOTE_FILE)
    for quote in quotes:
        if quote.get("id") != quote_id:
            continue
        if "client_id" in fields:
            quote["client_id"] = fields.get("client_id")
        for key in ["client_name", "title", "currency", "currency_symbol", "expiry_date", "notes"]:
            if key in fields:
                value = fields.get(key)
                quote[key] = value.strip() if isinstance(value, str) else value

        if "status" in fields:
            status = str(fields.get("status") or quote.get("status", "draft")).lower()
            if status in QUOTE_STATUS_OPTIONS:
                quote["status"] = status

        if "tax_rate" in fields:
            quote["tax_rate"] = float(fields.get("tax_rate") or 0.0)

        if "items" in fields:
            quote["items"] = _normalize_quote_items(fields.get("items") or [])

        subtotal = round(sum(item.get("amount", 0.0) for item in quote.get("items", [])), 2)
        tax_amount = round(subtotal * float(quote.get("tax_rate", 0.0) or 0.0) / 100, 2)
        quote["subtotal"] = subtotal
        quote["tax_amount"] = tax_amount
        quote["total"] = round(subtotal + tax_amount, 2)
        break
    _save(QUOTE_FILE, quotes)


def update_quote_status(quote_id: int, status: str):
    status = (status or "").lower()
    if status not in QUOTE_STATUS_OPTIONS:
        return
    update_quote(quote_id, status=status)


def delete_quote(quote_id: int) -> bool:
    quote = get_quote(quote_id)
    if not quote:
        return False
    if quote.get("converted_invoice_id"):
        return False
    quotes = [item for item in _load(QUOTE_FILE) if item.get("id") != quote_id]
    _save(QUOTE_FILE, quotes)
    return True


def convert_quote_to_invoice(quote_id: int) -> dict | None:
    """Convert an *accepted* quote into an invoice.

    Raises ``ValueError`` if the quote does not exist, has already been
    converted, or is not in ``'accepted'`` status — preventing invoices from
    being created out of draft or rejected quotes.
    """
    quote = get_quote(quote_id)
    if not quote:
        raise ValueError(f"Quote {quote_id} not found.")
    if quote.get("converted_invoice_id"):
        raise ValueError(
            f"Quote {quote.get('quote_number', quote_id)} has already been converted "
            f"to invoice #{quote['converted_invoice_id']}."
        )
    if quote.get("status") != "accepted":
        raise ValueError(
            f"Only accepted quotes can be converted to invoices "
            f"(current status: '{quote.get('status', 'unknown')}')."
        )

    invoice_items = [
        {
            "description": item.get("description", ""),
            "hours": float(item.get("qty", 0) or 0),
            "rate": float(item.get("rate", 0) or 0),
        }
        for item in quote.get("items", [])
    ]
    if not invoice_items:
        return None

    invoice = create_invoice(
        client_name=quote.get("client_name", "Unknown"),
        items=invoice_items,
        due_date=quote.get("expiry_date") or date.today().isoformat(),
        notes=f"Converted from quote {quote.get('quote_number', '')}. {quote.get('notes', '')}".strip(),
        currency=quote.get("currency", get_settings().get("currency", "USD")),
        currency_symbol=quote.get("currency_symbol", get_settings().get("currency_symbol", "$")),
        tax_rate=float(quote.get("tax_rate", 0.0) or 0.0),
    )

    quotes = _load(QUOTE_FILE)
    for item in quotes:
        if item.get("id") == quote_id:
            item["converted_invoice_id"] = invoice.get("id")
            item["status"] = "accepted"
            break
    _save(QUOTE_FILE, quotes)
    return invoice


def get_quote_stats() -> dict:
    quotes = _load(QUOTE_FILE)
    total = len(quotes)
    converted = sum(1 for quote in quotes if quote.get("converted_invoice_id"))
    conversion_rate = round((converted / total) * 100, 2) if total else 0.0
    return {
        "total": total,
        "draft": sum(1 for quote in quotes if quote.get("status") == "draft"),
        "sent": sum(1 for quote in quotes if quote.get("status") == "sent"),
        "accepted": sum(1 for quote in quotes if quote.get("status") == "accepted"),
        "rejected": sum(1 for quote in quotes if quote.get("status") == "rejected"),
        "expired": sum(1 for quote in quotes if quote.get("status") == "expired"),
        "conversion_rate": conversion_rate,
    }


def get_earnings_summary() -> dict:
    """Financial summary payload used by dashboard and reports pages."""
    invoices = _load("invoices.json")
    workhours = _load("workhours.json")
    expenses = _load("expenses.json")
    cfg = get_settings()

    def normalized_total(inv: dict) -> float:
        try:
            if inv.get("total_base") is not None:
                return float(inv.get("total_base", 0.0) or 0.0)
            return float(inv.get("total", 0.0) or 0.0) * float(inv.get("exchange_rate", 1.0) or 1.0)
        except (TypeError, ValueError):
            return float(inv.get("total", 0.0) or 0.0)

    total_paid = round(sum(normalized_total(i) for i in invoices if i.get("status") == "paid"), 2)
    total_outstanding = round(sum(normalized_total(i) for i in invoices if i.get("status") != "paid"), 2)
    total_expenses = round(sum(e["amount"] for e in expenses), 2)
    net_profit = round(total_paid - total_expenses, 2)

    # Hours this week (Mon–today)
    today = date.today()
    week_start = today.toordinal() - today.weekday()
    hours_this_week = round(sum(
        e["hours"] for e in workhours
        if date.fromisoformat(e["date"]).toordinal() >= week_start
    ), 2)

    # Overdue invoices
    overdue_count = sum(
        1 for i in invoices
        if i.get("status") != "paid" and i.get("due_date", "9999-12-31") < today.isoformat()
    )

    paid_invoices = [i for i in invoices if i.get("status") == "paid"]

    # Income by month (last 12 months)
    income_by_month: dict[str, float] = {}
    expense_by_month: dict[str, float] = {}
    for inv in invoices:
        if inv.get("status") == "paid" and inv.get("issue_date"):
            month = inv["issue_date"][:7]
            income_by_month[month] = round(income_by_month.get(month, 0) + normalized_total(inv), 2)

    for exp in expenses:
        month = exp.get("date", "")[:7]
        if month:
            expense_by_month[month] = round(expense_by_month.get(month, 0) + exp.get("amount", 0), 2)

    all_months = sorted(set(income_by_month.keys()) | set(expense_by_month.keys()))
    income_by_month = {m: income_by_month.get(m, 0.0) for m in all_months[-12:]}

    profit_by_month: dict[str, float] = {}
    for month in all_months[-12:]:
        profit_by_month[month] = round(income_by_month.get(month, 0.0) - expense_by_month.get(month, 0.0), 2)

    # Income by client (top 10)
    income_by_client: dict[str, float] = {}
    for inv in invoices:
        if inv.get("status") == "paid":
            name = inv.get("client_name", "Unknown")
            income_by_client[name] = round(income_by_client.get(name, 0) + normalized_total(inv), 2)
    income_by_client = dict(sorted(income_by_client.items(), key=lambda x: -x[1])[:10])

    # Hours by week (last 12 ISO weeks)
    weekly_hours = _weekly_hours(workhours, weeks=12, include_year=True)

    # Expense totals by category
    expense_by_cat: dict[str, float] = {}
    for exp in expenses:
        cat = exp.get("category", "Other") or "Other"
        expense_by_cat[cat] = round(expense_by_cat.get(cat, 0.0) + exp.get("amount", 0.0), 2)
    expense_by_cat = dict(sorted(expense_by_cat.items(), key=lambda x: -x[1]))

    total_hours_all = round(sum(e.get("hours", 0) for e in workhours), 2)
    avg_hourly_rate = round(total_paid / total_hours_all, 2) if total_hours_all > 0 else 0.0
    paid_count = len(paid_invoices)
    unpaid_count = len(invoices) - paid_count

    return {
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "hours_this_week": hours_this_week,
        "overdue_count": overdue_count,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "income_by_month": income_by_month,
        "income_by_client": income_by_client,
        "weekly_hours": weekly_hours,
        "profit_by_month": profit_by_month,
        "expense_by_cat": expense_by_cat,
        "avg_hourly_rate": avg_hourly_rate,
        "paid_count": paid_count,
        "unpaid_count": unpaid_count,
        "currency_symbol": cfg.get("currency_symbol", "$"),
    }


# ── Work Hours ────────────────────────────────────────────────────────────────

def get_workhours() -> list:
    return _load("workhours.json")


def log_hours(task: str, client: str, hours: float,
              log_date: str = "", notes: str = "", tag: str = "") -> dict:
    entries = _load("workhours.json")
    entry = {
        "id": max((e["id"] for e in entries), default=0) + 1,
        "task": task,
        "client": client,
        "hours": hours,
        "date": log_date or date.today().isoformat(),
        "notes": notes,
        "tag": tag,
    }
    entries.append(entry)
    _save("workhours.json", entries)
    return entry


def update_workhour(entry_id: int, task: str, client: str, hours: float,
                    log_date: str = "", notes: str = "", tag: str = ""):
    entries = _load("workhours.json")
    for e in entries:
        if e["id"] == entry_id:
            e["task"] = task
            e["client"] = client
            e["hours"] = hours
            e["date"] = log_date or e["date"]
            e["notes"] = notes
            e["tag"] = tag
            break
    _save("workhours.json", entries)


def delete_workhour(entry_id: int):
    entries = [e for e in _load("workhours.json") if e["id"] != entry_id]
    _save("workhours.json", entries)


def analytics(period: str = "all") -> dict:
    entries = _load("workhours.json")

    # Filter by period
    today = date.today()
    if period == "week":
        week_start = today.toordinal() - today.weekday()
        entries = [e for e in entries if date.fromisoformat(e["date"]).toordinal() >= week_start]
    elif period == "month":
        entries = [e for e in entries
                   if e["date"][:7] == today.isoformat()[:7]]

    if not entries:
        return {
            "total_hours": 0,
            "by_client": {},
            "by_task": {},
            "daily_avg": 0,
            "busiest_day": None,
            "busiest_day_hours": 0,
            "weekly_data": [],
        }

    total = sum(e["hours"] for e in entries)

    by_client: dict = {}
    for e in entries:
        by_client[e["client"]] = round(by_client.get(e["client"], 0) + e["hours"], 2)

    by_task: dict = {}
    for e in entries:
        by_task[e["task"]] = round(by_task.get(e["task"], 0) + e["hours"], 2)

    by_day: dict = {}
    for e in entries:
        by_day[e["date"]] = round(by_day.get(e["date"], 0) + e["hours"], 2)

    busiest = max(by_day, key=lambda d: by_day[d]) if by_day else None
    unique_days = len(by_day)
    daily_avg = round(total / unique_days, 2) if unique_days else 0

    # Weekly chart data: last 8 weeks
    weekly_data = _weekly_hours(entries)

    return {
        "total_hours": round(total, 2),
        "by_client": dict(sorted(by_client.items(), key=lambda x: -x[1])),
        "by_task": dict(sorted(by_task.items(), key=lambda x: -x[1])),
        "daily_avg": daily_avg,
        "busiest_day": busiest,
        "busiest_day_hours": by_day.get(busiest, 0) if busiest else 0,
        "weekly_data": weekly_data,
    }


def _weekly_hours(entries: list, weeks: int = 8, include_year: bool = False) -> list:
    """Return last N ISO-week labels and their hour totals."""
    by_week: dict = {}
    for e in entries:
        d = date.fromisoformat(e["date"])
        iso = d.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        by_week[key] = round(by_week.get(key, 0) + e["hours"], 2)
    sorted_weeks = sorted(by_week.items())[-weeks:]
    if include_year:
        return [{"week": w, "hours": h} for w, h in sorted_weeks]
    return [{"week": w.split("-")[1], "hours": h} for w, h in sorted_weeks]


# ── Live Timer ───────────────────────────────────────────────────────────────

def get_timer_sessions() -> list:
    sessions = _load(TIMER_FILE)
    return sorted(sessions, key=lambda item: item.get("start_time", ""), reverse=True)


def get_active_session() -> dict | None:
    sessions = get_timer_sessions()
    return next((session for session in sessions if session.get("status") == "running"), None)


def start_timer(client: str, task: str, mode: str = "normal") -> dict:
    if get_active_session():
        raise ValueError("Stop current session first.")

    sessions = _load(TIMER_FILE)
    now = datetime.now().replace(microsecond=0)
    mode = "pomodoro" if mode == "pomodoro" else "normal"
    session = {
        "id": max((item.get("id", 0) for item in sessions), default=0) + 1,
        "client": (client or "Unknown").strip(),
        "task": (task or "Untitled Task").strip(),
        "start_time": now.isoformat(),
        "end_time": None,
        "duration_seconds": 0,
        "date": now.date().isoformat(),
        "status": "running",
        "mode": mode,
    }
    sessions.append(session)
    _save(TIMER_FILE, sessions)
    return session


def stop_timer(session_id: int) -> dict:
    sessions = _load(TIMER_FILE)
    now = datetime.now().replace(microsecond=0)
    for session in sessions:
        if session.get("id") != session_id:
            continue
        if session.get("status") != "running":
            raise ValueError("Only running sessions can be stopped.")
        try:
            start_dt = datetime.fromisoformat(session.get("start_time", ""))
        except ValueError as exc:
            raise ValueError("Session start time is invalid.") from exc
        duration = max(0, int((now - start_dt).total_seconds()))
        session["end_time"] = now.isoformat()
        session["duration_seconds"] = duration
        session["status"] = "stopped"
        session["date"] = start_dt.date().isoformat()
        _save(TIMER_FILE, sessions)
        return session
    raise ValueError("Timer session not found.")


def save_timer_to_hours(session_id: int) -> dict:
    sessions = _load(TIMER_FILE)
    for session in sessions:
        if session.get("id") != session_id:
            continue
        if session.get("status") != "stopped":
            raise ValueError("Only stopped sessions can be saved to hours.")
        duration_seconds = int(session.get("duration_seconds", 0) or 0)
        hours = round(duration_seconds / 3600, 2)
        log_hours(
            task=session.get("task", "Untitled Task"),
            client=session.get("client", "Unknown"),
            hours=hours,
            log_date=session.get("date", date.today().isoformat()),
            notes=f"Logged from live timer ({session.get('mode', 'normal')}).",
            tag="timer",
        )
        session["status"] = "saved"
        _save(TIMER_FILE, sessions)
        return session
    raise ValueError("Timer session not found.")


def discard_timer(session_id: int) -> dict:
    sessions = _load(TIMER_FILE)
    for session in sessions:
        if session.get("id") != session_id:
            continue
        session["status"] = "discarded"
        _save(TIMER_FILE, sessions)
        return session
    raise ValueError("Timer session not found.")


def delete_timer_session(session_id: int):
    sessions = [session for session in _load(TIMER_FILE) if session.get("id") != session_id]
    _save(TIMER_FILE, sessions)


# ── Availability Calendar ───────────────────────────────────────────────────

def get_calendar_blocks() -> list:
    blocks = _load(CALENDAR_FILE)
    return sorted(blocks, key=lambda item: (item.get("date_from", ""), item.get("date_to", "")), reverse=True)


def add_calendar_block(date_from: str, date_to: str, label: str, block_type: str) -> dict:
    blocks = _load(CALENDAR_FILE)
    try:
        start = date.fromisoformat(date_from)
        end = date.fromisoformat(date_to)
    except ValueError as exc:
        raise ValueError("Invalid block dates.") from exc
    if end < start:
        start, end = end, start

    normalized_type = block_type if block_type in BLOCK_TYPES else "blocked"
    block = {
        "id": max((item.get("id", 0) for item in blocks), default=0) + 1,
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "label": (label or "Blocked").strip(),
        "type": normalized_type,
    }
    blocks.append(block)
    _save(CALENDAR_FILE, blocks)
    return block


def delete_calendar_block(block_id: int):
    blocks = [block for block in _load(CALENDAR_FILE) if block.get("id") != block_id]
    _save(CALENDAR_FILE, blocks)


def get_calendar_events(year: int, month: int) -> dict:
    _, month_days = calendar.monthrange(year, month)
    events: dict[str, dict] = {}
    for day in range(1, month_days + 1):
        day_key = date(year, month, day).isoformat()
        events[day_key] = {
            "projects": [],
            "hours": 0.0,
            "blocks": [],
            "status": "free",
        }

    # Aggregate work hours into visible days.
    for entry in get_workhours():
        day_key = entry.get("date", "")
        if day_key not in events:
            continue
        try:
            events[day_key]["hours"] = round(
                float(events[day_key]["hours"]) + float(entry.get("hours", 0) or 0),
                2,
            )
        except (TypeError, ValueError):
            continue

    # Mark scoped project windows.
    month_start = date(year, month, 1)
    month_end = date(year, month, month_days)
    for project in get_scoped_projects():
        raw_start = project.get("start_date") or project.get("target_date")
        raw_end = project.get("target_date") or project.get("start_date")
        if not raw_start or not raw_end:
            continue
        try:
            proj_start = date.fromisoformat(raw_start)
            proj_end = date.fromisoformat(raw_end)
        except ValueError:
            continue
        if proj_end < proj_start:
            proj_start, proj_end = proj_end, proj_start
        overlap_start = max(proj_start, month_start)
        overlap_end = min(proj_end, month_end)
        if overlap_end < overlap_start:
            continue
        cursor = overlap_start
        while cursor <= overlap_end:
            key = cursor.isoformat()
            events[key]["projects"].append(project.get("project_name", "Project"))
            cursor += timedelta(days=1)

    # Apply manual blocked ranges.
    for block in get_calendar_blocks():
        try:
            block_start = date.fromisoformat(block.get("date_from", ""))
            block_end = date.fromisoformat(block.get("date_to", ""))
        except ValueError:
            continue
        if block_end < block_start:
            block_start, block_end = block_end, block_start
        overlap_start = max(block_start, month_start)
        overlap_end = min(block_end, month_end)
        if overlap_end < overlap_start:
            continue
        cursor = overlap_start
        while cursor <= overlap_end:
            key = cursor.isoformat()
            label = block.get("label", "Blocked")
            events[key]["blocks"].append(label)
            cursor += timedelta(days=1)

    working_hours_per_day = float(get_settings().get("working_hours_per_day", 8.0) or 8.0)
    for day_data in events.values():
        if day_data["blocks"]:
            day_data["status"] = "blocked"
        elif float(day_data["hours"]) >= working_hours_per_day or bool(day_data["projects"]):
            day_data["status"] = "busy"
        elif float(day_data["hours"]) > 0:
            day_data["status"] = "light"
        else:
            day_data["status"] = "free"

    return events


def get_overdue_invoices() -> list:
    cfg = get_settings()
    late_fee_rate = float(cfg.get("late_fee_rate", DEFAULT_SETTINGS["late_fee_rate"]))
    today = date.today()
    overdue = []
    for inv in get_invoices():
        if inv.get("status") == "paid":
            continue
        due_date_str = inv.get("due_date")
        if not due_date_str:
            continue
        try:
            due_date = date.fromisoformat(due_date_str)
        except ValueError:
            continue
        if due_date >= today:
            continue
        days_overdue = (today - due_date).days
        total = float(inv.get("total", 0.0) or 0.0)
        late_fee_amount = round(total * (late_fee_rate / 100.0) * (days_overdue / 30.0), 2)
        inv_with_meta = dict(inv)
        inv_with_meta["days_overdue"] = days_overdue
        inv_with_meta["late_fee_amount"] = late_fee_amount
        overdue.append(inv_with_meta)
    return sorted(overdue, key=lambda item: item.get("days_overdue", 0), reverse=True)


def get_reminder_email_draft(invoice: dict) -> str:
    cfg = get_settings()
    days_overdue = invoice.get("days_overdue")
    if days_overdue is None:
        try:
            days_overdue = (date.today() - date.fromisoformat(invoice.get("due_date", date.today().isoformat()))).days
        except ValueError:
            days_overdue = 0
    amount = f"{invoice.get('currency_symbol', '$')}{float(invoice.get('total', 0.0)):.2f}"
    subject = f"Payment Reminder — Invoice {invoice.get('invoice_number', '')}"
    body = "\n".join([
        f"Subject: {subject}",
        "",
        f"Hi {invoice.get('client_name', 'there')},",
        "",
        f"This is a friendly reminder that invoice {invoice.get('invoice_number', '')} for {amount} was due on {invoice.get('due_date', '')} and is now {days_overdue} day(s) overdue.",
        "",
        "Please share payment confirmation at your earliest convenience.",
        "",
        f"Thank you,",
        f"{cfg.get('name', '')}",
    ])
    return body


def get_invoice_display_total(invoice: dict) -> str:
    cfg = get_settings()
    inv_currency = (invoice.get("currency") or cfg.get("currency", "USD")).upper()
    inv_symbol = invoice.get("currency_symbol") or CURRENCY_OPTIONS.get(inv_currency, "")
    inv_total = float(invoice.get("total", 0.0) or 0.0)

    base_currency = (invoice.get("base_currency") or cfg.get("currency", "USD")).upper()
    base_symbol = CURRENCY_OPTIONS.get(base_currency, "")
    exchange_rate = float(invoice.get("exchange_rate", 1.0) or 1.0)
    total_base = float(invoice.get("total_base", inv_total * exchange_rate) or 0.0)

    inv_text = f"{inv_symbol}{inv_total:,.2f} {inv_currency}".strip()
    if inv_currency != cfg.get("currency", "USD"):
        base_text = f"{base_symbol}{total_base:,.2f} {base_currency}".strip()
        return f"{inv_text}  (≈ {base_text})"
    return inv_text


# ── Proposal Templates ────────────────────────────────────────────────────────

TEMPLATES = {
    "web_design": {
        "title": "Web Design Project Proposal",
        "sections": [
            ("Project Overview", "Provide a 2-3 sentence summary of what you will build."),
            ("Deliverables", "List every page, feature, and asset you will deliver."),
            ("Timeline", "Break the project into milestones with target dates."),
            ("Pricing", "State your hourly rate or fixed price and payment schedule."),
            ("Revisions", "Specify how many revision rounds are included."),
            ("Terms", "Payment terms, IP ownership, cancellation policy."),
        ],
    },
    "content_writing": {
        "title": "Content Writing Proposal",
        "sections": [
            ("Scope of Work", "Number of articles/posts, word count, topics."),
            ("Research & SEO", "Keyword strategy, competitor analysis approach."),
            ("Timeline", "Turnaround per piece and total delivery date."),
            ("Pricing", "Per-word rate or flat fee per article."),
            ("Revisions", "Number of edits included post-delivery."),
            ("Terms", "Copyright transfer upon full payment."),
        ],
    },
    "software_dev": {
        "title": "Software Development Proposal",
        "sections": [
            ("Project Summary", "High-level description of the software you will build."),
            ("Technical Stack", "Languages, frameworks, databases, and hosting."),
            ("Features & Milestones", "Feature list grouped into sprints/phases."),
            ("Testing", "Unit tests, QA process, and acceptance criteria."),
            ("Pricing & Payment", "Fixed bid or T&M rate; milestone payment schedule."),
            ("Support & Maintenance", "Post-launch support window and SLA."),
        ],
    },
    "consulting": {
        "title": "Consulting Services Proposal",
        "sections": [
            ("Executive Summary", "Problem you're solving and value you bring."),
            ("Engagement Scope", "What's in-scope and explicitly out-of-scope."),
            ("Methodology", "How you will work — workshops, interviews, deliverables."),
            ("Timeline", "Start date, key checkpoints, end date."),
            ("Fees", "Day rate, estimated days, and total."),
            ("Terms", "Confidentiality, IP, termination clause."),
        ],
    },
    "graphic_design": {
        "title": "Graphic Design Proposal",
        "sections": [
            ("Project Brief", "Brand goals, target audience, design style."),
            ("Deliverables", "Logo, brand guide, assets — list all formats."),
            ("Timeline", "Concept phase, feedback rounds, final delivery."),
            ("Pricing", "Fixed fee or per-piece rate."),
            ("Revisions", "Number of revision rounds included."),
            ("Terms", "Source file ownership, usage rights."),
        ],
    },
    "video_editing": {
        "title": "Video Editing Proposal",
        "sections": [
            ("Project Scope", "Number of videos, length, style, purpose."),
            ("Deliverables", "File formats, resolutions, platform targets."),
            ("Timeline", "Draft delivery, review rounds, final delivery."),
            ("Pricing", "Per-minute rate or flat project fee."),
            ("Revisions", "Number of edit rounds included."),
            ("Terms", "Raw footage handling, copyright."),
        ],
    },
}


def get_templates() -> dict:
    return TEMPLATES


def get_template(key: str) -> dict | None:
    return TEMPLATES.get(key)


# ── Expenses ──────────────────────────────────────────────────────────────────

EXPENSE_CATEGORIES = [
    "Software & Tools", "Hardware", "Office Supplies", "Travel",
    "Marketing", "Education & Training", "Subscriptions",
    "Professional Services", "Communication", "Other",
]


def get_expenses() -> list:
    return _load(EXPENSES_FILE)


def add_expense(title: str, amount: float, category: str = "Other",
               expense_date: str = "", notes: str = "") -> dict:
    expenses = _load(EXPENSES_FILE)
    entry = {
        "id": max((e["id"] for e in expenses), default=0) + 1,
        "title": title,
        "amount": round(amount, 2),
        "category": category,
        "date": expense_date or date.today().isoformat(),
        "notes": notes,
    }
    expenses.append(entry)
    _save(EXPENSES_FILE, expenses)
    return entry


def update_expense(expense_id: int, title: str, amount: float,
                   category: str = "Other", expense_date: str = "",
                   notes: str = ""):
    expenses = _load(EXPENSES_FILE)
    for e in expenses:
        if e["id"] == expense_id:
            e["title"] = title
            e["amount"] = round(amount, 2)
            e["category"] = category
            e["date"] = expense_date or e["date"]
            e["notes"] = notes
            break
    _save(EXPENSES_FILE, expenses)


def delete_expense(expense_id: int):
    expenses = [e for e in _load(EXPENSES_FILE) if e["id"] != expense_id]
    _save(EXPENSES_FILE, expenses)


def get_expense_summary() -> dict:
    expenses = _load(EXPENSES_FILE)
    total = round(sum(float(e.get("amount", 0) or 0) for e in expenses), 2)
    by_category: dict = {}
    for e in expenses:
        cat = e.get("category", "Other")
        amt = float(e.get("amount", 0) or 0)
        by_category[cat] = round(by_category.get(cat, 0) + amt, 2)
    today = date.today()
    this_month = today.isoformat()[:7]
    month_total = round(sum(
        float(e.get("amount", 0) or 0)
        for e in expenses if e.get("date", "")[:7] == this_month
    ), 2)
    return {"total": total, "by_category": by_category, "month_total": month_total}


# ── CRM Interactions ─────────────────────────────────────────────────────────

CRM_TYPES = ["Call", "Email", "Meeting", "Proposal Sent", "Follow-up",
             "Contract Signed", "Payment Received", "Note"]


def get_interactions(client_id: int) -> list:
    all_interactions = _load("crm_interactions.json")
    return [i for i in all_interactions if i.get("client_id") == client_id]


def add_interaction(client_id: int, interaction_type: str, summary: str,
                    interaction_date: str = "", follow_up: str = "") -> dict:
    all_interactions = _load("crm_interactions.json")
    entry = {
        "id": max((i["id"] for i in all_interactions), default=0) + 1,
        "client_id": client_id,
        "type": interaction_type,
        "summary": summary,
        "date": interaction_date or date.today().isoformat(),
        "follow_up": follow_up,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    all_interactions.append(entry)
    _save("crm_interactions.json", all_interactions)
    return entry


def delete_interaction(interaction_id: int):
    interactions = [i for i in _load("crm_interactions.json")
                    if i["id"] != interaction_id]
    _save("crm_interactions.json", interactions)


# ── Client Notes ──────────────────────────────────────────────────────────────

def get_client_notes(client_id: int) -> list:
    notes = [n for n in _load(CLIENT_NOTES_FILE) if n.get("client_id") == client_id]
    return sorted(notes, key=lambda n: (bool(n.get("pinned", False)), n.get("updated", "")), reverse=True)


def get_client_note(note_id: int) -> dict | None:
    return next((n for n in _load(CLIENT_NOTES_FILE) if n.get("id") == note_id), None)


def add_client_note(client_id: int, title: str, content: str) -> dict:
    notes = _load(CLIENT_NOTES_FILE)
    today = date.today().isoformat()
    note = {
        "id": max((n["id"] for n in notes), default=0) + 1,
        "client_id": client_id,
        "title": title.strip() or "Untitled",
        "content": content.strip(),
        "created": today,
        "updated": today,
        "pinned": False,
    }
    notes.append(note)
    _save(CLIENT_NOTES_FILE, notes)
    return note


def update_client_note(note_id: int, title: str, content: str):
    notes = _load(CLIENT_NOTES_FILE)
    for note in notes:
        if note.get("id") == note_id:
            note["title"] = title.strip() or note.get("title", "Untitled")
            note["content"] = content.strip()
            note["updated"] = date.today().isoformat()
            break
    _save(CLIENT_NOTES_FILE, notes)


def delete_client_note(note_id: int):
    notes = [n for n in _load(CLIENT_NOTES_FILE) if n.get("id") != note_id]
    _save(CLIENT_NOTES_FILE, notes)


def toggle_note_pin(note_id: int):
    notes = _load(CLIENT_NOTES_FILE)
    for note in notes:
        if note.get("id") == note_id:
            note["pinned"] = not bool(note.get("pinned", False))
            note["updated"] = date.today().isoformat()
            break
    _save(CLIENT_NOTES_FILE, notes)


def search_client_notes(query: str) -> list:
    q = (query or "").strip().lower()
    if not q:
        return []
    clients = {c["id"]: c.get("name", "Unknown") for c in get_clients()}
    results = []
    for note in _load(CLIENT_NOTES_FILE):
        if q in note.get("title", "").lower() or q in note.get("content", "").lower():
            results.append({
                **note,
                "client_name": clients.get(note.get("client_id"), "Unknown"),
            })
    return sorted(results, key=lambda n: (bool(n.get("pinned", False)), n.get("updated", "")), reverse=True)


def get_upcoming_followups() -> list:
    """Return interactions with a follow_up date >= today, sorted by date.

    Uses ``get_clients()`` so any normalisation applied there is honoured.
    """
    today = date.today().isoformat()
    interactions = _load("crm_interactions.json")
    clients = {c["id"]: c["name"] for c in get_clients()}
    due = [
        {**i, "client_name": clients.get(i["client_id"], "Unknown")}
        for i in interactions
        if i.get("follow_up") and i["follow_up"] >= today
    ]
    return sorted(due, key=lambda x: x["follow_up"])


# ── Global Search ─────────────────────────────────────────────────────────────

def global_search(query: str) -> dict:
    q = query.lower().strip()
    if not q:
        return {
            "clients": [],
            "invoices": [],
            "hours": [],
            "expenses": [],
            "sdlc_templates": [],
            "scoped_projects": [],
            "notes": [],
            "quotes": [],
            "contracts": [],
            "milestones": [],
            "weekly_reviews": [],
        }
    clients = [
        c for c in _load("clients.json")
        if q in c.get("name", "").lower()
        or q in c.get("email", "").lower()
        or q in c.get("company", "").lower()
        or q in c.get("notes", "").lower()
    ]
    invoices = [
        i for i in _load("invoices.json")
        if q in i.get("client_name", "").lower()
        or q in i.get("invoice_number", "").lower()
        or q in i.get("notes", "").lower()
    ]
    hours = [
        e for e in _load("workhours.json")
        if q in e.get("task", "").lower()
        or q in e.get("client", "").lower()
        or q in e.get("notes", "").lower()
    ]
    expenses = [
        e for e in _load("expenses.json")
        if q in e.get("title", "").lower()
        or q in e.get("category", "").lower()
        or q in e.get("notes", "").lower()
    ]
    sdlc_templates = [
        template for template in get_sdlc_templates()
        if q in template.get("name", "").lower()
        or q in template.get("summary", "").lower()
        or q in template.get("best_for", "").lower()
        or q in " ".join(template.get("tags", [])).lower()
    ]
    scoped_projects = [
        project for project in get_scoped_projects()
        if q in project.get("project_name", "").lower()
        or q in project.get("summary", "").lower()
        or q in project.get("notes", "").lower()
        or q in project.get("client_name", "").lower()
        or q in project.get("template_name", "").lower()
    ]
    notes = search_client_notes(query)
    quotes = [
        quote for quote in get_quotes()
        if q in quote.get("quote_number", "").lower()
        or q in quote.get("client_name", "").lower()
        or q in quote.get("title", "").lower()
        or q in quote.get("notes", "").lower()
    ]
    contracts = [
        contract for contract in get_contracts()
        if q in contract.get("title", "").lower()
        or q in contract.get("client_name", "").lower()
        or q in contract.get("contract_type", "").lower()
        or q in contract.get("notes", "").lower()
    ]
    milestones = [
        m for m in _load(MILESTONE_FILE)
        if q in m.get("name", "").lower()
        or q in m.get("notes", "").lower()
    ]
    weekly_reviews = [
        r for r in _load("weekly_reviews.json")
        if q in r.get("went_well", "").lower()
        or q in r.get("improve", "").lower()
        or q in r.get("next_priority", "").lower()
    ]
    return {
        "clients": clients,
        "invoices": invoices,
        "hours": hours,
        "expenses": expenses,
        "sdlc_templates": sdlc_templates,
        "scoped_projects": scoped_projects,
        "notes": notes,
        "quotes": quotes,
        "contracts": contracts,
        "milestones": milestones,
        "weekly_reviews": weekly_reviews,
    }


# ── Profitability Report ──────────────────────────────────────────────────────

def profitability_report() -> list:
    """Per-client: total billed, total paid, hours logged, effective rate.

    All monetary/time values are cast defensively so a ``null``/missing field
    in a restored data file does not crash the /reports page.
    """
    invoices = _load("invoices.json")
    workhours = _load("workhours.json")
    clients = _load("clients.json")

    client_names = {c["name"] for c in clients if c.get("name")}
    # Also include clients from invoices/hours who may not be in clients.json
    all_names = client_names.union(
        {i["client_name"] for i in invoices if i.get("client_name")},
        {e["client"] for e in workhours if e.get("client")},
    )

    rows = []
    for name in sorted(all_names):
        client_invoices = [i for i in invoices if i.get("client_name") == name]
        total_billed = round(sum(
            float(i.get("total", 0) or 0) for i in client_invoices
        ), 2)
        total_paid = round(sum(
            float(i.get("total", 0) or 0)
            for i in client_invoices if i.get("status") == "paid"
        ), 2)
        total_hours = round(sum(
            float(e.get("hours", 0) or 0)
            for e in workhours if e.get("client") == name
        ), 2)
        # Effective rate = paid / hours
        eff_rate = round(total_paid / total_hours, 2) if total_hours > 0 else 0
        # Budget hours from invoice line items
        budgeted_hours = round(sum(
            float(item.get("hours", 0) or 0)
            for inv in client_invoices
            for item in inv.get("items", [])
        ), 2)
        rows.append({
            "client": name,
            "total_billed": total_billed,
            "total_paid": total_paid,
            "total_hours": total_hours,
            "budgeted_hours": budgeted_hours,
            "effective_rate": eff_rate,
            "invoice_count": len(client_invoices),
        })

    return sorted(rows, key=lambda x: -x["total_paid"])


# ── Backup & Restore ──────────────────────────────────────────────────────────

DATA_FILES = [
    "clients.json", "invoices.json", "workhours.json",
    "settings.json", "expenses.json", "crm_interactions.json",
    SDLC_TEMPLATE_FILE, SCOPED_PROJECT_FILE,
    CLIENT_NOTES_FILE, CONTRACT_FILE, QUOTE_FILE,
    TIMER_FILE, CALENDAR_FILE,
    "weekly_reviews.json", MILESTONE_FILE,
    CHANGE_ORDER_FILE,
]


def create_backup_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in DATA_FILES:
            fpath = os.path.join(DATA_DIR, fname)
            if os.path.exists(fpath):
                zf.write(fpath, arcname=fname)
    buf.seek(0)
    _append_audit_event("backup.export", "backup.zip", {"files": list(DATA_FILES)})
    return buf.read()


def _backups_dir() -> str:
    return os.path.join(DATA_DIR, "backups")


def _backup_index_path() -> str:
    return os.path.join(_backups_dir(), BACKUP_INDEX_FILE)


def _enforce_backup_retention(max_points: int = BACKUP_RETENTION):
    points = _safe_load_path(_backup_index_path(), [])
    if not isinstance(points, list):
        points = []
    if len(points) <= max_points:
        return

    points.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    keep = points[:max_points]
    drop = points[max_points:]
    for item in drop:
        fname = item.get("filename", "")
        if not fname:
            continue
        path = os.path.join(_backups_dir(), fname)
        if os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass
    _write_json_atomic_path(_backup_index_path(), keep)


def create_restore_point(label: str = "", reason: str = "manual") -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = _safe_slug(label or reason or "restore-point")
    filename = f"restore-point-{stamp}-{slug}.zip"
    os.makedirs(_backups_dir(), exist_ok=True)
    path = os.path.join(_backups_dir(), filename)

    with open(path, "wb") as f:
        f.write(create_backup_zip())

    point = {
        "filename": filename,
        "label": (label or reason or "restore-point").strip(),
        "reason": reason,
        "created_at": _now_utc(),
    }
    points = _safe_load_path(_backup_index_path(), [])
    if not isinstance(points, list):
        points = []
    points.append(point)
    _write_json_atomic_path(_backup_index_path(), points)
    _enforce_backup_retention(BACKUP_RETENTION)
    _append_audit_event("backup.restore_point.create", filename, {"label": point["label"], "reason": reason})
    return point


def list_restore_points() -> list:
    points = _safe_load_path(_backup_index_path(), [])
    if not isinstance(points, list):
        return []
    return sorted(points, key=lambda p: p.get("created_at", ""), reverse=True)


def restore_restore_point(filename: str) -> tuple[list, list]:
    path = os.path.join(_backups_dir(), filename)
    if not os.path.exists(path):
        return [], [f"Restore point '{filename}' was not found."]

    with open(path, "rb") as f:
        restored, errors = restore_from_zip(f.read())

    if restored:
        _append_audit_event("backup.restore_point.apply", filename, {"restored": restored})
    return restored, errors


def delete_restore_point(filename: str) -> bool:
    points = _safe_load_path(_backup_index_path(), [])
    if not isinstance(points, list):
        points = []
    remaining = [p for p in points if p.get("filename") != filename]
    changed = len(remaining) != len(points)
    if not changed:
        return False

    _write_json_atomic_path(_backup_index_path(), remaining)
    path = os.path.join(_backups_dir(), filename)
    if os.path.exists(path):
        try:
            os.unlink(path)
        except OSError:
            pass
    _append_audit_event("backup.restore_point.delete", filename, {})
    return True


def restore_from_zip(zip_bytes: bytes) -> tuple[list, list]:
    restored = []
    errors = []
    buf = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(buf, "r") as zf:
        for name in zf.namelist():
            if name in DATA_FILES:
                try:
                    content = zf.read(name)
                    json.loads(content)  # validate JSON
                    dest = os.path.join(DATA_DIR, name)
                    os.makedirs(DATA_DIR, exist_ok=True)
                    fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
                    with os.fdopen(fd, "wb") as f:
                        f.write(content)
                    os.replace(tmp_path, dest)
                    restored.append(name)
                except Exception as exc:
                    errors.append(f"{name}: {exc}")
    if restored:
        _append_audit_event("backup.restore_zip", "restore.zip", {"restored": restored, "errors": errors})
    return restored, errors


def _read_json_data_file(filename: str):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None, "missing"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), "ok"
    except json.JSONDecodeError as exc:
        return None, f"invalid_json: {exc}"
    except OSError as exc:
        return None, f"io_error: {exc}"


def scan_data_integrity(auto_repair: bool = False) -> dict:
    issues = []
    repairs = []
    loaded = {}

    expected = {fname: list for fname in DATA_FILES if fname != "settings.json"}
    expected["settings.json"] = dict

    for fname in DATA_FILES:
        payload, status = _read_json_data_file(fname)
        if status == "missing":
            continue
        if status != "ok":
            issues.append({
                "severity": "critical",
                "file": fname,
                "code": "invalid_json",
                "message": f"File cannot be parsed: {status}",
            })
            continue
        if not isinstance(payload, expected[fname]):
            issues.append({
                "severity": "major",
                "file": fname,
                "code": "invalid_top_level",
                "message": f"Expected {expected[fname].__name__} at top-level.",
            })
            if auto_repair:
                replacement = {} if expected[fname] is dict else []
                _write_json_atomic_path(os.path.join(DATA_DIR, fname), replacement)
                loaded[fname] = replacement
                repairs.append(f"Reset top-level structure for {fname}")
            continue
        loaded[fname] = payload

    clients = loaded.get("clients.json", []) if isinstance(loaded.get("clients.json", []), list) else []
    client_ids = {c.get("id") for c in clients if isinstance(c, dict)}
    client_names = {c.get("name") for c in clients if isinstance(c, dict) and c.get("name")}

    templates = loaded.get(SDLC_TEMPLATE_FILE, []) if isinstance(loaded.get(SDLC_TEMPLATE_FILE, []), list) else []
    template_ids = {t.get("id") for t in templates if isinstance(t, dict)}

    projects = loaded.get(SCOPED_PROJECT_FILE, []) if isinstance(loaded.get(SCOPED_PROJECT_FILE, []), list) else []
    milestones = loaded.get(MILESTONE_FILE, []) if isinstance(loaded.get(MILESTONE_FILE, []), list) else []
    contracts = loaded.get(CONTRACT_FILE, []) if isinstance(loaded.get(CONTRACT_FILE, []), list) else []
    invoices = loaded.get("invoices.json", []) if isinstance(loaded.get("invoices.json", []), list) else []
    quotes = loaded.get(QUOTE_FILE, []) if isinstance(loaded.get(QUOTE_FILE, []), list) else []

    valid_projects = []
    for project in projects:
        if not isinstance(project, dict):
            issues.append({
                "severity": "major",
                "file": SCOPED_PROJECT_FILE,
                "code": "invalid_record",
                "message": "Non-object project record detected.",
            })
            continue
        cid = project.get("client_id")
        tid = project.get("template_id")
        missing = []
        if cid not in client_ids:
            missing.append("client_id")
        if tid not in template_ids:
            missing.append("template_id")
        if missing:
            issues.append({
                "severity": "major",
                "file": SCOPED_PROJECT_FILE,
                "code": "orphan_project",
                "message": f"Project id={project.get('id')} has missing {'/'.join(missing)} reference.",
            })
            if auto_repair:
                repairs.append(f"Removed orphan project id={project.get('id')}")
                continue
        valid_projects.append(project)

    valid_project_ids = {p.get("id") for p in valid_projects if isinstance(p, dict)}
    valid_milestones = []
    for milestone in milestones:
        if not isinstance(milestone, dict):
            issues.append({
                "severity": "major",
                "file": MILESTONE_FILE,
                "code": "invalid_record",
                "message": "Non-object milestone record detected.",
            })
            continue
        if milestone.get("project_id") not in valid_project_ids:
            issues.append({
                "severity": "major",
                "file": MILESTONE_FILE,
                "code": "orphan_milestone",
                "message": f"Milestone id={milestone.get('id')} references missing project.",
            })
            if auto_repair:
                repairs.append(f"Removed orphan milestone id={milestone.get('id')}")
                continue
        valid_milestones.append(milestone)

    valid_contracts = []
    for contract in contracts:
        if not isinstance(contract, dict):
            issues.append({
                "severity": "major",
                "file": CONTRACT_FILE,
                "code": "invalid_record",
                "message": "Non-object contract record detected.",
            })
            continue
        cid = contract.get("client_id")
        if cid is not None and cid not in client_ids:
            issues.append({
                "severity": "minor",
                "file": CONTRACT_FILE,
                "code": "orphan_contract_client",
                "message": f"Contract id={contract.get('id')} references missing client_id.",
            })
            if auto_repair:
                contract = {**contract, "client_id": None}
                repairs.append(f"Cleared missing client reference in contract id={contract.get('id')}")
        valid_contracts.append(contract)

    for invoice in invoices:
        if isinstance(invoice, dict):
            cname = invoice.get("client_name")
            if cname and cname not in client_names:
                issues.append({
                    "severity": "minor",
                    "file": "invoices.json",
                    "code": "unknown_client_name",
                    "message": f"Invoice id={invoice.get('id')} references unknown client_name.",
                })

    for quote in quotes:
        if isinstance(quote, dict):
            cname = quote.get("client_name")
            if cname and cname not in client_names:
                issues.append({
                    "severity": "minor",
                    "file": QUOTE_FILE,
                    "code": "unknown_client_name",
                    "message": f"Quote id={quote.get('id')} references unknown client_name.",
                })

    if auto_repair:
        if valid_projects != projects:
            _save(SCOPED_PROJECT_FILE, valid_projects)
        if valid_milestones != milestones:
            _save(MILESTONE_FILE, valid_milestones)
        if valid_contracts != contracts:
            _save(CONTRACT_FILE, valid_contracts)
        if repairs:
            _append_audit_event("integrity.repair", "data", {"repairs": repairs, "issue_count": len(issues)})

    return {
        "checked_at": _now_utc(),
        "issues": issues,
        "repairs": repairs,
        "counts": {
            "critical": sum(1 for i in issues if i["severity"] == "critical"),
            "major": sum(1 for i in issues if i["severity"] == "major"),
            "minor": sum(1 for i in issues if i["severity"] == "minor"),
        },
    }


# ── Tax Estimator ─────────────────────────────────────────────────────────────

def estimate_tax(total_income: float, tax_rate: float,
                 total_expenses: float = 0.0) -> dict:
    taxable = max(0.0, round(total_income - total_expenses, 2))
    annual_tax = round(taxable * tax_rate / 100, 2)
    quarterly_tax = round(annual_tax / 4, 2)
    monthly_set_aside = round(annual_tax / 12, 2)
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "taxable_income": taxable,
        "tax_rate": tax_rate,
        "annual_tax": annual_tax,
        "quarterly_tax": quarterly_tax,
        "monthly_set_aside": monthly_set_aside,
    }


# ── N3: SCOPE CREEP DETECTOR ───────────────────────────────────────────────────

def get_scope_status(project_id: int) -> dict:
    """
    Compare budgeted hours vs actual logged hours for a project.
    Returns dict with status, budget_hours, actual_hours, utilisation %, warning.
    """
    project = get_scoped_project(project_id)
    if not project:
        return {}

    budget_hours = project.get("budget_hours", 0)
    client_name = project.get("client_name", "")

    # Sum hours logged for this client from workhours.json
    all_hours = get_workhours()
    actual_hours = sum(
        h.get("hours", 0) for h in all_hours
        if h.get("client", "").strip().lower() == client_name.strip().lower()
    )

    # Calculate utilisation
    if budget_hours > 0:
        utilisation = round(actual_hours / budget_hours, 4)
    else:
        utilisation = None

    # Determine status
    if utilisation is None:
        status = "no_budget"
    elif utilisation < 0.80:
        status = "on_track"
    elif utilisation < 1.00:
        status = "warning"
    else:
        status = "over_budget"

    # Hours over budget
    hours_over = max(0, actual_hours - budget_hours)

    return {
        "project_id": project_id,
        "project_name": project.get("name", ""),
        "client_name": client_name,
        "status": status,
        "budget_hours": budget_hours,
        "actual_hours": actual_hours,
        "utilisation": utilisation,
        "utilisation_percent": round(utilisation * 100, 1) if utilisation else None,
        "hours_over": hours_over,
    }


def get_all_scope_statuses() -> list:
    """
    Returns scope status for all active scoped projects, sorted by utilisation desc.
    """
    projects = get_scoped_projects()
    statuses = [get_scope_status(p["id"]) for p in projects if p.get("id")]
    # Sort by utilisation descending (over-budget first)
    return sorted(
        statuses,
        key=lambda s: (s.get("utilisation") or -1),
        reverse=True
    )


# ── N4: INVOICE AGEING REPORT ──────────────────────────────────────────────────

def get_ar_ageing() -> dict:
    """
    Classify unpaid invoices by age into buckets: current, 1-30, 31-60, 60+.
    Returns dict with bucket totals and per-invoice details.
    """
    today = date.today()
    invoices = get_invoices()
    unpaid = [i for i in invoices if i.get("status") != "paid"]

    buckets = {
        "current": {"total": 0.0, "count": 0, "invoices": []},
        "1_30": {"total": 0.0, "count": 0, "invoices": []},
        "31_60": {"total": 0.0, "count": 0, "invoices": []},
        "60_plus": {"total": 0.0, "count": 0, "invoices": []},
    }

    for inv in unpaid:
        due_date_str = inv.get("due_date", "")
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            # Skip invalid dates
            continue

        days_age = (today - due_date).days

        # Get invoice total (multi-currency aware)
        total = inv.get("total_base", inv.get("total", 0.0))

        invoice_entry = {
            "id": inv.get("id"),
            "invoice_number": inv.get("invoice_number", ""),
            "client_name": inv.get("client_name", ""),
            "due_date": due_date_str,
            "days_age": days_age,
            "total": total,
            "status": inv.get("status", "unpaid"),
        }

        if days_age < 0:
            bucket = "current"
        elif days_age <= 30:
            bucket = "1_30"
        elif days_age <= 60:
            bucket = "31_60"
        else:
            bucket = "60_plus"

        buckets[bucket]["total"] += total
        buckets[bucket]["count"] += 1
        buckets[bucket]["invoices"].append(invoice_entry)

    # Sort invoices within each bucket by due_date
    for bucket in buckets.values():
        bucket["invoices"].sort(key=lambda x: x["due_date"], reverse=True)

    # Calculate grand total
    grand_total = sum(b["total"] for b in buckets.values())

    return {
        "current": buckets["current"],
        "1_30": buckets["1_30"],
        "31_60": buckets["31_60"],
        "60_plus": buckets["60_plus"],
        "grand_total": grand_total,
    }


# ── N6: WEEKLY REVIEW & RETROSPECTIVE ──────────────────────────────────────────

REVIEW_FILE = "weekly_reviews.json"


def get_weekly_reviews() -> list:
    """Get all weekly reviews, sorted by week_start descending."""
    reviews = _load(REVIEW_FILE)
    return sorted(reviews, key=lambda r: r.get("week_start", ""), reverse=True)


def get_weekly_review(review_id: int) -> dict | None:
    """Get a single review by ID."""
    reviews = _load(REVIEW_FILE)
    return next((r for r in reviews if r.get("id") == review_id), None)


def get_review_for_week(week_start_date: str) -> dict | None:
    """Find existing review for a given week (ISO date string)."""
    reviews = _load(REVIEW_FILE)
    return next((r for r in reviews if r.get("week_start") == week_start_date), None)


def build_weekly_prefill(week_start_date: str) -> dict:
    """
    Build a dict with aggregated weekly stats for prefilling the review form.
    Returns income, hours logged, top clients, and top tasks for the week.
    """
    from datetime import datetime, timedelta

    try:
        week_start = datetime.strptime(week_start_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        week_start = date.today()

    week_end = week_start + timedelta(days=6)
    week_start_str = week_start.isoformat()
    week_end_str = week_end.isoformat()

    # Get hours logged this week
    all_hours = get_workhours()
    week_hours = [
        h for h in all_hours
        if week_start_str <= h.get("date", "") <= week_end_str
    ]
    total_hours = sum(h.get("hours", 0) for h in week_hours)

    # Get invoices issued this week
    all_invoices = get_invoices()
    week_invoices = [
        i for i in all_invoices
        if week_start_str <= i.get("issue_date", "") <= week_end_str
    ]
    week_income = sum(i.get("total_base", i.get("total", 0.0)) for i in week_invoices)

    # Top clients by hours
    client_hours = {}
    for h in week_hours:
        client = h.get("client", "").strip()
        if client:
            client_hours[client] = client_hours.get(client, 0) + h.get("hours", 0)

    top_clients = sorted(client_hours.items(), key=lambda x: x[1], reverse=True)[:3]

    # Top tasks
    task_counts = {}
    for h in week_hours:
        task = h.get("task", "").strip()
        if task:
            task_counts[task] = task_counts.get(task, 0) + 1

    top_tasks = sorted(task_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "week_start": week_start_date,
        "week_end": week_end_str,
        "total_hours": total_hours,
        "total_income": week_income,
        "top_clients": top_clients,
        "top_tasks": top_tasks,
    }


def save_weekly_review(week_start: str, went_well: str, improve: str,
                       next_priority: str) -> dict:
    """
    Save a new weekly review or update existing one for the week.
    Returns the saved review dict.
    """
    reviews = _load(REVIEW_FILE)
    review_id = max((r["id"] for r in reviews), default=0) + 1

    review = {
        "id": review_id,
        "week_start": week_start,
        "went_well": went_well.strip(),
        "improve": improve.strip(),
        "next_priority": next_priority.strip(),
        "created_at": date.today().isoformat(),
    }
    reviews.append(review)
    _save(REVIEW_FILE, reviews)
    return review


def update_weekly_review(review_id: int, went_well: str, improve: str,
                         next_priority: str) -> dict | None:
    """Update an existing review."""
    reviews = _load(REVIEW_FILE)
    for r in reviews:
        if r.get("id") == review_id:
            r["went_well"] = went_well.strip()
            r["improve"] = improve.strip()
            r["next_priority"] = next_priority.strip()
            _save(REVIEW_FILE, reviews)
            return r
    return None


def delete_weekly_review(review_id: int) -> bool:
    """Delete a review by ID."""
    reviews = _load(REVIEW_FILE)
    original_len = len(reviews)
    reviews = [r for r in reviews if r.get("id") != review_id]
    if len(reviews) < original_len:
        _save(REVIEW_FILE, reviews)
        return True
    return False


def search_reviews(query: str) -> list:
    """Search reviews by went_well, improve, or next_priority text."""
    q = query.strip().lower()
    reviews = get_weekly_reviews()
    return [
        r for r in reviews
        if q in r.get("went_well", "").lower()
        or q in r.get("improve", "").lower()
        or q in r.get("next_priority", "").lower()
    ]


# ── N7: CLIENT RATE & REVISION HISTORY ───────────────────────────────────────

def get_client_rate_at(client_id: int, date_str: str) -> float:
    """Return applicable client hourly rate at a specific date."""
    client = get_client(client_id)
    if not client:
        return 0.0

    try:
        target = date.fromisoformat((date_str or "").strip()).isoformat()
    except ValueError:
        target = date.today().isoformat()

    default_rate = float(client.get("default_rate", 0.0) or 0.0)
    history = sorted(client.get("rate_history", []), key=lambda e: e.get("from", ""))

    applicable = [entry for entry in history if entry.get("from", "") <= target]
    if not applicable:
        return default_rate

    try:
        return float(applicable[-1].get("rate", default_rate) or default_rate)
    except (TypeError, ValueError):
        return default_rate


def add_client_rate_entry(client_id: int, rate: float, from_date: str, note: str = "") -> dict:
    """Append a new rate history entry for a client and keep history sorted."""
    if rate <= 0:
        raise ValueError("Rate must be greater than zero.")
    try:
        effective_from = date.fromisoformat((from_date or "").strip()).isoformat()
    except ValueError as exc:
        raise ValueError("Invalid effective date.") from exc

    clients = _load("clients.json")
    for client in clients:
        if client.get("id") == client_id:
            history = list(client.get("rate_history", []))
            entry = {
                "rate": float(rate),
                "from": effective_from,
                "note": note.strip(),
            }
            history.append(entry)
            history.sort(key=lambda e: e.get("from", ""))
            client["rate_history"] = history
            _save("clients.json", clients)
            return entry

    raise ValueError("Client not found.")


# ── N8: FINANCIAL SNAPSHOT ───────────────────────────────────────────────────

def get_financial_snapshot() -> dict:
    """Aggregate one-page financial KPIs for the current year."""
    cfg = get_settings()
    invoices = get_invoices()
    expenses = get_expenses()
    workhours = get_workhours()
    today = date.today()
    this_year = today.year

    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return default

    def _normalized_total(inv: dict) -> float:
        if inv.get("total_base") is not None:
            return _safe_float(inv.get("total_base"))
        return _safe_float(inv.get("total")) * _safe_float(inv.get("exchange_rate", 1.0), 1.0)

    def _in_year(date_str: str, year: int) -> bool:
        if not date_str:
            return False
        try:
            return date.fromisoformat(date_str).year == year
        except ValueError:
            return False

    paid_ytd = [
        inv for inv in invoices
        if inv.get("status") == "paid" and _in_year(inv.get("issue_date", ""), this_year)
    ]
    ytd_income = round(sum(_normalized_total(inv) for inv in paid_ytd), 2)

    ytd_expenses = round(sum(
        _safe_float(exp.get("amount"))
        for exp in expenses
        if _in_year(exp.get("date", ""), this_year)
    ), 2)
    ytd_net = round(ytd_income - ytd_expenses, 2)

    ytd_hours = round(sum(
        _safe_float(row.get("hours"))
        for row in workhours
        if _in_year(row.get("date", ""), this_year)
    ), 2)
    effective_hourly = round(ytd_income / ytd_hours, 2) if ytd_hours > 0 else 0.0
    avg_invoice_value = round(ytd_income / len(paid_ytd), 2) if paid_ytd else 0.0

    outstanding = round(sum(
        _normalized_total(inv)
        for inv in invoices
        if inv.get("status") != "paid"
    ), 2)

    tax_rate = _safe_float(cfg.get("tax_rate", 20.0), 20.0)
    tax_estimate = estimate_tax(ytd_income, tax_rate, ytd_expenses)

    # Last 6 months including current month, chronological order.
    month_cursor = date(today.year, today.month, 1)
    month_keys = []
    for _ in range(6):
        month_keys.append(month_cursor.strftime("%Y-%m"))
        if month_cursor.month == 1:
            month_cursor = date(month_cursor.year - 1, 12, 1)
        else:
            month_cursor = date(month_cursor.year, month_cursor.month - 1, 1)
    month_keys.reverse()

    income_by_month: dict[str, float] = {k: 0.0 for k in month_keys}
    expenses_by_month: dict[str, float] = {k: 0.0 for k in month_keys}

    for inv in paid_ytd:
        month = (inv.get("issue_date", "") or "")[:7]
        if month in income_by_month:
            income_by_month[month] = round(income_by_month[month] + _normalized_total(inv), 2)

    for exp in expenses:
        month = (exp.get("date", "") or "")[:7]
        if month in expenses_by_month:
            expenses_by_month[month] = round(expenses_by_month[month] + _safe_float(exp.get("amount")), 2)

    months = []
    for month in month_keys:
        inc = income_by_month.get(month, 0.0)
        exp = expenses_by_month.get(month, 0.0)
        months.append({
            "month": month,
            "income": round(inc, 2),
            "expenses": round(exp, 2),
            "net": round(inc - exp, 2),
        })

    top_clients_map: dict[str, float] = {}
    for inv in paid_ytd:
        name = inv.get("client_name", "Unknown") or "Unknown"
        top_clients_map[name] = round(top_clients_map.get(name, 0.0) + _normalized_total(inv), 2)
    top_clients = [
        {"client": client, "income": amount}
        for client, amount in sorted(top_clients_map.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return {
        "ytd_income": ytd_income,
        "ytd_expenses": ytd_expenses,
        "ytd_net": ytd_net,
        "tax_estimate": tax_estimate.get("annual_tax", 0.0),
        "tax_rate_used": tax_rate,
        "outstanding": outstanding,
        "effective_hourly": effective_hourly,
        "avg_invoice_value": avg_invoice_value,
        "months": months,
        "top_clients": top_clients,
    }


# ── N9: OPERATIONAL EFFICIENCY (LEVEL 2) ───────────────────────────────────

def _parse_csv_rows(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        rows.append({(k or "").strip(): (v or "").strip() for k, v in row.items()})
    return rows


def _parse_xlsx_rows(file_bytes: bytes) -> list[dict]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ValueError("XLSX import requires openpyxl (pip install openpyxl).") from exc

    wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    values = list(ws.values)
    if not values:
        return []
    headers = [str(h or "").strip() for h in values[0]]
    rows = []
    for raw in values[1:]:
        row = {}
        for idx, head in enumerate(headers):
            row[head] = str(raw[idx] if idx < len(raw) and raw[idx] is not None else "").strip()
        rows.append(row)
    return rows


def import_preview(dataset: str, file_name: str, file_bytes: bytes) -> tuple[list[dict], list[str]]:
    dataset = (dataset or "").strip().lower()
    errors = []

    lower = file_name.lower()
    if lower.endswith(".csv"):
        rows = _parse_csv_rows(file_bytes)
    elif lower.endswith(".xlsx"):
        try:
            rows = _parse_xlsx_rows(file_bytes)
        except ValueError as exc:
            return [], [str(exc)]
    else:
        return [], ["Only CSV and XLSX import files are supported."]
    if not rows:
        return [], ["No rows found in uploaded file."]

    required = {
        "clients": {"name", "email"},
        "workhours": {"task", "client", "hours", "date"},
        "expenses": {"title", "amount", "category", "date"},
        "invoices": {"client_name", "due_date", "total"},
    }
    if dataset not in required:
        return [], ["Unsupported dataset for import."]

    headers = set(rows[0].keys())
    missing = [h for h in required[dataset] if h not in headers]
    if missing:
        errors.append(f"Missing required column(s): {', '.join(missing)}")

    normalized = []
    for idx, row in enumerate(rows, start=1):
        try:
            if dataset == "clients":
                normalized.append({
                    "name": row.get("name", ""),
                    "email": row.get("email", ""),
                    "phone": row.get("phone", ""),
                    "company": row.get("company", ""),
                    "default_rate": float(row.get("default_rate", 0) or 0),
                })
            elif dataset == "workhours":
                normalized.append({
                    "task": row.get("task", ""),
                    "client": row.get("client", ""),
                    "hours": float(row.get("hours", 0) or 0),
                    "date": row.get("date", ""),
                    "notes": row.get("notes", ""),
                })
            elif dataset == "expenses":
                normalized.append({
                    "title": row.get("title", ""),
                    "amount": float(row.get("amount", 0) or 0),
                    "category": row.get("category", "Other") or "Other",
                    "date": row.get("date", ""),
                    "notes": row.get("notes", ""),
                })
            elif dataset == "invoices":
                normalized.append({
                    "client_name": row.get("client_name", ""),
                    "due_date": row.get("due_date", ""),
                    "total": float(row.get("total", 0) or 0),
                    "status": (row.get("status", "unpaid") or "unpaid").lower(),
                })
        except ValueError:
            errors.append(f"Row {idx}: invalid numeric value.")
    return normalized, errors


def import_commit(dataset: str, rows: list[dict]) -> int:
    dataset = (dataset or "").strip().lower()
    created = 0
    for row in rows:
        if dataset == "clients":
            if not row.get("name"):
                continue
            add_client(
                name=row.get("name", "").strip(),
                email=row.get("email", "").strip(),
                phone=row.get("phone", ""),
                company=row.get("company", ""),
                default_rate=float(row.get("default_rate", 0) or 0),
            )
            created += 1
        elif dataset == "workhours":
            if not row.get("task"):
                continue
            log_hours(
                task=row.get("task", ""),
                client=row.get("client", "Unknown"),
                hours=float(row.get("hours", 0) or 0),
                log_date=row.get("date", "") or date.today().isoformat(),
                notes=row.get("notes", ""),
            )
            created += 1
        elif dataset == "expenses":
            if not row.get("title"):
                continue
            add_expense(
                title=row.get("title", ""),
                amount=float(row.get("amount", 0) or 0),
                category=row.get("category", "Other"),
                expense_date=row.get("date", "") or date.today().isoformat(),
                notes=row.get("notes", ""),
            )
            created += 1
        elif dataset == "invoices":
            if not row.get("client_name"):
                continue
            inv = create_invoice(
                client_name=row.get("client_name", ""),
                items=[{"description": "Imported", "hours": 1.0, "rate": float(row.get("total", 0) or 0)}],
                due_date=row.get("due_date", "") or date.today().isoformat(),
            )
            if row.get("status") == "paid":
                mark_invoice_paid(inv["id"])
            created += 1
    return created


def recurring_reminders(offsets: list[int] | None = None) -> list[dict]:
    offsets = offsets or [7, 3, -3]
    today = date.today()
    items = []
    for inv in get_invoices():
        if inv.get("payment_status") == "paid":
            continue
        try:
            due = date.fromisoformat(inv.get("due_date", ""))
        except ValueError:
            continue
        days_to_due = (due - today).days
        for off in offsets:
            if off >= 0 and days_to_due == off:
                items.append({
                    "invoice_id": inv.get("id"),
                    "invoice_number": inv.get("invoice_number"),
                    "client_name": inv.get("client_name"),
                    "label": f"T-{off}",
                    "days_to_due": days_to_due,
                })
            if off < 0 and days_to_due == off:
                items.append({
                    "invoice_id": inv.get("id"),
                    "invoice_number": inv.get("invoice_number"),
                    "client_name": inv.get("client_name"),
                    "label": f"Overdue +{abs(off)}",
                    "days_to_due": days_to_due,
                })
    return sorted(items, key=lambda i: (i.get("days_to_due", 0), i.get("invoice_number", "")))


def filter_invoices(invoices: list[dict], filters: dict) -> list[dict]:
    client = (filters.get("client") or "").strip().lower()
    status = (filters.get("status") or "").strip().lower()
    start = (filters.get("start_date") or "").strip()
    end = (filters.get("end_date") or "").strip()

    out = invoices
    if client:
        out = [inv for inv in out if client in str(inv.get("client_name", "")).lower()]
    if status:
        out = [inv for inv in out if str(inv.get("payment_status") or inv.get("status", "")).lower() == status]
    if start:
        out = [inv for inv in out if str(inv.get("issue_date", "")) >= start]
    if end:
        out = [inv for inv in out if str(inv.get("issue_date", "")) <= end]
    return out


def get_invoice_saved_views() -> list[dict]:
    views = _safe_load_path(os.path.join(DATA_DIR, INVOICE_VIEWS_FILE), [])
    if not isinstance(views, list):
        return []
    return views


def save_invoice_view(name: str, filters: dict) -> dict:
    label = (name or "").strip()
    if not label:
        raise ValueError("View name is required.")
    views = get_invoice_saved_views()
    views = [v for v in views if v.get("name") != label]
    view = {
        "name": label,
        "filters": {
            "client": filters.get("client", ""),
            "status": filters.get("status", ""),
            "start_date": filters.get("start_date", ""),
            "end_date": filters.get("end_date", ""),
        },
        "created_at": _now_utc(),
    }
    views.append(view)
    _write_json_atomic_path(os.path.join(DATA_DIR, INVOICE_VIEWS_FILE), views)
    return view


def delete_invoice_view(name: str) -> bool:
    views = get_invoice_saved_views()
    remaining = [v for v in views if v.get("name") != name]
    if len(remaining) == len(views):
        return False
    _write_json_atomic_path(os.path.join(DATA_DIR, INVOICE_VIEWS_FILE), remaining)
    return True


def bulk_invoice_action(ids: list[int], action: str) -> int:
    valid = [int(x) for x in ids if str(x).isdigit()]
    if not valid:
        return 0
    count = 0
    if action == "mark_paid":
        for inv_id in valid:
            try:
                mark_invoice_paid(inv_id)
                count += 1
            except ValueError:
                pass
        return count
    if action == "delete":
        for inv_id in valid:
            delete_invoice(inv_id)
            count += 1
        return count
    if action == "mark_unpaid":
        invoices = _load("invoices.json")
        for inv in invoices:
            if inv.get("id") in valid:
                inv["status"] = "unpaid"
                inv["payment_status"] = "unpaid"
                inv["payments"] = []
                count += 1
        _save("invoices.json", invoices)
        return count
    return 0


def invoice_ids_to_csv(ids: list[int]) -> str:
    valid = {int(x) for x in ids if str(x).isdigit()}
    rows = [inv for inv in get_invoices() if inv.get("id") in valid]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Invoice #", "Client", "Issue Date", "Due Date", "Total", "Paid", "Balance", "Status"])
    for inv in rows:
        writer.writerow([
            inv.get("invoice_number", ""),
            inv.get("client_name", ""),
            inv.get("issue_date", ""),
            inv.get("due_date", ""),
            inv.get("total", 0.0),
            inv.get("total_paid", 0.0),
            inv.get("balance_due", 0.0),
            inv.get("payment_status", inv.get("status", "unpaid")),
        ])
    return out.getvalue()


def _attachment_dir() -> str:
    return os.path.join(DATA_DIR, "attachments")


def _attachment_path() -> str:
    return os.path.join(DATA_DIR, ATTACHMENT_META_FILE)


def add_attachment(entity_type: str, entity_id: int, file_name: str, file_bytes: bytes) -> dict:
    os.makedirs(_attachment_dir(), exist_ok=True)
    original = os.path.basename(file_name or "file")
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in original)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    stored = f"{stamp}_{safe_name}"
    path = os.path.join(_attachment_dir(), stored)
    with open(path, "wb") as f:
        f.write(file_bytes)

    meta = _safe_load_path(_attachment_path(), [])
    if not isinstance(meta, list):
        meta = []
    rec = {
        "id": max((m.get("id", 0) for m in meta), default=0) + 1,
        "entity_type": entity_type,
        "entity_id": int(entity_id),
        "original_name": original,
        "stored_name": stored,
        "size": len(file_bytes),
        "uploaded_at": _now_utc(),
    }
    meta.append(rec)
    _write_json_atomic_path(_attachment_path(), meta)
    return rec


def list_attachments(entity_type: str, entity_id: int) -> list:
    meta = _safe_load_path(_attachment_path(), [])
    if not isinstance(meta, list):
        return []
    return [m for m in meta if m.get("entity_type") == entity_type and int(m.get("entity_id", 0)) == int(entity_id)]


def get_attachment(attachment_id: int) -> dict | None:
    meta = _safe_load_path(_attachment_path(), [])
    if not isinstance(meta, list):
        return None
    return next((m for m in meta if int(m.get("id", 0)) == int(attachment_id)), None)


def delete_attachment(attachment_id: int) -> bool:
    meta = _safe_load_path(_attachment_path(), [])
    if not isinstance(meta, list):
        return False
    target = next((m for m in meta if int(m.get("id", 0)) == int(attachment_id)), None)
    if not target:
        return False
    path = os.path.join(_attachment_dir(), target.get("stored_name", ""))
    if os.path.exists(path):
        try:
            os.unlink(path)
        except OSError:
            pass
    meta = [m for m in meta if int(m.get("id", 0)) != int(attachment_id)]
    _write_json_atomic_path(_attachment_path(), meta)
    return True
