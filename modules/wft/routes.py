from flask import render_template, request, redirect, url_for, flash, Response, jsonify
from modules.wft import wft_bp
import modules.wft.helpers as h


def _render_pdf_response(template_name: str, context: dict, filename: str,
                         fallback_endpoint: str, **fallback_values):
    try:
        from xhtml2pdf import pisa
        import io
        html = render_template(template_name, **context)
        buf = io.BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=buf)
        if pisa_status.err:
            flash("PDF generation failed.", "error")
            return redirect(url_for(fallback_endpoint, **fallback_values))
        buf.seek(0)
        return Response(
            buf.read(),
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError:
        flash("PDF export requires xhtml2pdf. Run: pip install xhtml2pdf", "error")
        return redirect(url_for(fallback_endpoint, **fallback_values))


# ── Settings ──────────────────────────────────────────────────────────────────

@wft_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        f = request.form
        try:
            rate = float(f.get("default_rate", 50))
            whrs = float(f.get("working_hours_per_day", 8))
            late_fee_rate = float(f.get("late_fee_rate", 1.5) or 1.5)
        except ValueError:
            flash("Invalid number in settings.", "error")
            return redirect(url_for("wft.settings"))

        currency = f.get("currency", "USD")
        symbol = h.CURRENCY_OPTIONS.get(currency, "$")

        h.save_settings({
            "name": f.get("name", "").strip() or "Your Name",
            "business": f.get("business", "").strip() or "Freelancer",
            "currency": currency,
            "currency_symbol": symbol,
            "default_rate": rate,
            "working_hours_per_day": whrs,
            "late_fee_rate": late_fee_rate,
        })
        flash("Settings saved.", "success")
        return redirect(url_for("wft.settings"))

    cfg = h.get_settings()
    return render_template("wft/system/settings.html", cfg=cfg,
                           currencies=h.CURRENCY_OPTIONS)


# ── Proposal Templates ────────────────────────────────────────────────────────

@wft_bp.route("/templates")
def templates():
    return render_template("wft/proposals/templates.html", templates=h.get_templates())


@wft_bp.route("/templates/<key>")
def template_detail(key):
    tmpl = h.get_template(key)
    if not tmpl:
        flash("Template not found.", "error")
        return redirect(url_for("wft.templates"))
    return render_template("wft/proposals/template_detail.html", tmpl=tmpl, key=key)


# ── SDLC Templates ───────────────────────────────────────────────────────────

@wft_bp.route("/sdlc/templates")
def sdlc_templates():
    templates = h.get_sdlc_templates()
    query = request.args.get("q", "").strip().lower()
    if query:
        templates = [
            template for template in templates
            if query in template.get("name", "").lower()
            or query in template.get("summary", "").lower()
            or query in " ".join(template.get("tags", [])).lower()
        ]
    return render_template(
        "wft/sdlc/sdlc_templates.html",
        templates=templates,
        stats=h.scoped_project_stats(),
        query=query,
    )


@wft_bp.route("/sdlc/templates/new", methods=["GET", "POST"])
def new_sdlc_template():
    if request.method == "POST":
        f = request.form
        name = f.get("name", "").strip()
        if not name:
            flash("Template name is required.", "error")
            return redirect(url_for("wft.new_sdlc_template"))
        template = h.add_sdlc_template(
            name=name,
            summary=f.get("summary", ""),
            best_for=f.get("best_for", ""),
            phases=f.get("phases", ""),
            deliverables=f.get("deliverables", ""),
            scope_controls=f.get("scope_controls", ""),
            strengths=f.get("strengths", ""),
            risks=f.get("risks", ""),
            revision_policy=f.get("revision_policy", ""),
            testing_strategy=f.get("testing_strategy", ""),
            client_fit=f.get("client_fit", ""),
            tags=f.get("tags", ""),
        )
        flash("SDLC template created.", "success")
        return redirect(url_for("wft.sdlc_template_detail", template_id=template["id"]))
    return render_template("wft/sdlc/sdlc_template_form.html", template=None)


@wft_bp.route("/sdlc/templates/<int:template_id>")
def sdlc_template_detail(template_id):
    template = h.get_sdlc_template(template_id)
    if not template:
        flash("SDLC template not found.", "error")
        return redirect(url_for("wft.sdlc_templates"))
    project_count = sum(
        1 for project in h.get_scoped_projects() if project.get("template_id") == template_id
    )
    return render_template(
        "wft/sdlc/sdlc_template_detail.html",
        template=template,
        project_count=project_count,
    )


@wft_bp.route("/sdlc/templates/<int:template_id>/edit", methods=["GET", "POST"])
def edit_sdlc_template(template_id):
    template = h.get_sdlc_template(template_id)
    if not template:
        flash("SDLC template not found.", "error")
        return redirect(url_for("wft.sdlc_templates"))

    if request.method == "POST":
        f = request.form
        name = f.get("name", "").strip()
        if not name:
            flash("Template name is required.", "error")
            return redirect(url_for("wft.edit_sdlc_template", template_id=template_id))
        h.update_sdlc_template(
            template_id=template_id,
            name=name,
            summary=f.get("summary", ""),
            best_for=f.get("best_for", ""),
            phases=f.get("phases", ""),
            deliverables=f.get("deliverables", ""),
            scope_controls=f.get("scope_controls", ""),
            strengths=f.get("strengths", ""),
            risks=f.get("risks", ""),
            revision_policy=f.get("revision_policy", ""),
            testing_strategy=f.get("testing_strategy", ""),
            client_fit=f.get("client_fit", ""),
            tags=f.get("tags", ""),
        )
        flash("SDLC template updated.", "success")
        return redirect(url_for("wft.sdlc_template_detail", template_id=template_id))

    return render_template("wft/sdlc/sdlc_template_form.html", template=template)


@wft_bp.route("/sdlc/templates/<int:template_id>/delete", methods=["POST"])
def delete_sdlc_template(template_id):
    if any(project.get("template_id") == template_id for project in h.get_scoped_projects()):
        flash("This template is already used by scoped projects and cannot be removed.", "error")
        return redirect(url_for("wft.sdlc_template_detail", template_id=template_id))
    h.delete_sdlc_template(template_id)
    flash("SDLC template deleted.", "info")
    return redirect(url_for("wft.sdlc_templates"))


@wft_bp.route("/sdlc/templates/export")
def export_sdlc_templates():
    import csv
    import io

    templates = h.get_sdlc_templates()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "ID", "Name", "Summary", "Best For", "Phases", "Deliverables",
        "Scope Controls", "Strengths", "Risks", "Revision Policy",
        "Testing Strategy", "Client Fit", "Tags",
    ])
    for template in templates:
        writer.writerow([
            template["id"],
            template["name"],
            template.get("summary", ""),
            template.get("best_for", ""),
            " | ".join(template.get("phases", [])),
            " | ".join(template.get("deliverables", [])),
            " | ".join(template.get("scope_controls", [])),
            " | ".join(template.get("strengths", [])),
            " | ".join(template.get("risks", [])),
            template.get("revision_policy", ""),
            template.get("testing_strategy", ""),
            template.get("client_fit", ""),
            ", ".join(template.get("tags", [])),
        ])
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sdlc-templates.csv"},
    )


