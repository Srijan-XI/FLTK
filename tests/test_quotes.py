import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def _make_quote(client_name, title, items=None, tax_rate=0):
    """Helper: create a quote with sensible defaults."""
    return h.add_quote(
        client_id=None,
        client_name=client_name,
        title=title,
        items=items or [{"description": "Work", "qty": 1, "rate": 100}],
        tax_rate=tax_rate,
        currency="USD",
        currency_symbol="$",
        expiry_date="2099-01-01",
        notes="",
    )


def test_quote_number_auto_increments(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    first = _make_quote("Acme", "Landing Page")
    second = _make_quote("Beta", "API Build")

    assert first["quote_number"] == "QT-001"
    assert second["quote_number"] == "QT-002"


def test_amounts_computed_correctly(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    quote = _make_quote(
        "Gamma",
        "Feature Work",
        items=[
            {"description": "Module A", "qty": 2, "rate": 50},
            {"description": "Module B", "qty": 1.5, "rate": 80},
        ],
        tax_rate=10,
    )

    assert quote["subtotal"] == 220.0
    assert quote["tax_amount"] == 22.0
    assert quote["total"] == 242.0


def test_convert_to_invoice_requires_accepted_status(temp_data_dir):
    """convert_quote_to_invoice must raise when status is not 'accepted'."""
    h.save_settings(h.DEFAULT_SETTINGS)
    quote = _make_quote("Delta", "Consulting")  # status = 'draft'

    with pytest.raises(ValueError, match="accepted"):
        h.convert_quote_to_invoice(quote["id"])


def test_convert_to_invoice_creates_invoice(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    quote = _make_quote("Delta", "Consulting")
    h.update_quote_status(quote["id"], "accepted")  # set correct status first

    invoice = h.convert_quote_to_invoice(quote["id"])
    reloaded = h.get_quote(quote["id"])

    assert invoice is not None
    assert invoice["invoice_number"].startswith("INV-")
    assert reloaded["converted_invoice_id"] == invoice["id"]


def test_convert_already_converted_quote_raises(temp_data_dir):
    """Trying to convert a quote that already has an invoice must raise."""
    h.save_settings(h.DEFAULT_SETTINGS)
    quote = _make_quote("Epsilon", "Support")
    h.update_quote_status(quote["id"], "accepted")
    h.convert_quote_to_invoice(quote["id"])

    with pytest.raises(ValueError, match="already been converted"):
        h.convert_quote_to_invoice(quote["id"])


def test_cannot_delete_converted_quote(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    quote = _make_quote("Epsilon", "Delete Test")
    h.update_quote_status(quote["id"], "accepted")
    h.convert_quote_to_invoice(quote["id"])

    assert h.delete_quote(quote["id"]) is False


def test_status_transitions(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    quote = _make_quote("Zeta", "Audit")

    h.update_quote_status(quote["id"], "sent")
    h.update_quote_status(quote["id"], "accepted")

    updated = h.get_quote(quote["id"])
    assert updated is not None
    assert updated["status"] == "accepted"
