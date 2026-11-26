#!/usr/bin/env python3
"""الراوي الكريستالي - مولد فيديو القصة السينمائية."""
استيراد asyncio
استيراد json
استيراد نظام التشغيل
استيراد مكتبة المسار
استيراد عشوائي
استيراد
استيراد العمليات الفرعية
استيراد sys
وقت الاستيراد
موجة الاستيراد
from urllib.parse import quote

استيراد numpy كـ np
طلبات الاستيراد
من مكتبة PIL استورد Image و ImageEnhance

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "output"
السجل = الجذر / "history.json"
العرض، الارتفاع، معدل الإطارات = 1080، 1920، 30
SELFTEST = "--selftest" في sys.argv

PAGE_NAME = os.environ.get("PAGE_NAME", "The Masked Truth")
الأصوات = ["en-US-AndrewNeural", "en-GB-RyanNeural", "en-US-BrianNeural"]

قفل الأحرف = (
    "شاب غامض يرتدي قناعًا فضيًا مرصعًا بأحجار الراين الكريستالية يغطي كامل الرأس"
    "بفتحات عيون مفتوحة تظهر عيونًا خضراء ثاقبة وفتحة فم مفتوحة مميزة،"
    "يرتدي سترة رياضية سوداء داكنة اللون مزودة بغطاء رأس وسحاب"
)

البيئات = [
    "مكتب دراسة خشبي فاخر ذو إضاءة خافتة ليلاً مع مصباح مكتب دافئ ورفوف كتب".
    "جرف صخري هادئ يطل على محيط أزرق هادئ عند غروب الشمس الذهبي".
    "قمة جبلية ضبابية فوق السحاب في وقت الشفق الصباحي الباكر"،
    "شارع مدينة مضاء بأضواء النيون ومغطى بالمطر ليلاً مع أضواء بوكيه ناعمة في الخلفية".
    "غرفة معيشة عصرية مريحة مع مدفأة دافئة وصوت المطر على النافذة".
    "مكتبة قديمة ذات أجواء مميزة، بأرفف خشبية طويلة وأشعة شمس ناعمة".
    "شرفة على سطح مبنى شاهق تطل على أفق المدينة المتلألئ عند الغسق"،
    "ركن مقهى عتيق هادئ بجوار نافذة ضبابية بإضاءة محيطة دافئة".
    "مسار هادئ في غابة صنوبر تتخلله أشعة الشمس الذهبية من خلال الأشجار الطويلة".
    "إعداد استوديو بودكاست بسيط ومظلم مزود بميكروفون احترافي وإضاءة خلفية دافئة".
]

المواضيع = [
    "حقيقة نفسية لا يتحدث عنها أحد"،
    "مصادفة غامضة في الواقع أنقذت حياة"،
    "القاعدة الصامتة للثقة والخيانة بين البشر"،
    "درس خفي وراء فعل صغير من اللطف يقوم به شخص غريب"،
    "لماذا يلاحظ أكثر الأشخاص هدوءًا في الغرفة كل شيء؟"
    "رسالة مؤثرة عُثر عليها بعد عقود من كتابتها"،
    "اللحظة التي يدرك فيها المرء أنه لم يُقدّر الحب حق قدره".
    "لغز لم يُحل من بلدة ساحلية صغيرة"،
    "كيف غيّر قرار واحد حياتين إلى الأبد"،
    "وعد منسي تم الوفاء به بعد ثلاثين عاماً"،
]

الحالة المزاجية = ["غامض"، "حزين"، "متفائل"، "متوتر"، "دافئ"]
الأوتار = {
    "حزين": [110.0، 130.81، 164.81، 220.0]،
    "متفائل": [130.81، 164.81، 196.0، 246.94]،
    "التوتر": [73.42، 110.0، 155.56، 220.0]،
    "دافئ": [87.31، 110.0، 130.81، 174.61]،
    "غامض": [98.0، 116.54، 138.59، 196.0]،
}
ألوان المزاج = {
    "حزين": (35، 50، 80)، "متفائل": (85، 70، 45)، "متوتر": (65، 30، 35).
    "دافئ": (95، 60، 35)، "غامض": (45، 35، 75)،
}


دالة تشغيل (cmd، cwd=لا شيء):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    إذا كان r.returncode != 0:
        raise RuntimeError(f"فشل الأمر: {' '.join(map(str, cmd))[:200]}\n{r.stderr[-1500:]}")
    إرجاع r.stdout


دالة media_duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    أعد القيمة العشرية (out.strip())


