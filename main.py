import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

# --- ⚙️ CONFIGURATION ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 6
SCENE_DURATION = 10 
VIDEO_PRIVACY = "private"

def get_stealth_image(prompt, filename, scene_num):
    """ระบบ 'Ghost Generator' ดึงภาพ 3 ชั้น: HuggingFace -> Pollinations -> Unsplash"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพ (Stealth Mode)...")
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip()
    seed = random.randint(1, 9999999)
    hf_token = os.getenv("HF_TOKEN")

    # --- หัวใจสำคัญ: หลอก Server ว่าเป็นคนจริงๆ ---
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Referer': 'https://pollinations.ai/'
    }

    # 1. ลอง Hugging Face (SDXL) - มักจะรอดถ้ามี Token
    if hf_token:
        try:
            api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
            res = requests.post(api_url, headers={"Authorization": f"Bearer {hf_token.strip()}"}, json={"inputs": prompt}, timeout=60)
            if res.status_code == 200:
                with open(filename, 'wb') as f: f.write(res.content)
                print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจาก Hugging Face")
                return True
        except: pass

    # 2. ลอง Pollinations (สุ่มรอเพื่อหลบการแบน)
    time.sleep(random.uniform(8, 15)) # หน่วงเวลาให้เหมือนคนกด
    url_p = f"https://pollinations.ai/p/{clean_p.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={seed}&nologo=true"
    try:
        r = requests.get(url_p, headers=headers, timeout=45)
        if r.status_code == 200 and len(r.content) > 50000:
            with open(filename, 'wb') as f: f.write(r.content)
            with Image.open(filename) as img: img.verify()
            print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจาก Pollinations")
            return True
    except: pass

    # 3. แผนไม้ตาย (Unsplash Stock) - เพื่อให้เห็นภาพจริง 100%
    print(f"   🔄 AI ปฏิเสธ... ดึงภาพมหากาพย์จาก Stock แทน...")
    url_stock = f"https://source.unsplash.com/1080x1920/?ancient,epic,cinematic,temple,{scene_num}"
    try:
        r = requests.get(url_stock, timeout=30)
        if r.status_code == 200:
            with open(filename, 'wb') as f: f.write(r.content)
            print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพจาก Stock Library")
            return True
    except: pass

    # 4. แผนสำรองสุดท้าย (วาดเอง)
    img = Image.new('RGB', (1080, 1920), color=(10, 10, 20))
    d = ImageDraw.Draw(img)
    d.rectangle([40,40,1040,1880], outline=(212,175,55), width=15)
    img.save(filename, 'JPEG')
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์ 60 วินาที...")
        prompt_sys = (
            f"Act as a Viral Thai Storyteller. Create a {SCENE_COUNT}-scene script. "
            "Topic: 'Deep Legend'. Each scene 10s. Thai voiceover. English visual prompts. "
            "Output JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"บทไทย...\", \"visual\": \"Epic English prompt\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย (Rate -15%)...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🎨 3. กระบวนการเนรมิตภาพประกอบ (6 ฉาก)...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            get_stealth_image(sc['visual'], f"i_{i}.jpg", i+1)

        print("🎬 4. ประกอบวิดีโอด้วยเทคนิค Motion Zoom...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'")
        
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -vf \"scale=2500:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4", shell=True, check=True)

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
            print("✨ ภารกิจสำเร็จ!")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("⚠️ YouTube Quota เต็ม! รอ 24 ชม.")
            else: raise e

    except Exception as e:
        print(f"‼️ พัง: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
