import asyncio
import re
from pathlib import Path

import edge_tts
from moviepy import AudioFileClip, concatenate_audioclips

CONTENT_DIR = Path("content")
OUTPUT = Path("telugu_audio.mp3")
SCENE_AUDIO_DIR = Path("assets/audio")
SCENE_COUNT = 6

VOICES = {
    "అమ్మమ్మ": "te-IN-ShrutiNeural",
    "అత్తయ్య": "te-IN-ShrutiNeural",
    "కోడలు": "te-IN-ShrutiNeural",
    "మామయ్య": "te-IN-MohanNeural",
    "భర్త": "te-IN-MohanNeural",
    "అవ్వ": "te-IN-ShrutiNeural",
    "నానమ్మ": "te-IN-ShrutiNeural",
    "అమ్మ": "te-IN-ShrutiNeural",
    "మనవరాలు": "te-IN-ShrutiNeural",
    "పాప": "te-IN-ShrutiNeural",
    "తాతయ్య": "te-IN-MohanNeural",
    "తాత": "te-IN-MohanNeural",
    "తాతగారు": "te-IN-MohanNeural",
    "నాన్న": "te-IN-MohanNeural",
    "Grandmother": "te-IN-ShrutiNeural",
    "Granddaughter": "te-IN-ShrutiNeural",
    "Mother": "te-IN-ShrutiNeural",
    "Grandfather": "te-IN-MohanNeural",
    "Father": "te-IN-MohanNeural",
}


def get_content_file():
    files = sorted(CONTENT_DIR.glob("*.md"))
    if not files:
        raise FileNotFoundError("content folderలో Markdown file లేదు")
    return files[-1]


def extract_script(text):
    match = re.search(
        r"Voiceover Script|వాయిస్ ఓవర్ స్క్రిప్ట్",
        text,
        re.IGNORECASE,
    )
    if not match:
        raise ValueError("Content fileలో Voiceover Script section కనిపించలేదు")

    remaining = text[match.end():]
    next_section = re.search(r"\n#{1,3}\s+|\n---", remaining)
    if next_section:
        remaining = remaining[:next_section.start()]
    return remaining.strip()


def clean_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"^\s*[-•]\s*", "", text)
    # Parenthetical stage directions are visual notes, not spoken dialogue.
    text = re.sub(r"^\([^)]*\)\s*", "", text)
    return text.strip()


def parse_scene_dialogue(script):
    speaker_names = "|".join(
        re.escape(name)
        for name in sorted(VOICES, key=len, reverse=True)
    )
    speaker_pattern = re.compile(
        rf"^\s*(?:[-*]\s*)?(?:\*\*)?({speaker_names})(?:\*\*)?\s*[:：]\s*(.*)$",
        re.IGNORECASE,
    )
    scene_pattern = re.compile(r"^\s*\*\*?\s*సన్నివేశం\s*(\d+)\b", re.IGNORECASE)

    scenes = {number: [] for number in range(1, SCENE_COUNT + 1)}
    current_scene = None

    for raw_line in script.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading = scene_pattern.match(line)
        if heading:
            current_scene = int(heading.group(1))
            if current_scene not in scenes:
                raise ValueError(f"Unexpected scene number: {current_scene}")
            continue

        if current_scene is None:
            continue

        match = speaker_pattern.match(line)
        if not match:
            continue

        speaker = match.group(1)
        spoken_text = clean_text(match.group(2))
        if spoken_text:
            voice = VOICES.get(speaker, "te-IN-ShrutiNeural")
            scenes[current_scene].append((voice, spoken_text))

    missing = [number for number, lines in scenes.items() if not lines]
    if missing:
        raise ValueError(
            "ప్రతి సన్నివేశానికి voice dialogue ఉండాలి. "
            f"డైలాగులు లేని సన్నివేశాలు: {missing}"
        )
    return scenes


async def create_scene_audio(scene_number, segments):
    SCENE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    output_file = SCENE_AUDIO_DIR / f"scene_{scene_number:02d}.mp3"
    temporary_files = []

    try:
        for index, (voice, spoken_text) in enumerate(segments, start=1):
            part_file = SCENE_AUDIO_DIR / f".scene_{scene_number:02d}_{index:03d}.mp3"
            print(
                f"Scene {scene_number}, dialogue {index}: {voice}",
                flush=True,
            )
            communicate = edge_tts.Communicate(
                text=spoken_text,
                voice=voice,
            )
            await communicate.save(str(part_file))
            temporary_files.append(part_file)

        clips = []
        combined = None
        try:
            clips = [AudioFileClip(str(path)) for path in temporary_files]
            combined = concatenate_audioclips(clips)
            combined.write_audiofile(
                str(output_file),
                fps=24000,
                codec="libmp3lame",
                logger=None,
            )
        finally:
            if combined:
                combined.close()
            for clip in clips:
                clip.close()
    finally:
        for path in temporary_files:
            path.unlink(missing_ok=True)

    print(f"Saved scene voice: {output_file}", flush=True)
    return output_file


def main():
    content_file = get_content_file()
    print("Reading story:", content_file, flush=True)
    story = content_file.read_text(encoding="utf-8")
    script = extract_script(story)
    scenes = parse_scene_dialogue(script)

    # Remove stale audio so a failed run cannot mix old and new scenes.
    SCENE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in SCENE_AUDIO_DIR.glob("scene_*.mp3"):
        old_file.unlink()

    scene_files = []
    for number in range(1, SCENE_COUNT + 1):
        scene_files.append(
            asyncio.run(create_scene_audio(number, scenes[number]))
        )

    clips = []
    combined = None
    try:
        clips = [AudioFileClip(str(path)) for path in scene_files]
        combined = concatenate_audioclips(clips)
        combined.write_audiofile(
            str(OUTPUT),
            fps=24000,
            codec="libmp3lame",
            logger=None,
        )
    finally:
        if combined:
            combined.close()
        for clip in clips:
            clip.close()

    print("Telugu scene-synced audio created:", OUTPUT, flush=True)


if __name__ == "__main__":
    main()
