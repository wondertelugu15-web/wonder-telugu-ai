
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
    "hook": "agnes_01_kitchen.mp4",
    "batter": "agnes_02_washing.mp4",
    "paniyaram": "agnes_03_chopping.mp4",
    "pakodi": "agnes_04_spices.mp4",
    "curd": "agnes_05_stirring.mp4",
    "serving": "agnes_06_serving.mp4",
}

KEYWORDS = {
    "hook": ["family story", "అత్తయ్య", "కోడలు", "మిగిలిన అన్నం"],
    "batter": ["mixing", "కలుపు", "బియ్యప్పిండి", "మిశ్రమం"],
    "paniyaram": ["పునుగులు", "పాన్", "తిప్పుతోంది", "బంగారు రంగు"],
    "pakodi": ["పకోడీ", "పకోడీలు", "వేడి నూనె", "వేయిస్తోంది"],
    "curd": ["పెరుగు అన్నం", "పెరుగు", "పోపు", "కరివేపాకు"],
    "serving": ["వడ్డిస్తోంది", "వడ్డించ", "కుటుంబం", "రుచి చూస్తున్నారు"],
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
    # Scene headings in the content file are authored in the same order
    # as the six generated story clips. Select by sequence so dialogue
    # mentioning a character cannot accidentally select the wrong footage.
    filenames = list(SCENE_FILES.values())
    if index >= len(filenames):
        raise IndexError(
            f"Scene {index + 1} has no generated clip. "
            f"Expected at most {len(filenames)} story scenes."
        )

    path = VIDEO_DIR / filenames[index]
    if not path.exists():
        raise FileNotFoundError(
            f"Required story clip is missing for scene {index + 1}: {path}"
        )
    return path

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
    sample_names = {
        "01_kitchen.mp4", "02_washing.mp4", "03_chopping.mp4",
        "04_spices.mp4", "05_stirring.mp4", "06_serving.mp4"
    }
    present_samples = sorted(
        p.name for p in VIDEO_DIR.glob("*.mp4")
        if p.name in sample_names
    )
    if present_samples:
        raise RuntimeError(
            "STOP: assets/videos contains demo/sample clips "
            f"({', '.join(present_samples)}). "
            "They are not allowed in published Wonder Telugu videos. "
            "Connect a genuine AI scene-generation source and place its "
            "recipe-matched clips in assets/videos before rendering."
        )

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
