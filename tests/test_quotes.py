import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def test_quote_number_auto_increments(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    first = h.add_quote(
        client_id=None,
        client_name="Acme",
        title="Landing Page",
        items=[{"description": "Design", "qty": 2, "rate": 100}],
        tax_rate=0,
        currency="USD",
        currency_symbol="$",
        expiry_date="2099-01-01",
        notes="",
    )
    second = h.add_quote(
        client_id=None,
        client_name="Beta",
        title="API Build",
        items=[{"description": "Dev", "qty": 3, "rate": 120}],
        tax_rate=0,
        currency="USD",
        currency_symbol="$",
        expiry_date="2099-01-01",
        notes="",
    )

    assert first["quote_number"] == "QT-001"
    assert second["quote_number"] == "QT-002"


def test_amounts_computed_correctly(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    quote = h.add_quote(
        client_id=None,
        client_name="Gamma",
        title="Feature Work",
        items=[
            {"description": "Module A", "qty": 2, "rate": 50},
            {"description": "Module B", "qty": 1.5, "rate": 80},
        ],
        tax_rate=10,
        currency="USD",
        currency_symbol="$",
        expiry_date="2099-01-01",
        notes="",
    )

    assert quote["subtotal"] == 220.0
    assert quote["tax_amount"] == 22.0
    assert quote["total"] == 242.0


def test_convert_to_invoice_creates_invoice(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    quote = h.add_quote(
        client_id=None,
        client_name="Delta",
        title="Consulting",
        items=[{"description": "Architecture", "qty": 4, "rate": 75}],
        tax_rate=0,
        currency="USD",
        currency_symbol="$",
        expiry_date="2099-01-01",
        notes="",
    )

    invoice = h.convert_quote_to_invoice(quote["id"])
    reloaded = h.get_quote(quote["id"])

    assert invoice is not None
    assert invoice["invoice_number"].startswith("INV-")
    assert reloaded["converted_invoice_id"] == invoice["id"]


def test_cannot_delete_converted_quote(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    quote = h.add_quote(
        client_id=None,
        client_name="Epsilon",
        title="Support",
        items=[{"description": "Monthly", "qty": 1, "rate": 500}],
        tax_rate=0,
        currency="USD",
        currency_symbol="$",
        expiry_date="2099-01-01",
        notes="",
    )
    h.convert_quote_to_invoice(quote["id"])

    assert h.delete_quote(quote["id"]) is False


def test_status_transitions(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    quote = h.add_quote(
        client_id=None,
        client_name="Zeta",
        title="Audit",
        items=[{"description": "Security Audit", "qty": 2, "rate": 150}],
        tax_rate=0,
        currency="USD",
        currency_symbol="$",
        expiry_date="2099-01-01",
        notes="",
    )

    h.update_quote_status(quote["id"], "sent")
    h.update_quote_status(quote["id"], "accepted")

    updated = h.get_quote(quote["id"])
    assert updated is not None
    assert updated["status"] == "accepted"
