import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def get_ai_image(prompt, filename, scene_num):
    """ระบบ 'นักล่าภาพ' 3 ชั้น: HuggingFace API -> Stealth AI -> Stock Photo"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังควานหาภาพประกอบ...")
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip()
    hf_token = os.getenv("HF_TOKEN")
    
    # --- ชั้นที่ 1: Hugging Face (เสถียรที่สุดถ้ามี Token) ---
    if hf_token:
        # ใช้โมเดล SDXL ที่รองรับการใช้งานผ่าน API สูง
        api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {hf_token.strip()}"}
        try:
            res = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=60)
            if res.status_code == 200:
                with open(filename, 'wb') as f: f.write(res.content)
                print(f"   ✅ สำเร็จ! ได้ภาพจาก Hugging Face")
                return True
        except: pass

    # --- ชั้นที่ 2: Pollinations (Stealth Mode) ---
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    url_p = f"https://pollinations.ai/p/{clean_p.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1,99999)}&nologo=true"
    try:
        time.sleep(random.uniform(2, 5)) # รอจังหวะสุ่ม
        r = requests.get(url_p, headers=headers, timeout=40)
        if r.status_code == 200 and len(r.content) > 50000:
            with open(filename, 'wb') as f: f.write(r.content)
            print(f"   ✅ สำเร็จ! ได้ภาพจาก Pollinations AI")
            return True
    except: pass

    # --- ชั้นที่ 3: Stock Photo Backup (แผนไม้ตายเพื่อให้เห็นภาพจริง 100%) ---
    print(f"   🔄 AI ล่ม... กำลังดึงภาพ Stock คุณภาพสูง (Unsplash) มาแทน...")
    keywords = "ancient, cinematic, epic, mystery" # คีย์เวิร์ดกลางๆ ให้เข้ากับมหากาพย์
    url_stock = f"https://source.unsplash.com/1080x1920/?{keywords.replace(' ', ',')}"
    try:
        r = requests.get(url_stock, timeout=30)
        if r.status_code == 200:
            with open(filename, 'wb') as f: f.write(r.content)
            print(f"   ✅ สำเร็จ! ใช้ภาพมหากาพย์จาก Stock Library")
            return True
    except: pass

    # ถ้าล่มหมดจริงๆ (ยากมาก) วาดรูปข้อความ
    img = Image.new('RGB', (1080, 1920), color=(5, 5, 10))
    d = ImageDraw.Draw(img)
    d.rectangle([40,40,1040,1880], outline=(212,175,55), width=12)
    img.save(filename, 'JPEG')
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์...")
        prompt_sys = (
            "Act as a Viral Storyteller. Create a 60s Thai script (6 scenes). "
            "Output JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"บทไทย...\", \"visual\": \"Epic English prompt\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:6]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🎨 3. กำลังดึงภาพประกอบ (6 ฉาก)...")
        for i, sc in enumerate(data['scenes'][:6]):
            get_ai_image(sc['visual'], f"i_{i}.jpg", i+1)

        print("🎬 4. ประกอบวิดีโอ (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(6): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")
        
        # ปรับ Scale และซูม
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4", shell=True, check=True)

        print("🚀 5. อัปโหลดสู่ YouTube (PRIVATE)...")
        if not os.path.exists('token.json'): return
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": "private"}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ สำเร็จ!")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("⚠️ Quota เต็ม! รอพรุ่งนี้")
            else: raise e

    except Exception as e:
        print(f"‼️ พัง: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
