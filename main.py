import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

# --- ⚙️ การตั้งค่าคลิป (5 ฉาก x 12 วินาที = 60 วินาทีพอดี) ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 5
SCENE_DURATION = 12 
VIDEO_PRIVACY = "private"

def validate_and_save(img_data, filename):
    """ฟอกไฟล์ภาพ: ตรวจสอบและแปลงเป็น JPEG มาตรฐานเพื่อป้องกัน FFmpeg Error 69"""
    try:
        if len(img_data) < 10000: return False 
        img = Image.open(io.BytesIO(img_data))
        img = img.convert('RGB') 
        img.save(filename, 'JPEG', quality=95)
        return True
    except: return False

def fetch_image_master(prompt, filename, scene_num):
    """ระบบรวมพลังสร้างภาพ: Hugging Face (หลัก) -> Lexica (รอง) -> Graphic (สำรอง)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพประกอบ...")
    hf_token = os.getenv("HF_TOKEN")
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip()
    
    # --- 1. Hugging Face API (ภาพ AI สวยที่สุด) ---
    if hf_token:
        print(f"      🎨 สั่ง Hugging Face SDXL วาดรูป...")
        api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {hf_token.strip()}"}
        # เพิ่มสไตล์มหากาพย์
        epic_prompt = f"{clean_p}, 3d cinematic render, masterpiece, 8k, highly detailed"
        
        for attempt in range(3): # พยายาม 3 ครั้งเผื่อโมเดลกำลังโหลด
            try:
                res = requests.post(api_url, headers=headers, json={"inputs": epic_prompt}, timeout=60)
                if res.status_code == 200:
                    if validate_and_save(res.content, filename):
                        print(f"      ✅ สำเร็จ! ได้ภาพ AI จาก Hugging Face")
                        return True
                elif res.status_code == 503: # โมเดลกำลัง Loading
                    wait = res.json().get('estimated_time', 20)
                    time.sleep(wait + 2)
                else: break
            except: pass

    # --- 2. Lexica API (ภาพ AI สำรองที่เสถียรมาก) ---
    try:
        print(f"      🔍 ค้นหาภาพ AI สำรองจาก Lexica...")
        url_lex = f"https://lexica.art/api/v1/search?q={clean_p.replace(' ', '+')}"
        res = requests.get(url_lex, timeout=20)
        if res.status_code == 200:
            img_url = random.choice(res.json()['images'][:5])['src']
            img_data = requests.get(img_url, timeout=20).content
            if validate_and_save(img_data, filename):
                print(f"      ✅ สำเร็จ! ได้ภาพจาก Lexica")
                return True
    except: pass

    # --- 3. แผนมหาอุด (วาดเองด้วยโค้ด) ---
    print(f"      ⚠️ สร้างภาพกราฟิกสำรอง (ป้องกันวิดีโอพัง)")
    img = Image.new('RGB', (1080, 1920), color=(15, 20, 35))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 1040, 1880], outline=(212, 175, 55), width=15)
    img.save(filename, 'JPEG')
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 1. Gemini สุ่มหัวข้อการเงินจริงและเขียนบท
        print("🧠 1. Gemini กำลังสุ่มหัวข้อการเงินจริงและเขียนบท...")
        prompt_sys = (
            "Act as a professional financial advisor. Randomly select ONE real financial concept (e.g., Compound Interest, DCA, Emergency Fund, Inflation). "
            "Create a 60-second Thai YouTube Shorts script explaining this concept. Structure into 5 scenes. "
            "For each scene, give me: 1. Thai voiceover text. 2. A descriptive English image prompt for a 3D cinematic illustration. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อวันนี้: {data['title']}")

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-10% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. เตรียมภาพ (High Reliability Mode)
        print("🖼️ 3. เข้าสู่กระบวนการเตรียมภาพประกอบ...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            fetch_image_master(sc['prompt'], f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ
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
        youtube.videos().insert(
            part="snippet,status",
            body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
            media_body=MediaFileUpload("final.mp4")
        ).execute()
        print("✨ ภารกิจสำเร็จ! รอบนี้คลิปต้องออกมาสวยและมีสาระแน่นอนครับ")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
