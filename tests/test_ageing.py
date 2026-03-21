"""
Tests for N4 — Invoice Ageing Report
"""
import pytest
from datetime import date, timedelta
from modules.wft import helpers as h


class TestInvoiceAgeing:
    """Test A/R ageing report functions."""

    def test_current_bucket_includes_not_yet_due(self):
        """Current bucket should include invoices not yet due."""
        ageing = h.get_ar_ageing()
        assert isinstance(ageing, dict)
        assert "current" in ageing

        # Verify structure
        assert "invoices" in ageing["current"]
        assert "total" in ageing["current"]
        assert "count" in ageing["current"]

    def test_1_30_bucket_correct_date_range(self):
        """1–30 days bucket should consider correct date range."""
        ageing = h.get_ar_ageing()
        assert "1_30" in ageing

        # All invoices in 1_30 should have days_age between 1 and 30
        for inv in ageing["1_30"]["invoices"]:
            assert 0 < inv["days_age"] <= 30

    def test_31_60_bucket_correct_date_range(self):
        """31–60 days bucket should consider correct date range."""
        ageing = h.get_ar_ageing()
        assert "31_60" in ageing

        for inv in ageing["31_60"]["invoices"]:
            assert 30 < inv["days_age"] <= 60

    def test_60_plus_bucket_accumulates_old_invoices(self):
        """60+ days bucket should include all very old invoices."""
        ageing = h.get_ar_ageing()
        assert "60_plus" in ageing

        for inv in ageing["60_plus"]["invoices"]:
            assert inv["days_age"] > 60

    def test_grand_total_equals_sum_of_buckets(self):
        """Grand total should equal sum of all bucket totals."""
        ageing = h.get_ar_ageing()
        
        bucket_sum = (
            ageing["current"]["total"]
            + ageing["1_30"]["total"]
            + ageing["31_60"]["total"]
            + ageing["60_plus"]["total"]
        )
        
        # Use approximate equality due to floating point
        assert abs(ageing["grand_total"] - bucket_sum) < 0.01

    def test_paid_invoices_excluded(self):
        """Paid invoices should not appear in any bucket."""
        ageing = h.get_ar_ageing()
        
        all_invoices = (
            ageing["current"]["invoices"]
            + ageing["1_30"]["invoices"]
            + ageing["31_60"]["invoices"]
            + ageing["60_plus"]["invoices"]
        )
        
        for inv in all_invoices:
            assert inv["status"] != "paid"

    def test_ageing_structure_complete(self):
        """Ageing report should have all required buckets and fields."""
        ageing = h.get_ar_ageing()
        
        required_buckets = {"current", "1_30", "31_60", "60_plus", "grand_total"}
        assert required_buckets.issubset(ageing.keys())
        
        for bucket_name in ["current", "1_30", "31_60", "60_plus"]:
            bucket = ageing[bucket_name]
            assert "total" in bucket
            assert "count" in bucket
            assert "invoices" in bucket
            assert isinstance(bucket["invoices"], list)

    def test_invoice_entry_has_required_fields(self):
        """Each invoice in ageing report should have required fields."""
        ageing = h.get_ar_ageing()
        
        # Get first invoice from any bucket
        test_invoice = None
        for bucket_name in ["current", "1_30", "31_60", "60_plus"]:
            if ageing[bucket_name]["invoices"]:
                test_invoice = ageing[bucket_name]["invoices"][0]
                break
        
        if test_invoice:
            required_fields = {
                "id",
                "invoice_number",
                "client_name",
                "due_date",
                "days_age",
                "total",
                "status",
            }
            assert required_fields.issubset(test_invoice.keys())

    def test_invoices_sorted_by_due_date_desc(self):
        """Invoices within each bucket should be sorted by due_date descending."""
        ageing = h.get_ar_ageing()
        
        for bucket_name in ["current", "1_30", "31_60", "60_plus"]:
            invoices = ageing[bucket_name]["invoices"]
            if len(invoices) > 1:
                for i in range(len(invoices) - 1):
                    assert invoices[i]["due_date"] >= invoices[i + 1]["due_date"]

    def test_bucket_count_matches_invoice_count(self):
        """Bucket count should match number of invoices in that bucket."""
        ageing = h.get_ar_ageing()
        
        for bucket_name in ["current", "1_30", "31_60", "60_plus"]:
            bucket = ageing[bucket_name]
            assert bucket["count"] == len(bucket["invoices"])

    def test_bucket_total_sums_invoice_amounts(self):
        """Bucket total should equal sum of individual invoice amounts."""
        ageing = h.get_ar_ageing()
        
        for bucket_name in ["current", "1_30", "31_60", "60_plus"]:
            bucket = ageing[bucket_name]
            invoice_sum = sum(inv["total"] for inv in bucket["invoices"])
            assert abs(bucket["total"] - invoice_sum) < 0.01

    def test_handles_empty_invoices_gracefully(self):
        """Report should handle case where no unpaid invoices exist."""
        ageing = h.get_ar_ageing()
        
        # If there are no invoices at all, all buckets should be empty
        total_count = sum(ageing[b]["count"] for b in ["current", "1_30", "31_60", "60_plus"])
        
        if total_count == 0:
            assert ageing["grand_total"] == 0
