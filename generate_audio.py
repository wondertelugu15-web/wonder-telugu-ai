import asyncio
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from moviepy import AudioFileClip, concatenate_audioclips

CONTENT_DIR = Path("content")
OUTPUT = Path("telugu_audio.mp3")
SCENE_AUDIO_DIR = Path("assets/audio")
SCENE_COUNT = 6
API_KEY = os.environ.get("GIGGY_API_KEY", "").strip()
TTS_URL = "https://api.giggy.ai/v1/text-to-speech"

# Character voice IDs must be authorized custom voices created in Giggy My Voices.
VOICE_ENV = {
    "అత్తయ్య": "GIGGY_VOICE_ATTHA",
    "కోడలు": "GIGGY_VOICE_KODALU",
    "మామయ్య": "GIGGY_VOICE_MAMAYYA",
    "భర్త": "GIGGY_VOICE_BHARTA",
    "పిల్ల": "GIGGY_VOICE_PILLA",
    "పిల్లలు": "GIGGY_VOICE_PILLA",
    "అబ్బాయి": "GIGGY_VOICE_PILLA",
    "అమ్మాయి": "GIGGY_VOICE_PILLA",
}

def load_voices():
    voices, missing = {}, []
    for character, secret_name in VOICE_ENV.items():
        voice_id = os.environ.get(secret_name, "").strip()
        if voice_id:
            voices[character] = voice_id
        else:
            missing.append(secret_name)
    if missing:
        raise SystemExit("Missing custom voice IDs: " + ", ".join(sorted(set(missing))))
    return voices

VOICES = load_voices()

def get_content_file():
    files = sorted(CONTENT_DIR.glob("*.md"))
    if not files:
        raise FileNotFoundError("content folderలో Markdown file లేదు")
    return files[-1]

def extract_script(text):
    match = re.search(r"Voiceover Script|వాయిస్ ఓవర్ స్క్రిప్ట్", text, re.IGNORECASE)
    if not match:
        raise ValueError("Content fileలో Voiceover Script section కనిపించలేదు")
    remaining = text[match.end():]
    next_section = re.search(r"\n##\s+|\n---", remaining)
    if next_section:
        remaining = remaining[:next_section.start()]
    return remaining.strip()

def clean_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"^\s*[-•]\s*", "", text)
    text = re.sub(r"^\([^)]*\)\s*", "", text)
    return text.strip()

def parse_scene_dialogue(script):
    speaker_names = "|".join(re.escape(name) for name in sorted(VOICES, key=len, reverse=True))
    speaker_pattern = re.compile(
        rf"^\s*(?:[-*]\s*)?(?:\*\*)?({speaker_names})(?:\*\*)?\s*[:：]\s*(.*)$",
        re.IGNORECASE,
    )
    scene_pattern = re.compile(r"^\s*(?:#{1,3}\s*)?(?:\*\*)?\s*సన్నివేశం\s*(\d+)\b", re.IGNORECASE)
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
        if match:
            speaker, spoken_text = match.group(1), clean_text(match.group(2))
            if spoken_text:
                scenes[current_scene].append((speaker, VOICES[speaker], spoken_text))
    missing = [n for n, lines in scenes.items() if not lines]
    if missing:
        raise ValueError(f"డైలాగులు లేని సన్నివేశాలు: {missing}")
    return scenes

def giggy_generate(text, voice_id, output_file, idempotency_key):
    payload = {
        "text": text,
        "voice_id": voice_id,
        "model_id": "giggyspeech",
        "mode": "batch",
        "output_format": "mp3_24000_160",
        "voice_settings": {"speed": 1.0},
    }
    req = urllib.request.Request(
        TTS_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "xi-api-key": API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
            "Idempotency-Key": idempotency_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            data = response.read()
            content_type = response.headers.get("Content-Type", "")
            if "audio" not in content_type.lower() or not data:
                raise RuntimeError(f"Giggy did not return audio (Content-Type={content_type}).")
            output_file.write_bytes(data)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Giggy TTS failed: HTTP {exc.code}: {details[:1500]}") from exc

async def create_scene_audio(scene_number, segments):
    SCENE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    output_file = SCENE_AUDIO_DIR / f"scene_{scene_number:02d}.mp3"
    part_files = []
    try:
        for index, (speaker, voice_id, spoken_text) in enumerate(segments, start=1):
            part_file = SCENE_AUDIO_DIR / f".scene_{scene_number:02d}_{index:03d}.mp3"
            print(f"Scene {scene_number}, dialogue {index}: {speaker} ({voice_id})", flush=True)
            await asyncio.to_thread(
                giggy_generate, spoken_text, voice_id, part_file,
                f"wonder-telugu-scene-{scene_number:02d}-line-{index:03d}",
            )
            part_files.append(part_file)
        clips = []
        combined = None
        try:
            clips = [AudioFileClip(str(path)) for path in part_files]
            combined = concatenate_audioclips(clips)
            combined.write_audiofile(str(output_file), fps=24000, codec="libmp3lame", logger=None)
        finally:
            if combined:
                combined.close()
            for clip in clips:
                clip.close()
    finally:
        for path in part_files:
            path.unlink(missing_ok=True)
    print(f"Saved Giggy scene audio: {output_file}", flush=True)
    return output_file

def main():
    if not API_KEY:
        raise SystemExit("Missing GitHub Actions secret: GIGGY_API_KEY")
    content_file = get_content_file()
    print("Reading story:", content_file, flush=True)
    scenes = parse_scene_dialogue(extract_script(content_file.read_text(encoding="utf-8")))
    SCENE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in SCENE_AUDIO_DIR.glob("scene_*.mp3"):
        old_file.unlink()
    scene_files = []
    for number in range(1, SCENE_COUNT + 1):
        scene_files.append(asyncio.run(create_scene_audio(number, scenes[number])))
    clips = []
    combined = None
    try:
        clips = [AudioFileClip(str(path)) for path in scene_files]
        combined = concatenate_audioclips(clips)
        combined.write_audiofile(str(OUTPUT), fps=24000, codec="libmp3lame", logger=None)
    finally:
        if combined:
            combined.close()
        for clip in clips:
            clip.close()
    print("Giggy Telugu scene-synced audio created:", OUTPUT, flush=True)

if __name__ == "__main__":
    main()
