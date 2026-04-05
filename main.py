import os, re, json, subprocess, requests, sys, time, random
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- ⚙️ การตั้งค่าคลิป ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 6
SCENE_DURATION = 10 
VIDEO_PRIVACY = "private"

def fetch_lexica_ai_image(keyword, filename, scene_num):
    """ระบบไปดูดภาพ AI ระดับเทพที่มีคนสร้างไว้แล้ว (ไม่โดนบล็อกชัวร์ 100%)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังค้นหาภาพ AI ระดับ 8K จาก Lexica...")
    
    # ล้าง Keyword ให้พร้อมค้นหา
    clean_key = re.sub(r'[^\w\s]', '', keyword).strip().replace(' ', '+')
    url = f"https://lexica.art/api/v1/search?q={clean_key}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code == 200:
            data = res.json()
            if 'images' in data and len(data['images']) > 0:
                # เลือกรูปจาก 3 อันดับแรก เพื่อให้ได้รูปที่สวยที่สุดแต่ไม่ซ้ำซาก
                top_images = data['images'][:3]
                selected_image = random.choice(top_images)['src']
                
                # ดาวน์โหลดรูปนั้นมา
                img_data = requests.get(selected_image, timeout=30).content
                with open(filename, 'wb') as f:
                    f.write(img_data)
                print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพ AI ของจริง สวยงามพร้อมใช้!")
                return True
    except Exception as e:
        print(f"   ⚠️ ขัดข้อง: {str(e)}")

    # แผนสำรอง: ถ้า Lexica ล่ม ไปดึง Unsplash มาแทน (เพื่อให้คลิปมีภาพของจริงเสมอ)
    print(f"   🔄 ค้นหาจาก Lexica ไม่เจอ... ดึงภาพถ่ายจริง (Stock) มาแทน")
    url_stock = f"https://source.unsplash.com/1080x1920/?{clean_key.replace('+', ',')}"
    try:
        r = requests.get(url_stock, timeout=20)
        with open(filename, 'wb') as f: f.write(r.content)
        print(f"   ✅ ฉากที่ {scene_num}: ได้ภาพ Stock ความละเอียดสูงมาใช้แทน")
        return True
    except:
        pass
        
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 1. ให้ Gemini เขียนบท และคิดคีย์เวิร์ดสำหรับ "ค้นหาภาพ AI"
        print("🧠 1. AI Director กำลังเขียนบทและคิดคีย์เวิร์ดภาพมหากาพย์...")
        prompt_sys = (
            "Act as a viral YouTube creator. Create a 60s Thai story script (6 scenes). "
            "Topic: 'The Secret of Wealth'. "
            "For each scene, give me: 1. Thai voiceover text. 2. A short, highly specific 3-4 word English keyword to search for a 3D mascot or epic scene (e.g. '3d cute robot money', 'epic golden temple', 'cinematic ancient coin'). "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"keyword\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. ดึงภาพ AI จากฐานข้อมูลโลก
        print("🖼️ 3. เข้าสู่กระบวนการดึงภาพ AI ของจริงมาใช้งาน...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            fetch_lexica_ai_image(sc['keyword'], f"i_{i}.jpg", i+1)

        # 4. ตัดต่อ (ใส่ Effect ซูมขลังๆ)
        print("🎬 4. กำลังประกอบ Video พร้อมเทคนิค Cinematic Zoom...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920,setsar=1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print(f"🚀 5. อัปโหลดสู่ YouTube (สถานะ: {VIDEO_PRIVACY})...")
        if not os.path.exists('token.json'): return
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! เข้าไปดูความสวยงามของภาพ AI ใน YouTube Studio ได้เลย")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("\n⚠️ Quota YouTube เต็ม! รอ 24 ชม.")
            else: raise e

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
