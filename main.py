import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# --- ⚙️ ตั้งค่าคลิป (5 ฉาก x 12 วินาที = 60 วินาที) ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 5   
SCENE_DURATION = 12 
VIDEO_PRIVACY = "private"

def fetch_image_turbo(prompt, filename, scene_num):
    """ระบบวาดรูป Turbo: ลดขนาดภาพเพื่อความเร็ว + เพิ่ม Timeout เป็น 120 วิ"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพ Anime Meme (Turbo Mode)...")
    
    # 📌 ปรับขนาดลงเป็น 512x896 เพื่อให้ AI ทำงานง่ายและไม่ Timeout (FFmpeg จะขยายให้เอง)
    width, height = 512, 896 
    style_suffix = "high-quality anime meme style, exaggerated expressions, vibrant colors, high contrast, 4k, masterpiece"
    full_prompt = f"{prompt}, {style_suffix}"
    clean_prompt = re.sub(r'[^\w\s]', '', full_prompt).strip().replace(' ', '%20')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # เพิ่มการพักเครื่องก่อนเริ่มฉากใหม่ 3 วินาที
    time.sleep(3)

    for attempt in range(4): # พยายาม 4 ครั้ง
        seed = random.randint(1, 999999)
        # ใช้ model=flux เพื่อคุณภาพสูงสุด
        url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width={width}&height={height}&seed={seed}&nologo=true&model=flux"
        
        try:
            # 📌 เพิ่ม timeout เป็น 120 วินาที
            response = requests.get(url, headers=headers, timeout=120)
            if response.status_code == 200 and len(response.content) > 10000:
                img = Image.open(io.BytesIO(response.content)).convert('RGB')
                img.save(filename, 'JPEG', quality=95)
                print(f"      ✅ สำเร็จ! ได้ภาพ AI (Seed: {seed})")
                return True
            else:
                print(f"      🔄 Server ไม่พร้อม (Code: {response.status_code}) ลองใหม่ใน 10 วิ...")
                time.sleep(10)
        except Exception as e:
            print(f"      ⚠️ ขัดข้อง: {str(e)}... พัก 10 วินาที")
            time.sleep(10)
            
    print(f"      ⚠️ สร้างภาพกราฟิกสำรอง (ป้องกันวิดีโอพัง)")
    img = Image.new('RGB', (1080, 1920), color=(15, 15, 35))
    img.save(filename, 'JPEG')
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังคิดคอนเทนต์และซับไตเติลไวรัล...")
        prompt_sys = (
            "Act as a viral financial storyteller. Pick a real money concept. "
            "Write a 60s Thai script (5 scenes). Tone: Funny, dramatic anime meme. "
            "For each scene, provide: 1.Thai voiceover 2.Anime prompt 3.A punchy, HUGE, BOLD Thai caption (max 5 words). "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อ: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-5% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. วาดภาพ AI (Turbo Unstoppable Method)...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            fetch_image_turbo(sc['prompt'], f"i_{i}.jpg", i+1)

        print("🎬 4. สร้างซับไตเติลสีเหลืองตัวแม่และประกอบ Video...")
        
        # ⚠️ สร้างไฟล์ซับไตเติล .ass (ตัวใหญ่สะใจ สีเหลืองขอบดำ)
        with open("subs.ass", "w", encoding="utf-8") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            # &H0000FFFF = สีเหลืองสด | Outline 12 = ขอบหนามาก
            f.write(f"Style: Viral,Arial,115,&H0000FFFF,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,12,8,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
                start = i * SCENE_DURATION
                end = (i + 1) * SCENE_DURATION
                f.write(f"Dialogue: 0,0:{start:02}:00.00,0:{end:02}:00.00,Viral,,0,0,0,,{sc['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        # 📌 FFmpeg: ขยายภาพ 512 เป็น 1080 + ฝังซับเหลือง + ซูม Cinematic
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass=subs.ass,zoompan=z='min(zoom+0.0015,1.5)':d=300:s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube...")
        if os.path.exists('token.json'):
            with open('token.json', 'r') as f:
                creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
            youtube = build("youtube", "v3", credentials=creds)
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "23"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! คลิปมาพร้อมซับตัวแม่แล้ว!")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
