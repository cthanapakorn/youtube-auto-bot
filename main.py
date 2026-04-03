import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def create_cinematic_fallback(path, text):
    """สร้างภาพพื้นหลังหรูหรา (Black & Gold) กรณีเว็บสร้างรูปล่ม"""
    img = Image.new('RGB', (1080, 1920), color=(5, 5, 5))
    d = ImageDraw.Draw(img)
    # วาดเส้นขอบสีทอง
    d.rectangle([30, 30, 1050, 1890], outline=(212, 175, 55), width=15)
    # ใส่ข้อความหลักสไตล์ Minimal
    d.text((100, 900), f"INSIGHT: {text[:25]}...", fill=(212, 175, 55))
    img.save(path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ API Key missing in environment")
        
        client = genai.Client(api_key=api_key.strip())
        model_id = 'models/gemini-2.5-flash'

        # 1. AI Director: ร่างบทและคำสั่งสร้างภาพระดับโลก
        print("🎬 1. ระบบกำลังออกแบบวิดีโอระดับ Cinematic (60 วินาที)...")
        system_prompt = (
            "Act as a world-class cinematic director. Create a 60-second Thai vertical video script (9:16) "
            "Topic: 'The Truth About Rich People'. Tone: Mysterious, Powerful. "
            "Structure: 6 scenes, each 10 seconds. Use '...' for dramatic pauses in voiceover. "
            "Output STRICT JSON: {\"title\": \"...\", \"hashtags\": \"...\", \"scenes\": ["
            "{\"text\": \"...\", \"visual\": \"High-end 3D, luxury gold and black, cinematic lighting, 8k\"}]}"
        )
        
        response = client.models.generate_content(model=model_id, contents=system_prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"✅ คอนเทนต์พร้อม: {data['title']}")

        # 2. เสียงพากย์: ปรับความเร็วให้ขลัง (Rate -15%)
        print("🎙️ 2. กำลังลงเสียงพากย์ด้วยระบบ AI (Powerful Tone)...")
        full_voice_text = " ".join([s['text'] for s in data['scenes']])
        # บันทึกเสียงพากย์รวม
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_voice_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. การเนรมิตภาพ: สร้างภาพ 8K ที่สอดคล้องกับทุกประโยค
        print("🎨 3. กำลังสร้างภาพประกอบ 8K ทีละฉาก...")
        for i, sc in enumerate(data['scenes']):
            # เสริม Prompt ให้หรูหราขึ้น
            final_visual_prompt = f"{sc['visual']}, premium feel, gold and deep blue accents, highly detailed, vertical orientation"
            url = f"https://pollinations.ai/p/{final_visual_prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 1000000)}"
            
            success = False
            try:
                r = requests.get(url, timeout=45)
                if r.status_code == 200 and len(r.content) > 30000:
                    with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                    print(f"   📸 ฉากที่ {i+1}: สำเร็จ (High Quality)")
                    success = True
            except: pass
            
            if not success:
                print(f"   ⚠️ ฉากที่ {i+1}: ใช้ระบบภาพสำรองระดับพรีเมียม")
                create_cinematic_fallback(f"i_{i}.jpg", sc['text'])

        # 4. การตัดต่อขั้นสูง: เพิ่ม Dynamic Zoom (Ken Burns Effect) ให้ภาพเคลื่อนไหว
        print("🎬 4. กำลังตัดต่อด้วยเทคนิค Dynamic Zoom (เป้าหมาย 60 วินาที)...")
        with open("l.txt", "w") as f:
            # 6 ฉาก ฉากละ 10 วินาที = 60 วินาทีพอดี
            for i in range(6):
                f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")

        # คำสั่ง FFmpeg พิเศษ: ซูมเข้าช้าๆ เพื่อสร้างอารมณ์ร่วม
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,setsar=1\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. การอัปโหลดแบบ Public: กระจายสู่สายตาชาวโลก
        print("🚀 5. อัปโหลดสู่ YouTube (Status: Public)...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": data['title'],
                    "description": f"{data['title']}\n\n{data['hashtags']} #การเงิน #Shorts #RichMindset",
                    "categoryId": "27" # Education
                },
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ ไวรัลสำเร็จแล้ว! คลิปของคุณอยู่ที่: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ ติดปัญหาที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