دالة تحميل السجل():
    يحاول:
        data = json.loads(HISTORY.read_text(encoding="utf-8"))
        أعد البيانات إذا كانت من نوع قائمة، وإلا فأعد []
    باستثناء الاستثناء:
        يعود []


def build_prompt(theme, environment, recent):
    moods_str = ", ".join(MOODS)
    return f"""أنت راوي قصص غامض ينتشر بسرعة كبيرة مثل السيد شيلبي لـ "{PAGE_NAME}".
اكتب قصة واحدة مثيرة وواقعية وعاطفية أو غامضة تُروى في حوالي 55 ثانية (135-155 كلمة).
السمة: {theme}
إعدادات جميع المشاهد: {البيئة}

قواعد صارمة:
- ابدأ بجملة افتتاحية قوية تجذب انتباه الناس وتمنعهم من التمرير فوراً.
- سرد قصة أو حقيقة نفسية يرغب الناس في مشاركتها مع العائلة والأصدقاء.
- ينتهي الفيلم بنهاية مفاجئة لا تُنسى أو بإدراك عميق في المشهدين الأخيرين.
- لغة إنجليزية منطوقة طبيعية، جمل قصيرة ذات إيقاع منتظم.
- لا تكرر العناوين الحديثة: {recent}
- مقسمة إلى 7 مشاهد. كل مشهد: جملة أو جملتان من السرد.
- يجب أن يصف كل "image_prompt" الراوي المقنع ({CHARACTER_LOCK}) داخل {environment}، مع إظهار زوايا كاميرا متنوعة (لقطة مقربة للعينين، لقطة متوسطة، صورة جانبية، تعبير متأمل، إيماءات) مع الحفاظ على نفس الإعداد والشخصية بالضبط.
- لا تقم أبدًا بتضمين نص أو كلمات أو ظلام دامس في أي صورة_موجهة.
- "mood": واحد من {moods_str}.

إرجاع بيانات JSON صالحة فقط:
{{"title": str, "caption": str (بحد أقصى 135 حرفًا، وينتهي بسؤال)،
"الهاشتاغات": [5 سلاسل نصية]،
"scenes": [{{"narration": str, "image_prompt": str, "mood": str}}]}}"""


دالة استخراج_json(نص):
    text = text.strip()
    a, b = text.find("{"), text.rfind("}")
    إذا كانت قيمة a تساوي -1 أو قيمة b تساوي -1:
        رفع خطأ القيمة ("لم يتم العثور على JSON")
    return json.loads(text[a:b + 1])


دالة ask_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    إذا لم يكن مفتاحًا:
        ارفع خطأ وقت التشغيل ("لا يوجد مفتاح Gemini")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9}}
    r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=120)
    إذا كان رمز الحالة r لا يساوي 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


دالة ask_pollinations(prompt):
    body = {"model": "openai", "seed": random.randint(1, 10**6),
            "الرسائل": [{"الدور": "النظام", "المحتوى": "الرد ببيانات JSON صالحة فقط."},
                         {"role": "user", "content": prompt}]}
    r = requests.post("https://text.pollinations.ai/openai", json=body, timeout=180)
    إذا كان رمز الحالة r لا يساوي 200:
        raise RuntimeError(f"استطلاعات HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"]


def generate_story(theme, environment, recent):
    prompt = build_prompt(theme, environment, recent)
    مقدمو الخدمات = [("gemini", ask_gemini), ("pollinations", ask_pollinations)]
    الأخير = لا شيء
    للمحاولة في النطاق (3):
        للحصول على الاسم، fn في مقدمي الخدمات:
            يحاول:
                story = extract_json(fn(prompt))
                تحقق من أن `story.get("scenes")` هو نوع قائمة، وأن طول `story["scenes"]` أكبر من أو يساوي 4.
                for sc in story["scenes"]:
                    assert sc.get("narration") and sc.get("image_prompt")
                    إذا لم يكن sc.get("mood") موجودًا في MOODS:
                        sc["mood"] = "mysterious"
                story.setdefault("title", "بدون عنوان")
                story.setdefault("caption", "")
                story.setdefault("hashtags", [])
                print(f"قصة من {name}")
                العودة إلى القصة
            باستثناء الاستثناء كـ e:
                last = f"{name}: {e}"
                print("story retry ->", last)
        time.sleep(5 * (attempt + 1))
    ارفع خطأ وقت التشغيل (f"فشلت جميع موفري النصوص. الأخير: {last}")


