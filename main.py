import os, re, json, subprocess, requests, sys, time, random, shutil, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# --- 🛠️ แก้ปัญหา Windows Terminal อ่านภาษาไทยไม่ได้ (UnicodeEncodeError) ---
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# --- ⚙️ ตั้งค่าความยาว (6 ฉาก x 10 วินาที = 60 วินาทีพอดี) ---
SCENE_COUNT = 6   
SCENE_DURATION = 10 
VIDEO_PRIVACY = "private"

# 📌 อัปเดตตัวละครคงที่: ล็อกสเปกสัดส่วนร่างกาย ตา และมือให้เป๊ะที่สุด
CHAR_ANCHOR = "An expressive 29-year-old Thai male professional, neat modern haircut, business casual attire, highly detailed anime style, highly detailed expressive face, perfectly drawn eyes, anatomically correct hands, exactly 5 fingers per hand, flawless human anatomy, vibrant colors, modern webtoon style, masterpiece illustration"

def install_font_simple():
    """ติดตั้งฟอนต์แบบเรียบง่าย ไม่ต้องใช้ PIL ให้วุ่นวาย"""
    if os.path.exists("font.ttf"):
        try:
            print(f"✅ ตรวจพบไฟล์ font.ttf กำลังเตรียมใช้งาน...")
            font_dir = os.path.expanduser("~/.fonts")
            os.makedirs(font_dir, exist_ok=True)
            shutil.copy("font.ttf", os.path.join(font_dir, "font.ttf"))
            
            # บังคับอัปเดตฟอนต์ (ข้ามไปถ้าเป็น Windows)
            try:
                subprocess.run(["fc-cache", "-f", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                pass 
        except Exception as e:
            print(f"⚠️ มีปัญหาการคัดลอกฟอนต์: {e}")
    else:
        print("‼️ ไม่พบไฟล์ font.ttf (ซับอาจเป็นต่างดาว)")
    
    # ส่งคืนชื่ออะไรก็ได้ เพราะเดี๋ยวเราบังคับ force ในไฟล์ .ass เอา
    return "MyCustomFont" 

def fetch_image_cartoon(prompt, filename, scene_num):
    """วาดภาพแนวกาตูนคุณภาพสูง พร้อมบังคับรายละเอียดมือและตา"""
    print(f"   🎨 ฉากที่ {scene_num}: กำลังวาดภาพสไตล์การ์ตูนที่ลงรายละเอียดชัดเจน...")
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    
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
        except: time.sleep(10)
            
    print(f"      ‼️ ใช้ภาพกราฟิกสำรองสำหรับฉากที่ {scene_num}")
    Image.new('RGB', (1080, 1920), color=(15, 15, 15)).save(filename, 'JPEG')
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังคิดหัวข้อการเงินระดับไวรัล และเขียนบท...")
        
        data = None
        for attempt in range(5): # ให้โอกาสแก้ตัวสูงสุด 5 ครั้ง
            print(f"🧠 [Attempt {attempt+1}] AI กำลังสุ่มหัวข้อและร่างบท...")
            prompt_sys = (
                "คุณคือผู้เชี่ยวชาญด้านการสร้างวิดีโอ YouTube Shorts ระดับไวรัล และการเล่าเรื่อง\n"
                "เป้าหมาย: สร้างคอนเทนต์วิดีโอความยาว 60 วินาที ที่ดึงดูดคนดูตั้งแต่ 3 วินาทีแรก\n"
                "หัวข้อ: 'ให้สุ่มคิดหัวข้อใหม่เกี่ยวกับการเงิน การลงทุน การสร้างรายได้ หรืออิสรภาพทางการเงิน'\n"
                "**ข้อควรระวัง: ให้คิดประเมินหัวข้อก่อน ถ้าหัวข้อดูธรรมดาหรือน่าเบื่อไป ให้คิดใหม่จนกว่าจะได้หัวข้อระดับไวรัลที่กระแทกใจคนดูที่สุด!**\n\n"
                "โครงสร้างสคริปต์ 6 ฉาก (ฉากละ 10 วินาที):\n"
                "- ฉาก 1: Hook (ประโยคสั้น กระแทกใจ ชวนสงสัย)\n"
                "- ฉาก 2: Setup (ปูเรื่อง)\n"
                "- ฉาก 3: ปัญหาเริ่มหนัก หรือ ความลับถูกเปิดเผย\n"
                "- ฉาก 4: วิกฤต หรือ จุดพีคของเนื้อหา\n"
                "- ฉาก 5: จุดเปลี่ยน หรือ วิธีแก้ปัญหา\n"
                "- ฉาก 6: บทเรียน + ทิ้งท้าย (มีข้อคิดชัดเจน)\n\n"
                "กฎเหล็กแต่ละฉาก:\n"
                "1. บทพากย์ (text): ภาษาไทย โทนเสียงจริงจัง มีอารมณ์ (ความยาว 40-50 คำต่อฉาก เพื่อให้พูดจบใน 10 วินาที)\n"
                "2. คำสั่งวาดรูป (prompt): ภาษาอังกฤษ บรรยายเหตุการณ์ สภาพแวดล้อม และอารมณ์ให้ **เห็นภาพชัดเจนที่สุด** หากมีฉากที่เห็นมือ ให้เน้น 'anatomically correct hands holding [object]'. สลับภาพชายวัย 29 ปี กับภาพเหตุการณ์ให้เข้ากับบท\n"
                "3. ซับไตเติล (caption): คำไทยสั้นๆ 1-2 คำ กระแทกอารมณ์\n\n"
                "ข้อมูลเสริม (SEO):\n"
                "1. title: น่าสนใจ กระตุ้นให้คลิก\n"
                "2. desc: สั้น กระชับ มีคีย์เวิร์ด พร้อมคำแนะนำเพลง background\n"
                "3. tags: แฮชแท็ก 5 อัน\n"
                "Output STRICT JSON FORMAT ONLY (Do NOT wrap in
