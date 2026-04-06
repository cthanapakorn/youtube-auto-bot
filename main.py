import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

# --- ⚙️ ตั้งค่าล็อกเวลา (20 ท่อน x 3 วินาที = 60 วินาทีพอดี) ---
SCENE_COUNT = 20   
SCENE_DURATION = 3 
VIDEO_PRIVACY = "private"
CHAR_ANCHOR = "A charismatic 25-year-old Thai male office worker, messy black hair, white shirt, blue tie, high-quality anime style"

def download_image_robust(args):
    """วาดภาพเล่าเรื่องคุณภาพสูงและลองใหม่ถ้าพลาด"""
    prompt, filename, scene_num = args
    print(f"   🎨 ฉากที่ {scene_num}: กำลังวาดภาพประกอบ...")
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    style = "cinematic lighting, 8k resolution, detailed face, emotional atmosphere, masterpiece"
    url = f"https://image.pollinations.ai/prompt/{clean_p},{CHAR_ANCHOR},{style}?width=1024&height=1792&seed=8888&nologo=true&model=flux"
    
    for attempt in range(5):
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=120)
            if r.status_code == 200:
                with open(filename, 'wb') as f: f.write(r.content)
                return True
            time.sleep(15)
        except: time.sleep(15)
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังร่างบทสรุปการเงิน 60 วินาที (ไม่ขาดตอน)...")
        # สั่งให้ AI คิดเนื้อหาที่จบใน 60 วินาที แบ่งเป็น 20 ท่อน
        prompt_sys = (
            "จงเขียนบทวิดีโอ Shorts ยาว 60 วินาทีเต็ม หัวข้อ: 'สรุป 5 นิสัยอันตรายที่ทำให้เก็บเงินไม่ได้' "
            "ภารกิจ: สร้างสคริปต์ 20 ท่อน (ท่อนละ 3 วินาที) เนื้อหาต้องต่อเนื่องตั้งแต่ต้นจนจบ "
            "กฎเหล็ก:\n"
            "1. บทพากย์ (text): ภาษาไทยธรรมชาติ แบ่งเป็น 20 ท่อน ท่อนละประมาณ 15-20 คำ เพื่อให้พูดจบใน 3 วินาทีพอดี\n"
            "2. คำสั่งวาดรูป (prompt): ภาษาอังกฤษที่อธิบายเหตุการณ์ในท่อนนั้นๆ สลับภาพคนและสัญลักษณ์\n"
            "3. ซับไตเติล (caption): คำไทยสั้นๆ 1-2 คำ เพื่อให้เด้งขึ้นมาทีละตัว\n"
            "ส่งผลลัพธ์เป็น JSON: {\"title\": \"...\", \"desc\": \"...\", \"tags\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())

        print("🎙️ 2. สร้างเสียงพากย์คุณนิวัฒน์ (Niwat)...")
        full_voice = " . . ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-2% --voice "th-TH-NiwatNeural" --text "{full_voice}" --write-media "v.mp3"', shell=True, check=True)

        print(f"🖼️ 3. วาดภาพประกอบ 20 ฉาก (Quality Mode)...")
        tasks = [(s['prompt'], f"i_{i}.jpg", i+1) for i, s in enumerate(data['scenes'])]
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(download_image_robust, tasks))

        print("🎬 4. ประกอบวิดีโอ 60 วินาที (ล็อกเวลา + ซับไทยเด้ง)...")
        font_name = "font.ttf" if os.path.exists("font.ttf") else "Sans"
        
        with open("subs.ass", "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write(f"Style: PopUp,{font_name},160,&H0000FFFF,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,18,12,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i in range(20):
                start, end = i * 3, (i + 1) * 3
                f.write(f"Dialogue: 0,0:{start//60:02}:{start%60:02}.00,0:{end//60:02}:{end%60:02}.00,PopUp,,0,0,0,,{data['scenes'][i]['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(20): f.write(f"file 'i_{i}.jpg'\nduration 3\n")
            f.write(f"file 'i_19.jpg'") # ปิดท้าย

        # 📌 FFmpeg: ล็อกเวลาที่ 60 วินาที (-t 60) และประกอบเสียง
        has_bg = os.path.exists("bg.mp3")
        music_input = "-i bg.mp3" if has_bg else ""
        audio_filter = "-filter_complex \"[1:a]volume=1.0[a1];[2:a]volume=0.1[a2];[a1][a2]amix=inputs=2:duration=first[a]\" -map 0:v -map \"[a]\"" if has_bg else "-c:a aac"
        
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 {music_input} "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass=subs.ass:fontsdir=.,zoompan=z='min(zoom+0.0015,1.5)':d=75:s=1080x1920\" "
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
                body={"snippet": {"title": data['title'], "description": f"{data['desc']}\n\n{data['tags']}", "categoryId": "27"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ สำเร็จ! วิดีโอสรุป 60 วินาทีสมบูรณ์แบบพร้อมออนไลน์!")

    except Exception as e:
        print(f"‼️ พังตรงนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
