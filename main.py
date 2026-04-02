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
        
        print("🔍 กำลังเลือก AI รุ่นที่ดีที่สุดจากบัญชีของคุณ...")
        available_models = [m.name for m in client.models.list()]
        
        # เลือกใช้รุ่นใหม่ล่าสุดที่บัญชีคุณมี (2.5 -> 2.0 -> flash)
        selected_model = None
        priority_list = [
            'models/gemini-2.5-flash', 
            'models/gemini-2.0-flash', 
            'models/gemini-1.5-flash',
            'models/gemini-flash-latest'
        ]
        
        for target in priority_list:
            if target in available_models:
                selected_model = target
                break
        
        if not selected_model:
            # ถ้าไม่เจอตัวข้างบนเลย ให้เอาตัวแรกที่มีคำว่า flash
            for m in available_models:
                if 'flash' in m.lower() and 'image' not in m.lower():
                    selected_model = m
                    break

        if not selected_model:
            raise ValueError("❌ ไม่พบรุ่นที่เหมาะสมในบัญชีของคุณ")

        print(f"✅ ตกลงใช้รุ่น: {selected_model}")

        # --- เริ่มงานเนื้อหา ---
        print("🧠 1. AI กำลังร่างสคริปต์ไวรัล...")
        prompt = "สรุปเคล็ดลับการเงิน 3 ฉาก ตอบเป็น JSON เท่านั้น: {\"topic\": \"...\", \"scenes\": [{\"text\": \"...\", \"image_prompt\": \"Cinematic finance, high quality\"}]}"
        
        response = client.models.generate_content(model=selected_model, contents=prompt)
        
        # ล้างข้อมูลเผื่อ AI ใส่ Markdown มา
        json_text = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        data = json.loads(json_text)
        print(f"✅ หัวข้อคลิป: {data['topic']}")

        # --- ขั้นตอนสร้างคลิป ---
        print("🎙️ 2. สร้างเสียงพากย์...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🎨 3. สร้างภาพ AI ประกอบเนื้อหา...")
        for i, sc in enumerate(data['scenes']):
            url = f"https://pollinations.ai/p/{sc['image_prompt'].replace(' ', '%20')}?width=1080&height=1920&model=flux"
            r = requests.get(url)
            with open(f"i_{i}.jpg", "wb") as f: f.write(r.content)

        print("🎬 4. กำลังประกอบร่างเป็นวิดีโอ...")
        with open("l.txt", "w") as f:
            for i in range(3): f.write(f"file 'i_{i}.jpg'\nduration 5\n")
            f.write("file 'i_2.jpg'")
        subprocess.run("ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 -pix_fmt yuv420p -shortest final.mp4", shell=True, check=True)

        # --- อัปโหลด ---
        print("🚀 5. อัปโหลดไป YouTube Studio...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": data['topic'], "description": "#AI #Finance"},
                "status": {"privacyStatus": "private"} # อัปโหลดเป็น Private ให้คุณเช็คก่อน
            },
            media_body=MediaFileUpload("final.mp4")
        )
        res = request.execute()
        print(f"✨ สำเร็จ 100%! ดูคลิปได้ที่: https://youtu.be/{res['id']}")

    except Exception as e:
        print(f"\n‼️ พังตรงนี้ครับ: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