@wft_bp.route("/sdlc/templates/<int:template_id>/print")
def print_sdlc_template(template_id):
    template = h.get_sdlc_template(template_id)
    if not template:
        flash("SDLC template not found.", "error")
        return redirect(url_for("wft.sdlc_templates"))
    return render_template("wft/sdlc/sdlc_template_print.html", template=template)


@wft_bp.route("/sdlc/templates/<int:template_id>/pdf")
def pdf_sdlc_template(template_id):
    template = h.get_sdlc_template(template_id)
    if not template:
        flash("SDLC template not found.", "error")
        return redirect(url_for("wft.sdlc_templates"))
    filename = f"{template['slug'] or template['id']}.pdf"
    return _render_pdf_response(
        "wft/sdlc/sdlc_template_print.html",
        {"template": template},
        filename,
        "wft.sdlc_template_detail",
        template_id=template_id,
    )


# ── Scoped Projects ─────────────────────────────────────────────────────────

@wft_bp.route("/sdlc/projects")
def scoped_projects():
    selected_client = request.args.get("client_id", type=int)
    scope_filter = request.args.get("filter", "")
    projects = h.get_scoped_projects()
    if selected_client:
        projects = [project for project in projects if project.get("client_id") == selected_client]
    
    # Apply scope filter if specified
    if scope_filter:
        scope_statuses = h.get_all_scope_statuses()
        scope_by_id = {s["project_id"]: s for s in scope_statuses}
        if scope_filter == "warning":
            projects = [p for p in projects if scope_by_id.get(p["id"], {}).get("status") == "warning"]
        elif scope_filter == "over_budget":
            projects = [p for p in projects if scope_by_id.get(p["id"], {}).get("status") == "over_budget"]
    
    return render_template(
        "wft/sdlc/scoped_projects.html",
        projects=projects,
        clients=h.get_clients(),
        selected_client=selected_client,
        stats=h.scoped_project_stats(),
        scope_statuses=h.get_all_scope_statuses(),
        scope_filter=scope_filter,
    )


@wft_bp.route("/sdlc/projects/new", methods=["GET", "POST"])
def new_scoped_project():
    clients = h.get_clients()
    templates = h.get_sdlc_templates()
    selected_client_id = request.args.get("client_id", type=int)
    selected_template_id = request.args.get("template_id", type=int)
    selected_template = h.get_sdlc_template(selected_template_id) if selected_template_id else None

    if request.method == "POST":
        f = request.form
        client_id = f.get("client_id", type=int)
        template_id = f.get("template_id", type=int)
        project_name = f.get("project_name", "").strip()
        if not client_id or not any(client["id"] == client_id for client in clients):
            flash("Select a valid client.", "error")
            return redirect(url_for("wft.new_scoped_project", client_id=selected_client_id, template_id=selected_template_id))
        if not template_id or not h.get_sdlc_template(template_id):
            flash("Select a valid SDLC template.", "error")
            return redirect(url_for("wft.new_scoped_project", client_id=selected_client_id, template_id=selected_template_id))
        if not project_name:
            flash("Project name is required.", "error")
            return redirect(url_for("wft.new_scoped_project", client_id=selected_client_id, template_id=selected_template_id))
        project = h.add_scoped_project(
            client_id=client_id,
            template_id=template_id,
            project_name=project_name,
            summary=f.get("summary", ""),
            objectives=f.get("objectives", ""),
            scope_in=f.get("scope_in", ""),
            scope_out=f.get("scope_out", ""),
            deliverables=f.get("deliverables", ""),
            milestones=f.get("milestones", ""),
            change_control=f.get("change_control", ""),
            revision_policy=f.get("revision_policy", ""),
            communication_plan=f.get("communication_plan", ""),
            acceptance_criteria=f.get("acceptance_criteria", ""),
            notes=f.get("notes", ""),
            status=f.get("status", "draft"),
            start_date=f.get("start_date", ""),
            target_date=f.get("target_date", ""),
        )
        flash("Scoped project saved.", "success")
        return redirect(url_for("wft.scoped_project_detail", project_id=project["id"]))

    return render_template(
        "wft/sdlc/scoped_project_form.html",
        project=None,
        clients=clients,
        templates=templates,
        statuses=h.PROJECT_STATUS_OPTIONS,
        selected_client_id=selected_client_id,
        selected_template_id=selected_template_id,
        selected_template=selected_template,
    )


@wft_bp.route("/sdlc/projects/<int:project_id>")
def scoped_project_detail(project_id):
    project = h.get_scoped_project(project_id)
    if not project:
        flash("Scoped project not found.", "error")
        return redirect(url_for("wft.scoped_projects"))
    template = h.get_sdlc_template(project.get("template_id"))
    scope = h.get_scope_status(project_id)
    return render_template("wft/sdlc/scoped_project_detail.html", project=project, template=template, scope=scope)


@wft_bp.route("/sdlc/projects/<int:project_id>/edit", methods=["GET", "POST"])
def edit_scoped_project(project_id):
    project = h.get_scoped_project(project_id)
    if not project:
        flash("Scoped project not found.", "error")
        return redirect(url_for("wft.scoped_projects"))
    clients = h.get_clients()
    templates = h.get_sdlc_templates()

    if request.method == "POST":
        f = request.form
        client_id = f.get("client_id", type=int)
        template_id = f.get("template_id", type=int)
        project_name = f.get("project_name", "").strip()
        if not client_id or not any(client["id"] == client_id for client in clients):
            flash("Select a valid client.", "error")
            return redirect(url_for("wft.edit_scoped_project", project_id=project_id))
        if not template_id or not h.get_sdlc_template(template_id):
            flash("Select a valid SDLC template.", "error")
            return redirect(url_for("wft.edit_scoped_project", project_id=project_id))
        if not project_name:
            flash("Project name is required.", "error")
            return redirect(url_for("wft.edit_scoped_project", project_id=project_id))
        h.update_scoped_project(
            project_id=project_id,
            client_id=client_id,
            template_id=template_id,
            project_name=project_name,
            summary=f.get("summary", ""),
            objectives=f.get("objectives", ""),
            scope_in=f.get("scope_in", ""),
            scope_out=f.get("scope_out", ""),
            deliverables=f.get("deliverables", ""),
            milestones=f.get("milestones", ""),
            change_control=f.get("change_control", ""),
            revision_policy=f.get("revision_policy", ""),
            communication_plan=f.get("communication_plan", ""),
            acceptance_criteria=f.get("acceptance_criteria", ""),
            notes=f.get("notes", ""),
            status=f.get("status", "draft"),
            start_date=f.get("start_date", ""),
            target_date=f.get("target_date", ""),
        )
        flash("Scoped project updated.", "success")
        return redirect(url_for("wft.scoped_project_detail", project_id=project_id))

    return render_template(
        "wft/sdlc/scoped_project_form.html",
        project=project,
        clients=clients,
        templates=templates,
        statuses=h.PROJECT_STATUS_OPTIONS,
        selected_client_id=project.get("client_id"),
        selected_template_id=project.get("template_id"),
        selected_template=h.get_sdlc_template(project.get("template_id")),
    )


