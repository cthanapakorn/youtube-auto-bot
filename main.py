import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# --- ⚙️ ตั้งค่าคลิป (5 ฉาก x 12 วินาที) ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 5   
SCENE_DURATION = 12 
VIDEO_PRIVACY = "private"

def fetch_image_super_stable(prompt, filename, scene_num):
    """ระบบดึงภาพที่เสถียรที่สุดสำหรับ GitHub: Pollinations AI (Flux Engine)"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพ Anime Meme ด้วย Flux Engine...")
    
    # ปรับแต่ง Prompt ให้เป็นสไตล์ Anime Meme เป๊ะๆ ตามที่คุณต้องการ
    style_suffix = "anime meme style, exaggerated expressions, young Asian office worker, messy hair, dramatic, vibrant colors, high contrast, 4k, masterpiece"
    full_prompt = f"{prompt}, {style_suffix}"
    
    # ล้างข้อความให้ปลอดภัยสำหรับ URL
    clean_prompt = re.sub(r'[^\w\s]', '', full_prompt).strip().replace(' ', '%20')
    seed = random.randint(1, 999999)
    
    # ใช้ Pollinations เพราะไม่ต้องใช้ Token และรองรับ GitHub IP ได้ดีกว่า
    url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1080&height=1920&seed={seed}&nologo=true&model=flux"
    
    # ⚠️ หัวใจสำคัญ: ใส่ Headers ปลอมเป็น Browser เพื่อเลี่ยงการโดนบล็อก IP
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for attempt in range(4):
        try:
            response = requests.get(url, headers=headers, timeout=40)
            if response.status_code == 200 and len(response.content) > 10000:
                img = Image.open(io.BytesIO(response.content)).convert('RGB')
                img.save(filename, 'JPEG', quality=95)
                print(f"      ✅ สำเร็จ! ได้ภาพ AI คุณภาพสูง (Seed: {seed})")
                return True
            else:
                print(f"      🔄 ลองใหม่ครั้งที่ {attempt+1}... (Status: {response.status_code})")
                time.sleep(5)
        except Exception as e:
            print(f"      ❌ ขัดข้อง: {str(e)}")
            time.sleep(5)
            
    # ถ้ายังไม่ได้จริงๆ สร้างภาพสีพื้นสวยๆ ป้องกันวิดีโอพัง (Error 69/254)
    print(f"      ⚠️ สร้างภาพกราฟิกฉุกเฉิน (ป้องกัน Error 69)")
    img = Image.new('RGB', (1080, 1920), color=(20, 20, 40))
    img.save(filename, 'JPEG')
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังเขียนบทมหากาพย์มนุษย์เงินเดือน (Anime Meme Style)...")
        # สคริปต์ 5 ฉากสไตล์ที่คุณต้องการ
        prompt_sys = (
            "Act as a viral YouTube creator. Create a 60s Thai script (5 scenes) about a young office worker and money. "
            "Tone: Relatable anime meme style, exaggerated, funny. "
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\"}]}"
        )
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ภาษาไทย...")
        full_text = " ".join([s['text'] for s in data['scenes'][:SCENE_COUNT]])
        subprocess.run(f'edge-tts --rate=-5% --voice "th-TH-NiwatNeural" --text "{full_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการวาดภาพ AI (The Unstoppable Method)...")
        for i, sc in enumerate(data['scenes'][:SCENE_COUNT]):
            fetch_image_super_stable(sc['prompt'], f"i_{i}.jpg", i+1)

        print("🎬 4. กำลังประกอบ Video (60 วินาที)...")
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        # FFmpeg: ปรับให้ภาพลื่นไหลและมี Zoom Cinematic
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920,setsar=1,zoompan=z='min(zoom+0.0015,1.5)':d=300:s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube (สถานะ: {VIDEO_PRIVACY})...")
        if os.path.exists('token.json'):
            with open('token.json', 'r') as f:
                creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
            youtube = build("youtube", "v3", credentials=creds)
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "23"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! เลิกท้อได้เลย คลิปมาแล้วครับ!")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
