import os, re, json, subprocess, requests, sys, time
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def generate_external_image(prompt, filename):
    """ส่งคำสั่งไป Generate ภาพที่ Server ภายนอก (Hugging Face) แล้วดึงกลับมา"""
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token: raise ValueError("❌ ไม่พบ HF_TOKEN ใน GitHub Secrets")

    # ใช้โมเดลระดับโลก Stable Diffusion XL
    api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {hf_token.strip()}"}
    payload = {"inputs": prompt}

    print(f"   ⏳ ส่งคำสั่งให้ External AI Cloud วาดรูป...")
    # ระบบอาจต้องใช้เวลาโหลดโมเดล เราจะให้มันพยายามดึงข้อมูล 5 รอบ
    for attempt in range(5):
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            print("   ✅ ดึงไฟล์ภาพกลับมาสำเร็จ!")
            return True
        elif response.status_code == 503:
            print(f"   ⏳ Server ภายนอกกำลังปลุก AI... รอ 15 วินาที (รอบที่ {attempt+1}/5)")
            time.sleep(15)
        else:
            print(f"   ⚠️ Server Error: {response.status_code} - กำลังลองใหม่...")
            time.sleep(5)
            
    raise RuntimeError("❌ ดึงภาพจาก Server ภายนอกไม่สำเร็จ (Time Out)")

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("❌ ไม่พบ GEMINI_API_KEY")
        
        client = genai.Client(api_key=api_key.strip())
        model_id = 'models/gemini-2.5-flash'

        # 1. ร่างสคริปต์
        print("🧠 1. AI Director กำลังเขียนบทมหากาพย์ 60 วินาที...")
        prompt = (
            "Create a 60s viral Thai storytelling script about 'Epic Transformation'. "
            "6 scenes total. Thai voiceover. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"บทพากย์ไทย...\", \"visual\": \"Detailed English visual prompt for Stable Diffusion, cinematic 3d, 8k\"}]}"
        )
        response = client.models.generate_content(model=model_id, contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อ: {data['title']}")

        # 2. เสียงพากย์
        print("🎙️ 2. สร้างเสียงพากย์ด้วย AI (Rate -15%)...")
        full_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-15% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        # 3. สั่ง Generate ภาพจากภายนอก
        print("🎨 3. สั่ง Generate ภาพระดับ 8K จาก External Server...")
        scenes = data['scenes'][:6]
        for i, sc in enumerate(scenes):
            print(f"--- กำลังทำฉากที่ {i+1}/6 ---")
            enhanced_prompt = f"{sc['visual']}, unreal engine 5 render, highly detailed, dramatic lighting, vertical 9:16 format"
            # ฟังก์ชันตัวนี้จะวิ่งไป Generate ข้างนอกแล้วดึงกลับมา
            generate_external_image(enhanced_prompt, f"i_{i}.jpg")

        # 4. ประกอบวิดีโอ (Motion Zoom)
        print("🎬 4. นำทุกอย่างมาประกอบเป็น Video ในเครื่อง (FFmpeg)...")
        with open("l.txt", "w") as f:
            for i in range(len(scenes)):
                f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_{len(scenes)-1}.jpg'")

        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=2000:-1,zoompan=z='min(zoom+0.0015,1.5)':d=250:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 5. อัปโหลด
        print("🚀 5. อัปโหลด VDO ที่เสร็จแล้วสู่ YouTube...")
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "description": "#เรื่องเล่า #AI", "categoryId": "27"}, "status": {"privacyStatus": "private"}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ สำเร็จ 100%! VDO ถูกสร้างและส่งขึ้นช่องเรียบร้อยครับ")
        except Exception as e:
            if "uploadLimitExceeded" in str(e):
                print("\n⚠️ อัปโหลดไม่ผ่านเพราะโควตา YouTube วันนี้เต็มครับ (ต้องรอ 24 ชม.) แต่ VDO ทำเสร็จสมบูรณ์แล้วใน GitHub!")
            else: raise e

    except Exception as e:
        print(f"\n‼️ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
