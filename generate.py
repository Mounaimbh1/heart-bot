#!/usr/bin/env python3
"""Crystal Narrator - Cinematic Story Video Generator."""
import asyncio
import json
import os
import pathlib
import random
import re
import subprocess
import sys
import time
import wave
from urllib.parse import quote

import numpy as np
import requests
from PIL import Image, ImageEnhance

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "output"
HISTORY = ROOT / "history.json"
W, H, FPS = 1080, 1920, 30
SELFTEST = "--selftest" in sys.argv

PAGE_NAME = os.environ.get("PAGE_NAME", "The Masked Truth")
VOICES = ["en-US-AndrewNeural", "en-GB-RyanNeural", "en-US-BrianNeural"]

CHARACTER_LOCK = (
    "a mysterious young man wearing a full-head silver rhinestone crystal-studded balaclava mask "
    "with open eye holes showing piercing green eyes and a distinct open mouth hole, "
    "wearing a dark charcoal black hooded athletic zip-up jacket"
)

ENVIRONMENTS = [
    "a dimly lit luxury wooden study office at night with a warm desk lamp and bookshelves",
    "a quiet rocky cliff overlooking a calm blue ocean at golden sunset",
    "a misty mountain peak above the clouds during early morning twilight",
    "a rain-slicked neon-lit city street at night with soft bokeh lights in the background",
    "a cozy modern living room with warm fireplace glow and rain on the window",
    "an ancient atmospheric library with tall wooden shelves and soft rays of sunlight",
    "a high-rise rooftop balcony overlooking a sparkling city skyline at dusk",
    "a quiet vintage cafe corner by a foggy window with warm ambient lighting",
    "a serene pine forest path with golden sunbeams filtering through tall trees",
    "a minimalist dark studio podcast setup with a professional microphone and warm rim light",
]

THEMES = [
    "a psychological truth nobody talks about",
    "a mysterious real-life coincidence that saved a life",
    "the silent rule of human trust and betrayal",
    "a hidden lesson behind a stranger's small act of kindness",
    "why the quietest person in the room notices everything",
    "a haunting letter found decades after it was written",
    "the moment someone realizes they took love for granted",
    "an unexplained mystery from a small coastal town",
    "how one decision changed two lives forever",
    "a forgotten promise kept after thirty years",
]

MOODS = ["mysterious", "sad", "hopeful", "tense", "warm"]
CHORDS = {
    "sad": [110.0, 130.81, 164.81, 220.0],
    "hopeful": [130.81, 164.81, 196.0, 246.94],
    "tense": [73.42, 110.0, 155.56, 220.0],
    "warm": [87.31, 110.0, 130.81, 174.61],
    "mysterious": [98.0, 116.54, 138.59, 196.0],
}
MOOD_COLORS = {
    "sad": (35, 50, 80), "hopeful": (85, 70, 45), "tense": (65, 30, 35),
    "warm": (95, 60, 35), "mysterious": (45, 35, 75),
}


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(map(str, cmd))[:200]}\n{r.stderr[-1500:]}")
    return r.stdout


def media_duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.strip())


def load_history():
    try:
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    except Exception:
        return []
def build_prompt(theme, environment, recent):
    return f"""You are a viral mysterious storyteller like Mr. Shelby for "{PAGE_NAME}".
Write ONE gripping, realistic, emotional or mysterious story narrated in ~55 seconds (135-155 words).
Theme: {theme}
Setting for all scenes: {environment}

Strict Rules:
- Open with a powerful hook that stops people from scrolling immediately.
- Tell a story or psychological truth that people want to share with family and friends.
- End with a memorable twist or deep realization in the last 2 scenes.
- Natural spoken English, short rhythmic sentences.
- Do NOT repeat recent titles: {recent}
- Split into 7 scenes. Each scene: 1-2 sentences of narration.
- Every "image_prompt" MUST describe the masked narrator ({CHARACTER_LOCK}) inside {environment}, showing varied camera angles (close-up on eyes, medium shot, side profile, thoughtful expression, gesturing) while keeping the exact same setting and character.
- NEVER include text, words, or pitch-black darkness in any image_prompt.
- "mood": one of {", ".join(MOODS)}.

Return ONLY valid JSON:
{{"title": str, "caption": str (max 135 chars, ends with a question),
"hashtags": [5 strings],
"scenes": [{{"narration": str, "image_prompt": str, "mood": str}}]}}"""


