# Phase 5 image interface and testing

Implemented 8 November 2026 within the existing React/FastAPI architecture.
The image workspace is part of `/campaigns/:campaignId`, in Arabic and English,
using the current navy/gold design. Use the **Campaign images / صور الحملة** shortcut
near the campaign title. No backend migration or provider change is required.

## What works

- Browse source text in pages of 20 and choose an approved package. Only approved
  packages on the current page are selectable; a page without approved text does
  not imply that the campaign has none on other pages. Open the source editor to
  review/approve text first. Source text keeps its original language/direction.
- Write a required scene brief (up to 2,000 Unicode characters) and choose
  illustration or photorealistic style. Images are square and text-free; the
  provider's combined prompt limit can still reject a long brief with source text.
- Explicitly submit generation. The original request key and inputs are saved
  before sending. No page load, refresh, language switch or polling generates an
  image. Pending mutations prevent repeat submission within this app instance.
- Keep the latest attempt in browser session storage for this campaign/tab,
  including the resulting image ID when available. This stores the brief and
  source ID, not credentials. Blocked storage gives an honest warning and falls
  back to memory. Closing a tab or starting a new tab may lose this local recovery
  record; server history still persists. There is no cross-tab shared pending lock.
- Recover/continue only after an explicit click, reusing the original request key
  and inputs. A saved request is returned without another provider call. If the
  original request never reached the server, recovery may start it and use quota;
  the interface explains this. Failed/unknown requests are never automatically
  restarted or labelled successful merely because replay returned HTTP 200.
- Starting a different image request requires a separate acknowledgement of
  additional quota use and any earlier uncertainty. Preparing the new form does
  not itself generate anything or delete saved image history.
- Read paginated image history, saved snapshots, references, actual provider/model,
  dimensions, review state and request state. A saved reserved/generating latest
  request with a known image ID is polled with GET every five seconds; no provider
  retry or invented percentage is shown. Other records refresh explicitly.
- Preview ready images and download through the backend's verified file endpoint.
  Missing/invalid previews show an error and disable approval. Fake-provider blue
  placeholders are clearly labelled. This validates file handling, not image quality.
- Review each image separately: approve, reject or return to draft. Approval needs
  a loaded preview, human-review acknowledgement and current source eligibility;
  the backend independently enforces eligibility and file verification. No review
  action publishes the campaign or approves the source text.
- Source edits/review changes invalidate image metadata in the current app. Refresh
  image history to check changes made outside this app/tab. Stale historical
  approvals are explicitly labelled and cannot be approved against changed text.
  Source snapshots remain the original text used to generate the image.

## Try it in the regular application

1. Open [campaigns](http://localhost:5173/campaigns), then a traffic-safety campaign.
2. Review a text package. Correct it first, save, then approve it separately.
3. Use **صور الحملة**, select the approved text, and describe a scene. Example:

   > A parked car in Egypt. An adult driver and front passenger correctly wearing
   > seat belts across shoulder and hips. Clear daylight, no writing or logos.

4. Click **توليد صورة جديدة** once. With Cloudflare configured this is a real
   quota-consuming request; these manual steps were not run against your live
   provider during implementation. Wait and inspect the saved result.
5. Check message relevance, equipment, anatomy, Egyptian context, unsafe details
   and accidental text/logos. Reject unsuitable output. Mark the review checkbox
   and approve only after actually reviewing an acceptable image.
6. Download the image and reload the campaign to confirm history persists.
7. For a disposable example, edit its source text and return to the campaign.
   Confirm the stale-source notice and disabled approval. No real source needs
   editing merely to test this; the isolated fixture already covered the behavior.

If a request fails, refresh saved images and inspect its state. Keep the original
request while deciding whether to recover it. A new key means a new request and
may use more quota, including when an earlier outcome is unknown.

## Verification record

Automated frontend checks cover image request validation, Unicode limits,
required identity, replay states, no automatic retries, safe error handling,
response identity/ready metadata, paginated reads, separate review, guarded file
URLs, corrupt/blocked recovery storage, approval gates, stale history, source link
safety, language direction and translated UI. All 67 frontend tests pass, alongside
source lint and the production build. Existing text/campaign tests remain. The
existing >500 kB JavaScript bundle advisory remains non-blocking.

Browser walkthrough used a separate frontend on port 5174 and an ephemeral
fake-provider API on 8001, with an isolated in-memory SQLite database and temporary
media. The fixture normalizes SQLite timestamps to the production PostgreSQL UTC
contract. It does not touch real campaigns, `.env` or Cloudflare/Gemini.

Observed: approved-source selection; explicit generation; preview; downloaded PNG;
separate approval; reload preserving the key, image ID and approval; source edit
resetting text to draft; stale image warning with historical approval; blocked
approval; independent rejection; Arabic/English interface switching. The fixture
reported **one provider call and one saved image**, even after reload and review.
No browser console errors were observed at the end of the walkthrough.

A 375-pixel viewport override was inspected (360-pixel document width excluding
the scrollbar); document width and content width matched, with no horizontal
overflow. This is a narrow-layout check, not a full physical-device test. A wider
responsive check was interrupted by browser reconnection, so no tablet coverage
is claimed. Full mobile-device and keyboard accessibility sign-off remains pending.

Real image visual quality, live latency and a small human-reviewed image pilot
remain next. Video, multiple video export formats and direct social publishing
remain later planned scope.
