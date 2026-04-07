import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

# --- ⚙️ ตั้งค่า (20 ท่อน x 3 วินาที = 60 วินาทีเป๊ะ) ---
SCENE_COUNT = 20   
SCENE_DURATION = 3 
VIDEO_PRIVACY = "private"
# ล็อกหน้าตัวละครให้คงที่ตลอดคลิป
CHAR_ANCHOR = "A charismatic 25-year-old Thai male office worker, messy black hair, white shirt, blue tie, hyper-realistic anime style"

def download_image_robust(args):
    """วาดภาพเล่าเรื่องคุณภาพสูง (Flux) เน้นความต่อเนื่องและลองใหม่เมื่อพลาด"""
    prompt, filename, scene_num = args
    print(f"   🎨 ฉากที่ {scene_num}: กำลังเนรมิตภาพประกอบ...")
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    # ใส่รายละเอียดให้ภาพสื่ออารมณ์ชัดเจน (Cinematic)
    style = "cinematic lighting, 8k resolution, detailed expressive face, emotional atmosphere, masterpiece"
    url = f"https://image.pollinations.ai/prompt/{clean_p},{CHAR_ANCHOR},{style}?width=1024&height=1792&seed=12345&nologo=true&model=flux"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    for attempt in range(5): # พยายามสูงสุด 5 ครั้ง
        try:
            r = requests.get(url, headers=headers, timeout=120)
            if r.status_code == 200 and len(r.content) > 10000:
                with open(filename, 'wb') as f: f.write(r.content)
                return True
            time.sleep(15)
        except: time.sleep(15)
    
    # ถ้าวาดไม่ได้จริงๆ สร้างภาพพื้นหลังสีเข้มเพื่อป้องกันวิดีโอพัง
    img = Image.new('RGB', (1080, 1920), color=(20, 20, 40))
    img.save(filename, 'JPEG')
    return True

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังเขียนบทมหากาพย์ 60 วินาทีและข้อมูล SEO...")
        prompt_sys = (
            "จงสวมบทบาทเป็นนักเล่าเรื่อง (Storyteller) การเงินที่เก่งที่สุด หัวข้อ: 'กฎลับ 5 ข้อที่คนรวยไม่เคยบอกคุณ' "
            "ภารกิจ: สร้างสคริปต์ 20 ท่อนสั้นๆ (ท่อนละ 3 วินาที) เนื้อหาต้องลึกซึ้งและสรุปจบใน 60 วินาทีพอดี "
            "กฎเหล็ก:\n"
            "1. บทพากย์ (text): ภาษาไทยแนวเล่าเรื่อง มีจุดดึงดูดและใช้น้ำเสียงหนักเบา '...' เพื่อหยุดหายใจ (ต้องยาว 20-30 คำต่อท่อน)\n"
            "2. คำสั่งวาดรูป (prompt): ภาษาอังกฤษที่อธิบาย 'เหตุการณ์ อารมณ์ และสัญลักษณ์' สลับกับตัวละครเพื่อให้ภาพไม่น่าเบื่อ\n"
            "3. ซับไตเติล (caption): คำไทยสั้นๆ 1-2 คำ เพื่อให้เด้งขึ้นมาทีละตัวตามเสียงพากย์\n"
            "4. SEO: เขียน Description ที่น่าดึงดูด และ Hashtags 5-7 อัน\n"
            "Output STRICT JSON: {\"title\": \"...\", \"desc\": \"...\", \"tags\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        print("🎙️ 2. สร้างเสียงพากย์ผู้ชาย (คุณนิวัฒน์) แบบเน้นอารมณ์เล่าเรื่อง...")
        full_voice = " . . . ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-3% --voice "th-TH-NiwatNeural" --text "{full_voice}" --write-media "v.mp3"', shell=True, check=True)

        print(f"🖼️ 3. วาดภาพ 20 ฉากแบบขนาน (Quality Mode 💎)...")
        tasks = [(s['prompt'], f"i_{i}.jpg", i+1) for i, s in enumerate(data['scenes'])]
        with ThreadPoolExecutor(max_workers=3) as executor:
            list(executor.map(download_image_robust, tasks))

        print("🎬 4. ประกอบวิดีโอ 60 วินาที (แก้ซับไทยถาวรด้วยการ Force Font)...")
        
        # ⚠️ สร้างไฟล์ซับไตเติล .ass โดยใช้ชื่อฟอนต์มาตรฐาน (เราจะบังคับผ่าน FFmpeg)
        with open("subs.ass", "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            # เราใช้ Fontname ว่า 'ThaiFont' แล้วจะไปสั่ง FFmpeg ให้แมพ 'ThaiFont' เข้ากับ 'font.ttf'
            f.write(f"Style: PopUp,ThaiFont,160,&H0000FFFF,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,18,10,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i in range(20):
                start, end = i * 3, (i + 1) * 3
                f.write(f"Dialogue: 0,0:{start//60:02}:{start%60:02}.00,0:{end//60:02}:{end%60:02}.00,PopUp,,0,0,0,,{data['scenes'][i]['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(20): f.write(f"file 'i_{i}.jpg'\nduration 3\n")
            f.write(f"file 'i_19.jpg'")

        # 📌 FFmpeg: ผสมเสียง + ซูม Cinematic + บังคับใช้ฟอนต์ไทยจากไฟล์ตรงๆ
        has_bg = os.path.exists("bg.mp3")
        music_input = "-i bg.mp3" if has_bg else ""
        audio_filter = "-filter_complex \"[1:a]volume=1.0[a1];[2:a]volume=0.08[a2];[a1][a2]amix=inputs=2:duration=first[a]\" -map 0:v -map \"[a]\"" if has_bg else "-c:a aac"
        
        # ⚠️ ไม้ตาย: ใช้ 'subtitles' filter พร้อม 'force_style' เพื่อชี้เป้าไปที่ไฟล์ font.ttf โดยตรง
        # fontsdir=. จะบอกให้มองหาฟอนต์ในโฟลเดอร์ปัจจุบัน
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 {music_input} "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles=subs.ass:fontsdir=.:force_style='Fontname=font',zoompan=z='min(zoom+0.0015,1.5)':d=75:s=1080x1920\" "
            f"{audio_filter} -c:v libx264 -crf 18 -pix_fmt yuv420p -r 25 -t 60 final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube พร้อมข้อมูล SEO...")
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
            print("✨ ภารกิจมหากาพย์สำเร็จ! วิดีโอ 60 วินาที พร้อมซับไทยตัวพ่อมาแล้ว!")

    except Exception as e:
        print(f"‼️ พังตรงนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
