#!/usr/bin/env python3
"""Heart Awakening - daily 1-minute story video generator."""
import asyncio
import json
import os
import pathlib
import random
import subprocess
import sys
import time
import wave
from urllib.parse import quote

import numpy as np
import requests
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "output"
HISTORY = ROOT / "history.json"
W, H, FPS = 720, 1280, 25
SELFTEST = "--selftest" in sys.argv

PAGE_NAME = os.environ.get("PAGE_NAME", "Heart Awakening")
VOICES = ["en-US-AndrewNeural", "en-US-AriaNeural", "en-GB-RyanNeural", "en-US-GuyNeural"]

THEMES = [
    "a letter that was never sent", "forgiving someone too late", "a mother's silent sacrifice",
    "a second chance at love", "the stranger who changed everything", "hidden pain behind a smile",
    "a promise kept after many years", "coming home after a long absence", "a friendship betrayed and healed",
    "the last conversation with a father", "a small kindness that returned a hundredfold",
    "learning to let go", "a child's innocent wisdom", "regret and a final chance to fix it",
]
STYLES = [
    "first-person confession", "third-person cinematic narration", "a letter read aloud",
    "a memory told by an old person", "a story that opens in the middle of a tense moment",
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
    "sad": (20, 30, 55), "hopeful": (60, 50, 30), "tense": (40, 15, 20),
    "warm": (70, 40, 20), "mysterious": (30, 20, 50), "joyful": (70, 60, 25),
}


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(map(str, cmd))[:200]}\n{r.stderr[-1500:]}")
    return r.stdout


def media_duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.strip())


# ---------------------------------------------------------------- script
def load_history():
    try:
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    except Exception:
        return []


