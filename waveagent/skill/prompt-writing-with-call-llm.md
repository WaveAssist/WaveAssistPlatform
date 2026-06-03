---
name: prompt-writing-with-call-llm
description: How to write prompts for waveassist.call_llm — the signature, exactly what Pydantic auto-injects into the prompt (and what it doesn't), the XML prompt anatomy, and dos and don'ts.
type: reference
---

# Prompt writing with `waveassist.call_llm`

This skill is the contract between you and `call_llm`. It answers
three questions:

1. What does `call_llm` do with my prompt before sending?
2. What does Pydantic auto-inject — so I don't restate it?
3. How do I structure the prompt so the model actually produces what
   I want?

## Provider note — OpenRouter (current)

`call_llm` currently routes through **OpenRouter**, so model names
follow OpenRouter's `provider/model` format:

| `model` value | Provider routed |
|---|---|
| `anthropic/claude-sonnet-4.6` | Anthropic Claude Sonnet 4.6 |
| `anthropic/claude-opus-4-7` | Anthropic Claude Opus 4.7 |
| `openai/gpt-5-mini` | OpenAI GPT-5 Mini |
| `google/gemini-2.5-flash` | Google Gemini 2.5 Flash |

This is implementation-specific and may change — if the provider layer
moves, model strings move with it. Always read the current default from
`fetch_data("model_name", default=DEFAULT_MODEL)` rather than
hardcoding.

A dev-only escape hatch exists: setting `LLM_PROVIDER=claude_cli` in
the environment routes calls through the local Claude CLI (Claude Max
subscription, no API credits used). This is for local testing; the
same prompts and response models work unchanged.

## The signature

```python
result: T = waveassist.call_llm(
    model="anthropic/claude-sonnet-4.6",
    prompt=prompt_text,
    response_model=MyPydanticModel,
    max_tokens=3000,
    temperature=0.2,
    should_retry=True,
    extra_body={"web_search_options": {"search_context_size": "medium"}},  # optional
)
```

**Always:**
- `model` from `fetch_data("model_name", default=DEFAULT_MODEL)` — let
  the user choose.
- `response_model` must be a Pydantic `BaseModel`. Don't parse JSON
  yourself; the SDK does it (leniently — missing optional fields
  become `None`, unknown fields are dropped).
- `max_tokens` generous for the expected output. Running out of tokens
  mid-JSON is an expensive failure.
- `temperature=0.2` for deterministic structure, higher only when you
  *want* variation (rare in pipelines).
- `should_retry=True` on format-sensitive calls — the SDK retries once
  on JSON/format errors. Free insurance.

**Not so often:**
- `extra_body={"web_search_options": {...}}` for models that support
  built-in web search. Only a few models do; check before relying on
  it.

**Returns an instance of `response_model`**, already validated. Call
`.model_dump()` to get a plain dict to store:

```python
result_dict = result.model_dump()
waveassist.store_data("my_key", result_dict, data_type="json")
```

Use `.model_dump(by_alias=True)` if any field uses `Field(alias=...)`
and downstream consumers expect the aliased key.

## What `call_llm` sends to the model — exactly

Internally, your prompt is wrapped like this (see
`waveassist/utils.py: create_json_prompt`):

```
{your prompt text, verbatim}

    Respond with a JSON object following this structure:
    {JSON template generated from response_model}

    Return ONLY the JSON object, no explanations or other text. Return JSON now:
```

Two important consequences:

- **The closer is always appended.** You don't need to say "return
  JSON" at the end of your prompt. It's added for you.
- **The JSON template is generated from the Pydantic model.** You
  don't need to show the shape yourself either.

## What Pydantic auto-injects — the precise contract

`generate_json_template_dict` walks your `response_model` and emits a
JSON template. Here's what it DOES and DOESN'T include.

### ✅ Included (model sees this)

| Pydantic construct | Injected as |
|---|---|
| Field names | Object keys: `{"status": ..., "items": ...}` |
| Basic types (`str`, `int`, `float`, `bool`) | `"<str>"`, `"<int>"`, etc. |
| `Literal["a", "b", "c"]` | `"'a' \| 'b' \| 'c'"` — enum constraints ARE visible |
| `Optional[X]` / `X \| None` | Unwrapped to just `"<X>"` |
| `list[str]` | `["<str>"]` |
| `list[SomeModel]` | `[{...nested template...}]` |
| `dict[K, V]` | `"<dict[K, V]>"` |
| Nested `BaseModel` | Expanded recursively as a nested object |
| `Field(description="...")` | Appended to the type: `"<str> your description"` |

### ❌ NOT included (model does NOT see this)

| Pydantic construct | Why you care |
|---|---|
| `Field(default=...)` values | If a default is semantically meaningful to the model, restate it in `description`. |
| `Field(min_length=...)`, `max_length=...`, `ge=`, `le=` | Validation-only; NOT communicated. If you need the model to respect a range, say so in `description`. |
| `Field(alias="foo")` | Template uses the *field name*, not the alias. If the output key differs from the field name, either rename the field or state the alias in `description`. |
| Class docstrings | Ignored. Put model-level guidance in the prompt body, not the docstring. |
| Custom validators (`@field_validator`) | Run AFTER parsing — the model won't know and will fail parses that don't meet them. Prefer descriptive prompt rules over validators for LLM output. |
| Required vs optional | The template doesn't mark required fields; it just shows the type. If a field MUST be filled, say so in `description`. |

### Practical implication

Always put useful field-level guidance in `Field(description="...")`.
It's the only per-field hint the model actually sees.

```python
# GOOD — description will appear in the template
action_slug: Optional[str] = Field(
    default=None,
    description="Required when no_fit=False. Must be a slug from the candidates list above.",
)

# WEAK — model won't know this is required-when-X
action_slug: Optional[str] = None
```

## Prompt anatomy

Anthropic's guidance ([XML tags docs][xml-docs]) is clear: **use XML
tags to structure multi-section prompts**. They improve parse
accuracy when mixing instructions, context, examples, and variable
input. Markdown headers also work, but XML is more precise because
the tag boundary is unambiguous. Be consistent within a prompt.

[xml-docs]: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags

The anatomy below is the shape to copy — don't invent a new one
without a reason.

```
<role>
One sentence: what the model IS in this call. "You are the X for Y."
</role>

<context>
2-5 sentences: what the product/system is, what this step does, what
happens next. The model generalises MUCH better when it knows WHY the
task exists. Don't skip this.
</context>

<task>
One sentence or a short paragraph: what to produce. If the output has
edge-case behavior, name it here (e.g. "If ambiguous, return
status=clarify instead.").
</task>

<rules>
### Section A
- Bullet rule.
- Bullet rule (with brief why if non-obvious).

### Section B (optional sub-rules tables, do/don't)
</rules>

<examples>
<example>
Input: ...
→ Output: ...
</example>
<example>
Input: ...
→ Output: ...
</example>
...3-6 diverse examples...
</examples>

<{data_block_1}>
...the actual input: catalog, candidates, history, whatever...
</{data_block_1}>

<{data_block_2}>
...more input...
</{data_block_2}>

<user_prompt>
{the user's literal request}
</user_prompt>

Return a {ResponseModelName}.
```

Why each piece:

- **`<role>`** — anchors voice and behaviour without wasting tokens.
  Anthropic's docs flag role as high-leverage.
- **`<context>`** — the model has no idea what your product is.
  Telling it "we build X; your output feeds step Y" measurably
  improves sensible defaulting on ambiguous inputs.
- **`<task>`** — one-sentence what. Pairs with `<rules>` for how.
- **`<rules>`** — this is where the real work happens. Explain
  constraints. Every rule should have a *why* if it's not obvious —
  the model generalises from reasons, not commandments.
- **`<examples>`** — 3-6 diverse few-shots beat long prescriptive
  rule tables. If you're writing a sixth bullet to a rule, try
  writing an example instead. Wrap in `<example>` inside `<examples>`
  — the model is trained to recognise these tags.
- **Data blocks** — all variable input gets its own tag. Don't splice
  user input into a sentence — wrap it.
- **Closer: `Return a XYZResult.`** — restates the schema name as a
  final cue. Cheap, grounds the model.

### Long-context rule

If any data block is bigger than a few thousand tokens (a catalog, a
document dump), put it **at the top**, above `<task>` and `<rules>`.
Queries at the end can improve response quality by up to 30% on
long-context prompts. For short prompts the "context at top, query
at bottom" shape is fine.

## General principles — DO

Distilled from Anthropic's [prompting best practices][bp] and proven
on our own nodes.

[bp]: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

- **Be clear and direct.** Imagine a new colleague reading your prompt.
  If they'd be confused, the model will be too. Specify format, scope,
  and success criteria.
- **Explain WHY, not just WHAT.** "Never use ellipses because our TTS
  engine can't pronounce them" generalises. "Never use ellipses"
  doesn't.
- **Use positive instructions.** "Write in flowing prose" beats
  "Don't use bullet points." The model steers better toward a target
  than away from one.
- **Examples beat abstract rules.** 3-5 diverse examples outperform a
  long bullet list 90% of the time. Wrap in `<example>` tags.
- **Match prompt style to desired output.** If you don't want markdown
  in the response, don't use markdown in your prompt.
- **Include edge cases in examples.** At least one "empty", "clarify",
  or "none-of-the-above" example steers the model toward handling
  them correctly instead of forcing a fit.

## What NOT to do — DON'T

Common mistakes. Every one of these has burned us or the prompt-
engineering docs flag it specifically.

- **Don't tell the model to "return JSON" or "respond in JSON
  format."** `call_llm` appends that instruction for you. Restating
  it wastes tokens and sometimes confuses the model into describing
  the JSON instead of producing it.
- **Don't restate the Pydantic schema in your prompt.** The SDK
  injects a typed template after your prompt. If you also write
  "return `{status: ..., items: [...]}`" you'll diverge from the
  injected template the moment someone edits the schema.
- **Don't put load-bearing guidance in class docstrings,
  validators, constraints, or default values.** None of those reach
  the model (see the "NOT included" table above). Put it in
  `Field(description=...)` or the prompt body.
- **Don't use negative framing when positive works.** "Do not
  hallucinate action slugs" is weaker than "Pick `picker_action_slug`
  verbatim from the candidate list below. If none fit, return
  `no_fit=true`."
- **Don't stack prescriptive rules when a few examples would
  communicate the same thing.** Three diverse `<example>` blocks
  routinely outperform a 10-bullet rule list.
- **Don't mix XML and markdown headers inconsistently within one
  prompt.** Pick one structural idiom and use it everywhere — mixing
  them makes parsing ambiguous.
- **Don't splice user input directly into sentences.**
  `"The user said '{user_input}'. Do X."` is prompt-injection-prone
  and harder for the model to parse. Always wrap variable input in
  its own XML tag.
- **Don't rely on `temperature` for variety in structured-output
  pipelines.** It destabilises JSON format too. If you need variety,
  ask for N alternatives in the schema (`options: list[Option]`)
  instead.
- **Don't ship without at least one edge-case example.** Without
  one, the model fabricates when input doesn't fit. At minimum
  include an "I don't have enough information" / "empty" / "clarify"
  example.

## Prompt regression testing (optional but high-value)

When a prompt has rules earned through painful iteration
("operation sense-check", "never pick the same resource type",
specific edge-case examples), encode them as test assertions so a
refactor doesn't accidentally delete them:

```python
def test_prompt_keeps_operation_sense_check_rule(self):
    prompt = build_pass1_prompt(...)
    assert "operation sense-check" in prompt.lower()
    assert "github: list open PRs" in prompt
```

Cheap to write, catches real regressions.

## Cost discipline

Rough ballpark with Claude Sonnet 4.6 (order of magnitude):

| Pattern | Input tokens | Cost per call (USD) |
|---|---|---|
| Short classifier (brief prompt, small model) | ~1K | ~$0.003 |
| Typical structured-output node | 3-5K | ~$0.01-0.02 |
| Node with full catalog context | 8-10K | ~$0.04 |
| Big document analysis | 20K+ | ~$0.08+ |

`max_tokens` on the OUTPUT doesn't cost anything unused. Set it
generously — truncating mid-JSON costs more than the savings.

## Worked example — end-to-end

A classifier that categorises a user prompt into `{question, request,
feedback}` with a confidence:

```python
from typing import Literal, Optional
import waveassist
from pydantic import BaseModel, Field

DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"
waveassist.init()


class Classification(BaseModel):
    status: Literal["ready", "clarify"]
    category: Optional[Literal["question", "request", "feedback"]] = Field(
        default=None,
        description="Required when status=ready. Pick the closest single fit.",
    )
    confidence: Optional[float] = Field(
        default=None,
        description="Required when status=ready. 0.0-1.0. Below 0.4 means use status=clarify instead.",
    )
    clarify_question: Optional[str] = Field(
        default=None,
        description="Required when status=clarify. One short sentence.",
    )


def build_prompt(user_prompt: str) -> str:
    return f"""<role>
You are a prompt classifier. Route the user's message to one of three
handlers.
</role>

<context>
Incoming messages land in an inbox and must be routed. Questions go
to FAQ; requests to ops; feedback to product. Routing is hard to
undo, so prefer clarify over a low-confidence guess.
</context>

<task>
Classify the user's message into exactly one category, with a
confidence. If the message is too ambiguous to classify above 0.4
confidence, return status=clarify with a one-sentence question.
</task>

<rules>
- Pick exactly one category — no multi-label.
- "question" = asking how/what/why; answer-expected.
- "request" = asking for something to be done.
- "feedback" = volunteering an opinion / reporting an issue.
- If multiple categories fit equally well, clarify.
</rules>

<examples>
<example>
Input: "how do I reset my password?"
→ status=ready, category=question, confidence=0.95
</example>
<example>
Input: "please delete my account"
→ status=ready, category=request, confidence=0.90
</example>
<example>
Input: "the dashboard feels slow lately"
→ status=ready, category=feedback, confidence=0.85
</example>
<example>
Input: "thanks"
→ status=clarify, clarify_question="Happy to help — what can I do for you?"
</example>
</examples>

<user_prompt>
{user_prompt}
</user_prompt>

Return a Classification.
"""


# orchestration
user_prompt = waveassist.fetch_data("user_prompt", default="")
model = waveassist.fetch_data("model_name", default=DEFAULT_MODEL)

if not user_prompt.strip():
    out = Classification(status="clarify", clarify_question="What would you like to do?").model_dump()
else:
    try:
        result = waveassist.call_llm(
            model=model,
            prompt=build_prompt(user_prompt),
            response_model=Classification,
            max_tokens=500,
            temperature=0.2,
            should_retry=True,
        )
        out = result.model_dump()
    except Exception as exc:
        print(f"LLM failed: {exc}")
        out = Classification(status="clarify", clarify_question="Please rephrase your message.").model_dump()

waveassist.store_data("classification", out, data_type="json")
print(f"Classifier: stored (status={out['status']}, category={out.get('category')}).")
```

Every piece is intentional: role, context, task, rules, 4 diverse
examples (including a clarify case), the user prompt in its own tag,
a closer naming the schema. `Field(description=...)` communicates
"required when X" rules that Pydantic itself can't express to the
model.

## Checklist

Before shipping a `call_llm`-using node:

- [ ] `Field(description="...")` on every field the model fills. Non-obvious rules (required-when, value ranges, format) are stated there.
- [ ] `Literal[...]` used for enum fields (status, category, type) — they're visible to the model.
- [ ] Prompt has `<role>`, `<context>`, `<task>` at minimum.
- [ ] 3-6 diverse `<example>` entries in `<examples>`, including at least one edge case (empty, clarify, none-of-the-above).
- [ ] Every variable input is wrapped in its own XML tag.
- [ ] Prompt ends with `Return a {ModelName}.` — no JSON instructions.
- [ ] `should_retry=True` unless the call is extremely expensive.
- [ ] `max_tokens` generous enough for the output in the worst case.
- [ ] Didn't splice user input into a sentence; no "return JSON" line; no schema restated in prompt body.

## See also

- `waveassist-sdk.md` — `call_llm` sits on top of `init`; node
  structure rules.
- `waveassist-integrations.md` — how Composio data (catalogs,
  candidates, action descriptions) tends to feed a prompt.
