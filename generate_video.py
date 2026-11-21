import re
from pathlib import Path

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    concatenate_audioclips,
    concatenate_videoclips,
    vfx,
)

CONTENT_DIR = Path("content")
VIDEO_DIR = Path("assets/videos")
SCENE_AUDIO_DIR = Path("assets/audio")
OUTPUT = Path("wonder_telugu_video.mp4")

WIDTH = 720
HEIGHT = 1280
FPS = 24
SCENE_COUNT = 6

SCENE_FILES = (
    "agnes_01_kitchen.mp4",
    "agnes_02_washing.mp4",
    "agnes_03_chopping.mp4",
    "agnes_04_spices.mp4",
    "agnes_05_stirring.mp4",
    "agnes_06_serving.mp4",
)


def get_content_file():
    files = sorted(CONTENT_DIR.glob("*.md"))
    if not files:
        raise FileNotFoundError("content folderలో Markdown file లేదు")
    return files[-1]


def get_scenes():
    content_file = get_content_file()
    text = content_file.read_text(encoding="utf-8")

    section = re.search(
        r"##\s*\d+\.\s*Scene-by-Scene Video Prompts(.*?)(?=##\s*\d+\.|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not section:
        raise ValueError(
            f"{content_file}లో Scene-by-Scene Video Prompts section లేదు."
        )

    scenes = re.findall(
        r"###\s*Scene\s*(\d+)\s*:\s*(.*?)(?=###\s*Scene\s*\d+\s*:|\Z)",
        section.group(1),
        re.IGNORECASE | re.DOTALL,
    )
    scenes = sorted(
        ((int(number), re.sub(r"\s+", " ", body).strip()) for number, body in scenes),
        key=lambda item: item[0],
    )
    expected = list(range(1, SCENE_COUNT + 1))
    actual = [number for number, _ in scenes]
    if actual != expected or any(not body for _, body in scenes):
        raise ValueError(
            f"కథలో Scene 1 నుంచి Scene {SCENE_COUNT} వరకు పూర్తి prompts అవసరం. "
            f"కనిపించినవి: {actual}"
        )
    return [body for _, body in scenes]


def make_vertical(clip):
    scale = max(WIDTH / clip.w, HEIGHT / clip.h)
    resized = clip.resized(scale)
    x1 = (resized.w - WIDTH) / 2
    y1 = (resized.h - HEIGHT) / 2
    return resized.cropped(
        x1=x1,
        y1=y1,
        x2=x1 + WIDTH,
        y2=y1 + HEIGHT,
    )


def main():
    # Refuse demo footage; only actual story-matched generated clips are allowed.
    demo_names = {
        "01_kitchen.mp4",
        "02_washing.mp4",
        "03_chopping.mp4",
        "04_spices.mp4",
        "05_stirring.mp4",
        "06_serving.mp4",
    }
    present_samples = sorted(
        path.name for path in VIDEO_DIR.glob("*.mp4")
        if path.name in demo_names
    )
    if present_samples:
        raise RuntimeError(
            "STOP: demo/sample clips cannot be used in Wonder Telugu videos: "
            + ", ".join(present_samples)
        )

    scenes = get_scenes()
    original_clips = []
    scene_audio_clips = []
    scene_video_clips = []
    final_audio = None
    final_video = None

    try:
        for index, scene_description in enumerate(scenes):
            scene_number = index + 1
            video_path = VIDEO_DIR / SCENE_FILES[index]
            audio_path = SCENE_AUDIO_DIR / f"scene_{scene_number:02d}.mp3"

            if not video_path.exists():
                raise FileNotFoundError(
                    f"Scene {scene_number} video missing: {video_path}"
                )
            if not audio_path.exists():
                raise FileNotFoundError(
                    f"Scene {scene_number} Telugu voice missing: {audio_path}. "
                    "Run generate_audio.py first."
                )

            narration = AudioFileClip(str(audio_path))
            scene_audio_clips.append(narration)
            duration = narration.duration
            if duration <= 0:
                raise ValueError(f"Scene {scene_number} audio has no duration.")

            print(
                f"Scene {scene_number} ({duration:.1f}s): "
                f"{scene_description[:90]}",
                flush=True,
            )

            original = VideoFileClip(str(video_path), audio=False)
            original_clips.append(original)
            vertical = make_vertical(original)

            # Match each generated cooking clip to its own dialogue duration.
            looped = vertical.with_effects([vfx.Loop(duration=duration)])
            scene_video = looped.subclipped(0, duration)
            scene_video_clips.append(scene_video)

        final_audio = concatenate_audioclips(scene_audio_clips)
        final_video = concatenate_videoclips(
            scene_video_clips,
            method="compose",
        ).with_audio(final_audio)

        final_video.write_videofile(
            str(OUTPUT),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
        )
        print("Scene-synchronized Wonder Telugu video created:", OUTPUT, flush=True)

    finally:
        if final_video:
            final_video.close()
        if final_audio:
            final_audio.close()
        for clip in scene_video_clips:
            clip.close()
        for clip in scene_audio_clips:
            clip.close()
        for clip in original_clips:
            clip.close()


if __name__ == "__main__":
    main()
