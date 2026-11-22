import os
import re
import time
from pathlib import Path

import requests

API_ROOT = "https://apihub.agnes-ai.com"
MODEL = "agnes-video-2.5-flash"
API_KEY = os.environ.get("AGNES_API_KEY")
ALLOW_PAID_VIDEO_GENERATION = os.environ.get("ALLOW_PAID_VIDEO_GENERATION", "false").lower() == "true"
CONTENT_DIR = Path("content")
VIDEO_DIR = Path("assets/videos")
POLL_SECONDS = 10
MAX_POLLS = 90
# Agnes queue-full is a provider-side transient condition. Wait up to 2 hours.
QUEUE_RETRY_DELAYS = (300,) * 24

SCENE_FILENAMES = (
    "agnes_01_kitchen.mp4",
    "agnes_02_washing.mp4",
    "agnes_03_chopping.mp4",
    "agnes_04_spices.mp4",
    "agnes_05_stirring.mp4",
    "agnes_06_serving.mp4",
)

CONTINUITY_PROMPT = """
Create a vertical 9:16 photorealistic live-action Telugu family cooking drama.
Keep the same people, faces, ages, hairstyles, clothing and the same warm,
clean South Indian home kitchen across every scene. Mother-in-law: middle-aged
Telugu woman in a maroon sari, tied-back dark hair and small bindi. Daughter-in-law:
young adult Telugu woman in a mustard-gold sari, maroon blouse, long dark braid
and small bindi. Husband: young adult Telugu man in a plain olive-green shirt.
Father-in-law: middle-aged Telugu man in simple traditional clothes.
Natural Indian body language, subtle facial expressions and realistic hands.
Show the exact ingredients and cooking action described for this scene.
Cinematic natural light, clear food detail, believable movement. No cartoon,
no slideshow, no montage of still images, no text, no logos, no subtitles,
no extra fingers, no duplicated people.
""".strip()


def get_content_file():
    files = sorted(CONTENT_DIR.glob("*.md"))
    if not files:
        raise FileNotFoundError("content folderలో Markdown file లేదు")
    return files[-1]


def load_story_scenes():
    content_file = get_content_file()
    story = content_file.read_text(encoding="utf-8")
    section = re.search(
        r"##\s*\d+\.\s*Scene-by-Scene Video Prompts(.*?)(?=##\s*\d+\.|\Z)",
        story,
        re.IGNORECASE | re.DOTALL,
    )
    if not section:
        raise ValueError(
            f"{content_file}లో '3. Scene-by-Scene Video Prompts' section లేదు. "
            "కథ, డైలాగులు, సన్నివేశాలు సిద్ధం చేసిన తర్వాతే వీడియో చేయాలి."
        )

    matches = re.findall(
        r"###\s*Scene\s*(\d+)\s*:\s*(.*?)(?=###\s*Scene\s*\d+\s*:|\Z)",
        section.group(1),
        re.IGNORECASE | re.DOTALL,
    )
    scenes = []
    for number, body in matches:
        description = re.sub(r"\s+", " ", body).strip()
        if not description:
            raise ValueError(f"Scene {number}లో video prompt ఖాళీగా ఉంది.")
        scenes.append((int(number), description))

    scenes.sort(key=lambda item: item[0])
    expected = list(range(1, len(SCENE_FILENAMES) + 1))
    actual = [number for number, _ in scenes]
    if actual != expected:
        raise ValueError(
            f"{content_file}లో ఖచ్చితంగా Scene 1 నుంచి Scene 6 వరకు ఉండాలి. "
            f"కనిపించినవి: {actual}"
        )

    print(f"Story-first mode: {content_file} ({len(scenes)} authored scenes)", flush=True)
    return [
        (SCENE_FILENAMES[number - 1],
         f"{CONTINUITY_PROMPT}\n\nScene {number}: {description}")
        for number, description in scenes
    ]


def api_request(method, url, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {API_KEY}"
    headers["Content-Type"] = "application/json"

    is_video_create = method.upper() == "POST" and url.endswith("/v1/videos")
    attempts = len(QUEUE_RETRY_DELAYS) + 1 if is_video_create else 1

    for attempt in range(attempts):
        response = requests.request(method, url, headers=headers, timeout=90, **kwargs)
        if response.ok:
            try:
                return response.json()
            except ValueError as exc:
                raise RuntimeError("Agnes API returned non-JSON response") from exc

        if (
            is_video_create
            and response.status_code == 503
            and "video_queue_full" in response.text
            and attempt < len(QUEUE_RETRY_DELAYS)
        ):
            delay = QUEUE_RETRY_DELAYS[attempt]
            print(
                f"Agnes video queue is full. Safe retry "
                f"{attempt + 1}/{len(QUEUE_RETRY_DELAYS)} in {delay} seconds.",
                flush=True,
            )
            time.sleep(delay)
            continue

        raise RuntimeError(
            f"Agnes API HTTP {response.status_code}: {response.text[:1200]}"
        )

    raise RuntimeError("Agnes video queue remained full after all safe retries.")


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

    print(f"Created {filename}; waiting for video result.", flush=True)
    result = {}
    for attempt in range(MAX_POLLS):
        result = api_request(
            "GET",
            f"{API_ROOT}/agnesapi",
            params={"video_id": video_id, "model_name": MODEL},
        )
        status = str(result.get("status", "")).lower()
        print(f"{filename}: {status or 'pending'} ({attempt + 1}/{MAX_POLLS})", flush=True)
        if status in {"completed", "succeeded", "success", "done"}:
            break
        if status in {"failed", "error", "cancelled"}:
            raise RuntimeError(f"Agnes video generation failed for {filename}: {result}")
        time.sleep(POLL_SECONDS)
    else:
        raise TimeoutError(f"Timed out waiting for Agnes video {video_id}")

    video_url = result.get("url") or result.get("video_url")
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
    print(f"Saved {target} ({target.stat().st_size} bytes)", flush=True)


def main():
    # Parse and validate the complete story before any paid API request.
    scenes = load_story_scenes()

    if not ALLOW_PAID_VIDEO_GENERATION:
        raise RuntimeError(
            "Paid video generation is LOCKED. No Agnes API request was made. "
            "Set ALLOW_PAID_VIDEO_GENERATION=true only after reviewing the "
            "estimated cost and explicitly approving this run."
        )
    if not API_KEY:
        raise RuntimeError("AGNES_API_KEY GitHub Secret is missing.")
    if not API_KEY.startswith("sk-"):
        raise RuntimeError("AGNES_API_KEY does not look like an Agnes secret key.")

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    for filename, prompt in scenes:
        target = VIDEO_DIR / filename
        if target.exists() and target.stat().st_size >= 100_000:
            print(
                f"Reusing completed scene {target} "
                f"({target.stat().st_size} bytes); skipping paid generation.",
                flush=True,
            )
            continue
        target.unlink(missing_ok=True)
        create_and_download(filename, prompt)

    missing = [
        filename for filename, _ in scenes
        if not (VIDEO_DIR / filename).exists()
        or (VIDEO_DIR / filename).stat().st_size < 100_000
    ]
    if missing:
        raise RuntimeError("Scenes still missing after generation: " + ", ".join(missing))


if __name__ == "__main__":
    main()
