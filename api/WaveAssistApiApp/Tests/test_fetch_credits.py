from django.test import SimpleTestCase
from unittest.mock import patch, MagicMock

from WaveAssistApiApp.Utils import utils


def _resp(data):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": data}
    return resp


class FetchCreditsFromOpenRouterTests(SimpleTestCase):
    """Regression coverage for uncapped OpenRouter keys (limit/limit_remaining == null)."""

    def test_capped_key_returns_floats(self):
        data = {"limit": 10, "usage": 3.5, "limit_remaining": 6.5}
        with patch.object(utils.requests, "get", return_value=_resp(data)):
            result = utils.fetch_credits_from_openrouter("sk-or-test")
        self.assertEqual(result, {"limit": 10.0, "usage": 3.5, "limit_remaining": 6.5})

    def test_uncapped_key_returns_none_instead_of_crashing(self):
        # A valid key with NO spending limit set: OpenRouter returns 200 with null limit /
        # limit_remaining. Previously this raised "float() argument must be ... not 'NoneType'".
        data = {"limit": None, "usage": 55.07, "limit_remaining": None}
        with patch.object(utils.requests, "get", return_value=_resp(data)):
            result = utils.fetch_credits_from_openrouter("sk-or-test")
        self.assertIsNone(result["limit"])
        self.assertIsNone(result["limit_remaining"])
        self.assertEqual(result["usage"], 55.07)

    def test_zero_remaining_retries_once_but_none_does_not(self):
        # limit_remaining == 0 retries once (stale-0 guard); None must NOT trigger a retry.
        zero = _resp({"limit": 5, "usage": 5, "limit_remaining": 0})
        with patch.object(utils.requests, "get", return_value=zero) as g:
            utils.fetch_credits_from_openrouter("sk-or-test")
        self.assertEqual(g.call_count, 2)

        uncapped = _resp({"limit": None, "usage": 1, "limit_remaining": None})
        with patch.object(utils.requests, "get", return_value=uncapped) as g:
            utils.fetch_credits_from_openrouter("sk-or-test")
        self.assertEqual(g.call_count, 1)