@wft_bp.route("/sdlc/projects/<int:project_id>/delete", methods=["POST"])
def delete_scoped_project(project_id):
    project = h.get_scoped_project(project_id)
    if not project:
        flash("Scoped project not found.", "error")
        return redirect(url_for("wft.scoped_projects"))
    client_id = project.get("client_id")
    h.delete_scoped_project(project_id)
    flash("Scoped project deleted.", "info")
    if request.args.get("return_to") == "client" and client_id:
        return redirect(url_for("wft.crm_client", client_id=client_id))
    return redirect(url_for("wft.scoped_projects"))


@wft_bp.route("/sdlc/projects/export")
def export_scoped_projects():
    import csv
    import io

    projects = h.get_scoped_projects()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "ID", "Project Name", "Client", "Template", "Status", "Start Date",
        "Target Date", "Summary", "Objectives", "Scope In", "Scope Out",
        "Deliverables", "Milestones", "Change Control", "Revision Policy",
        "Communication Plan", "Acceptance Criteria", "Notes",
    ])
    for project in projects:
        writer.writerow([
            project["id"],
            project["project_name"],
            project.get("client_name", ""),
            project.get("template_name", ""),
            project.get("status", ""),
            project.get("start_date", ""),
            project.get("target_date", ""),
            project.get("summary", ""),
            " | ".join(project.get("objectives", [])),
            " | ".join(project.get("scope_in", [])),
            " | ".join(project.get("scope_out", [])),
            " | ".join(project.get("deliverables", [])),
            " | ".join(project.get("milestones", [])),
            project.get("change_control", ""),
            project.get("revision_policy", ""),
            project.get("communication_plan", ""),
            " | ".join(project.get("acceptance_criteria", [])),
            project.get("notes", ""),
        ])
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=scoped-projects.csv"},
    )


@wft_bp.route("/sdlc/projects/<int:project_id>/print")
def print_scoped_project(project_id):
    project = h.get_scoped_project(project_id)
    if not project:
        flash("Scoped project not found.", "error")
        return redirect(url_for("wft.scoped_projects"))
    template = h.get_sdlc_template(project.get("template_id"))
    return render_template("wft/sdlc/scoped_project_print.html", project=project, template=template)


@wft_bp.route("/sdlc/projects/<int:project_id>/pdf")
def pdf_scoped_project(project_id):
    project = h.get_scoped_project(project_id)
    if not project:
        flash("Scoped project not found.", "error")
        return redirect(url_for("wft.scoped_projects"))
    template = h.get_sdlc_template(project.get("template_id"))
    filename = f"{project['project_name'].replace(' ', '-').lower()}.pdf"
    return _render_pdf_response(
        "wft/sdlc/scoped_project_print.html",
        {"project": project, "template": template},
        filename,
        "wft.scoped_project_detail",
        project_id=project_id,
    )


# ── Client Tracker ───────────────────────────────────────────────────────────

@wft_bp.route("/clients")
def clients():
    clients = h.get_clients()
    for client in clients:
        client["notes_count"] = len(h.get_client_notes(client["id"]))
    return render_template("wft/clients/clients.html", clients=clients,
                           currencies=h.CURRENCY_OPTIONS)


@wft_bp.route("/clients/add", methods=["POST"])
def add_client():
    try:
        rate = float(request.form.get("default_rate", 0) or 0)
    except ValueError:
        rate = 0.0
    currency = request.form.get("currency", "")
    symbol = h.CURRENCY_OPTIONS.get(currency, "") if currency else ""
    h.add_client(
        name=request.form["name"],
        email=request.form["email"],
        phone=request.form.get("phone", ""),
        notes=request.form.get("notes", ""),
        default_rate=rate,
        company=request.form.get("company", ""),
        currency=currency,
        currency_symbol=symbol,
        status=request.form.get("status", "active"),
        website=request.form.get("website", ""),
    )
    flash("Client added.", "success")
    return redirect(url_for("wft.clients"))


@wft_bp.route("/clients/edit/<int:client_id>", methods=["GET", "POST"])
def edit_client(client_id):
    all_clients = h.get_clients()
    client = next((c for c in all_clients if c["id"] == client_id), None)
    if not client:
        flash("Client not found.", "error")
        return redirect(url_for("wft.clients"))

    if request.method == "POST":
        try:
            rate = float(request.form.get("default_rate", 0) or 0)
        except ValueError:
            rate = 0.0
        currency = request.form.get("currency", "")
        symbol = h.CURRENCY_OPTIONS.get(currency, "") if currency else ""
        h.update_client(
            client_id=client_id,
            name=request.form["name"],
            email=request.form["email"],
            phone=request.form.get("phone", ""),
            notes=request.form.get("notes", ""),
            default_rate=rate,
            company=request.form.get("company", ""),
            currency=currency,
            currency_symbol=symbol,
            status=request.form.get("status", "active"),
            website=request.form.get("website", ""),
        )
        flash("Client updated.", "success")
        return redirect(url_for("wft.clients"))

    return render_template("wft/clients/edit_client.html", client=client,
                           currencies=h.CURRENCY_OPTIONS)


@wft_bp.route("/clients/delete/<int:client_id>", methods=["POST"])
def delete_client(client_id):
    h.delete_client(client_id)
    flash("Client removed.", "info")
    return redirect(url_for("wft.clients"))


# ── Invoice Generator ─────────────────────────────────────────────────────────

@wft_bp.route("/invoices")
def invoices():
    invs = h.get_invoices()
    from datetime import date
    today = date.today().isoformat()
    summary = h.get_earnings_summary()
    cfg = h.get_settings()
    overdue_map = {inv["id"]: inv for inv in h.get_overdue_invoices()}
    for inv in invs:
        overdue = overdue_map.get(inv["id"])
        inv["is_overdue"] = bool(overdue)
        inv["days_overdue"] = overdue.get("days_overdue", 0) if overdue else 0
        inv["display_total"] = h.get_invoice_display_total(inv)
        inv["base_total"] = float(inv.get("total_base", (inv.get("total", 0.0) or 0.0) * float(inv.get("exchange_rate", 1.0) or 1.0)) or 0.0)
        inv["base_currency"] = inv.get("base_currency") or cfg.get("currency", "USD")
    return render_template("wft/invoices/invoices.html", invoices=invs, today=today, summary=summary)


@wft_bp.route("/invoices/overdue")
def overdue_invoices():
    cfg = h.get_settings()
    overdue = h.get_overdue_invoices()
    return render_template("wft/invoices/overdue.html", overdue=overdue, cfg=cfg)


@wft_bp.route("/invoices/ageing")
def invoice_ageing():
    ageing = h.get_ar_ageing()
    cfg = h.get_settings()
    return render_template("wft/invoices/invoice_ageing.html", ageing=ageing, cfg=cfg)