def extract_json(text):
    text = text.strip()
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b == -1:
        raise ValueError("no JSON found")
    return json.loads(text[a:b + 1])


def ask_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("no Gemini key")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://googleapis.com{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9}}
    r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def ask_pollinations(prompt):
    body = {"model": "openai", "seed": random.randint(1, 10**6),
            "messages": [{"role": "system", "content": "Reply with valid JSON only."},
                         {"role": "user", "content": prompt}]}
    r = requests.post("https://pollinations.ai", json=body, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"Pollinations HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"]


def generate_story(theme, environment, recent):
    prompt = build_prompt(theme, environment, recent)
    providers = [("gemini", ask_gemini), ("pollinations", ask_pollinations)]
    last = None
    for attempt in range(3):
        for name, fn in providers:
            try:
                story = extract_json(fn(prompt))
                assert isinstance(story.get("scenes"), list) and len(story["scenes"]) >= 4
                for sc in story["scenes"]:
                    assert sc.get("narration") and sc.get("image_prompt")
                    if sc.get("mood") not in MOODS:
                        sc["mood"] = "mysterious"
                story.setdefault("title", "Untitled")
                story.setdefault("caption", "")
                story.setdefault("hashtags", [])
                print(f"story from {name}")
                return story
            except Exception as e:
                last = f"{name}: {e}"
                print("story retry ->", last)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"All text providers failed. Last: {last}")


async def _tts(text, voice, path):
    import edge_tts
    natural = re.sub(r"\.\s+", "... ", text.strip())
    await edge_tts.Communicate(natural, voice, rate="-7%", pitch="-2Hz").save(str(path))


def make_voice(text, voice, path):
    if SELFTEST:
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=d=3.5:c=pink:a=0.02",
             "-ar", "24000", "-ac", "1", str(path)])
        return
    for attempt in range(3):
        try:
            asyncio.run(_tts(text, voice, path))
            if pathlib.Path(path).stat().st_size > 1000:
                return
        except Exception as e:
            print("tts retry:", e)
        time.sleep(3)
    raise RuntimeError("TTS failed")
def is_valid_bright_image(img):
    arr = np.asarray(img.convert("L"), dtype=np.float32)
    return float(np.mean(arr)) > 18.0 and float(np.std(arr)) > 12.0


def save_cropped_9_16(raw_bytes, path):
    tmp = pathlib.Path(path).with_suffix(".raw")
    tmp.write_bytes(raw_bytes)
    try:
        img = Image.open(tmp).convert("RGB")
        if not is_valid_bright_image(img):
            raise ValueError("Image too dark")
        tw, th = 1080, 1920
        scale = max(tw / img.width, th / img.height)
        img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.Resampling.LANCZOS)
        left, top = (img.width - tw) // 2, (img.height - th) // 2
        img = img.crop((left, top, left + tw, top + th))
        img = ImageEnhance.Contrast(img).enhance(1.06)
        img = ImageEnhance.Color(img).enhance(1.08)
        img.save(path, quality=94)
        return True
    finally:
        tmp.unlink(missing_ok=True)


