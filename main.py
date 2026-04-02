import os, re, json, subprocess, requests, sys
from google import genai # ระบบใหม่ใช้แบบนี้
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def run_workflow():
    try:
        # 1. เชื่อมต่อ AI ด้วยกุญแจ (SDK ใหม่)
        key = os.getenv("GEMINI_API_KEY")
        if not key: raise ValueError("❌ ไม่พบ API Key ใน GitHub Secrets")
        
        client = genai.Client(api_key=key.strip())
        
        print("🧠 1. AI กำลังคิดสคริปต์ (ใช้ระบบใหม่ล่าสุด)...")
        prompt = "สรุปเคล็ดลับการเงิน 3 ฉาก ตอบเป็น JSON เท่านั้น: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"image_prompt\": \"Cinematic finance\"}]}"
        
        # เรียกใช้รุ่น gemini-1.5-flash แบบถูกวิธี
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        
        # แกะ JSON
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not json_match: raise ValueError(f"❌ AI ตอบมาไม่ใช่ JSON: {response.text}")
        data = json.loads(json_match.group())
        print(f"✅ AI คิดหัวข้อได้แล้ว: {data['topic']}")

        # 2. สร้างเสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สร้างภาพ AI (3 ใบ)
        print("🎨 3. สร้างภาพ AI...")
        for i, sc in enumerate(data['scenes']):
            url = f"https://pollinations.ai/p/{sc['image_prompt'].replace(' ', '%20')}?width=1080&height=1920&model=flux"
            open(f"i_{i}.jpg", "wb").write(requests.get(url).content)

        # 4. ตัดต่อวิดีโอ
        print("🎬 4. กำลังประกอบร่างคลิป...")
        with open("l.txt", "w") as f:
            for i in range(3): f.write(f"file 'i_{i}.jpg'\nduration 5\n")
            f.write("file 'i_2.jpg'")
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -pix_fmt yuv420p -shortest final.mp4", shell=True, check=True)

        # 5. อัปโหลดไป YouTube
        print("🚀 5. อัปโหลดไป YouTube...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={"snippet": {"title": data['topic']}, "status": {"privacyStatus": "private"}},
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ สำเร็จ 100%! ดูคลิปที่: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ ติดปัญหาที่: {str(e)}")
        sys.exit(1) # บังคับให้ GitHub ขึ้นสีแดงถ้าพัง

if __name__ == "__main__":
    run_workflow()