async def _tts(text, voice, path):
    استيراد edge_tts
    # وقفات تنفس درامية: حوّل نهايات الجمل إلى علامات حذف.
    natural = re.sub(r"\.\s+", "... ", text.strip())
    await edge_tts.Communicate(natural, voice, rate="-7%", pitch="-2Hz").save(str(path))


دالة make_voice(نص، صوت، مسار):
    إذا كان الاختبار الذاتي:
        تشغيل(["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=d=3.5:c=pink:a=0.02",
             "-ar", "24000", "-ac", "1", str(path)])
        يعود
    للمحاولة في النطاق (3):
        يحاول:
            asyncio.run(_tts(text, voice, path))
            إذا كان حجم المسار المحدد في مكتبة pathlib أكبر من 1000:
                يعود
        باستثناء الاستثناء كـ e:
            print("إعادة محاولة تحويل النص إلى كلام:", e)
        time.sleep(3)
    رفع خطأ وقت التشغيل ("فشل تحويل النص إلى كلام")


دالة is_valid_bright_image(img):
    arr = np.asarray(img.convert("L"), dtype=np.float32)
    أرجع قيمة `float(np.mean(arr)) > 18.0` وقيمة `float(np.std(arr)) > 12.0`


def save_cropped_9_16(raw_bytes, path):
    tmp = pathlib.Path(path).with_suffix(".raw")
    tmp.write_bytes(raw_bytes)
    يحاول:
        img = Image.open(tmp).convert("RGB")
        إذا لم تكن الصورة (img) صورة ساطعة صالحة:
            رفع خطأ القيمة ("الصورة داكنة جدًا").
        tw, th = 1080, 1920
        scale = max(tw / img.width, th / img.height)
        img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1), Image.Resampling.LANCZOS)
        left, top = (img.width - tw) // 2, (img.height - th) // 2
        img = img.crop((left, top, left + tw, top + th))
        img = ImageEnhance.Contrast(img).enhance(1.06)
        img = ImageEnhance.Color(img).enhance(1.08)
        img.save(path, quality=94)
        إرجاع صحيح
    أخيراً:
        tmp.unlink(missing_ok=True)


دالة make_image(prompt, environment, mood, path, seed):
    إذا كان الاختبار الذاتي:
        Image.new("RGB", (1080, 1920), MOOD_COLORS.get(mood, (50, 45, 65))).save(path, quality=92)
        يعود
    base_style = "صورة سينمائية واقعية من فيلم 35 ملم، تركيز حاد على بريق قناع الكريستال الفضي، إضاءة طبيعية، 8K، بدون نص"
    المطالبات = [
        f"{prompt}, {base_style}"[:380],
        f"صورة متوسطة الحجم لـ {CHARACTER_LOCK} في {environment}، {base_style}"[:380]،
    ]
    للمحاولة في النطاق (6):
        p = prompts[0] إذا كانت المحاولة < 4 وإلا prompts[1]
        model = "flux" إذا كانت المحاولة < 4 وإلا "turbo"
        url = (f"https://image.pollinations.ai/prompt/{quote(p, safe='')}"
               f"?width=768&height=1344&nologo=true&seed={seed + attempt * 13}&model={model}")
        يحاول:
            r = requests.get(url, timeout=90)
            إذا كان رمز الحالة r يساوي 200 وكان r.headers.get("content-type", "").startswith("image"):
                if save_cropped_9_16(r.content, path):
                    يعود
        باستثناء الاستثناء كـ e:
            print(f"img retry {attempt + 1}:", e)
        time.sleep(3)
    يحاول:
        r = requests.get(f"https://picsum.photos/seed/{seed}/1080/1920", timeout=45)
        إذا كان رمز الحالة r يساوي 200 وتم حفظ المحتوى المقتطع 9_16(r.content, path):
            يعود
    باستثناء الاستثناء:
        يمر
    Image.new("RGB", (1080, 1920), MOOD_COLORS.get(mood, (50, 45, 65))).save(path, quality=92)


