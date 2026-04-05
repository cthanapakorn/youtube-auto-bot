import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def fetch_stock_image(keyword, filename, scene_num):
    """ระบบดึงภาพ Stock ฟรีจาก Unsplash (การันตี GitHub ไม่โดนบล็อก)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังควานหาภาพ Stock ที่เข้ากับบท...")
    
    # ล้างข้อความ keyword ให้สะอาด
    clean_key = re.sub(r'[^\w\s]', '', keyword).strip().replace(' ', ',')
    
    # URL สำหรับดึงภาพแบบสุ่มตาม Keyword (ขนาดสำหรับมือถือ 9:16)
    # เราใช้ Source.unsplash ซึ่งดึงได้ฟรีและไม่ค่อยโดนแบน IP
    url = f"https://source.unsplash.com/1080x1920/?{clean_key}"
    
    headers = {'User-Agent': 'Mozilla/5.0'}

    # พยายามดึงภาพ 3 ครั้ง
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200 and len(r.content) > 50000: # ต้องมีขนาด > 50KB ถึงจะนับว่าเป็นภาพจริง
                with open(filename, 'wb') as f: f.write(r.content)
                # ตรวจสอบไฟล์ว่าเสียไหม
                with Image.open(filename) as img: img.verify()
                print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพ Stock ที่สวยงาม!")
                return True
        except: pass
        time.sleep(2)

    # แผนสำรองสุดท้าย: ถ้า Unsplash ล่ม (ยากมาก) วาดรูปข้อความ
    print(f"   ⚠️ ฉากที่ {scene_num}: ดึงภาพไม่สำเร็จ วาดภาพกราฟิกสำรอง")
    img = Image.new('RGB', (1080, 1920), color=(10, 10, 20))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 50, 1030, 1870], outline=(212, 175, 55), width=12)
    d.text((100, 900), f"SCENE {scene_num}", fill=(212, 175, 55))
    img.save(filename, 'JPEG')
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 1. ให้ Gemini เขียนบท และคิด Keyword ภาษาอังกฤษสำหรับค้นหาภาพ
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์และคิด Keyword ภาพ...")
        prompt_sys = (
            "Act as a viral storytelling YouTuber. Create a 60s Thai script (6 scenes). "
            "For each scene, give me: 1. Thai voiceover text 2. One precise English keyword for finding a majestic, epic stock photo. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"keyword\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:6]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. ดึงภาพ Stock (6 ฉาก)
        print("🖼️ 3. เข้าสู่กระบวนการจัดเตรียมภาพ Stock (High Reliability Mode)...")
        for i, sc in enumerate(data['scenes'][:6]):
            # ใช้ Keyword ที่ Gemini คิดให้ ไปดึงรูปถ่ายจริง
            fetch_stock_image(sc['keyword'], f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ (ใส่ Effect ซูมให้ภาพมีชีวิต)
        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(6): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'") # บรรทัดสุดท้ายกัน Error
        
        # ใช้คำสั่ง FFmpeg ที่เสถียรที่สุดเพื่อกัน Error 69
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด (PRIVATE)
        print("🚀 5. อัปโหลดสู่ YouTube (สถานะ: private)...")
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
            print("✨ ภารกิจสำเร็จ! เข้าไปตรวจงานใน YouTube Studio ได้เลย")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("\n⚠️ Quota เต็ม! รอ 24 ชม.")
            else: raise e

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
