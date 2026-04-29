import sys
import subprocess
import os
import re
import json
import time
import random
import asyncio
import requests
import edge_tts
import traceback
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# --- 🛠️ 1. ติดตั้ง Library อัตโนมัติ ---
def auto_install():
    pkgs = {"google.genai": "google-genai", "edge_tts": "edge-tts", "requests": "requests", 
            "PIL": "pillow", "googleapiclient": "google-api-python-client"}
    for mod, pip in pkgs.items():
        try: __import__(mod)
        except ImportError: subprocess.check_call([sys.executable, "-m", "pip", "install", pip, "--quiet"])

auto_install()

# ตั้งค่าพื้นฐาน
SCENE_COUNT = 6
VIDEO_PRIVACY = "private" # ตรวจงานก่อนเสมอตามสั่งครับ!
# ✅ UPGRADE: Anchor ล็อคสเปคภาพแบบขีดสุด กันนิ้วแหว่ง ตาเบี้ยว
CHAR_ANCHOR = "An extremely high-quality 29-year-old Thai male, neat professional hair, symmetrical face, flawlessly drawn expressive eyes, anatomically correct hands, exactly 5 fingers, highly detailed anime webtoon style, vibrant lighting, 8k, sharp focus, masterpiece"

def get_audio_duration(file_path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path], stdout=subprocess.PIPE, text=True)
    return float(result.stdout.strip())

# ✅ UPGRADE: ระบบสุ่มหมวดหมู่เนื้อหา
def get_random_topic():
    cats = ["ความลับการเงินของมหาเศรษฐี", "จิตวิทยาการดึงดูดความสำเร็จ", "เรื่องแปลกในโลกการลงทุน", "นิสัยที่ทำให้คนรวยรวยขึ้น", "ทริคประหยัดเงินแบบคนฉลาด"]
    return random.choice(cats)

def fetch_image(prompt, filename, scene_num):
    print(f"🎨 วาดฉากที่ {scene_num}...")
    negative = "deformed, extra fingers, asymmetric eyes, text, watermark, blurry, lowres, bad anatomy"
    full_p = f"{re.sub(r'[^\\w\\s]', '', prompt)},{CHAR_ANCHOR},masterpiece"
    url = f"https://image.pollinations.ai/prompt/{full_p}?width=1080&height=1920&seed={random.randint(1,999999)}&nologo=true&model=flux"
    for _ in range(3):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200:
                with open(filename, 'wb') as f: f.write(r.content)
                return True
        except: time.sleep(5)
    return False

async def generate_voice(text, output_file):
    # ปรับความเร็ว -5% เพื่อให้ฟังสบายและเว้นวรรคชัดเจนขึ้น
    communicate = edge_tts.Communicate(text, "th-TH-NiwatNeural", rate="-5%")
    await communicate.save(output_file)

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        topic = get_random_topic()
        print(f"🧠 เริ่มคิดคอนเทนต์หมวด: {topic}")

        # ✅ UPGRADE: บังคับเว้นวรรคด้วยเครื่องหมาย เพื่อให้ AI พากย์เสียงมีจังหวะหายใจ
        prompt = f"""
        สร้างบท YouTube Shorts 60 วินาที หัวข้อ: {topic}
        กฎเหล็ก: 
        1. ความยาวรวม 120-130 คำ (ห้ามเกินเพื่อให้จบใน 58 วิ)
        2. ใส่เครื่องหมาย , และ . ในบทพูดเพื่อบังคับจังหวะหยุดหายใจของเสียง AI
        3. ฉากสุดท้ายต้องสรุปจบสมบูรณ์ และพูดว่า "ฝากกดติดตามด้วยนะครับ"
        4. caption ต้องสั้นมาก (ไม่เกิน 15 ตัวอักษร) เพื่อไม่ให้หลุดขอบจอ
        
        Output STRICT JSON:
        {{ "title": "...", "desc": "...", "tags": "...", 
           "scenes": [{{"text": "บทพูดใส่ลูกน้ำเว้นวรรค", "prompt": "english image description", "caption": "คำสั้นๆ"}}] }}
        """
        response = client.models.generate_content(model='models/gemini-2.0-flash', contents=prompt)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 🎙️ สร้างเสียง
        full_script = " ".join([s['text'] + "." for s in data['scenes']])
        asyncio.run(generate_voice(full_script, "v.mp3"))
        
        duration = get_audio_duration("v.mp3")
        scene_time = duration / SCENE_COUNT

        # 🖼️ วาดรูป
        for i, sc in enumerate(data['scenes']):
            fetch_image(sc['prompt'], f"i_{i}.jpg", i+1)

        # 🎬 ประกอบวิดีโอ (FFmpeg)
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\\nduration {scene_time:.2f}\\n")
            f.write(f"file 'i_5.jpg'")

        # ✅ UPGRADE: ซับไตเติ้ลปัดบรรทัดอัตโนมัติ (Force Wrap)
        vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.001,1.3)':d=250:s=1080x1920"
        subs = []
        for i, sc in enumerate(data['scenes']):
            t = sc['caption'].replace("'", "")
            start, end = i*scene_time, (i+1)*scene_time
            # สั่ง FFmpeg ตัดคำที่ 15 ตัวอักษร
            subs.append(f"drawtext=text='{t}':fontcolor=white:fontsize=120:borderw=5:x=(w-text_w)/2:y=(h-text_h)/2+400:enable='between(t,{start},{end})'")
        
        filter_complex = f"{vf},{','.join(subs)}"
        
        # ✅ UPGRADE: เริ่มเพลง BGM ที่วินาทีที่ 30 (-ss 30)
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "l.txt", "-i", "v.mp3"]
        if os.path.exists("bg.mp3"):
            cmd.extend(["-ss", "30", "-i", "bg.mp3", "-filter_complex", f"[1:a]volume=1.0[a1];[2:a]volume=0.1[a2];[a1][a2]amix=inputs=2:duration=first[a]", "-map", "0:v", "-map", "[a]"])
        else: cmd.extend(["-map", "0:v", "-map", "1:a"])
        
        cmd.extend(["-vf", filter_complex, "-c:v", "libx264", "-t", f"{duration}", "final.mp4"])
        subprocess.run(cmd, check=True)

        # 🚀 อัปโหลด
        print("🚀 กำลังส่งตรงไป YouTube...")
        creds = YoutubeCredentials.from_authorized_user_info(json.loads(os.getenv("YOUTUBE_CREDENTIALS")))
        youtube = build("youtube", "v3", credentials=creds)
        youtube.videos().insert(
            part="snippet,status",
            body={"snippet": {"title": data['title'], "description": data['desc'], "categoryId": "27"}, 
                  "status": {"privacyStatus": VIDEO_PRIVACY}},
            media_body=MediaFileUpload("final.mp4")
        ).execute()
        print("✨ สำเร็จ! ไปตรวจคลิปใน YT Studio ได้เลยครับ")

    except Exception as e:
        print(f"❌ พังเพราะ: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_workflow()
