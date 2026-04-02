import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

def create_fallback_image(path, text):
    img = Image.new('RGB', (1080, 1920), color=(10, 20, 30))
    d = ImageDraw.Draw(img)
    d.text((100, 960), f"AI Finance: {text[:25]}...", fill=(255, 255, 255))
    img.save(path, 'JPEG')

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ ไม่พบ API Key")
        
        client = genai.Client(api_key=api_key.strip())
        selected_model = 'models/gemini-2.5-flash'

        # 1. ร่างเนื้อหา และ 'ออกแบบภาพ' ให้ตรงกับคำพูด
        print("🧠 1. AI กำลังออกแบบบทและ 'ภาพประกอบ' ให้สอดคล้องกัน...")
        viral_prompt = (
            "Create a viral Thai YouTube Shorts (60s) about Finance. "
            "Focus on a controversial or secret wealth tip. "
            "Response ONLY in JSON format: "
            "{\"title\": \"...\", \"hashtags\": \"...\", \"scenes\": ["
            "{\"text\": \"คำพากย์ฉากที่ 1\", \"image_prompt\": \"Detailed description of image for this scene, 3D render style, cinematic\"},"
            "{\"text\": \"คำพากย์ฉากที่ 2\", \"image_prompt\": \"...\"},"
            "{\"text\": \"คำพากย์ฉากที่ 3\", \"image_prompt\": \"...\"},"
            "{\"text\": \"คำพากย์ฉากที่ 4\", \"image_prompt\": \"...\"}]}"
        )
        
        response = client.models.generate_content(model=selected_model, contents=viral_prompt)
        # ล้างเศษข้อความอื่นออก เอาเฉพาะ JSON
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not json_match: raise ValueError("AI ตอบกลับมาไม่ใช่รูปแบบที่ถูกต้อง")
        data = json.loads(json_match.group())
        print(f"✅ หัวข้อ: {data['title']}")

        # 2. เสียงพากย์ (เน้นฟังง่าย ไม่เร็วเกินไป)
        print("🎙️ 2. กำลังลงเสียงพากย์ (Rate -10%)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        # ปรับความเร็วช้าลง 10% เพื่อให้ฟิลลิ่งดูน่าเชื่อถือ
        subprocess.run(f'edge-tts --rate=-10% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพประกอบ (AI คิดมาให้แล้วว่าแต่ละฉากต้องเป็นรูปอะไร)
        print("🎨 3. กำลังสร้างภาพประกอบ 'ตามเนื้อหา'...")
        for i, sc in enumerate(data['scenes']):
            # ใส่สไตล์ 3D Pixar/Cinematic เพื่อความไวรัล
            style = "3D isometric render, high detail, masterpiece, cinematic lighting, 8k, vertical"
            final_prompt = f"{sc['image_prompt']}, {style}"
            
            url = f"https://pollinations.ai/p/{final_prompt.replace(' ', '%20')}?width=1080&height=1920&model=flux&seed={random.randint(1, 100000)}"
            
            success = False
            for attempt in range(3): # ลองใหม่ 3 รอบถ้าเว็บสร้างรูปไม่ตอบสนอง
                try:
                    r = requests.get(url, timeout=40)
                    if r.status_code == 200 and len(r.content) > 20000:
                        with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
                        print(f"   📸 ฉากที่ {i+1}: ภาพตรงเนื้อหา (โหลดสำเร็จ)")
                        success = True
                        break
                except: pass
                time.sleep(2)
            
            if not success:
                print(f"   ⚠️ ฉากที่ {i+1}: เว็บล่ม ใช้ระบบวาดรูปสำรอง")
                create_fallback_image(f"i_{i}.jpg", sc['text'])

        # 4. ตัดต่อ (เพิ่มเอฟเฟกต์ซูมเพื่อให้ภาพนิ่งดูเหมือนอนิเมชั่น)
        print("🎬 4. กำลังประกอบร่างวิดีโอ (เพิ่ม Dynamic Zoom)...")
        with open("l.txt", "w") as f:
            # เฉลี่ยเวลาให้ยาวขึ้นเพื่อให้ถึง 60 วินาที
            duration_per_scene = 55 / len(data['scenes'])
            for i in range(len(data['scenes'])):
                f.write(f"file 'i_{i}.jpg'\nduration {duration_per_scene}\n")
            f.write(f"file 'i_{len(data['scenes'])-1}.jpg'")

        # ใช้ Zoompan เพื่อให้ภาพขยับได้ (เหมือนอนิเมชั่น)
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.001,1.5)':d=125:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,setsar=1\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print("🚀 5. อัปโหลดสู่ YouTube (เปิดสาธารณะ)...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": data['title'],
                    "description": f"{data['title']}\n\n{data['hashtags']} #การเงิน #Shorts #AI",
                    "categoryId": "27"
                },
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
