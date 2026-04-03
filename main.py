import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def create_viral_fallback(path, text):
    """สร้างภาพแนว Infographic สไตล์ Modern เมื่อเว็บสร้างรูปล่ม"""
    img = Image.new('RGB', (1080, 1920), color=(18, 18, 18))
    d = ImageDraw.Draw(img)
    # วาดกรอบสีเหลืองทองให้ดูแพง
    d.rectangle([40, 40, 1040, 1880], outline=(255, 215, 0), width=20)
    # ใส่ข้อความหลัก
    d.text((100, 900), f"STRATEGY: {text[:25]}...", fill=(255, 215, 0))
    img.save(path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ ไม่พบ API Key")
        
        client = genai.Client(api_key=api_key.strip())
        selected_model = 'models/gemini-2.5-flash'

        # 1. ร่างเนื้อหา (6 ฉาก เพื่อให้ยาว 50-60 วิ)
        print("🧠 1. AI กำลังออกแบบคอนเทนต์ไวรัลและ 'ซับไตเติล'...")
        viral_prompt = (
            "Create a viral 60s Thai Finance Shorts. Use a 'Dark Secret' hook. "
            "Response ONLY JSON: {\"title\": \"...\", \"hashtags\": \"...\", \"scenes\": ["
            "{\"text\": \"(หยุด 1 วิ) ทำไมคนรวยถึงยิ่งรวย... ขณะที่คุณยังเหนื่อย?\", \"visual\": \"Cinematic 3D, gold coins in dark room, lighting, 8k\"},"
            "{\"text\": \"...\", \"visual\": \"...\"}, {\"text\": \"...\", \"visual\": \"...\"},"
            "{\"text\": \"...\", \"visual\": \"...\"}, {\"text\": \"...\", \"visual\": \"...\"},"
            "{\"text\": \"ถ้าอยากรู้วิธีแก้... พิมพ์ 'พร้อม' แล้วผมจะบอก!\", \"visual\": \"Futuristic city sunrise, success\"}]}"
        )
        
        response = client.models.generate_content(model=selected_model, contents=viral_prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อ: {data['title']}")

        # 2. เสียงพากย์ (Rate -12% เพื่อให้ดูขลังและน่าเชื่อถือ)
        print("🎙️ 2. สร้างเสียงพากย์ (Natural Pacing)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-12% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. เตรียมภาพประกอบ (3D Cinematic Style)
        print("🎨 3. กำลังสร้างภาพประกอบให้สอดคล้องกับเนื้อหา...")
        for i, sc in enumerate(data['scenes']):
            # ใส่สไตล์ 3D Animation ให้หยุดนิ้วคน
            style = "Masterpiece, 3D render style, octane render, vibrant, cinematic, vertical 9:16"
            url = f"https://pollinations.ai/p/{sc['visual'].replace(' ', '%20')},{style.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 99999)}"
            
            success = False
            try:
                r = requests.get(url, timeout=40)
                if r.status_code == 200 and len(r.content) > 20000:
                    with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                    print(f"   📸 ฉากที่ {i+1}: ภาพระดับ 4K พร้อม!")
                    success = True
            except: pass
            
            if not success:
                print(f"   ⚠️ ฉากที่ {i+1}: ใช้ระบบวาดภาพสำรอง")
                create_viral_fallback(f"i_{i}.jpg", sc['text'])

        # 4. ตัดต่อ (ใส่ Dynamic Zoom และซับไตเติล)
        print("🎬 4. กำลังประกอบวิดีโอ (60 วินาที + Zoom Effects)...")
        with open("l.txt", "w") as f:
            for i in range(len(data['scenes'])):
                f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_{len(data['scenes'])-1}.jpg'")

        # FFmpeg: เพิ่มการขยับของภาพ (Ken Burns Effect)
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,setsar=1\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print("🚀 5. อัปโหลดสู่ YouTube (เปิดสาธารณะ)...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": data['title'],
                    "description": f"{data['title']}\n\n{data['hashtags']} #การเงิน #Shorts #AI",
                    "categoryId": "27"
                },
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ ไวรัลสำเร็จ! ดูคลิปที่: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ ติดปัญหาที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
