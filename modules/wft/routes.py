from flask import render_template, request, redirect, url_for, flash, Response
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
        })
        flash("Settings saved.", "success")
        return redirect(url_for("wft.settings"))

    cfg = h.get_settings()
    return render_template("wft/settings.html", cfg=cfg,
                           currencies=h.CURRENCY_OPTIONS)


# ── Proposal Templates ────────────────────────────────────────────────────────

@wft_bp.route("/templates")
def templates():
    return render_template("wft/templates.html", templates=h.get_templates())


@wft_bp.route("/templates/<key>")
def template_detail(key):
    tmpl = h.get_template(key)
    if not tmpl:
        flash("Template not found.", "error")
        return redirect(url_for("wft.templates"))
    return render_template("wft/template_detail.html", tmpl=tmpl, key=key)


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
        "wft/sdlc_templates.html",
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
    return render_template("wft/sdlc_template_form.html", template=None)


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
        "wft/sdlc_template_detail.html",
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

    return render_template("wft/sdlc_template_form.html", template=template)


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
    return render_template("wft/sdlc_template_print.html", template=template)


@wft_bp.route("/sdlc/templates/<int:template_id>/pdf")
def pdf_sdlc_template(template_id):
    template = h.get_sdlc_template(template_id)
    if not template:
        flash("SDLC template not found.", "error")
        return redirect(url_for("wft.sdlc_templates"))
    filename = f"{template['slug'] or template['id']}.pdf"
    return _render_pdf_response(
        "wft/sdlc_template_print.html",
        {"template": template},
        filename,
        "wft.sdlc_template_detail",
        template_id=template_id,
    )


# ── Scoped Projects ─────────────────────────────────────────────────────────

@wft_bp.route("/sdlc/projects")
def scoped_projects():
    selected_client = request.args.get("client_id", type=int)
    projects = h.get_scoped_projects()
    if selected_client:
        projects = [project for project in projects if project.get("client_id") == selected_client]
    return render_template(
        "wft/scoped_projects.html",
        projects=projects,
        clients=h.get_clients(),
        selected_client=selected_client,
        stats=h.scoped_project_stats(),
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
        "wft/scoped_project_form.html",
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
    return render_template("wft/scoped_project_detail.html", project=project, template=template)


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
        "wft/scoped_project_form.html",
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
    return render_template("wft/scoped_project_print.html", project=project, template=template)


@wft_bp.route("/sdlc/projects/<int:project_id>/pdf")
def pdf_scoped_project(project_id):
    project = h.get_scoped_project(project_id)
    if not project:
        flash("Scoped project not found.", "error")
        return redirect(url_for("wft.scoped_projects"))
    template = h.get_sdlc_template(project.get("template_id"))
    filename = f"{project['project_name'].replace(' ', '-').lower()}.pdf"
    return _render_pdf_response(
        "wft/scoped_project_print.html",
        {"project": project, "template": template},
        filename,
        "wft.scoped_project_detail",
        project_id=project_id,
    )


# ── Client Tracker ───────────────────────────────────────────────────────────

@wft_bp.route("/clients")
def clients():
    return render_template("wft/clients.html", clients=h.get_clients(),
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

    return render_template("wft/edit_client.html", client=client,
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
    return render_template("wft/invoices.html", invoices=invs, today=today, summary=summary)


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

        invoice = h.create_invoice(
            client_name=f["client_name"],
            items=items,
            due_date=f["due_date"],
            notes=f.get("notes", ""),
            currency=currency,
            currency_symbol=symbol,
            tax_rate=tax_rate,
        )
        flash(f"Invoice {invoice['invoice_number']} created.", "success")
        return redirect(url_for("wft.invoice_detail", inv_id=invoice["id"]))
    return render_template("wft/invoice_form.html", clients=h.get_clients(),
                           cfg=cfg, currencies=h.CURRENCY_OPTIONS)


@wft_bp.route("/invoices/<int:inv_id>")
def invoice_detail(inv_id):
    inv_list = h.get_invoices()
    inv = next((i for i in inv_list if i["id"] == inv_id), None)
    if not inv:
        flash("Invoice not found.", "error")
        return redirect(url_for("wft.invoices"))
    cfg = h.get_settings()
    return render_template("wft/invoice_detail.html", inv=inv, cfg=cfg)


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
        html = render_template("wft/invoice_pdf.html", inv=inv,
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
    return render_template("wft/hours.html", entries=entries, stats=stats,
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

    return render_template("wft/edit_hours.html", entry=entry,
                           clients=h.get_clients())


@wft_bp.route("/hours/delete/<int:entry_id>", methods=["POST"])
def delete_hours(entry_id):
    h.delete_workhour(entry_id)
    flash("Entry deleted.", "info")
    return redirect(url_for("wft.hours"))


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
    return render_template("wft/expenses.html", expenses=entries,
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
    return render_template("wft/tax.html", result=result, cfg=cfg,
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
    }
    total = sum(len(v) for v in results.values())
    return render_template("wft/search.html", results=results, query=q, total=total)


# ── Profitability Report ──────────────────────────────────────────────────────

@wft_bp.route("/reports")
def reports():
    rows = h.profitability_report()
    cfg = h.get_settings()
    return render_template("wft/reports.html", rows=rows, cfg=cfg)


# ── Data Backup & Restore ────────────────────────────────────────────────────

@wft_bp.route("/backup")
def backup():
    return render_template("wft/backup.html")


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
    return render_template(
        "wft/crm_client.html",
        client=client,
        interactions=interactions,
        invoices=invoices[:5],
        scoped_projects=scoped_projects,
        total_hours=total_hours,
        total_billed=total_billed,
        total_paid=total_paid,
        crm_types=h.CRM_TYPES,
        cfg=cfg,
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
