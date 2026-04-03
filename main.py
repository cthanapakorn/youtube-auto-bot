import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageFont

def add_text_overlay(image_path, text):
    """วาดซับไตเติลภาษาไทยตัวใหญ่ๆ ลงบนภาพเพื่อความไวรัล"""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    # วาดแถบดำโปร่งแสงด้านล่าง
    draw.rectangle([0, height-400, width, height-150], fill=(0, 0, 0, 150))
    
    # ใส่ข้อความ (ใช้ฟอนต์ระบบหรือวาดแบบเรียบง่าย)
    # หมายเหตุ: ใน GitHub Actions อาจไม่มีฟอนต์ไทย เราจะเน้นสร้างภาพที่สื่อความหมาย
    draw.text((100, height-300), f">> {text[:40]}...", fill=(255, 255, 0)) # สีเหลืองสด
    img.save(image_path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        model_id = 'models/gemini-2.5-flash'

        print("🧠 1. AI Director กำลังร่างสคริปต์แนว Image-to-Video (Luma Style)...")
        # สั่งให้ AI เน้นการบรรยายภาพที่มีการเคลื่อนไหว
        prompt = (
            "Act as a High-End Video Editor. Create a 60s Thai viral video script. "
            "Describe 6 scenes with 'Motion Prompts' (e.g., particles moving, light flickering). "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": ["
            "{\"text\": \"บทพากย์ไทย...\", \"visual\": \"Motion prompt in English: smoke rising, golden coins falling, 8k cinematic\"}]}"
        )
        
        response = client.models.generate_content(model=model_id, contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        print("🎙️ 2. สร้างเสียงพากย์เน้นอารมณ์...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🎨 3. สร้างภาพประกอบและใส่ซับไตเติล...")
        for i, sc in enumerate(data['scenes']):
            url = f"https://pollinations.ai/p/{sc['visual'].replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 99999)}"
            try:
                r = requests.get(url, timeout=40)
                if r.status_code == 200:
                    with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                    # ใส่ซับไตเติลลงในภาพทันที
                    add_text_overlay(f"i_{i}.jpg", sc['text'])
                    print(f"   📸 ฉากที่ {i+1}: สร้างภาพ + ซับสำเร็จ")
            except: pass

        print("🎬 4. ตัดต่อด้วยเทคนิค Motion Zoom (จำลองวิดีโอ AI)...")
        with open("l.txt", "w") as f:
            for i in range(6): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")

        # FFmpeg ขั้นสูง: เพิ่มความเร็วการซูมและแพนภาพให้ดูเหมือนวิดีโอเคลื่อนไหว
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2500:-1,zoompan=z='min(zoom+0.002,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print("🚀 5. อัปโหลดสู่ YouTube (เปิดสาธารณะ)...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": data['title'], "description": f"{data['title']} #AI #LumaAI #Shorts", "categoryId": "27"},
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload("final.mp4")
        ).execute()
        print("✨ ไวรัลสำเร็จ!")

    except Exception as e:
        print(f"\n‼️ พังตรงนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
