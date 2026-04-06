import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

# --- ⚙️ ตั้งค่า (30 ท่อน x 2 วินาที = 60 วินาที) ---
# การซอยให้สั้นลงเหลือ 2-3 วินาที จะทำให้ซับเด้งตามคำพูดได้ "เป๊ะ" ที่สุด
SCENE_COUNT = 20   
SCENE_DURATION = 3 
VIDEO_PRIVACY = "private"

def download_image_task(args):
    """วาดภาพเล่าเรื่องแบบขนาน (Flux Engine)"""
    prompt, filename, scene_num = args
    print(f"   🎨 ฉากที่ {scene_num}: วาดภาพประกอบ...")
    
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    style = "high-quality anime style, cinematic storytelling, emotional atmosphere, 8k resolution, masterpiece"
    url = f"https://image.pollinations.ai/prompt/{clean_p},{style}?width=768&height=1344&seed={random.randint(1,999999)}&nologo=true&model=flux"
    
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=60)
        if r.status_code == 200:
            with open(filename, 'wb') as f: f.write(r.content)
            return True
    except: pass
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังเนรมิตบทเล่าเรื่อง + ซับเด้ง + SEO...")
        prompt_sys = (
            "จงสวมบทบาทเป็นนักเล่าเรื่องการเงิน (Storyteller) ที่เก่งที่สุด หัวข้อ: 'ความจริงที่โหดร้ายของเงินเฟ้อ' "
            "ภารกิจ: สร้างสคริปต์ 20 ท่อน (ท่อนละ 3 วินาที) "
            "กฎเหล็ก:\n"
            "1. บทพากย์ (text): ภาษาไทยแนวเล่าเรื่อง มีจุดดึงดูด ใช้ '...' เพื่อหยุดหายใจ และ '!' เพื่อเน้นอารมณ์ ห้ามมีคำบรรยายฉากปน\n"
            "2. คำสั่งวาดรูป (prompt): ภาษาอังกฤษที่อธิบาย 'เหตุการณ์' หรือ 'สัญลักษณ์' (เช่น เงินละลาย, ตึกสูง, คนเครียด, ตลาดที่วุ่นวาย) สลับกันไป\n"
            "3. ซับไตเติล (caption): คำไทย 1-2 คำสั้นๆ ให้เด้งขึ้นมาทีละตัวตามเสียงพากย์\n"
            "4. SEO: เขียน Description ที่น่าสนใจ และ Hashtags ที่เกี่ยวข้อง 5 อัน\n"
            "Output STRICT JSON: {\"title\": \"...\", \"desc\": \"...\", \"tags\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        
        print(f"🎬 หัวข้อ: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์คุณนิวัฒน์ (Niwat)...")
        # ใช้คุณนิวัฒน์ที่มีพลังในการเล่าเรื่องสูง
        full_voice = " . . ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-2% --voice "th-TH-NiwatNeural" --text "{full_voice}" --write-media "v.mp3"', shell=True, check=True)

        print(f"🖼️ 3. วาดภาพ 20 ฉากแบบขนาน (Turbo Mode 🚀)...")
        tasks = [(s['prompt'], f"i_{i}.jpg", i+1) for i, s in enumerate(data['scenes'])]
        with ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(download_image_task, tasks))

        print("🎬 4. แก้ไขซับไตเติลและประกอบ Video (ผสมเสียงเพลงเบาๆ)...")
        
        # ตรวจสอบไฟล์สำคัญ ป้องกัน Error 254
        font_exists = os.path.exists("font.ttf")
        bg_exists = os.path.exists("bg.mp3")
        font_name = "font.ttf" if font_exists else "Arial"

        # สร้างไฟล์ซับไตเติล .ass แบบ Pop-up (ตัวใหญ่มาก สีเหลือง ขอบดำหนา)
        with open("subs.ass", "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write(f"Style: PopUp,{font_name},160,&H0000FFFF,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,18,10,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i in range(20):
                start, end = i * 3, (i + 1) * 3
                f.write(f"Dialogue: 0,0:{start//60:02}:{start%60:02}.00,0:{end//60:02}:{end%60:02}.00,PopUp,,0,0,0,,{data['scenes'][i]['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(20): f.write(f"file 'i_{i}.jpg'\nduration 3\n")
            f.write(f"file 'i_19.jpg'")

        # 📌 FFmpeg: ผสมเสียง (เสียงพากย์ 100% + เพลงประกอบ 10%)
        music_input = "-i bg.mp3" if bg_exists else ""
        audio_filter = "-filter_complex \"[1:a]volume=1.0[a1];[2:a]volume=0.1[a2];[a1][a2]amix=inputs=2:duration=first[a]\" -map 0:v -map \"[a]\"" if bg_exists else "-c:a aac"
        
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 {music_input} "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass=subs.ass:fontsdir=.,zoompan=z='min(zoom+0.0015,1.5)':d=75:s=1080x1920\" "
            f"{audio_filter} -c:v libx264 -preset superfast -pix_fmt yuv420p -r 25 -shortest final.mp4"
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
                        "categoryId": "27",
                        "tags": data['tags'].replace("#","").split()
                    }, 
                    "status": {"privacyStatus": VIDEO_PRIVACY}
                },
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจมหากาพย์สำเร็จ! ทุกอย่างเป๊ะตามที่สั่งครับ")

    except Exception as e:
        print(f"‼️ พังตรงจุดนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
