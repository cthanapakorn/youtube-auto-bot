import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_cinematic_slide(path, scene_text, scene_num, mascot_name="ปู่วอลลี่"):
    """สร้างสไลด์กราฟิกคุณภาพสูงด้วยโค้ด (แผนไม้ตายถ้า AI/Stock ล่ม)"""
    # 1. สร้างพื้นหลังไล่สี (Gradient)
    base = Image.new('RGB', (1080, 1920), color=(10, 15, 30))
    d = ImageDraw.Draw(base)
    
    # วาดวงกลมเรืองแสงเป็น Mascot จำลอง (ปู่วอลลี่ตัวกลมๆ)
    d.ellipse([340, 700, 740, 1100], fill=(50, 100, 255)) # ตัว
    d.ellipse([450, 800, 500, 850], fill=(255, 255, 255)) # ตาซ้าย
    d.ellipse([580, 800, 630, 850], fill=(255, 255, 255)) # ตาขวา
    
    # วาดกรอบทอง Cinematic
    d.rectangle([40, 40, 1040, 1880], outline=(212, 175, 55), width=12)
    
    # ใส่ข้อความหัวข้อ
    d.text((100, 100), f"SCENE {scene_num}", fill=(212, 175, 55))
    # หมายเหตุ: ใน GitHub อาจไม่มีฟอนต์ไทย เราจะเน้นภาพประกอบที่รันผ่าน
    d.text((100, 1200), f">> M A S C O T   S T O R Y <<", fill=(255, 255, 255))
    
    base.save(path, 'JPEG', quality=95)
    print(f"   🎨 สร้างสไลด์กราฟิกอัตโนมัติสำหรับฉากที่ {scene_num}")

def fetch_image_pro(keyword, filename, scene_num):
    """ระบบดึงภาพ 3 ชั้น (Unsplash -> Pollinations -> Graphic Engine)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังควานหาภาพประกอบ...")
    
    # ชั้นที่ 1: ดึงจาก Unsplash (ภาพถ่ายจริง มักจะรอดจากการบล็อก)
    headers = {'User-Agent': 'Mozilla/5.0'}
    clean_key = re.sub(r'[^\w\s]', '', keyword).strip().replace(' ', ',')
    url_unsplash = f"https://images.unsplash.com/photo-1501167786227-4cba60f6d58f?w=1080&q=80" # Default 
    # ลองสุ่มภาพตาม keyword
    url_random = f"https://source.unsplash.com/featured/1080x1920?{clean_key}"
    
    try:
        r = requests.get(url_random, headers=headers, timeout=20)
        if r.status_code == 200 and len(r.content) > 50000:
            with open(filename, 'wb') as f: f.write(r.content)
            print(f"   ✅ ได้ภาพ Stock จาก Unsplash")
            return True
    except: pass

    # ชั้นที่ 2: ลอง AI Generator (Pollinations)
    url_ai = f"https://pollinations.ai/p/{clean_key.replace(',', '%20')}?width=1080&height=1920&model=flux&nologo=true"
    try:
        r = requests.get(url_ai, headers=headers, timeout=20)
        if r.status_code == 200 and len(r.content) > 50000:
            with open(filename, 'wb') as f: f.write(r.content)
            print(f"   ✅ ได้ภาพจาก AI Generator")
            return True
    except: pass

    # ชั้นที่ 3: แผนไม้ตาย (วาดรูปด้วยโค้ด) - การันตีไฟล์ไม่เสีย
    create_cinematic_slide(filename, keyword, scene_num)
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังวางแผนบทและ Keyword ภาพ...")
        prompt_sys = (
            "Act as a professional YouTuber. Create a 60s Thai storytelling script (6 scenes). "
            "For each scene, give me: 1. Thai script 2. A simple English keyword for image searching. "
            "Output JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"keyword\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:6]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการเตรียมภาพประกอบ (High Reliability Mode)...")
        for i, sc in enumerate(data['scenes'][:6]):
            fetch_image_pro(sc['keyword'], f"i_{i}.jpg", i+1)

        print("🎬 4. ตัดต่อ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(6): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")
        
        # ใช้คำสั่ง FFmpeg ที่ปลอดภัยที่สุดเพื่อกัน Error 69
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920,setsar=1,zoompan=z='min(zoom+0.001,1.2)':d=250:s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print("🚀 5. อัปโหลดสู่ YouTube (PRIVATE)...")
        if not os.path.exists('token.json'): return
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": "private"}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! ตรวจสอบวิดีโอได้ใน YouTube Studio")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("⚠️ Quota เต็ม! รอพรุ่งนี้")
            else: raise e

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
