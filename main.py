import os, re, json, subprocess, requests
import google.generativeai as genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def run_workflow():
    try:
        # 1. ตั้งค่า AI
        key = os.getenv("GEMINI_API_KEY").strip()
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        print("🧠 AI Thinking...")
        prompt = "Create a 3-scene YouTube Shorts script about Finance in Thai. Response ONLY JSON: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"image_prompt\": \"Cinematic finance\"}]}"
        response = model.generate_content(prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 2. สร้างเสียงพากย์
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True)

        # 3. สร้างภาพ AI (3 ใบ)
        for i, sc in enumerate(data['scenes']):
            url = f"https://pollinations.ai/p/{sc['image_prompt'].replace(' ', '%20')}?width=1080&height=1920&model=flux"
            open(f"i_{i}.jpg", "wb").write(requests.get(url).content)

        # 4. ตัดต่อ (FFmpeg)
        with open("l.txt", "w") as f:
            for i in range(3): f.write(f"file 'i_{i}.jpg'\nduration 5\n")
            f.write("file 'i_2.jpg'")
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -pix_fmt yuv420p -shortest final.mp4", shell=True)

        # 5. อัปโหลด
        print("🚀 Uploading...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={"snippet": {"title": data['topic']}, "status": {"privacyStatus": "private"}},
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ Success! https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    run_workflow()