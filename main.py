import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# --- ⚙️ ตั้งค่า (10 ฉาก x 6 วินาที = 60 วินาทีพอดี) ---
MODEL_ID = 'models/gemini-2.5-flash'
SCENE_COUNT = 10   
SCENE_DURATION = 6 
VIDEO_PRIVACY = "private"
CHAR_ANCHOR = "A charismatic 25-year-old Thai male office worker, messy black hair, white shirt, blue tie, hyper-realistic anime style."

def fetch_image_pro(prompt, filename, scene_num):
    """วาดภาพคุณภาพสูง (1024x1792) และรักษาหน้าตัวละครให้เป๊ะ"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพความละเอียดสูง...")
    
    # เพิ่มคุณภาพใน Prompt
    full_prompt = f"{CHAR_ANCHOR}, {prompt}, detailed facial features, expressive eyes, cinematic lighting, 8k resolution, trending on pixiv"
    clean_prompt = re.sub(r'[^\w\s]', '', full_prompt).strip().replace(' ', '%20')
    
    # เพิ่ม Seed เพื่อความต่อเนื่องของภาพ
    url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1024&height=1792&seed=8888&nologo=true&model=flux"

    for attempt in range(4):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200:
                with open(filename, 'wb') as f: f.write(r.content)
                return True
            time.sleep(10)
        except: time.sleep(10)
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. AI กำลังออกแบบบทพากย์ที่มีจังหวะหนักเบาและตรวจสอบความถูกต้อง...")
        # 📌 สั่งให้ AI ใส่ ... เพื่อสร้างจังหวะหยุดพัก (Pause) ให้เสียงพากย์ดูสมจริง
        prompt_sys = (
            "Create a 60s Thai viral script about 'Inflation'. Split into 10 SHORT segments (6s each). "
            "Rules:\n"
            "1. Text for voice: Use '...' for natural pauses. Use '!' for emphasis. No technical tags.\n"
            "2. Scene prompt: Describe action clearly for the SAME character.\n"
            "3. Caption: 1-3 POWERFUL words per segment to sync with speech.\n"
            "Check if the flow is emotional and realistic before outputting.\n"
            "Output STRICT JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        
        response = client.models.generate_content(model=MODEL_ID, contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        
        print(f"🎬 หัวข้อ: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ที่มีน้ำเสียงหนักเบา...")
        # ใช้เสียง th-TH-PremwadeeNeural เพราะน้ำเสียงมีความเป็นธรรมชาติและใส่อารมณ์ได้ดีกว่า
        full_voice_text = " . . ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-5% --voice "th-TH-PremwadeeNeural" --text "{full_voice_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. วาดภาพความละเอียดสูง (Character Consistency)...")
        for i, sc in enumerate(data['scenes']):
            fetch_image_pro(sc['prompt'], f"i_{i}.jpg", i+1)

        print("🎬 4. แก้ปัญหาซับไทยและประกอบ Video...")
        
        # ตรวจสอบว่ามีไฟล์ฟอนต์ไหม ถ้าไม่มีจะใช้ค่าพื้นฐาน (แต่อาจจะอ่านไม่ออก)
        font_path = "font.ttf" if os.path.exists("font.ttf") else "Sans"
        
        # ⚠️ สร้างไฟล์ซับไตเติล (เปลี่ยนซับทุก 6 วินาทีเพื่อให้ตรงตามคำพูด)
        with open("subs.ass", "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            # 🎨 ซับตัวใหญ่มาก สีเหลือง ขอบดำหนา วางกึ่งกลางจอ
            f.write(f"Style: Viral,{font_path},130,&H0000FFFF,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,15,10,2,80,80,900,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i, sc in enumerate(data['scenes']):
                start = i * SCENE_DURATION
                end = (i + 1) * SCENE_DURATION
                f.write(f"Dialogue: 0,0:{start:02}:00.00,0:{end:02}:00.00,Viral,,0,0,0,,{sc['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'") 
        
        # 📌 FFmpeg: ขยายภาพชัด 8K, ฝังซับจากไฟล์ฟอนต์ตรงๆ และทำ Zoompan
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass=subs.ass,zoompan=z='min(zoom+0.0015,1.5)':d=150:s=1080x1920\" "
            f"-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
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
            print("✨ ภารกิจสำเร็จ! ภาพชัด เสียงเหมือนคน ซับไทยอ่านออกแล้ว!")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
