import os, re, json, subprocess, requests, sys, time, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# --- ⚙️ การตั้งค่าคลิป (5 ฉาก x 12 วินาที = 60 วินาทีพอดี) ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 5   
SCENE_DURATION = 12 
VIDEO_PRIVACY = "private"

def fetch_hf_anime_final(prompt, filename, scene_num):
    """
    ระบบวาดรูปขั้นสุด: ใช้ Animagine XL 3.1 (ตัวท็อปสาย Anime) 
    แก้ทาง Error 410/404 ด้วยการระบุ Endpoint เจาะจงโมเดล
    """
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพอนิเมะด้วย Animagine XL 3.1...")
    
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("      ❌ Error: ไม่พบ HF_TOKEN! กรุณาเช็คใน Secrets อีกครั้ง")
        return False
        
    # โมเดลนี้คือที่สุดของสาย Anime ใน Hugging Face และมักจะ Online ตลอด
    model_id = "cagliostrolab/animagine-xl-3.1"
    
    # ใช้ URL แบบเจาะจงโมเดล (วิธีนี้เสถียรที่สุดสำหรับบ้านใหม่)
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"
    
    headers = {
        "Authorization": f"Bearer {hf_token.strip()}",
        "Content-Type": "application/json",
        "x-use-cache": "false"
    }
    
    # Prompt สไตล์ Anime Meme แบบที่คุณต้องการเป๊ะๆ
    anime_prompt = f"masterpiece, best quality, {prompt}, anime style, exaggerated facial expressions, funny, dramatic, vibrant colors, high contrast"
    negative_prompt = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, cropped, worst quality, low quality, jpeg artifacts, watermark, blurry"

    payload = {
        "inputs": anime_prompt,
        "parameters": {
            "negative_prompt": negative_prompt,
            "num_inference_steps": 28,
            "guidance_scale": 7.0
        }
    }

    for attempt in range(5):
        try:
            # พยายามเรียกครั้งแรก
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            
            # ถ้าเจอ 410 หรือ 404 ให้สลับไปใช้ Router URL ทันที
            if response.status_code in [410, 404]:
                router_url = f"https://router.huggingface.co/models/{model_id}"
                response = requests.post(router_url, headers=headers, json=payload, timeout=120)

            if response.status_code == 200:
                if response.headers.get('Content-Type', '').startswith('image'):
                    img = Image.open(io.BytesIO(response.content)).convert('RGB')
                    img.save(filename, 'JPEG', quality=95)
                    print(f"      ✅ สำเร็จ! ได้ภาพอนิเมะคุณภาพสูง")
                    return True
            elif response.status_code == 503:
                # กรณีโมเดลกำลังอุ่นเครื่อง
                wait_time = response.json().get('estimated_time', 20)
                print(f"      🔄 โมเดลกำลังโหลด... รอ {int(wait_time)} วินาที (ครั้งที่ {attempt+1})")
                time.sleep(int(wait_time) + 2)
            else:
                print(f"      ❌ API Error {response.status_code}: {response.text}")
                break 
                
        except Exception as e:
            print(f"      ❌ พังที่ระบบเชื่อมต่อ: {str(e)}")
            time.sleep(5)
            
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังเขียนบทมีมการเงิน (Anime Meme Style)...")
        prompt_sys = (
            "Act as a viral finance content creator. Select ONE real financial concept. "
            "Write a 60s Thai script (5 scenes) with funny, exaggerated anime meme style. "
            "Each scene must have: 1.Relatable Thai voiceover 2.Dramatic anime prompt. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-5% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการวาดภาพ AI (Anime Only)...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            success = fetch_hf_anime_final(sc['prompt'], f"i_{i}.jpg", i+1)
            if not success:
                print(f"\n‼️ หยุดการทำงาน: ไม่สามารถสร้างภาพอนิเมะฉากที่ {i+1} ได้")
                sys.exit(1)

        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        # FFmpeg: ปรับให้รองรับภาพแนวตั้งสำหรับ Shorts
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1080,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,zoompan=z='min(zoom+0.0015,1.3)':d=300:s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube...")
        if os.path.exists('token.json'):
            with open('token.json', 'r') as f:
                creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
            youtube = build("youtube", "v3", credentials=creds)
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ!")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
