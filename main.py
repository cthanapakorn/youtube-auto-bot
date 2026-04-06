import os, re, json, subprocess, requests, sys, time, random, io
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image

# --- ⚙️ ตั้งค่าระดับสูงสุด (20 ฉากย่อย ฉากละ 3 วินาที = 60 วินาทีพอดี) ---
# การเพิ่มจำนวนฉากเป็น 20 จะทำให้ซับไตเติล "เด้ง" ขึ้นมาทีละคำตามจังหวะพูด
SCENE_COUNT = 20   
SCENE_DURATION = 3 
VIDEO_PRIVACY = "private"

# 📌 ล็อกคาแรคเตอร์ตัวละคร (หน้าเดิมตลอดทั้งคลิป)
CHAR_ANCHOR = "A charismatic 25-year-old Thai male office worker, messy black hair, white shirt, dark blue tie, hyper-realistic anime style, detailed facial features"

def fetch_image_master(prompt, filename, scene_num):
    """ฟังก์ชันวาดภาพ Ultra-HD 1024x1792 เน้นการแสดงออกและท่าทางที่ชัดเจน"""
    print(f"   ⏳ ฉากที่ {scene_num}: กำลังเนรมิตภาพ (Action Focus)...")
    
    # เน้นให้ AI วาดอาการตัวละครให้ชัด (Emphasize Actions)
    full_prompt = f"{CHAR_ANCHOR}, {prompt}, cinematic lighting, 8k resolution, highly detailed, expressive face, masterpiece"
    clean_p = re.sub(r'[^\w\s]', '', full_prompt).strip().replace(' ', '%20')
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    # ใช้ Seed 8888 คุมหน้าตัวละคร
    url = f"https://image.pollinations.ai/prompt/{clean_p}?width=1024&height=1792&seed=8888&nologo=true&model=flux"

    for attempt in range(5):
        try:
            r = requests.get(url, headers=headers, timeout=120)
            if r.status_code == 200:
                with open(filename, 'wb') as f: f.write(r.content)
                print(f"      ✅ ฉากที่ {scene_num} สำเร็จ!")
                return True
            time.sleep(15)
        except: time.sleep(15)
    return False

def run_workflow():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        print("🧠 1. AI กำลังคิดบทพากย์และซับไตเติลแบบ Pop-up (ทีละคำ)...")
        
        prompt_sys = (
            "จงสวมบทบาทเป็นมือโปรทำคลิป Shorts การเงิน หัวข้อ: 'วิธีแก้จนฉบับมนุษย์เงินเดือน' "
            "ภารกิจ: สร้างสคริปต์ที่แบ่งเป็น 20 ช่วงสั้นๆ (ช่วงละ 3 วินาที) "
            "กฎเหล็ก:\n"
            "1. บทพากย์ (text): ต้องเป็นภาษาไทยที่มีอารมณ์ ใช้ '...' เพื่อหยุดพัก และ '!' เพื่อเน้นเสียง ห้ามมีคำบรรยายฉากปนมา\n"
            "2. คำสั่งวาดรูป (prompt): เป็นภาษาอังกฤษ อธิบาย 'ท่าทางและอารมณ์' ของตัวละครให้ชัดเจน (เช่น 'looking shocked at a credit card bill' หรือ 'celebrating with money raining')\n"
            "3. ซับไตเติล (caption): ต้องเป็นคำไทยสั้นๆ แค่ 1-2 คำ เพื่อให้มันเด้งขึ้นมาทีละตัวตามคำพูด\n"
            "ตรวจสอบ: บทต้องตื่นเต้นและซับไตเติลต้องกระแทกใจ "
            "ส่งผลลัพธ์เป็น JSON: {\"title\": \"...\", \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]}"
        )
        
        response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
        data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        
        print(f"🎬 หัวข้อวิดีโอ: {data['title']}")

        print("🎙️ 2. สร้างเสียงพากย์ที่มีน้ำเสียงหนักเบา (Premwadee)...")
        # ใส่จังหวะหยุดพักระหว่างวลีเพื่อให้เสียงดูสมจริง
        full_voice_text = " . . ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-8% --voice "th-TH-PremwadeeNeural" --text "{full_voice_text}" --write-media "v.mp3"', shell=True, check=True)

        print("🖼️ 3. เข้าสู่กระบวนการวาดภาพระดับ Ultra HD (20 ฉาก)...")
        for i in range(20):
            scene_data = data['scenes'][i]
            fetch_image_master(scene_data['prompt'], f"i_{i}.jpg", i+1)

        print("🎬 4. ประกอบวิดีโอพร้อมซับไตเติลแบบ Pop-up ทีละคำ...")
        
        # ใช้ฟอนต์ที่คุณอัปโหลดขึ้นไป (font.ttf)
        font_name = "font.ttf" if os.path.exists("font.ttf") else "Sans"
        
        # ⚠️ สร้างไฟล์ซับไตเติล .ass (ตัวใหญ่สะใจ สีเหลืองนีออน ขอบดำหนา)
        with open("subs.ass", "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            # &H0000E6FF = สีเหลืองอมส้ม (นีออน) | ขอบหนา 18 | เงา 12 | Alignment 2 (กึ่งกลางล่าง)
            f.write(f"Style: Viral,{font_name},140,&H0000E6FF,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,18,12,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            for i in range(20):
                start = i * SCENE_DURATION
                end = (i + 1) * SCENE_DURATION
                f.write(f"Dialogue: 0,0:{start//60:02}:{start%60:02}.00,0:{end//60:02}:{end%60:02}.00,Viral,,0,0,0,,{data['scenes'][i]['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(20): f.write(f"file 'i_{i}.jpg'\nduration {SCENE_DURATION}\n")
            f.write(f"file 'i_19.jpg'") 
        
        # 📌 FFmpeg: รวมพลังคุณภาพสูงสุดและซูม Cinematic
        cmd = (
            "ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 "
            "-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass=subs.ass,zoompan=z='min(zoom+0.0015,1.5)':d=75:s=1080x1920\" "
            "-c:v libx264 -pix_fmt yuv420p -r 25 -c:a aac -shortest final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        print(f"🚀 5. อัปโหลดสู่ YouTube...")
        if os.path.exists('token.json'):
            with open('token.json', 'r') as f:
                creds = YoutubeCredentials.from_authorized_user_info(json.load(f))
            youtube = build("youtube", "v3", credentials=creds)
            youtube.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": data['title'], "categoryId": "27"}, "status": {"privacyStatus": VIDEO_PRIVACY}},
                media_body=MediaFileUpload("final.mp4")
            ).execute()
            print("✨ ภารกิจมหากาพย์สำเร็จ! ซับไทยเด้งทีละคำและภาพสื่ออารมณ์ชัดเจนแล้วครับ")

    except Exception as e:
        print(f"‼️ พังตรงนี้: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_workflow()
