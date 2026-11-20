"""Upload a finished clip to YouTube as a Short.

usage: python upload_to_youtube.py jobs/<id>/edits/clip_<n>.mp4 [--caption "TEXT"]
                                             [--title "TEXT"] [--privacy private|unlisted|public]
                                             [--no-shorts-tag]

Reads clip_<n>.json next to the clip for title/hook/source credit if --title and --caption
are not given. One-time OAuth flow: opens a browser to google.com for consent, then saves
token.json next to credentials.json in the page folder. Reuses saved credentials afterward.

YouTube Shorts: vertical 1080x1920 (already ensured by clip-cutter), #Shorts in the title
and description, category 22 (People & Blogs) which Shorts default to.
"""
import argparse, json, os, sys, webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load_json

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_NAME = "client_secret.json"   # OAuth client credentials from Google Cloud Console
TOKEN_NAME = "token.json"                   # saved after first OAuth flow


def get_creds(page_dir):
    """Load or run the OAuth flow. Returns google.oauth2.credentials.Credentials."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    token_path = page_dir / TOKEN_NAME
    client_path = page_dir / CLIENT_SECRET_NAME
    if not client_path.exists():
        sys.exit(f"Missing {client_path}. Download your OAuth client JSON from the Google Cloud Console "
                 "(APIs & Services > Credentials > OAuth 2.0 Client IDs > Download JSON) "
                 "and save it as client_secret.json in your page folder. "
                 "See https://console.cloud.google.com/apis/credentials")

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
            # Pick an open port, print the URL, and open the browser.
            creds = flow.run_local_server(port=0, open_browser=False)
            auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
            print(f"\nOpen this URL if the browser did not open automatically:\n{auth_url}\n")
            webbrowser.open(auth_url)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def shorts_title(caption_meta, override_title):
    """Build a Shorts-ready title: hook first, then credit + #Shorts."""
    if override_title:
        return override_title[:100]
    hook = caption_meta.get("hook") or ""
    channel = caption_meta.get("source_channel") or "a creator"
    title = hook if hook else "GTA 6 clip"
    if len(title) + len(channel) + 4 <= 100:
        title = f"{title} via {channel}"
    if "#Shorts" not in title:
        title = (title + " #Shorts")[:100]
    return title


def shorts_description(caption_meta, override_caption):
    """Build the Shorts description with credit, source link, and hashtags."""
    if override_caption:
        return override_caption[:5000]
    lines = []
    hook = caption_meta.get("hook") or ""
    if hook:
        lines.append(hook)
        lines.append("")
    channel = caption_meta.get("source_channel") or "the creator"
    url = caption_meta.get("source_url")
    lines.append(f"Clip by {channel}.")
    if url:
        lines.append(f"Source: {url}")
    lines.append("")
    lines.append("#GTA6 #GTAVI #GTA6Clip #Shorts #Gaming")
    return "\n".join(lines)[:5000]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip", help="path to the finished clip mp4")
    ap.add_argument("--caption", default="", help="override description text")
    ap.add_argument("--title", default="", help="override video title")
    ap.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private",
                    help="initial privacy status (default private so you can review before public)")
    ap.add_argument("--no-shorts-tag", action="store_true",
                    help="do not append #Shorts to title/description")
    a = ap.parse_args()

    clip = Path(a.clip)
    if not clip.exists():
        sys.exit(f"FAIL file not found: {clip}")

    # Page folder: clip is in jobs/<id>/edits/, so page dir is jobs/<id>/.. i.e. two levels up from edits.
    # Walk up from <clip> until we find a folder containing token.json or client_secret.json,
    # defaulting to the parent of jobs/ (CLIP_DESK_HOME/cwd).
    page_dir = None
    p = clip.resolve()
    for _ in range(6):
        if (p / CLIENT_SECRET_NAME).exists() or (p / TOKEN_NAME).exists():
            page_dir = p; break
        if p == p.parent:
            break
        p = p.parent
    if page_dir is None:
        # fallback: look two levels up from edits (jobs/<id>/edits -> page root)
        page_dir = clip.resolve().parents[2] if len(clip.resolve().parents) >= 2 else Path.cwd()

    creds = get_creds(page_dir)

    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", credentials=creds)

    side = clip.with_suffix(".json")
    meta = load_json(side) if side.exists() else {}

    title = shorts_title(meta, a.title)
    desc = shorts_description(meta, a.caption)
    if a.no_shorts_tag:
        title = title.replace(" #Shorts", "")
        desc = desc.replace("#Shorts", "").strip()

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": desc,
                "categoryId": "22",  # People & Blogs — YouTube Shorts default
                "tags": ["GTA 6", "GTA VI", "GTA6", "gaming", "shorts"],
            },
            "status": {
                "privacyStatus": a.privacy,
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(str(clip), chunksize=-1, resumable=True),
    )

    print(f"Uploading {clip} to YouTube as a Short (privacy={a.privacy})...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}% uploaded")

    video_id = response["id"]
    video_url = f"https://youtube.com/watch?v={video_id}"
    shorts_url = f"https://youtube.com/shorts/{video_id}"
    print(f"\nUpload complete.")
    print(f"  Video: {video_url}")
    print(f"  Shorts: {shorts_url}")
    print(f"  Privacy: {a.privacy}")
    print(f"\nReview it at {shorts_url}, then change privacy to public when you're ready to post.")
    return 0


if __name__ == "__main__":
    main()