def make_music(moods, durs, path, sr=44100):
    xf = 1.0
    المجموع = مجموع (الدورات)
    buf = np.zeros(int(sr * (total + 2 * xf)))
    pos = 0.0
    for mood, d in zip(moods, durs):
        t = np.arange(int(sr * (d + xf))) / sr
        sig = np.zeros_like(t)
        for i, f in enumerate(CHORDS.get(mood, CHORDS["mysterious"])):
            للتحديد في (-0.35، 0.0، 0.35):
                sig += np.sin(2 * np.pi * (f + det) * t + i) / (1 + 0.4 * i)
        سيج /= (np.max(np.abs(sig)) + 1e-9)
        ramp = np.linspace(0, 1, int(sr * xf))
        env = np.ones(len(sig))
        env[:len(ramp)] = ramp
        env[-len(ramp):] = ramp[::-1]
        start = int(sr * max(0.0, pos - xf / 2))
        النهاية = دقيقة (بداية + لين (سيج)، لين (بوف))
        buf[start:end] += (sig * env)[:end - start]
        pos += d
    buf = buf[:int(sr * total)]
    buf = buf / (np.max(np.abs(buf)) + 1e-9) * 0.55
    fade = int(sr * 1.5)
    buf[:fade] *= np.linspace(0, 1, fade)
    buf[-fade:] *= np.linspace(1, 0, fade)
    stereo = np.stack([buf, np.roll(buf, 260)], axis=1)
    باستخدام wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((stereo * 32767).astype(np.int16).tobytes())


