import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# --- ⚙️ ตั้งค่า (5 ฉาก x 12 วินาที) ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 5   
SCENE_DURATION = 12 
VIDEO_PRIVACY = "private"

# 📌 คำอธิบายตัวละครคงที่ (เพื่อให้หน้าไม่เปลี่ยน)
CHAR_ANCHOR = "A young Thai male office worker, 25 years old, slightly messy black hair, wearing a white dress shirt and a dark blue tie."

def fetch_image_turbo_v2(prompt, filename, scene_num):
    """วาดรูปโดยเน้นความคงที่ของตัวละครและขนาดที่ AI ทำงานเร็ว"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังวาดตัวละครเดิมด้วย Flux...")
    
    # รวม Character Anchor เข้ากับ Prompt ของแต่ละฉาก
    full_prompt = f"{CHAR_ANCHOR}, {prompt}, anime meme style, exaggerated expressions, vibrant colors, high contrast, masterpiece"
    clean_prompt = re.sub(r'[^\w\s]', '', full_prompt).strip().replace(' ', '%20')
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=512&height=896&seed=12345&nologo=true&model=flux"

    for attempt in range(4):
        try:
            response = requests.get(url, headers=headers, timeout=120)
            if response.status_code == 200:
                with open(filename, 'wb') as f: f.write(response.content)
                print(f"      ✅ ฉากที่ {scene_num} สำเร็จ!")
                return True
            time.sleep(10)
        except: time.sleep(10)
    
    # ฉุกเฉิน: วาดพื้นหลังเปล่า
    Image.new('RGB', (1080, 1920), color=(20, 20, 40)).save(filename, 'JPEG')
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. AI กำลังคิดบทและตรวจสอบความถูกต้อง (Self-Correction)...")
        
        # 📌 สั่งให้ AI คิดสคริปต์ที่สะอาดและตรวจทานก่อน
        prompt_sys = (
            "Act as a professional YouTube Shorts creator. Topic: 'Emergency Fund' (เงินสำรองฉุกเฉิน). "
            "Task: Create a 5-scene script. \n"
            "Rules:\n"
            "1. Voiceover text must be PURE Thai speech. NO 'Scene 1:', NO 'Voice:', NO brackets.\n"
            "2. Image prompts must be detailed and involve the SAME character (young office worker).\n"
            "3. Caption must be HUGE Thai words for the screen.\n"
            "4. THINK: Is the story funny and educational? If not, rewrite it internally before providing the JSON.\n"
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        
        print(f"🎬 หัวข้อ: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ (ตัดเท็กซ์ส่วนเกินออกแล้ว)...")
        # รวมเสียงพากย์ทุกฉาก
        full_voice_text = " ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-5% --voice "th-TH-NiwatNeural" --text "{full_voice_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. วาดภาพด้วยตัวละครคงที่...")
        for i, sc in enumerate(data['scenes']):
            fetch_image_turbo_v2(sc['prompt'], f"i_{i}.jpg", i+1)

        print("🎬 4. แก้ไขซับไตเติลภาษาไทยและประกอบ Video...")
        
        # ⚠️ แก้ไขซับไตเติล: ใช้ฟอนต์ Sans-Serif มาตรฐานของ Linux เพื่อให้ไทยอ่านออก
        with open("subs.ass", "w", encoding="utf-8-sig") as f: # ใช้ utf-8-sig เพื่อความชัวร์
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            # ใช้ฟอนต์ 'Sans' หรือ 'DejaVu Sans' ซึ่งปกติจะมีใน Ubuntu Runner
            f.write(f"Style: Viral,Sans,110,&H0000FFFF,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,12,8,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i, sc in enumerate(data['scenes']):
                start = i * SCENE_DURATION
                end = (i + 1) * SCENE_DURATION
                f.write(f"Dialogue: 0,0:{start:02}:00.00,0:{end:02}:00.00,Viral,,0,0,0,,{sc['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        # 📌 FFmpeg: ฝังซับและซูม
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass=subs.ass,zoompan=z='min(zoom+0.0015,1.5)':d=300:s=1080x1920\" "
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
                body={"snippet": {"title": data['title'], "categoryId": "23"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ! ตัวละครหน้าเหมือนกันและซับไทยมาแล้ว!")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