@wft_bp.route("/invoices/ageing/pdf")
def invoice_ageing_pdf():
    ageing = h.get_ar_ageing()
    cfg = h.get_settings()
    return _render_pdf_response(
        "wft/invoices/invoice_ageing_print.html",
        {"ageing": ageing, "cfg": cfg},
        "AR_Ageing.pdf",
        "wft.invoice_ageing"
    )


@wft_bp.route("/invoices/<int:inv_id>/reminder")
def invoice_reminder(inv_id):
    inv_list = h.get_invoices()
    inv = next((i for i in inv_list if i["id"] == inv_id), None)
    if not inv:
        flash("Invoice not found.", "error")
        return redirect(url_for("wft.invoices"))
    overdue_map = {item["id"]: item for item in h.get_overdue_invoices()}
    inv = overdue_map.get(inv_id, inv)
    draft = h.get_reminder_email_draft(inv)
    cfg = h.get_settings()
    return render_template("wft/invoices/invoice_reminder.html", inv=inv, draft=draft, cfg=cfg)


@wft_bp.route("/invoices/new", methods=["GET", "POST"])
def new_invoice():
    cfg = h.get_settings()
    if request.method == "POST":
        f = request.form
        descs = f.getlist("description")
        hours_list = f.getlist("hours")
        rates = f.getlist("rate")
        items = []
        for d, hr, rt in zip(descs, hours_list, rates):
            if d.strip():
                try:
                    items.append({
                        "description": d,
                        "hours": float(hr or 0),
                        "rate": float(rt or 0),
                    })
                except ValueError:
                    flash("Invalid number in line items.", "error")
                    return redirect(url_for("wft.new_invoice"))

        if not items:
            flash("Add at least one line item.", "error")
            return redirect(url_for("wft.new_invoice"))

        try:
            tax_rate = float(f.get("tax_rate", 0) or 0)
        except ValueError:
            tax_rate = 0.0

        currency = f.get("currency", cfg["currency"])
        symbol = h.CURRENCY_OPTIONS.get(currency, cfg["currency_symbol"])
        base_currency = f.get("base_currency", cfg["currency"])
        try:
            exchange_rate = float(f.get("exchange_rate", 1.0) or 1.0)
        except ValueError:
            exchange_rate = 1.0
        if currency == base_currency:
            exchange_rate = 1.0

        invoice = h.create_invoice(
            client_name=f["client_name"],
            items=items,
            due_date=f["due_date"],
            notes=f.get("notes", ""),
            currency=currency,
            currency_symbol=symbol,
            tax_rate=tax_rate,
            exchange_rate=exchange_rate,
            base_currency=base_currency,
        )
        flash(f"Invoice {invoice['invoice_number']} created.", "success")
        return redirect(url_for("wft.invoice_detail", inv_id=invoice["id"]))
    return render_template("wft/invoices/invoice_form.html", clients=h.get_clients(),
                           cfg=cfg, currencies=h.CURRENCY_OPTIONS)


@wft_bp.route("/invoices/<int:inv_id>")
def invoice_detail(inv_id):
    inv_list = h.get_invoices()
    inv = next((i for i in inv_list if i["id"] == inv_id), None)
    if not inv:
        flash("Invoice not found.", "error")
        return redirect(url_for("wft.invoices"))
    cfg = h.get_settings()
    inv["display_total"] = h.get_invoice_display_total(inv)
    sdlc_templates = h.get_sdlc_templates()
    return render_template("wft/invoices/invoice_detail.html", inv=inv, cfg=cfg, sdlc_templates=sdlc_templates)


