import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

# --- ⚙️ การตั้งค่า ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 6
SCENE_DURATION = 10 
VIDEO_PRIVACY = "private"

def create_emergency_bg(filename, scene_num):
    """แผนไม้ตายก้นหีบ: ถ้าระบบพังหมด วาดภาพพื้นหลังสีขลังๆ ขึ้นมาเอง เพื่อไม่ให้ FFmpeg พัง"""
    img = Image.new('RGB', (1080, 1920), color=(15, 20, 25))
    d = ImageDraw.Draw(img)
    # วาดกรอบสีทองแดง
    d.rectangle([40, 40, 1040, 1880], outline=(184, 115, 51), width=15)
    img.save(filename, 'JPEG', quality=95)
    print(f"   ⚠️ สร้างภาพพื้นหลังฉุกเฉินสำหรับฉากที่ {scene_num} (ป้องกันวิดีโอพัง)")

def validate_and_save(img_data, filename):
    """ฟอกไฟล์ภาพ: ตรวจสอบว่าเป็นภาพจริง และแปลงเป็น JPEG มาตรฐาน"""
    try:
        if len(img_data) < 15000: return False 
        img = Image.open(io.BytesIO(img_data))
        img = img.convert('RGB') 
        img.save(filename, 'JPEG', quality=95)
        return True
    except:
        return False

def fetch_epic_image(prompt, filename, scene_num):
    """ระบบดึงภาพมหากาพย์ที่อุดรอยรั่วทุกจุด"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพมหากาพย์...")
    
    # เพิ่ม Keyword ระดับเทพให้ภาพดูขลัง
    epic_prompt = f"{prompt}, cinematic lighting, highly detailed, unreal engine 5, masterpiece, 8k"
    clean_p = re.sub(r'[^\w\s]', '', epic_prompt).strip()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # 1. ลองดึงจาก Lexica.art (ภาพ AI ที่สวยและไม่บล็อก IP)
    try:
        url_lexica = f"https://lexica.art/api/v1/search?q={clean_p.replace(' ', '+')}"
        res = requests.get(url_lexica, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            if 'images' in data and len(data['images']) > 0:
                img_url = random.choice(data['images'][:3])['src']
                img_data = requests.get(img_url, timeout=20).content
                if validate_and_save(img_data, filename):
                    print(f"   ✅ ได้ภาพ AI มหากาพย์จาก Lexica!")
                    return True
    except: pass

    # 2. ลอง AI Pollinations (สุ่ม Seed เลี่ยงบล็อก)
    try:
        seed = random.randint(1, 999999)
        url_pol = f"https://image.pollinations.ai/prompt/{clean_p.replace(' ', '%20')}?width=1080&height=1920&seed={seed}&nologo=true"
        img_data = requests.get(url_pol, headers=headers, timeout=25).content
        if validate_and_save(img_data, filename):
            print(f"   ✅ ได้ภาพมหากาพย์จาก Pollinations!")
            return True
    except: pass

    # 3. ลอง Stock Photo จาก LoremFlickr (แทน Unsplash ที่ตายไปแล้ว)
    try:
        url_flickr = f"https://loremflickr.com/1080/1920/epic,ancient"
        img_data = requests.get(url_flickr, headers=headers, timeout=20).content
        if validate_and_save(img_data, filename):
            print(f"   ✅ ได้ภาพ Stock สำรอง!")
            return True
    except: pass

    # 4. ถ้าทุกอย่างบนโลกอินเทอร์เน็ตล่มหมด... บังคับสร้างไฟล์ภาพด้วยโค้ด!
    create_emergency_bg(filename, scene_num)
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์ (60 วินาที)...")
        prompt_sys = (
            "Act as a professional YouTube Storyteller. Create a 60s Thai script (6 scenes). "
            "Tone: powerful, emotional, deep Thai wisdom. "
            "For each scene, give me: 1. Thai voiceover text 2. A 3-4 word specific English keyword for image searching (e.g., 'ancient gold temple', 'buddha statue lighting'). "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"keyword\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการเตรียมภาพประกอบมหากาพย์...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            fetch_epic_image(sc['keyword'], f"i_{i}.jpg", i+1)

        print("🎬 4. กำลังประกอบ Video (60 วินาที) ด้วย Cinematic Zoom...")
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
            print("✨ ภารกิจสำเร็จ! ไม่เจอ Error หาไฟล์ไม่เจอแล้วครับ")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("\n⚠️ Quota YouTube เต็ม! รอ 24 ชม.")
            else: raise e

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