def make_image(prompt, environment, mood, path, seed):
    if SELFTEST:
        Image.new("RGB", (1080, 1920), MOOD_COLORS.get(mood, (50, 45, 65))).save(path, quality=92)
        return
    base_style = "photorealistic 35mm cinema still, sharp focus on silver crystal mask sparkles, natural lighting, 8k, no text"
    prompts = [
        f"{prompt}, {base_style}"[:380],
        f"Medium portrait of {CHARACTER_LOCK} in {environment}, {base_style}"[:380],
    ]
    for attempt in range(6):
        p = prompts[0] if attempt < 4 else prompts[1]
        model = "flux" if attempt < 4 else "turbo"
        url = f"https://pollinations.ai{quote(p)}?width=768&height=1344&nologo=true&seed={seed + attempt * 13}&model={model}"
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                if save_cropped_9_16(r.content, path):
                    return
        except Exception as e:
            print(f"img retry {attempt + 1}:", e)
        time.sleep(3)
    try:
        r = requests.get(f"https://picsum.photos{seed}/1080/1920", timeout=45)
        if r.status_code == 200 and save_cropped_9_16(r.content, path):
            return
    except Exception:
        pass
    Image.new("RGB", (1080, 1920), MOOD_COLORS.get(mood, (50, 45, 65))).save(path, quality=92)


def make_music(moods, durs, path, sr=44100):
    xf = 1.0
    total = sum(durs)
    buf = np.zeros(int(sr * (total + 2 * xf)))
    pos = 0.0
    for mood, d in zip(moods, durs):
        t = np.arange(int(sr * (d + xf))) / sr
        sig = np.zeros_like(t)
        for i, f in enumerate(CHORDS.get(mood, CHORDS["mysterious"])):
            for det in (-0.35, 0.0, 0.35):
                sig += np.sin(2 * np.pi * (f + det) * t + i) / (1 + 0.4 * i)
        sig /= (np.max(np.abs(sig)) + 1e-9)
        ramp = np.linspace(0, 1, int(sr * xf))
        env = np.ones(len(sig))
        env[:len(ramp)] = ramp
        env[-len(ramp):] = ramp[::-1]
        start = int(sr * max(0.0, pos - xf / 2))
        buf[start:start + len(sig)] += sig * env
        pos += d
    buf = buf[:int(sr * total)]
    buf = buf / (np.max(np.abs(buf)) + 1e-9) * 0.55
    fade = int(sr * 1.5)
    buf[:fade] *= np.linspace(0, 1, fade)
    buf[-fade:] *= np.linspace(1, 0, fade)
    stereo = np.stack([buf, np.roll(buf, 260)], axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((stereo * 32767).astype(np.int16).tobytes())


def ass_time(s):
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def make_ass(text, total, path):
    words = text.replace("{", "").replace("}", "").split()
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 4 or (w[-1] in ".!?," and len(cur) >= 2):
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    weight = sum(len(c) for c in chunks) or 1
    usable = max(1.0, total - 0.45)
    t = 0.1
    lines = []
    for c in chunks:
        d = usable * len(c) / weight
        lines.append(f"Dialogue: 0,{ass_time(t)},{ass_time(t + d)},Main,,0,0,0,,{c}")
        t += d
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Main,DejaVu Sans,62,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,5,2,2,70,70,360,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    pathlib.Path(path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def render_scene(work, i, text, total):
    frames = max(1, int(total * FPS))
    mode = i % 3
    if mode == 0:
        zoom, x_expr = f"1.02+0.12*on/{frames}", "iw/2-(iw/zoom/2)"
    elif mode == 1:
        zoom, x_expr = f"1.14-0.12*on/{frames}", "iw/2-(iw/zoom/2)"
    else:
        zoom, x_expr = "1.10", f"(iw-iw/zoom)*(on/{frames})"
    make_ass(text, total, work / f"s{i}.ass")
    vf = (
        "scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
        f"zoompan=z='{zoom}':x='{x_expr}':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
        f"eq=contrast=1.04:saturation=1.06,subtitles=s{i}.ass,format=yuv420p"
    )
    run(["ffmpeg", "-y", "-i", f"img{i}.jpg", "-i", f"voice{i}.mp3",
         "-vf", vf, "-af", f"apad=whole_dur={total:.3f},aresample=44100",
         "-t", f"{total:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "fast", "-crf", "20",
         "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", f"clip{i}.mp4"], cwd=work)


def make_video(idx, story, environment, out_path):
    work = OUT / f"work{idx}"
    work.mkdir(parents=True, exist_ok=True)
    voice = VOICES[idx % len(VOICES)]
    durs, moods = [], []
    seed_base = random.randint(1, 10**6)
    for i, sc in enumerate(story["scenes"]):
        make_voice(sc["narration"], voice, work / f"voice{i}.mp3")
        total = media_duration(work / f"voice{i}.mp3") + 0.50
        durs.append(total)
        moods.append(sc["mood"])
        make_image(sc["image_prompt"], environment, sc["mood"], work / f"img{i}.jpg", seed_base + i)
        render_scene(work, i, sc["narration"], total)
        time.sleep(1 if SELFTEST else 2)
    (work / "list.txt").write_text("".join(f"file 'clip{i}.mp4'\n" for i in range(len(story["scenes"]))))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "joined.mp4"], cwd=work)
    make_music(moods, durs, work / "music.wav")
    total_len = sum(durs)
    fc = ("[1:a]lowpass=f=850,volume=0.13[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
          f"loudnorm=I=-15:TP=-1.5:LRA=9,afade=t=out:st={max(0, total_len - 1.2):.2f}:d=1.2[a];"
          f"[0:v]fade=t=in:st=0:d=0.4,fade=t=out:st={max(0, total_len - 0.7):.2f}:d=0.7[v]")
    run(["ffmpeg", "-y", "-i", "joined.mp4", "-i", "music.wav", "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-crf", "21",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out_path)], cwd=work)
    return total_len