@wft_bp.route("/invoices/pay/<int:inv_id>", methods=["POST"])
def pay_invoice(inv_id):
    try:
        h.mark_invoice_paid(inv_id)
        flash("Invoice marked as paid.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("wft.invoice_detail", inv_id=inv_id))


@wft_bp.route("/invoices/delete/<int:inv_id>", methods=["POST"])
def delete_invoice(inv_id):
    h.delete_invoice(inv_id)
    flash("Invoice deleted.", "info")
    return redirect(url_for("wft.invoices"))


# ── Contracts ───────────────────────────────────────────────────────────────

@wft_bp.route("/contracts")
def contracts():
    return render_template(
        "wft/contracts/contracts.html",
        contracts=h.get_contracts(),
        stats=h.get_contract_stats(),
    )


@wft_bp.route("/contracts/new", methods=["GET", "POST"])
def new_contract():
    cfg = h.get_settings()
    clients = h.get_clients()
    prefill_client_id = request.args.get("client_id", type=int)
    prefill_client = h.get_client(prefill_client_id) if prefill_client_id else None

    if request.method == "POST":
        f = request.form
        client_id = f.get("client_id", type=int)
        client = h.get_client(client_id) if client_id else None
        contract = h.add_contract(
            title=f.get("title", ""),
            contract_type=f.get("contract_type", ""),
            client_id=client_id,
            client_name=f.get("client_name", "") or (client.get("name") if client else ""),
            client_email=f.get("client_email", "") or (client.get("email") if client else ""),
            project_description=f.get("project_description", ""),
            payment_terms=f.get("payment_terms", ""),
            project_value=float(f.get("project_value", 0) or 0.0),
            currency_symbol=f.get("currency_symbol") or cfg.get("currency_symbol", "$"),
            start_date=f.get("start_date", ""),
            end_date=f.get("end_date", ""),
            revision_limit=int(f.get("revision_limit", 0) or 0),
            late_fee_percent=float(f.get("late_fee_percent", 0) or 0.0),
            ip_ownership=f.get("ip_ownership", "client"),
            confidentiality=bool(f.get("confidentiality")),
            governing_law=f.get("governing_law", ""),
            freelancer_name=f.get("freelancer_name", ""),
            freelancer_business=f.get("freelancer_business", ""),
            custom_clauses=f.get("custom_clauses", ""),
            notes=f.get("notes", ""),
            status="draft",
        )
        flash("Contract created.", "success")
        return redirect(url_for("wft.contract_detail", contract_id=contract["id"]))

    return render_template(
        "wft/contracts/contract_form.html",
        contract=None,
        clients=clients,
        cfg=cfg,
        contract_types=h.CONTRACT_TYPES,
        prefill_client=prefill_client,
    )


@wft_bp.route("/contracts/<int:contract_id>")
def contract_detail(contract_id):
    contract = h.get_contract(contract_id)
    if not contract:
        flash("Contract not found.", "error")
        return redirect(url_for("wft.contracts"))
    return render_template("wft/contracts/contract_detail.html", contract=contract)


@wft_bp.route("/contracts/<int:contract_id>/edit", methods=["GET", "POST"])
def edit_contract(contract_id):
    contract = h.get_contract(contract_id)
    if not contract:
        flash("Contract not found.", "error")
        return redirect(url_for("wft.contracts"))

    cfg = h.get_settings()
    clients = h.get_clients()

    if request.method == "POST":
        f = request.form
        client_id = f.get("client_id", type=int)
        client = h.get_client(client_id) if client_id else None
        h.update_contract(
            contract_id,
            title=f.get("title", ""),
            contract_type=f.get("contract_type", ""),
            client_id=client_id,
            client_name=f.get("client_name", "") or (client.get("name") if client else ""),
            client_email=f.get("client_email", "") or (client.get("email") if client else ""),
            project_description=f.get("project_description", ""),
            payment_terms=f.get("payment_terms", ""),
            project_value=float(f.get("project_value", 0) or 0.0),
            currency_symbol=f.get("currency_symbol") or cfg.get("currency_symbol", "$"),
            start_date=f.get("start_date", ""),
            end_date=f.get("end_date", ""),
            revision_limit=int(f.get("revision_limit", 0) or 0),
            late_fee_percent=float(f.get("late_fee_percent", 0) or 0.0),
            ip_ownership=f.get("ip_ownership", "client"),
            confidentiality=bool(f.get("confidentiality")),
            governing_law=f.get("governing_law", ""),
            freelancer_name=f.get("freelancer_name", ""),
            freelancer_business=f.get("freelancer_business", ""),
            custom_clauses=f.get("custom_clauses", ""),
            notes=f.get("notes", ""),
        )
        flash("Contract updated.", "success")
        return redirect(url_for("wft.contract_detail", contract_id=contract_id))

    return render_template(
        "wft/contracts/contract_form.html",
        contract=contract,
        clients=clients,
        cfg=cfg,
        contract_types=h.CONTRACT_TYPES,
        prefill_client=None,
    )


@wft_bp.route("/contracts/<int:contract_id>/delete", methods=["POST"])
def delete_contract(contract_id):
    h.delete_contract(contract_id)
    flash("Contract deleted.", "info")
    return redirect(url_for("wft.contracts"))


@wft_bp.route("/contracts/<int:contract_id>/status", methods=["POST"])
def update_contract_status(contract_id):
    status = request.form.get("status", "").lower()
    if status in {"draft", "sent", "signed"}:
        h.update_contract(contract_id, status=status)
        flash(f"Contract marked as {status}.", "success")
    else:
        flash("Invalid contract status.", "error")
    return redirect(url_for("wft.contract_detail", contract_id=contract_id))


@wft_bp.route("/contracts/<int:contract_id>/print")
def print_contract(contract_id):
    contract = h.get_contract(contract_id)
    if not contract:
        flash("Contract not found.", "error")
        return redirect(url_for("wft.contracts"))
    return render_template("wft/contracts/contract_print.html", contract=contract)


@wft_bp.route("/contracts/<int:contract_id>/pdf")
def pdf_contract(contract_id):
    contract = h.get_contract(contract_id)
    if not contract:
        flash("Contract not found.", "error")
        return redirect(url_for("wft.contracts"))
    filename = f"contract-{contract_id}.pdf"
    return _render_pdf_response(
        "wft/contracts/contract_print.html",
        {"contract": contract},
        filename,
        "wft.contract_detail",
        contract_id=contract_id,
    )


# ── Quotes ──────────────────────────────────────────────────────────────────

@wft_bp.route("/quotes")
def quotes():
    return render_template(
        "wft/quotes/quotes.html",
        quotes=h.get_quotes(),
        stats=h.get_quote_stats(),
    )


@wft_bp.route("/quotes/new", methods=["GET", "POST"])
def new_quote():
    cfg = h.get_settings()
    clients = h.get_clients()
    prefill_client_id = request.args.get("client_id", type=int)
    prefill_client = h.get_client(prefill_client_id) if prefill_client_id else None

    if request.method == "POST":
        f = request.form
        descs = f.getlist("description")
        qtys = f.getlist("qty")
        rates = f.getlist("rate")
        items = []
        for desc, qty, rate in zip(descs, qtys, rates):
            if not desc.strip():
                continue
            try:
                items.append({
                    "description": desc,
                    "qty": float(qty or 0),
                    "rate": float(rate or 0),
                })
            except ValueError:
                flash("Invalid quote item values.", "error")
                return redirect(url_for("wft.new_quote"))

        if not items:
            flash("Add at least one quote line item.", "error")
            return redirect(url_for("wft.new_quote"))

        client_id = f.get("client_id", type=int)
        client = h.get_client(client_id) if client_id else None
        quote = h.add_quote(
            client_id=client_id,
            client_name=f.get("client_name", "") or (client.get("name") if client else ""),
            title=f.get("title", ""),
            items=items,
            tax_rate=float(f.get("tax_rate", 0) or 0.0),
            currency=f.get("currency", cfg.get("currency", "USD")),
            currency_symbol=h.CURRENCY_OPTIONS.get(
                f.get("currency", cfg.get("currency", "USD")),
                cfg.get("currency_symbol", "$"),
            ),
            expiry_date=f.get("expiry_date", ""),
            notes=f.get("notes", ""),
        )
        flash(f"Quote {quote['quote_number']} created.", "success")
        return redirect(url_for("wft.quote_detail", quote_id=quote["id"]))

    return render_template(
        "wft/quotes/quote_form.html",
        quote=None,
        clients=clients,
        cfg=cfg,
        currencies=h.CURRENCY_OPTIONS,
        prefill_client=prefill_client,
    )


@wft_bp.route("/quotes/<int:quote_id>")
def quote_detail(quote_id):
    quote = h.get_quote(quote_id)
    if not quote:
        flash("Quote not found.", "error")
        return redirect(url_for("wft.quotes"))
    return render_template("wft/quotes/quote_detail.html", quote=quote)


@wft_bp.route("/quotes/<int:quote_id>/edit", methods=["GET", "POST"])
def edit_quote(quote_id):
    quote = h.get_quote(quote_id)
    if not quote:
        flash("Quote not found.", "error")
        return redirect(url_for("wft.quotes"))
    if quote.get("status") not in {"draft", "sent"}:
        flash("Only draft or sent quotes can be edited.", "error")
        return redirect(url_for("wft.quote_detail", quote_id=quote_id))

    cfg = h.get_settings()
    clients = h.get_clients()

    if request.method == "POST":
        f = request.form
        descs = f.getlist("description")
        qtys = f.getlist("qty")
        rates = f.getlist("rate")
        items = []
        for desc, qty, rate in zip(descs, qtys, rates):
            if not desc.strip():
                continue
            try:
                items.append({
                    "description": desc,
                    "qty": float(qty or 0),
                    "rate": float(rate or 0),
                })
            except ValueError:
                flash("Invalid quote item values.", "error")
                return redirect(url_for("wft.edit_quote", quote_id=quote_id))

        if not items:
            flash("Add at least one quote line item.", "error")
            return redirect(url_for("wft.edit_quote", quote_id=quote_id))

        client_id = f.get("client_id", type=int)
        client = h.get_client(client_id) if client_id else None
        h.update_quote(
            quote_id,
            client_id=client_id,
            client_name=f.get("client_name", "") or (client.get("name") if client else ""),
            title=f.get("title", ""),
            items=items,
            tax_rate=float(f.get("tax_rate", 0) or 0.0),
            currency=f.get("currency", cfg.get("currency", "USD")),
            currency_symbol=h.CURRENCY_OPTIONS.get(
                f.get("currency", cfg.get("currency", "USD")),
                cfg.get("currency_symbol", "$"),
            ),
            expiry_date=f.get("expiry_date", ""),
            notes=f.get("notes", ""),
        )
        flash("Quote updated.", "success")
        return redirect(url_for("wft.quote_detail", quote_id=quote_id))

    return render_template(
        "wft/quotes/quote_form.html",
        quote=quote,
        clients=clients,
        cfg=cfg,
        currencies=h.CURRENCY_OPTIONS,
        prefill_client=None,
    )


@wft_bp.route("/quotes/<int:quote_id>/delete", methods=["POST"])
def delete_quote(quote_id):
    if h.delete_quote(quote_id):
        flash("Quote deleted.", "info")
    else:
        flash("Converted quotes cannot be deleted.", "error")
    return redirect(url_for("wft.quotes"))


@wft_bp.route("/quotes/<int:quote_id>/status", methods=["POST"])
def update_quote_status(quote_id):
    status = request.form.get("status", "").lower()
    if status in h.QUOTE_STATUS_OPTIONS:
        h.update_quote_status(quote_id, status)
        flash(f"Quote marked as {status}.", "success")
    else:
        flash("Invalid quote status.", "error")
    return redirect(url_for("wft.quote_detail", quote_id=quote_id))


@wft_bp.route("/quotes/<int:quote_id>/convert", methods=["POST"])
def convert_quote(quote_id):
    try:
        invoice = h.convert_quote_to_invoice(quote_id)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("wft.quote_detail", quote_id=quote_id))

    flash(f"Invoice {invoice['invoice_number']} created.", "success")
    return redirect(url_for("wft.invoice_detail", inv_id=invoice["id"]))


