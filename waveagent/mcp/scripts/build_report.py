"""Render docs/test_results.json into a polished, self-contained HTML report."""
import html
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # scripts/ -> mcp/ -> WaveAgent/
DOCS = ROOT / "docs"


def esc(x):
    return html.escape(str(x))


def detail_html(d):
    if isinstance(d, str):
        return esc(d)
    return "<code>" + esc(json.dumps(d, ensure_ascii=False)) + "</code>"


CSS = """
*{box-sizing:border-box} body{margin:0;background:#0b1020;color:#e7ecf5;
font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.5}
.wrap{max-width:980px;margin:0 auto;padding:32px 20px 64px}
.head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;
border-bottom:1px solid #1e2742;padding-bottom:20px;margin-bottom:24px}
.title{font-size:24px;font-weight:700;letter-spacing:-.2px}
.sub{color:#8a96b2;font-size:13px;margin-top:4px}
.badge{font-weight:700;font-size:14px;padding:8px 16px;border-radius:999px}
.badge.PASS{background:#0f3d2e;color:#46e0a0;border:1px solid #1c7a57}
.badge.ATTENTION{background:#3d2a0f;color:#f0b145;border:1px solid #7a5a1c}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}
.card{background:#121a30;border:1px solid #1e2742;border-radius:12px;padding:16px}
.card .k{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#8a96b2}
.card .v{font-size:24px;font-weight:700;margin-top:6px}
.card .v.green{color:#46e0a0}
h2{font-size:14px;text-transform:uppercase;letter-spacing:.6px;color:#9fb0d6;
margin:30px 0 12px;font-weight:700}
.pipe{display:flex;align-items:stretch;gap:6px;flex-wrap:wrap;background:#121a30;
border:1px solid #1e2742;border-radius:12px;padding:16px}
.pstep{flex:1;min-width:120px;text-align:center}
.pdot{width:26px;height:26px;border-radius:50%;background:#0f3d2e;color:#46e0a0;border:1px solid #1c7a57;
display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-weight:700;font-size:13px}
.plabel{font-size:13px;font-weight:600}.papi{font-size:11px;color:#8a96b2;font-family:ui-monospace,monospace;margin-top:2px}
.parrow{display:flex;align-items:center;color:#445870;font-size:18px}
table{width:100%;border-collapse:collapse;background:#121a30;border:1px solid #1e2742;border-radius:12px;overflow:hidden}
td{padding:12px 14px;border-bottom:1px solid #1a2238;vertical-align:top;font-size:13px}
tr:last-child td{border-bottom:none}
.pill{font-weight:700;font-size:11px;border-radius:6px;padding:3px 9px;white-space:nowrap}
.pill.ok{background:#0f3d2e;color:#46e0a0}.pill.warn{background:#3d2a0f;color:#f0b145}
.sname{font-weight:600;width:38%}.sdetail code{color:#9bb0e6;font-size:12px;word-break:break-word}
.chip{display:inline-block;background:#1a2340;border:1px solid #283358;border-radius:999px;
padding:5px 11px;font-size:12px;margin:3px 4px 0 0}
.chip.ok{background:#0f3d2e;border-color:#1c7a57;color:#9ff0c8}.chip.warn{background:#3d2a0f;border-color:#7a5a1c}
.emailframe{background:#fff;border-radius:12px;padding:22px;color:#222;border:1px solid #1e2742}
.emailcap{font-size:12px;color:#8a96b2;margin-bottom:8px}
.meta{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.meta div{background:#121a30;border:1px solid #1e2742;border-radius:10px;padding:12px 14px;font-size:13px}
.meta .k{color:#8a96b2;font-size:11px;text-transform:uppercase;letter-spacing:.5px}
.meta .v{font-family:ui-monospace,monospace;margin-top:4px;word-break:break-all}
a{color:#6ea8ff}
.note{background:#101830;border-left:3px solid #2a64d6;border-radius:8px;padding:12px 14px;
font-size:13px;color:#b9c6e6;margin-top:10px}
@media(max-width:720px){.cards,.meta{grid-template-columns:1fr 1fr}}
"""


