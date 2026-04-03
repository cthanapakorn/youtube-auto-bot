import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def download_image(url, filename):
    """ฟังก์ชันช่วยดาวน์โหลดและตรวจสอบไฟล์ภาพ"""
    try:
        r = requests.get(url, timeout=45)
        if r.status_code == 200 and len(r.content) > 30000: # ต้องมีขนาดมากกว่า 30KB ถึงจะนับว่าเป็นภาพจริง
            with open(filename, 'wb') as f: f.write(r.content)
            with Image.open(filename) as img: img.verify() # ตรวจสอบว่าไฟล์ไม่เสีย
            return True
    except: pass
    return False

def generate_real_image(prompt, filename, scene_num):
    """ระบบดึงภาพ 2 ชั้น (ถ้า Hugging Face ล่ม ให้ไป Pollinations ทันที)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพประกอบ...")
    
    # --- แผน A: ใช้ FLUX AI (ผ่าน Pollinations พร้อม Bypass Block) ---
    seed = random.randint(1, 1000000)
    clean_prompt = re.sub(r'[^\w\s]', '', prompt) # ล้างอักขระพิเศษ
    url_a = f"https://pollinations.ai/p/{clean_prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={seed}&nologo=true"
    
    if download_image(url_a, filename):
        print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจาก FLUX AI")
        return True

    # --- แผน B: ใช้ Stable Diffusion (ผ่าน Hugging Face) ---
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        api_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        headers = {"Authorization": f"Bearer {hf_token.strip()}"}
        try:
            res = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=60)
            if res.status_code == 200:
                with open(filename, 'wb') as f: f.write(res.content)
                print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจาก Stable Diffusion")
                return True
        except: pass

    # --- แผน C: วาดภาพกราฟิกข้อความ (ถ้าล่มหมดจริงๆ) ---
    print(f"   ⚠️ ฉากที่ {scene_num}: AI ล่มหมด! กำลังวาดภาพกราฟิกสำรอง...")
    img = Image.new('RGB', (1080, 1920), color=(15, 15, 25))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 50, 1030, 1870], outline=(255, 215, 0), width=15)
    d.text((100, 900), f"SCENE {scene_num}\n{prompt[:30]}...", fill=(255, 215, 0))
    img.save(filename, 'JPEG')
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 1. เขียนบทมหากาพย์
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์ 60 วินาที...")
        prompt = (
            "Create a 60s Thai viral storytelling script. 6 scenes. "
            "Thai voiceover. Detailed English prompts for image generation. "
            "Output JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"visual\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย (Rate -15%)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพ (6 ฉาก)
        print("🎨 3. เริ่มกระบวนการสร้างภาพประกอบทีละฉาก...")
        scenes = data['scenes'][:6]
        for i, sc in enumerate(scenes):
            # เนรมิตภาพด้วยระบบ 2 ชั้น
            generate_real_image(sc['visual'], f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ (Dynamic Zoom)
        print("🎬 4. กำลังประกอบวิดีโอ 60 วินาที...")
        with open("l.txt", "w") as f:
            for i in range(len(scenes)): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")

        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

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
            print("✨ สำเร็จ! วิดีโอถูกอัปโหลดเป็น 'ส่วนตัว' เรียบร้อยครับ")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("\n⚠️ โควตาวันนี้เต็ม! (รอ 24 ชม. นะครับ)")
            else: raise e

    except Exception as e:
        print(f"\n‼️ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
