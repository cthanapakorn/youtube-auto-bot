import os, re, json, subprocess, requests, sys
import google.generativeai as genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ ไม่พบ API Key ใน Secrets")
        genai.configure(api_key=api_key.strip())

        # --- แก้ทาง 404: ลองหารุ่นที่ใช้ได้จริง ---
        print("🔍 1. กำลังสแกนหา AI ที่กุญแจคุณใช้ได้...")
        model = None
        # ลองเรียก 3 ชื่อที่ Google ชอบเปลี่ยนไปมา
        for m_name in ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-1.5-flash-latest']:
            try:
                test_model = genai.GenerativeModel(m_name)
                test_model.generate_content("hi") # ทดสอบสั้นๆ
                model = test_model
                print(f"✅ เจอแล้ว! ใช้รุ่น: {m_name}")
                break
            except:
                continue
        
        if not model:
            raise ValueError("❌ กุญแจนี้หา AI ไม่เจอ (404 ทุกทาง) ลองเช็คที่ Google AI Studio อีกครั้งครับ")

        # --- ส่วนที่เหลือทำเหมือนเดิม ---
        print("🧠 2. AI กำลังร่างเนื้อหา...")
        prompt = "สรุปเคล็ดลับการเงิน 3 ฉาก ตอบเป็น JSON: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"image_prompt\": \"Cinematic finance\"}]}"
        response = model.generate_content(prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        print("🎙️ 3. สร้างเสียงพากย์...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True)

        print("🎨 4. สร้างภาพ AI...")
        for i, sc in enumerate(data['scenes']):
            url = f"https://pollinations.ai/p/{sc['image_prompt'].replace(' ', '%20')}?width=1080&height=1920&model=flux"
            open(f"i_{i}.jpg", "wb").write(requests.get(url).content)

        print("🎬 5. ตัดต่อวิดีโอ...")
        with open("l.txt", "w") as f:
            for i in range(3): f.write(f"file 'i_{i}.jpg'\nduration 5\n")
            f.write("file 'i_2.jpg'")
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -pix_fmt yuv420p -shortest final.mp4", shell=True)

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
        print(f"✨ สำเร็จ! ลิงก์คลิป: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ พังตรงนี้ครับ: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
