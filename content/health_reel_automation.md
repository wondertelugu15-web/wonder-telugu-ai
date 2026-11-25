# Wonder Telugu — zero-budget animated health reel workflow

## What is implemented
- A Telugu health-tip pilot script about ordinary dry-skin care.
- Edge TTS Telugu narration using the free online Telugu neural voice, with no API key.
- A Python/Pillow renderer that creates original expressive mascot scenes, Telugu captions and a vertical 9:16 MP4.
- FFmpeg/MoviePy assembly.
- A GitHub Actions workflow that can be run manually and is scheduled weekly. It uploads the MP4 as an artifact for review.

## Important quality limitation
This first zero-cost renderer creates simple 2.5D/illustrated mascot animation with procedural movement. It does NOT yet create the fully realistic 3D CGI characters, detailed skin macro simulation, or advanced character lip-sync shown in the Instagram reference. No free unlimited text-to-video provider is assumed. The purpose is to validate a reproducible zero-cost pipeline before spending money.

## How to run
1. Open the repository Actions tab.
2. Select Wonder Telugu Free Health Reel.
3. Choose Run workflow.
4. Wait for the run to finish.
5. Download the wonder-telugu-health-reel artifact and review the MP4.

The weekly schedule also creates an artifact automatically; it does not publish anything.

## Cost and publishing safety
- No Kling, Replicate, paid API, or paid credit is used by this workflow.
- GitHub Actions usage is subject to GitHub account/plan limits; public repository standard runners may be free within applicable limits.
- No automatic upload to YouTube, Facebook or Instagram is enabled. Review each video before publishing. Platform API access, permissions and policy requirements still apply.
- Health content must remain general education, not diagnosis or cure claims. Verify health facts before publishing.
