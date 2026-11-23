import os
from pathlib import Path

import replicate
from moviepy import AudioFileClip

IMAGE = Path("assets/characters/family_reference_01.jpg")
AUDIO = Path("assets/audio/scene_01.mp3")
OUTPUT = Path("replicate_test_scene.mp4")
MODEL = "wan-video/wan-2.2-s2v"
MAX_SECONDS = 20


def main():
    if not os.environ.get("REPLICATE_API_TOKEN", "").strip():
        raise RuntimeError("Missing GitHub Secret: REPLICATE_API_TOKEN")
    if not IMAGE.is_file():
        raise FileNotFoundError("Add the approved family reference image at " + str(IMAGE))
    if not AUDIO.is_file():
        raise FileNotFoundError("Expected first-scene dialogue audio not found: " + str(AUDIO))

    with AudioFileClip(str(AUDIO)) as clip:
        duration = clip.duration
    if duration <= 0 or duration > MAX_SECONDS:
        raise RuntimeError("Audio length exceeds the approved 20-second test cap; refusing paid generation.")

    print("One scene only. Maximum expected charge at $0.02/sec: $" + format(duration * 0.02, ".2f"), flush=True)
    with IMAGE.open("rb") as image_file, AUDIO.open("rb") as audio_file:
        result = replicate.run(MODEL, input={
            "image": image_file,
            "audio": audio_file,
            "prompt": "A Telugu family in a warm South Indian home kitchen having a natural conversation. Preserve the faces and clothing from the family reference image. Subtle realistic facial and head movement, natural expressions, vertical portrait composition.",
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
