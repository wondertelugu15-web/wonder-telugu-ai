from __future__ import annotations
import asyncio, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import AudioFileClip, ImageSequenceClip, concatenate_videoclips
import edge_tts

W,H,FPS=540,960,15
OUT=Path("wonder_telugu_health_reel.mp4")
AUDIO=Path("build/health_reel/audio")
VOICE="te-IN-ShrutiNeural"
SCENES=[
("చర్మం పొడిబారుతోందా?","అయ్యో! నా చర్మం చాలా పొడిగా మారిపోయింది. ఏం చేయాలి?","dry"),
("చర్మానికి తేమ అవసరం","చర్మం పొడిగా ఉన్నప్పుడు మృదువైన మాయిశ్చరైజర్ ఉపయోగపడుతుంది.","skin"),
("షియా బట్టర్ ఏమి చేస్తుంది?","షియా బట్టర్ చర్మంలో తేమ నిలవడానికి సహాయపడే పదార్థం.","butter"),
("ముందుగా పరీక్షించండి","కొత్త ఉత్పత్తిని చిన్న భాగంలో పరీక్షించండి. మంట లేదా దురద వస్తే వాడటం ఆపండి.","care"),
("ఎప్పుడు డాక్టర్‌ను కలవాలి?","పొడిబారడం, దురద లేదా పగుళ్లు తగ్గకపోతే చర్మ వైద్యుడిని సంప్రదించండి.","doctor"),
("చర్మ సంరక్షణ గుర్తుంచుకోండి","ఈ సమాచారం ఉపయోగపడితే Wonder Teluguని ఫాలో అవ్వండి. ఆరోగ్యంగా ఉండండి!","happy"),
]
def font(n):
    for p in ["/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf","/usr/share/fonts/truetype/noto/NotoSansTeluguUI-Regular.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(p).exists(): return ImageFont.truetype(p,n)
    return ImageFont.load_default()
def background(kind):
    palettes={"dry":((112,57,49),(222,151,119)),"skin":((125,69,52),(230,174,140)),"butter":((110,66,38),(235,187,112)),"care":((99,62,47),(221,165,126)),"doctor":((82,61,54),(207,163,139)),"happy":((104,65,42),(235,182,116))}
    a,b=palettes[kind]; yy,xx=np.mgrid[0:H,0:W]; yy=yy/H
    arr=np.zeros((H,W,3),dtype=np.uint8)
    for c in range(3): arr[:,:,c]=(a[c]*(1-yy)+b[c]*yy).astype(np.uint8)
    dist=((xx-W*.5)/(W*.75))**2+((yy*H-H*.55)/(H*.8))**2
    arr=np.clip(arr.astype(float)+(np.exp(-dist*2.4)*23-dist*12)[:,:,None],0,255).astype(np.uint8)
    im=Image.fromarray(arr).convert("RGBA")
    tex=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(tex)
    for k in range(80):
        x=(k*97+31)%W; y=(k*173+71)%H; r=3+k%9
        d.ellipse((x-r,y-r,x+r,y+r),fill=(255,211,185,10))
    return Image.alpha_composite(im,tex.filter(ImageFilter.GaussianBlur(5)))
def sphere(d,cx,cy,rx,ry,base,outline):
    d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=base,outline=outline,width=5)
    d.ellipse((cx-rx*.68,cy-ry*.82,cx+rx*.45,cy+ry*.12),fill=(255,255,255,48))
    d.ellipse((cx-rx*.75,cy+ry*.42,cx+rx*.8,cy+ry*1.02),fill=(55,25,20,28))
