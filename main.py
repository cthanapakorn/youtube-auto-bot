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

def fetch_hf_smart(prompt, filename, scene_num):
    """ระบบวาดรูปอัจฉริยะ: ลอง SDXL ถ้าพัง (404/503) จะสลับไป SD 1.5 ทันที"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังสั่ง Hugging Face วาดรูป...")
    
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("      ❌ Error: ไม่พบ HF_TOKEN!")
        return False
        
    # รายชื่อโมเดลที่เราจะลอง (เรียงจากสวยสุดไปหาตัวที่ติดง่ายสุด)
    # เราจะกลับไปใช้ Endpoint มาตรฐานแต่ปรับ Path ให้ถูกต้อง
    models = [
        "stabilityai/stable-diffusion-xl-base-1.0",
        "runwayml/stable-diffusion-v1-5",
        "prompthero/openjourney"
    ]
    
    headers = {"Authorization": f"Bearer {hf_token.strip()}"}
    base_style = "anime meme style, exaggerated expressions, young Asian office worker, messy hair, dramatic, vibrant colors, high contrast"
    enhanced_prompt = f"{prompt}, {base_style}, 4k"

    for model in models:
        api_url = f"https://api-inference.huggingface.co/models/{model}"
        try:
            print(f"      🎨 พยายามใช้โมเดล: {model.split('/')[-1]}...")
            response = requests.post(api_url, headers=headers, json={"inputs": enhanced_prompt}, timeout=60)
            
            if response.status_code == 200:
                if response.headers.get('Content-Type', '').startswith('image'):
                    img = Image.open(io.BytesIO(response.content)).convert('RGB')
                    img.save(filename, 'JPEG', quality=95)
                    print(f"      ✅ สำเร็จ! ได้ภาพจาก {model.split('/')[-1]}")
                    return True
            elif response.status_code == 503:
                wait_time = response.json().get('estimated_time', 20)
                print(f"      🔄 โมเดลกำลังโหลด... รอ {int(wait_time)} วินาที")
                time.sleep(int(wait_time) + 2)
                # ลองตัวเดิมอีกรอบหลังรอ
                response = requests.post(api_url, headers=headers, json={"inputs": enhanced_prompt}, timeout=60)
                if response.status_code == 200:
                    img = Image.open(io.BytesIO(response.content)).convert('RGB')
                    img.save(filename, 'JPEG', quality=95)
                    return True
            else:
                print(f"      ⚠️ {model.split('/')[-1]} ตอบกลับ Error {response.status_code} (กำลังสลับตัวใหม่...)")
                continue # ลองโมเดลถัดไปใน List
                
        except Exception as e:
            print(f"      ❌ พังที่ระบบเชื่อมต่อ: {str(e)}")
            continue
            
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังสุ่มหัวข้อการเงินจริงและเขียนบท (Anime Meme Style)...")
        prompt_sys = (
            "Act as a professional financial advisor. Randomly select ONE real financial concept. "
            "Create a 60s Thai script with 5 scenes. Funny anime meme tone. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-5% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการวาดภาพ AI (Multi-Model HF)...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            success = fetch_hf_smart(sc['prompt'], f"i_{i}.jpg", i+1)
            if not success:
                print(f"\n‼️ หยุดการทำงาน: ไม่สามารถวาดรูปฉากที่ {i+1} ได้จากทุกโมเดล")
                sys.exit(1)

        print("🎬 4. กำลังประกอบ Video...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -vf \"scale=1080:1920,setsar=1\" -c:v libx264 -pix_fmt yuv420p -shortest final.mp4", shell=True, check=True)

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
            print("✨ ภารกิจสำเร็จ!")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
