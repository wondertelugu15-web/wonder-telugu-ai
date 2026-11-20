
import os
import re
import requests
import tempfile
from pathlib import Path

from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx

AUDIO = Path("telugu_audio.mp3")
OUTPUT = Path("wonder_telugu_video.mp4")
CONTENT_DIR = Path("content")

PEXELS_API = "https://api.pexels.com/videos/search"

SCENE_QUERIES = [
    "Indian woman cooking in traditional kitchen",
    "washing fresh vegetables in kitchen",
    "chopping vegetables close up cooking",
    "adding spices to Indian curry in pan",
    "stirring food cooking in pan close up",
    "serving homemade Indian food family"
]


def get_content_file():
    files = sorted(CONTENT_DIR.glob("*.md"))
    if not files:
        raise FileNotFoundError("No daily content found in content folder")
    return files[-1]


def get_scenes():
    content_file = get_content_file()
    text = content_file.read_text(encoding="utf-8")

    scenes = re.findall(
        r"(?:Scene|సన్నివేశం)\s*\d+[:\-]?\s*(.*?)(?=(?:Scene|సన్నివేశం)\s*\d+[:\-]?|\Z)",
        text,
        re.S | re.I
    )

    if not scenes:
        return SCENE_QUERIES

    return [re.sub(r"\s+", " ", s).strip()[:500] for s in scenes[:6]]


def get_query(scene, index):
    scene = scene.lower()

    keywords = [
        (["wash", "కడగ", "శుభ్రం"], "washing vegetables in Indian kitchen"),
        (["chop", "cut", "కట్", "కోయ"], "chopping vegetables close up"),
        (["spice", "మసాలా", "పసుపు"], "adding spices to Indian cooking"),
        (["stir", "mix", "కలప", "కలుప"], "stirring curry in cooking pan"),
        (["fry", "వేయించ"], "frying food in Indian kitchen"),
        (["serve", "వడ్డ", "ప్లేట్"], "serving Indian homemade food"),
        (["cook", "వంట", "ఉడిక"], "Indian woman cooking in kitchen")
    ]

    for words, query in keywords:
        if any(word in scene for word in words):
            return query

    return SCENE_QUERIES[index % len(SCENE_QUERIES)]


def find_video(query):
    api_key = os.getenv("PEXELS_API_KEY")

    if not api_key:
        raise RuntimeError(
            "PEXELS_API_KEY missing. Add it in GitHub repository secrets."
        )

    response = requests.get(
        PEXELS_API,
        headers={"Authorization": api_key},
        params={
            "query": query,
            "per_page": 10,
            "orientation": "portrait"
        },
        timeout=60
    )

    response.raise_for_status()
    videos = response.json().get("videos", [])

    if not videos:
        raise RuntimeError(f"No Pexels videos found for: {query}")

    # Prefer portrait videos with sufficient resolution.
    videos.sort(
        key=lambda v: (
            v.get("height", 0) > v.get("width", 0),
            v.get("height", 0)
        ),
        reverse=True
    )

    for video in videos:
        files = video.get("video_files", [])

        usable = [
            f for f in files
            if f.get("link")
            and f.get("width", 0) >= 480
            and f.get("height", 0) >= 480
        ]

        if usable:
            usable.sort(
                key=lambda f: (
                    f.get("height", 0) > f.get("width", 0),
                    f.get("height", 0)
                ),
                reverse=True
            )
            return usable[0]["link"]

    raise RuntimeError("Pexels did not return a usable video file")


def download_video(url, path):
    with requests.get(url, stream=True, timeout=180) as response:
        response.raise_for_status()

        with open(path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)


def make_vertical(clip):
    target_width = 1080
    target_height = 1920

    scale = max(
        target_width / clip.w,
        target_height / clip.h
    )

    resized = clip.resized(
        new_size=(
            int(clip.w * scale),
            int(clip.h * scale)
        )
    )

    x1 = max(0, (resized.w - target_width) / 2)
    y1 = max(0, (resized.h - target_height) / 2)

    return resized.cropped(
        x1=x1,
        y1=y1,
        x2=x1 + target_width,
        y2=y1 + target_height
    )


def main():
    if not AUDIO.exists():
        raise FileNotFoundError("telugu_audio.mp3 not found")

    scenes = get_scenes()

    print(f"Found {len(scenes)} cooking scenes")

    audio = AudioFileClip(str(AUDIO))
    scene_duration = audio.duration / len(scenes)

    final_clips = []
    source_clips = []

    try:
        with tempfile.TemporaryDirectory() as temp_dir:

            for index, scene in enumerate(scenes):
                query = get_query(scene, index)

                print(f"Scene {index + 1}: {query}")

                video_url = find_video(query)

                video_path = Path(temp_dir) / f"scene_{index + 1}.mp4"

                download_video(video_url, video_path)

                source = VideoFileClip(str(video_path))
                source_clips.append(source)

                vertical = make_vertical(source)

                # Repeat short clips to fill the scene duration.
                looped = vertical.with_effects([
                    vfx.Loop(duration=scene_duration)
                ])

                final_clips.append(
                    looped.subclipped(0, scene_duration)
                )

            video = concatenate_videoclips(
                final_clips,
                method="compose"
            )

            video = video.with_audio(audio)

            video.write_videofile(
                str(OUTPUT),
                fps=24,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast",
                threads=2
            )

            video.close()

        print("Wonder Telugu vertical cooking video created!")

    finally:
        audio.close()

        for clip in source_clips:
            clip.close()


if __name__ == "__main__":
    main()
