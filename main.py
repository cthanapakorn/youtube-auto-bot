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

def fetch_hf_flux(prompt, filename, scene_num):
    """ใช้โมเดล FLUX.1-schnell ตัวแรงล่าสุด (แก้ทาง 404 และภาพสวยกว่าเดิม)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังสั่ง FLUX AI เนรมิตภาพ (Highest Quality)...")
    
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("      ❌ Error: ไม่พบ HF_TOKEN ใน Secrets!")
        return False
        
    # เปลี่ยนมาใช้ FLUX.1-schnell (โมเดลตัวท็อปปัจจุบันที่รองรับ API ฟรีได้ดีที่สุด)
    model_id = "black-forest-labs/FLUX.1-schnell"
    
    # เราจะลองทั้ง 2 Endpoint เผื่อระบบ Router ของเขาเอ๋อ
    endpoints = [
        f"https://api-inference.huggingface.co/models/{model_id}",
        f"https://router.huggingface.co/models/{model_id}"
    ]
    
    headers = {
        "Authorization": f"Bearer {hf_token.strip()}",
        "x-use-cache": "false" # บังคับเจนใหม่ ไม่เอาภาพเก่า
    }
    
    # ปรับ Prompt ให้เข้ากับสไตล์ Anime Meme ที่คุณต้องการ
    base_style = "high-quality anime style, exaggerated facial expressions, funny 2D animation look, vibrant colors, 4k resolution"
    full_prompt = f"{prompt}, {base_style}"

    for url in endpoints:
        print(f"      🎨 กำลังลองส่งคำสั่งไปที่: {url.split('/')[2]}")
        for attempt in range(3): # พยายามซ้ำกรณีโมเดลกำลัง Load
            try:
                response = requests.post(url, headers=headers, json={"inputs": full_text_prompt(full_prompt)}, timeout=90)
                
                if response.status_code == 200:
                    if response.headers.get('Content-Type', '').startswith('image'):
                        img = Image.open(io.BytesIO(response.content)).convert('RGB')
                        img.save(filename, 'JPEG', quality=95)
                        print(f"      ✅ สำเร็จ! ได้ภาพ AI คุณภาพระดับ FLUX")
                        return True
                elif response.status_code == 503:
                    print(f"      🔄 โมเดลกำลังอุ่นเครื่อง... รอ 25 วินาที")
                    time.sleep(25)
                else:
                    print(f"      ⚠️ API ตอบกลับ: {response.status_code} - {response.text[:100]}")
                    break 
            except Exception as e:
                print(f"      ❌ พังที่ระบบเชื่อมต่อ: {str(e)}")
                time.sleep(5)
    return False

def full_text_prompt(p): return p # Helper function

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังเขียนบทมหากาพย์การเงิน (Anime Meme Style)...")
        prompt_sys = (
            "Act as a viral YouTube creator. Create a 60s Thai script (5 scenes) about a real financial concept. "
            "Tone: Relatable anime meme style with funny exaggerated reactions. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-5% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการวาดภาพ AI (FLUX Engine Only)...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            success = fetch_hf_flux(sc['prompt'], f"i_{i}.jpg", i+1)
            if not success:
                print(f"\n‼️ หยุดการทำงาน: ไม่สามารถวาดรูปฉากที่ {i+1} ได้จาก FLUX API")
                sys.exit(1)

        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920,setsar=1,zoompan=z='min(zoom+0.0015,1.5)':d=300:s=1080x1920\" "
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
            print("✨ ภารกิจสำเร็จ! รอบนี้ภาพต้องมาแน่นอนครับ")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
