import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def validate_and_fallback(path, text, scene_num):
    """ตรวจสอบว่าไฟล์ภาพใช้ได้ไหม ถ้าเสียให้วาดใหม่ทันที"""
    try:
        with Image.open(path) as img:
            img.verify()
        print(f"   ✅ ฉากที่ {scene_num}: ภาพสมบูรณ์")
    except:
        print(f"   ⚠️ ฉากที่ {scene_num}: ภาพเสีย! กำลังวาดภาพ Cinematic สำรอง...")
        img = Image.new('RGB', (1080, 1920), color=(5, 5, 15))
        d = ImageDraw.Draw(img)
        d.rectangle([40, 40, 1040, 1880], outline=(255, 191, 0), width=15)
        d.text((100, 960), f"EPIC SCENE {scene_num}\n{text[:30]}...", fill=(255, 191, 0))
        img.save(path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        model_id = 'models/gemini-2.5-flash'

        # 1. ร่างสคริปต์ไทย สไตล์เรื่องเล่ามหากาพย์
        print("🧠 1. AI กำลังออกแบบบทพากย์ไทยและภาพ Cinematic (DODI Style)...")
        prompt = (
            "Create a 60s viral Thai storytelling script about 'Epic Destiny' or 'Ancient Legend'. "
            "Use powerful Thai language with '...' for dramatic pauses. "
            "Visual Prompts: English, 3D Cinematic, Unreal Engine 5, Epic lighting. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"visual\": \"...\"}]}"
        )
        response = client.models.generate_content(model=model_id, contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        
        # 2. เสียงพากย์ (เน้นความขลัง)
        print("🎙️ 2. สร้างเสียงพากย์โทนลึกลับ (Rate -15%)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพประกอบ (6 ฉาก ฉากละ 10 วินาที)
        print("🎨 3. กำลังเนรมิตภาพประกอบระดับ 8K...")
        scenes = data['scenes'][:6] # บังคับ 6 ฉาก
        for i, sc in enumerate(scenes):
            enhanced_prompt = f"{sc['visual']}, masterwork, cinematic atmosphere, gold and dark blue, vertical 9:16"
            url = f"https://pollinations.ai/p/{enhanced_prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 999999)}"
            
            try:
                r = requests.get(url, timeout=45)
                with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
            except: pass
            validate_and_fallback(f"i_{i}.jpg", sc['text'], i+1)

        # 4. ตัดต่อ (Dynamic Zoom)
        print("🎬 4. กำลังตัดต่อวิดีโอ (จำลองวิดีโอ AI)...")
        with open("l.txt", "w") as f:
            for i in range(len(scenes)):
                f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_{len(scenes)-1}.jpg'")

        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print("🚀 5. อัปโหลดสู่ YouTube...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "description": "#เรื่องเล่า #AI", "categoryId": "27"}, "status": {"privacyStatus": "public"}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ สำเร็จ! คลิปมหากาพย์ของคุณพร้อมรับยอดวิวแล้ว")
        except Exception as e:
            if "uploadLimitExceeded" in str(e):
                print("\n⚠️ โควตาอัปโหลดวันนี้เต็ม! (รอ 24 ชม. หรือยืนยันตัวตนช่องใน YouTube Studio นะครับ)")
            else: raise e

    except Exception as e:
        print(f"\n‼️ พังตรงนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
