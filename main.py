import sys, subprocess, os

# --- 🛠️ 1. ระบบซ่อมแซมตัวเอง: ติดตั้ง Library ที่หายไปอัตโนมัติ ---
# ปิดตายปัญหา ModuleNotFoundError (เช่น ไม่มี edge-tts)
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
            print(f"📦 ระบบกำลังติดตั้ง '{pip_name}' ที่ขาดหายไปอัตโนมัติ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "--quiet"])

auto_install_requirements()

# --- 🛠️ 2. Import Libraries ตามปกติ ---
import re, json, time, random, shutil, traceback, asyncio, urllib.request
import edge_tts
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# --- 🛠️ 3. แก้ปัญหา Windows Terminal อ่านภาษาไทยไม่ได้ ---
if sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass
if sys.stderr.encoding.lower() != 'utf-8':
    try: sys.stderr.reconfigure(encoding='utf-8')
    except: pass

# --- ⚙️ ตั้งค่าความยาว (6 ฉาก x 10 วินาที = 60 วินาทีพอดี) ---
SCENE_COUNT = 6   
SCENE_DURATION = 10 
VIDEO_PRIVACY = "private"
CHAR_ANCHOR = "An expressive 29-year-old Thai male professional, neat modern haircut, business casual attire, highly detailed anime style, highly detailed expressive face, perfectly drawn eyes, anatomically correct hands, exactly 5 fingers per hand, flawless human anatomy, vibrant colors, modern webtoon style, masterpiece illustration"

def ensure_font_exists():
    """✅ ดึงฟอนต์ Kanit แบบฝังแกนกลาง ปิดตายปัญหา FFmpeg หาฟอนต์ไม่เจอ"""
    font_filename = "font.ttf"
    if not os.path.exists(font_filename) or os.path.getsize(font_filename) < 10000:
        print("⏳ กำลังดาวน์โหลดฟอนต์ไทย (Kanit-Bold) เพื่อใช้ฝังซับไตเติล...")
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/kanit/Kanit-Bold.ttf"
            urllib.request.urlretrieve(url, font_filename)
            print("✅ ดาวน์โหลดฟอนต์สำเร็จสมบูรณ์!")
        except Exception as e:
            print(f"⚠️ ดาวน์โหลดฟอนต์ล้มเหลว: {e}")

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
                with open(filename, 'wb') as f: f.write(r.content)
                print(f"      ✅ ฉากที่ {scene_num} วาดเสร็จสิ้น!")
                return True
            time.sleep(10)
        except Exception as e:
            print(f"      🔄 กำลังลองใหม่... ({e})")
            time.sleep(10)
            
    print(f"      ‼️ ใช้ภาพกราฟิกสำรองสำหรับฉากที่ {scene_num}")
    Image.new('RGB', (1080, 1920), color=(15, 15, 15)).save(filename, 'JPEG')
    return True

async def generate_voice(text, output_file):
    """สร้างเสียงพากย์ด้วย API ตรงๆ ป้องกัน Error คำสั่งหายบน Windows"""
    communicate = edge_tts.Communicate(text, "th-TH-NiwatNeural", rate="-3%")
    await communicate.save(output_file)

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("ไม่พบ GEMINI_API_KEY ในระบบ กรุณาตรวจสอบการตั้งค่า Secret บน GitHub หรือ Environment Variable")
            
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
            except Exception as e:
                continue

            score = temp_data.get('viral_score', 0)
            print(f"   📊 Viral Score ที่ได้: {score}/10")
            
            if score >= 8 and len(temp_data.get('scenes', [])) == SCENE_COUNT:
                data = temp_data
                print("   ✅ คุณภาพผ่านเกณฑ์! นำไปผลิตต่อได้")
                break

        if not data:
            raise ValueError("สร้างบทไม่สำเร็จใน 5 รอบ AI อาจจะติดขัดการตอบกลับ JSON")

        print(f"📌 หัวข้อที่ได้: {data.get('title', 'Viral Finance Shorts')}")
        
        print("🎙️ 2. สร้างเสียงพากย์คุณนิวัฒน์ ด้วย Python Native API...")
        full_voice = " . . . ".join([str(s.get('text', '')) for s in data['scenes']])
        
        # รันสร้างเสียงอย่างปลอดภัย
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

        # การันตีโหลดฟอนต์ 100%
        ensure_font_exists()

        # ⚠️ จัดรูปแบบ Path ฟอนต์ระดับพระกาฬให้ FFmpeg บน Windows ไม่งอแง
        drawtext_filters = []
        font_opt = ""
        if os.path.exists("font.ttf"):
            # แปลง Path ให้เป็น Forward Slash ทั้งหมด (FFmpeg ชอบแบบนี้)
            abs_font_path = os.path.abspath("font.ttf").replace('\\', '/')
            font_opt = f"fontfile='{abs_font_path}':"
        
        for i in range(SCENE_COUNT):
            start_time = i * SCENE_DURATION
            end_time = start_time + 3  
            # ล้างอักขระขยะที่อาจทำให้ FFmpeg รวน
            caption = str(data['scenes'][i].get('caption', '')).replace("'", "").replace(":", "").replace(",", "").replace("\\", "").strip()
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
        if "YOUTUBE_CREDENTIALS" in os.environ and os.environ["YOUTUBE_CREDENTIALS"].strip():
            try:
                creds_data = json.loads(os.environ["YOUTUBE_CREDENTIALS"])
            except Exception as e:
                print(f"   ⚠️ อ่าน YOUTUBE_CREDENTIALS ไม่สำเร็จ: {e}")
        elif os.path.exists('token.json'):
            try:
                with open('token.json', 'r', encoding='utf-8') as f:
                    creds_data = json.load(f)
            except Exception as e:
                print(f"   ⚠️ อ่านไฟล์ token.json ไม่สำเร็จ: {e}")

        if creds_data:
            try:
                creds = YoutubeCredentials.from_authorized_user_info(creds_data)
                youtube = build("youtube", "v3", credentials=creds)
                youtube.videos().insert(
                    part="snippet,status",
                    body={
                        "snippet": {"title": data['title'], "description": f"{data['desc']}\n\n{data['tags']}", "categoryId": "27"}, 
                        "status": {"privacyStatus": VIDEO_PRIVACY}
                    },
                    media_body=MediaFileUpload("final.mp4")
                ).execute()
                print("✨ ภารกิจสำเร็จ 100%! อัปโหลดขึ้น YouTube เรียบร้อยแล้ว!")
            except Exception as e:
                print(f"‼️ อัปโหลด YouTube พัง: {e}")
                print("✨ แต่วิดีโอ final.mp4 สร้างเสร็จสมบูรณ์แล้ว สามารถนำไปใช้อัปโหลดเองได้!")
        else:
            print("⚠️ ไม่พบ Token สำหรับ YouTube -> สร้างคลิป final.mp4 เสร็จสมบูรณ์แล้ว!")

    except subprocess.CalledProcessError as e:
        print("\n" + "="*50)
        print("‼️ ขัดข้องที่โปรแกรมภายนอก (FFmpeg)")
        print(f"💥 คำสั่งที่พัง: {' '.join(e.cmd)}")
        print(f"🔍 [รายละเอียด Error จากระบบ]:\n{e.stderr}")
        print("="*50 + "\n")
        sys.exit(1)
    except Exception as e:
        print("\n" + "="*50)
        print(f"‼️ ขัดข้องที่ระบบ Python: {str(e)}")
        print("🔍 [ตรวจสอบจุดที่พังแบบเจาะลึกด้านล่าง]:")
        traceback.print_exc()
        print("="*50 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
