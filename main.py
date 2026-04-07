import os, re, json, subprocess, requests, sys, time, random, shutil
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageFont

# --- ⚙️ ตั้งค่าความยาว (6 ฉาก x 10 วินาที = 60 วินาทีพอดี) ---
SCENE_COUNT = 6   
SCENE_DURATION = 10 
VIDEO_PRIVACY = "private"

# 📌 อัปเดตตัวละครคงที่: ล็อกสเปกสัดส่วนร่างกาย ตา และมือให้เป๊ะที่สุด
CHAR_ANCHOR = "An expressive 29-year-old Thai male professional, neat modern haircut, business casual attire, highly detailed anime style, highly detailed expressive face, perfectly drawn eyes, anatomically correct hands, exactly 5 fingers per hand, flawless human anatomy, vibrant colors, modern webtoon style, masterpiece illustration"

def install_and_get_font():
    """ติดตั้งฟอนต์ไทยลงระบบ OS ป้องกันฟอนต์เพี้ยน 100%"""
    font_family = "Sans"
    if os.path.exists("font.ttf"):
        try:
            font = ImageFont.truetype("font.ttf")
            font_family, _ = font.getname()
            print(f"✅ ตรวจพบฟอนต์ไทย: {font_family}")
            
            font_dir = os.path.expanduser("~/.fonts")
            os.makedirs(font_dir, exist_ok=True)
            shutil.copy("font.ttf", os.path.join(font_dir, "font.ttf"))
            
            subprocess.run(["fc-cache", "-f", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"⚠️ มีปัญหาการติดตั้งฟอนต์: {e}")
    else:
        print("‼️ ไม่พบไฟล์ font.ttf (ซับอาจเป็นต่างดาว)")
    return font_family

def fetch_image_cartoon(prompt, filename, scene_num):
    """วาดภาพแนวกาตูนคุณภาพสูง พร้อมบังคับรายละเอียดมือและตา"""
    print(f"   🎨 ฉากที่ {scene_num}: กำลังวาดภาพสไตล์การ์ตูนที่ลงรายละเอียดชัดเจน...")
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    
    # บังคับสไตล์ให้เป็นการ์ตูนคุณภาพสูง และย้ำเรื่องโครงสร้างร่างกายอีกรอบ
    style = "high-quality anime style, stunning visual, dramatic lighting, detailed background, perfect hands, detailed eyes, masterpiece"
    url = f"https://image.pollinations.ai/prompt/{clean_p},{CHAR_ANCHOR},{style}?width=1080&height=1920&seed={random.randint(1,999999)}&nologo=true&model=flux"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    for attempt in range(5): 
        try:
            r = requests.get(url, headers=headers, timeout=120)
            if r.status_code == 200 and len(r.content) > 20000:
                with open(filename, 'wb') as f: f.write(r.content)
                print(f"      ✅ ฉากที่ {scene_num} วาดเสร็จสิ้น!")
                return True
            time.sleep(10)
        except: time.sleep(10)
            
    print(f"      ‼️ ใช้ภาพกราฟิกสำรองสำหรับฉากที่ {scene_num}")
    Image.new('RGB', (1080, 1920), color=(15, 15, 15)).save(filename, 'JPEG')
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังเขียนบทและกำหนดภาพแต่ละเหตุการณ์ให้ชัดเจน...")
        prompt_sys = (
            "คุณคือผู้เชี่ยวชาญด้านการสร้างวิดีโอ YouTube Shorts ระดับไวรัล และการเล่าเรื่อง\n"
            "เป้าหมาย: สร้างคอนเทนต์วิดีโอความยาว 60 วินาที ที่ดึงดูดคนดูตั้งแต่ 3 วินาทีแรก\n"
            "หัวข้อ: 'ข้อผิดพลาดทางการเงินที่เกือบทำให้หมดตัว'\n\n"
            "โครงสร้างสคริปต์ 6 ฉาก (ฉากละ 10 วินาที):\n"
            "- ฉาก 1: Hook (ประโยคสั้น กระแทกใจ ชวนสงสัย)\n"
            "- ฉาก 2: Setup (ปูเรื่อง)\n"
            "- ฉาก 3: ปัญหาเริ่มหนัก\n"
            "- ฉาก 4: วิกฤต\n"
            "- ฉาก 5: จุดเปลี่ยน\n"
            "- ฉาก 6: บทเรียน + ทิ้งท้าย (มีข้อคิดชัดเจน)\n\n"
            "กฎเหล็กแต่ละฉาก:\n"
            "1. บทพากย์ (text): ภาษาไทย โทนเสียงจริงจัง มีอารมณ์ (ความยาว 40-50 คำต่อฉาก เพื่อให้พูดจบใน 10 วินาที)\n"
            "2. คำสั่งวาดรูป (prompt): ภาษาอังกฤษ บรรยายเหตุการณ์ สภาพแวดล้อม และอารมณ์ให้ **เห็นภาพชัดเจนที่สุด** (เช่น 'A man sitting at a dark desk holding a glowing phone, looking stressed with unpaid bills'). หากมีฉากที่เห็นมือ ให้เน้น 'anatomically correct hands holding [object]'. สลับภาพชายวัย 29 ปี กับภาพเหตุการณ์ให้เข้ากับบท\n"
            "3. ซับไตเติล (caption): คำไทยสั้นๆ 1-2 คำ กระแทกอารมณ์ เช่น 'พัง', 'เครียด', 'หมดตัว'\n\n"
            "ข้อมูลเสริม (SEO):\n"
            "1. title: น่าสนใจ กระตุ้นให้คลิก (Curiosity + Emotion)\n"
            "2. desc: สั้น กระชับ มีคีย์เวิร์ด พร้อมคำแนะนำเพลง background\n"
            "3. tags: แฮชแท็ก 5 อัน\n"
            "Output STRICT JSON: {\"title\": \"...\", \"desc\": \"...\", \"tags\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        print("🎙️ 2. สร้างเสียงพากย์คุณนิวัฒน์ (โทนจริงจัง น่าเชื่อถือ)...")
        full_voice = " . . . ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-3% --voice "th-TH-NiwatNeural" --text "{full_voice}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. วาดภาพการ์ตูนคุณภาพสูง 6 ฉาก (เน้นรายละเอียดสัดส่วน)...")
        for i, sc in enumerate(data['scenes']):
            fetch_image_cartoon(sc['prompt'], f"i_{i}.jpg", i+1)
            time.sleep(3)

        print("🎬 4. ประกอบวิดีโอ 60 วินาที (ซับขึ้น 3 วิแรกแล้วหายไป)...")
        font_family = install_and_get_font()
        
        with open("subs.ass", "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            # ซับสไตล์ภาพยนตร์: สีขาว ขอบดำหนา วางกึ่งกลางค่อนไปทางล่าง
            f.write(f"Style: MovieSub,{font_family},160,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,18,8,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            
            # ซับขึ้นมาแค่ 3 วินาทีแรกของแต่ละฉาก แล้ว "หายไป" 
            for i in range(SCENE_COUNT):
                start_time = i * SCENE_DURATION
                end_time = start_time + 3  # โชว์แค่ 3 วินาที
                f.write(f"Dialogue: 0,0:{start_time//60:02}:{start_time%60:02}.00,0:{end_time//60:02}:{end_time%60:02}.00,MovieSub,,0,0,0,,{data['scenes'][i]['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")

        # 📌 FFmpeg: ผสมเสียง (Voice + BGM 8%) + ซูมนุ่มๆ แบบกล้องภาพยนตร์
        has_bg = os.path.exists("bg.mp3")
        music_input = "-i bg.mp3" if has_bg else ""
        audio_filter = "-filter_complex \"[1:a]volume=1.0[a1];[2:a]volume=0.08[a2];[a1][a2]amix=inputs=2:duration=first[a]\" -map 0:v -map \"[a]\"" if has_bg else "-c:a aac"
        
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 {music_input} "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles=subs.ass,zoompan=z='min(zoom+0.001,1.3)':d=250:s=1080x1920\" "
            f"{audio_filter} -c:v libx264 -crf 18 -pix_fmt yuv420p -r 25 -t 60 final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube พร้อม SEO...")
        if os.path.exists('token.json'):
            with open('token.json', 'r') as f:
                creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
            youtube = build("youtube", "v3", credentials=creds)
            youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": data['title'], 
                        "description": f"{data['desc']}\n\n{data['tags']}", 
                        "categoryId": "27"
                    }, 
                    "status": {"privacyStatus": VIDEO_PRIVACY}
                },
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! คลิปหนุ่มวัย 29 สัดส่วนเป๊ะ ซับเด้งแล้วหาย พร้อมออนไลน์!")

    except Exception as e:
        print(f"‼️ ขัดข้องที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
