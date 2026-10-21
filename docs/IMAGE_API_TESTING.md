# Image API verification

Run the backend as usual and open [Swagger](http://127.0.0.1:8000/docs).
Restart it if the new **Images** section has not appeared. Image configuration is
read from the private root .env. Cloudflare requests consume your account quota;
automated tests and the PostgreSQL API diagnostic always use fake images.

## Manual steps

1. Use an existing campaign and GET its `/api/v1/campaigns/{campaign_id}/contents`.
   Choose one text package you have reviewed; use its content **id**, not the
   campaign ID or generation UUID. Correct the text first if needed, then approve
   it separately with PATCH `/api/v1/contents/{content_id}`:

   ```json
   {"review_status": "approved"}
   ```

2. POST `/api/v1/campaigns/{campaign_id}/generate-image`. Enter the campaign ID,
   and enter `seatbelt-image-test-1` in the required **Idempotency-Key** header.
   Replace 15 below with your approved content ID:

   ```json
   {
     "source_content_id": 15,
     "visual_brief": "A parked car in Egypt. An adult driver and adult front passenger wearing seat belts correctly across shoulder and hips. Calm daylight, clear safety equipment, no text or logos.",
     "style": "illustration"
   }
   ```

   Expected: **201**, `request_state: ready`, `review_status: draft`, actual
   provider/model metadata and `source_is_current: true`. Note the image **id**.
   The fake provider produces a blue placeholder only; Cloudflare produces artwork.

3. Execute the identical POST with the identical key again. Expected: **200**,
   the same image ID/state; no new generation. Changing inputs with the same key
   returns **409**. A replay never restarts a failed or uncertain request.

4. GET `/api/v1/campaigns/{campaign_id}/images` and GET `/api/v1/images/{image_id}`:
   **200** with saved metadata. History supports `skip` and `limit` (1–100).

5. Open `/api/v1/images/{image_id}/file` in the browser to view the image. Use
   `/api/v1/images/{image_id}/file?download=true` to download. Expected **200** with
   PNG/JPEG content type. Inspect road-safety correctness, seat belts, anatomy,
   Egyptian context, accidental writing/logos and visual defects. Structural file
   validation does not check these qualities.

6. PATCH `/api/v1/images/{image_id}` separately after visual review:

   ```json
   {"review_status": "approved"}
   ```

   Expected **200**. You can use `rejected` or `draft` instead. This updates only
   the image, and does not publish it or change the source text review status.

7. Optional stale-source test, using disposable content: edit the source text.
   Image GET must report `source_is_current: false`; approval must return **409**.
   The old snapshot and file remain inspectable. A previous recorded approval is
   historical; consumers must also check current source eligibility.

8. Optional deletion test: delete only a disposable campaign you created for this
   check. This deletes its text/image records and associated image files. Expected
   campaign DELETE **204**, image GET **404**. Never delete a real campaign merely
   to test cleanup.

If the provider times out or returns an error, inspect the campaign's image
history. Same-key replay returns saved state with **200**, including `failed`,
`reserved`, `generating` or `outcome_unknown`; it does not mean an image succeeded.
Only `ready` records have usable files. Resolve/check an uncertain outcome before
deciding whether to explicitly submit a new key (which makes a new quota-consuming
request). There is no automatic retry or provider fallback. Missing/damaged stored
files return **503** and cannot be approved; non-ready file/review requests return
**409**. A ready image is initially a draft requiring human review.

These local prototype routes have no authentication. Do not expose the API/media
to the public as a production service. Stored drafts/rejected/stale images are
accessible through the file endpoint for review; file access implies no approval.

## Automated PostgreSQL API check

From `backend`:

```powershell
.venv/Scripts/python.exe -m scripts.check_image_api
```

Uses disposable records and a temporary media folder. Covers generation, replay,
download, review, stale-source rejection and campaign cascade/file cleanup. Rows
are rolled back and files removed; no Cloudflare/Gemini calls. Sequence IDs may
advance even though rows roll back. CI runs this diagnostic too.

## File cleanup and interrupted requests

Database and local files cannot commit atomically. Campaign deletion cleans up
after a successful DB commit; cleanup failures are logged using opaque file keys.
After a process crash, use inspection first:

```powershell
.venv/Scripts/python.exe -m scripts.reconcile_images
```

Reports old orphan file keys, missing/invalid ready image IDs and pending request
IDs/states. Default age protection is 24 hours, minimum one hour. Does not traverse
directories, symlinks or unfamiliar filenames, or remove files referenced by rows.
Missing files are reported for operator investigation, never silently regenerated.

For changes, **stop every API and image diagnostic process first**; `--offline`
is your confirmation of that condition, not an automatic process detector:

```powershell
# Delete only old unreferenced media, after inspecting the report.
.venv/Scripts/python.exe -m scripts.reconcile_images --offline --apply

# Optional: mark one old interrupted generating request uncertain. Replace 123.
.venv/Scripts/python.exe -m scripts.reconcile_images --offline --mark-unknown 123
```

State recovery does not call a provider, reclaim a request, or make an uncertain
image ready. Reserved/failed/unknown records remain inspectable. Cleanup is local,
operator-run and not a background job. Use one persistent local media directory;
this storage design does not support multiple cloud replicas yet.
