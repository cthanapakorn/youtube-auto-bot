import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw, ImageFont # ตัวช่วยวาดรูป

def create_fallback_image(path, text):
    # วาดรูปพื้นหลังแบบ 'อนิเมชั่นภาพเคลื่อนไหว' เบลอๆ (1080x1920)
    img = Image.new('RGB', (1080, 1920), color=(15, 25, 45))
    d = ImageDraw.Draw(img)
    # ใส่ข้อความเล็กน้อยไว้กลางจอ (กันเหนียว)
    d.text((100, 960), f"AI Finance: {text[:20]}...", fill=(255, 255, 255))
    img.save(path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ ไม่พบ API Key")
        
        client = genai.Client(api_key=api_key.strip())
        selected_model = 'models/gemini-2.5-flash'

        # 1. ร่างเนื้อหา (บังคับ AI คิดสคริปต์ 4 ฉาก ให้รวมกันไม่เกิน 50 วินาที)
        print("🧠 1. AI กำลังออกแบบสคริปต์ไวรัล (แนวการ์ตูน)...")
        prompt = (
            "Create a viral 4-scene Thai YouTube Shorts script about Finance (60s total). "
            "Response ONLY in JSON: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"visual_prompt\": \"Cartoon illustration, vertical, finance concept\"}]}"
        )
        response = client.models.generate_content(model=selected_model, contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['topic']}")

        # 2. เสียงพากย์ (ช้าลง 10%)
        print("🎙️ 2. สร้างเสียงพากย์ (Rate -10%)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-10% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. เตรียมภาพประกอบ (ทนทานที่สุเ)
        print("🎨 3. กำลังเตรียมภาพประกอบ 'แนวการ์ตูน'...")
        for i, sc in enumerate(data['scenes']):
            # ใส่คีย์เวิร์ดเพิ่มความเป็น อนิเมชั่น/การ์ตูน
            final_prompt = f"{sc['visual_prompt']}, vector art, anime style, vertical, dynamic angle"
            url = f"https://pollinations.ai/p/{final_prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 100000)}"
            
            success = False
            try:
                # พยายามโหลด 2 รอบ
                for attempt in range(2):
                    r = requests.get(url, timeout=30)
                    if r.status_code == 200 and len(r.content) > 15000:
                        with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                        print(f"   📸 ฉากที่ {i+1}: ภาพการ์ตูนพร้อม!")
                        success = True
                        break
                    time.sleep(2)
            except: pass
            
            # --- ไม้ตาย: ถ้าเว็บล่ม บอทวาดรูปสำรองให้เองอัตโนมัติ ---
            if not success:
                print(f"   ⚠️ ฉากที่ {i+1}: เว็บสร้างรูปล่ม, บอทกำลังวาดรูปให้เอง...")
                create_fallback_image(f"i_{i}.jpg", data['topic'])

        # 4. ตัดต่อ (คำนวณเวลาให้พอดี 60 วินาที)
        print("🎬 4. กำลังประกอบร่างวิดีโอ (เพิ่ม Dynamic Zoom)...")
        with open("l.txt", "w") as f:
            # เฉลี่ยเวลา 4 ฉากให้ได้รวมกันประมาณ 55-60 วินาที
            duration_per_scene = 56 / 4 
            for i in range(4):
                f.write(f"file 'i_{i}.jpg'\nduration {duration_per_scene}\n")
            f.write(f"file 'i_3.jpg'") # บรรทัดสุดท้าย不用 duration

        # ใช้ Zoompan เพื่อให้ภาพนิ่งดูเหมือนอนิเมชั่น
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.001,1.5)':d=125:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,setsar=1\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print("🚀 5. อัปโหลดสู่เป้าหมายไวรัล...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": data['topic'], "description": f"{data['topic']} #Shorts #Cartoon #AI"},
                "status": {"privacyStatus": "public"}
            },
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ ไวรัลเริ่มแล้ว! ดูคลิปที่: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ พังตรงนี้ครับ: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
