"""
Workflow Toolkit (WFT) - business logic helpers
Covers: invoice generation, client tracker, workhour analytics, proposal templates.
"""

import json
import os
from datetime import date, datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _load(filename: str) -> list:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def _save(filename: str, data: list):
    path = os.path.join(DATA_DIR, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── Settings ──────────────────────────────────────────────────────────────────

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "name": "Your Name",
    "business": "Freelancer",
    "currency": "USD",
    "currency_symbol": "$",
    "default_rate": 50.0,
    "working_hours_per_day": 8.0,
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
                       target_date: str = "") -> dict:
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
                          target_date: str = ""):
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


def save_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


# ── Clients ──────────────────────────────────────────────────────────────────

def get_clients() -> list:
    return _load("clients.json")


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
    return _load("invoices.json")


def create_invoice(client_name: str, items: list[dict], due_date: str,
                   notes: str = "", currency: str = "USD",
                   currency_symbol: str = "$", tax_rate: float = 0.0) -> dict:
    """
    items: [{"description": str, "hours": float, "rate": float}, ...]
    """
    invoices = _load("invoices.json")
    inv_id = max((i["id"] for i in invoices), default=0) + 1

    for item in items:
        item["amount"] = round(item["hours"] * item["rate"], 2)
    subtotal = round(sum(i["amount"] for i in items), 2)
    tax_amount = round(subtotal * tax_rate / 100, 2)
    total = round(subtotal + tax_amount, 2)

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
        "status": "unpaid",
        "notes": notes,
    }
    invoices.append(invoice)
    _save("invoices.json", invoices)
    return invoice


def mark_invoice_paid(inv_id: int):
    invoices = _load("invoices.json")
    found = False
    for inv in invoices:
        if inv["id"] == inv_id:
            inv["status"] = "paid"
            found = True
    if not found:
        raise ValueError(f"Invoice #{inv_id} not found.")
    _save("invoices.json", invoices)


def delete_invoice(inv_id: int):
    invoices = [i for i in _load("invoices.json") if i["id"] != inv_id]
    _save("invoices.json", invoices)


