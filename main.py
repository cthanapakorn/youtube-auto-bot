import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def create_fallback_image(path, text):
    img = Image.new('RGB', (1080, 1920), color=(15, 23, 42))
    d = ImageDraw.Draw(img)
    d.text((100, 960), f"AI Finance: {text[:25]}...", fill=(255, 255, 255))
    img.save(path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ ไม่พบ API Key")
        
        client = genai.Client(api_key=api_key.strip())
        selected_model = 'models/gemini-2.5-flash'

        # 1. ร่างเนื้อหาแบบไวรัล (เน้น Hook และ Engagement)
        print("🧠 1. AI กำลังออกแบบคอนเทนต์ไวรัล...")
        viral_prompt = (
            "Create a viral YouTube Shorts script about Finance in Thai. "
            "Focus on 'Dark Truths' or 'Secrets to Wealth'. "
            "Structure: 1 strong hook, 3 value points, 1 question for comments. "
            "Response ONLY JSON: {\"title\": \"...\", \"hashtags\": \"...\", \"scenes\": ["
            "{\"text\": \"...\", \"visual\": \"Cinematic motion, close up, highly detailed, finance concept, 4k\"}]}"
        )
        
        response = client.models.generate_content(model=selected_model, contents=viral_prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อไวรัล: {data['title']}")

        # 2. เสียงพากย์ (ปรับความเร็วให้ช้าลง 10% เพื่อความชัดเจน)
        print("🎙️ 2. สร้างเสียงพากย์ (จังหวะเน้นอารมณ์)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        # เพิ่ม --rate=-10% เพื่อให้พูดช้าลง
        subprocess.run(f'edge-tts --rate=-10% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. เตรียมภาพประกอบแบบ Cinematic
        print("🎨 3. กำลังเนรมิตภาพประกอบให้สอดคล้อง...")
        for i, sc in enumerate(data['scenes']):
            # ใส่คีย์เวอร์ดเพิ่มความเป็นอนิเมชั่นและแสงเงา
            enhanced_prompt = f"{sc['visual']}, unreal engine 5 render, cinematic lighting, vertical composition"
            url = f"https://pollinations.ai/p/{enhanced_prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 99999)}"
            
            success = False
            try:
                r = requests.get(url, timeout=30)
                if r.status_code == 200 and len(r.content) > 15000:
                    with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                    print(f"   📸 ฉากที่ {i+1}: ภาพ Cinematic พร้อม!")
                    success = True
            except: pass
            
            if not success:
                create_fallback_image(f"i_{i}.jpg", data['title'])

        # 4. ตัดต่อ (เพิ่ม Zoom Effect เบาๆ ผ่าน FFmpeg เพื่อให้ดูเหมือนอนิเมชั่น)
        print("🎬 4. กำลังประกอบวิดีโอแบบไดนามิก...")
        with open("l.txt", "w") as f:
            for i in range(len(data['scenes'])):
                f.write(f"file 'i_{i}.jpg'\nduration 10\n") # ปรับเวลาต่อฉากให้นานขึ้นเพื่อให้พอดี 60 วิ
            f.write(f"file 'i_{len(data['scenes'])-1}.jpg'")

        # คำสั่ง FFmpeg พิเศษ: เพิ่มการซูมเข้า (Zoom pan) เพื่อให้ภาพนิ่งดูมีชีวิต
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.001,1.5)':d=125:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,setsar=1\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลดพร้อม #Hashtag ที่ AI คิดให้
        print("🚀 5. อัปโหลดสู่เป้าหมายไวรัล...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": data['title'],
                    "description": f"{data['title']}\n\n{data['hashtags']} #AI #Shorts #FinanceThai",
                    "categoryId": "27" # Education
                },
                "status": {"privacyStatus": "public"} # ปรับเป็น Public ทันทีเพื่อความไวรัล!
            },
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ ไวรัลเริ่มแล้ว! ดูความปังได้ที่: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ พังตรงนี้ครับ: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
