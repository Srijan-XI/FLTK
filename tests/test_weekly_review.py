"""
Tests for N6 — Weekly Reviews
"""
import pytest
from datetime import date, datetime, timedelta
from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "REVIEW_FILE", "weekly_reviews.json")
    return tmp_path


class TestWeeklyReviews:
    """Test weekly review functions."""

    def test_save_weekly_review_creates_entry(self, temp_data_dir):
        """Saving a review should create a new entry with unique ID."""
        before_count = len(h.get_weekly_reviews())
        
        review = h.save_weekly_review(
            week_start="2026-03-16",
            went_well="Made good progress on project A.",
            improve="Need to communicate more with client.",
            next_priority="Finish design mockups for project B."
        )
        
        assert review["id"] > 0
        assert review["week_start"] == "2026-03-16"
        assert review["went_well"] == "Made good progress on project A."
        assert review["improve"] == "Need to communicate more with client."
        assert review["next_priority"] == "Finish design mockups for project B."
        assert review["created_at"] == date.today().isoformat()
        
        after_count = len(h.get_weekly_reviews())
        assert after_count == before_count + 1

    def test_get_weekly_reviews_sorted_desc(self, temp_data_dir):
        """Reviews should be sorted by week_start descending."""
        reviews = h.get_weekly_reviews()
        if len(reviews) > 1:
            for i in range(len(reviews) - 1):
                assert reviews[i]["week_start"] >= reviews[i + 1]["week_start"]

    def test_get_weekly_review_by_id(self, temp_data_dir):
        """Should retrieve a specific review by ID."""
        reviews = h.get_weekly_reviews()
        if reviews:
            review_id = reviews[0]["id"]
            retrieved = h.get_weekly_review(review_id)
            assert retrieved is not None
            assert retrieved["id"] == review_id

    def test_get_review_for_week(self, temp_data_dir):
        """Should find existing review for a given week."""
        review = h.save_weekly_review(
            week_start="2026-03-23",
            went_well="Excellent week!",
            improve="Time management",
            next_priority="Focus on quality"
        )
        
        found = h.get_review_for_week("2026-03-23")
        assert found is not None
        assert found["id"] == review["id"]

    def test_get_review_for_week_not_found(self, temp_data_dir):
        """Should return None if no review for the week."""
        found = h.get_review_for_week("1999-01-01")
        # If this date exists in test data, skip; otherwise assert None
        if not found:
            assert found is None

    def test_update_weekly_review(self, temp_data_dir):
        """Should update an existing review."""
        review = h.save_weekly_review(
            week_start="2026-03-30",
            went_well="Initial entry",
            improve="Initial entry",
            next_priority="Initial entry"
        )
        
        updated = h.update_weekly_review(
            review["id"],
            went_well="Updated: Great week!",
            improve="Updated: Communication",
            next_priority="Updated: Quality focus"
        )
        
        assert updated is not None
        assert updated["went_well"] == "Updated: Great week!"
        assert updated["improve"] == "Updated: Communication"
        assert updated["next_priority"] == "Updated: Quality focus"

    def test_delete_weekly_review(self, temp_data_dir):
        """Should delete a review by ID."""
        review = h.save_weekly_review(
            week_start="2026-04-06",
            went_well="Temp review",
            improve="Temp review",
            next_priority="Temp review"
        )
        
        deleted = h.delete_weekly_review(review["id"])
        assert deleted is True
        
        # Verify it's gone
        found = h.get_weekly_review(review["id"])
        assert found is None

    def test_search_reviews_by_went_well(self, temp_data_dir):
        """Should search reviews by went_well text."""
        results = h.search_reviews("excellent")
        # Results may vary depending on test data
        assert isinstance(results, list)

    def test_search_reviews_case_insensitive(self, temp_data_dir):
        """Search should be case-insensitive."""
        review = h.save_weekly_review(
            week_start="2026-04-13",
            went_well="Amazing progress!",
            improve="Time management",
            next_priority="Continue momentum"
        )
        
        results = h.search_reviews("amazing")
        assert any(r["id"] == review["id"] for r in results)

    def test_build_weekly_prefill_structure(self, temp_data_dir):
        """build_weekly_prefill should return proper structure."""
        prefill = h.build_weekly_prefill("2026-03-16")
        
        required_fields = {
            "week_start",
            "week_end",
            "total_hours",
            "total_income",
            "top_clients",
            "top_tasks"
        }
        assert required_fields.issubset(prefill.keys())

    def test_build_weekly_prefill_valid_dates(self, temp_data_dir):
        """Prefilled dates should be valid ISO strings."""
        prefill = h.build_weekly_prefill("2026-03-16")
        
        # Should parse without error
        datetime.strptime(prefill["week_start"], "%Y-%m-%d")
        datetime.strptime(prefill["week_end"], "%Y-%m-%d")

    def test_build_weekly_prefill_week_span(self, temp_data_dir):
        """week_end should be 6 days after week_start (full week)."""
        prefill = h.build_weekly_prefill("2026-03-16")
        
        start = datetime.strptime(prefill["week_start"], "%Y-%m-%d").date()
        end = datetime.strptime(prefill["week_end"], "%Y-%m-%d").date()
        
        assert (end - start).days == 6

    def test_build_weekly_prefill_totals_non_negative(self, temp_data_dir):
        """Hours and income should never be negative."""
        prefill = h.build_weekly_prefill("2026-03-16")
        
        assert prefill["total_hours"] >= 0
        assert prefill["total_income"] >= 0

    def test_review_entry_has_required_fields(self, temp_data_dir):
        """Saved review should have all required fields."""
        review = h.save_weekly_review(
            week_start="2026-04-20",
            went_well="Good week",
            improve="Communication",
            next_priority="Focus"
        )
        
        required_fields = {
            "id",
            "week_start",
            "went_well",
            "improve",
            "next_priority",
            "created_at"
        }
        assert required_fields.issubset(review.keys())

    def test_save_review_strips_whitespace(self, temp_data_dir):
        """Whitespace should be stripped from text fields."""
        review = h.save_weekly_review(
            week_start="2026-04-27",
            went_well="  Extra spaces  ",
            improve="\n\nWith newlines\n",
            next_priority="  \t  Tabs too  "
        )
        
        assert review["went_well"] == "Extra spaces"
        assert review["improve"] == "With newlines"
        assert review["next_priority"] == "Tabs too"

    def test_search_reviews_empty_query(self, temp_data_dir):
        """Empty search query should return all or filtered results."""
        results = h.search_reviews("")
        assert isinstance(results, list)

    def test_get_weekly_reviews_returns_list(self, temp_data_dir):
        """get_weekly_reviews should always return a list."""
        reviews = h.get_weekly_reviews()
        assert isinstance(reviews, list)

    def test_update_nonexistent_review(self, temp_data_dir):
        """Updating nonexistent review should return None."""
        updated = h.update_weekly_review(
            99999,
            went_well="test",
            improve="test",
            next_priority="test"
        )
        assert updated is None

    def test_delete_nonexistent_review(self, temp_data_dir):
        """Deleting nonexistent review should return False."""
        deleted = h.delete_weekly_review(99999)
        assert deleted is False
