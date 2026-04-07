import os, re, json, subprocess, requests, sys, time, random, shutil
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageFont

# --- ⚙️ ตั้งค่าความสมบูรณ์แบบ (6 ฉาก x 10 วินาที = 60 วินาทีเป๊ะ) ---
SCENE_COUNT = 6   
SCENE_DURATION = 10 
VIDEO_PRIVACY = "private"

# 📌 ตัวละครคงที่ระดับหนัง:Photorealistic Middle-aged Thai Male Owner
CHAR_ANCHOR = "A deeply expressive 45-year-old Thai male business owner, detailed skin texture, raw photo, shot on 35mm lens, dynamic portrait, cinematic realism"

def install_and_get_font():
    """ติดตั้งฟอนต์ไทยลงระบบ OS เพื่อให้ซับไตเติลแสดงผลเป๊ะ 100%"""
    font_family = "Sans"
    if os.path.exists("font.ttf"):
        try:
            font = ImageFont.truetype("font.ttf")
            font_family, _ = font.getname()
            print(f"✅ ตรวจพบฟอนต์ไทย: {font_family}")
            
            font_dir = os.path.expanduser("~/.fonts")
            os.makedirs(font_dir, exist_ok=True)
            shutil.copy("font.ttf", os.path.join(font_dir, "font.ttf"))
            
            print("🔄 กำลังติดตั้งฟอนต์ลงระบบ...")
            subprocess.run(["fc-cache", "-f", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"⚠️ เกิดปัญหาในการติดตั้งฟอนต์: {e}")
    else:
        print("‼️ ไม่พบไฟล์ font.ttf (ซับอาจไม่อ่านไทย)")
    return font_family

def fetch_image_storytelling(prompt, filename, scene_num):
    """วาดภาพด้วยเทคนิค Photographic Storytelling (สัมพันธ์บทระดับ Masterpiece)"""
    print(f"   🎥 ฉากที่ {scene_num}: กำลังเนรมิตภาพ Photographic Storytelling...")
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    
    # ⚠️ คีย์เวิร์ดบังคับให้ภาพดูเป็น "คนจริง" และ "หนังโรง" สัมพันธ์บท
    style = "cinematic photorealistic, raw photo, best quality, ultra-detailed, dramatic shadows, documentary atmosphere, 8k resolution"
    url = f"https://image.pollinations.ai/prompt/{clean_p},{CHAR_ANCHOR},{style}?width=1080&height=1920&seed={random.randint(1,999999)}&nologo=true&model=flux"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for attempt in range(5): 
        try:
            r = requests.get(url, headers=headers, timeout=120)
            if r.status_code == 200 and len(r.content) > 20000:
                with open(filename, 'wb') as f: f.write(r.content)
                print(f"      ✅ ฉากที่ {scene_num} ถ่ายทำเสร็จสิ้น!")
                return True
            print(f"      🔄 กำลังโฟกัสภาพใหม่... (รอ 10 วิ)")
            time.sleep(10)
        except: 
            time.sleep(10)
            
    print(f"      ‼️ ใช้ภาพกราฟิกสำรองสำหรับฉากที่ {scene_num}")
    Image.new('RGB', (1080, 1920), color=(15, 15, 20)).save(filename, 'JPEG')
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังคิดบทเล่าเรื่องแบบ 6 ฉาก (ภาพสัมพันธ์บทอย่างลึกซึ้ง)...")
        prompt_sys = (
            "จงสวมบทบาทเป็นนักเล่าเรื่องประสบการณ์จริงมาเล่าบทเรียน ราคาแพง หัวข้อ: 'ข้อผิดพลาดทางการเงินที่ทำให้เกือบหมดตัว' "
            "ภารกิจ: สร้างสคริปต์ 6 ท่อนยาว (ท่อนละ 10 วินาที) ที่เล่าเรื่องสนุก ลึกซึ้ง และจบใน 60 วินาทีพอดี "
            "กฎเหล็ก:\n"
            "1. บทพากย์ (text): ภาษาไทยธรรมชาติ แนวแชร์ประสบการณ์ มีน้ำหนัก น่าเชื่อถือ (ความยาวประมาณ 40-50 คำต่อท่อน)\n"
            "2. คำสั่งวาดรูป (prompt): ภาษาอังกฤษอธิบาย 'เหตุการณ์และอารมณ์' ที่เฉพาะเจาะจงมาก (เช่น นั่งเครียดหน้าคอมที่มีกราฟแดงถล่ม, จับหัวกลางกองบิล, พนักงานในออฟฟิศโดนไล่ออก) ห้ามใช้คำว่า anime\n"
            "3. ซับไตเติล (caption): คำไทยสั้นๆ 1-2 คำ ให้เด้งขึ้นมาทีละตัวตามคำพูดเป๊ะๆ และหายไป\n"
            "4. SEO: เขียน Description ดึงดูดๆ และ Hashtags 5 อัน\n"
            "Output STRICT JSON: {\"title\": \"...\", \"desc\": \"...\", \"tags\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        print("🎙️ 2. สร้างเสียงพากย์ผู้ชาย (คุณนิวัฒน์) แบบนักเล่าเรื่องมีอารมณ์หนักแน่น...")
        full_voice = " . . . ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-2% --voice "th-TH-NiwatNeural" --text "{full_voice}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการสร้างภาพคนจริง (Photographic Storytelling)...")
        for i, sc in enumerate(data['scenes']):
            fetch_image_storytelling(sc['prompt'], f"i_{i}.jpg", i+1)
            time.sleep(2)

        print("🎬 4. ติดตั้งฟอนต์ และ ประกอบวิดีโอ 60 วินาที สไตล์ ProSub...")
        font_family = install_and_get_font()
        
        with open("subs.ass", "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            # ⚠️ ซับสไตล์โปร: สีขาว (&H00FFFFFF) ขอบดำหนา (Outline=18) อ่านง่าย ดูแพง วางสูงขึ้นนิดนึง (MarginV=450)
            f.write(f"Style: ProSub,{font_family},150,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,18,8,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i in range(SCENE_COUNT):
                start, end = i * SCENE_DURATION, (i + 1) * SCENE_DURATION
                f.write(f"Dialogue: 0,0:{start//60:02}:{start%60:02}.00,0:{end//60:02}:{end%60:02}.00,ProSub,,0,0,0,,{data['scenes'][i]['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")

        # 📌 FFmpeg: ประกอบร่างพร้อม Zoompan นุ่มๆ สลับฉากเล่าเรื่องระดับหนัง
        has_bg = os.path.exists("bg.mp3")
        music_input = "-i bg.mp3" if has_bg else ""
        audio_filter = "-filter_complex \"[1:a]volume=1.0[a1];[2:a]volume=0.08[a2];[a1][a2]amix=inputs=2:duration=first[a]\" -map 0:v -map \"[a]\"" if has_bg else "-c:a aac"
        
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 {music_input} "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles=subs.ass,zoompan=z='min(zoom+0.0012,1.5)':d=250:s=1080x1920\" "
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
            print("✨ ภารกิจสำเร็จ! ได้คลิปคนจริง สไตล์หนังโรง พร้อมซับสไตล์โปรเรียบร้อยครับ!")

    except Exception as e:
        print(f"‼️ ขัดข้องที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
