import os, re, json, subprocess, requests, sys, time, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# --- ⚙️ การตั้งค่าคลิป ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 5   # จำนวนฉาก
SCENE_DURATION = 12 # ความยาวต่อฉาก (รวม 60 วินาที)
VIDEO_PRIVACY = "private"

def fetch_hf_only(prompt, filename, scene_num):
    """ฟังก์ชันสั่งวาดรูปจาก Hugging Face โดยตรง (ไม่มีระบบสำรอง)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังสั่ง Hugging Face SDXL วาดรูป...")
    
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("      ❌ Error: ไม่พบ HF_TOKEN ใน GitHub Secrets!")
        return False
        
    # URL โมเดล Stable Diffusion XL (ตัวที่สวยที่สุดของสายฟรี)
    api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {hf_token.strip()}"}
    
    # ปรับจูน Prompt ให้เป็นสไตล์ Anime Meme / Epic ตามที่คุณต้องการ
    enhanced_prompt = f"{prompt}, anime style, high quality, vibrant colors, cinematic lighting, 4k"
    
    # พยายามยิง API (Retry loop สำหรับกรณี Model กำลัง Load)
    for attempt in range(5):
        try:
            response = requests.post(api_url, headers=headers, json={"inputs": enhanced_prompt}, timeout=60)
            
            if response.status_code == 200:
                # ตรวจสอบว่าเป็นไฟล์ภาพจริงไหม
                if response.headers.get('Content-Type', '').startswith('image'):
                    img = Image.open(io.BytesIO(response.content)).convert('RGB')
                    img.save(filename, 'JPEG', quality=95)
                    print(f"      ✅ สำเร็จ! ได้ภาพ AI คุณภาพสูง")
                    return True
                else:
                    print(f"      ⚠️ ได้รับข้อมูลที่ไม่ใช่รูปภาพ: {response.text[:200]}")
            elif response.status_code == 503:
                # กรณีโมเดลกำลังอุ่นเครื่อง (Loading)
                wait_time = response.json().get('estimated_time', 20)
                print(f"      🔄 โมเดลกำลังโหลด... รอ {int(wait_time)} วินาที (ครั้งที่ {attempt+1})")
                time.sleep(int(wait_time) + 2)
            else:
                # 🚨 แจ้ง Error จริงจาก Server ให้คุณเห็น
                print(f"      ❌ API Error {response.status_code}: {response.text}")
                break # ถ้า Error อื่นๆ ให้หยุดเพื่อเช็คสาเหตุ
                
        except Exception as e:
            print(f"      ❌ พังที่ระบบเชื่อมต่อ: {str(e)}")
            time.sleep(5)
            
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังสุ่มหัวข้อการเงินจริงและเขียนบท...")
        # สุ่มหัวข้อการเงินจากข้อมูลจริง
        prompt_sys = (
            "Act as a professional financial advisor. Randomly select ONE real financial concept (e.g., Compound Interest, DCA, Inflation, Emergency Fund). "
            "Create a 60-second Thai YouTube Shorts script explaining this concept with facts. "
            f"Structure into {SCENE_COUNT} scenes. "
            "For each scene, provide: 1. Thai voiceover text. 2. A descriptive English prompt for an anime-style illustration. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-10% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการวาดภาพ AI (Hugging Face Only)...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            success = fetch_hf_only(sc['prompt'], f"i_{i}.jpg", i+1)
            if not success:
                print(f"\n‼️ หยุดการทำงาน: ไม่สามารถสร้างภาพฉากที่ {i+1} ได้ (โปรดเช็ค Error ด้านบน)")
                sys.exit(1) # บังคับให้ Workflow แดงถ้าภาพไม่มา

        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        # FFmpeg แบบเน้นคุณภาพ
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920,setsar=1,zoompan=z='min(zoom+0.0015,1.5)':d=300:s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube (สถานะ: {VIDEO_PRIVACY})...")
        if os.path.exists('token.json'):
            with open('token.json', 'r') as f:
                creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
            youtube = build("youtube", "v3", credentials=creds)
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! คลิปของคุณพร้อมแล้วใน YouTube Studio")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
