# ⚡ VishKron — Freelancer Toolkit (FLTK)

A self-hosted web application built with **Flask** that brings together every tool a freelancer needs in one place — from deadline prediction to invoicing, expense tracking, and profitability reports.

> Created by **srijan-xi** · *For the community, by the community.*

---

## Features

### 🎯 Deadline Predictor (DRP)
- Predicts whether a task can be completed before its deadline based on estimated hours, daily workload, and historical speed.
- Stores prediction history with the ability to review or clear past entries.

### 📄 Proposal Templates
- Browse and preview ready-to-use freelance proposal templates.

### 👥 Client Tracker
- Add, edit, and manage clients with contact info and currency preferences.
- Dedicated CRM view per client showing linked invoices, scoped projects, interactions, and pinned notes.

### 📝 Client Notes & Meeting Logs
- Store rich notes per client with title/content.
- Pin important notes and search them globally.

### 🧾 Invoicing
- Create, view, and manage invoices.
- Generate and download invoices as **PDF**.
- Overdue invoice detection with days overdue and reminder drafts.
- Multi-currency support with manual exchange rate and base-currency totals.

### 💼 Quotes / Estimates
- Create itemized quotes with tax and expiry date.
- Track quote status (`draft`, `sent`, `accepted`, `rejected`, `expired`).
- Convert accepted quotes into invoices in one click.

### 📝 Contracts
- Create and manage service contracts/NDAs/fixed-price/retainer agreements.
- Track status (`draft`, `sent`, `signed`).
- Print and export contract PDFs.

### ⏱ Work Hours
- Log billable work hours per client/project.
- Edit or delete existing entries.

### ⏱ Live Time Tracker
- Start/stop live sessions with single active-session guard.
- Optional Pomodoro mode (25-minute countdown + browser notification).
- Save stopped sessions directly to Work Hours.
- Export timer sessions to CSV.

### 📅 Availability Calendar
- Month-view calendar showing free/light/busy/blocked days.
- Aggregates work hours + scoped project date windows.
- Add manual blocks (vacation/meeting/holiday/blocked).
- Filter by status and navigate months without full page reload.

### 💸 Expense Tracker
- Record and track project expenses to keep costs visible.
- Includes category-level breakdown and CSV export support.

### 🧮 Tax Estimator
- Estimate tax liability based on earnings and a configurable tax rate.

### 📊 Profitability Reports
- Interactive analytics dashboard with local Chart.js.
- Income/profit trends, top clients, expense categories, and weekly hours.

### 🔍 Global Search
- Search across clients, invoices, quotes, contracts, notes, expenses, work hours, and SDLC data.

### 🗄️ Backup & Restore
- Export all app data as ZIP and restore at any time.
- Includes timer sessions, calendar blocks, notes, quotes, contracts, and SDLC data.

### ⚙️ Settings
- Set your name, business name, default hourly rate, working hours per day, and preferred currency.
- Configure late fee rate used in overdue invoice calculations.

---

## Tech Stack

| Layer     | Technology              |
|-----------|-------------------------|
| Backend   | Python 3 · Flask 3      |
| Frontend  | Jinja2 · Vanilla JS · CSS custom properties |
| PDF       | xhtml2pdf               |
| Storage   | JSON flat files (`data/`) |
| Testing   | pytest                  |

---

## Project Structure 

[Project Structure🔗](Project_Structure.md)

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Srijan-XI/FLTK.git
cd FLTK
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

Or use the provided launcher scripts:

```bash
# Windows
app.bat

# macOS / Linux (make executable first)
chmod +x app.sh
./app.sh
```

Open your browser at **http://127.0.0.1:5000**

---

## Configuration

You can set a custom secret key via an environment variable (optional):

```bash
# .env
SECRET_KEY=your-secret-key-here
```

All other settings (name, currency, hourly rate, etc.) are configurable from the **Settings** page inside the app.

---

## Running Tests

```bash
pytest tests/
```

For faster targeted checks while developing:

```bash
pytest tests/test_timer.py tests/test_calendar.py
```

For quotes/contracts + finance checks:

```bash
pytest tests/test_quotes.py tests/test_contracts.py tests/test_overdue.py tests/test_multicurrency.py
```

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started and [CONTRIBUTORS.md](CONTRIBUTORS.md) for a list of everyone who has helped build VishKron.

---

## License

**GNU AGPL-3.0** — see [LICENSE](LICENSE) for full terms.

