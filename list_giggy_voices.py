import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.giggy.ai/v1/voices"
API_KEY = os.environ.get("GIGGY_API_KEY", "").strip()

if not API_KEY:
    raise SystemExit("Missing GitHub Actions secret: GIGGY_API_KEY")

telugu = []
offset = 0
page_size = 20

while offset <= 10000:
    query = urllib.parse.urlencode({
        "language": "Telugu",
        "limit": page_size,
        "offset": offset,
    })
    request = urllib.request.Request(
        f"{BASE}?{query}",
        headers={"xi-api-key": API_KEY, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"Giggy public voice-list request failed: HTTP {exc.code}: {detail[:1000]}"
        )

    page = payload.get("voices", [])
    telugu.extend(page)
    print(f"Loaded Telugu voice page at offset {offset}: {len(page)} voices", flush=True)
    if len(page) < page_size:
        break
    offset += page_size

if not telugu:
    raise SystemExit(
        "Giggy returned zero voices for language=Telugu. "
        "The API key authenticated, but the public voice endpoint returned no Telugu matches."
    )

telugu.sort(key=lambda voice: (
    str(voice.get("gender") or "").lower(),
    str(voice.get("name") or voice.get("voice_name") or "").lower(),
))
print(f"Found {len(telugu)} Telugu voices. No speech was generated and no credits were used.")
print("NAME | GENDER | ACCENT | VOICE_ID | PREVIEW")
for voice in telugu:
    name = voice.get("name") or voice.get("voice_name") or "Unnamed"
    gender = voice.get("gender") or "not specified"
    accent = voice.get("accent") or voice.get("description") or "not specified"
    voice_id = voice.get("voice_id") or ""
    preview = voice.get("preview_url") or voice.get("sample_url") or ""
    print(" | ".join(
        str(value).replace("|", "/")
        for value in (name, gender, accent, voice_id, preview)
    ))

summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
if summary_path:
    with open(summary_path, "a", encoding="utf-8") as summary:
        summary.write("# Giggy Telugu voice list\\n\\n")
        summary.write("Public Telugu voice catalog. No speech was generated; no credits were used.\\n\\n")
        summary.write("| Voice | Gender | Accent / description | Voice ID | Preview |\\n")
        summary.write("|---|---|---|---|---|\\n")
        for voice in telugu:
            name = str(voice.get("name") or voice.get("voice_name") or "Unnamed").replace("|", "\\|")
            gender = str(voice.get("gender") or "not specified").replace("|", "\\|")
            accent = str(voice.get("accent") or voice.get("description") or "not specified").replace("|", "\\|")
            voice_id = str(voice.get("voice_id") or "")
            preview = str(voice.get("preview_url") or voice.get("sample_url") or "")
            preview_cell = f"[Listen]({preview})" if preview else "—"
            summary.write(f"| {name} | {gender} | {accent} | `{voice_id}` | {preview_cell} |\\n")
