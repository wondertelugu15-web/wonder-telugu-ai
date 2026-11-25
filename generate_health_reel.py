from __future__ import annotations

import asyncio
import math
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import AudioFileClip, ImageSequenceClip, concatenate_videoclips
import edge_tts

W, H, FPS = 540, 960, 15
OUT = Path("wonder_telugu_health_reel.mp4")
ASSET = Path("build/health_reel")
AUDIO = ASSET / "audio"
FRAMES = ASSET / "frames"
VOICE = os.getenv("TELUGU_VOICE", "te-IN-ShrutiNeural")

SCENES = [
    ("చర్మం పొడిబారుతోందా?", "అయ్యో! నా చర్మం చాలా పొడిగా మారిపోయింది. ఏం చేయాలి?", "dry"),
    ("చర్మానికి తేమ అవసరం", "చర్మం పొడిగా ఉన్నప్పుడు మృదువైన మాయిశ్చరైజర్ ఉపయోగపడుతుంది.", "skin"),
    ("షియా బట్టర్ ఏమి చేస్తుంది?", "షియా బట్టర్ చర్మంలో తేమ నిలవడానికి సహాయపడే మాయిశ్చరైజర్ పదార్థం.", "butter"),
    ("చిన్న జాగ్రత్త", "కొత్త ఉత్పత్తి వాడే ముందు చిన్న భాగంలో పరీక్షించండి. మంట లేదా దురద వస్తే ఆపండి.", "care"),
    ("ఎప్పుడు డాక్టర్‌ను కలవాలి?", "పొడిబారడం, దురద లేదా పగుళ్లు తగ్గకపోతే చర్మ వైద్యుడిని సంప్రదించండి.", "doctor"),
    ("చర్మ సంరక్షణ గుర్తుంచుకోండి", "ఈ సమాచారం ఉపయోగపడితే Wonder Teluguని ఫాలో అవ్వండి. ఆరోగ్యంగా ఉండండి!", "happy"),
]

def font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansTeluguUI-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for item in candidates:
        if Path(item).exists():
            return ImageFont.truetype(item, size)
    return ImageFont.load_default()

def gradient_bg(kind: str):
    im = Image.new("RGB", (W, H))
    px = im.load()
    top = (190, 112, 83) if kind in ("dry", "skin") else (210, 154, 105)
    bottom = (245, 202, 160)
    for y in range(H):
        t = y / (H - 1)
        c = tuple(int(top[i] * (1-t) + bottom[i] * t) for i in range(3))
        for x in range(W):
            px[x, y] = c
    # soft skin-like rounded texture
    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    for i in range(16):
        x = (i * 173) % W
        y = (i * 251) % H
        d.ellipse((x-100,y-55,x+100,y+55), fill=(255,220,190,22))
    overlay = overlay.filter(ImageFilter.GaussianBlur(35))
    return Image.alpha_composite(im.convert("RGBA"), overlay)

def draw_mascot(im, kind, t):
    d = ImageDraw.Draw(im)
    cx, cy = W//2, 690 + int(math.sin(t*4)*12)
    # soft shadow
    d.ellipse((cx-155,cy+175,cx+155,cy+225), fill=(90,45,35,70))
    if kind == "butter":
        # butter dollop mascot
        d.ellipse((cx-135,cy-110,cx+135,cy+150), fill=(255,219,105,255), outline=(189,129,43,255), width=8)
        d.ellipse((cx-95,cy-140,cx+75,cy+35), fill=(255,238,166,255))
        body=(255,215,92,255)
    elif kind == "dry":
        # cracked dry-skin creature
        d.rounded_rectangle((cx-130,cy-125,cx+130,cy+145), radius=85, fill=(166,79,65,255), outline=(105,48,45,255), width=9)
        for dx in [-65,0,70]:
            d.line((cx+dx,cy-90,cx+dx-18,cy-35,cx+dx+12,cy+10), fill=(95,45,42,255), width=8)
        body=(166,79,65,255)
    elif kind == "happy":
        d.ellipse((cx-140,cy-130,cx+140,cy+150), fill=(255,178,75,255), outline=(176,94,45,255), width=8)
        body=(255,178,75,255)
    else:
        d.ellipse((cx-135,cy-125,cx+135,cy+145), fill=(238,147,108,255), outline=(155,78,61,255), width=8)
        body=(238,147,108,255)
    # glossy highlight
    d.ellipse((cx-88,cy-95,cx-30,cy-45), fill=(255,255,255,95))
    # eyes
    blink = (int(t*2) % 7 == 0)
    for ex in [cx-48,cx+48]:
        if blink:
            d.arc((ex-19,cy-25,ex+19,cy+8), 10,170, fill=(55,38,35,255), width=7)
        else:
            d.ellipse((ex-19,cy-35,ex+19,cy+12), fill=(255,255,255,255))
            d.ellipse((ex-8,cy-24,ex+9,cy+6), fill=(38,35,32,255))
            d.ellipse((ex-3,cy-22,ex+3,cy-15), fill=(255,255,255,255))
    # mouth and cheeks
    d.arc((cx-34,cy+18,cx+34,cy+75), 10,170, fill=(75,35,35,255), width=7)
    d.ellipse((cx-105,cy+15,cx-72,cy+39), fill=(255,130,130,110))
    d.ellipse((cx+72,cy+15,cx+105,cy+39), fill=(255,130,130,110))
    # tiny arms
    arm_y=cy+40
    d.line((cx-120,arm_y,cx-190,arm_y-35-int(8*math.sin(t*4))), fill=body, width=24)
    d.ellipse((cx-205,arm_y-55-int(8*math.sin(t*4)),cx-170,arm_y-20-int(8*math.sin(t*4))), fill=body)
    d.line((cx+120,arm_y,cx+190,arm_y-35+int(8*math.sin(t*4))), fill=body, width=24)
    d.ellipse((cx+170,arm_y-55+int(8*math.sin(t*4)),cx+205,arm_y-20+int(8*math.sin(t*4))), fill=body)

