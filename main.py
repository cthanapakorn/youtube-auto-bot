import os, re, json, subprocess, requests, sys
import google.generativeai as genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def run_workflow():
    try:
        # --- 1. ตั้งค่ากุญแจ ---
        key = os.getenv("GEMINI_API_KEY")
        if not key: raise ValueError("❌ ไม่พบ API Key ใน Secrets")
        genai.configure(api_key=key.strip())

        # --- 2. แก้ปัญหา 404 (งมหารุ่นที่กุญแจนี้ใช้ได้) ---
        print("🔍 1. กำลังหารุ่น AI ที่กุญแจคุณใช้ได้...")
        model_to_use = None
        # รายชื่อรุ่นที่น่าจะใช้ได้ เรียงจากตัวที่อยากได้ที่สุด
        potential_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        for m_name in potential_models:
            try:
                test_model = genai.GenerativeModel(m_name)
                # ทดลองเรียกสั้นๆ เพื่อเช็คว่า 404 ไหม
                test_model.generate_content("hi")
                model_to_use = test_model
                print(f"✅ เจอแล้ว! ใช้รุ่น: {m_name}")
                break
            except:
                continue
        
        if not model_to_use:
            raise ValueError("❌ กุญแจนี้ใช้ไม่ได้กับรุ่นไหนเลย เช็คใน AI Studio อีกทีครับ")

        # --- 3. ร่างเนื้อหา ---
        print("🧠 2. AI กำลังคิดบทพากย์...")
        prompt = "สรุปเคล็ดลับการเงิน 3 ฉาก ตอบเป็น JSON: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"image_prompt\": \"Cinematic finance\"}]}"
        response = model_to_use.generate_content(prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # --- 4. สร้างเสียง ---
        print("🎙️ 3. สร้างเสียงพากย์...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True)

        # --- 5. สร้างภาพ ---
        print("🎨 4. สร้างภาพ AI...")
        for i, sc in enumerate(data['scenes']):
            url = f"https://pollinations.ai/p/{sc['image_prompt'].replace(' ', '%20')}?width=1080&height=1920&model=flux"
            open(f"i_{i}.jpg", "wb").write(requests.get(url).content)

        # --- 6. ตัดต่อ ---
        print("🎬 5. ตัดต่อวิดีโอ...")
        with open("l.txt", "w") as f:
            for i in range(3): f.write(f"file 'i_{i}.jpg'\nduration 5\n")
            f.write("file 'i_2.jpg'")
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -pix_fmt yuv420p -shortest final.mp4", shell=True)

        # --- 7. อัปโหลด ---
        print("🚀 6. อัปโหลดไป YouTube...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={"snippet": {"title": data['topic']}, "status": {"privacyStatus": "private"}},
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ สำเร็จ! วิดีโอ ID: {res['id']}")

    except Exception as e:
        print(f"\n‼️ ติดปัญหาที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
