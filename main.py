import os, re, json, subprocess, requests, sys, time, random, shutil
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageFont

# --- ⚙️ ตั้งค่าความสมบูรณ์แบบ (20 ฉาก x 3 วินาที = 60 วินาทีเต็ม) ---
SCENE_COUNT = 20   
SCENE_DURATION = 3 
VIDEO_PRIVACY = "private"
CHAR_ANCHOR = "A charismatic 25-year-old Thai male office worker, messy black hair, white shirt, blue tie, high-quality anime style"

def install_and_get_font():
    """สุดยอดวิธีแก้ฟอนต์เพี้ยน: ติดตั้ง font.ttf ลงระบบ OS ของ GitHub โดยตรง"""
    font_family = "Sans"
    if os.path.exists("font.ttf"):
        try:
            # 1. ดึงชื่อจริงของฟอนต์
            font = ImageFont.truetype("font.ttf")
            font_family, _ = font.getname()
            print(f"✅ ตรวจพบฟอนต์ไทย: {font_family}")
            
            # 2. คัดลอกไปติดตั้งในระบบ Linux
            font_dir = os.path.expanduser("~/.fonts")
            os.makedirs(font_dir, exist_ok=True)
            shutil.copy("font.ttf", os.path.join(font_dir, "font.ttf"))
            
            # 3. บังคับให้ระบบอัปเดตแคชฟอนต์
            print("🔄 กำลังติดตั้งฟอนต์ลงระบบของ GitHub...")
            subprocess.run(["fc-cache", "-f", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"⚠️ เกิดปัญหาในการติดตั้งฟอนต์: {e}")
    else:
        print("‼️ ไม่พบไฟล์ font.ttf ซับไตเติลอาจเป็นภาษาต่างดาว")
    return font_family

def fetch_image_masterpiece(prompt, filename, scene_num):
    """วาดภาพคุณภาพสูงสุด (1080x1920) แบบประณีต ไม่รีบร้อน"""
    print(f"   🎨 ฉากที่ {scene_num}: กำลังวาดภาพระดับ Masterpiece...")
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    
    # บังคับคีย์เวิร์ดเพิ่มคุณภาพแบบจัดเต็ม
    style = "masterpiece, best quality, ultra-detailed, 8k resolution, cinematic lighting, dramatic atmosphere"
    url = f"https://image.pollinations.ai/prompt/{clean_p},{CHAR_ANCHOR},{style}?width=1080&height=1920&seed={random.randint(1,999999)}&nologo=true&model=flux"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for attempt in range(5): # พยายามสูงสุด 5 ครั้ง
        try:
            r = requests.get(url, headers=headers, timeout=120)
            if r.status_code == 200 and len(r.content) > 20000: # เช็คว่าภาพไม่พัง (ขนาดไฟล์ต้องเกิน 20KB)
                with open(filename, 'wb') as f: f.write(r.content)
                print(f"      ✅ ฉากที่ {scene_num} เสร็จสมบูรณ์!")
                return True
            print(f"      🔄 Server คืนภาพคุณภาพต่ำ... รอ 10 วินาทีเพื่อลองใหม่")
            time.sleep(10)
        except: 
            time.sleep(10)
            
    # ภาพสำรองกันวิดีโอพัง
    print(f"      ‼️ ใช้ภาพสำรองสำหรับฉากที่ {scene_num}")
    Image.new('RGB', (1080, 1920), color=(20, 20, 30)).save(filename, 'JPEG')
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังคิดบทมหากาพย์การเงิน (60 วินาทีเป๊ะ)...")
        prompt_sys = (
            "จงสวมบทบาทเป็นนักเล่าเรื่อง (Storyteller) ระดับโลก หัวข้อ: 'ทำไมคนขยันถึงไม่รวย? ความลับที่คน 1% ปกปิดไว้' "
            "ภารกิจ: สร้างสคริปต์ 20 ท่อน (ท่อนละ 3 วินาที) ที่เล่าเรื่องสนุก ลึกซึ้ง และจบใน 60 วินาทีพอดี "
            "กฎเหล็ก:\n"
            "1. บทพากย์ (text): ภาษาไทยธรรมชาติ มี Hook, Drama, Solution ใช้ '...' เพื่อหยุดพักเสียง (ความยาวประมาณ 18-22 คำต่อท่อนเพื่อให้พอดี 3 วินาที)\n"
            "2. คำสั่งวาดรูป (prompt): ภาษาอังกฤษอธิบาย 'เหตุการณ์และอารมณ์' (เช่น คนจมกองหนี้, นาฬิกาทราย, แสงสว่างปลายอุโมงค์) สลับภาพให้หลากหลาย\n"
            "3. ซับไตเติล (caption): คำไทยสั้นๆ 1-2 คำ เพื่อให้เด้งขึ้นมาตรงจังหวะพอดี\n"
            "4. SEO: เขียน Description ดึงดูดๆ และ Hashtags 5 อัน\n"
            "Output STRICT JSON: {\"title\": \"...\", \"desc\": \"...\", \"tags\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        print("🎙️ 2. สร้างเสียงพากย์ผู้ชาย (คุณนิวัฒน์) แบบนักเล่าเรื่อง...")
        full_voice = " . . . ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-2% --voice "th-TH-NiwatNeural" --text "{full_voice}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการวาดภาพ 20 ฉาก (Quality Priority - ประณีตทีละภาพ)...")
        # ยกเลิกรันขนาน เปลี่ยนมาวาดเรียงคิวทีละภาพ เพื่อให้ได้ภาพคุณภาพสูงสุดจาก Server
        for i, sc in enumerate(data['scenes']):
            fetch_image_masterpiece(sc['prompt'], f"i_{i}.jpg", i+1)
            time.sleep(2) # พักหายใจ 2 วินาทีระหว่างรูป ไม่ให้โดนแบน

        print("🎬 4. ติดตั้งฟอนต์ และ ประกอบวิดีโอ 60 วินาที...")
        # ระบบจะติดตั้งฟอนต์ลงเครื่องและส่งชื่อที่ถูกต้องกลับมา
        font_family = install_and_get_font()
        
        with open("subs.ass", "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            # ใส่ชื่อฟอนต์ที่ติดตั้งแล้ว
            f.write(f"Style: PopUp,{font_family},160,&H0000E6FF,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,18,12,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i in range(20):
                start, end = i * 3, (i + 1) * 3
                f.write(f"Dialogue: 0,0:{start//60:02}:{start%60:02}.00,0:{end//60:02}:{end%60:02}.00,PopUp,,0,0,0,,{data['scenes'][i]['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(20): f.write(f"file 'i_{i}.jpg'\nduration 3\n")
            f.write(f"file 'i_19.jpg'")

        # 📌 FFmpeg: ผสมเสียง (Voice 100% + BGM 8%) + ซูมนุ่มๆ + บังคับเวลา 60s
        has_bg = os.path.exists("bg.mp3")
        music_input = "-i bg.mp3" if has_bg else ""
        audio_filter = "-filter_complex \"[1:a]volume=1.0[a1];[2:a]volume=0.08[a2];[a1][a2]amix=inputs=2:duration=first[a]\" -map 0:v -map \"[a]\"" if has_bg else "-c:a aac"
        
        # ลบคำสั่ง fontsdir=. ออก เพราะเราติดตั้งฟอนต์ลงระบบไปแล้ว FFmpeg จะหาเจออัตโนมัติ
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 {music_input} "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles=subs.ass,zoompan=z='min(zoom+0.0015,1.5)':d=75:s=1080x1920\" "
            f"{audio_filter} -c:v libx264 -crf 18 -pix_fmt yuv420p -r 25 -t 60 final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube พร้อม SEO...")
        if os.path.exists('token.json'):
            with open('token.json', 'r') as f:
                creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
            youtube = build("youtube", "v3", credentials=creds)
            youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": data['title'], 
                        "description": f"{data['desc']}\n\n{data['tags']}", 
                        "categoryId": "27"
                    }, 
                    "status": {"privacyStatus": VIDEO_PRIVACY}
                },
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจสมบูรณ์แบบ! คลิป 60 วิ, ภาพชัด, ซับไทยเป๊ะ, เสียงมีอารมณ์!")

    except Exception as e:
        print(f"‼️ ขัดข้องที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