@wft_bp.route("/quotes/<int:quote_id>/print")
def print_quote(quote_id):
    quote = h.get_quote(quote_id)
    if not quote:
        flash("Quote not found.", "error")
        return redirect(url_for("wft.quotes"))
    return render_template("wft/quotes/quote_print.html", quote=quote)


@wft_bp.route("/quotes/<int:quote_id>/pdf")
def pdf_quote(quote_id):
    quote = h.get_quote(quote_id)
    if not quote:
        flash("Quote not found.", "error")
        return redirect(url_for("wft.quotes"))
    filename = f"{quote.get('quote_number', 'quote')}.pdf"
    return _render_pdf_response(
        "wft/quotes/quote_print.html",
        {"quote": quote},
        filename,
        "wft.quote_detail",
        quote_id=quote_id,
    )


# ── Invoice PDF Export ────────────────────────────────────────────────────────

@wft_bp.route("/invoices/<int:inv_id>/pdf")
def invoice_pdf(inv_id):
    inv_list = h.get_invoices()
    inv = next((i for i in inv_list if i["id"] == inv_id), None)
    if not inv:
        flash("Invoice not found.", "error")
        return redirect(url_for("wft.invoices"))

    try:
        from xhtml2pdf import pisa
        import io
        from flask import render_template, current_app
        html = render_template("wft/invoices/invoice_pdf.html", inv=inv,
                               cfg=h.get_settings())
        buf = io.BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=buf)
        if pisa_status.err:
            flash("PDF generation failed.", "error")
            return redirect(url_for("wft.invoice_detail", inv_id=inv_id))
        buf.seek(0)
        return Response(
            buf.read(),
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{inv["invoice_number"]}.pdf"'
            }
        )
    except ImportError:
        flash("PDF export requires xhtml2pdf. Run: pip install xhtml2pdf", "error")
        return redirect(url_for("wft.invoice_detail", inv_id=inv_id))


# ── Work Hour Analytics ───────────────────────────────────────────────────────

@wft_bp.route("/hours")
def hours():
    entries = h.get_workhours()
    period = request.args.get("period", "all")
    stats = h.analytics(period=period)
    clients_list = h.get_clients()
    return render_template("wft/hours/hours.html", entries=entries, stats=stats,
                           period=period, clients=clients_list)


@wft_bp.route("/hours/log", methods=["POST"])
def log_hours():
    f = request.form
    try:
        hrs = float(f["hours"])
        if hrs <= 0:
            raise ValueError("Hours must be positive.")
    except (ValueError, KeyError) as e:
        flash(f"Invalid hours value: {e}", "error")
        return redirect(url_for("wft.hours"))

    h.log_hours(
        task=f.get("task", "").strip() or "Untitled",
        client=f.get("client", "").strip() or "Unknown",
        hours=hrs,
        log_date=f.get("log_date", ""),
        notes=f.get("notes", ""),
        tag=f.get("tag", ""),
    )
    flash("Hours logged.", "success")
    return redirect(url_for("wft.hours"))


@wft_bp.route("/hours/edit/<int:entry_id>", methods=["GET", "POST"])
def edit_hours(entry_id):
    entries = h.get_workhours()
    entry = next((e for e in entries if e["id"] == entry_id), None)
    if not entry:
        flash("Entry not found.", "error")
        return redirect(url_for("wft.hours"))

    if request.method == "POST":
        f = request.form
        try:
            hrs = float(f["hours"])
        except ValueError:
            flash("Invalid hours value.", "error")
            return redirect(url_for("wft.edit_hours", entry_id=entry_id))
        h.update_workhour(
            entry_id=entry_id,
            task=f.get("task", "").strip(),
            client=f.get("client", "").strip(),
            hours=hrs,
            log_date=f.get("log_date", ""),
            notes=f.get("notes", ""),
            tag=f.get("tag", ""),
        )
        flash("Entry updated.", "success")
        return redirect(url_for("wft.hours"))

    return render_template("wft/hours/edit_hours.html", entry=entry,
                           clients=h.get_clients())


@wft_bp.route("/hours/delete/<int:entry_id>", methods=["POST"])
def delete_hours(entry_id):
    h.delete_workhour(entry_id)
    flash("Entry deleted.", "info")
    return redirect(url_for("wft.hours"))


# ── Live Timer ───────────────────────────────────────────────────────────────

