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

# ตั้งค่าการอ่านภาษาไทยให้รองรับทุกระบบ
if sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass
if sys.stderr.encoding.lower() != 'utf-8':
    try: sys.stderr.reconfigure(encoding='utf-8')
    except: pass

SCENE_COUNT = 6   
VIDEO_PRIVACY = "private" 
# ล็อคสเปคภาพให้แน่นหนาที่สุด เพื่อความสมบูรณ์ทุกภาพ
CHAR_ANCHOR = "An expressive 29-year-old Thai male professional, wide angle shot, flawless human anatomy, perfectly drawn eyes, exactly 5 fingers per hand, no extra limbs, business casual attire, highly detailed anime webtoon style, vibrant colors, masterpiece illustration"

def get_audio_duration(file_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"⚠️ ไม่สามารถหาความยาวเสียงได้ ใช้ค่าพื้นฐาน 55 วินาทีแทน: {e}")
        return 55.0

def ensure_font_exists():
    font_filename = "font.ttf"
    if os.path.exists(font_filename) and os.path.getsize(font_filename) < 40000:
        os.remove(font_filename)
    if not os.path.exists(font_filename):
        print("⏳ กำลังดาวน์โหลดฟอนต์ไทย...")
        urls = [
            "https://raw.githubusercontent.com/google/fonts/main/ofl/kanit/Kanit-Bold.ttf",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/prompt/Prompt-Bold.ttf",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/sarabun/Sarabun-Bold.ttf"
        ]
        headers = {'User-Agent': 'Mozilla/5.0'}
        for url in urls:
            try:
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code == 200 and len(r.content) > 40000:
                    with open(font_filename, 'wb') as f:
                        f.write(r.content)
                    print(f"✅ ดาวน์โหลดฟอนต์สำเร็จ!")
                    return
            except:
                continue

# ฟังก์ชันตัดคำขึ้นบรรทัดใหม่ (Word Wrap) สำหรับซับไตเติ้ล
def wrap_text(text, max_chars_per_line=18):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= max_chars_per_line:
            current_line += (word + " ")
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    if current_line:
        lines.append(current_line.strip())
    
    return "\n".join(lines)

def fetch_image_cartoon(prompt, filename, scene_num):
    print(f"   🎨 ฉากที่ {scene_num}: กำลังวาดภาพ...")
    
    # บังคับใส่ Negative Prompt (ข้อห้าม) เข้าไปในทุกรูปอย่างเด็ดขาด!
    negative_prompt = "no deformed anatomy, no asymmetric eyes, no extra fingers, no extra limbs, no text, no watermark, no blurred faces"
    
    clean_p = re.sub(r'[^\w\s]', '', str(prompt)).strip().replace(' ', '%20')
    style = "high-quality anime style, stunning visual, dramatic lighting, detailed background, masterpiece"
    
    full_prompt = f"{clean_p},{CHAR_ANCHOR},{style}"
    url = f"https://image.pollinations.ai/prompt/{full_prompt}?width=1080&height=1920&seed={random.randint(1,999999)}&nologo=true&model=flux&negative_prompt={negative_prompt.replace(' ', '%20')}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for attempt in range(5): 
        try:
            r = requests.get(url, headers=headers, timeout=120)
            if r.status_code == 200 and len(r.content) > 20000:
                with open(filename, 'wb') as f: f.write(r.content)
                print(f"      ✅ ฉากที่ {scene_num} วาดเสร็จ! (ใส่รายละเอียดครบถ้วน)")
                return True
            time.sleep(10)
        except:
            time.sleep(10)
    Image.new('RGB', (1080, 1920), color=(15, 15, 15)).save(filename, 'JPEG')
    return True

