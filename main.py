import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def get_image_pro(prompt, filename, scene_num):
    """ระบบดึงภาพ 3 ชั้น (Hugging Face > Pollinations > Fallback)"""
    hf_token = os.getenv("HF_TOKEN")
    
    # --- ชั้นที่ 1: Hugging Face (ใช้ Token ของคุณ) ---
    if hf_token:
        print(f"   ⏳ ฉากที่ {scene_num}: กำลังดึงภาพจาก Hugging Face (SDXL)...")
        api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {hf_token.strip()}"}
        try:
            res = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=60)
            if res.status_code == 200:
                with open(filename, 'wb') as f: f.write(res.content)
                print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจริงจาก SDXL")
                return True
        except: pass

    # --- ชั้นที่ 2: Pollinations (Bypass Mode) ---
    print(f"   ⏳ ฉากที่ {scene_num}: แผน A ล่ม... กำลังลอง Pollinations (Bypass Mode)...")
    url_p = f"https://pollinations.ai/p/{prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1,99999)}"
    try:
        r = requests.get(url_p, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        if r.status_code == 200 and len(r.content) > 50000:
            with open(filename, 'wb') as f: f.write(r.content)
            print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจริงจาก Flux AI")
            return True
    except: pass

    # --- ชั้นที่ 3: Fallback (วาดรูปสวยๆ เองถ้า AI ล่มหมด) ---
    print(f"   ❌ AI ทุกตัวปฏิเสธ! กำลังวาดสไลด์พรีเมียมให้แทน...")
    img = Image.new('RGB', (1080, 1920), color=(10, 15, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 50, 1030, 1870], outline=(212, 175, 55), width=15)
    d.text((120, 900), f"LEGEND SCENE {scene_num}\n{prompt[:30]}...", fill=(212, 175, 55))
    img.save(filename, 'JPEG')
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())

        # 1. ร่างบท 60 วินาที (สั่งให้เขียนบทพากย์ไทยยาวพิเศษ)
        print("🧠 1. AI กำลังเขียนบทมหากาพย์ 'ยาว 60 วินาที'...")
        prompt_ai = (
            "Act as a Master Storyteller. Create a 60-second Thai viral script. "
            "IMPORTANT: The script must be LONG (at least 200 words) to cover 60 seconds. "
            "Structure: 6 scenes, each 10 seconds. Thai voiceover. English visual prompts. "
            "Output JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"บทพากย์ไทยยาวๆ...\", \"visual\": \"Detailed English prompt\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_ai)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:6]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพ
        scenes = data['scenes'][:6]
        for i, sc in enumerate(scenes):
            get_image_pro(sc['visual'], f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ (Dynamic Zoom)
        print("🎬 4. กำลังประกอบวิดีโอ (Ken Burns Effect)...")
        with open("l.txt", "w") as f:
            for i in range(len(scenes)):
                f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")

        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด (PRIVATE)
        print("🚀 5. อัปโหลดสู่ YouTube (ส่วนตัว)...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": "private"}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ สำเร็จ! วิดีโอถูกส่งขึ้นช่องแล้ว (เข้าไปดูที่ 'วิดีโอส่วนตัว' นะครับ)")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("\n⚠️ โควตาวันนี้เต็ม! (รอ 24 ชม. นะครับ)")
            else: raise e

    except Exception as e:
        print(f"\n‼️ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