def build_prompt(theme, style, recent):
    return f"""You are a award-winning short-form storyteller for a Facebook page called "{PAGE_NAME}"
whose tagline is "Stories that make you feel. Watch until the very end...".

Write ONE original emotional story that can be narrated in about 60 seconds (140-160 words total).
Theme: {theme}
Narrative style: {style}

Rules:
- The first sentence must be a strong hook that makes people keep watching.
- Build to an emotional twist or a bittersweet resolution in the last 2 scenes.
- Simple spoken English, short sentences, no cliches like "little did they know".
- Do NOT reuse these recent titles or their ideas: {recent}
- Split into 7 to 9 scenes. Each scene: 1-3 sentences of narration.
- "character_look": one fixed visual description of the main character(s) (age, hair, clothes) so images stay consistent.
- "visual_style": one fixed cinematic style line (lighting, color grade, lens) used for every image.
- Each "image_prompt" describes only what is visible in that scene (no text, no words in image).
- "mood" must be one of: {", ".join(MOODS)}.

Return ONLY JSON with this shape:
{{"title": str, "caption": str (max 140 chars, ends with a question to boost comments),
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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0}}
    r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def ask_pollinations(prompt):
    """Free, no API key needed."""
    body = {"model": "openai", "seed": random.randint(1, 10**6),
            "messages": [{"role": "system", "content": "You reply with JSON only."},
                         {"role": "user", "content": prompt}]}
    r = requests.post("https://text.pollinations.ai/openai", json=body, timeout=180)
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
            except Exception as e:  # noqa: BLE001
                last = f"{name}: {e}"
                print("story retry ->", last)
        time.sleep(8 * (attempt + 1))
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
    s.setdefault("character_look", "")
    s.setdefault("visual_style", "cinematic, soft light, shallow depth of field")


# ---------------------------------------------------------------- voice
async def _tts(text, voice, path):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate="-6%").save(str(path))


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
        except Exception as e:  # noqa: BLE001
            print("tts retry:", e)
        time.sleep(4)
    raise RuntimeError("TTS failed")


# ---------------------------------------------------------------- images
def fallback_image(mood, path):
    base = MOOD_COLORS.get(mood, (30, 30, 40))
    img = Image.new("RGB", (1080, 1920), base)
    d = ImageDraw.Draw(img)
    for y in range(1920):
        k = 1 - y / 1920 * 0.7
        d.line([(0, y), (1080, y)], fill=tuple(int(c * k) for c in base))
    img.save(path, quality=92)


def make_image(prompt, mood, path, seed):
    if SELFTEST:
        return fallback_image(mood, path)
    url = (f"https://image.pollinations.ai/prompt/{quote(prompt)}"
           f"?width=1080&height=1920&nologo=true&seed={seed}&model=flux")
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=150)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                tmp = pathlib.Path(path).with_suffix(".raw")
                tmp.write_bytes(r.content)
                img = Image.open(tmp).convert("RGB")
                tw, th = 1080, 1920
                scale = max(tw / img.width, th / img.height)
                img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1))
                left, top = (img.width - tw) // 2, (img.height - th) // 2
                img.crop((left, top, left + tw, top + th)).save(path, quality=92)
                tmp.unlink(missing_ok=True)
                return
        except Exception as e:  # noqa: BLE001
            print("image retry:", e)
        time.sleep(8 * (attempt + 1))
    print("image failed, using fallback gradient")
    fallback_image(mood, path)


# ---------------------------------------------------------------- music
def _pad(mood, dur, sr=44100):
    t = np.arange(int(sr * dur)) / sr
    sig = np.zeros_like(t)
    for i, f in enumerate(CHORDS.get(mood, CHORDS["warm"])):
        for det in (-0.5, 0.0, 0.5):
            sig += np.sin(2 * np.pi * (f + det) * t + i) / (1 + 0.3 * i)
        sig += 0.25 * np.sin(2 * np.pi * f * 2 * t)
    sig *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.12 * t)
    return sig / (np.max(np.abs(sig)) + 1e-9)


def make_music(moods, durs, path, sr=44100):
    xf = 0.8
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
    buf = buf / (np.max(np.abs(buf)) + 1e-9) * 0.7
    fade = int(sr * 1.5)
    buf[:fade] *= np.linspace(0, 1, fade)
    buf[-fade:] *= np.linspace(1, 0, fade)
    stereo = np.stack([buf, np.roll(buf, 220)], axis=1)
    data = (stereo * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


# ---------------------------------------------------------------- render
def ass_time(s):
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def make_ass(text, total, path):
    words = text.replace("{", "").replace("}", "").split()
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 5 or (w[-1] in ".!?," and len(cur) >= 3):
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    weight = sum(len(c) for c in chunks) or 1
    usable = max(1.0, total - 0.5)
    t = 0.1
    lines = []
    for c in chunks:
        d = usable * len(c) / weight
        lines.append(f"Dialogue: 0,{ass_time(t)},{ass_time(t + d)},Main,,0,0,0,,{c}")
        t += d
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Main,DejaVu Sans,44,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,50,50,250,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    pathlib.Path(path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def render_scene(work, i, text, total):
    frames = max(1, int(total * FPS))
    zoom = f"1+0.18*on/{frames}" if i % 2 == 0 else f"1.18-0.18*on/{frames}"
    make_ass(text, total, work / f"s{i}.ass")
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
        f"subtitles=s{i}.ass,format=yuv420p"
    )
    run(["ffmpeg", "-y", "-i", f"img{i}.jpg", "-i", f"voice{i}.mp3",
         "-vf", vf, "-af", f"apad=whole_dur={total:.3f},aresample=44100",
         "-t", f"{total:.3f}", "-r", str(FPS),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
         "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k", f"clip{i}.mp4"], cwd=work)


def make_video(idx, story, out_path):
    work = OUT / f"work{idx}"
    work.mkdir(parents=True, exist_ok=True)
    voice = VOICES[idx % len(VOICES)]
    scenes = story["scenes"]
    durs, moods = [], []
    seed_base = random.randint(1, 10**6)
    for i, sc in enumerate(scenes):
        make_voice(sc["narration"], voice, work / f"voice{i}.mp3")
        total = media_duration(work / f"voice{i}.mp3") + 0.55
        durs.append(total)
        moods.append(sc["mood"])
        full_prompt = f'{sc["image_prompt"]}. {story["character_look"]}. {story["visual_style"]}. vertical 9:16, no text, no watermark'
        make_image(full_prompt, sc["mood"], work / f"img{i}.jpg", seed_base + i)
        render_scene(work, i, sc["narration"], total)
        time.sleep(1 if SELFTEST else 3)

    (work / "list.txt").write_text("".join(f"file 'clip{i}.mp4'\n" for i in range(len(scenes))))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "joined.mp4"], cwd=work)
    make_music(moods, durs, work / "music.wav")
    total_len = sum(durs)
    fc = ("[1:a]volume=0.20[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
          f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st={max(0, total_len - 1.2):.2f}:d=1.2[a];"
          f"[0:v]fade=t=in:st=0:d=0.5,fade=t=out:st={max(0, total_len - 0.8):.2f}:d=0.8[v]")
    run(["ffmpeg", "-y", "-i", "joined.mp4", "-i", "music.wav", "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
         str(out_path)], cwd=work)
    return total_len


# ---------------------------------------------------------------- telegram
def tg(method, **kw):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return requests.post(f"https://api.telegram.org/bot{token}/{method}", timeout=300, **kw)


def send_video(path, caption):
    chat = os.environ["TELEGRAM_CHAT_ID"]
    with open(path, "rb") as f:
        r = tg("sendVideo", data={"chat_id": chat, "caption": caption[:1000], "supports_streaming": "true",
                                  "width": W, "height": H}, files={"video": f})
    if r.status_code != 200:
        raise RuntimeError(f"Telegram error: {r.text[:300]}")


def send_text(text):
    tg("sendMessage", data={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text[:4000]})


# ---------------------------------------------------------------- main
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
        except Exception as e:  # noqa: BLE001
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
