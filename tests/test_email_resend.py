"""Checks for the Resend email transport; no network or production credentials."""
import ast
import types
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api"


class FakeRequests:
    def __init__(self, status_code=200, body=None):
        self.calls = []
        self.status_code = status_code
        self.body = body if body is not None else {"id": "re_test"}

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return types.SimpleNamespace(status_code=self.status_code, text=str(self.body), json=lambda: self.body)


def load_send(fake, key="key-main", gitzoid_key=""):
    tree = ast.parse((API / "WaveAssistApiApp/Utils/utils.py").read_text())
    function = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "send_email_resend"]
    ns = {"requests": fake, "RESEND_API_KEY": key, "RESEND_API_KEY_GITZOID": gitzoid_key,
          "RESEND_API_URL": "https://api.resend.com/emails"}
    exec(compile(ast.Module(body=function, type_ignores=[]), "utils", "exec"), ns)
    return ns["send_email_resend"]


def test_owner_only_send_builds_minimal_payload():
    fake = FakeRequests()
    assert load_send(fake)("A <a@x.io>", "b@y.io", "Hi", "<p>hi</p>") == "re_test"
    call = fake.calls[0]
    assert call["url"] == "https://api.resend.com/emails"
    assert call["headers"] == {"Authorization": "Bearer key-main"}
    assert call["json"] == {"from": "A <a@x.io>", "to": ["b@y.io"], "subject": "Hi", "html": "<p>hi</p>"}


def test_cc_bcc_and_attachments_are_passed_through():
    fake = FakeRequests()
    attachment = {"filename": "r.pdf", "content": "UEZE"}
    load_send(fake)("a@x.io", "b@y.io", "s", "h", cc=["c@y.io"], bcc=["d@y.io"], attachments=[attachment])
    body = fake.calls[0]["json"]
    assert body["cc"] == ["c@y.io"] and body["bcc"] == ["d@y.io"] and body["attachments"] == [attachment]


@pytest.mark.parametrize("product,gitzoid_key,expected", [
    ("gitzoid", "key-gz", "key-gz"),
    ("gitzoid", "", "key-main"),
    ("waveassist", "key-gz", "key-main"),
])
def test_key_is_chosen_per_brand(product, gitzoid_key, expected):
    fake = FakeRequests()
    load_send(fake, gitzoid_key=gitzoid_key)("a@x.io", "b@y.io", "s", "h", product=product)
    assert fake.calls[0]["headers"]["Authorization"] == "Bearer " + expected


def test_errors_raise_so_callers_fall_back():
    with pytest.raises(Exception, match="Resend error 403"):
        load_send(FakeRequests(status_code=403, body={"message": "domain not verified"}))("a@x.io", "b@y.io", "s", "h")
    with pytest.raises(Exception, match="RESEND_API_KEY is not set"):
        load_send(FakeRequests(), key="")("a@x.io", "b@y.io", "s", "h")


def test_every_send_path_uses_resend():
    sdk = (API / "WaveAssistApiApp/sdk_views.py").read_text()
    utils = (API / "WaveAssistApiApp/Utils/utils.py").read_text()
    assert "PostmarkClient" not in sdk and "PostmarkClient" not in utils
    assert sdk.count("utils.send_email_resend(") == 3
    assert "send_email_resend(from_email, to_email, subject, html_content, product=product_key)" in utils
