# Cloudflare images: Free-plan setup

Selected by the user on 2026-10-21 as the initial real image provider. Gemini stays
the text provider. Paid image APIs remain deferred. The Cloudflare adapter is
implemented and mock-tested; account credentials/live access have not been checked.
Image HTTP endpoints and UI are still a separate implementation increment.

## 1. Keep the account on Workers Free

Create/sign in to a [Cloudflare account](https://dash.cloudflare.com/) and check
the Workers plan is **Free**. Do not upgrade or enable paid AI Gateway billing.
Cloudflare currently includes 10,000 Neurons per day, shared across Workers AI
usage. Free-plan requests stop at the allocation limit; the allowance is not an
unlimited image count. Usage depends on model/settings and other account activity.
[Official pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/).

The app does not inspect your billing subscription. The confirmation setting below
is your acknowledgement, not a technical account-wide spending cap. If the account
is changed to Paid later, disable this configuration until we review the budget.
No app request upgrades plans or falls back to another provider.

## 2. Create an account-scoped Workers AI token

In the dashboard, open **Workers AI → Use REST API**. Copy the Account ID and
use **Create a Workers AI API Token**, limiting it to the intended account. Review
the template's Workers AI permissions rather than creating a global API key.
For custom tokens, the current guide specifies Workers AI Read and Edit.
[Official setup guide](https://developers.cloudflare.com/workers-ai/get-started/rest-api/).

Keep the token in the local root `.env`, not chat, frontend code, Git, screenshots,
or a public document. No need to deploy a Worker or move FastAPI to Cloudflare;
the adapter uses the REST API from the Python backend.

## 3. Configure the backend

Add/update these values in your local `.env` (replace the placeholders privately):

```dotenv
IMAGE_PROVIDER=cloudflare
CLOUDFLARE_ACCOUNT_ID=your_32_character_account_id
CLOUDFLARE_API_TOKEN=your_workers_ai_token
CLOUDFLARE_FREE_PLAN_CONFIRMED=true
CLOUDFLARE_IMAGE_TIMEOUT_SECONDS=90
```

Set the confirmation to true only after checking the actual Free plan. Default
configuration remains `IMAGE_PROVIDER=fake`, with blank credentials and the
confirmation false. Existing Gemini key/model settings stay unchanged. Restart
FastAPI after `.env` changes; do not print the resulting settings object.

The fixed model is `@cf/black-forest-labs/flux-1-schnell`, with four steps. The API
returns base64 image output; our adapter decodes it and the pipeline verifies the
JPEG format, square dimensions and size. Model selection is not exposed to clients.
[Model contract](https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/).

The image prompt uses the approved headline, slogan and call to action as concise
reference text, plus the reviewed scene brief/style and versioned safety/no-text
rules. Full source text remains in the database snapshot. Oversized composed
prompts are rejected rather than silently truncating the reference or asking
another LLM to rewrite it. Prompt requests do not guarantee visual correctness;
human review remains necessary.

## 4. Explicit one-request connection check

Once configured, from `backend`:

```powershell
# Safe default: fake provider, zero network generation requests.
.venv/Scripts/python.exe -m scripts.check_image_pipeline

# Explicit live test: one Cloudflare image request, consumes account quota.
.venv/Scripts/python.exe -m scripts.check_image_pipeline --cloudflare
```

The diagnostic uses synthetic seat-belt text, tests saved metadata/replay, rolls
back its database rows and removes its temporary files. It does not save a lasting
image to view or approve. A same-key replay inside the check must not cause another
provider call. No real Cloudflare requests were run during implementation.

401/403/404: check token, account scope, plan and model access. 429: quota/rate
limit; wait/check the dashboard, with no automatic paid continuation. Timeouts or
lost connections leave an inspectable ambiguous outcome; there is no automatic
retry. Errors do not include token values or raw provider response bodies.

Next implementation work: image endpoints, file cleanup/recovery and bilingual UI.
The Cloudflare credential test can happen before those screens are available.
