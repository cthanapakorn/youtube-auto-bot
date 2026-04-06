import os, re, json, subprocess, sys, time, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageDraw

# --- ⚙️ การตั้งค่าคลิป ---
SCENE_COUNT = 5
SCENE_DURATION = 12 
VIDEO_PRIVACY = "private"

def create_emergency_bg(filename, scene_num, error_msg="Error"):
    """ถ้าโควตาวาดรูปเต็ม จะวาดสไลด์บอกฉากแทน"""
    img = Image.new('RGB', (1080, 1920), color=(20, 30, 50))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 50, 1030, 1870], outline=(255, 215, 0), width=15)
    d.text((100, 900), f"SCENE {scene_num}\nVisual Placeholder", fill=(255, 215, 0))
    img.save(filename, 'JPEG')

def fetch_gemini_image(client, prompt, filename, scene_num):
    """⭐️ สุดยอดระบบวาดภาพ: ใช้โมเดล Imagen 3 ของ Google ผ่าน API โดยตรง"""
    print(f"   ⏳ ฉากที่ {scene_num}: สั่ง Gemini (Imagen 3) วาดรูป...")
    
    # คำสั่งภาพสไตล์ Cinematic 3D เพื่อความพรีเมียม
    epic_prompt = f"{prompt}, highly detailed 3D render, cinematic lighting, masterpiece, finance concept"
    
    try:
        # เรียกใช้ Imagen 3 ผ่าน google-genai SDK
        result = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=epic_prompt,
            config=dict(
                number_of_images=1,
                aspect_ratio="9:16", # กำหนดเป็นแนวตั้ง Shorts ได้เลย
                output_mime_type="image/jpeg",
            )
        )
        
        # ถ้าระบบส่งภาพกลับมาสำเร็จ
        if result.generated_images:
            img_bytes = result.generated_images[0].image.image_bytes
            img = Image.open(io.BytesIO(img_bytes))
            img.save(filename, 'JPEG', quality=95)
            print(f"   ✅ สำเร็จ! ได้ภาพคุณภาพสูงจาก Gemini API")
            return True
            
    except Exception as e:
        print(f"   ❌ Gemini Image API ล้มเหลว (อาจติดโควตาหรือ Safety): {e}")

    # แผนสำรอง
    create_emergency_bg(filename, scene_num)
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังสุ่มหัวข้อการเงินจริง และเขียนบท...")
        
        # 📌 สั่งให้ AI สุ่มเนื้อหาการเงิน "ของจริง" 
        prompt_sys = (
            "Act as a professional financial advisor. Randomly select ONE real financial concept (e.g., Compound Interest, DCA, Inflation, Emergency Fund, Asset Allocation, Dividend investing). "
            "Create a 60-second Thai YouTube Shorts script explaining this real concept with factual information. "
            f"Structure into {SCENE_COUNT} scenes. "
            "For each scene, provide: 1. Thai voiceover text. 2. An English prompt to generate a 3D cinematic image representing the scene. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิปวันนี้: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-10% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการวาดภาพด้วย Imagen 3...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            # ส่ง API Key ตัวเดิมไปสั่งวาดรูป
            fetch_gemini_image(client, sc['prompt'], f"i_{i}.jpg", i+1)

        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920,setsar=1,zoompan=z='min(zoom+0.0015,1.2)':d=300:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube (สถานะ: {VIDEO_PRIVACY})...")
        if not os.path.exists('token.json'): return
        with open('token.json', 'r') as f:
            creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
        
        youtube = build("youtube", "v3", credentials=creds)
        try:
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! เข้าไปชมวิดีโอความรู้การเงินใน Studio ได้เลยครับ")
        except Exception as e:
            if "uploadLimitExceeded" in str(e): print("\n⚠️ Quota YouTube เต็ม! รอ 24 ชม.")
            else: raise e

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