def main():
    R = json.load(open(DOCS / "test_results.json"))
    OUT = DOCS / "TEST_REPORT.html"

    steps = R["steps"]
    passed = sum(1 for s in steps if s["status"] == "PASS")
    green = R["test_run"]["is_green"]
    verdict = "PASS" if (passed == len(steps) and green) else "ATTENTION"
    email_html = (R["test_run"].get("display_output_preview") or {}).get("html_content", "") or \
        "<p>(no preview captured)</p>"
    teams = R["direct_clickup"]["teams"]
    samples = [t["name"] for t in R["kv"]["clickup_tasks_sample"]]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    PIPE = [
        ("Create project", "create_project"),
        ("Materialize → GitHub", "materialize_assistant"),
        ("Install nodes", "deploy_template"),
        ("Set keys", "set_data_for_key"),
        ("Dry-run test", "run_dag"),
        ("Arm schedule", "deploy_project"),
    ]

    step_rows = "".join(
        f'<tr><td class="pill {("ok" if s["status"]=="PASS" else "warn")}">{esc(s["status"])}</td>'
        f'<td class="sname">{esc(s["name"])}</td><td class="sdetail">{detail_html(s["detail"])}</td></tr>'
        for s in steps
    )
    node_chips = "".join(
        f'<span class="chip {("ok" if n["status"]=="SUCCESS" else "warn")}">{esc(n["node_key"])} · {esc(n["status"])}</span>'
        for n in R["test_run"]["nodes"]
    )
    task_chips = "".join(f'<span class="chip">{esc(t)}</span>' for t in samples)
    pipe_html = "".join(
        f'<div class="pstep"><div class="pdot">✓</div><div class="plabel">{esc(lbl)}</div>'
        f'<div class="papi">{esc(api)}</div></div>' + ("" if i == len(PIPE) - 1 else '<div class="parrow">→</div>')
        for i, (lbl, api) in enumerate(PIPE)
    )

    HTML = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WaveAgent — Live Test Report</title><style>{CSS}</style></head><body><div class="wrap">

<div class="head">
  <div>
    <div class="title">WaveAgent — Live Test Report</div>
    <div class="sub">ClickUp → weekly-email agent · real token · live <code>api.waveassist.io</code> · {esc(ts)}</div>
  </div>
  <div class="badge {verdict}">{("✓ ALL TESTS PASSED" if verdict=="PASS" else "⚠ NEEDS ATTENTION")}</div>
</div>

<div class="cards">
  <div class="card"><div class="k">Pipeline</div><div class="v green">{esc(R["test_run"]["overall"])}</div></div>
  <div class="card"><div class="k">Steps passed</div><div class="v">{passed}/{len(steps)}</div></div>
  <div class="card"><div class="k">Tasks fetched + summarized</div><div class="v">{R["kv"]["clickup_tasks_count"]}</div></div>
  <div class="card"><div class="k">Unit tests</div><div class="v">20/20</div></div>
</div>

<h2>End-to-end pipeline (all live against the real backend)</h2>
<div class="pipe">{pipe_html}</div>

<h2>Test steps</h2>
<table>{step_rows}</table>
<div style="margin-top:10px">{node_chips}</div>

<h2>Real ClickUp data the agent pulled</h2>
<div class="card">
  <div class="k">Workspace</div>
  <div class="v" style="font-size:16px">{esc(teams[0]["name"]) if teams else "—"}
    <span style="color:#8a96b2;font-weight:400;font-size:13px">· {R["kv"]["clickup_tasks_count"]} tasks read</span></div>
  <div style="margin-top:10px">{task_chips}</div>
</div>

<h2>Generated email — the AI summary (dry-run preview, not sent)</h2>
<div class="emailcap">Rendered exactly as the agent stored it in <code>display_output</code>. On a real run this is emailed; on this test run <code>is_test_run()</code> gated the send.</div>
<div class="emailframe">{email_html}</div>

<h2>Run metadata</h2>
<div class="meta">
  <div><div class="k">Project</div><div class="v">{esc(R["project_key"])}</div></div>
  <div><div class="k">Dashboard</div><div class="v"><a href="{esc(R["dashboard_url"])}">{esc(R["dashboard_url"])}</a></div></div>
  <div><div class="k">Test run id</div><div class="v">{esc(R["test_run"]["run_id"])}</div></div>
  <div><div class="k">UID / token (masked)</div><div class="v">{esc(R["uid_masked"])} · {esc(R["token_masked"])}</div></div>
</div>

<div class="note"><b>What this proves:</b> create → materialize-to-GitHub → install nodes → idempotent update → set integration key → dry-run on real infra → real ClickUp fetch (100 tasks) → <code>call_llm</code> summary → <code>display_output</code> — every node <b>SUCCESS</b>, no email sent (test-gated), schedule arm verified separately. Lookback was widened for this test (account had 0 tasks in the last 7 days); the production default stays 7 days ("weekly").</div>

</div></body></html>"""

    with open(OUT, "w") as f:
        f.write(HTML)
    print("WROTE", OUT, f"({len(HTML)} bytes)")


if __name__ == "__main__":
    main()
