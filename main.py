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

def fetch_hf_only(prompt, filename, scene_num):
    """ฟังก์ชันสั่งวาดรูปจากที่อยู่ใหม่ (router.huggingface.co) ตามที่ Error แจ้งมา"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังสั่ง Hugging Face SDXL วาดรูป (New Endpoint)...")
    
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("      ❌ Error: ไม่พบ HF_TOKEN ใน GitHub Secrets!")
        return False
        
    # ✅ เปลี่ยนที่อยู่ตามที่ Error 410 แจ้งมา: ใช้ router.huggingface.co
    api_url = "https://router.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {hf_token.strip()}"}
    
    # ฝังคำสั่งสไตล์ Anime Meme ที่คุณต้องการ
    base_style = "anime meme style, exaggerated expressions, young Asian office worker, messy hair, dramatic, vibrant colors, high contrast"
    enhanced_prompt = f"{prompt}, {base_style}, 4k, cinematic lighting"
    
    for attempt in range(5):
        try:
            response = requests.post(api_url, headers=headers, json={"inputs": enhanced_prompt}, timeout=60)
            
            if response.status_code == 200:
                if response.headers.get('Content-Type', '').startswith('image'):
                    img = Image.open(io.BytesIO(response.content)).convert('RGB')
                    img.save(filename, 'JPEG', quality=95)
                    print(f"      ✅ สำเร็จ! ได้ภาพ AI คุณภาพสูง")
                    return True
                else:
                    print(f"      ⚠️ ได้รับข้อมูลที่ไม่ใช่รูปภาพ: {response.text[:200]}")
            elif response.status_code == 503 or response.status_code == 424:
                # กรณีโมเดลกำลังโหลด หรือ Overload ให้รอแล้วลองใหม่
                print(f"      🔄 โมเดลกำลังเตรียมตัว... รอ 20 วินาที (ครั้งที่ {attempt+1})")
                time.sleep(20)
            else:
                print(f"      ❌ API Error {response.status_code}: {response.text}")
                break 
                
        except Exception as e:
            print(f"      ❌ พังที่ระบบเชื่อมต่อ: {str(e)}")
            time.sleep(5)
            
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังสุ่มหัวข้อการเงินจริงและเขียนบท (Anime Meme Style)...")
        # สุ่มเนื้อหาการเงินจริง + สไตล์ Anime ฮาๆ
        prompt_sys = (
            "Act as a professional financial advisor. Randomly select ONE real financial concept (e.g., DCA, Inflation, Compound Interest). "
            "Create a 60s Thai script with 5 scenes. Use funny, relatable anime meme tone. "
            "Each scene must have: 1. Funny Thai voiceover. 2. Dramatic image prompt for the scene. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-5% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการวาดภาพ AI (Hugging Face Only)...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            success = fetch_hf_only(sc['prompt'], f"i_{i}.jpg", i+1)
            if not success:
                print(f"\n‼️ หยุดการทำงาน: ไม่สามารถสร้างภาพฉากที่ {i+1} ได้")
                sys.exit(1)

        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920,setsar=1,zoompan=z='min(zoom+0.002,1.3)':d=300:s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube...")
        if os.path.exists('token.json'):
            with open('token.json', 'r') as f:
                creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
            youtube = build("youtube", "v3", credentials=creds)
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! ไปดูผลงานใน Studio ได้เลยครับ")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
