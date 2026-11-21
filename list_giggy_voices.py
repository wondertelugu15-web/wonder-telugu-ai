import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.giggy.ai/v1/integrations/voices"
API_KEY = os.environ.get("GIGGY_API_KEY")

if not API_KEY:
    raise SystemExit("Missing GitHub Actions secret: GIGGY_API_KEY")

all_voices = []
offset = 0
while True:
    query = urllib.parse.urlencode({"limit": 100, "offset": offset})
    request = urllib.request.Request(
        f"{BASE}?{query}",
        headers={"xi-api-key": API_KEY, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Giggy voice-list request failed: HTTP {exc.code}: {detail[:1000]}")

    voices = payload.get("voices", [])
    all_voices.extend(voices)
    if not payload.get("has_more") or payload.get("next_offset") is None:
        break
    offset = payload["next_offset"]

telugu = [
    voice for voice in all_voices
    if "telugu" in str(voice.get("language", "")).lower()
]
if not telugu:
    raise SystemExit(
        f"Giggy API key worked, but no Telugu voices were returned. "
        f"Total public voices checked: {len(all_voices)}"
    )

telugu.sort(key=lambda voice: (
    str(voice.get("gender") or "").lower(),
    str(voice.get("name") or "").lower(),
))
print(f"Found {len(telugu)} Telugu voices. No speech was generated and no credits were used.")
print("NAME | GENDER | ACCENT | VOICE_ID | PREVIEW")
for voice in telugu:
    row = [
        voice.get("name", ""),
        voice.get("gender") or "unspecified",
        voice.get("accent") or "unspecified",
        voice.get("voice_id", ""),
        voice.get("preview_url") or "",
    ]
    print(" | ".join(str(value).replace("|", "/") for value in row))

summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
if summary_path:
    with open(summary_path, "a", encoding="utf-8") as summary:
        summary.write("# Giggy Telugu voice list\\n\\n")
        summary.write("No TTS generation was run; this lookup does not generate audio.\\n\\n")
        summary.write("| Voice | Gender | Accent | Voice ID | Preview |\\n")
        summary.write("|---|---|---|---|---|\\n")
        for voice in telugu:
            name = str(voice.get("name", "")).replace("|", "\\|")
            gender = str(voice.get("gender") or "unspecified").replace("|", "\\|")
            accent = str(voice.get("accent") or "unspecified").replace("|", "\\|")
            voice_id = str(voice.get("voice_id", ""))
            preview = str(voice.get("preview_url") or "")
            preview_cell = f"[Listen]({preview})" if preview else "—"
            summary.write(f"| {name} | {gender} | {accent} | `{voice_id}` | {preview_cell} |\\n")