def tg(method, **kw):  
return requests.post(f"https://telegram.org{os.environ['TELEGRAM_BOT_TOKEN']}/{method}", timeout=300, **kw)


def send_video(path, caption):
    with open(path, "rb") as f:
        r = tg("sendVideo", data={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "caption": caption[:1000],
                                  "supports_streaming": "true", "width": W, "height": H}, files={"video": f})
    if r.status_code != 200:
        raise RuntimeError(f"Telegram error: {r.text[:300]}")


def send_text(text):
    tg("sendMessage", data={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text[:4000]})


def main():
    OUT.mkdir(exist_ok=True)
    if SELFTEST:
        fake = {"title": "Test", "caption": "Test?", "hashtags": ["#test"],
                "scenes": [{"narration": "Some truths stay hidden until the right moment.", "image_prompt": "x", "mood": "mysterious"}]}
        print("OK", make_video(0, fake, ENVIRONMENTS[0], OUT / "selftest.mp4"))
        return
    history = load_history()
    recent = [h["title"] for h in history[-40:]]
    n = int(os.environ.get("VIDEOS_PER_RUN", "3"))
    themes = random.sample(THEMES, n)
    envs = random.sample(ENVIRONMENTS, min(n, len(ENVIRONMENTS)))
    made, errors = [], []
    for k in range(n):
        try:
            story = generate_story(themes[k], envs[k % len(envs)], recent)
            path = OUT / f"video{k + 1}.mp4"
            length = make_video(k, story, envs[k % len(envs)], path)
            caption = f"Option {k + 1} | {story['title']} ({length:.0f}s)\n\n{story['caption']}\n{' '.join(story['hashtags'])}"
            made.append((path, caption))
            history.append({"title": story["title"], "date": time.strftime("%Y-%m-%d")})
            recent.append(story["title"])
        except Exception as e:
            print(f"video {k + 1} failed: {e}")
            errors.append(f"video {k + 1}: {str(e)[:300]}")
    HISTORY.write_text(json.dumps(history[-200:], ensure_ascii=False, indent=1), encoding="utf-8")
    if made:
        send_text(f"Today's {len(made)} Crystal Narrator videos are ready:")
        for path, caption in made:
            send_video(path, caption)
    if errors:
        send_text("Errors:\n" + "\n".join(errors))
    if not made:
        sys.exit(1)


if __name__ == "__main__":
    main()
