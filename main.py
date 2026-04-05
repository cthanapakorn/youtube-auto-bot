import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

# --- ⚙️ การตั้งค่าคลิป ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 6
SCENE_DURATION = 10 
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
    except Exception as e:
        return False

def fetch_safe_image(keyword, filename, scene_num):
    """ระบบดูดภาพที่ป้องกันไฟล์เสีย 100%"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังค้นหาภาพ AI ระดับ 8K...")
    
    clean_key = re.sub(r'[^\w\s]', '', keyword).strip().replace(' ', '+')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # --- แหล่งที่ 1: Lexica.art (ดึงรูป AI ที่สวยงาม) ---
    try:
        url_lexica = f"https://lexica.art/api/v1/search?q={clean_key}"
        res = requests.get(url_lexica, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            if 'images' in data and len(data['images']) > 0:
                top_images = data['images'][:5] # สุ่มจาก 5 รูปแรก
                img_url = random.choice(top_images)['src']
                img_data = requests.get(img_url, timeout=20).content
                
                if validate_and_save(img_data, filename):
                    print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพ AI สวยงามจาก Lexica!")
                    return True
    except: pass

    # --- แหล่งที่ 2: Pollinations (AI แบบไม่ใช้ Token) ---
    try:
        print(f"   🔄 ค้นหา Lexica ไม่สำเร็จ ลองดึงภาพจาก Pollinations...")
        url_pol = f"https://image.pollinations.ai/prompt/{clean_key}?width=1080&height=1920&nologo=true"
        img_data = requests.get(url_pol, headers=headers, timeout=25).content
        if validate_and_save(img_data, filename):
            print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจากระบบ AI สำรอง!")
            return True
    except: pass

    # --- แหล่งที่ 3: LoremFlickr (แทน Unsplash ที่พังไปแล้ว) ---
    try:
        print(f"   🔄 ดึงภาพ Stock เผื่อฉุกเฉิน...")
        url_flickr = f"https://loremflickr.com/1080/1920/{clean_key.replace('+', ',')}"
        img_data = requests.get(url_flickr, headers=headers, timeout=20).content
        if validate_and_save(img_data, filename):
            print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพ Stock ใช้งานได้จริง!")
            return True
    except: pass

    # แผนสุดท้ายจริงๆ วาดสีพื้นหลังสวยๆ ป้องกัน Error 69 ถาวร
    print(f"   ⚠️ ระบบภาพขัดข้อง สร้างภาพกราฟิกทดแทนเพื่อไม่ให้คลิปพัง")
    img = Image.new('RGB', (1080, 1920), color=(15, 20, 30))
    img.save(filename, 'JPEG')
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. AI Director กำลังเขียนบทและคิดคีย์เวิร์ดภาพมหากาพย์...")
        prompt_sys = (
            "Act as a viral YouTube creator. Create a 60s Thai story script (6 scenes). "
            "Topic: 'The Secret of Success'. "
            "For each scene, give me: 1. Thai voiceover text. 2. A highly specific 2-3 word English keyword for image searching (e.g., 'golden temple', 'rich man', 'ancient coin'). "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"keyword\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการดึงภาพ ป้องกันไฟล์เสีย (Error 69)...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            fetch_safe_image(sc['keyword'], f"i_{i}.jpg", i+1)

        print("🎬 4. กำลังประกอบ Video พร้อมเทคนิค Cinematic Zoom...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920,setsar=1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

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
            print("✨ ภารกิจสำเร็จ! ไม่เจอ Error 69 แล้ว เข้าไปตรวจคลิปได้เลย")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("\n⚠️ Quota YouTube เต็ม! รอ 24 ชม.")
            else: raise e

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
