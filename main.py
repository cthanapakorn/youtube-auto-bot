import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageFont

def create_cartoon_background(path, text):
    """สร้างภาพพื้นหลังสไตล์การ์ตูนกราฟิก พร้อมข้อความกลางจอ"""
    # สร้างพื้นหลังไล่สีแบบการ์ตูน (1080x1920)
    base_color = random.choice([(45, 85, 255), (255, 100, 100), (46, 204, 113), (155, 89, 182)])
    img = Image.new('RGB', (1080, 1920), color=base_color)
    d = ImageDraw.Draw(img)
    
    # วาดวงกลม/สี่เหลี่ยมกราฟิกให้ดูมีมิติ
    for _ in range(5):
        x, y = random.randint(0, 1080), random.randint(0, 1920)
        r = random.randint(100, 500)
        d.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 255, 30))

    # วาดกล่องข้อความ (Subtitle)
    d.rectangle([50, 800, 1030, 1120], fill=(0, 0, 0, 180))
    # ใส่ข้อความ (ตัดคำให้พอดี)
    display_text = text[:60] + "..." if len(text) > 60 else text
    d.text((100, 900), display_text, fill=(255, 255, 0)) # ตัวหนังสือสีเหลืองแบบการ์ตูน
    
    img.save(path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ ไม่พบ API Key")
        
        client = genai.Client(api_key=api_key.strip())
        selected_model = 'models/gemini-2.5-flash'

        # 1. ร่างสคริปต์ไวรัล (4 ฉาก เพื่อให้ยาวเกือบ 60 วินาที)
        print("🧠 1. AI กำลังออกแบบบทพากย์และภาพการ์ตูน...")
        prompt = (
            "Create a viral 4-scene Thai YouTube Shorts script about Finance (Total 60s). "
            "Tone: Exciting and Fun. Style: Bright Cartoon. "
            "Response ONLY in JSON: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"visual\": \"Fun 2D cartoon, colorful, vertical\"}]}"
        )
        response = client.models.generate_content(model=selected_model, contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"✅ หัวข้อ: {data['topic']}")

        # 2. เสียงพากย์ (ช้าลง 10% เพื่อความชัดเจน)
        print("🎙️ 2. สร้างเสียงพากย์ (ความเร็วเหมาะสม)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-10% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. เตรียมภาพประกอบ
        print("🎨 3. กำลังสร้างภาพประกอบ (เน้นให้สอดคล้อง)...")
        for i, sc in enumerate(data['scenes']):
            # ลองโหลดภาพ AI ก่อน
            url = f"https://pollinations.ai/p/{sc['visual'].replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 99999)}"
            success = False
            try:
                r = requests.get(url, timeout=25)
                if r.status_code == 200 and len(r.content) > 20000:
                    with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                    print(f"   📸 ฉากที่ {i+1}: ภาพ AI สำเร็จ")
                    success = True
            except: pass
            
            if not success:
                print(f"   ⚠️ ฉากที่ {i+1}: เว็บล่ม, บอทวาดภาพการ์ตูนกราฟิกให้เอง...")
                create_cartoon_background(f"i_{i}.jpg", sc['text'])

        # 4. ตัดต่อ (ยาว 56-60 วินาที)
        print("🎬 4. กำลังตัดต่อวิดีโอ (เพิ่ม Dynamic Zoom)...")
        with open("l.txt", "w") as f:
            duration_per_scene = 56 / 4 
            for i in range(4):
                f.write(f"file 'i_{i}.jpg'\nduration {duration_per_scene}\n")
            f.write(f"file 'i_3.jpg'")

        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.001,1.5)':d=125:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,setsar=1\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print("🚀 5. อัปโหลดสู่ YouTube...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": data['topic'], "description": f"{data['topic']} #Shorts #Cartoon #FinanceThai"},
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ ไวรัลสำเร็จ! ดูคลิปที่: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ พังตรงนี้ครับ: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
