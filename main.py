import os, re, json, subprocess, requests, sys
from google import genai # เปลี่ยนวิธี Import
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def run_workflow():
    try:
        # 1. ตั้งค่า AI ด้วย SDK ตัวใหม่ (google-genai)
        key = os.getenv("GEMINI_API_KEY")
        if not key: raise ValueError("❌ ไม่พบ API Key")
        
        client = genai.Client(api_key=key.strip())
        
        print("🧠 1. AI กำลังร่างเนื้อหา (ใช้ SDK ตัวใหม่ล่าสุด)...")
        prompt = "สรุปเคล็ดลับการเงินสั้นๆ 3 ฉาก ตอบเป็น JSON: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"image_prompt\": \"Cinematic finance\"}]}"
        
        # เรียกใช้ AI แบบใหม่
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        
        if not response.text: raise ValueError("❌ AI ไม่ตอบกลับ")

        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"✅ AI Done: {data['topic']}")

        # 2. เสียงพากย์
        print("🎙️ 2. Generating Voice...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True)

        # 3. ภาพ AI
        print("🎨 3. Fetching Images...")
        for i, sc in enumerate(data['scenes']):
            url = f"https://pollinations.ai/p/{sc['image_prompt'].replace(' ', '%20')}?width=1080&height=1920&model=flux"
            open(f"i_{i}.jpg", "wb").write(requests.get(url).content)

        # 4. ตัดต่อ
        print("🎬 4. Rendering Video...")
        with open("l.txt", "w") as f:
            for i in range(3): f.write(f"file 'i_{i}.jpg'\nduration 5\n")
            f.write("file 'i_2.jpg'")
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -pix_fmt yuv420p -shortest final.mp4", shell=True)

        # 5. อัปโหลด
        print("🚀 5. Uploading...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={"snippet": {"title": data['topic']}, "status": {"privacyStatus": "private"}},
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ SUCCESS! Video ID: {res['id']}")

    except Exception as e:
        print(f"\n‼️ ERROR OCCURRED: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
