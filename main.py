import os, re, json, subprocess, requests, sys
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ ไม่พบ API Key ใน Secrets")
        
        client = genai.Client(api_key=api_key.strip())
        
        # --- ระบบเรดาร์: หารุ่นฟรีที่ใช้งานได้จริง ---
        print("🔍 กำลังสแกนหารุ่น AI ฟรีที่คุณใช้ได้...")
        available_models = [m.name for m in client.models.list()]
        
        # เรียงลำดับตัวที่เราอยากได้ (จากดีไปหาพอใช้)
        target_models = ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.0-pro']
        selected_model = None
        
        for target in target_models:
            # เช็คทั้งแบบมี models/ นำหน้าและไม่มี
            full_name = f"models/{target}"
            if full_name in available_models or target in available_models:
                selected_model = target
                break
        
        if not selected_model:
            print("📋 รุ่นที่คุณใช้ได้ตอนนี้มีแค่:")
            for m in available_models: print(f" - {m}")
            raise ValueError("❌ ไม่พบรุ่น Flash ในบัญชีของคุณ (ลองเช็คใน AI Studio อีกทีครับ)")

        print(f"✅ เจอแล้ว! จะใช้รุ่น: {selected_model}")

        # --- เริ่มงานเนื้อหา ---
        print("🧠 1. AI กำลังร่างเนื้อหา...")
        prompt = "สรุปเคล็ดลับการเงิน 3 ฉาก ตอบเป็น JSON: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"image_prompt\": \"Cinematic finance\"}]}"
        
        response = client.models.generate_content(model=selected_model, contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # --- ขั้นตอนสร้างคลิป (เหมือนเดิมแต่ทำให้ชัวร์) ---
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True)

        for i, sc in enumerate(data['scenes']):
            url = f"https://pollinations.ai/p/{sc['image_prompt'].replace(' ', '%20')}?width=1080&height=1920&model=flux"
            open(f"i_{i}.jpg", "wb").write(requests.get(url).content)

        with open("l.txt", "w") as f:
            for i in range(3): f.write(f"file 'i_{i}.jpg'\nduration 5\n")
            f.write("file 'i_2.jpg'")
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -pix_fmt yuv420p -shortest final.mp4", shell=True)

        # --- อัปโหลด ---
        print("🚀 อัปโหลดไป YouTube...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={"snippet": {"title": data['topic']}, "status": {"privacyStatus": "private"}},
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ สำเร็จ 100%! คลิปอยู่ที่: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ พังตรงนี้ครับ: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
