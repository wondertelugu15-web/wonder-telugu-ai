import os
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

def main():
    video_file = Path("wonder_telugu_video.mp4")
    if not video_file.exists():
        raise FileNotFoundError("Video file not found")

    token_data = json.loads(os.environ["YOUTUBE_TOKEN_JSON"])

    credentials = Credentials.from_authorized_user_info(
        token_data,
        scopes=SCOPES
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    youtube = build("youtube", "v3", credentials=credentials)

    content_files = sorted(Path("content").glob("*.md"))
    if not content_files:
        raise FileNotFoundError("Content file not found")

    content = content_files[-1].read_text(encoding="utf-8")
    title = "Wonder Telugu - ఆరోగ్యకరమైన జీవన విధానం"

    for line in content.splitlines():
        clean = line.strip().strip("*# ")
        if clean and ("–" in clean or "-" in clean):
            title = clean[:100]
            break

    body = {
        "snippet": {
            "title": title,
            "description": "తెలుగు ఆరోగ్య సమాచారం. మరిన్ని వీడియోల కోసం Wonder Telugu ఛానల్‌ను చూడండి.\n\nసూచన: ఈ వీడియో సాధారణ సమాచార ప్రయోజనాల కోసం మాత్రమే.",
            "categoryId": "26"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        str(video_file),
        mimetype="video/mp4",
        resumable=True
    )

    result = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    ).execute()

    print("YouTube upload successful!")
    print("Video ID:", result["id"])
    print("Video URL: https://www.youtube.com/watch?v=" + result["id"])

if __name__ == "__main__":
    main()
