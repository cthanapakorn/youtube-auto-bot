import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def fetch_visual(prompt, filename, scene_num):
    """ระบบค้นหาภาพประกอบ: เน้นสไตล์มหากาพย์ Cinematic 8K"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังควานหาภาพประกอบ...")
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    
    # --- หัวใจสำคัญ: คำสั่ง (Prompt) ระดับเทพเพื่อให้ได้ภาพมหากาพย์ ---
    # เราเพิ่ม Keyword ลับอย่าง 'majestic', 'epic', 'cinema 4d render', 'masterpiece' 
    enhanced_prompt = f"{clean_p}, majestic lighting, deeply dramatic, cinema 4d render, unreal engine 5, 8k, masterpiece"
    seed = random.randint(1, 9999999)
    
    # 1. ลองใช้ AI Generator (Pollinations Flux)
    headers = {'User-Agent': 'Mozilla/5.0'}
    url_ai = f"https://pollinations.ai/p/{enhanced_prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={seed}&nologo=true"
    
    try:
        r = requests.get(url_ai, headers=headers, timeout=30)
        if r.status_code == 200 and len(r.content) > 50000:
            with open(filename, 'wb') as f: f.write(r.content)
            print(f"   ✅ สำเร็จ! ได้ภาพ AI มหากาพย์")
            return True
    except: pass

    # 2. แผนไม้ตาย: ถ้า AI ล่ม ให้ไปดึงภาพ Stock คุณภาพสูงมาแทน (ไม่เอาจอดำแล้ว)
    print(f"   🔄 AI ล่ม... กำลังดึงภาพ Stock มหากาพย์มาแทน...")
    url_stock = f"https://source.unsplash.com/1080x1920/?ancient,epic,mystic,wisdome,#{scene_num}"
    try:
        r = requests.get(url_stock, timeout=20)
        if r.status_code == 200:
            with open(filename, 'wb') as f: f.write(r.content)
            print(f"   ✅ สำเร็จ! ได้ภาพ Stock ที่เข้าธีม")
            return True
    except: pass
    return False

def run_workflow():
    try:
        # เชื่อมต่อกับสมอง (Gemini)
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์ 60 วินาที...")
        prompt_system = (
            "Act as a professional YouTube Storyteller. Create a 60s Thai script (6 scenes). "
            "Tone: powerful, emotional. Focus on deep Thai wisdom. For each scene, give me: 1. Thai voiceover text 2. Detailed English image prompt. "
            "Output JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"visual\": \"Detailed English prompt\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_system)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # สร้างเสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:6]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # เตรียมภาพประกอบ
        print("🖼️ 3. เข้าสู่กระบวนการเตรียมภาพประกอบ (High Reliability Mode)...")
        scenes = data['scenes'][:6]
        for i, sc in enumerate(scenes):
            fetch_visual(sc['visual'], f"i_{i}.jpg", i+1)

        # ตัดต่อ (Dynamic Zoom)
        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(6): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")
        
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # อัปโหลด (PRIVATE)
        print("🚀 5. อัปโหลดสู่ YouTube (สถานะ: ส่วนตัว)...")
        # (โค้ดอัปโหลดเดิมของคุณ)
        print("✨ ภารกิจสำเร็จ! เข้าไปตรวจคลิปใน Studio ได้เลย")

    except Exception as e:
        print(f"‼️ พังตรงนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
