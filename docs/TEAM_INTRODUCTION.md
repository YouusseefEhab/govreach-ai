# GovReach AI — New Team Member Introduction

Status: 8 November 2026

## What is our project?

GovReach AI is our graduation project: a platform that helps teams prepare
Egyptian government awareness campaigns using generative AI. We are starting
with **traffic safety**, such as seat belts, speeding and phone distraction.
Campaign content supports **Egyptian Arabic and English**.

The platform creates drafts for people to review. It is a student prototype,
not an official government service, and approval does not automatically publish
anything.

## What have we finished?

- **Project foundation:** the backend, database and campaign records are set up.
- **Campaign management:** users can create, view, edit and delete campaigns.
- **AI text:** Gemini generates a headline, slogan, awareness message, social
  media caption and call to action. We save the results and supplied references.
- **Text review:** users can edit drafts and approve or reject each language
  separately. Editing sends the text back to draft.
- **Website:** an Arabic-first interface with an English switch supports the
  campaign and text workflows. The team's new logo, navy/gold theme, navigation
  and homepage have been integrated while preserving the existing editors.
  Earlier mobile checks predate this redesign; keyboard testing is still pending.
- **Image backend:** Cloudflare image generation is connected. The API supports
  images based on approved text, saved history, preview, download and separate
  review. Repeat requests with the same request key do not generate again.
- **Image website workflow:** choose approved text, describe a scene, generate,
  recover a saved request, view/download images and review them independently.
  Browser tests used fake images; real visual-quality review is still needed.
- **Checks:** the latest recorded backend run passed 260 automated tests, plus
  a PostgreSQL image API check. Image visual quality still needs a human pilot.

## What are we doing next?

1. Test the image website workflow with a real image and inspect its quality.
2. Review usability and record the team's feedback.
3. Evaluate sample campaigns for Arabic quality, English meaning, factual
   accuracy and safe, relevant images. Finish keyboard testing.
4. Prepare the demonstration and update the project documentation.

**Agreed future direction:** short campaign videos with narration, subtitles and
sound; export in vertical 9:16, square 1:1, portrait 4:5 and landscape 16:9; and
direct publishing to connected social accounts after explicit user confirmation.
These are planned, not implemented. Platform/API access must be checked. User
accounts and cloud deployment are also later work. Paid AI services need a separate
budget decision. See [current status and roadmap](PROJECT_STATUS.md).

## What technologies do we use?

| Part | Tools |
| --- | --- |
| Website | React, TypeScript and Vite |
| Backend API | Python and FastAPI |
| Database | PostgreSQL, with SQLAlchemy and Alembic |
| Text generation | Google Gemini API |
| Image generation | Cloudflare Workers AI, FLUX.1 Schnell |
| Collaboration | Git and GitHub |

We use existing AI APIs rather than training our own model. Images currently
use local file storage; the application runs locally during development.

## How does the main workflow work?

Create a campaign → generate text → review/edit the text → approve the text →
generate an image → review the image → download the reviewed material.

## Where should a new member start?

- Repository: https://github.com/YouusseefEhab/govreach-ai
- Read the root README for setup and the `docs` folder for progress/testing guides.
- Ask the team which Git branch to use; recent work is on
  `codex/phase-4-foundation`.
- Keep API keys in your private `.env` file. Never commit or share real keys.
