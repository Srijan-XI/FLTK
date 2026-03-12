```
FreelancerToolkit/
├── app.py                  # Flask app entry point
├── requirements.txt
├── data/                   # JSON data store
│   ├── .gitkeep
│   ├── clients.json
│   ├── contracts.json
│   ├── quotes.json
│   ├── invoices.json
│   ├── timer_sessions.json
│   ├── calendar_blocks.json
│   ├── workhours.json
│   ├── sdlc_templates.json
│   ├── settings.json
│   └── ... (additional JSON files auto-created as features are used)
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
│       ├── calendar.html
│       ├── clients/
│       │   ├── clients.html
│       │   ├── client_notes.html
│       │   ├── crm_client.html
│       │   └── edit_client.html
│       ├── contracts/
│       │   ├── contracts.html
│       │   ├── contract_detail.html
│       │   ├── contract_form.html
│       │   └── contract_print.html
│       ├── finance/
│       │   ├── expenses.html
│       │   ├── reports.html
│       │   └── tax.html
│       ├── hours/
│       │   ├── edit_hours.html
│       │   └── hours.html
│       ├── invoices/
│       │   ├── invoices.html
│       │   ├── invoice_detail.html
│       │   ├── invoice_form.html
│       │   ├── invoice_pdf.html
│       │   ├── invoice_reminder.html
│       │   └── overdue.html
│       ├── proposals/
│       │   ├── templates.html
│       │   └── template_detail.html
│       ├── quotes/
│       │   ├── quotes.html
│       │   ├── quote_detail.html
│       │   ├── quote_form.html
│       │   └── quote_print.html
│       ├── sdlc/
│       │   ├── scoped_projects.html
│       │   ├── scoped_project_detail.html
│       │   ├── scoped_project_form.html
│       │   ├── scoped_project_print.html
│       │   ├── sdlc_templates.html
│       │   ├── sdlc_template_detail.html
│       │   ├── sdlc_template_form.html
│       │   └── sdlc_template_print.html
│       ├── timer.html
│       └── system/
│           ├── backup.html
│           ├── search.html
│           └── settings.html
├── static/
│   ├── js/
│   │   └── chart.umd.min.js
│   └── css/
│       └── style.css
└── tests/
    ├── test_predictor.py
    ├── test_analytics.py
    ├── test_overdue.py
    ├── test_multicurrency.py
    ├── test_client_notes.py
    ├── test_quotes.py
    ├── test_contracts.py
    ├── test_timer.py
    ├── test_calendar.py
    └── test_wft_sdlc.py
```
