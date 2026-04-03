import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def create_valid_slide(path, text, scene_num):
    """สร้างสไลด์สำรองที่ 'สมบูรณ์' เพื่อป้องกัน FFmpeg พัง"""
    img = Image.new('RGB', (1080, 1920), color=(15, 15, 25))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 50, 1030, 1870], outline=(212, 175, 55), width=15)
    d.text((120, 900), f"SCENE {scene_num}\n{text[:30]}...", fill=(212, 175, 55))
    img.save(path, 'JPEG')
    print(f"   ⚠️ สร้างสไลด์สำรองสำเร็จสำหรับฉากที่ {scene_num}")

def get_ai_image(prompt, filename, scene_num):
    """ระบบดึงภาพที่เน้นความชัวร์ (ลอง Pollinations ก่อน เพราะ HF มักจะ 410)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังหาช่องทางดึงภาพ...")
    seed = random.randint(1, 999999)
    # ใช้ Pollinations เป็นหลักเพราะเสถียรกว่าในตอนนี้
    url = f"https://pollinations.ai/p/{prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={seed}&nologo=true"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    success = False
    try:
        r = requests.get(url, headers=headers, timeout=45)
        if r.status_code == 200 and len(r.content) > 10000:
            with open(filename, 'wb') as f: f.write(r.content)
            # --- ตรวจสอบความสมบูรณ์ของภาพ (สำคัญมากเพื่อกัน Error 69) ---
            with Image.open(filename) as img:
                img.verify() 
            print(f"   ✅ สำเร็จ! ได้ภาพจริงสำหรับฉากที่ {scene_num}")
            success = True
    except:
        pass

    if not success:
        create_valid_slide(filename, prompt, scene_num)
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())

        # 1. ร่างบทมหากาพย์
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์ 60 วินาที...")
        response = client.models.generate_content(
            model='models/gemini-2.5-flash', 
            contents="Create 60s viral Thai Story script. 6 scenes. Output JSON: {\"title\":\"...\",\"scenes\":[{\"text\":\"...\",\"visual\":\"Detailed English prompt\"}]}"
        )
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:6]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพ
        for i, sc in enumerate(data['scenes'][:6]):
            get_ai_image(f"{sc['visual']}, cinematic, 8k, majestic", f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ (Dynamic Zoom)
        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        # สร้างไฟล์รายการ input ให้ FFmpeg
        with open("l.txt", "w") as f:
            for i in range(6): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'") # บรรทัดสุดท้ายเพื่อปิด loop

        # ใช้คำสั่ง FFmpeg ที่ปลอดภัยขึ้น
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0: raise RuntimeError("FFmpeg พัง!")

        # 5. อัปโหลด (PRIVATE)
        print("🚀 5. อัปโหลดสู่ YouTube (สถานะ: ส่วนตัว)...")
        if not os.path.exists('token.json'):
            print("⚠️ ไม่พบ token.json ข้ามการอัปโหลด")
            return

        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": "private"}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ สำเร็จ! เข้าไปตรวจวิดีโอใน Studio ได้เลย")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("\n⚠️ โควตา YouTube เต็ม! รอ 24 ชม.")
            else: raise e

    except Exception as e:
        print(f"\n‼️ พังตรงนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
