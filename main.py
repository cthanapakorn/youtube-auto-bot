import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def generate_external_image(prompt, filename):
    """ดึงพลังจาก FLUX.1 (โมเดลที่เทพที่สุดตอนนี้) มาวาดรูปให้"""
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token: raise ValueError("❌ อย่าลืมใส่ HF_TOKEN ใน GitHub Secrets!")

    # เปลี่ยนมาใช้ FLUX.1-schnell (คุณภาพสูงมากและเสถียร)
    api_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {
        "Authorization": f"Bearer {hf_token.strip()}",
        "User-Agent": "Mozilla/5.0" # ป้องกันการโดนบล็อก
    }
    payload = {"inputs": prompt}

    print(f"   ⏳ กำลังส่งคำสั่งไปที่ FLUX AI Server...")
    for attempt in range(5):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                with open(filename, 'wb') as f: f.write(response.content)
                # ตรวจสอบว่าไฟล์ที่ได้มาเป็นรูปภาพจริง ไม่ใช่ไฟล์เสีย (ป้องกัน Error 69)
                with Image.open(filename) as img:
                    img.verify()
                print("   ✅ ดึงภาพ FLUX 8K สำเร็จ!")
                return True
            elif response.status_code in [503, 410, 429]:
                print(f"   ⏳ AI กำลังเตรียมตัว... รอ 20 วิ (รอบที่ {attempt+1}/5)")
                time.sleep(20)
            else:
                print(f"   ⚠️ Server Error {response.status_code}: กำลังลองใหม่...")
                time.sleep(10)
        except:
            time.sleep(5)
    
    # ถ้าดึงไม่ได้จริงๆ วาดรูปสำรองเองเพื่อให้งานไม่ค้าง (ป้องกัน Error 69)
    print("   ⚠️ AI Cloud ไม่ตอบสนอง วาดรูปสำรองอัตโนมัติ...")
    img = Image.new('RGB', (1080, 1920), color=(10, 15, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 1040, 1880], outline=(255, 215, 0), width=15)
    img.save(filename, 'JPEG')
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 1. เขียนบทไทย
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์ภาษาไทย...")
        prompt = (
            "Create a 60s viral Thai storytelling script. 6 scenes. "
            "Thai voiceover. Detailed English prompts for FLUX image gen. "
            "Output JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"visual\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ (Rate -15%)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพจากภายนอก (FLUX)
        print("🎨 3. สั่งวาดรูปจาก FLUX AI Cloud...")
        scenes = data['scenes'][:6]
        for i, sc in enumerate(scenes):
            print(f"--- ฉากที่ {i+1}/6 ---")
            enhanced_prompt = f"{sc['visual']}, cinematic, hyper-realistic, majestic, 8k, vertical 9:16"
            generate_external_image(enhanced_prompt, f"i_{i}.jpg")

        # 4. ตัดต่อ (Dynamic Zoom)
        print("🎬 4. ประกอบวิดีโอ 60 วินาที...")
        with open("l.txt", "w") as f:
            for i in range(len(scenes)): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")

        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,setsar=1\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด (PRIVATE)
        print("🚀 5. อัปโหลดสู่ YouTube (Status: Private)...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": "private"}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ สำเร็จ! วิดีโอถูกสร้างและอัปโหลดเป็นส่วนตัวแล้ว")
        except Exception as e:
            if "uploadLimitExceeded" in str(e):
                print("\n⚠️ โควตา YouTube วันนี้เต็ม! (แต่ VDO เสร็จแล้ว)")
            else: raise e

    except Exception as e:
        print(f"\n‼️ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
