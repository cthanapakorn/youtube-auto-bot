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

def fetch_image_master(prompt, filename, scene_num):
    """ระบบวาดรูปมหาอุด: ใช้ FLUX Engine พร้อมระบบรอและลองใหม่ (Exponential Backoff)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพ Anime Meme ด้วย FLUX Engine...")
    
    style_suffix = "anime meme style, exaggerated expressions, young Asian office worker, messy hair, dramatic, vibrant colors, high contrast, 4k, masterpiece"
    full_prompt = f"{prompt}, {style_suffix}"
    clean_prompt = re.sub(r'[^\w\s]', '', full_prompt).strip().replace(' ', '%20')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # ⚠️ ไม้ตายชั้นที่ 1: ระบบ Exponential Backoff (รอและค่อยๆ ลองใหม่)
    backoff_time = 2 # เริ่มต้นรอ 2 วินาที
    for attempt in range(5): # พยายามสูงสุด 5 ครั้ง
        seed = random.randint(1, 999999)
        url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1080&height=1920&seed={seed}&nologo=true&model=flux"
        
        try:
            response = requests.get(url, headers=headers, timeout=40)
            if response.status_code == 200 and len(response.content) > 10000:
                img = Image.open(io.BytesIO(response.content)).convert('RGB')
                img.save(filename, 'JPEG', quality=95)
                print(f"      ✅ สำเร็จ! ได้ภาพ AI คุณภาพสูง (Seed: {seed})")
                return True
            else:
                # ถ้าพลาดหรือคิวยาว ให้รอแล้วลองใหม่
                print(f"      🔄 คิวยาวหรือพลาด... รอ {backoff_time} วินาที (ครั้งที่ {attempt+1})")
                time.sleep(backoff_time)
                backoff_time *= 2 # เพิ่มเวลารอเป็น 2 เท่าในครั้งถัดไป
        except Exception as e:
            print(f"      ❌ ขัดข้อง: {str(e)}")
            time.sleep(5)
            
    # ไม้ตายชั้นที่ 2: ถ้าพลาดหมด บังคับสร้างไฟล์ภาพฉุกเฉิน
    print(f"      ⚠️ สร้างภาพกราฟิกฉุกเฉิน (ป้องกัน Error 69)")
    img = Image.new('RGB', (1080, 1920), color=(10, 10, 30))
    img.save(filename, 'JPEG')
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังเขียนบทและซับไตเติลตัวใหญ่ๆ...")
        # 📌 สั่งให้ Gemini เขียนสคริปต์และซับไตเติล
        prompt_sys = (
            "Act as a viral YouTube Shorts creator. Select ONE real financial concept. "
            "Write a 60s Thai script (5 scenes) with funny relatable anime meme tone. "
            "For each scene, provide: 1.Relatable Thai voiceover text 2.Dramatic anime prompt "
            "3.A short, compelling, large, bold Thai caption/hook (max 6 words). "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-5% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการวาดภาพ AI (The Unstoppable Method)...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            fetch_image_master(sc['prompt'], f"i_{i}.jpg", i+1)

        print("🎬 4. สร้างซับตัวใหญ่ๆ และประกอบ Video...")
        
        # ⚠️ ไม้ตายชั้นที่ 3: สร้างไฟล์ซับไตเติลแบบ .ass (Advanced Substation Alpha)
        with open("subs.ass", "w", encoding="utf-8") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nTimer: 100.0000\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            # 🎨 ตั้งค่าซับตัวใหญ่ Bold สีทองแดง ขอบดำ หนา มีเงา
            f.write(f"Style: FinalBoss,Arial,110,&H004B75D4,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,15,10,2,80,80,960,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
                start_time = i * SCENE_DURATION
                end_time = (i + 1) * SCENE_DURATION
                f.write(f"Dialogue: 0,0:{start_time:02}:00.00,0:{end_time:02}:00.00,FinalBoss,,0,0,0,,{sc['caption']}\n")

        # ประกอบ Video พร้อมใส่เอฟเฟกต์ซูม Cinematic และฝังซับไตเติล
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        # 📌 FFmpeg: สเกล,sar,ฝังซับ ass,ซูม Ken Burns
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920,setsar=1,ass=subs.ass,zoompan=z='min(zoom+0.0015,1.5)':d=300:s=1080x1920\" "
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
            print("✨ ภารกิจสำเร็จ! เลิกท้อได้เลย คลิปการเงินมหากาพย์มาแล้ว!")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
