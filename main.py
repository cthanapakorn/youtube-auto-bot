import sys
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

# --- ⚙️ ตั้งค่าพื้นฐาน ---
SCENE_COUNT = 6
VIDEO_PRIVACY = "private" 
CHAR_ANCHOR = "An expressive 29-year-old Thai male professional, symmetrical face, flawlessly drawn eyes, exactly 5 distinct fingers, business casual, high-detail anime webtoon style, masterpiece, 8k resolution, cinematic lighting"

def get_audio_duration(file_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True
    )
    return float(result.stdout.strip())

def fetch_image(prompt, filename, scene_num):
    print(f"🎨 ฉากที่ {scene_num}: กำลังวาดภาพ...")
    # ✅ แก้ SyntaxError: แยกคำสั่งล้าง Prompt ออกมาข้างนอก f-string
    clean_p = re.sub(r'[^\w\s]', '', str(prompt))
    negative_p = "deformed anatomy, extra fingers, asymmetric eyes, text, watermark, blur"
    
    full_p = f"{clean_p},{CHAR_ANCHOR},vibrant colors,masterpiece"
    url = f"https://image.pollinations.ai/prompt/{full_p}?width=1080&height=1920&seed={random.randint(1,999999)}&nologo=true&model=flux&negative_prompt={negative_p.replace(' ', '%20')}"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    for _ in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=120)
            if r.status_code == 200:
                with open(filename, 'wb') as f: f.write(r.content)
                return True
        except: time.sleep(5)
    return False

async def generate_voice(text, output_file):
    communicate = edge_tts.Communicate(text, "th-TH-NiwatNeural", rate="-5%")
    await communicate.save(output_file)

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key: raise ValueError("ไม่พบ GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        cats = ["ความลับการเงินมหาเศรษฐี", "จิตวิทยาความสำเร็จ", "เรื่องแปลกในโลกการลงทุน", "นิสัยคนรวย"]
        selected_cat = random.choice(cats)
        print(f"🧠 หัวข้อวันนี้: {selected_cat}")

        prompt_sys = f"""
        สร้างบท YouTube Shorts 60 วินาที หัวข้อ: {selected_cat}
        กฎเหล็ก:
        1. ความยาวรวมทุกฉาก 120-130 คำ (ห้ามเกิน)
        2. ใส่เครื่องหมาย , และ . เพื่อบังคับจังหวะหายใจของเสียงพากย์ AI
        3. ฉากสุดท้ายต้องสรุปจบ และทิ้งท้าย "ฝากกดติดตามด้วยนะครับ"
        4. caption ใน JSON ต้องสั้นมาก (ไม่เกิน 15 ตัวอักษร)
        
        Output STRICT JSON FORMAT:
        {{ "title": "...", "desc": "...", "tags": "...", 
           "scenes": [{{"text": "บทพูดใส่ลูกน้ำ", "prompt": "english image prompt", "caption": "สั้นๆ"}}] }}
        """
        response = client.models.generate_content(model='models/gemini-2.0-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        # 🎙️ 1. สร้างเสียงพากย์
        import subprocess # นำเข้าเฉพาะที่จำเป็น
        full_script = " ".join([s['text'].strip() + "." for s in data['scenes']])
        asyncio.run(generate_voice(full_script, "v.mp3"))
        
        duration = get_audio_duration("v.mp3")
        scene_time = duration / SCENE_COUNT

        # 🖼️ 2. วาดภาพ 6 ฉาก
        for i, sc in enumerate(data['scenes']):
            fetch_image(sc['prompt'], f"i_{i}.jpg", i+1)

        # 🎬 3. ประกอบวิดีโอ
        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration {scene_time:.2f}\n")
            f.write(f"file 'i_5.jpg'")

        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.001,1.3)':d=250:s=1080x1920"
        subs = []
        for i, sc in enumerate(data['scenes']):
            cap = sc['caption'].replace("'", "").replace(":", "")
            start, end = i*scene_time, (i+1)*scene_time
            subs.append(f"drawtext=text='{cap}':fontcolor=white:fontsize=120:borderw=5:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2+400:enable='between(t,{start:.2f},{end:.2f})'")
        
        final_vf = f"{vf},{','.join(subs)}"
        
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "l.txt", "-i", "v.mp3"]
        if os.path.exists("bg.mp3"):
            cmd.extend(["-ss", "30", "-i", "bg.mp3", "-filter_complex", "[1:a]volume=1.0[a1];[2:a]volume=0.1[a2];[a1][a2]amix=inputs=2:duration=first[a]", "-map", "0:v", "-map", "[a]"])
        else: cmd.extend(["-map", "0:v", "-map", "1:a"])
        
        cmd.extend(["-vf", final_vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", f"{duration}", "final.mp4"])
        subprocess.run(cmd, check=True)

        # 🚀 4. อัปโหลดสู่ YouTube
        print("🚀 กำลังส่งตรงไป YouTube...")
        creds_info = json.loads(os.getenv("YOUTUBE_CREDENTIALS"))
        creds = YoutubeCredentials.from_authorized_user_info(creds_info)
        youtube = build("youtube", "v3", credentials=creds)
        youtube.videos().insert(
            part="snippet,status",
            body={"snippet": {"title": data['title'], "description": f"{data['desc']}\n\n{data['tags']}", "categoryId": "27"}, 
                  "status": {"privacyStatus": VIDEO_PRIVACY}},
            media_body=MediaFileUpload("final.mp4")
        ).execute()
        print("✨ ภารกิจสำเร็จ 100%!")

    except Exception as e:
        print(f"❌ พัง: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_workflow()
