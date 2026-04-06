import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

# --- ⚙️ การตั้งค่าคลิป ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 5
SCENE_DURATION = 12 
VIDEO_PRIVACY = "private"

def validate_and_save(img_data, filename):
    """สุดยอดตัวกรอง: ตรวจสอบว่าเป็นภาพจริงไหม และแปลงเป็น JPEG มาตรฐานเพื่อไม่ให้ FFmpeg พัง"""
    try:
        # ถ้าไฟล์เล็กเกิน 15KB มักจะเป็นหน้าเว็บ Error ไม่ใช่รูปภาพ
        if len(img_data) < 15000: 
            return False 
        
        # เปิดอ่านข้อมูลภาพจากหน่วยความจำ
        img = Image.open(io.BytesIO(img_data))
        # แปลงเป็น RGB เสมอ (ลบพื้นหลังใส Alpha ออก เพื่อป้องกัน FFmpeg Error 69)
        img = img.convert('RGB') 
        # เซฟเป็นไฟล์ JPEG ที่สมบูรณ์
        img.save(filename, 'JPEG', quality=95)
        return True
    except:
        return False

def fetch_lexica_ai_image(keyword, filename, scene_num):
    """ระบบไปดูดภาพ AI ระดับเทพที่มีคนสร้างไว้แล้ว (ไม่โดนบล็อกชัวร์ 100%)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังค้นหาภาพ AI ระดับ 8K จาก Lexica...")
    
    # ล้าง Keyword ให้พร้อมค้นหา
    clean_key = re.sub(r'[^\w\s]', '', keyword).strip().replace(' ', '+')
    url = f"https://lexica.art/api/v1/search?q={clean_key}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code == 200:
            data = res.json()
            if 'images' in data and len(data['images']) > 0:
                # เลือกรูปจาก 3 อันดับแรก เพื่อให้ได้รูปที่สวยที่สุดแต่ไม่ซ้ำซาก
                top_images = data['images'][:3]
                selected_image = random.choice(top_images)['src']
                
                # ดาวน์โหลดรูปนั้นมา
                img_data = requests.get(selected_image, timeout=30).content
                if validate_and_save(img_data, filename):
                    print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพ AI ของจริง สวยงามพร้อมใช้!")
                    return True
    except Exception as e:
        print(f"   ⚠️ ขัดข้อง: {str(e)}")

    # แผนสำรองถาวร: สร้างภาพสไลด์กราฟิกภายในเครื่อง ป้องกันจอดำ Error 69, 254
    print(f"   🔄 ค้นหาจาก Lexica ไม่เจอ... สร้างภาพสไลด์กราฟิกมหากาพย์สำรอง")
    img = Image.new('RGB', (1080, 1920), color=(15, 20, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 50, 1030, 1870], outline=(212, 175, 55), width=15)
    img.save(filename, 'JPEG', quality=95)
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 1. ให้ Gemini สุ่มหัวข้อการเงินจริง เขียนบท และคิดคีย์เวิร์ดสำหรับ "ค้นหาภาพ AI"
        print("🧠 1. AI Director กำลังสุ่มหัวข้อการเงินจริง เขียนบทและคีย์เวิร์ดภาพ...")
        prompt_sys = (
            "Act as a professional financial advisor. Randomly select ONE real financial concept (e.g., Compound Interest, DCA, Inflation, Emergency Fund, Dividend investing). "
            "Create a 60-second Thai YouTube Shorts script explaining this real concept with factual information. Structured into 5 scenes. "
            "For each scene, give me: 1. Thai voiceover text. 2. A precise English keyword to search for an epic 3D cinematic image representing the scene. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"keyword\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิปวันนี้: {data['title']}")

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-10% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. ดึงภาพ AI จากคลังภาพโลก (Lexica) - เสถียรกว่าสั่งสร้างใหม่
        print("🖼️ 3. เข้าสู่กระบวนการเตรียมภาพประกอบ AI (High Reliability Mode)...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            fetch_lexica_ai_image(sc['keyword'], f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ (ใส่ Effect ซูม Cinematic)
        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920,setsar=1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print(f"🚀 5. อัปโหลดสู่ YouTube (สถานะ: {VIDEO_PRIVACY})...")
        if not os.path.exists('token.json'): return
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! รอบนี้คลิปการเงินความรู้จริงต้องออกมาแน่นอน")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("\n⚠️ Quota YouTube เต็ม! รอ 24 ชม.")
            else: raise e

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
