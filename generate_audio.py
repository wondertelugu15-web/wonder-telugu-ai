import asyncio
import edge_tts
from pathlib import Path

async def main():
    text = Path("content/2026-11-20.md").read_text(encoding="utf-8")

    voice = "te-IN-ShrutiNeural"

    communicate = edge_tts.Communicate(
        text,
        voice,
        rate="-5%",
        volume="+0%"
    )

    await communicate.save("telugu_audio.mp3")
    print("Telugu audio generated successfully!")

if __name__ == "__main__":
    asyncio.run(main())