@wft_bp.route("/timer")
def timer():
    active = h.get_active_session()
    all_sessions = h.get_timer_sessions()
    page = request.args.get("page", 1, type=int)
    per_page = 10
    total_sessions = len(all_sessions)
    total_pages = max(1, (total_sessions + per_page - 1) // per_page)
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    sessions = all_sessions[start:end]
    clients = h.get_clients()
    return render_template(
        "wft/timer.html",
        active=active,
        sessions=sessions,
        clients=clients,
        page=page,
        total_pages=total_pages,
        total_sessions=total_sessions,
    )


@wft_bp.route("/timer/start", methods=["POST"])
def start_timer():
    client = request.form.get("client", "").strip()
    task = request.form.get("task", "").strip()
    mode = request.form.get("mode", "normal")
    if not client or not task:
        flash("Client and task are required.", "error")
        return redirect(url_for("wft.timer"))
    try:
        h.start_timer(client=client, task=task, mode=mode)
        flash("Timer started.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("wft.timer"))


@wft_bp.route("/timer/stop/<int:session_id>", methods=["POST"])
def stop_timer(session_id):
    try:
        h.stop_timer(session_id)
        flash("Timer stopped.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("wft.timer"))


@wft_bp.route("/timer/save/<int:session_id>", methods=["POST"])
def save_timer(session_id):
    try:
        session = h.save_timer_to_hours(session_id)
        hours = round(float(session.get("duration_seconds", 0) or 0) / 3600, 2)
        flash(f"Logged {hours:.2f} hours for {session.get('task', 'task')}.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("wft.timer"))


@wft_bp.route("/timer/discard/<int:session_id>", methods=["POST"])
def discard_timer(session_id):
    try:
        h.discard_timer(session_id)
        flash("Timer session discarded.", "info")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("wft.timer"))


@wft_bp.route("/timer/delete/<int:session_id>", methods=["POST"])
def delete_timer(session_id):
    h.delete_timer_session(session_id)
    flash("Timer session deleted.", "info")
    return redirect(url_for("wft.timer"))


@wft_bp.route("/timer/export")
def export_timer_sessions():
    import csv
    import io

    sessions = h.get_timer_sessions()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "ID", "Date", "Client", "Task", "Mode", "Status",
        "Start", "End", "Duration Seconds", "Duration Hours",
    ])
    for session in sessions:
        seconds = int(session.get("duration_seconds", 0) or 0)
        writer.writerow([
            session.get("id"),
            session.get("date", ""),
            session.get("client", ""),
            session.get("task", ""),
            session.get("mode", "normal"),
            session.get("status", ""),
            session.get("start_time", ""),
            session.get("end_time", ""),
            seconds,
            round(seconds / 3600, 2),
        ])
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=timer-sessions.csv"},
    )


# ── Availability Calendar ───────────────────────────────────────────────────

@wft_bp.route("/calendar")
def calendar():
    from datetime import date

    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month
    if month < 1 or month > 12:
        month = today.month

    events = h.get_calendar_events(year, month)
    blocks = h.get_calendar_blocks()
    cfg = h.get_settings()

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    import calendar as pycalendar

    return render_template(
        "wft/calendar.html",
        events=events,
        blocks=blocks,
        cfg=cfg,
        year=year,
        month=month,
        month_name=pycalendar.month_name[month],
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        block_types=h.BLOCK_TYPES,
    )


@wft_bp.route("/calendar/block", methods=["POST"])
def add_calendar_block():
    date_from = request.form.get("date_from", "")
    date_to = request.form.get("date_to", "")
    label = request.form.get("label", "")
    block_type = request.form.get("type", "blocked")
    try:
        h.add_calendar_block(date_from=date_from, date_to=date_to, label=label, block_type=block_type)
        flash("Calendar block added.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("wft.calendar"))


@wft_bp.route("/calendar/block/<int:block_id>/delete", methods=["POST"])
def delete_calendar_block(block_id):
    h.delete_calendar_block(block_id)
    flash("Calendar block removed.", "info")
    return redirect(url_for("wft.calendar"))


@wft_bp.route("/calendar/api/events")
def calendar_events_api():
    from datetime import date

    today = date.today()
    year = request.args.get("year", type=int) or today.year
    month = request.args.get("month", type=int) or today.month
    if month < 1 or month > 12:
        month = today.month
    return jsonify(h.get_calendar_events(year, month))


# ── CSV Export ────────────────────────────────────────────────────────────────

@wft_bp.route("/hours/export")
def export_hours():
    import csv, io
    entries = h.get_workhours()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Date", "Task", "Client", "Hours", "Tag", "Notes"])
    for e in sorted(entries, key=lambda x: x["date"], reverse=True):
        writer.writerow([e["date"], e["task"], e["client"],
                         e["hours"], e.get("tag", ""), e.get("notes", "")])
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=workhours.csv"}
    )


# ── Invoices CSV Export ─────────────────────────────────────────────────────────

@wft_bp.route("/invoices/export")
def export_invoices():
    import csv, io
    invs = h.get_invoices()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Invoice #", "Client", "Issue Date", "Due Date",
                     "Subtotal", "Tax Rate", "Tax Amount", "Total",
                     "Currency", "Status"])
    for i in sorted(invs, key=lambda x: x["issue_date"], reverse=True):
        writer.writerow([
            i["invoice_number"], i["client_name"], i["issue_date"],
            i["due_date"], i["subtotal"], i.get("tax_rate", 0),
            i.get("tax_amount", 0), i["total"],
            i.get("currency", "USD"), i["status"],
        ])
    return Response(
        out.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices.csv"}
    )


@wft_bp.route("/clients/export")
def export_clients():
    import csv, io
    clients = h.get_clients()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Name", "Company", "Email", "Phone", "Website",
                     "Default Rate", "Currency", "Status", "Notes", "Added"])
    for c in clients:
        writer.writerow([
            c["name"], c.get("company", ""), c["email"], c.get("phone", ""),
            c.get("website", ""), c.get("default_rate", ""),
            c.get("currency", ""), c.get("status", "active"),
            c.get("notes", ""), c.get("created", ""),
        ])
    return Response(
        out.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=clients.csv"}
    )


@wft_bp.route("/expenses/export")
def export_expenses():
    import csv, io
    expenses = h.get_expenses()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Date", "Title", "Category", "Amount", "Notes"])
    for e in sorted(expenses, key=lambda x: x["date"], reverse=True):
        writer.writerow([e["date"], e["title"], e.get("category", ""),
                         e["amount"], e.get("notes", "")])
    return Response(
        out.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses.csv"}
    )


# ── Expense Tracker ─────────────────────────────────────────────────────────────

@wft_bp.route("/expenses", methods=["GET", "POST"])
def expenses():
    if request.method == "POST":
        f = request.form
        try:
            amount = float(f.get("amount", 0) or 0)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("wft.expenses"))
        h.add_expense(
            title=f.get("title", "").strip() or "Untitled",
            amount=amount,
            category=f.get("category", "Other"),
            expense_date=f.get("expense_date", ""),
            notes=f.get("notes", ""),
        )
        flash("Expense added.", "success")
        return redirect(url_for("wft.expenses"))

    cfg = h.get_settings()
    entries = sorted(h.get_expenses(), key=lambda x: x["date"], reverse=True)
    summary = h.get_expense_summary()
    return render_template("wft/finance/expenses.html", expenses=entries,
                           summary=summary, cfg=cfg,
                           categories=h.EXPENSE_CATEGORIES)