async def generate_voice(text, output_file):
    max_retries = 5 
    for attempt in range(max_retries):
        try:
            print(f"   🎙️ เชื่อมต่อเซิร์ฟเวอร์เสียง ({attempt + 1}/{max_retries})...")
            communicate = edge_tts.Communicate(text, "th-TH-NiwatNeural", rate="-3%")
            await communicate.save(output_file)
            return  
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  
                print(f"   🔄 รอ {wait_time} วิ...")
                await asyncio.sleep(wait_time)
            else:
                raise Exception("เซิร์ฟเวอร์เสียงไม่ตอบสนอง")

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("ไม่พบ GEMINI_API_KEY กรุณาตรวจสอบการตั้งค่า Secret")
            
        client = genai.Client(api_key=api_key.strip())
        
        TOPIC_CATEGORIES = [
            "เรื่องลี้ลับในประวัติศาสตร์การเงิน",
            "ข้อคิดการใช้ชีวิตจากมหาเศรษฐีระดับโลก",
            "ทริคจิตวิทยาการเก็บเงินที่คนส่วนใหญ่ไม่รู้",
            "ความจริงของการลงทุนที่โรงเรียนไม่เคยสอน",
            "นิสัยเล็กๆ ที่ทำให้คนรวยต่างจากคนทั่วไป"
        ]
        random_topic = random.choice(TOPIC_CATEGORIES)
        
        print(f"🧠 1. คิดหัวข้อและเขียนบท (หมวดหมู่: {random_topic})...")
        data = None
        for attempt in range(5): 
            try:
                print(f"🧠 [Attempt {attempt+1}]...")
                
                # 🔥 แก้ไขล่าสุด: บังคับเว้นวรรคด้วยลูกน้ำ (,) และ จุด (.)
                prompt_sys = f"""
                คุณคือผู้เชี่ยวชาญด้าน YouTube Shorts ไวรัล
                เป้าหมาย: สร้างวิดีโอ 60 วินาที หัวข้อ: {random_topic}
                กฎเหล็ก:
                1. ความยาวรวมทั้งหมดต้องไม่เกิน 130 คำ แบ่งเป็น 6 ฉาก 
                2. ภาษาพูดเป็นธรรมชาติ **และที่สำคัญที่สุด: ให้ใส่เครื่องหมายลูกน้ำ (,) ตรงจุดที่ต้องการให้เสียงพากย์หยุดพักหายใจ และใส่เครื่องหมายจุด (.) เมื่อจบประโยคเสมอ เพื่อบังคับให้ AI พากย์เสียงเว้นวรรคได้ถูกต้องและไม่รัวจนความหมายเพี้ยน**
                3. ในส่วนของ 'caption' (ซับไตเติ้ล) ให้เขียนให้สั้นกระชับที่สุด ดึงมาแค่ใจความสำคัญของฉากนั้น เพื่อไม่ให้ยาวเกินขอบจอ (ห้ามมีลูกน้ำใน caption)
                4. ฉากสุดท้าย ต้องสรุปจบ และทิ้งท้าย "ฝากกดติดตามด้วยนะครับ"
                5. 'prompt' รูปภาพ ให้เขียนเป็นภาษาอังกฤษ เน้นรายละเอียดองค์ประกอบภาพให้ชัดเจน
                
                Output STRICT JSON FORMAT ONLY:
                {{
                  "viral_score": 9,
                  "title": "...",
                  "desc": "...",
                  "tags": "...",
                  "scenes": [{{"text": "...", "prompt": "...", "caption": "..."}}]
                }}
                """
                response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
                raw_text = response.text
                clean_text = raw_text.replace('```json', '').replace('```', '').strip()
                match = re.search(r'\{.*\}', clean_text, re.DOTALL)
                if not match: continue
                
                temp_data = json.loads(match.group())
                if temp_data.get('viral_score', 0) >= 8 and len(temp_data.get('scenes', [])) == SCENE_COUNT:
                    data = temp_data
                    break
            except Exception as e:
                print(f"   ⚠️ เซิร์ฟเวอร์ Gemini คิวเต็มหรือขัดข้อง (รอ 15 วิแล้วลองใหม่)...")
                time.sleep(15)
                continue

        if not data:
            raise ValueError("สร้างบทไม่สำเร็จ เซิร์ฟเวอร์อาจจะทำงานหนักเกินไป")

        print(f"📌 หัวข้อที่ได้: {data.get('title', 'Viral Finance')}")
        
        os.makedirs("output", exist_ok=True)
        with open("output/metadata.txt", "w", encoding="utf-8") as f:
            f.write(f"Title: {data.get('title')}\nDescription: {data.get('desc')}\nTags: {data.get('tags')}")

        print("🎙️ 2. สร้างเสียงพากย์...")
        
        # 🔥 แก้ไขล่าสุด: ใส่จุด (.) เติมท้ายทุกฉาก เพื่อบังคับหยุดพักหายใจก่อนเปลี่ยนภาพ
        full_voice = " ".join([str(s.get('text', '')).strip() + "." for s in data['scenes']])
        
        asyncio.run(generate_voice(full_voice, "v.mp3"))

        voice_duration = get_audio_duration("v.mp3")
        scene_duration = voice_duration / SCENE_COUNT
        print(f"⏱️ ความยาวเสียงทั้งหมด {voice_duration:.2f} วิ -> ตกฉากละ {scene_duration:.2f} วินาที")

        print("🖼️ 3. วาดภาพ 6 ฉาก...")
        for i, sc in enumerate(data['scenes']):
            fetch_image_cartoon(sc.get('prompt', ''), f"i_{i}.jpg", i+1)
            time.sleep(3)

        print("🎬 4. ประกอบวิดีโอ...")
        with open("l.txt", "w", encoding="utf-8") as f:
            for i in range(SCENE_COUNT):
                f.write(f"file 'i_{i}.jpg'\nduration {scene_duration:.2f}\n")
            f.write(f"file 'i_{SCENE_COUNT-1}.jpg'")

        ensure_font_exists()
        drawtext_filters = []
        font_opt = ""
        if os.path.exists("font.ttf") and os.path.getsize("font.ttf") > 40000:
            abs_font_path = os.path.abspath("font.ttf").replace('\\', '/').replace(':', r'\:')
            font_opt = f"fontfile='{abs_font_path}':"
        
        for i in range(SCENE_COUNT):
            start_time = i * scene_duration
            end_time = start_time + (scene_duration * 0.9)  
            
            raw_caption = str(data['scenes'][i].get('caption', '')).replace("'", "").replace(":", "").replace(",", "").strip()
            if not raw_caption: continue
            
            wrapped_caption = wrap_text(raw_caption, max_chars_per_line=18)
            escaped_caption = wrapped_caption.replace('\n', r'\n')
            
            dt = f"drawtext={font_opt}text='{escaped_caption}':fontcolor=white:bordercolor=black:borderw=6:fontsize=150:x=(w-text_w)/2:y=(h-text_h)/2+400:enable='between(t,{start_time:.2f},{end_time:.2f}):text_align=C'"
            drawtext_filters.append(dt)
            
        drawtexts_str = ",".join(drawtext_filters)
        vf_string = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.001,1.3)':d=250:s=1080x1920"
        if drawtexts_str:
            vf_string += f",{drawtexts_str}"

        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "l.txt", "-i", "v.mp3"]
        if os.path.exists("bg.mp3"):
            # เริ่มเพลงที่ 30 วินาที (-ss 30) เพื่อหลบเสียง Intro หรือความเงียบช่วงแรก
            cmd.extend(["-ss", "30", "-i", "bg.mp3", "-filter_complex", "[1:a]volume=1.0[a1];[2:a]volume=0.08[a2];[a1][a2]amix=inputs=2:duration=first[a]", "-map", "0:v", "-map", "[a]"])
        else:
            cmd.extend(["-map", "0:v", "-map", "1:a", "-c:a", "aac"])
        
        cmd.extend(["-vf", vf_string, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "25", "-t", f"{voice_duration:.2f}", "final.mp4"])
        
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube (ตั้ง Private)...")
        creds_data = None
        if "YOUTUBE_CREDENTIALS" in os.environ and os.environ["YOUTUBE_CREDENTIALS"].strip():
            creds_data = json.loads(os.environ["YOUTUBE_CREDENTIALS"])
        
        if creds_data:
            creds = YoutubeCredentials.from_authorized_user_info(creds_data)
            youtube = build("youtube", "v3", credentials=creds)
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "description": f"{data['desc']}\n\n{data['tags']}", "categoryId": "27"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสำเร็จ 100%! ภาพชัด เสียงเป๊ะ เว้นวรรคเป็นมนุษย์!")
        else:
            print("⚠️ สร้างคลิป final.mp4 เสร็จแล้ว (แต่ไม่พบ Token สำหรับอัปโหลด)")

    except Exception as e:
        print(f"\n‼️ ขัดข้อง: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
