"""
EmailSummary — turn the collected ClickUp tasks into a short weekly summary and
email it. Uses call_llm for the natural-language summary (server-side key, no user
LLM key). Guarded by is_test_run() so a dry run never sends a real email.

Runtime contract (see fetch_clickup.py): the file is wrapped into def run_task();
do NOT use exit()/SystemExit/top-level return — use if/else and fall through.
"""
import html

import waveassist
from pydantic import BaseModel, Field

waveassist.init()

DEFAULT_MODEL = "anthropic/claude-haiku-4.5"


class WeeklySummary(BaseModel):
    # Plain-text fields only. ClickUp task names are untrusted user input that flows
    # into the prompt, so we never let the model emit HTML — we escape + build it.
    headline: str = Field(description="One short, friendly headline for the week. Plain text, no HTML.")
    intro: str = Field(description="One plain-text sentence introducing the week. No HTML/markdown.")
    points: list[str] = Field(
        description="3-8 short plain-text bullet points summarizing the tasks. No HTML/markdown."
    )


def render_fallback(tasks: list) -> str:
    rows = "".join(
        f"<li style=\"margin-bottom:6px;\"><b>{html.escape(t.get('name', ''))}</b>"
        f" <span style=\"color:#888;\">[{html.escape(t.get('status', ''))}]</span>"
        f"{(' · ' + html.escape(t.get('workspace', ''))) if t.get('workspace') else ''}</li>"
        for t in tasks[:25]
    )
    return (f"<ul style=\"padding-left:18px;font-size:14px;\">"
            f"{rows or '<li>No tasks were updated this week.</li>'}</ul>")


def render_points(intro: str, points: list) -> str:
    """Build the summary body from the model's PLAIN-TEXT fields, escaping everything."""
    intro_html = f"<p style=\"font-size:14px;\">{html.escape(intro)}</p>" if intro else ""
    items = "".join(
        f"<li style=\"margin-bottom:6px;\">{html.escape(str(p))}</li>" for p in (points or []) if p
    )
    list_html = f"<ul style=\"padding-left:18px;font-size:14px;\">{items}</ul>" if items else ""
    return intro_html + list_html


def build_email_html(headline: str, body_html: str, count: int) -> str:
    return (
        "<div style=\"font-family:Inter,-apple-system,sans-serif;max-width:640px;\">"
        f"<h2 style=\"font-size:20px;margin:0 0 4px;\">{html.escape(headline)}</h2>"
        f"<p style=\"font-size:13px;color:#888;margin:0 0 16px;\">"
        f"{count} task(s) updated recently</p>"
        f"{body_html}"
        "<p style=\"font-size:12px;color:#aaa;margin-top:20px;\">"
        "Sent by your WaveAssist ClickUp Weekly agent.</p></div>"
    )


def build_prompt(tasks: list) -> str:
    lines = "\n".join(
        f"- {t.get('name', '')} [{t.get('status', '')}] ({t.get('workspace', '')})"
        for t in tasks[:60]
    )
    return f"""<role>
You write a concise, friendly weekly status summary from a list of ClickUp tasks.
</role>
<tasks>
{lines}
</tasks>
Write a one-line headline, a one-sentence intro, and 3-8 short bullet points
summarizing the most important items. PLAIN TEXT ONLY — no HTML, no markdown.
Group by status or workspace if helpful. Keep it concise.
"""


def summarize(tasks: list):
    """Return (headline, body_html). Uses the LLM when there are tasks, else a fallback."""
    headline = "Your weekly ClickUp summary"
    body_html = render_fallback(tasks)
    if tasks:
        model = waveassist.fetch_data("model_name", default=DEFAULT_MODEL)
        try:
            result = waveassist.call_llm(
                model=model,
                prompt=build_prompt(tasks),
                response_model=WeeklySummary,
                max_tokens=800,
                temperature=0.3,
                should_retry=True,
            )
            headline = result.headline or headline
            built = render_points(result.intro, result.points)
            if built:
                body_html = built
        except Exception as exc:  # noqa: BLE001
            print(f"Email: LLM summary failed, using fallback. ({exc})")
    return headline, body_html


# orchestration (flat — no early exit)
print("Email: building weekly summary...")
error = waveassist.fetch_data("clickup_error", default="")
tasks = waveassist.fetch_data("clickup_tasks", default=[])

if error and error != "":
    print(f"Email: upstream error, not sending. ({error})")
    display_output = {
        "html_content": (
            "<div style=\"font-family:Inter,sans-serif;padding:16px;\">"
            "<h2 style=\"font-size:18px;\">Weekly ClickUp summary unavailable</h2>"
            f"<p style=\"font-size:14px;color:#444;\">{html.escape(str(error))}</p></div>"
        ),
        "type": "error",
    }
else:
    count = len(tasks)
    headline, body_html = summarize(tasks)
    email_html = build_email_html(headline, body_html, count)

    if waveassist.is_test_run():
        print("Email: test run — skipping real send, storing preview.")
        display_output = {
            "html_content": (
                "<div style=\"font-family:Inter,sans-serif;\">"
                "<p style=\"font-size:13px;color:#888;\">Preview (test run — email not sent):</p>"
                f"{email_html}</div>"
            ),
            "type": "preview",
        }
    else:
        try:
            waveassist.send_email(
                subject="Your weekly ClickUp summary",
                html_content=email_html,
                raise_on_failure=False,
            )
            print("Email: sent.")
        except Exception as exc:  # noqa: BLE001
            print(f"Email: send failed. ({exc})")
        display_output = {"html_content": email_html, "type": "success"}

waveassist.store_data("display_output", display_output, run_based=True, data_type="json")
print("Email: done.")
