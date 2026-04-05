import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

# --- ⚙️ การตั้งค่า ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 6
SCENE_DURATION = 10 
VIDEO_PRIVACY = "private"

def get_stealth_image(prompt, filename, scene_num):
    """ฟังก์ชันดึงภาพ AI แบบ Stealth Mode เพื่อป้องกันการโดน GitHub บล็อก IP"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพตามบทพูด...")
    
    # ล้างข้อความให้สะอาด
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    seed = random.randint(1, 9999999)
    
    # หลอก Server ว่าเราเป็นคนเล่นเว็บจริงๆ (สำคัญมาก!)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': 'https://pollinations.ai/'
    }

    # รายชื่อโมเดล AI (ถ้าตัวหนึ่งพัง จะสลับไปอีกตัวทันที)
    sources = [
        f"https://pollinations.ai/p/{clean_p}?width=1080&height=1920&model=flux&seed={seed}&nologo=true",
        f"https://image.pollinations.ai/prompt/{clean_p}?width=1080&height=1920&seed={seed}"
    ]

    # สุ่มเวลารอ 7-12 วินาที เพื่อไม่ให้เหมือนบอท
    time.sleep(random.uniform(7, 12))

    for url in sources:
        try:
            r = requests.get(url, headers=headers, timeout=50)
            if r.status_code == 200 and len(r.content) > 50000:
                with open(filename, 'wb') as f: f.write(r.content)
                with Image.open(filename) as img: img.verify()
                print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจริงสำเร็จ!")
                return True
        except: continue

    # แผนสุดท้าย: ถ้า AI ล่มจริงๆ ให้ไปดึงภาพ Stock คุณภาพสูงมาแทน (ไม่เอาจอดำแล้ว)
    print(f"   🔄 AI ล่ม... กำลังดึงภาพ Stock ที่ตรงกับบทมาแทน...")
    url_stock = f"https://source.unsplash.com/1080x1920/?ancient,epic,wisdom,{scene_num}"
    try:
        r = requests.get(url_stock, timeout=30)
        if r.status_code == 200:
            with open(filename, 'wb') as f: f.write(r.content)
            print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจาก Stock Library")
            return True
    except: pass

    # ถ้าพังหมดจริงๆ ค่อยวาดสไลด์
    img = Image.new('RGB', (1080, 1920), color=(10, 10, 20))
    img.save(filename, 'JPEG')
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 1. ให้ Gemini เขียนบท และวิเคราะห์คำสั่งสร้างภาพจากบทนั้น
        print("🧠 1. Gemini กำลังเขียนบทและออกแบบคำสั่งสร้างภาพ (Prompt Engineer Mode)...")
        # เราสั่งให้ Gemini คิดตัวละคร Mascot แบบคลิปที่คุณชอบด้วย
        mascot_style = "A cute 3d round robot mascot, friendly face, blue glow, octane render style"
        
        prompt_sys = (
            f"Act as a Professional Content Creator. 1. Write a 60s Thai storytelling script (6 scenes). "
            f"2. For each scene, create a very detailed English image prompt featuring: {mascot_style}. "
            "The prompt must describe what the mascot is doing in that specific scene. "
            "Output JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"บทไทย...\", \"visual_prompt\": \"Detailed English prompt\"}]}"
        )
        
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย (Rate -15% เพื่อความขลัง)...")
        full_voice_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_voice_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพจากบท (โดยใช้ Prompt ที่ Gemini เขียนให้)
        print("🎨 3. กระบวนการเนรมิตภาพประกอบทีละฉาก...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            # ส่งคำสั่งภาษาอังกฤษที่ Gemini เขียนให้ ไปสร้างรูป
            get_stealth_image(f"{sc['visual_prompt']}, majestic lighting, 8k, cinematic", f"i_{i}.jpg", i+1)

        # 4. ประกอบวิดีโอ (60 วินาที)
        print("🎬 4. ประกอบวิดีโอด้วยเทคนิค Motion Zoom...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'")
        
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -vf \"scale=2500:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4", shell=True, check=True)

        # 5. อัปโหลด
        print(f"🚀 5. อัปโหลดสู่ YouTube (สถานะ: {VIDEO_PRIVACY})...")
        if not os.path.exists('token.json'): return
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! เข้าไปตรวจงานใน YouTube Studio ได้เลย")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("⚠️ YouTube Quota เต็ม! รอ 24 ชม.")
            else: raise e

    except Exception as e:
        print(f"‼️ พังตรงนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
