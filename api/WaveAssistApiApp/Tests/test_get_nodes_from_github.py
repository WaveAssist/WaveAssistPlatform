import base64
from django.test import SimpleTestCase
from unittest.mock import patch, MagicMock

from WaveAssistApiApp.Utils import projectSetup as ps


def _b64(text):
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


# Repo tree mimicking gitzoid: 3 real node files at the root plus a tests/ tree.
FAKE_TREE = {
    "tree": [
        {"type": "blob", "path": "fetch_pull_requests.py"},
        {"type": "blob", "path": "generate_review.py"},
        {"type": "blob", "path": "post_comment.py"},
        {"type": "blob", "path": "tests/__init__.py"},
        {"type": "blob", "path": "tests/conftest.py"},
        {"type": "blob", "path": "tests/unit/test_generate_review.py"},
        {"type": "blob", "path": "README.md"},
    ]
}


def _make_get(call_log):
    """Return a fake requests.get that records calls and serves tree/file JSON."""

    def fake_get(url, *args, **kwargs):
        call_log.append({"url": url, "timeout": kwargs.get("timeout")})
        resp = MagicMock()
        resp.status_code = 200
        if "git/trees/" in url:
            resp.json.return_value = FAKE_TREE
        else:
            # contents endpoint -> return some base64 content
            resp.json.return_value = {"content": _b64("print('hi')")}
        return resp

    return fake_get


class GetNodesFromGithubTests(SimpleTestCase):
    def test_only_fetches_files_referenced_in_config(self):
        call_log = []
        wanted = {"fetch_pull_requests", "generate_review", "post_comment"}
        with patch.object(ps.requests, "get", side_effect=_make_get(call_log)):
            node_files = ps.get_nodes_from_github(
                "gitzoid", owner="WaveAssist", wanted_files=wanted
            )

        fetched_names = {n["node_name"] for n in node_files}
        self.assertEqual(fetched_names, wanted)

        # 1 tree call + exactly 3 file calls (no tests/, no README)
        content_calls = [c for c in call_log if "git/trees/" not in c["url"]]
        self.assertEqual(len(content_calls), 3)
        for c in content_calls:
            self.assertTrue(
                any(w in c["url"] for w in wanted),
                f"Unexpected file fetched: {c['url']}",
            )

    def test_every_request_has_a_timeout(self):
        call_log = []
        wanted = {"fetch_pull_requests"}
        with patch.object(ps.requests, "get", side_effect=_make_get(call_log)):
            ps.get_nodes_from_github("gitzoid", owner="WaveAssist", wanted_files=wanted)

        self.assertTrue(call_log)
        for c in call_log:
            self.assertIsNotNone(
                c["timeout"], f"requests.get called without timeout for {c['url']}"
            )