def get_earnings_summary() -> dict:
    """Total paid, total outstanding, hours this week, expenses, net profit."""
    invoices = _load("invoices.json")
    workhours = _load("workhours.json")
    expenses = _load("expenses.json")

    total_paid = round(sum(i["total"] for i in invoices if i.get("status") == "paid"), 2)
    total_outstanding = round(sum(i["total"] for i in invoices if i.get("status") != "paid"), 2)
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

    # Income by month (last 6 months) for charts
    income_by_month: dict = {}
    for inv in invoices:
        if inv.get("status") == "paid" and inv.get("issue_date"):
            month = inv["issue_date"][:7]
            income_by_month[month] = round(income_by_month.get(month, 0) + inv["total"], 2)

    # Income by client for pie chart
    income_by_client: dict = {}
    for inv in invoices:
        if inv.get("status") == "paid":
            name = inv.get("client_name", "Unknown")
            income_by_client[name] = round(income_by_client.get(name, 0) + inv["total"], 2)

    # Hours by week (last 8 weeks)
    weekly_hours = _weekly_hours(workhours)

    return {
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "hours_this_week": hours_this_week,
        "overdue_count": overdue_count,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "income_by_month": dict(sorted(income_by_month.items())[-6:]),
        "income_by_client": dict(sorted(income_by_client.items(), key=lambda x: -x[1])[:8]),
        "weekly_hours": weekly_hours,
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


def _weekly_hours(entries: list) -> list:
    """Return last 8 ISO-week labels and their hour totals."""
    by_week: dict = {}
    for e in entries:
        d = date.fromisoformat(e["date"])
        iso = d.isocalendar()
        label = f"W{iso.week:02d}"
        by_week[label] = round(by_week.get(label, 0) + e["hours"], 2)
    # Sort by label (week number) and return last 8
    sorted_weeks = sorted(by_week.items())[-8:]
    return [{"week": w, "hours": h} for w, h in sorted_weeks]


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
    return _load("expenses.json")


def add_expense(title: str, amount: float, category: str = "Other",
               expense_date: str = "", notes: str = "") -> dict:
    expenses = _load("expenses.json")
    entry = {
        "id": max((e["id"] for e in expenses), default=0) + 1,
        "title": title,
        "amount": round(amount, 2),
        "category": category,
        "date": expense_date or date.today().isoformat(),
        "notes": notes,
    }
    expenses.append(entry)
    _save("expenses.json", expenses)
    return entry


def update_expense(expense_id: int, title: str, amount: float,
                   category: str = "Other", expense_date: str = "",
                   notes: str = ""):
    expenses = _load("expenses.json")
    for e in expenses:
        if e["id"] == expense_id:
            e["title"] = title
            e["amount"] = round(amount, 2)
            e["category"] = category
            e["date"] = expense_date or e["date"]
            e["notes"] = notes
            break
    _save("expenses.json", expenses)


def delete_expense(expense_id: int):
    expenses = [e for e in _load("expenses.json") if e["id"] != expense_id]
    _save("expenses.json", expenses)


def get_expense_summary() -> dict:
    expenses = _load("expenses.json")
    total = round(sum(e["amount"] for e in expenses), 2)
    by_category: dict = {}
    for e in expenses:
        cat = e.get("category", "Other")
        by_category[cat] = round(by_category.get(cat, 0) + e["amount"], 2)
    today = date.today()
    this_month = today.isoformat()[:7]
    month_total = round(sum(
        e["amount"] for e in expenses if e.get("date", "")[:7] == this_month
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


def get_upcoming_followups() -> list:
    """Return interactions with a follow_up date >= today, sorted by date."""
    today = date.today().isoformat()
    interactions = _load("crm_interactions.json")
    clients = {c["id"]: c["name"] for c in _load("clients.json")}
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
    return {
        "clients": clients,
        "invoices": invoices,
        "hours": hours,
        "expenses": expenses,
        "sdlc_templates": sdlc_templates,
        "scoped_projects": scoped_projects,
    }


# ── Profitability Report ──────────────────────────────────────────────────────

def profitability_report() -> list:
    """Per-client: total billed, total paid, hours logged, effective rate."""
    invoices = _load("invoices.json")
    workhours = _load("workhours.json")
    clients = _load("clients.json")

    client_names = {c["name"] for c in clients}
    # Also include clients from invoices/hours who may not be in clients.json
    all_names = client_names.union(
        {i["client_name"] for i in invoices},
        {e["client"] for e in workhours},
    )

    rows = []
    for name in sorted(all_names):
        client_invoices = [i for i in invoices if i.get("client_name") == name]
        total_billed = round(sum(i["total"] for i in client_invoices), 2)
        total_paid = round(sum(
            i["total"] for i in client_invoices if i.get("status") == "paid"
        ), 2)
        total_hours = round(sum(
            e["hours"] for e in workhours if e.get("client") == name
        ), 2)
        # Effective rate = paid / hours
        eff_rate = round(total_paid / total_hours, 2) if total_hours > 0 else 0
        # Budget hours from invoice line items
        budgeted_hours = round(sum(
            item.get("hours", 0)
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
]


def create_backup_zip() -> bytes:
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in DATA_FILES:
            fpath = os.path.join(DATA_DIR, fname)
            if os.path.exists(fpath):
                zf.write(fpath, arcname=fname)
    buf.seek(0)
    return buf.read()


def restore_from_zip(zip_bytes: bytes) -> list:
    import io
    import zipfile
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
                    with open(dest, "wb") as f:
                        f.write(content)
                    restored.append(name)
                except Exception as exc:
                    errors.append(f"{name}: {exc}")
    return restored, errors


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
