import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def get_ai_image(prompt, filename, scene_num):
    """ระบบ 'นักล่าภาพ' สลับ 3 แหล่ง (SD 2.1 > SD 1.5 > Pollinations)"""
    hf_token = os.getenv("HF_TOKEN")
    
    # รายชื่อโมเดลใน Hugging Face ที่เสถียรที่สุด (ไม่ค่อย Error 410)
    hf_models = [
        "stabilityai/stable-diffusion-2-1",
        "runwayml/stable-diffusion-v1-5"
    ]
    
    headers = {
        "Authorization": f"Bearer {hf_token.strip()}" if hf_token else "",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"
    }

    print(f"   ⏳ ฉากที่ {scene_num}: กำลังหาช่องทางดึงภาพ...")

    # --- แผน A: ลอง Hugging Face ทีละโมเดล ---
    if hf_token:
        for model in hf_models:
            api_url = f"https://api-inference.huggingface.co/models/{model}"
            try:
                res = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=40)
                if res.status_code == 200:
                    with open(filename, 'wb') as f: f.write(res.content)
                    print(f"   ✅ สำเร็จ! ได้ภาพจาก {model}")
                    return True
                else:
                    print(f"   ⚠️ {model} ตอบกลับ Error {res.status_code}")
            except: continue

    # --- แผน B: ถ้าข้างบนล่มหมด ใช้ Pollinations (Flux Engine) ---
    print(f"   🔄 แผนสำรอง: ดึงภาพผ่าน Pollinations...")
    seed = random.randint(1, 999999)
    url_p = f"https://pollinations.ai/p/{prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={seed}&nologo=true"
    try:
        r = requests.get(url_p, timeout=30)
        if r.status_code == 200:
            with open(filename, 'wb') as f: f.write(r.content)
            print(f"   ✅ สำเร็จ! ได้ภาพจาก Pollinations")
            return True
    except: pass

    # --- แผน C: วาดสไลด์เอง (ป้องกันวิดีโอพัง) ---
    print(f"   ❌ AI ทุกตัวปฏิเสธ! วาดสไลด์พรีเมียมให้แทน...")
    img = Image.new('RGB', (1080, 1920), color=(10, 10, 20))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 1040, 1880], outline=(212, 175, 55), width=15)
    d.text((120, 900), f"LEGEND SCENE {scene_num}\n{prompt[:30]}...", fill=(212, 175, 55))
    img.save(filename, 'JPEG')
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())

        # 1. ร่างบทมหากาพย์
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์ 60 วินาที...")
        response = client.models.generate_content(
            model='models/gemini-2.5-flash', 
            contents="Create 60s viral Thai Story script. 6 scenes. Output JSON: {\"title\":\"...\",\"scenes\":[{\"text\":\"...\",\"visual\":\"Detailed English prompt\"}]}"
        )
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:6]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพ
        for i, sc in enumerate(data['scenes'][:6]):
            get_ai_image(f"{sc['visual']}, cinematic, 8k, dramatic lighting", f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ (Dynamic Zoom)
        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(6): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")
        
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4", shell=True, check=True)

        # 5. อัปโหลด (PRIVATE)
        print("🚀 5. อัปโหลดสู่ YouTube (สถานะ: ส่วนตัว)...")
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
        print(f"\n‼️ พังตรงนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
