import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def create_pro_fallback(path, text):
    """สร้างภาพพื้นหลังสไตล์ Infographic กรณีเว็บบล็อก"""
    img = Image.new('RGB', (1080, 1920), color=(10, 20, 30))
    d = ImageDraw.Draw(img)
    # วาดเส้นกราฟฟิกตกแต่ง
    d.rectangle([0, 0, 1080, 100], fill=(255, 215, 0)) # แถบบนสีทอง
    d.text((100, 900), f"STRATEGY: {text[:30]}...", fill=(255, 255, 255))
    img.save(path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ ไม่พบ API Key")
        
        client = genai.Client(api_key=api_key.strip())
        # ใช้รุ่นท็อปที่คุณมีในบัญชี
        selected_model = 'models/gemini-2.5-flash'

        print("🧠 1. กำลังวิเคราะห์คอนเทนต์ไวรัล (60 วินาที)...")
        # สั่ง AI ให้เขียนบทแบบมีจังหวะหยุด (ใช้ ... แทนการเว้นวรรค)
        viral_prompt = (
            "Act as a Viral Content Creator. Create a 60-second Thai YouTube Shorts script about 'Financial Secrets'. "
            "Structure: Hook (Shocking), 3 Value Points (Secretive), and Engagement Question. "
            "Important: Add '...' in text for natural pauses. "
            "Response ONLY JSON: {\"title\": \"...\", \"hashtags\": \"...\", \"scenes\": ["
            "{\"text\": \"(หยุด 1 วิ) คุณเคยสงสัยไหมว่า... ทำไมคนทำงานหนักถึงไม่รวยสักที?\", \"visual\": \"Cinematic 3D, stressed worker, dark office, golden aura, 8k\"},"
            "{\"text\": \"ข้อที่ 1... ความลับของดอกเบี้ยทบต้น... ที่โรงเรียนไม่เคยสอนคุณ!\", \"visual\": \"Futuristic bank vault, glowing coins multiplying, 3d render\"},"
            "{\"text\": \"ข้อที่ 2... หนี้ไม่ได้น่ากลัว... ถ้าคุณใช้มันซื้อสินทรัพย์ ไม่ใช่ของเล่น!\", \"visual\": \"Luxury house vs expensive car comparison, isometric cartoon\"},"
            "{\"text\": \"และข้อที่ 3... ทักษะที่ผลิตเงิน... สำคัญกว่าใบปริญญาหลายเท่า!\", \"visual\": \"Digital brain glowing with icons of money and skills, neon style\"},"
            "{\"text\": \"อยากรู้วิธีเริ่มไหม?... พิมพ์คำว่า 'เริ่ม' ในคอมเมนต์... แล้วผมจะส่งทางลัดให้!\", \"visual\": \"Confident person walking towards a bright city skyline, sunset\"}"
            "]}"
        )
        
        response = client.models.generate_content(model=selected_model, contents=viral_prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อไวรัล: {data['title']}")

        # 2. เสียงพากย์ (ปรับความเร็วและจังหวะ)
        print("🎙️ 2. ลงเสียงพากย์ (เว้นวรรคแบบธรรมชาติ)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        # ใช้ความเร็ว -10% เพื่อให้ดูมีน้ำหนักและน่าเชื่อถือ
        subprocess.run(f'edge-tts --rate=-10% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพประกอบ (Cinematic Cartoon Style)
        print("🎨 3. เนรมิตภาพประกอบระดับ 4K...")
        for i, sc in enumerate(data['scenes']):
            # ใส่ Prompt สำหรับสร้างภาพที่สวยและหยุดนิ้วคน
            style = "Masterpiece, cinematic lighting, 3D render style, vibrant colors, hyper-detailed, vertical 9:16"
            url = f"https://pollinations.ai/p/{sc['visual'].replace(' ', '%20')},{style.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 100000)}"
            
            success = False
            try:
                r = requests.get(url, timeout=40)
                if r.status_code == 200 and len(r.content) > 20000:
                    with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                    print(f"   📸 ฉากที่ {i+1}: ภาพสวยตรงปก!")
                    success = True
            except: pass
            
            if not success:
                create_pro_fallback(f"i_{i}.jpg", sc['text'])

        # 4. ตัดต่อ (เพิ่มเสียงเพลง + เอฟเฟกต์เคลื่อนไหว)
        print("🎬 4. กำลังตัดต่อแบบ Dynamic (ความยาว 60 วิ)...")
        with open("l.txt", "w") as f:
            # เฉลี่ยเวลา 5 ฉาก ให้ได้ฉากละประมาณ 11-12 วินาที
            for i in range(len(data['scenes'])):
                f.write(f"file 'i_{i}.jpg'\nduration 11.5\n")
            f.write(f"file 'i_{len(data['scenes'])-1}.jpg'")

        # ใช้คำสั่ง FFmpeg พิเศษ: เพิ่มการซูม (Zoom) และใส่ดนตรีประกอบแบบวนลูป
        # หมายเหตุ: เราจะใช้เสียงพากย์เป็นหลัก และใส่เพลงเบาๆ
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=300:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,setsar=1\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print("🚀 5. อัปโหลดสู่ YouTube (Status: Public)...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": data['title'],
                    "description": f"{data['title']}\n\n{data['hashtags']} #การเงิน #Shorts #เศรษฐี",
                    "categoryId": "27"
                },
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ ไวรัลสำเร็จ! ลิงก์คลิป: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ ติดปัญหา: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
