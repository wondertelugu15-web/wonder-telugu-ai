import re
import requests
from pathlib import Path
from urllib.parse import quote
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

CONTENT = Path("content/2026-11-20.md")
AUDIO = Path("telugu_audio.mp3")
OUTPUT = Path("wonder_telugu_video.mp4")

def get_scenes():
    text = CONTENT.read_text(encoding="utf-8")

    scenes = re.findall(
        r"(?:Scene|సన్నివేశం)\s*\d+[:\-]?\s*(.*?)(?=(?:Scene|సన్నివేశం)\s*\d+[:\-]?|\Z)",
        text,
        re.S | re.I
    )

    if not scenes:
        scenes = [
            "A beautiful traditional Telugu village kitchen, warm morning light",
            "A Telugu mother preparing healthy ragi porridge at home",
            "A grandmother explaining the benefits of ragi to a child",
            "A happy family enjoying healthy homemade food",
            "Close up of a bowl of nutritious ragi porridge",
            "A peaceful traditional Telugu village home"
        ]

    return [re.sub(r"\s+", " ", s).strip()[:500] for s in scenes[:6]]

def download_image(prompt, number):
    import time

    url = "https://stable-diffusion-xl.endpoints.kepler.ai.cloud.ovh.net/api/text2image"

    payload = {
        "prompt": (
            "Realistic cinematic photograph, traditional Telugu village "
            "home, family friendly, natural lighting, " + prompt
        ),
        "negative_prompt": "blurry, cartoon, distorted, low quality"
    }

    time.sleep(35)

    response = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=180
    )
    response.raise_for_status()

    path = Path(f"scene_{number}.jpg")
    path.write_bytes(response.content)
    return str(path)

def main():
    if not AUDIO.exists():
        raise FileNotFoundError("telugu_audio.mp3 not found")

    scenes = get_scenes()
    images = [
        download_image(prompt, i + 1)
        for i, prompt in enumerate(scenes)
    ]

    audio = AudioFileClip(str(AUDIO))
    duration = audio.duration / len(images)

    clips = [
        ImageClip(image).with_duration(duration)
        for image in images
    ]

    video = concatenate_videoclips(clips, method="compose")
    video = video.with_audio(audio)

    video.write_videofile(
        str(OUTPUT),
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    audio.close()
    video.close()
    print("Wonder Telugu video created successfully!")

if __name__ == "__main__":
    main()
