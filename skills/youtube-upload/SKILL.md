---
name: youtube-upload
description: Upload a finished clip to YouTube as a Short. Use after rule-check passes, when the user says "upload to YouTube", "post as Short", or "publish the clip".
---

# YouTube Shorts upload

Uploads the finished 1080x1920 clip to YouTube as a Short (vertical video, `#Shorts` tag).
Nothing is uploaded automatically — you approve the privacy status and review the link before going public.

## 1. One-time Google Cloud setup (no questions)

Before the first upload, create OAuth credentials:

1. Go to https://console.cloud.google.com/apis/credentials
2. Create project (if needed) → "Create Credentials" → "OAuth client ID"
3. Application type: **Desktop app**. Name it anything (e.g. "gtavi-codex upload").
4. Download the JSON and save it as `client_secret.json` in your page folder
   (the folder that contains `jobs/`, `campaigns.md`, `scoreboard.csv`).

You only do this once. The OAuth flow runs in the browser and saves `token.json` next to it.

## 2. Install the Google API client (no questions)

```
python -m pip install -U google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Add these to `requirements.txt` too.

## 3. Upload

Run:

```
python "${PLUGIN_ROOT}/scripts/upload_to_youtube.py" jobs/<id>/edits/clip_<n>.mp4
```

Options:

- `--title "TEXT"` — override the auto-generated title
- `--caption "TEXT"` — override the auto-generated description
- `--privacy private|unlisted|public` — initial privacy (default `private`, so you can review first)
- `--no-shorts-tag` — do not append `#Shorts`

The title and description are auto-generated from `clip_<n>.json` (hook, source channel, source URL)
written by `clip-cutter`. They include credit to the creator and `#GTA6 #GTAVI #Shorts` hashtags.

## 4. After upload

The script prints the watch URL and Shorts URL. Review the Short at the link, then:

- Keep it `private` / `unlisted` until you are happy
- Change privacy to `public` in YouTube Studio when ready
- Submit the link to the campaign (if you are clipping for a paid campaign)

Only after all checks pass (`rule-check`) and you say yes, upload. Never auto-upload without approval.
