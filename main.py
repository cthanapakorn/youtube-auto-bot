import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def get_ai_image(prompt, filename, scene_num):
    """ระบบดึงภาพ FLUX.1 แบบ Bypass Block และแก้ Error 410"""
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token: raise ValueError("❌ หา HF_TOKEN ใน Secrets ไม่เจอ!")

    # ใช้โมเดลที่เสถียรที่สุด: FLUX.1-schnell
    api_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {
        "Authorization": f"Bearer {hf_token.strip()}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังสั่งภาพจาก AI Cloud...")
    for attempt in range(5):
        try:
            response = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=60)
            if response.status_code == 200:
                with open(filename, 'wb') as f: f.write(response.content)
                with Image.open(filename) as img: img.verify()
                print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจริงแล้ว!")
                return True
            elif response.status_code in [503, 410, 429]:
                print(f"   ⚠️ Server ไม่พร้อม (Error {response.status_code}) รอ 20 วิ... (รอบ {attempt+1}/5)")
                time.sleep(20)
            else:
                print(f"   ❌ Error {response.status_code}: ลองใหม่...")
                time.sleep(5)
        except: time.sleep(5)
    
    # วาดรูปสำรองระดับพรีเมียม (ถ้า AI ล่มจริงๆ)
    img = Image.new('RGB', (1080, 1920), color=(15, 15, 25))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 50, 1030, 1870], outline=(212, 175, 55), width=15)
    d.text((120, 900), f"SCENE {scene_num}\n{prompt[:30]}...", fill=(212, 175, 55))
    img.save(filename, 'JPEG')
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 1. เขียนบทไทย
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์ 60 วินาที...")
        prompt_sys = (
            "Create a 60s viral Thai storytelling script. 6 scenes. Thai voiceover. "
            "Output JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"บทไทย...\", \"visual\": \"Detailed English prompt\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:6]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพ
        scenes = data['scenes'][:6]
        for i, sc in enumerate(scenes):
            get_ai_image(f"{sc['visual']}, cinematic, 8k, majestic", f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ
        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(len(scenes)): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")
        
        # ปรับ Scale ก่อน Zoom เพื่อไม่ให้ FFmpeg พัง
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4", shell=True, check=True)

        # 5. อัปโหลด
        print("🚀 5. อัปโหลดสู่ YouTube (PRIVATE)...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": "private"}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ!")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("\n⚠️ YouTube Quota เต็ม! รอ 24 ชม.")
            else: raise e

    except Exception as e:
        print(f"\n‼️ พบข้อผิดพลาด: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
