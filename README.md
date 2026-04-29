# Rocket.Chat upload filename fix (Docker)

Rocket.Chat shows the **client’s raw filename** on attachment headers (mobile and desktop). For non-ASCII names - Cyrillic, spaces, odd punctuation - that looks broken and is awkward to share.

This repo ships a **small server-side patch** to the bundled `app.js`: transliterate Cyrillic to Latin, fold spaces and junk characters to hyphens, and keep **upload validation + image pipeline** intact. **Tested on Rocket.Chat `8.3.2`** (official `registry.rocket.chat/rocketchat/rocket.chat:8.3.2` image).

**Suggested GitHub “About” line (copy-paste):**  
`Server patch for Rocket.Chat Docker: normalize attachment filenames (Cyrillic - Latin). Works on 8.3.x bundle.`

**Topics to add:** `rocketchat`, `docker`, `upload`, `filename`, `i18n`, `nodejs`

---

## What changes

| Before | After (example) |
|--------|------------------|
| Something like `ТЕСТ (В!!) () 00() всратос~.jpg` in the attachment title | A single safe string, e.g. `test-v-00-vsratos-.jpg` (lowercase, hyphens) |

Old messages keep their stored titles; **send a new file** to verify after deploy.

If you add before/after screenshots, drop them under `docs/images/` and link them here (pull requests welcome).

---

## What’s in the box

| Path | Role |
|------|------|
| [`patch_appjs_upload_names.py`](./patch_appjs_upload_names.py) | Idempotent edits to a **vanilla** `app.js` from the same image tag you run (three hooks: `uploadsOnValidate`, `sendFileMessage` after `updateFileComplete`, visitor livechat). |
| [`Patched_file/docker-patch/Dockerfile`](./Patched_file/docker-patch/Dockerfile) | `FROM` your server image + `COPY` patched `app.js` into the bundle path. |
| [`docs/patching.md`](./docs/patching.md) | Full deploy procedure: extract `app.js`, run the script, build image, `docker compose`, checks, pitfalls. |

The checked-in `Patched_file/docker-patch/app.js` is a **large** reference bundle; you can stop tracking it and rely on extracting from the image each time - see [`.gitignore`](./.gitignore).

---

## Quick use

1. **Backup MongoDB** before you touch production.
2. Pull the **exact** Rocket.Chat image tag you use, extract `app.js` from  
   `/app/bundle/programs/server/app/app.js` (`docker create` + `docker cp`).
3. Run (Python 3):

   ```bash
   python3 patch_appjs_upload_names.py /path/to/vanilla-app.js
   ```

4. Put patched `app.js` next to the Dockerfile, build a derived image (e.g. `:8.3.2-patched`), point `docker-compose.yml` at it, recreate the `rocketchat` service. Use `docker build --no-cache` if the old layer masks a new `app.js`.

5. Confirm logs show `SERVER RUNNING`, then upload a **new** file with a messy name and check the attachment title.

Details, edge cases, and upgrade notes: **[docs/patching.md](docs/patching.md)**.

---

## License

Treat the **patch script** as MIT-level permissive unless you add your own file; **Rocket.Chat** and its bundle remain under their upstream licenses. If you ship a derivative image, comply with Rocket.Chat’s terms and your registry rules.

---

*Maintained for our own Docker deploy; if it helps you, open an issue with your **Rocket.Chat version** and **image tag** when something drifts after an upgrade.*
