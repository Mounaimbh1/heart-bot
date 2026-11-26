#!/usr/bin/env python3
"""Heart Awakening - Professional Cinematic 1-Minute Story Generator."""
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
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "output"
HISTORY = ROOT / "history.json"
W, H, FPS = 1080, 1920, 30
SELFTEST = "--selftest" in sys.argv

PAGE_NAME = os.environ.get("PAGE_NAME", "Heart Awakening")
VOICES = ["en-US-AndrewNeural", "en-GB-RyanNeural", "en-US-BrianNeural", "en-US-AriaNeural"]

THEMES = [
    "a letter that was never sent", "forgiving someone too late", "a mother's silent sacrifice",
    "a second chance at love", "the stranger who changed everything", "hidden pain behind a smile",
    "a promise kept after many years", "coming home after a long absence", "a friendship betrayed and healed",
    "the last conversation with a father", "a small kindness that returned a hundredfold",
    "learning to let go", "a child's innocent wisdom", "regret and a final chance to fix it",
]
STYLES = [
    "first-person emotional confession", "third-person cinematic narration", "a handwritten letter read aloud",
    "a vivid memory told by an elderly person", "a story opening right in the middle of a quiet turning point",
]
MOODS = ["sad", "hopeful", "tense", "warm", "mysterious", "joyful"]
CHORDS = {
    "sad": [110.0, 130.81, 164.81, 220.0],
    "hopeful": [130.81, 164.81, 196.0, 246.94],
    "tense": [73.42, 110.0, 155.56, 220.0],
    "warm": [87.31, 110.0, 130.81, 174.61],
    "mysterious": [98.0, 116.54, 138.59, 196.0],
    "joyful": [196.0, 246.94, 293.66, 392.0],
}
MOOD_COLORS = {
    "sad": (35, 50, 80), "hopeful": (85, 70, 45), "tense": (65, 30, 35),
    "warm": (95, 60, 35), "mysterious": (45, 35, 75), "joyful": (95, 80, 40),
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


def build_prompt(theme, style, recent):
    return f"""You are a master cinematic storyteller for "{PAGE_NAME}".
Write ONE deeply emotional, realistic story narrated in ~55-60 seconds (135-155 words total).
Theme: {theme}
Style: {style}

Strict Rules:
- Start with an irresistible emotional hook in the first sentence.
- Build tension naturally to a touching, unforgettable twist in the final 2 scenes.
- Write in natural, human spoken English. Use short, rhythmic sentences with natural pauses.
- Avoid recent stories: {recent}
- Split into 8 scenes. Each scene: 1-2 sentences of narration.
- "character_look": clear, realistic physical description of the main person (e.g., "a 28-year-old woman with dark hair in a beige trench coat" or "a 70-year-old grandfather with silver hair and a knitted cardigan").
- "visual_style": "photorealistic 35mm movie still, natural cinematic lighting, shallow depth of field, warm film grain, emotional expression".
- "image_prompt": describe ONLY physical subjects, facial expressions, and real-world scenery in that exact moment. NEVER ask for text, letters with readable words, signs, or dark/black rooms. Always ensure well-lit, visible cinematic scenes.
- "mood": one of {", ".join(MOODS)}.

Return ONLY valid JSON:
{{"title": str, "caption": str (max 135 chars, ends with a thoughtful question),
"hashtags": [5 strings], "character_look": str, "visual_style": str,
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
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.95}}
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
def gemini_story(theme, style, recent):
    prompt = build_prompt(theme, style, recent)
    providers = [("gemini", ask_gemini), ("pollinations", ask_pollinations)]
    last = None
    for attempt in range(3):
        for name, fn in providers:
            try:
                story = extract_json(fn(prompt))
                validate_story(story)
                print(f"story from {name}")
                return story
            except Exception as e:
                last = f"{name}: {e}"
                print("story retry ->", last)
        time.sleep(6 * (attempt + 1))
    raise RuntimeError(f"All text providers failed. Last: {last}")


def validate_story(s):
    assert isinstance(s.get("scenes"), list) and 4 <= len(s["scenes"]) <= 14, "bad scene count"
    for sc in s["scenes"]:
        assert sc.get("narration") and sc.get("image_prompt"), "empty scene"
        if sc.get("mood") not in MOODS:
            sc["mood"] = "warm"
    s.setdefault("title", "Untitled")
    s.setdefault("caption", "")
    s.setdefault("hashtags", [])
    s.setdefault("character_look", "realistic person in natural clothes")
    s.setdefault("visual_style", "photorealistic 35mm movie still, natural cinematic lighting, shallow depth of field")


def humanize_narration(text):
    text = text.strip()
    text = re.sub(r"\.\s+", "... ", text)
    text = re.sub(r",\s+", ", ", text)
    return text


async def _tts(text, voice, path):
    import edge_tts
    natural_text = humanize_narration(text)
    communicate = edge_tts.Communicate(natural_text, voice, rate="-8%", pitch="-2Hz")
    await communicate.save(str(path))


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
    mean_brightness = float(np.mean(arr))
    std_contrast = float(np.std(arr))
    return mean_brightness > 18.0 and std_contrast > 12.0


def clean_visual_prompt(prompt):
    banned = ["detonated", "explosion", "blood", "suicide", "kill", "dead", "corpse", "pitch black", "darkness", "text", "words", "letters written"]
    cleaned = prompt
    for b in banned:
        cleaned = re.sub(rf"\b{re.escape(b)}\b", "emotional moment", cleaned, flags=re.IGNORECASE)
    return cleaned[:380]


def save_cropped_9_16(raw_bytes, path):
    tmp = pathlib.Path(path).with_suffix(".raw")
    tmp.write_bytes(raw_bytes)
    try:
        img = Image.open(tmp).convert("RGB")
        if not is_valid_bright_image(img):
            raise ValueError("Image too dark or blank")
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


def make_image(prompt, mood, path, seed):
    if SELFTEST:
        img = Image.new("RGB", (1080, 1920), MOOD_COLORS.get(mood, (60, 50, 40)))
        img.save(path, quality=92)
        return

    safe_prompt = clean_visual_prompt(prompt)
    fallback_prompts = [
        safe_prompt,
        f"cinematic emotional portrait in soft golden hour sunlight, realistic 35mm photography, {mood} atmosphere",
        "cinematic scenic view of a quiet city street at sunset, warm natural light, photorealistic movie still",
    ]

    for attempt in range(6):
        current_prompt = fallback_prompts[min(attempt // 2, len(fallback_prompts) - 1)]
        model = "flux" if attempt < 4 else "turbo"
        url = (f"https://pollinations.ai{quote(current_prompt)}"
               f"?width=768&height=1344&nologo=true&seed={seed + attempt * 17}&model={model}")
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                if save_cropped_9_16(r.content, path):
                    return
        except Exception as e:
            print(f"image attempt {attempt + 1} retry:", e)
        time.sleep(3)

    try:
        r = requests.get(f"https://picsum.photos{seed}/1080/1920", timeout=45)
        if r.status_code == 200 and save_cropped_9_16(r.content, path):
            print("used real photo fallback")
            return
    except Exception as e:
        print("picsum fallback failed:", e)

    base = MOOD_COLORS.get(mood, (60, 50, 45))
    img = Image.new("RGB", (1080, 1920), base)
    img.save(path, quality=92)
def _pad(mood, dur, sr=44100):
    t = np.arange(int(sr * dur)) / sr
    sig = np.zeros_like(t)
    for i, f in enumerate(CHORDS.get(mood, CHORDS["warm"])):
        for det in (-0.35, 0.0, 0.35):
            sig += np.sin(2 * np.pi * (f + det) * t + i) / (1 + 0.4 * i)
        sig += 0.15 * np.sin(2 * np.pi * f * 2 * t)
    sig *= 0.88 + 0.12 * np.sin(2 * np.pi * 0.10 * t)
    return sig / (np.max(np.abs(sig)) + 1e-9)


def make_music(moods, durs, path, sr=44100):
    xf = 1.0
    total = sum(durs)
    buf = np.zeros(int(sr * (total + 2 * xf)))
    pos = 0.0
    for mood, d in zip(moods, durs):
        seg_d = d + xf
        seg = _pad(mood, seg_d, sr)
        n = len(seg)
        ramp = np.linspace(0, 1, int(sr * xf))
        env = np.ones(n)
        env[: len(ramp)] = ramp
        env[-len(ramp):] = ramp[::-1]
        start = int(sr * max(0.0, pos - xf / 2))
        buf[start:start + n] += seg * env
        pos += d
    buf = buf[: int(sr * total)]
    buf = buf / (np.max(np.abs(buf)) + 1e-9) * 0.55
    fade = int(sr * 1.8)
    buf[:fade] *= np.linspace(0, 1, fade)
    buf[-fade:] *= np.linspace(1, 0, fade)
    stereo = np.stack([buf, np.roll(buf, 260)], axis=1)
    data = (stereo * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


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
        zoom = f"1.02+0.12*on/{frames}"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif mode == 1:
        zoom = f"1.14-0.12*on/{frames}"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        zoom = "1.10"
        x_expr = f"(iw-iw/zoom)*(on/{frames})"
        y_expr = "ih/2-(ih/zoom/2)"

    make_ass(text, total, work / f"s{i}.ass")
    vf = (
        "scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
        f"zoompan=z='{zoom}':x='{x_expr}':y='{y_expr}':d={frames}:s={W}x{H}:fps={FPS},"
        "eq=contrast=1.04:saturation=1.06,"
        f"subtitles=s{i}.ass,format=yuv420p"
    )
    run(["ffmpeg", "-y", "-i", f"img{i}.jpg", "-i", f"voice{i}.mp3",
         "-vf", vf, "-af", f"apad=whole_dur={total:.3f},aresample=44100",
         "-t", f"{total:.3f}", "-r", str(FPS),
         "-c:v", "libx264", "-preset", "fast", "-crf", "20",
         "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", f"clip{i}.mp4"], cwd=work)


def make_video(idx, story, out_path):
    work = OUT / f"work{idx}"
    work.mkdir(parents=True, exist_ok=True)
    voice = VOICES[idx % len(VOICES)]
    scenes = story["scenes"]
    durs, moods = [], []
    seed_base = random.randint(1, 10**6)
    for i, sc in enumerate(scenes):
        make_voice(sc["narration"], voice, work / f"voice{i}.mp3")
        total = media_duration(work / f"voice{i}.mp3") + 0.50
        durs.append(total)
        moods.append(sc["mood"])
        full_prompt = (
            f'{sc["image_prompt"]}. Character: {story["character_look"]}. '
            f'Style: {story["visual_style"]}, well-lit scene, natural skin texture, vertical 9:16, strictly no text'
        )
        make_image(full_prompt, sc["mood"], work / f"img{i}.jpg", seed_base + i)
        render_scene(work, i, sc["narration"], total)
        time.sleep(1 if SELFTEST else 2)

    (work / "list.txt").write_text("".join(f"file 'clip{i}.mp4'\n" for i in range(len(scenes))))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "joined.mp4"], cwd=work)
    make_music(moods, durs, work / "music.wav")
    total_len = sum(durs)
    fc = ("[1:a]lowpass=f=900,volume=0.14[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
          f"loudnorm=I=-15:TP=-1.5:LRA=9,afade=t=out:st={max(0, total_len - 1.2):.2f}:d=1.2[a];"
          f"[0:v]fade=t=in:st=0:d=0.4,fade=t=out:st={max(0, total_len - 0.7):.2f}:d=0.7[v]")
    run(["ffmpeg", "-y", "-i", "joined.mp4", "-i", "music.wav", "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-crf", "21",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
         str(out_path)], cwd=work)
    return total_len


def tg(method, **kw):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return requests.post(f"https://telegram.org{token}/{method}", timeout=300, **kw)


def send_video(path, caption):
    chat = os.environ["TELEGRAM_CHAT_ID"]
    with open(path, "rb") as f:
        r = tg("sendVideo", data={"chat_id": chat, "caption": caption[:1000], "supports_streaming": "true",
                                  "width": W, "height": H}, files={"video": f})
    if r.status_code != 200:
        raise RuntimeError(f"Telegram error: {r.text[:300]}")


def send_text(text):
    tg("sendMessage", data={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text[:4000]})


FAKE_STORY = {
    "title": "Selftest", "caption": "Test?", "hashtags": ["#test"],
    "character_look": "", "visual_style": "",
    "scenes": [
        {"narration": "She kept the letter for twenty years. She never opened it.", "image_prompt": "x", "mood": "sad"},
        {"narration": "Then one rainy morning, everything changed.", "image_prompt": "x", "mood": "tense"},
        {"narration": "Some words find us exactly when we are ready.", "image_prompt": "x", "mood": "hopeful"},
    ],
}


def main():
    OUT.mkdir(exist_ok=True)
    if SELFTEST:
        out = OUT / "selftest.mp4"
        length = make_video(0, FAKE_STORY, out)
        print(f"OK selftest {out} {length:.1f}s")
        return
    history = load_history()
    recent = [h["title"] for h in history[-40:]]
    n = int(os.environ.get("VIDEOS_PER_RUN", "3"))
    themes = random.sample(THEMES, n)
    styles = random.sample(STYLES, min(n, len(STYLES)))
    made, errors = [], []
    for k in range(n):
        try:
            story = gemini_story(themes[k], styles[k % len(styles)], recent)
            path = OUT / f"video{k + 1}.mp4"
            length = make_video(k, story, path)
            tags = " ".join(story["hashtags"])
            caption = (f"Option {k + 1} | {story['title']} ({length:.0f}s)\n\n"
                       f"{story['caption']}\n{tags}\n\n"
                       f"(AI-generated story - remember to turn on the AI label when posting)")
            made.append((path, caption))
            history.append({"title": story["title"], "date": time.strftime("%Y-%m-%d")})
            recent.append(story["title"])
        except Exception as e:
            print(f"video {k + 1} failed: {e}")
            errors.append(f"video {k + 1}: {str(e)[:300]}")
    HISTORY.write_text(json.dumps(history[-200:], ensure_ascii=False, indent=1), encoding="utf-8")
    if made:
        send_text(f"Today's {len(made)} videos are ready. Pick the best one.")
        for path, caption in made:
            send_video(path, caption)
    if errors:
        send_text("Some videos failed:\n" + "\n".join(errors))
    if not made:
        sys.exit(1)


if __name__ == "__main__":
    main()
