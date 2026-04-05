import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def get_mascot_image(prompt, filename, scene_num, mascot_desc):
    """สร้างภาพที่มี Mascot ตัวเดิม ในฉากที่แตกต่างกัน (สไตล์ Wally Investor)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพ Mascot...")
    
    # รวมรายละเอียด Mascot เข้ากับเนื้อหาฉาก
    full_prompt = f"{mascot_desc}, {prompt}, 3d render style, octane render, soft lighting, pastel colors, high detail, masterpiece, vertical 9:16"
    clean_p = re.sub(r'[^\w\s]', '', full_prompt).strip().replace(' ', '%20')
    seed = 42 # ใช้ Seed เดิมช่วยให้หน้าตัวละครใกล้เคียงกันมากขึ้น
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    # ใช้ Pollinations Flux เป็นหลัก เพราะสร้างตัวละครได้สวยและเสถียร
    url = f"https://pollinations.ai/p/{clean_p}?width=1080&height=1920&model=flux&seed={seed + scene_num}&nologo=true"
    
    try:
        time.sleep(random.uniform(5, 8)) # ป้องกันการโดนแบน IP
        r = requests.get(url, headers=headers, timeout=50)
        if r.status_code == 200 and len(r.content) > 50000:
            with open(filename, 'wb') as f: f.write(r.content)
            print(f"   ✅ ฉากที่ {scene_num}: ภาพ Mascot สำเร็จ!")
            return True
    except: pass

    # ถ้าล่มจริงๆ วาดภาพกราฟิกให้น่ารักๆ แทนจอดำ
    img = Image.new('RGB', (1080, 1920), color=(240, 240, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 50, 1030, 1870], outline=(100, 100, 255), width=10)
    d.text((150, 900), f"MASCOT SCENE {scene_num}", fill=(100, 100, 255))
    img.save(filename, 'JPEG')
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 1. ออกแบบตัวละครและบท (ตามสไตล์วิดีโอที่ส่งมา)
        print("🧠 1. AI Director กำลังออกแบบตัวละครและบทพูด...")
        # กำหนดลักษณะ Mascot ให้ Gemini จำไว้
        mascot_definition = "A cute, round, friendly 3d robot mascot with blue glowing eyes" 
        
        prompt_sys = (
            f"Act as a Mascot Storyteller. Create a 60s Thai script. "
            f"Mascot: {mascot_definition}. Topic: 'Wealth Secret'. "
            "Output JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"บทไทย...\", \"visual\": \"ฉากที่ Mascot กำลังทำอะไร...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย (โทนสดใส)...")
        full_text = " ".join([s['text'] for s in data['scenes'][:6]])
        subprocess.run(f'edge-tts --rate=+5% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพ Mascot
        print("🎨 3. กระบวนการสร้างภาพ Mascot ทีละฉาก...")
        for i, sc in enumerate(data['scenes'][:6]):
            get_mascot_image(sc['visual'], f"i_{i}.jpg", i+1, mascot_definition)

        # 4. ตัดต่อ (Dynamic Zoom)
        print("🎬 4. ประกอบวิดีโอ (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(6): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")
        
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.001,1.3)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print("🚀 5. อัปโหลดสู่ YouTube (PRIVATE)...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        youtube = build("youtube", "v3", credentials=creds)
        youtube.videos().insert(
            part="snippet,status",
            body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": "private"}},
            media_body=MediaFileUpload("final.mp4")
        ).execute()
        print("✨ ภารกิจสำเร็จ! เข้าไปตรวจความน่ารักใน Studio ได้เลย")

    except Exception as e:
        print(f"‼️ พัง: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
