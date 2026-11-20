
import re
from pathlib import Path

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    vfx
)

CONTENT_DIR = Path("content")
VIDEO_DIR = Path("assets/videos")

AUDIO = Path("telugu_audio.mp3")
OUTPUT = Path("wonder_telugu_video.mp4")

WIDTH = 720
HEIGHT = 1280
FPS = 24

SCENE_FILES = {
    "kitchen": "01_kitchen.mp4",
    "washing": "02_washing.mp4",
    "chopping": "03_chopping.mp4",
    "spices": "04_spices.mp4",
    "stirring": "05_stirring.mp4",
    "serving": "06_serving.mp4",
}

KEYWORDS = {
    "washing": [
        "wash", "washing", "కడగ", "శుభ్రం"
    ],
    "chopping": [
        "chop", "cut", "కోయ", "ముక్కలు"
    ],
    "spices": [
        "spice", "masala", "మసాలా", "పసుపు"
    ],
    "stirring": [
        "stir", "mix", "కలప", "వేయించ", "ఉడిక"
    ],
    "serving": [
        "serve", "serving", "వడ్డ", "ప్లేట్"
    ],
    "kitchen": [
        "kitchen", "వంటగది", "వంట"
    ],
}


def get_content_file():
    files = sorted(CONTENT_DIR.glob("*.md"))

    if not files:
        raise FileNotFoundError(
            "content folderలో Markdown file లేదు"
        )

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
        scenes = [
            "Traditional Indian kitchen",
            "Washing vegetables",
            "Chopping vegetables",
            "Adding spices",
            "Stirring food in a pan",
            "Serving homemade food"
        ]

    return [
        re.sub(r"\s+", " ", scene).strip()
        for scene in scenes[:8]
    ]


def select_video(scene, index):
    scene_lower = scene.lower()

    for category, words in KEYWORDS.items():
        if any(word in scene_lower for word in words):
            filename = SCENE_FILES[category]
            path = VIDEO_DIR / filename

            if path.exists():
                return path

    # If no keyword matches, use the clips in order.
    available = [
        VIDEO_DIR / filename
        for filename in SCENE_FILES.values()
        if (VIDEO_DIR / filename).exists()
    ]

    if not available:
        raise FileNotFoundError(
            "assets/videos folderలో వీడియో క్లిప్‌లు లేవు"
        )

    return available[index % len(available)]


def make_vertical(clip):
    scale = max(
        WIDTH / clip.w,
        HEIGHT / clip.h
    )

    resized = clip.resized(scale)

    x1 = (resized.w - WIDTH) / 2
    y1 = (resized.h - HEIGHT) / 2

    return resized.cropped(
        x1=x1,
        y1=y1,
        x2=x1 + WIDTH,
        y2=y1 + HEIGHT
    )


def main():
    if not AUDIO.exists():
        raise FileNotFoundError(
            "telugu_audio.mp3 not found. Run generate_audio.py first."
        )

    if not VIDEO_DIR.exists():
        raise FileNotFoundError(
            "assets/videos folder not found"
        )

    scenes = get_scenes()

    audio = AudioFileClip(str(AUDIO))
    scene_duration = audio.duration / len(scenes)

    original_clips = []
    scene_clips = []
    final_video = None

    try:
        for index, scene in enumerate(scenes):
            video_path = select_video(scene, index)

            print(
                f"Scene {index + 1}: {scene[:80]}"
            )
            print("Using:", video_path)

            original = VideoFileClip(
                str(video_path),
                audio=False
            )

            original_clips.append(original)

            vertical = make_vertical(original)

            looped = vertical.with_effects([
                vfx.Loop(duration=scene_duration)
            ])

            scene_clip = looped.subclipped(
                0,
                scene_duration
            )

            scene_clips.append(scene_clip)

        final_video = concatenate_videoclips(
            scene_clips,
            method="compose"
        )

        final_video = final_video.with_audio(audio)

        final_video.write_videofile(
            str(OUTPUT),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2
        )

        print("Video created successfully:", OUTPUT)

    finally:
        if final_video:
            final_video.close()

        for clip in original_clips:
            clip.close()

        audio.close()


if __name__ == "__main__":
    main()
