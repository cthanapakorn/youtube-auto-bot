import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def create_fallback_image(path, text):
    # สร้างรูปพื้นหลังการ์ตูนสีสดใส (1080x1920)
    img = Image.new('RGB', (1080, 1920), color=(40, 120, 200))
    d = ImageDraw.Draw(img)
    d.text((100, 960), f"Finance Cartoon: {text[:20]}...", fill=(255, 255, 255))
    img.save(path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ ไม่พบ API Key")
        
        client = genai.Client(api_key=api_key.strip())
        selected_model = 'models/gemini-2.5-flash'

        # 1. ร่างเนื้อหา 4 ฉาก (เพื่อให้ยาวพอถึง 60 วิ)
        print("🧠 1. AI กำลังออกแบบสคริปต์การ์ตูนไวรัล...")
        prompt = (
            "Create a viral 4-scene Thai YouTube Shorts script about Finance (Total 60s). "
            "Tone: Fun and Educational. Style: Cartoon. "
            "Response ONLY in JSON: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"visual\": \"Colorful 2D cartoon, financial character, flat design, vertical\"}]}"
        )
        response = client.models.generate_content(model=selected_model, contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"✅ หัวข้อ: {data['topic']}")

        # 2. เสียงพากย์ (ช้าลงเล็กน้อยเพื่อให้ยาวขึ้นและฟังชัด)
        print("🎙️ 2. สร้างเสียงพากย์ (Rate -10%)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-10% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. เตรียมภาพการ์ตูน (ใช้ Pollinations AI พร้อมระบบสำรอง)
        print("🎨 3. กำลังเนรมิตภาพการ์ตูนประกอบเนื้อหา...")
        for i, sc in enumerate(data['scenes']):
            final_prompt = f"{sc['visual']}, high quality, vibrant colors, anime style, 4k, vertical"
            url = f"https://pollinations.ai/p/{final_prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 99999)}"
            
            success = False
            try:
                # ลองโหลด 2 รอบ
                for attempt in range(2):
                    r = requests.get(url, timeout=30)
                    if r.status_code == 200 and len(r.content) > 15000:
                        with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                        print(f"   📸 ฉากที่ {i+1}: ภาพการ์ตูนโหลดสำเร็จ")
                        success = True
                        break
                    time.sleep(2)
            except: pass
            
            if not success:
                print(f"   ⚠️ ฉากที่ {i+1}: เว็บล่ม บอทวาดรูปสำรองให้เอง")
                create_fallback_image(f"i_{i}.jpg", data['topic'])

        # 4. ตัดต่อ (คำนวณเวลาให้รวม 56-60 วินาที)
        print("🎬 4. กำลังประกอบวิดีโอ (60 วินาที)...")
        with open("l.txt", "w") as f:
            duration_per_scene = 56 / 4  # 14 วินาทีต่อฉาก
            for i in range(4):
                f.write(f"file 'i_{i}.jpg'\nduration {duration_per_scene}\n")
            f.write(f"file 'i_3.jpg'")

        # คำสั่ง FFmpeg แบบมาตรฐานที่ระบบหาเจอแน่นอน
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -vf 'scale=1080:1920' "
            "-c:a aac -shortest final.mp4"
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
                "snippet": {"title": data['topic'], "description": f"{data['topic']} #Shorts #Cartoon #Finance"},
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ สำเร็จ! ลิงก์คลิปไวรัล: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ พังตรงนี้ครับ: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
