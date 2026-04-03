import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def create_cinematic_fallback(path, text):
    """สร้างภาพ Infographic หรูหรา กรณีเว็บบล็อก"""
    img = Image.new('RGB', (1080, 1920), color=(10, 15, 25))
    d = ImageDraw.Draw(img)
    d.rectangle([30, 30, 1050, 1890], outline=(212, 175, 55), width=15)
    d.text((100, 900), f"AI INSIGHT: {text[:25]}...", fill=(212, 175, 55))
    img.save(path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        model_id = 'models/gemini-2.5-flash'

        # 1. ออกแบบสคริปต์ไวรัล
        print("🧠 1. กำลังร่างสคริปต์ Cinematic (60 วินาที)...")
        system_prompt = "Act as a world-class cinematic director. Create a 60s Thai Finance script. 6 scenes. Response ONLY JSON: {\"title\": \"...\", \"hashtags\": \"...\", \"scenes\": [{\"text\": \"...\", \"visual\": \"3D cinematic style\"}]}"
        response = client.models.generate_content(model=model_id, contents=system_prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"✅ หัวข้อ: {data['title']}")

        # 2. เสียงพากย์
        print("🎙️ 2. กำลังลงเสียงพากย์...")
        full_voice_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_voice_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพประกอบ
        print("🎨 3. กำลังสร้างภาพประกอบ 8K...")
        for i, sc in enumerate(data['scenes']):
            url = f"https://pollinations.ai/p/{sc['visual'].replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 999999)}"
            try:
                r = requests.get(url, timeout=45)
                if r.status_code == 200 and len(r.content) > 30000:
                    with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                else: create_cinematic_fallback(f"i_{i}.jpg", sc['text'])
            except: create_cinematic_fallback(f"i_{i}.jpg", sc['text'])

        # 4. ตัดต่อวิดีโอ (60 วินาที)
        print("🎬 4. กำลังตัดต่อด้วย Dynamic Zoom...")
        with open("l.txt", "w") as f:
            for i in range(6): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")
        
        # FFmpeg Dynamic Zoom
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4", shell=True, check=True)

        # 5. อัปโหลดแบบ PRIVATE
        print("🚀 5. อัปโหลดสู่ YouTube (โหมด: Private สำหรับการทดสอบ)...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            request = youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": f"[TEST] {data['title']}", 
                        "description": f"{data['title']}\n{data['hashtags']}", 
                        "categoryId": "27"
                    },
                    "status": {
                        "privacyStatus": "private" # เปลี่ยนกลับเป็น Private แล้วครับ!
                    }
                },
                media_body=MediaFileUpload("final.mp4")
            )
            res = request.execute()
            print(f"✨ สำเร็จ! ตรวจสอบวิดีโอที่: https://studio.youtube.com/video/{res['id']}/edit")
        except Exception as e:
            if "uploadLimitExceeded" in str(e):
                print("\n⚠️ โควตาวันนี้เต็มแล้ว! วิดีโอสร้างเสร็จแล้วแต่ต้องรอพรุ่งนี้ถึงจะอัปโหลดได้ครับ")
            else: raise e

    except Exception as e:
        print(f"\n‼️ ติดปัญหา: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
