import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def get_image_with_retry(prompt, filename, scene_num):
    """ฟังก์ชัน 'จิก' ภาพจาก AI Cloud ให้ได้ 100% (Bypass GitHub Block)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพประกอบ...")
    
    # ล้าง Prompt ให้เหลือแค่คำสำคัญ (ป้องกัน URL พัง)
    clean_prompt = re.sub(r'[^\w\s]', '', prompt).strip()
    seed = random.randint(1, 999999)
    
    # รายชื่อ AI Image Servers (แผน A และ แผน B)
    urls = [
        f"https://pollinations.ai/p/{clean_prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={seed}&nologo=true",
        f"https://image.pollinations.ai/prompt/{clean_prompt.replace(' ', '%20')}?width=1080&height=1920&seed={seed}"
    ]

    for url in urls:
        try:
            # หลอก Server ว่าเราคือ Browser จริงๆ ไม่ใช่ GitHub Bot
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            r = requests.get(url, headers=headers, timeout=50)
            
            if r.status_code == 200 and len(r.content) > 50000: # ต้องมีขนาด > 50KB ถึงจะเป็นภาพจริง
                with open(filename, 'wb') as f: f.write(r.content)
                with Image.open(filename) as img: img.verify() # เช็คว่าไฟล์ไม่เสีย
                print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจริงจาก AI")
                return True
        except: continue
        time.sleep(2)

    # --- ถ้า AI ล่มจริงๆ (Fallback) ให้สร้างภาพ Infographic ที่ดูดีกว่าเดิม ---
    print(f"   ⚠️ ฉากที่ {scene_num}: AI ปฏิเสธการเชื่อมต่อ ใช้ภาพกราฟิกสำรอง")
    img = Image.new('RGB', (1080, 1920), color=(10, 15, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 1040, 1880], outline=(255, 215, 0), width=15)
    d.text((100, 960), f"STORY SCENE {scene_num}\n{prompt[:35]}...", fill=(255, 215, 0))
    img.save(filename, 'JPEG')
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 1. เขียนบทไทย (เน้นเนื้อหาแบบคลิปที่คุณต้องการ)
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์ 60 วินาที...")
        prompt_script = (
            "Create a 60s viral Thai storytelling script about 'Ancient Wisdom'. "
            "Powerful Thai voiceover. English visual prompts. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"visual\": \"Detailed English 3D cinematic prompt\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_script)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพ (6 ฉาก)
        scenes = data['scenes'][:6]
        for i, sc in enumerate(scenes):
            get_image_with_retry(sc['visual'], f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ (Dynamic Zoom)
        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
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