@wft_bp.route("/expenses/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    h.delete_expense(expense_id)
    flash("Expense deleted.", "info")
    return redirect(url_for("wft.expenses"))


# ── Tax Estimator ───────────────────────────────────────────────────────────────

@wft_bp.route("/tax", methods=["GET", "POST"])
def tax_estimator():
    result = None
    cfg = h.get_settings()
    summary = h.get_earnings_summary()
    if request.method == "POST":
        f = request.form
        try:
            income = float(f.get("total_income", 0) or 0)
            rate = float(f.get("tax_rate", 0) or 0)
            exp = float(f.get("total_expenses", 0) or 0)
            result = h.estimate_tax(income, rate, exp)
        except ValueError:
            flash("Invalid numbers provided.", "error")
    return render_template("wft/finance/tax.html", result=result, cfg=cfg,
                           summary=summary)


# ── Global Search ────────────────────────────────────────────────────────────

@wft_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = h.global_search(q) if q else {
        "clients": [],
        "invoices": [],
        "hours": [],
        "expenses": [],
        "sdlc_templates": [],
        "scoped_projects": [],
        "notes": [],
        "quotes": [],
        "contracts": [],
    }
    total = sum(len(v) for v in results.values())
    return render_template("wft/system/search.html", results=results, query=q, total=total)


# ── Profitability Report ──────────────────────────────────────────────────────

@wft_bp.route("/reports")
def reports():
    rows = h.profitability_report()
    cfg = h.get_settings()
    summary = h.get_earnings_summary()
    overdue = h.get_overdue_invoices()
    return render_template("wft/finance/reports.html", rows=rows, cfg=cfg, summary=summary, overdue=overdue)


# ── Data Backup & Restore ────────────────────────────────────────────────────

@wft_bp.route("/backup")
def backup():
    return render_template("wft/system/backup.html")


@wft_bp.route("/backup/download")
def backup_download():
    from datetime import date
    zip_bytes = h.create_backup_zip()
    filename = f"fltk-backup-{date.today().isoformat()}.zip"
    return Response(
        zip_bytes, mimetype="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@wft_bp.route("/backup/restore", methods=["POST"])
def backup_restore():
    if "backup_file" not in request.files:
        flash("No file uploaded.", "error")
        return redirect(url_for("wft.backup"))
    f = request.files["backup_file"]
    if not f.filename.endswith(".zip"):
        flash("Please upload a .zip backup file.", "error")
        return redirect(url_for("wft.backup"))
    restored, errors = h.restore_from_zip(f.read())
    if restored:
        flash(f"Restored: {', '.join(restored)}", "success")
    if errors:
        for e in errors:
            flash(f"Error: {e}", "error")
    return redirect(url_for("wft.backup"))


# ── CRM ──────────────────────────────────────────────────────────────────────

@wft_bp.route("/crm/<int:client_id>")
def crm_client(client_id):
    all_clients = h.get_clients()
    client = next((c for c in all_clients if c["id"] == client_id), None)
    if not client:
        flash("Client not found.", "error")
        return redirect(url_for("wft.clients"))
    interactions = sorted(h.get_interactions(client_id),
                          key=lambda x: x["date"], reverse=True)
    invoices = [i for i in h.get_invoices()
                if i.get("client_name") == client["name"]]
    work_hours = [e for e in h.get_workhours()
                  if e.get("client") == client["name"]]
    total_hours = round(sum(e["hours"] for e in work_hours), 2)
    total_billed = round(sum(i["total"] for i in invoices), 2)
    total_paid = round(sum(i["total"] for i in invoices
                           if i.get("status") == "paid"), 2)
    cfg = h.get_settings()
    scoped_projects = h.get_client_scoped_projects(client_id)
    pinned_notes = [n for n in h.get_client_notes(client_id) if n.get("pinned")][:3]
    return render_template(
        "wft/clients/crm_client.html",
        client=client,
        interactions=interactions,
        invoices=invoices[:5],
        scoped_projects=scoped_projects,
        total_hours=total_hours,
        total_billed=total_billed,
        total_paid=total_paid,
        crm_types=h.CRM_TYPES,
        cfg=cfg,
        pinned_notes=pinned_notes,
    )


@wft_bp.route("/crm/<int:client_id>/add", methods=["POST"])
def crm_add_interaction(client_id):
    f = request.form
    h.add_interaction(
        client_id=client_id,
        interaction_type=f.get("type", "Note"),
        summary=f.get("summary", "").strip() or "No details.",
        interaction_date=f.get("date", ""),
        follow_up=f.get("follow_up", ""),
    )
    flash("Interaction logged.", "success")
    return redirect(url_for("wft.crm_client", client_id=client_id))


@wft_bp.route("/crm/<int:client_id>/delete/<int:interaction_id>", methods=["POST"])
def crm_delete_interaction(client_id, interaction_id):
    h.delete_interaction(interaction_id)
    flash("Interaction removed.", "info")
    return redirect(url_for("wft.crm_client", client_id=client_id))


# ── Client Notes ─────────────────────────────────────────────────────────────

@wft_bp.route("/clients/<int:client_id>/notes")
def client_notes(client_id):
    all_clients = h.get_clients()
    client = next((c for c in all_clients if c["id"] == client_id), None)
    if not client:
        flash("Client not found.", "error")
        return redirect(url_for("wft.clients"))
    notes = h.get_client_notes(client_id)
    return render_template("wft/clients/client_notes.html", client=client, notes=notes, edit_note=None)


@wft_bp.route("/clients/<int:client_id>/notes/add", methods=["POST"])
def add_client_note(client_id):
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not title and not content:
        flash("Add a title or content for the note.", "error")
        return redirect(url_for("wft.client_notes", client_id=client_id))
    h.add_client_note(client_id, title, content)
    flash("Note added.", "success")
    return redirect(url_for("wft.client_notes", client_id=client_id))


@wft_bp.route("/clients/<int:client_id>/notes/<int:note_id>/edit")
def edit_client_note(client_id, note_id):
    all_clients = h.get_clients()
    client = next((c for c in all_clients if c["id"] == client_id), None)
    note = h.get_client_note(note_id)
    if not client or not note or note.get("client_id") != client_id:
        flash("Note not found.", "error")
        return redirect(url_for("wft.client_notes", client_id=client_id))
    notes = h.get_client_notes(client_id)
    return render_template("wft/clients/client_notes.html", client=client, notes=notes, edit_note=note)


@wft_bp.route("/clients/<int:client_id>/notes/<int:note_id>/edit", methods=["POST"])
def update_client_note(client_id, note_id):
    note = h.get_client_note(note_id)
    if not note or note.get("client_id") != client_id:
        flash("Note not found.", "error")
        return redirect(url_for("wft.client_notes", client_id=client_id))
    h.update_client_note(note_id, request.form.get("title", ""), request.form.get("content", ""))
    flash("Note updated.", "success")
    return redirect(url_for("wft.client_notes", client_id=client_id))


@wft_bp.route("/clients/<int:client_id>/notes/<int:note_id>/delete", methods=["POST"])
def delete_client_note(client_id, note_id):
    note = h.get_client_note(note_id)
    if note and note.get("client_id") == client_id:
        h.delete_client_note(note_id)
        flash("Note deleted.", "info")
    else:
        flash("Note not found.", "error")
    return redirect(url_for("wft.client_notes", client_id=client_id))


@wft_bp.route("/clients/<int:client_id>/notes/<int:note_id>/pin", methods=["POST"])
def pin_client_note(client_id, note_id):
    note = h.get_client_note(note_id)
    if note and note.get("client_id") == client_id:
        h.toggle_note_pin(note_id)
        flash("Note pin updated.", "success")
    else:
        flash("Note not found.", "error")
    return redirect(url_for("wft.client_notes", client_id=client_id))

