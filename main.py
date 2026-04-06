import os, re, json, subprocess, requests, sys, time, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# --- ⚙️ การตั้งค่าคลิป ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 5
SCENE_DURATION = 12 
VIDEO_PRIVACY = "private"

def validate_and_save(img_data, filename):
    """ฟอกไฟล์ภาพ ป้องกันจอดำและ Error 69"""
    try:
        # เช็คว่าเป็นไฟล์ภาพจริงไหม (ไม่ใช่ Error JSON ที่ส่งมาจาก API)
        if len(img_data) < 5000: return False 
        img = Image.open(io.BytesIO(img_data))
        img = img.convert('RGB') 
        img.save(filename, 'JPEG', quality=95)
        return True
    except:
        return False

def fetch_hf_image(prompt, filename, scene_num):
    """ส่งคำสั่งไปวาดรูปที่ Hugging Face (Stable Diffusion XL)"""
    print(f"   ⏳ ฉากที่ {scene_num}: สั่ง Hugging Face API วาดรูป...")
    
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("      ❌ พัง: ไม่พบ HF_TOKEN ใน GitHub Secrets! กรุณาไปเพิ่มก่อนครับ")
        return False
        
    # เพิ่ม Keyword ให้ภาพดูพรีเมียมและสวยงาม
    enhanced_prompt = f"{prompt}, highly detailed, cinematic lighting, masterpiece, 8k resolution, trending on artstation"
    
    # ใช้โมเดล SDXL (ตัวฟรีที่สวยที่สุด)
    api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {hf_token.strip()}"}
    payload = {"inputs": enhanced_prompt}

    # พยายามยิง API สูงสุด 5 ครั้ง (เพราะบางทีโมเดลฟรีต้องใช้เวลา 'อุ่นเครื่อง' หรือ Loading)
    for attempt in range(5):
        try:
            res = requests.post(api_url, headers=headers, json=payload, timeout=60)
            
            if res.status_code == 200:
                if validate_and_save(res.content, filename):
                    print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพ AI สวยๆ จาก Hugging Face แล้ว!")
                    return True
            elif res.status_code == 503:
                # 503 คือ Model กำลังโหลด (เรื่องปกติของของฟรี) ให้รอแล้วยิงใหม่
                wait_time = res.json().get('estimated_time', 15)
                print(f"      🔄 โมเดลกำลังอุ่นเครื่อง รอประมาณ {int(wait_time)} วินาที...")
                time.sleep(int(wait_time) + 2)
            else:
                print(f"      ⚠️ API ตอบกลับ: {res.status_code} - {res.text[:100]}")
                time.sleep(5)
        except Exception as e:
            print(f"      ⚠️ ขัดข้อง: {str(e)}")
            time.sleep(5)
            
    print(f"   ❌ ดึงภาพฉากที่ {scene_num} ไม่สำเร็จหลังจากพยายามหลายครั้ง")
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("ไม่พบ GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 1. ให้ Gemini สุ่มเนื้อหาการเงินจริง เขียนบท
        print("🧠 1. AI Director กำลังสุ่มหัวข้อการเงินจริงและเขียนบท...")
        prompt_sys = (
            "Act as a professional financial advisor. Randomly select ONE real financial concept (e.g., Compound Interest, DCA, Emergency Fund). "
            "Create a 60-second Thai YouTube Shorts script explaining this concept. Structure into 5 scenes. "
            "For each scene, give me: 1. Thai voiceover text. 2. A highly descriptive English prompt for an AI image generator to create a cinematic 3D illustration of this scene. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิปวันนี้: {data['title']}")

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-10% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. วาดภาพด้วย Hugging Face API
        print("🖼️ 3. เข้าสู่กระบวนการสั่งวาดภาพ AI ของจริง...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            success = fetch_hf_image(sc['prompt'], f"i_{i}.jpg", i+1)
            if not success:
                raise Exception(f"หยุดการทำงาน: สร้างภาพฉากที่ {i+1} ไม่สำเร็จ (ตรวจสอบ HF_TOKEN หรือลองรันใหม่)")

        # 4. ตัดต่อ (ใส่ Effect ซูม)
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
        print("✨ ภารกิจสำเร็จ! คลิปการเงินพร้อมภาพ AI ของจริงเสร็จสมบูรณ์แล้วครับ")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
