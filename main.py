import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageFont # เพิ่ม ImageFont เพื่อดึงชื่อฟอนต์

# --- ⚙️ ตั้งค่า (20 ท่อน x 3 วินาที = 60 วินาที) ---
SCENE_COUNT = 20   
SCENE_DURATION = 3 
VIDEO_PRIVACY = "private"

def get_font_family_name(font_path):
    """ดึงชื่อ Font Family จากไฟล์ .ttf เพื่อให้ซับไตเติลอ่านออก"""
    try:
        font = ImageFont.truetype(font_path)
        family, style = font.getname()
        print(f"   🎯 ตรวจพบฟอนต์: {family}")
        return family
    except:
        return "Sans"

def download_image_pro(args):
    """วาดภาพเล่าเรื่องคุณภาพสูง (Flux Engine)"""
    prompt, filename, scene_num = args
    print(f"   🎨 ฉากที่ {scene_num}: วาดภาพประกอบ...")
    
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    style = "cinematic anime style, high contrast, dramatic lighting, 8k resolution, detailed scenery, masterpiece"
    url = f"https://image.pollinations.ai/prompt/{clean_p},{style}?width=1024&height=1792&seed={random.randint(1,999999)}&nologo=true&model=flux"
    
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=120)
        if r.status_code == 200:
            with open(filename, 'wb') as f: f.write(r.content)
            return True
    except: pass
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. Gemini กำลังร่างสคริปต์แนว Storytelling ที่น่าดึงดูด...")
        # สั่งให้ AI เขียนบทที่ยาวและเข้มข้นเพื่อให้วิดีโอไม่สั้นเกินไป
        prompt_sys = (
            "จงสวมบทบาทเป็นนักเล่าเรื่อง (Storyteller) การเงินระดับโลก หัวข้อ: 'ทำไมคุณถึงยังไม่รวย? ความลับที่คน 1% ไม่บอกคุณ' "
            "ภารกิจ: สร้างสคริปต์ 20 ท่อนสั้นๆ (ท่อนละ 3 วินาที) ที่เล่าเรื่องแบบมี Hook, Drama และจุดหักมุม "
            "กฎเหล็ก:\n"
            "1. บทพากย์ (text): ภาษาไทยแนวเล่าเรื่องที่เข้มข้น ใช้ '...' เพื่อหยุดจังหวะ และ '!' เพื่อเน้นอารมณ์ ห้ามมีโค้ดฉากปน\n"
            "2. คำสั่งวาดรูป (prompt): ภาษาอังกฤษที่อธิบาย 'เหตุการณ์' (เช่น ตลาดหุ้นถล่ม, คนเดินกลางพายุเงิน, ประตูสู่ความมั่งคั่ง) สลับกับตัวละครบ้าง\n"
            "3. ซับไตเติล (caption): คำไทย 1-2 คำสั้นๆ เพื่อให้เด้งขึ้นมาทีละตัวตามเสียงพากย์\n"
            "Output STRICT JSON: {\"title\": \"...\", \"desc\": \"...\", \"tags\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        
        print(f"🎬 หัวข้อ: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ผู้ชาย (คุณนิวัฒน์)...")
        full_voice = " . . . ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-2% --voice "th-TH-NiwatNeural" --text "{full_voice}" --write-media "v.mp3"', shell=True, check=True)

        print(f"🖼️ 3. วาดภาพ 20 ฉากแบบขนาน (Quality Mode 💎)...")
        tasks = [(s['prompt'], f"i_{i}.jpg", i+1) for i, s in enumerate(data['scenes'])]
        with ThreadPoolExecutor(max_workers=3) as executor:
            list(executor.map(download_image_pro, tasks))

        print("🎬 4. แก้ไขซับไทยและประกอบ Video (แบบไม่รีบ แต่คุณภาพเน้นๆ)...")
        
        # ⚠️ หัวใจสำคัญ: ดึงชื่อจริงของฟอนต์มาใช้
        actual_font_name = get_font_family_name("font.ttf") if os.path.exists("font.ttf") else "Sans"

        # สร้างไฟล์ซับไตเติล .ass (ตัวใหญ่ สีเหลืองนีออน ขอบดำหนา)
        with open("subs.ass", "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            # ใช้ actual_font_name แทนชื่อไฟล์
            f.write(f"Style: PopUp,{actual_font_name},160,&H0000FFFF,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,18,12,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i in range(20):
                f.write(f"Dialogue: 0,0:{i*3//60:02}:{i*3%60:02}.00,0:{(i+1)*3//60:02}:{(i+1)*3%60:02}.00,PopUp,,0,0,0,,{data['scenes'][i]['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(20): f.write(f"file 'i_{i}.jpg'\nduration 3\n")
            f.write(f"file 'i_19.jpg'")

        # 📌 FFmpeg: ใช้ Filter 'subtitles' แทน 'ass' เพื่อความแม่นยำของฟอนต์
        music_input = "-i bg.mp3" if os.path.exists("bg.mp3") else ""
        audio_filter = "-filter_complex \"[1:a]volume=1.0[a1];[2:a]volume=0.1[a2];[a1][a2]amix=inputs=2:duration=first[a]\" -map 0:v -map \"[a]\"" if os.path.exists("bg.mp3") else "-c:a aac"
        
        # แก้ไข: เปลี่ยนจาก 'ass' filter เป็น 'subtitles' filter ซึ่งรองรับ fontsdir ได้ดีกว่า
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 {music_input} "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles=subs.ass:fontsdir=.,zoompan=z='min(zoom+0.0015,1.5)':d=75:s=1080x1920\" "
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
            print("✨ ภารกิจมหากาพย์สำเร็จ! วิดีโอ 60 วินาที พร้อมฟอนต์ไทยมาแล้ว!")

    except Exception as e:
        print(f"‼️ พังที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
