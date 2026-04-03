import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

# --- ⚙️ ตั้งค่าระบบ ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 6
SCENE_DURATION = 10  # รวมเป็น 60 วินาทีพอดี
VIDEO_PRIVACY = "private" # เปลี่ยนเป็น public ได้ถ้าต้องการเปิดทันที

def create_valid_slide(path, text, scene_num):
    """วาดภาพกราฟิกพรีเมียม (Gold-Black) เมื่อ AI ล่มหมดจริงๆ"""
    img = Image.new('RGB', (1080, 1920), color=(10, 10, 20))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 50, 1030, 1870], outline=(212, 175, 55), width=15)
    d.text((120, 960), f"มหากาพย์ตอนที่ {scene_num}\n{text[:30]}...", fill=(212, 175, 55))
    img.save(path, 'JPEG')

def get_ai_image(prompt, filename, scene_num):
    """ฟังก์ชัน 'นักล่าภาพ' (Stealth Mode + Multi-Source)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพประกอบ (Bypass Mode)...")
    
    # ล้าง Prompt ให้สะอาดสำหรับ URL
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    seed = random.randint(1, 999999)
    
    # หลอกว่าเป็น Browser จริง (สำคัญมากเพื่อกัน GitHub โดนแบน IP)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    # รายชื่อแหล่งภาพ (ลองจากคุณภาพสูงสุดลงมา)
    sources = [
        f"https://pollinations.ai/p/{clean_p}?width=1080&height=1920&model=flux&seed={seed}&nologo=true",
        f"https://image.pollinations.ai/prompt/{clean_p}?width=1080&height=1920&seed={seed}",
        f"https://pollinations.ai/p/{clean_p}?width=1080&height=1920&model=turbo&seed={seed}"
    ]

    # เพิ่มการรอสุ่ม 5-10 วินาที เพื่อไม่ให้ Server ตกใจจนบล็อกเรา
    time.sleep(random.uniform(5, 10))

    for url in sources:
        try:
            r = requests.get(url, headers=headers, timeout=50)
            if r.status_code == 200 and len(r.content) > 40000:
                with open(filename, 'wb') as f:
                    f.write(r.content)
                # ตรวจสอบว่าไฟล์ภาพสมบูรณ์ (กัน FFmpeg Error 69)
                with Image.open(filename) as img:
                    img.verify()
                print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจริงสำเร็จ!")
                return True
        except:
            continue

    # หากล่มหมด ใช้ภาพกราฟิกสำรอง
    print(f"   ⚠️ ฉากที่ {scene_num}: AI ปฏิเสธการเชื่อมต่อ ใช้ภาพกราฟิกสำรอง")
    create_valid_slide(filename, prompt, scene_num)
    return False

def run_workflow():
    try:
        # 1. ร่างบทมหากาพย์
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์ 60 วินาที (DODI Style)...")
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        prompt_script = (
            f"Act as a Viral Thai Storyteller. Create a {SCENE_COUNT}-scene script. "
            "Topic: 'Deep Wisdom'. Each scene 10s. Thai voiceover. English visual prompts. "
            "Output JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"บทไทย...\", \"visual\": \"Detailed English 3D prompt\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_script)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย (โทนเสียงขลัง)...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพ
        print("🎨 3. กระบวนการเนรมิตภาพประกอบทีละฉาก...")
        scenes = data['scenes'][:SCENE_COUNT]
        for i, sc in enumerate(scenes):
            get_ai_image(f"{sc['visual']}, majestic lighting, unreal engine 5, 8k", f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ (Dynamic Zoom)
        print("🎬 4. กำลังประกอบ Video ด้วยเทคนิค Motion Zoom...")
        with open("l.txt", "w") as f:
            for i in range(len(scenes)):
                f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'")

        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2500:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,setsar=1\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print(f"🚀 5. อัปโหลดสู่ YouTube (สถานะ: {VIDEO_PRIVACY})...")
        if not os.path.exists('token.json'):
            print("⚠️ ไม่พบ token.json ข้ามการอัปโหลด")
            return

        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {"title": data['title'], "description": "#เรื่องเล่า #AI #DODI", "categoryId": "27"},
                    "status": {"privacyStatus": VIDEO_PRIVACY}
                },
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! เข้าไปตรวจงานใน YouTube Studio ของคุณได้เลย")
        except Exception as e:
            if "uploadLimitExceeded" in str(e):
                print("\n⚠️ โควตา YouTube วันนี้เต็ม! (รอ 24 ชม. ระบบจะรีเซ็ตให้เองครับ)")
            else: raise e

    except Exception as e:
        print(f"\n‼️ พังตรงนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
