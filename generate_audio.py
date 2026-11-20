
import asyncio
import re
import tempfile
from pathlib import Path

import edge_tts
from moviepy import AudioFileClip, concatenate_audioclips

CONTENT_DIR = Path("content")
OUTPUT = Path("telugu_audio.mp3")

VOICES = {
    "అమ్మమ్మ": "te-IN-ShrutiNeural",
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
        re.IGNORECASE
    )

    if not match:
        raise ValueError("Content fileలో Voiceover Script section కనిపించలేదు")

    remaining = text[match.end():]

    next_section = re.search(
        r"\n#{1,3}\s+|\n---",
        remaining
    )

    if next_section:
        remaining = remaining[:next_section.start()]

    return remaining.strip()


def clean_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"^\s*[-•]\s*", "", text)
    return text.strip()


def parse_dialogue(script):
    segments = []

    speaker_names = "|".join(
        re.escape(name) for name in VOICES.keys()
    )

    pattern = re.compile(
        rf"^\s*(?:[-*]\s*)?(?:\*\*)?({speaker_names})(?:\*\*)?\s*[:：]\s*(.*)$",
        re.IGNORECASE
    )

    for line in script.splitlines():
        line = line.strip()

        if not line:
            continue

        match = pattern.match(line)

        if match:
            speaker = match.group(1)
            spoken_text = clean_text(match.group(2))

            if spoken_text:
                voice = VOICES.get(
                    speaker,
                    "te-IN-ShrutiNeural"
                )
                segments.append((voice, spoken_text))

    if not segments:
        plain_text = clean_text(script)

        if plain_text:
            segments.append(
                ("te-IN-ShrutiNeural", plain_text)
            )

    if not segments:
        raise ValueError("Voiceover Scriptలో మాట్లాడే వాక్యాలు లేవు")

    return segments


async def create_audio(segments, temp_dir):
    audio_files = []

    for index, (voice, text) in enumerate(segments):
        output_file = Path(temp_dir) / f"voice_{index}.mp3"

        print(f"Creating voice segment {index + 1}: {voice}")

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice
        )

        await communicate.save(str(output_file))
        audio_files.append(output_file)

    return audio_files


def main():
    content_file = get_content_file()
    print("Reading:", content_file)

    text = content_file.read_text(encoding="utf-8")
    script = extract_script(text)
    segments = parse_dialogue(script)

    print("Dialogue segments:", len(segments))

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_files = asyncio.run(
            create_audio(segments, temp_dir)
        )

        clips = []
        final_audio = None

        try:
            for file in audio_files:
                clips.append(
                    AudioFileClip(str(file))
                )

            final_audio = concatenate_audioclips(clips)

            final_audio.write_audiofile(
                str(OUTPUT),
                fps=24000,
                codec="libmp3lame"
            )

        finally:
            if final_audio:
                final_audio.close()

            for clip in clips:
                clip.close()

    print("Telugu audio created:", OUTPUT)


if __name__ == "__main__":
    main()
