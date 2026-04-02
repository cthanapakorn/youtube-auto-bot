import os, re, json, subprocess, requests, sys, time
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw # ใช้สร้างรูปเองถ้าเน็ตล่ม

def create_fallback_image(path, text):
    # สร้างรูปพื้นหลังสีน้ำเงินเข้ม (1080x1920)
    img = Image.new('RGB', (1080, 1920), color=(20, 30, 50))
    d = ImageDraw.Draw(img)
    # วาดข้อความง่ายๆ ไว้กลางจอ (ป้องกัน FFmpeg งง)
    d.text((100, 960), f"Finance AI: {text[:20]}...", fill=(255, 255, 255))
    img.save(path, "JPEG")

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ ไม่พบ API Key")
        
        client = genai.Client(api_key=api_key.strip())
        selected_model = 'models/gemini-2.5-flash'
        print(f"✅ ใช้โมเดล: {selected_model}")

        # 1. ร่างสคริปต์
        print("🧠 1. AI กำลังร่างเนื้อหา...")
        prompt = "สรุปเคล็ดลับการเงิน 3 ฉาก ตอบเป็น JSON: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"image_prompt\": \"Cinematic finance, 4k\"}]}"
        response = client.models.generate_content(model=selected_model, contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อ: {data['topic']}")

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. เตรียมภาพ
        print("🎨 3. กำลังเตรียมภาพประกอบ...")
        for i, sc in enumerate(data['scenes']):
            url = f"https://pollinations.ai/p/{sc['image_prompt'].replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={int(time.time())+i}"
            
            success = False
            try:
                r = requests.get(url, timeout=20)
                if r.status_code == 200 and len(r.content) > 10000:
                    with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                    print(f"   📸 ฉากที่ {i+1}: โหลดสำเร็จ")
                    success = True
            except: pass
            
            if not success:
                print(f"   ⚠️ ฉากที่ {i+1}: เว็บล่ม, บอทกำลังสร้างรูปให้เอง...")
                create_fallback_image(f"i_{i}.jpg", data['topic'])

        # 4. ตัดต่อวิดีโอ
        print("🎬 4. กำลังตัดต่อวิดีโอ...")
        with open("l.txt", "w") as f:
            for i in range(3):
                f.write(f"file 'i_{i}.jpg'\nduration 5\n")
            f.write(f"file 'i_2.jpg'")

        # คำสั่ง FFmpeg แบบเน้นความเสถียร
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -vf 'scale=1080:1920' "
            "-c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print("🚀 5. อัปโหลดไป YouTube...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": data['topic'], "description": "#AI #Finance"},
                "status": {"privacyStatus": "private"}
            },
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ สำเร็จ 100%! ลิงก์คลิป: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ พังตรงนี้ครับ: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
