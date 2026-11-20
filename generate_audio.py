import asyncio
import re
from pathlib import Path
import edge_tts

def get_voiceover():
    files = sorted(Path("content").glob("2026-11-20.*"))
    if not files:
        raise FileNotFoundError("Today's content file not found")

    content = files[0].read_text(encoding="utf-8")

    match = re.search(
        r"Voiceover Script\s*(.*?)(?=\n#\s|\Z)",
        content,
        re.S | re.I
    )

    if not match:
        raise ValueError("Voiceover Script section not found")

    text = match.group(1)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"[*#\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text

async def main():
    text = get_voiceover()

    communicate = edge_tts.Communicate(
        text,
        "te-IN-ShrutiNeural",
        rate="-5%"
    )

    await communicate.save("telugu_audio.mp3")
    print("Telugu voice generated!")

if __name__ == "__main__":
    asyncio.run(main())
