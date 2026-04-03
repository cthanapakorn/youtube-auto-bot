import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def create_pro_fallback(path, text):
    """สร้างภาพ Infographic สีทอง-ดำ ดูแพง เมื่อเว็บสร้างรูปล่ม"""
    img = Image.new('RGB', (1080, 1920), color=(10, 15, 25))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 850, 1030, 1070], fill=(255, 215, 0), outline=(255, 255, 255), width=5)
    d.text((120, 930), f"AI INSIGHT: {text[:25]}...", fill=(0, 0, 0))
    img.save(path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        selected_model = 'models/gemini-2.5-flash'

        print("🧠 1. ออกแบบสคริปต์ไวรัล 60 วินาที (6 ฉาก)...")
        # สั่งให้ AI เว้นจังหวะพากย์ด้วยจุดไข่ปลา (...)
        prompt = (
            "Act as a Master Content Creator. Create a 60s Thai Finance Short. "
            "Theme: 'The Truth About Rich People'. 6 scenes total. "
            "Response ONLY JSON: {\"title\": \"...\", \"hashtags\": \"...\", \"scenes\": ["
            "{\"text\": \"(หยุด 1 วิ) ทำไมคนรวยถึงซื้อหนี้... เพื่อสร้างความมั่งคั่ง?\", \"visual\": \"Cinematic 3D, golden key unlocking a vault, floating coins, 8k\"},"
            "{\"text\": \"...\", \"visual\": \"...\"}, {\"text\": \"...\", \"visual\": \"...\"},"
            "{\"text\": \"...\", \"visual\": \"...\"}, {\"text\": \"...\", \"visual\": \"...\"},"
            "{\"text\": \"คุณพร้อมจะเปลี่ยนชีวิตหรือยัง?... พิมพ์ 'ลุย' แล้วเริ่มกันเลย!\", \"visual\": \"Future city skyline at sunset, success concept\"}]}"
        )
        response = client.models.generate_content(model=selected_model, contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 2. เสียงพากย์ (ปรับให้ช้าและขลัง)
        print("🎙️ 2. สร้างเสียงพากย์ (Rate -15% เพื่อความชัดเจน)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. เตรียมภาพที่ 'สอดคล้อง'
        print("🎨 3. กำลังสร้างภาพประกอบ (สไตล์ 3D Animation)...")
        for i, sc in enumerate(data['scenes']):
            style = "Masterpiece, 3D isometric render, vibrant lighting, highly detailed, vertical 9:16"
            url = f"https://pollinations.ai/p/{sc['visual'].replace(' ', '%20')},{style.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 99999)}"
            
            success = False
            try:
                r = requests.get(url, timeout=40)
                if r.status_code == 200 and len(r.content) > 15000:
                    with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                    print(f"   📸 ฉากที่ {i+1}: ภาพสวยตรงปก")
                    success = True
            except: pass
            
            if not success: create_pro_fallback(f"i_{i}.jpg", sc['text'])

        # 4. ตัดต่อ (ระบบ ZoomPan ให้ดูเหมือนวิดีโอ)
        print("🎬 4. กำลังประกอบวิดีโอ (เน้นความเคลื่อนไหว)...")
        with open("l.txt", "w") as f:
            for i in range(6): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")

        # FFmpeg: เพิ่มการซูมเข้าช้าๆ ตลอด 60 วินาที
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0012,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,setsar=1\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print("🚀 5. อัปโหลดสู่ YouTube...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": data['title'], "description": f"{data['title']}\n\n{data['hashtags']}", "categoryId": "27"},
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload("final.mp4")
        ).execute()
        print("✨ ไวรัลสำเร็จ!")

    except Exception as e:
        print(f"\n‼️ พังตรงนี้ครับ: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
