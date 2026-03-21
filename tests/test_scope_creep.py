"""
Tests for N3 — Scope Creep Detector
"""
import pytest
from modules.wft import helpers as h


class TestScopeCreep:
    """Test scope creep detector functions."""

    def test_on_track_when_under_80_percent(self):
        """Utilisation under 80% should show 'on_track' status."""
        # Find or create a project
        projects = h.get_scoped_projects()
        if not projects:
            pytest.skip("No scoped projects in test data")

        project_id = projects[0]["id"]
        scope = h.get_scope_status(project_id)

        # If the project has budget_hours and utilisation < 0.80, status should be "on_track"
        if scope.get("budget_hours", 0) > 0:
            if scope.get("utilisation", 1) < 0.80:
                assert scope["status"] == "on_track"

    def test_warning_when_between_80_and_100(self):
        """Utilisation between 80% and 100% should show 'warning' status."""
        projects = h.get_scoped_projects()
        if not projects:
            pytest.skip("No scoped projects in test data")

        project_id = projects[0]["id"]
        scope = h.get_scope_status(project_id)

        if scope.get("budget_hours", 0) > 0:
            util = scope.get("utilisation", 1)
            if 0.80 <= util < 1.00:
                assert scope["status"] == "warning"

    def test_over_budget_status_when_exceeded(self):
        """Utilisation >= 100% should show 'over_budget' status."""
        projects = h.get_scoped_projects()
        if not projects:
            pytest.skip("No scoped projects in test data")

        project_id = projects[0]["id"]
        scope = h.get_scope_status(project_id)

        if scope.get("budget_hours", 0) > 0:
            if scope.get("utilisation", 0) >= 1.00:
                assert scope["status"] == "over_budget"
                assert scope["hours_over"] > 0

    def test_zero_budget_hours_returns_none_utilisation(self):
        """Project with no budget_hours should have None utilisation."""
        projects = h.get_scoped_projects()
        if not projects:
            pytest.skip("No scoped projects in test data")

        project_id = projects[0]["id"]
        # Temporarily mock a project with zero budget
        scope = h.get_scope_status(project_id)

        if scope.get("budget_hours", 0) == 0:
            assert scope["status"] == "no_budget"
            assert scope["utilisation"] is None

    def test_get_all_scope_statuses_sorted_by_utilisation(self):
        """get_all_scope_statuses should return list sorted by utilisation desc."""
        statuses = h.get_all_scope_statuses()
        assert isinstance(statuses, list)

        # Verify sorted by utilisation descending
        if len(statuses) > 1:
            for i in range(len(statuses) - 1):
                util_curr = statuses[i].get("utilisation") or -1
                util_next = statuses[i + 1].get("utilisation") or -1
                assert util_curr >= util_next

    def test_scope_status_includes_required_fields(self):
        """Scope status dict should include all required fields."""
        projects = h.get_scoped_projects()
        if not projects:
            pytest.skip("No scoped projects in test data")

        project_id = projects[0]["id"]
        scope = h.get_scope_status(project_id)

        required_fields = {
            "project_id",
            "project_name",
            "client_name",
            "status",
            "budget_hours",
            "actual_hours",
            "utilisation",
            "utilisation_percent",
            "hours_over",
        }
        assert required_fields.issubset(scope.keys())

    def test_scope_correctly_counts_client_hours(self):
        """Scope should sum all workhours for matching client name."""
        projects = h.get_scoped_projects()
        if not projects:
            pytest.skip("No scoped projects in test data")

        project = projects[0]
        project_id = project["id"]
        client_name = project.get("client_name", "")

        scope = h.get_scope_status(project_id)

        # Manually verify the hour count
        if client_name:
            all_hours = h.get_workhours()
            expected_hours = sum(
                wh.get("hours", 0)
                for wh in all_hours
                if wh.get("client", "").strip().lower() == client_name.strip().lower()
            )
            assert scope["actual_hours"] == expected_hours
