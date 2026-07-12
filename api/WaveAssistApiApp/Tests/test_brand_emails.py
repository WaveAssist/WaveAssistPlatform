"""Tests for brand-aware transactional email + Knock removal.

These are pure-function tests (no DB), so they use SimpleTestCase. They cover:
  - get_from_email() resolves the right sender per product and falls back to WaveAssist,
  - the welcome templates render the correct brand and GitZoid follows its copy rules,
  - the credits template is brand-aware without regressing the WaveAssist output,
  - the Knock integration is fully removed from utils.
"""
import re

from django.test import SimpleTestCase

import WaveAssistApiApp.Utils.utils as utils


# GitZoid brand copy rules (mirrors GitZoidWebsite/CLAUDE.md): no "bot(s)", no "deploy",
# no em/en dashes, no semicolons, no exclamation marks — checked against visible text only.
GZ_FORBIDDEN = [r"\bbots?\b", "deploy", "—", "–", ";", "!"]


def _visible_text(html):
    html = re.sub(r"<style.*?</style>", "", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"&[a-z]+;", " ", text)


class GetFromEmailTests(SimpleTestCase):
    def test_waveassist(self):
        self.assertEqual(utils.get_from_email("waveassist"), "WaveAssist <updates@waveassist.ai>")

    def test_gitzoid(self):
        self.assertEqual(utils.get_from_email("gitzoid"), "GitZoid <updates@gitzoid.com>")

    def test_unknown_falls_back_to_waveassist(self):
        # A bad/absent product must never yield an unverified From that would bounce.
        for bad in ("bogus", "", None):
            self.assertEqual(utils.get_from_email(bad), "WaveAssist <updates@waveassist.ai>")

    def test_default(self):
        self.assertEqual(utils.get_from_email(), "WaveAssist <updates@waveassist.ai>")


class WelcomeTemplateTests(SimpleTestCase):
    def test_waveassist_content(self):
        html = utils.get_email_template_welcome("waveassist")
        self.assertIn("app.waveassist.io", html)             # dashboard is .io
        self.assertIn('href="https://waveassist.ai"', html)  # brand/footer is .ai
        self.assertNotIn("Any MCP host", html)
        self.assertNotIn("—", html)                     # no em dash
        self.assertNotIn("&mdash;", html)

    def test_gitzoid_content(self):
        html = utils.get_email_template_welcome("gitzoid")
        self.assertIn("app.gitzoid.com", html)
        self.assertIn("Connect your repos", html)
        self.assertNotIn("Try GitZoid", html)                # onboarding, not acquisition
        self.assertIn("The product manager for your", html)  # leads with positioning
        self.assertNotIn("GitZoid is on watch", html)
        self.assertIn("Built on the WaveAssist engine", html)  # the one sanctioned WA mention

    def test_gitzoid_copy_rules(self):
        text = _visible_text(utils.get_email_template_welcome("gitzoid"))
        for pat in GZ_FORBIDDEN:
            self.assertIsNone(re.search(pat, text, re.I), f"GitZoid copy rule violated: {pat}")

    def test_unknown_product_falls_back_to_waveassist(self):
        self.assertEqual(
            utils.get_email_template_welcome("bogus"),
            utils.get_email_template_welcome("waveassist"),
        )


class CreditsExpiredTemplateTests(SimpleTestCase):
    """WaveAssist pay-as-you-go 'credits ran out, add credits' email."""

    def test_copy_and_cta(self):
        html = utils.get_email_template_credits_expired()
        self.assertIn("your assistants are paused", html)   # generic, no specific assistant name
        self.assertIn("Add credits", html)                  # top-up CTA, not a plan upgrade
        self.assertIn("app.waveassist.io", html)
        self.assertIn(">/</span>waveassist</span>", html)   # wordmark lockup
        self.assertIn("Pay as you go", html)
        self.assertNotIn("Runs resume the moment you top up", html)   # meta trimmed
        self.assertNotIn("Upgrade to", html)                # WaveAssist is pay-as-you-go, no plans
        self.assertNotIn("—", html)


class TrialEndedTemplateTests(SimpleTestCase):
    """GitZoid 'trial ended, upgrade to Pro' email."""

    def test_copy_and_cta(self):
        html = utils.get_email_template_trial_ended()
        self.assertIn("trial has ended", html)
        self.assertIn("Upgrade to Pro", html)
        self.assertIn("app.gitzoid.com", html)
        self.assertIn(">/</span>gitzoid</span>", html)      # wordmark lockup
        self.assertIn("Built on the WaveAssist engine", html)

    def test_gitzoid_copy_rules(self):
        text = _visible_text(utils.get_email_template_trial_ended())
        for pat in GZ_FORBIDDEN:
            self.assertIsNone(re.search(pat, text, re.I), f"GitZoid copy rule violated: {pat}")


class KnockRemovedTests(SimpleTestCase):
    def test_knock_symbols_gone(self):
        self.assertFalse(hasattr(utils, "run_knock_workflow"))
        self.assertFalse(hasattr(utils, "knock_client"))

    def test_send_welcome_email_present(self):
        self.assertTrue(callable(getattr(utils, "send_welcome_email", None)))
