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
- Dedicated CRM view per client showing linked invoices and hours.

### 🧾 Invoicing
- Create, view, and manage invoices.
- Generate and download invoices as **PDF**.

### ⏱ Work Hours
- Log billable work hours per client/project.
- Edit or delete existing entries.

### 💸 Expense Tracker
- Record and track project expenses to keep costs visible.

### 🧮 Tax Estimator
- Estimate tax liability based on earnings and a configurable tax rate.

### 📊 Profitability Reports
- View earnings summaries broken down by client, project, and time period.

### 🔍 Global Search
- Search across clients, invoices, and work hours from the navbar.

### 🗄️ Backup & Restore
- Export all your data as a JSON backup and restore it at any time.

### ⚙️ Settings
- Set your name, business name, default hourly rate, working hours per day, and preferred currency.

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

```
FreelancerToolkit/
├── app.py                  # Flask app entry point
├── requirements.txt
├── data/                   # JSON data store
│   ├── clients.json
│   ├── invoices.json
│   ├── workhours.json
│   └── settings.json
├── modules/
│   ├── drp/                # Deadline Predictor module
│   │   ├── predictor.py
│   │   ├── history.py
│   │   └── routes.py
│   └── wft/                # Workflow & Finance Tools module
│       ├── helpers.py
│       └── routes.py
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── home.html
│   ├── drp/
│   └── wft/
├── static/
│   └── css/
│       └── style.css
└── tests/
    └── test_predictor.py
```

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

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started and [CONTRIBUTORS.md](CONTRIBUTORS.md) for a list of everyone who has helped build VishKron.

---

## License

**GNU AGPL-3.0** — see [LICENSE](LICENSE) for full terms.