def ass_time(s):
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def make_ass(text, total, path):
    الكلمات = النص.استبدال("{", "").استبدال("}", "").تقسيم()
    chunks, cur = [], []
    بالنسبة لـ w بالكلمات:
        cur.append(w)
        إذا كان طول (cur) >= 4 أو (w[-1] في ".!?," وطول (cur) >= 2):
            chunks.append(" ".join(cur))
            cur = []
    إذا كان الوضع الحالي:
        chunks.append(" ".join(cur))
    الوزن = مجموع (طول (ج) لكل ج في أجزاء) أو 1
    القابل للاستخدام = الحد الأقصى (1.0، الإجمالي - 0.45)
    t = 0.1
    الأسطر = []
    for c in chunks:
        د = قابل للاستخدام * طول(ج) / الوزن
        lines.append(f"Dialogue: 0,{ass_time(t)},{ass_time(t + d)},Main,,0,0,0,,{c}")
        t += d
    العنوان = (
        "[معلومات البرنامج النصي]\nنوع البرنامج النصي: الإصدار 4.00+\nدقة العرض الأفقية: 1080\nدقة العرض الرأسية: 1920\n\n"
        "[أنماط الإصدار 4+]\nالتنسيق: الاسم، اسم الخط، حجم الخط، اللون الأساسي، اللون الثانوي، لون الإطار الخارجي، "
        "لون الخلفية، غامق، مائل، تسطير، شطب، مقياس أفقي، مقياس رأسي، تباعد، زاوية، نمط الحدود، "
        "مخطط تفصيلي، ظل، محاذاة، هامش يسار، هامش يمين، هامش رأسي، ترميز\n"
        "النمط: رئيسي،DejaVu Sans،62،&H00FFFFFF،&H000000FF،&H00000000،&H90000000،-1,0,0,0,100,100,0,0,1,5,2,2,70,70,360,1\n\n"
        "[الأحداث]\nالتنسيق: الطبقة، البداية، النهاية، النمط، الاسم، الهامش الأيسر، الهامش الأيمن، الهامش الرأسي، التأثير، النص\n"
    )
    pathlib.Path(path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def render_scene(work, i, text, total):
    الإطارات = الحد الأقصى (1، العدد الصحيح (الإجمالي * معدل الإطارات في الثانية))
    الوضع = i % 3
    إذا كان الوضع يساوي 0:
        zoom, x_expr = f"1.02+0.12*on/{frames}", "iw/2-(iw/zoom/2)"
    elif mode == 1:
        zoom, x_expr = f"1.14-0.12*on/{frames}", "iw/2-(iw/zoom/2)"
    آخر:
        تكبير، x_expr = "1.10"، f"(iw-iw/zoom)*(on/{frames})"
    make_ass(text, total, work / f"s{i}.ass")
    vf = (
        "scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
        f"zoompan=z='{zoom}':x='{x_expr}':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
        f"eq=contrast=1.04:saturation=1.06,subtitles=s{i}.ass,format=yuv420p"
    )
    تشغيل(["ffmpeg", "-y", "-i", f"img{i}.jpg", "-i", f"voice{i}.mp3",
         "-vf", vf, "-af", f"apad=whole_dur={total:.3f},aresample=44100",
         "-t", f"{total:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "fast", "-crf", "20",
         "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", f"clip{i}.mp4"], cwd=work)


دالة make_video(idx, story, environment, out_path):
    العمل = OUT / f"work{idx}"
    work.mkdir(parents=True, exist_ok=True)
    voice = VOICES[idx % len(VOICES)]
    durs, moods = [], []
    seed_base = random.randint(1, 10**6)
    for i, sc in enumerate(story["scenes"]):
        make_voice(sc["narration"], voice, work / f"voice{i}.mp3")
        الإجمالي = مدة الوسائط (العمل / f"صوت{i}.mp3") + 0.50
        durs.append(total)
        moods.append(sc["mood"])
        make_image(sc["image_prompt"], environment, sc["mood"], work / f"img{i}.jpg", seed_base + i)
        render_scene(work, i, sc["narration"], total)
        time.sleep(1 if SELFTEST else 2)
    (work / "list.txt").write_text("".join(f"file 'clip{i}.mp4'\n" for i in range(len(story["scenes"]))))
    تشغيل(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "joined.mp4"], cwd=work)
    make_music(moods, durs, work / "music.wav")
    الطول_الإجمالي = مجموع(المدد)
    fc = ("[1:a]lowpass=f=850,volume=0.13[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
          f"loudnorm=I=-15:TP=-1.5:LRA=9,afade=t=out:st={max(0, total_len - 1.2):.2f}:d=1.2[a];"
          f"[0:v]fade=t=in:st=0:d=0.4,fade=t=out:st={max(0, total_len - 0.7):.2f}:d=0.7[v]")
    تشغيل(["ffmpeg", "-y", "-i", "joined.mp4", "-i", "music.wav", "-filter_complex", fc,
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-crf", "21",
         [-pix_fmt, "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out_path)], cwd=work)
    إرجاع الطول الإجمالي


def tg(method, **kw):
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}"
    return requests.post(url, timeout=300, **kw)


def send_video(path, caption):
    مع فتح (المسار، "rb") كـ f:
        r = tg("sendVideo", data={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "caption": caption[:1000],
                                  {"supports_streaming": "true", "width": W, "height": H}, files={"video": f})
    إذا كان رمز الحالة r لا يساوي 200:
        raise RuntimeError(f"خطأ في تيليجرام: {r.text[:300]}")


def send_text(text):
    r = tg("sendMessage", data={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text[:4000]})
    إذا كان رمز الحالة r لا يساوي 200:
        print(f"خطأ في نص تيليجرام: {r.text[:300]}")


def main():
    OUT.mkdir(exist_ok=True)
    إذا كان الاختبار الذاتي:
        fake = {"title": "اختبار", "caption": "اختبار؟", "hashtags": ["#اختبار"],
                "مشاهد": [{"سرد": "تبقى بعض الحقائق مخفية حتى اللحظة المناسبة."،
                            "image_prompt": "x", "mood": "mysterious"}]}
        print("OK", make_video(0, fake, ENVIRONMENTS[0], OUT / "selftest.mp4"))
        يعود
    history = load_history()
    recent = [h.get("title", "") for h in history[-40:] if isinstance(h, dict)]
    n = int(os.environ.get("VIDEOS_PER_RUN", "3"))
    themes = random.sample(THEMES, min(n, len(THEMES)))
    envs = random.sample(ENVIRONMENTS, min(n, len(ENVIRONMENTS)))
    تم الإنشاء، الأخطاء = []، []
    لكل k في النطاق (n):
        يحاول:
            theme = themes[k % len(themes)]
            environment = envs[k % len(envs)]
            story = generate_story(theme, environment, recent)
            path = OUT / f"video{k + 1}.mp4"
            الطول = إنشاء_فيديو(ك، القصة، البيئة، المسار)
            tags = " ".join(str(h) for h in story["hashtags"])
            caption = f"الخيار {k + 1} | {story['title']} ({length:.0f}s)\n\n{story['caption']}\n{tags}"
            made.append((path, caption))
            history.append({"title": story["title"], "date": time.strftime("%Y-%m-%d")})
            recent.append(story["title"])
        باستثناء الاستثناء كـ e:
            print(f"فشل الفيديو {k + 1}: {e}")
            errors.append(f"video {k + 1}: {str(e)[:300]}")
    HISTORY.write_text(json.dumps(history[-200:], ensure_ascii=False, indent=1), encoding="utf-8")
    إذا تم صنعه:
        send_text(f"فيديوهات Crystal Narrator لليوم {len(made)} جاهزة:")
        بالنسبة للمسار، تم إنشاء التسمية التوضيحية:
            إرسال_الفيديو(المسار، التعليق)
    في حالة حدوث أخطاء:
        send_text("الأخطاء:\n" + "\n".join(errors))
    إذا لم يتم صنعه:
        sys.exit(1)


إذا كان __name__ == "__main__":
    رئيسي()
