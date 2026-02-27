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
        return {"clients": [], "invoices": [], "hours": [], "expenses": []}
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
    return {"clients": clients, "invoices": invoices,
            "hours": hours, "expenses": expenses}


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
