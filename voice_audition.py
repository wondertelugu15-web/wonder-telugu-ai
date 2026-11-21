import json
import os
import urllib.error
import urllib.request
from pathlib import Path

API_KEY = os.environ.get("GIGGY_API_KEY", "").strip()
URL = "https://api.giggy.ai/v1/text-to-speech"
OUT = Path("voice-audition")
TEXT = "అమ్మా, ఈ రోజు మిగిలిన అన్నంతో ఏం చేద్దాం? రుచిగా ఏదైనా కొత్త వంటకం చేద్దామా?"

# Shortlist based on the Telugu voice catalogue descriptions.
# These are auditions, not final role assignments.
CANDIDATES = [
    ("A1_Grandmother_Pragat", "bfa43980-3843-4372-a218-18a7917a0a2f"),
    ("A2_Grandmother_Ananya", "b65be8c6-8251-4a90-9a3f-987ec3111ba6"),
    ("A3_Grandmother_Sravani", "1e70b97b-9a47-420a-86c1-33e80e3cda42"),
    ("B1_Daughter_Meghana", "20f1ddf7-61ab-4ee5-8691-d8a26eb53b9f"),
    ("B2_Daughter_Priyarthi", "d9dc10cf-1f5d-459f-94eb-2956d3d725cc"),
    ("B3_Daughter_Ananya", "b65be8c6-8251-4a90-9a3f-987ec3111ba6"),
]

def main():
    if not API_KEY:
        raise SystemExit("Missing GIGGY_API_KEY.")
    OUT.mkdir(exist_ok=True)
    for name, voice_id in CANDIDATES:
        payload = {
            "text": TEXT,
            "voice_id": voice_id,
            "model_id": "giggyspeech",
            "mode": "batch",
            "output_format": "mp3_24000_160",
            "voice_settings": {"speed": 1.0},
        }
        req = urllib.request.Request(
            URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "xi-api-key": API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
                "Idempotency-Key": "wonder-telugu-audition-" + name,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                data = response.read()
                content_type = response.headers.get("Content-Type", "")
                if "audio" not in content_type.lower() or not data:
                    raise RuntimeError(f"{name}: expected audio, got {content_type}: {data[:500]!r}")
                (OUT / f"{name}.mp3").write_bytes(data)
                print(f"OK {name}: {len(data)} bytes", flush=True)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{name}: HTTP {exc.code}: {detail[:1000]}") from exc
    (OUT / "LISTENING_GUIDE.txt").write_text(
        "All six clips speak the exact same Telugu sentence for fair voice comparison.\n"
        "A1-A3: possible mother-in-law/grandmother voices. B1-B3: possible daughter-in-law voices.\n"
        "Choose one A clip and one B clip that sound clearly different.\n"
        "These are candidate auditions; no role mapping is final until you approve.\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    main()
