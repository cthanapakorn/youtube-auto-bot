import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

# --- ⚙️ การตั้งค่าคลิป ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 5   # ปรับเป็น 5 ฉากตามสคริปต์
SCENE_DURATION = 12 # ฉากละ 12 วินาที = 60 วินาทีพอดี
VIDEO_PRIVACY = "private"

def validate_and_save(img_data, filename):
    """ฟอกไฟล์ภาพ ป้องกันจอดำและ Error 69"""
    try:
        if len(img_data) < 15000: return False 
        img = Image.open(io.BytesIO(img_data))
        img = img.convert('RGB') 
        img.save(filename, 'JPEG', quality=95)
        return True
    except:
        return False

def create_emergency_bg(filename, scene_num):
    """แผนไม้ตาย ถ้าระบบวาดรูปพังหมด"""
    img = Image.new('RGB', (1080, 1920), color=(30, 20, 40))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 1040, 1880], outline=(255, 100, 100), width=15)
    d.text((100, 900), f"ANIME SCENE {scene_num}\nSystem Error", fill=(255, 100, 100))
    img.save(filename, 'JPEG', quality=95)

def fetch_anime_image(action_prompt, filename, scene_num):
    """ระบบวาดภาพสไตล์ Anime Meme มนุษย์เงินเดือน"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังวาดภาพ Anime Meme...")
    
    # 📌 ฝัง Base Style ที่คุณต้องการลงไปในทุกรูป
    base_style = "anime meme style, young Asian office worker 25 years old, messy hair, over-exaggerated emotion, funny chaotic energy, vibrant colors, high contrast"
    full_prompt = f"{action_prompt}, {base_style}"
    
    clean_p = re.sub(r'[^\w\s,]', '', full_prompt).strip()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # 1. ใช้ AI Generator (Flux) ที่เก่งเรื่องลายเส้นอนิเมะ
    try:
        # ล็อก Seed เป็นตัวเลขชุดเดียวกันเพื่อให้หน้าตาตัวละครใกล้เคียงกันทุกฉาก
        seed = 8888 + scene_num 
        url_pol = f"https://pollinations.ai/p/{clean_p.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={seed}&nologo=true"
        img_data = requests.get(url_pol, headers=headers, timeout=30).content
        if validate_and_save(img_data, filename):
            print(f"   ✅ ได้ภาพ Anime Meme ฉากที่ {scene_num} แล้ว!")
            return True
    except: pass

    # 2. แผนสำรอง: ดึงรูป Anime ฮาๆ จาก Lexica
    try:
        url_lexica = f"https://lexica.art/api/v1/search?q=funny+anime+office+worker+reaction"
        res = requests.get(url_lexica, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            if 'images' in data and len(data['images']) > 0:
                img_url = random.choice(data['images'][:5])['src']
                img_data = requests.get(img_url, timeout=20).content
                if validate_and_save(img_data, filename):
                    print(f"   ✅ ได้ภาพ Anime สำรองจาก Lexica")
                    return True
    except: pass

    create_emergency_bg(filename, scene_num)
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. AI Director กำลังเขียนบทจาก 5 ฉากที่คุณกำหนด...")
        
        # 📌 สั่งให้ Gemini เขียนบทตาม Storyline 5 ฉากของคุณเป๊ะๆ
        prompt_sys = (
            "Act as a funny viral YouTube creator. Create a 60-second Thai story script based EXACTLY on these 5 scenes:\n"
            "1: extreme happy face, checking salary notification, glowing background\n"
            "2: suddenly shocked, surrounded by flying bills (rent, credit card), comedic panic\n"
            "3: screaming internally, looking at empty bank balance on phone\n"
            "4: dead inside expression, sitting in dark room eating instant noodles, ghost leaving body\n"
            "5: fake motivation mode, determined pose holding notebook 'budget plan', messy room\n\n"
            "For each scene, give me: 1. A relatable and funny Thai voiceover text. 2. The specific English action to draw the anime image.\n"
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย (ฟีลลิ่งตลกขบขัน)...")
        # เปลี่ยนเป็น Rate 0% หรือ -5% ให้เสียงฟังดูเป็นธรรมชาติขึ้นสำหรับคลิปตลก
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-5% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการวาดภาพ Anime 5 ฉาก...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            # ส่งคำสั่งเฉพาะของฉากนั้นๆ ไปให้ฟังก์ชันวาดรูป
            fetch_anime_image(sc['prompt'], f"i_{i}.jpg", i+1)

        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920,setsar=1,zoompan=z='min(zoom+0.002,1.3)':d=300:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
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
                body={"snippet": {"title": data['title'], "categoryId": "23"}, "status": {"privacyStatus": VIDEO_PRIVACY}}, # หมวดหมู่ Comedy
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! ไปดูผลงานมนุษย์เงินเดือนใน Studio ได้เลยครับ")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("\n⚠️ Quota YouTube เต็ม! รอ 24 ชม.")
            else: raise e

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
