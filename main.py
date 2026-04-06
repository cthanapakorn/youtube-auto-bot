import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

# --- ⚙️ ตั้งค่า (20 ท่อน x 3 วินาที = 60 วินาที) ---
SCENE_COUNT = 20   
SCENE_DURATION = 3 
VIDEO_PRIVACY = "private"

def download_image_parallel(args):
    """ฟังก์ชันวาดภาพประกอบแบบรันขนาน เพื่อความรวดเร็ว"""
    prompt, filename, scene_num = args
    print(f"   🎨 ฉากที่ {scene_num}: กำลังเนรมิตภาพ...")
    
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    # สไตล์อนิเมะพรีเมียม สื่ออารมณ์ชัดเจนตามบท
    style = "high-quality anime style, cinematic lighting, 8k resolution, expressive facial features, masterpiece"
    url = f"https://image.pollinations.ai/prompt/{clean_p},{style}?width=768&height=1344&seed={random.randint(1,999999)}&nologo=true&model=flux"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=60)
            if r.status_code == 200:
                with open(filename, 'wb') as f: f.write(r.content)
                return True
        except: time.sleep(5)
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังร่างบทเล่าเรื่อง + ซับเด้ง + คำอธิบายคลิปที่น่าสนใจ...")
        # 📌 สั่งให้ AI คิดบทพากย์, ซับไตเติล, Description, และ Hashtags
        prompt_sys = (
            "จงสวมบทบาทเป็นผู้เชี่ยวชาญการทำ YouTube Shorts ที่มียอดวิวนับล้าน หัวข้อ: 'นิสัยที่ทำให้คุณจนตลอดชีวิต' "
            "ภารกิจ: สร้างสคริปต์ 20 ท่อน (ท่อนละ 3 วินาที) ที่เน้นการเล่าเรื่องแบบมีอารมณ์ร่วม "
            "กฎเหล็ก:\n"
            "1. บทพากย์ (text): ภาษาไทยธรรมชาติ ใช้ '...' เพื่อหยุดหายใจ และ '!' เพื่อเน้นเสียง\n"
            "2. คำสั่งวาดรูป (prompt): ภาษาอังกฤษที่อธิบายเหตุการณ์ อารมณ์ และสิ่งของที่สื่อถึงบทพูด\n"
            "3. ซับไตเติล (caption): คำไทย 1-2 คำสั้นๆ ให้เด้งขึ้นมาตามเสียงพากย์\n"
            "4. ข้อมูลเสริม: เขียน Description ที่น่าดึงดูด และ Hashtags ที่เกี่ยวข้อง 5-7 อัน\n"
            "Output STRICT JSON: {\"title\": \"...\", \"description\": \"...\", \"hashtags\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        
        print(f"🎬 หัวข้อคลิป: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ผู้ชาย (คุณนิวัฒน์) แบบมีจังหวะหนักเบา...")
        full_voice = " . . ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-3% --voice "th-TH-NiwatNeural" --text "{full_voice}" --write-media "v.mp3"', shell=True, check=True)

        print(f"🖼️ 3. วาดภาพ 20 ฉากแบบขนาน (Parallel 🚀) - ประหยัดเวลา 5-7 นาที...")
        image_tasks = [(s['prompt'], f"i_{i}.jpg", i+1) for i, s in enumerate(data['scenes'])]
        with ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(download_image_parallel, image_tasks))

        print("🎬 4. ประกอบวิดีโอ (ผสมเสียงเพลง + ฝังซับไทยเด้ง + Turbo Preset)...")
        font_name = "font.ttf" if os.path.exists("font.ttf") else "Sans"
        
        # ⚠️ สร้างไฟล์ซับไตเติล .ass แบบ Pop-up (ตัวใหญ่ สีเหลืองนีออน ขอบดำหนา)
        with open("subs.ass", "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write(f"Style: PopUp,{font_name},150,&H0000E6FF,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,18,12,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i in range(20):
                start, end = i * 3, (i + 1) * 3
                f.write(f"Dialogue: 0,0:{start//60:02}:{start%60:02}.00,0:{end//60:02}:{end%60:02}.00,PopUp,,0,0,0,,{data['scenes'][i]['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(20): f.write(f"file 'i_{i}.jpg'\nduration 3\n")
            f.write(f"file 'i_19.jpg'")

        # 📌 FFmpeg Optimized: ผสมเสียงพากย์ + เพลงประกอบ + ฝังซับเด้ง
        has_bg = os.path.exists("bg.mp3")
        audio_cmd = "-filter_complex \"[1:a]volume=1.0[a1];[2:a]volume=0.1[a2];[a1][a2]amix=inputs=2:duration=first[a]\" -map 0:v -map \"[a]\"" if has_bg else "-c:a aac"
        music_input = "-i bg.mp3" if has_bg else ""
        
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 {music_input} "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass=subs.ass:fontsdir=.,zoompan=z='min(zoom+0.0015,1.5)':d=75:s=1080x1920\" "
            f"{audio_cmd} -c:v libx264 -preset superfast -pix_fmt yuv420p -r 25 -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube พร้อมข้อมูล SEO จัดเต็ม...")
        full_description = f"{data['description']}\n\n{data['hashtags']}"
        
        if os.path.exists('token.json'):
            with open('token.json', 'r') as f:
                creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
            youtube = build("youtube", "v3", credentials=creds)
            youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": data['title'], 
                        "description": full_description, 
                        "categoryId": "27",
                        "tags": data['hashtags'].replace("#", "").split()
                    }, 
                    "status": {"privacyStatus": VIDEO_PRIVACY}
                },
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจมหากาพย์สำเร็จ! ทุกรายละเอียดที่คุณต้องการอยู่ในคลิปนี้แล้วครับ")

    except Exception as e:
        print(f"‼️ พังตรงจุดนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
