import os
import time
from pathlib import Path

import requests

API_ROOT = "https://apihub.agnes-ai.com"
MODEL = "agnes-video-2.5-flash"
API_KEY = os.environ.get("AGNES_API_KEY")
VIDEO_DIR = Path("assets/videos")
POLL_SECONDS = 10
MAX_POLLS = 90
# Agnes queue-full is a provider-side transient condition. Wait up to 2 hours.
QUEUE_RETRY_DELAYS = (300,) * 24

SCENES = [
    ("agnes_01_kitchen.mp4", "Vertical 9:16 cinematic photorealistic South Indian family drama. In the same warm, sunlit Indian home kitchen, a middle-aged Telugu mother-in-law wearing a maroon sari with tied-back dark hair and a small bindi holds a steel bowl of leftover rice. She speaks with her young adult daughter-in-law wearing a mustard-gold sari, maroon blouse, long dark braid and small bindi. The younger woman smiles confidently and gestures that she can make three dishes. Natural expressive faces, believable body movement, medium two-shot, consistent character appearance. No cartoon style, no text, no subtitles, no logos."),
    ("agnes_02_washing.mp4", "Vertical 9:16 cinematic photorealistic cooking scene in the exact same warm South Indian kitchen. The same young Telugu daughter-in-law in mustard-gold sari and maroon blouse mashes leftover cooked rice in a steel bowl, adds curd, rice flour, chopped onion, green chilli, cumin and coriander, then mixes with her hands. The same middle-aged mother-in-law in maroon sari watches curiously beside her. Show clear realistic hand action and ingredient textures, close-up then medium shot. Preserve the same faces, clothes and kitchen. No cartoon, no text, no subtitles, no logos."),
    ("agnes_03_chopping.mp4", "Vertical 9:16 photorealistic cinematic South Indian cooking close-up in the same kitchen. The same young daughter-in-law, mustard-gold sari and maroon blouse, places small portions of leftover-rice batter into a hot paniyaram pan, turns the round golden rice paniyaram with a small wooden skewer. The same mother-in-law in maroon sari smiles in the background. Visible sizzling and accurate cooking motion, warm natural light, realistic food. Maintain character and kitchen continuity. No cartoon, no text, no subtitles, no logos."),
    ("agnes_04_spices.mp4", "Vertical 9:16 photorealistic cinematic cooking scene in the same South Indian kitchen. The same daughter-in-law in mustard-gold sari carefully drops small onion and rice-flour pakodi portions into hot oil; they bubble and turn crisp golden brown. The same middle-aged mother-in-law in maroon sari tastes one pakodi and reacts with delighted surprise. Clear frying action, realistic oil bubbles, expressive reaction, warm light. Same faces, clothes and kitchen. No cartoon, no text, no subtitles, no logos."),
    ("agnes_05_stirring.mp4", "Vertical 9:16 photorealistic cinematic close-up in the same warm South Indian kitchen. The same young daughter-in-law in mustard-gold sari mixes leftover rice with curd and a little milk in a steel bowl, then pours a sizzling tempering of mustard seeds, green chilli and curry leaves into it. Show the actual mixing and pouring clearly, realistic food texture and natural hand movement. Preserve the same character and kitchen. No cartoon, no text, no subtitles, no logos."),
    ("agnes_06_serving.mp4", "Vertical 9:16 photorealistic cinematic family finale in the same Indian home. The same daughter-in-law in mustard-gold sari serves three dishes: golden rice paniyaram, crisp rice pakodi and curd rice. The same mother-in-law in maroon sari, young husband in olive-green shirt and father-in-law in simple traditional clothes taste the food and smile with impressed surprise. Warm family interaction, natural expressive faces, wide shot then food close-up. Keep faces and clothing consistent. No cartoon, no text, no subtitles, no logos."),
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

        # Agnes explicitly rejected this request because its queue is full.
        # Retry only this known transient response; never retry other API errors.
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
        print(f"{filename}: {status or 'pending'} ({attempt + 1}/{MAX_POLLS})")
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
