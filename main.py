import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageFilter

# --- CONFIGURATION ---
MODEL_ID = 'models/gemini-2.5-flash'
VOICE = "th-TH-NiwatNeural"
SCENE_COUNT = 6  # 6 ฉาก ฉากละ 10 วินาที = 60 วินาที
VIDEO_STATUS = "private" # ตั้งเป็น private เพื่อตรวจงานก่อน

def create_emergency_slide(path, text, scene_num):
    """แผนสำรองสุดท้าย: วาดภาพ Cinematic สไตล์มหากาพย์ (Gold-Black) ถ้า AI ล่มหมด"""
    img = Image.new('RGB', (1080, 1920), color=(5, 5, 10))
    d = ImageDraw.Draw(img)
    # วาดกรอบหรูๆ
    d.rectangle([40, 40, 1040, 1880], outline=(212, 175, 55), width=15)
    # ใส่ข้อความไทย
    display_text = f"ตำนานบทที่ {scene_num}\n\n{text[:30]}..."
    d.text((120, 900), display_text, fill=(212, 175, 55))
    img.save(path, 'JPEG')

def get_ai_image(prompt, filename, scene_num):
    """ระบบ Hybrid Image: พยายามจิกภาพจาก AI หลายแหล่งเพื่อเลี่ยงการโดนบล็อก IP"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพประกอบ...")
    clean_prompt = re.sub(r'[^\w\s]', '', prompt).strip()
    seed = random.randint(1, 999999)
    
    # หลอกว่าเป็น Browser จริง (Bypass GitHub Action block)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # แผน A: Pollinations (Flux Model)
    url_a = f"https://pollinations.ai/p/{clean_prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={seed}&nologo=true"
    
    # แผน B: Hugging Face (ถ้ามี Token)
    hf_token = os.getenv("HF_TOKEN")
    
    # ลองแผน A
    try:
        r = requests.get(url_a, headers=headers, timeout=40)
        if r.status_code == 200 and len(r.content) > 50000:
            with open(filename, 'wb') as f: f.write(r.content)
            with Image.open(filename) as img: img.verify()
            print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจาก Flux AI")
            return True
    except: pass

    # ลองแผน B (Stable Diffusion)
    if hf_token:
        try:
            api_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
            auth_h = {"Authorization": f"Bearer {hf_token.strip()}"}
            res = requests.post(api_url, headers=auth_h, json={"inputs": prompt}, timeout=60)
            if res.status_code == 200:
                with open(filename, 'wb') as f: f.write(res.content)
                print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจากแผนสำรอง (SD)")
                return True
        except: pass

    # ถ้าล่มหมด ใช้แผน C (วาดเอง)
    create_emergency_slide(filename, prompt, scene_num)
    return False

def run_workflow():
    try:
        # 0. เตรียม API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ Missing GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())

        # 1. เขียนบท (AI Director)
        print("🧠 1. AI Director กำลังร่างบทมหากาพย์ 60 วินาที...")
        prompt_system = (
            f"Act as a Viral Storyteller. Create a {SCENE_COUNT}-scene Thai script about 'Ancient Mysteries'. "
            "Each scene must be 10 seconds. Voiceover in THAI. Visual prompts in ENGLISH. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"visual\": \"Detailed 3D cinematic prompt\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_system)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อ: {data['title']}")

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย (Rate -15% เพื่อความขลัง)...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-15% --voice "{VOICE}" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างรูปภาพ
        print("🎨 3. กระบวนการสร้างภาพประกอบ...")
        scenes = data['scenes'][:SCENE_COUNT]
        for i, sc in enumerate(scenes):
            get_ai_image(sc['visual'], f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ (Dynamic Zoom)
        print("🎬 4. กำลังประกอบวิดีโอ (Ken Burns Effect)...")
        with open("l.txt", "w") as f:
            for i in range(len(scenes)):
                f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_{len(scenes)-1}.jpg'") # ป้องกัน ffmpeg duration bug

        # FFmpeg: ปรับ Scale ให้สูงก่อน Zoom เพื่อภาพไม่แตก
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2500:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,setsar=1\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print(f"🚀 5. อัปโหลดสู่ YouTube (สถานะ: {VIDEO_STATUS})...")
        if not os.path.exists('token.json'):
            print("⚠️ ไม่พบไฟล์ token.json ข้ามการอัปโหลด (แต่คลิปสร้างเสร็จแล้ว)")
            return

        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {"title": data['title'], "description": "#เรื่องเล่า #AI #DODI", "categoryId": "27"},
                    "status": {"privacyStatus": VIDEO_STATUS}
                },
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! วิดีโอของคุณพร้อมแล้ว")
        except Exception as e:
            if "uploadLimitExceeded" in str(e):
                print("\n⚠️ โควตา YouTube เต็ม! (รอ 24 ชม.) แต่ไฟล์วิดีโอ 'final.mp4' สร้างเสร็จแล้วใน Artifacts")
            else: raise e

    except Exception as e:
        print(f"\n‼️ พบข้อผิดพลาด: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
