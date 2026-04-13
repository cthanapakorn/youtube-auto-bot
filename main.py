import sys
import subprocess
import os

# --- 🛠️ 1. ระบบซ่อมแซมตัวเอง: ติดตั้ง Library ---
def auto_install_requirements():
    packages = {
        "google.genai": "google-genai",
        "edge_tts": "edge-tts",
        "requests": "requests",
        "PIL": "pillow",
        "googleapiclient": "google-api-python-client",
        "google_auth_oauthlib": "google-auth-oauthlib"
    }
    for module_name, pip_name in packages.items():
        try:
            __import__(module_name)
        except ImportError:
            print(f"📦 ระบบกำลังติดตั้ง '{pip_name}'...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

auto_install_requirements()

# --- 🛠️ 2. Import Libraries ---
import re
import json
import time
import random
import shutil
import traceback
import asyncio
import requests
import edge_tts
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

if sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass
if sys.stderr.encoding.lower() != 'utf-8':
    try: sys.stderr.reconfigure(encoding='utf-8')
    except: pass

SCENE_COUNT = 6   
SCENE_DURATION = 10 
VIDEO_PRIVACY = "private"
CHAR_ANCHOR = "An expressive 29-year-old Thai male professional, neat modern haircut, business casual attire, highly detailed anime style, highly detailed expressive face, perfectly drawn eyes, anatomically correct hands, exactly 5 fingers per hand, flawless human anatomy, vibrant colors, modern webtoon style, masterpiece illustration"

def ensure_font_exists():
    """✅ ระบบโหลดฟอนต์อัจฉริยะ ป้องกันการโหลดไฟล์ขยะ/หน้าเว็บ 404"""
    font_filename = "font.ttf"
    
    if os.path.exists(font_filename) and os.path.getsize(font_filename) < 40000:
        os.remove(font_filename)
        print("🗑️ ตรวจพบไฟล์ฟอนต์ขยะ ทำการลบทิ้งเพื่อโหลดใหม่...")
        
    if not os.path.exists(font_filename):
        print("⏳ กำลังดาวน์โหลดฟอนต์ไทย...")
        urls = [
            "https://raw.githubusercontent.com/google/fonts/main/ofl/kanit/Kanit-Bold.ttf",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/prompt/Prompt-Bold.ttf",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/sarabun/Sarabun-Bold.ttf"
        ]
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        for url in urls:
            try:
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code == 200 and len(r.content) > 40000:
                    with open(font_filename, 'wb') as f:
                        f.write(r.content)
                    print(f"✅ ดาวน์โหลดฟอนต์ของจริงสำเร็จสมบูรณ์!")
                    return
            except Exception:
                continue
        print("⚠️ โหลดฟอนต์ไม่สำเร็จ ซับไตเติลอาจแสดงผลผิดปกติ")

def fetch_image_cartoon(prompt, filename, scene_num):
    print(f"   🎨 ฉากที่ {scene_num}: กำลังวาดภาพสไตล์การ์ตูน...")
    clean_p = re.sub(r'[^\w\s]', '', str(prompt)).strip().replace(' ', '%20')
    style = "high-quality anime style, stunning visual, dramatic lighting, detailed background, perfect hands, detailed eyes, masterpiece"
    url = f"https://image.pollinations.ai/prompt/{clean_p},{CHAR_ANCHOR},{style}?width=1080&height=1920&seed={random.randint(1,999999)}&nologo=true&model=flux"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    for attempt in range(5): 
        try:
            r = requests.get(url, headers=headers, timeout=120)
            if r.status_code == 200 and len(r.content) > 20000:
                with open(filename, 'wb') as f:
                    f.write(r.content)
                print(f"      ✅ ฉากที่ {scene_num} วาดเสร็จสิ้น!")
                return True
            time.sleep(10)
        except Exception:
            time.sleep(10)
    
    Image.new('RGB', (1080, 1920), color=(15, 15, 15)).save(filename, 'JPEG')
    return True

async def generate_voice(text, output_file):
    max_retries = 5 
    for attempt in range(max_retries):
        try:
            print(f"   🎙️ กำลังเชื่อมต่อเซิร์ฟเวอร์เสียง (รอบที่ {attempt + 1}/{max_retries})...")
            communicate = edge_tts.Communicate(text, "th-TH-NiwatNeural", rate="-3%")
            await communicate.save(output_file)
            return  
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  
                print(f"   🔄 เซิร์ฟเวอร์เสียงไม่ตอบสนอง รอ {wait_time} วิแล้วลองใหม่...")
                await asyncio.sleep(wait_time)
            else:
                raise Exception("เซิร์ฟเวอร์เสียงของ Microsoft ขัดข้อง กรุณาลองใหม่ภายหลัง")

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("ไม่พบ GEMINI_API_KEY ในระบบ กรุณาตรวจสอบการตั้งค่า Secret")
            
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังคิดหัวข้อการเงินระดับไวรัล และเขียนบท...")
        data = None
        for attempt in range(5): 
            print(f"🧠 [Attempt {attempt+1}] AI กำลังสุ่มหัวข้อและร่างบท...")
            prompt_sys = (
                "คุณคือผู้เชี่ยวชาญด้านการสร้างวิดีโอ YouTube Shorts ระดับไวรัล\n"
                "เป้าหมาย: สร้างคอนเทนต์วิดีโอความยาว 60 วินาที ที่ดึงดูดคนดูตั้งแต่ 3 วินาทีแรก\n"
                "หัวข้อ: 'ให้สุ่มคิดหัวข้อใหม่เกี่ยวกับการเงิน การลงทุน การสร้างรายได้ หรืออิสรภาพทางการเงิน'\n"
                "**ให้คิดใหม่จนกว่าจะได้หัวข้อระดับไวรัลที่กระแทกใจคนดูที่สุด!**\n\n"
                "โครงสร้างสคริปต์ 6 ฉาก (ฉากละ 10 วินาที):\n"
                "- ฉาก 1: Hook (ประโยคสั้น กระแทกใจ ชวนสงสัย)\n"
                "- ฉาก 2: Setup (ปูเรื่อง)\n"
                "- ฉาก 3: ปัญหาเริ่มหนัก หรือ ความลับถูกเปิดเผย\n"
                "- ฉาก 4: วิกฤต หรือ จุดพีคของเนื้อหา\n"
                "- ฉาก 5: จุดเปลี่ยน หรือ วิธีแก้ปัญหา\n"
                "- ฉาก 6: บทเรียน + ทิ้งท้าย (มีข้อคิดชัดเจน)\n\n"
                "กฎเหล็กแต่ละฉาก:\n"
                "1. บทพากย์ (text): ภาษาไทย โทนเสียงจริงจัง มีอารมณ์ (ความยาว 40-50 คำต่อฉาก เพื่อให้พูดจบใน 10 วินาที)\n"
                "2. คำสั่งวาดรูป (prompt): ภาษาอังกฤษ บรรยายเหตุการณ์ สภาพแวดล้อม และอารมณ์ สลับภาพชายวัย 29 ปี กับภาพเหตุการณ์\n"
                "3. ซับไตเติล (caption): คำไทยสั้นๆ 1-2 คำ กระแทกอารมณ์\n\n"
                "Output STRICT JSON FORMAT ONLY:\n"
                "{\n  \"viral_score\": 9,\n  \"title\": \"...\",\n  \"desc\": \"...\",\n  \"tags\": \"...\",\n  \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]\n}"
            )
            response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
            
            raw_text = response.text
            clean_text = raw_text.replace('```json', '').replace('```', '').strip()
            match = re.search(r'\{.*\}', clean_text, re.DOTALL)
            if not match: continue
                
            try:
                temp_data = json.loads(match.group())
            except Exception:
                continue

            score = temp_data.get('viral_score', 0)
            if score >= 8 and len(temp_data.get('scenes', [])) == SCENE_COUNT:
                data = temp_data
                break

        if not data:
            raise ValueError("สร้างบทไม่สำเร็จใน 5 รอบ AI อาจจะติดขัดการตอบกลับ JSON")

        print(f"📌 หัวข้อที่ได้: {data.get('title', 'Viral Finance Shorts')}")
        
        print("💾 กำลังบันทึกข้อมูลสคริปต์ลงโฟลเดอร์ output/ ...")
        os.makedirs("output", exist_ok=True)
        with open("output/metadata.txt", "w", encoding="utf-8") as f:
            f.write(f"Title: {data.get('title', '')}\n")
            f.write(f"Description: {data.get('desc', '')}\n")
            f.write(f"Tags: {data.get('tags', '')}\n")
        
        with open("output/script.txt", "w", encoding="utf-8") as f:
            for i, sc in enumerate(data.get('scenes', [])):
                f.write(f"Scene {i+1}: {sc.get('text', '')}\n")
        
        print("🎙️ 2. สร้างเสียงพากย์คุณนิวัฒน์ ด้วย Python Native API...")
        full_voice = " . . . ".join([str(s.get('text', '')) for s in data['scenes']])
        
        asyncio.run(generate_voice(full_voice, "v.mp3"))
        print("   ✅ สร้างเสียงเสร็จสมบูรณ์!")

        print("🖼️ 3. วาดภาพการ์ตูนคุณภาพสูง 6 ฉาก...")
        for i, sc in enumerate(data['scenes']):
            fetch_image_cartoon(sc.get('prompt', ''), f"i_{i}.jpg", i+1)
            time.sleep(3)

        print("🎬 4. ประกอบวิดีโอ 60 วินาที...")
        with open("l.txt", "w", encoding="utf-8") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")

        ensure_font_exists()

        drawtext_filters = []
        font_opt = ""
        if os.path.exists("font.ttf") and os.path.getsize("font.ttf") > 40000:
            abs_font_path = os.path.abspath("font.ttf").replace('\\', '/').replace(':', r'\:')
            font_opt = f"fontfile='{abs_font_path}':"
        
        for i in range(SCENE_COUNT):
            start_time = i * SCENE_DURATION
            end_time = start_time + 3  
            caption = str(data['scenes'][i].get('caption', '')).replace("'", "").replace(":", "").replace(",", "").replace("%", "").replace("\\", "").strip()
            if not caption: continue
            
            dt = f"drawtext={font_opt}text='{caption}':fontcolor=white:bordercolor=black:borderw=6:fontsize=160:x=(w-text_w)/2:y=(h-text_h)/2+350:enable='between(t,{start_time},{end_time})'"
            drawtext_filters.append(dt)
            
        drawtexts_str = ",".join(drawtext_filters)
        
        vf_string = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.001,1.3)':d=250:s=1080x1920"
        if drawtexts_str:
            vf_string += f",{drawtexts_str}"

        cmd = [
            "ffmpeg", "-y", 
            "-f", "concat", "-safe", "0", "-i", "l.txt", 
            "-i", "v.mp3"
        ]
        
        if os.path.exists("bg.mp3"):
            cmd.extend([
                "-i", "bg.mp3",
                "-filter_complex", "[1:a]volume=1.0[a1];[2:a]volume=0.08[a2];[a1][a2]amix=inputs=2:duration=first[a]",
                "-map", "0:v", "-map", "[a]"
            ])
        else:
            cmd.extend(["-map", "0:v", "-map", "1:a", "-c:a", "aac"])

        cmd.extend([
            "-vf", vf_string,
            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "25", "-t", "60", "final.mp4"
        ])
        
        print("   ✅ กำลังรัน FFmpeg ตัดต่อคลิป...")
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube พร้อม SEO...")
        creds_data = None
        if "YOUTUBE_CREDENTIALS" in
