# Assistant Integrations — wiring status

This is the source-of-truth for **which integrations actually work** vs. which are
listed in the UI but not yet wired. The catalog in `providerConfigs.ts` lists ~26
providers, but a provider only functions if its backend is set up.

## How the integration system works (native, NOT Composio)

Two distinct auth styles:

- **OAuth providers** — `authType: "oauth"` in `providerConfigs.ts` (and ClickUp via the
  custom `ClickUpInput.tsx`). Connecting hits `providers/initiate/` →
  `WaveAssistApi/.../providers.py`, which looks up a row in the **MySQL
  `WaveAssist_Provider`** table by `name`. **No row (or placeholder creds) = the
  "Connect" button bounces to an invalid OAuth screen.** Tokens are stored in the
  Mongo KV store as `{provider}_access_token` / `_refresh_token`.
- **API-key providers** — `authType: "api_key"`. The user pastes a token; it's saved
  directly via `setDataForKeyApi` as `{provider}_access_token`. These need **no**
  `WaveAssist_Provider` row.

> This is the WaveAgent / "integrations-without-composio" path. Composio is a separate,
> deprecated system (see bottom).

## Status (verified against `WaveAssist_Provider`, June 2026)

### ✅ Live — real OAuth credentials, production redirect
| Provider | Notes |
|----------|-------|
| `clickup` | Custom `ClickUpInput.tsx`. `resource_configs` uses `items_key: "teams"`. |
| `hubspot` | `client_secret_post` + `code` fetch (correct for HubSpot). |
| `github`  | |
| `linear`  | GraphQL `resource_configs`. |

### ⚠️ Sample / dev only
| Provider | Issue |
|----------|-------|
| `slack` | Real client_id, but `redirect_uri` is a dead `ngrok-free.app` URL. Set a prod redirect before relying on it. |

### ❌ Placeholder — never set up (`client_id`/`secret` = `PLACEHOLDER…`)
`confluence`, `discord`, `figma`, `gmail`, `google_analytics`, `google_calendar`,
`google_drive`, `intercom`, `jira`, `notion`, `outlook`, `pipedrive`, `salesforce`,
`typeform`. These appear in the UI but **do not work** until real OAuth app
credentials are added to the DB row.

### API-key providers (no OAuth row needed)
`zendesk`, `airtable`, `postgresql`, `shopify`, `stripe`, `mixpanel`, `fireflies`,
`whatsapp` — function only insofar as the consuming node code reads the stored token.

## Wiring a new OAuth provider
1. Register an OAuth app with the provider; set redirect URI to
   `https://api.waveassist.io/provider/callback/`.
2. Insert/activate a `WaveAssist_Provider` row with real `client_id`, `client_secret`,
   `auth_url`, `token_url`, `refresh_url`, `default_scopes`, and a `resource_configs`
   using **`items_key`** (the key `providers.py` reads) to point at the list field in
   the API response.
3. Add/confirm the entry in `providerConfigs.ts` (or a custom input component).

## Composio (deprecated, being removed)
A separate backend subsystem (`integrations_view.py`, `/api/v1/tools/*`, SDK
`call_tool()`, `Assistants/WaveMaker/`) used Composio for tool execution. WaveMaker is
superseded by WaveAgent and no live agent calls `call_tool`, so this path is being torn
out. It is **not** related to the native integrations above.
