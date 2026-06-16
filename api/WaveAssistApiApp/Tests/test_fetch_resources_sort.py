import json
from django.test import SimpleTestCase, RequestFactory
from unittest.mock import patch, MagicMock

from WaveAssistApiApp import providers
from WaveAssistApiApp.providers import fetch_resources


# Raw GitHub-style repo items with pushed_at out of chronological order.
# B (2026-06-01) is newest, then C (2025-03-01), then A (2024-01-01).
def _items_out_of_order():
    return [
        {"id": "a", "full_name": "A", "pushed_at": "2024-01-01T00:00:00Z"},
        {"id": "b", "full_name": "B", "pushed_at": "2026-06-01T00:00:00Z"},
        {"id": "c", "full_name": "C", "pushed_at": "2025-03-01T00:00:00Z"},
    ]


class FetchResourcesSortTestCase(SimpleTestCase):
    """Tests for recent-first sorting + archived/sort_key promotion in fetch_resources.

    Uses SimpleTestCase (no DB) because the provider lookup, validator, auth-token
    fetch and provider item fetch are all mocked — matching test_get_nodes_from_github.py.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def _call(self, items, resource_configs=None):
        """Drive fetch_resources with provider/auth/items all mocked; return parsed body."""
        if resource_configs is None:
            resource_configs = {
                "id_field": "id",
                "name_field": "full_name",
                "endpoint": "https://api.github.com/user/repos",
            }

        request = self.factory.post("/fetch_resources", {"provider_name": "github"})

        fake_user = MagicMock(uid="uid-1")
        fake_project = MagicMock(project_key="proj-1")
        fake_provider = MagicMock(resource_configs=resource_configs)

        with patch.object(
            providers.validator,
            "validate_user_and_project",
            return_value=(True, "ok", fake_user, fake_project),
        ), patch.object(
            providers.Provider.objects,
            "get",
            return_value=fake_provider,
        ), patch.object(
            providers.utils,
            "fetch_data_for_key_internal",
            return_value=(True, "fake-token", "ok"),
        ), patch.object(
            providers,
            "fetch_provider_items",
            return_value=(items, None),
        ):
            response = fetch_resources(request)

        body = json.loads(response.content)
        self.assertEqual(body.get("success"), "1", body)
        return body["data"]["resources"]

    def test_resources_sorted_by_sort_key_desc(self):
        resources = self._call(_items_out_of_order())
        self.assertEqual([r["name"] for r in resources], ["B", "C", "A"])
        for r in resources:
            self.assertIn("sort_key", r)

    def test_archived_flag_promoted_and_default_false(self):
        items = [
            {"id": "a", "full_name": "A", "pushed_at": "2026-01-01T00:00:00Z", "archived": True},
            {"id": "b", "full_name": "B", "pushed_at": "2025-01-01T00:00:00Z"},
        ]
        resources = self._call(items)
        by_name = {r["name"]: r for r in resources}
        self.assertIs(by_name["A"]["archived"], True)
        self.assertIs(by_name["B"]["archived"], False)
        # Archived repos remain in the list (UI excludes them from preselection only).
        self.assertEqual(len(resources), 2)

    def test_missing_sort_key_sorts_last(self):
        items = [
            {"id": "a", "full_name": "A", "pushed_at": "2025-01-01T00:00:00Z"},
            {"id": "b", "full_name": "B"},  # no pushed_at
            {"id": "c", "full_name": "C", "pushed_at": "2026-01-01T00:00:00Z"},
        ]
        resources = self._call(items)
        self.assertEqual([r["name"] for r in resources], ["C", "A", "B"])
        self.assertIsNone(resources[-1]["sort_key"])

    def test_custom_sort_field_from_config(self):
        items = [
            {"id": "a", "full_name": "A", "pushed_at": "2030-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"},
            {"id": "b", "full_name": "B", "pushed_at": "2020-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
        ]
        resource_configs = {
            "id_field": "id",
            "name_field": "full_name",
            "endpoint": "https://api.github.com/user/repos",
            "sort_field": "updated_at",
        }
        resources = self._call(items, resource_configs=resource_configs)
        # Ordered by updated_at desc -> B before A, even though pushed_at says otherwise.
        self.assertEqual([r["name"] for r in resources], ["B", "A"])

    def test_extra_still_contains_raw_fields(self):
        resources = self._call(_items_out_of_order())
        newest = resources[0]
        # Promotion does not remove fields from extra (back-compat for existing consumers).
        self.assertIn("pushed_at", newest["extra"])
        self.assertEqual(newest["extra"]["pushed_at"], "2026-06-01T00:00:00Z")
