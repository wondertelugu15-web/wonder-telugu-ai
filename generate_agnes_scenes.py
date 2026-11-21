import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

API_ROOT = "https://apihub.agnes-ai.com"
MODEL = "agnes-video-2.5-flash"
API_KEY = os.environ.get("AGNES_API_KEY")
VIDEO_DIR = Path("assets/videos")
POLL_SECONDS = 10
MAX_POLLS = 90

SCENES = [
    ("agnes_01_kitchen.mp4", "A realistic Telugu grandmother in a clean, attractive South Indian home kitchen preparing ingredients for homemade tomato dal. Warm natural daylight, authentic Indian kitchen, medium camera shot, realistic human appearance and natural hand movements. No text, no subtitles, no logos."),
    ("agnes_02_washing.mp4", "Close-up of a Telugu grandmother's hands washing fresh red tomatoes and green chilies in a stainless steel bowl under clean running water, ingredients for South Indian tomato dal. Realistic water movement, clean home kitchen, natural daylight. No text, no subtitles, no logos."),
    ("agnes_03_chopping.mp4", "Close-up of an adult Indian woman's hands safely chopping washed ripe red tomatoes into small pieces on a clean wooden cutting board, green chilies beside them, South Indian home kitchen. Clear knife and hand movements, realistic food texture. No text, no subtitles, no logos."),
    ("agnes_04_spices.mp4", "Close-up of South Indian tempering for tomato dal: mustard seeds, cumin, dried red chilies and curry leaves sizzling in hot oil in a small pan. Visible bubbling and gentle movement, realistic Indian cooking, no people speaking. No text, no subtitles, no logos."),
    ("agnes_05_stirring.mp4", "A Telugu grandmother gently stirring cooked yellow lentils and tomato mixture in a pot with a ladle, adding the prepared South Indian tempering. Thick tomato dal visibly moves as she stirs, realistic steam, clean home kitchen. No text, no subtitles, no logos."),
    ("agnes_06_serving.mp4", "A Telugu grandmother serving steaming homemade tomato dal beside hot white rice onto a stainless steel plate at a family dining table. Close-up of the dal being ladled, appetizing realistic food, warm South Indian home atmosphere. No text, no subtitles, no logos."),
]


def api_request(method, url, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {API_KEY}"
    headers["Content-Type"] = "application/json"
    response = requests.request(method, url, headers=headers, timeout=90, **kwargs)
    if not response.ok:
        raise RuntimeError(
            f"Agnes API HTTP {response.status_code}: {response.text[:1200]}"
        )
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("Agnes API returned non-JSON response") from exc


def create_and_download(filename, prompt):
    payload = {
        "model": MODEL,
        "mode": "text",
        "prompt": prompt,
        "seconds": "5",
        "size": "720P",
        "aspect_ratio": "9:16",
        "n": 1,
    }
    created = api_request("POST", f"{API_ROOT}/v1/videos", json=payload)
    video_id = created.get("video_id")
    if not video_id:
        raise RuntimeError(f"Agnes create response has no video_id: {created}")

    print(f"Created {filename}; waiting for video result.")
    result = {}
    for attempt in range(MAX_POLLS):
        result = api_request(
            "GET",
            f"{API_ROOT}/agnesapi",
            params={"video_id": video_id, "model_name": MODEL},
        )
        status = str(result.get("status", "")).lower()
        print(f"{filename}: {status or 'pending'} ({attempt + 1}/{MAX_POLLS})")
        if status in {"completed", "succeeded", "success", "done"}:
            break
        if status in {"failed", "error", "cancelled"}:
            raise RuntimeError(f"Agnes video generation failed for {filename}: {result}")
        time.sleep(POLL_SECONDS)
    else:
        raise TimeoutError(f"Timed out waiting for Agnes video {video_id}")

    video_url = result.get("url") or result.get("video_url") or result.get("remixed_from_video_id")
    if not isinstance(video_url, str) or not video_url.startswith("https://"):
        raise RuntimeError(f"Agnes completed response has no HTTPS video URL: {result}")

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    target = VIDEO_DIR / filename
    with requests.get(video_url, stream=True, timeout=180) as response:
        response.raise_for_status()
        with target.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)

    if not target.exists() or target.stat().st_size < 100_000:
        target.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded video is missing or unexpectedly small: {filename}")
    print(f"Saved {target} ({target.stat().st_size} bytes)")


def main():
    if not API_KEY:
        raise RuntimeError("AGNES_API_KEY GitHub Secret is missing.")
    if not API_KEY.startswith("sk-"):
        raise RuntimeError("AGNES_API_KEY does not look like an Agnes secret key.")

    # Do not reuse old generated clips from a previous workflow run.
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    for filename, _ in SCENES:
        (VIDEO_DIR / filename).unlink(missing_ok=True)

    for filename, prompt in SCENES:
        create_and_download(filename, prompt)


if __name__ == "__main__":
    main()