def wrap_text(draw, text, fnt, max_width):
    words=text.split()
    lines=[]; cur=""
    for word in words:
        test=(cur+" "+word).strip()
        if draw.textbbox((0,0),test,font=fnt)[2] <= max_width:
            cur=test
        else:
            if cur: lines.append(cur)
            cur=word
    if cur: lines.append(cur)
    return lines

def make_frame(title, dialogue, kind, t):
    im=gradient_bg(kind)
    draw_mascot(im,kind,t)
    d=ImageDraw.Draw(im)
    # top label
    d.rounded_rectangle((36,42,W-36,145), radius=28, fill=(50,35,31,195), outline=(255,255,255,80), width=2)
    tf=font(34)
    lines=wrap_text(d,title,tf,W-100)
    y=64
    for line in lines[:2]:
        box=d.textbbox((0,0),line,font=tf)
        d.text(((W-(box[2]-box[0]))//2,y),line,font=tf,fill=(255,255,255,255),stroke_width=1,stroke_fill=(40,20,20,255))
        y+=52
    # dialogue subtitle panel
    d.rounded_rectangle((34,1010,W-34,1215), radius=30, fill=(30,24,22,220))
    sf=font(26)
    lines=wrap_text(d,dialogue,sf,W-100)
    y=1045
    for line in lines[:4]:
        box=d.textbbox((0,0),line,font=sf)
        d.text(((W-(box[2]-box[0]))//2,y),line,font=sf,fill=(255,255,255,255))
        y+=43
    d.text((38,1230),"Wonder Telugu • ఆరోగ్య సమాచారం",font=font(16),fill=(255,255,255,220))
    return im.convert("RGB")

async def make_audio(index, text, path):
    if path.exists() and path.stat().st_size > 1000:
        return
    communicate=edge_tts.Communicate(text, VOICE, rate="+0%")
    await communicate.save(str(path))

def main():
    ASSET.mkdir(parents=True,exist_ok=True); AUDIO.mkdir(parents=True,exist_ok=True); FRAMES.mkdir(parents=True,exist_ok=True)
    audio_paths=[]
    for i,(_,dialogue,_) in enumerate(SCENES,1):
        p=AUDIO/f"scene_{i:02d}.mp3"
        asyncio.run(make_audio(i,dialogue,p))
        audio_paths.append(p)
    clips=[]; audios=[]
    try:
        for i,(title,dialogue,kind) in enumerate(SCENES,1):
            audio=AudioFileClip(str(audio_paths[i-1])); audios.append(audio)
            duration=max(4.5,audio.duration+0.4)
            frame_list=[]
            count=max(1,int(duration*FPS))
            for j in range(count):
                frame=make_frame(title,dialogue,kind,j/FPS)
                frame_list.append(__import__("numpy").array(frame))
            clip=ImageSequenceClip(frame_list,fps=FPS).with_duration(duration).with_audio(audio)
            clips.append(clip)
        final=concatenate_videoclips(clips,method="compose")
        final.write_videofile(str(OUT),fps=FPS,codec="libx264",audio_codec="aac",preset="ultrafast",threads=2,logger="bar")
        final.close()
    finally:
        for c in clips:
            try: c.close()
            except Exception: pass
        for a in audios:
            try: a.close()
            except Exception: pass
    print(f"Created {OUT}")

if __name__=="__main__":
    main()
