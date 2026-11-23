import os
from pathlib import Path

import replicate
from moviepy import AudioFileClip

IMAGE = Path("assets/characters/family_reference_01.jpg")
AUDIO_DIR = Path("assets/audio")
OUTPUT = Path("replicate_test_scene.mp4")
MODEL = "wan-video/wan-2.2-s2v"
MAX_SECONDS = 20


def main():
    if not os.environ.get("REPLICATE_API_TOKEN", "").strip():
        raise RuntimeError("Missing GitHub Secret: REPLICATE_API_TOKEN")
    if not IMAGE.is_file():
        raise FileNotFoundError("Add the approved family reference image at " + str(IMAGE))

    # Use only the first speaker's original dialogue clip, not the full combined scene.
    candidates = sorted(AUDIO_DIR.glob(".scene_01_001_*.mp3"))
    if not candidates:
        raise FileNotFoundError("First dialogue audio clip not found in " + str(AUDIO_DIR))
    audio_path = candidates[0]

    with AudioFileClip(str(audio_path)) as clip:
        duration = float(clip.duration or 0)
    print("First dialogue clip duration: " + format(duration, ".2f") + " seconds", flush=True)
    if duration <= 0 or duration > MAX_SECONDS:
        raise RuntimeError(
            "First dialogue clip must be between 0 and 20 seconds; actual duration is "
            + format(duration, ".2f") + " seconds. No paid generation was started."
        )

    print("One short dialogue clip only. Maximum expected charge at $0.02/sec: $" + format(duration * 0.02, ".2f"), flush=True)
    with IMAGE.open("rb") as image_file, audio_path.open("rb") as audio_file:
        result = replicate.run(MODEL, input={
            "image": image_file,
            "audio": audio_file,
            "prompt": "A Telugu mother-in-law in a warm South Indian home kitchen speaking naturally. Preserve the face and clothing from the family reference image. Subtle realistic facial and head movement, natural expression, vertical portrait composition.",
            "num_frames_per_chunk": 81,
            "interpolate": False,
        })

    if hasattr(result, "read"):
        data = result.read()
    elif isinstance(result, (bytes, bytearray)):
        data = bytes(result)
    else:
        raise RuntimeError("Unexpected Replicate output type: " + type(result).__name__)
    if not data or len(data) < 50000:
        raise RuntimeError("Replicate returned an empty or unexpectedly small video.")

    OUTPUT.write_bytes(data)
    print("Created " + str(OUTPUT) + " (" + str(OUTPUT.stat().st_size) + " bytes)", flush=True)


if __name__ == "__main__":
    main()
