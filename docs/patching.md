# Patching Rocket.Chat `app.js` (Docker)

Use this when you run Rocket.Chat from Docker and want **normalized attachment filenames** (see the [root README](../README.md) for context).

**Verified stack:** Rocket.Chat **8.3.2**, `patch_appjs_upload_names.py` with three anchored insertions: `uploadsOnValidate`, after `Uploads.updateFileComplete` in `sendFileMessage`, visitor livechat. Older messages in MongoDB are unchanged; test with a **new** upload.

---

## Rules

1. **`app.js` must match your image tag** - the bundle is built for one release; don’t drop in another minor’s file.
2. **Patch a vanilla extract** from the **same** image the server runs.
3. **Don’t replace the entire `uploadsOnValidate` method** - the image pipeline (`tmpFile` / Sharp / etc.) must stay after the first `if (!file.type …)`. The script only prepends logic at the needle; if needles move in a newer Rocket.Chat, adjust `NEEDLE_*` in the script or patch by hand following the same idea.
4. **Back up MongoDB** before production changes.

---

## Repo layout

- `patch_appjs_upload_names.py` - run against vanilla `app.js`.
- `Patched_file/docker-patch/Dockerfile` - example `FROM` + `COPY`.
- Optional reference `app.js` in tree (heavy); you can omit it from git and extract per build.

---

## On the server (typical flow)

Paths vary; adapt to your host layout and Compose file location.

### 1) Inventory

- `docker ps -a` (or `sudo docker …`) - note the **full image name:tag** for Rocket.Chat.
- Find `docker-compose.yml` and MongoDB service names.

### 2) Backup database

`mongodump` (or your usual backup) before stopping app services for long maintenance. Optionally save a copy of `docker-compose.yml` with the backup.

### 3) Stop the app container

Usually only the `rocketchat` service, not MongoDB:

```bash
docker compose stop rocketchat
```

### 4) Extract vanilla `app.js`

Inside the official image:

`/app/bundle/programs/server/app/app.js`

Example:

```bash
sudo docker create --name rc-src <FULL_IMAGE_NAME:TAG>
sudo docker cp rc-src:/app/bundle/programs/server/app/app.js /tmp/rc_app.js
sudo docker rm rc-src
```

Copy the result to your build dir (e.g. `docker-patch-build/app.js`).

### 5) Apply the patch

```bash
python3 patch_appjs_upload_names.py /tmp/rc_app.js
```

Re-run against a fresh copy if edits go wrong - don’t accumulate half-patches.

The script skips work if markers / `CYR_MAP` already present (idempotent sections).

### 6) Dockerfile

Minimal:

```dockerfile
FROM <same registry/image:tag as production>
COPY app.js /app/bundle/programs/server/app/app.js
```

Build:

```bash
docker build -t <your-registry>/rocketchat/rocket.chat:8.3.2-patched .
```

If `COPY app.js` was cached but you changed `app.js`, rebuild with **`docker build --no-cache`**.

### 7) Compose and start

Point the `rocketchat` service `image:` at your `-patched` tag, backup the old compose if you like, then:

```bash
docker compose up -d rocketchat --force-recreate
```

### 8) Verify

- Logs: expect `SERVER RUNNING`, migrations finishing without fatal errors.
- Smoke: homepage, optionally `/api/info` from inside the container.
- Functional: upload a file with Cyrillic/spaces/weird punctuation; attachment title should be normalized.

---

## Troubleshooting

| Symptom | Likely cause |
|--------|----------------|
| No visible change | Old messages unchanged; test **new** upload. Client cache: hard-reload or retry on mobile. |
| Patch “does nothing” on upgrade | Bundle layout changed; update `NEEDLE_*` in the script or re-locate hooks in the new `app.js`. |
| Broken image previews / Sharp / EXIF | Full `uploadsOnValidate` was replaced or bundle isn’t vanilla - re-extract from the official image and patch only at the needles. |
| Image still old after editing `app.js` | Rebuild with `--no-cache`. |

---

## After a successful deploy

- Align `Patched_file/docker-patch/Dockerfile` `FROM` with production.
- Commit script + doc changes; optional: stop tracking huge `app.js` via `.gitignore`.

---

## Upgrade loop

For each Rocket.Chat bump: `docker pull` new tag - extract fresh `app.js` - adjust script needles if needed - rebuild `-patched` image - update Compose - recreate container - verify.
