import os, re, json, subprocess, requests, sys
import google.generativeai as genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def run_workflow():
    try:
        # 1. เช็คกุญแจ
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("❌ ไม่พบ GEMINI_API_KEY ใน Secrets")
        
        genai.configure(api_key=key.strip())
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        print("🧠 1. AI is drafting content...")
        prompt = "Create a 3-scene YouTube Shorts script about Finance in Thai. Response ONLY in JSON: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"image_prompt\": \"Cinematic finance\"}]}"
        response = model.generate_content(prompt)
        
        if not response.text:
            raise ValueError("❌ AI ไม่ตอบกลับ (Check Quota/API Key)")

        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"✅ AI Done: {data['topic']}")

        # 2. เสียงพากย์
        print("🎙️ 2. Generating Voice...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        res_voice = subprocess.run(f'edge-tts --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True)
        if res_voice.returncode != 0:
            raise RuntimeError("❌ สร้างเสียงพากย์ไม่สำเร็จ")

        # 3. ภาพ AI
        print("🎨 3. Fetching Images...")
        for i, sc in enumerate(data['scenes']):
            url = f"https://pollinations.ai/p/{sc['image_prompt'].replace(' ', '%20')}?width=1080&height=1920&model=flux"
            r = requests.get(url)
            if r.status_code == 200:
                with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)
            else:
                raise RuntimeError(f"❌ โหลดภาพฉากที่ {i} ไม่ได้")

        # 4. ตัดต่อ
        print("🎬 4. Rendering Video...")
        with open("l.txt", "w") as f:
            for i in range(3): f.write(f"file 'i_{i}.jpg'\nduration 5\n")
            f.write("file 'i_2.jpg'")
        
        res_ffmpeg = subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -pix_fmt yuv420p -shortest final.mp4", shell=True)
        if res_ffmpeg.returncode != 0:
            raise RuntimeError("❌ ตัดต่อวิดีโอ (FFmpeg) พัง")

        # 5. อัปโหลด
        print("🚀 5. Uploading to YouTube...")
        if not os.path.exists('token.json'):
            raise FileNotFoundError("❌ ไม่พบไฟล์ token.json ในเครื่อง")

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
        sys.exit(1) # บังคับให้ GitHub ขึ้นสีแดงทันทีถ้ามีอะไรพัง

if __name__ == "__main__":
    run_workflow()