def mascot(im,kind,t):
    d=ImageDraw.Draw(im); cx=W//2; cy=565+int(7*math.sin(t*2.8))
    d.ellipse((cx-155,cy+155,cx+155,cy+204),fill=(42,24,20,80))
    colors={"dry":(164,83,67,255),"skin":(227,151,115,255),"butter":(246,199,91,255),"care":(222,147,102,255),"doctor":(213,151,117,255),"happy":(241,169,74,255)}
    base=colors[kind]; sphere(d,cx,cy,132,142,base,(112,62,48,255))
    wave=int(12*math.sin(t*3.2))
    for s in (-1,1):
        ax=cx+s*119; hx=cx+s*(187+wave)
        d.line((ax,cy+42,hx,cy-8),fill=base,width=25)
        d.ellipse((hx-17,cy-26,hx+17,cy+10),fill=base)
    blink=int(t*2.1)%9==0
    for ex in (cx-48,cx+48):
        if blink: d.arc((ex-18,cy-34,ex+18,cy+8),5,175,fill=(54,34,30,255),width=7)
        else:
            d.ellipse((ex-20,cy-40,ex+20,cy+12),fill="white")
            d.ellipse((ex-9,cy-27,ex+10,cy+7),fill=(35,30,28,255))
            d.ellipse((ex-5,cy-25,ex+1,cy-18),fill="white")
    if int(t*5)%3==0: d.ellipse((cx-23,cy+35,cx+23,cy+68),fill=(91,39,38,255))
    else: d.arc((cx-34,cy+30,cx+34,cy+76),5,175,fill=(91,39,38,255),width=7)
    d.ellipse((cx-104,cy+17,cx-72,cy+39),fill=(255,119,124,105)); d.ellipse((cx+72,cy+17,cx+104,cy+39),fill=(255,119,124,105))
    if kind=="dry":
        for dx in (-60,15,62): d.line((cx+dx,cy-91,cx+dx-14,cy-49,cx+dx+8,cy-15),fill=(103,48,43,220),width=5)
    if kind=="butter": d.arc((cx-68,cy-88,cx+66,cy+38),190,500,fill=(255,244,198,220),width=10)
def wrap(d,text,fnt,maxw):
    lines=[]; line=""
    for word in text.split():
        trial=(line+" "+word).strip()
        if d.textbbox((0,0),trial,font=fnt)[2]<=maxw: line=trial
        else:
            if line: lines.append(line)
            line=word
    if line: lines.append(line)
    return lines
def frame(title,dialogue,kind,t):
    im=background(kind); mascot(im,kind,t); d=ImageDraw.Draw(im)
    d.rounded_rectangle((28,32,W-28,133),radius=25,fill=(37,25,23,220),outline=(255,232,216,160),width=2)
    tf=font(29); y=52
    for line in wrap(d,title,tf,W-78)[:2]:
        bb=d.textbbox((0,0),line,font=tf); d.text(((W-(bb[2]-bb[0]))//2,y),line,font=tf,fill="white",stroke_width=1,stroke_fill=(40,20,18)); y+=39
    d.rounded_rectangle((25,758,W-25,900),radius=24,fill=(30,23,21,228),outline=(255,255,255,70),width=2)
    sf=font(23); y=778
    for line in wrap(d,dialogue,sf,W-70)[:3]:
        bb=d.textbbox((0,0),line,font=sf); d.text(((W-(bb[2]-bb[0]))//2,y),line,font=sf,fill="white"); y+=34
    d.text((W-245,920),"WONDER TELUGU  •  HEALTH TIPS",font=font(13),fill=(255,245,236,220))
    return im.convert("RGB")
async def audio(text,path):
    if path.exists() and path.stat().st_size>1000: return
    await edge_tts.Communicate(text,VOICE,rate="+0%").save(str(path))
def main():
    AUDIO.mkdir(parents=True,exist_ok=True); clips=[]; audios=[]
    try:
        for i,scene in enumerate(SCENES,1):
            ap=AUDIO/f"scene_{i:02d}.mp3"; asyncio.run(audio(scene[1],ap))
            a=AudioFileClip(str(ap)); audios.append(a); duration=max(4.5,a.duration+.35); frames=[]
            for j in range(int(duration*FPS)): frames.append(np.asarray(frame(*scene,j/FPS)))
            clips.append(ImageSequenceClip(frames,fps=FPS).with_duration(duration).with_audio(a))
        final=concatenate_videoclips(clips,method="compose")
        final.write_videofile(str(OUT),fps=FPS,codec="libx264",audio_codec="aac",preset="medium",threads=2,logger="bar")
        final.close()
    finally:
        for c in clips:
            try:c.close()
            except:pass
        for a in audios:
            try:a.close()
            except:pass
    print(f"Created {OUT}")
if __name__=="__main__": main()
