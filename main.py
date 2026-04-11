import os, re, json, subprocess, requests, sys, time, random, shutil
from google import genai
from google.oauth2.credentials import Credentials as YoutubeCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from PIL import Image, ImageFont

SCENE_COUNT = 6   
SCENE_DURATION = 10 
VIDEO_PRIVACY = "private"

def install_and_get_font():
    font_family = "Sans"
    if os.path.exists("font.ttf"):
        try:
            font = ImageFont.truetype("font.ttf")
            font_family, _ = font.getname()
            font_dir = os.path.expanduser("~/.fonts")
            os.makedirs(font_dir, exist_ok=True)
            shutil.copy("font.ttf", os.path.join(font_dir, "font.ttf"))
            subprocess.run(["fc-cache", "-f", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass
    return font_family

def fetch_image(prompt, char_anchor, filename, scene_num):
    print(f"   🎨 ฉากที่ {scene_num}: กำลังวาดภาพตาม Video Plan...")
    clean_p = re.sub(r'[^\w\s]', '', prompt).strip().replace(' ', '%20')
    style = "cinematic photorealistic, dramatic lighting, masterpiece, 8k resolution"
    
    url = f"https://image.pollinations.ai/prompt/{clean_p},{char_anchor},{style}?width=1080&height=1920&seed={random.randint(1,999999)}&nologo=true&model=flux"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    for attempt in range(5): 
        try:
            r = requests.get(url, headers=headers, timeout=120)
            if r.status_code == 200 and len(r.content) > 20000:
                with open(filename, 'wb') as f: f.write(r.content)
                return True
            time.sleep(10)
        except: time.sleep(10)
    
    Image.new('RGB', (1080, 1920), color=(15, 15, 15)).save(filename, 'JPEG')
    return True

def run_autonomous_system():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key.strip())
        
        # 🧠 STEP 1-3 & 7: Idea Generation + Scripting + Self-Critique Loop
        data = None
        for attempt in range(3): # ลูปตรวจสอบคุณภาพ ให้โอกาสแก้ตัว 3 ครั้ง
            print(f"🧠 [Attempt {attempt+1}] AI กำลังสุ่มไอเดีย, เขียนบท และประเมินความไวรัล...")
            
            prompt_sys = (
                "You are an autonomous AI content production system for YouTube Shorts.\n"
                "STEP 1: Brainstorm 5 viral ideas (finance, psychology, life hacks, etc.) with psychological hooks. Select the BEST one.\n"
                "STEP 2: Design a cinematic character (e.g., 'A stressed 30-year-old Thai entrepreneur, cinematic realism').\n"
                "STEP 3: Write a 6-scene script (10s per scene). Thai voiceover (40-50 words/scene). Hook->Setup->Problem->Crisis->Turning Point->Lesson.\n"
                "STEP 4: Provide English image prompts for each scene. MUST include the character description in scenes showing people.\n"
                "STEP 5: Add short 1-2 word Thai captions.\n"
                "STEP 6: Evaluate your own work. Give a Viral Score (1-10) based on Hook strength, Retention, and Emotion. Be strict.\n\n"
                "Output STRICT JSON format:\n"
                "{\n"
                "  \"selected_idea\": \"...\",\n"
                "  \"character_design\": \"...\",\n"
                "  \"viral_score\": 9,\n"
                "  \"title\": \"...\",\n"
                "  \"desc\": \"...\",\n"
                "  \"tags\": \"...\",\n"
                "  \"scenes\": [{\"text\": \"...\", \"prompt\": \"...\", \"caption\": \"...\"}]\n"
                "}"
            )
            response = client.models.generate_content(model='models/gemini-2.5-flash', contents=prompt_sys)
            temp_data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
            
            print(f"   📊 Viral Score ที่ได้: {temp_data['viral_score']}/10")
            if temp_data['viral_score'] >= 8:
                data = temp_data
                print("   ✅ คุณภาพผ่านเกณฑ์! นำไปผลิตต่อได้")
                break
            else:
                print("   ❌ คุณภาพต่ำกว่าเกณฑ์ (Score < 8) สั่งรื้อเขียนใหม่...")

        if not data: raise ValueError("ไม่สามารถสร้างคอนเทนต์ที่ผ่านเกณฑ์ (Score >= 8) ได้ใน 3 รอบ")

        # 💾 STEP 9 & 10: Save Outputs to Folder
        os.makedirs("output", exist_ok=True)
        with open("output/metadata.txt", "w", encoding="utf-8") as f:
            f.write(f"Title: {data['title']}\nDesc: {data['desc']}\nTags: {data['tags']}\nIdea: {data['selected_idea']}")
        with open("output/script.txt", "w", encoding="utf-8") as f:
            for i, sc in enumerate(data['scenes']): f.write(f"Scene {i+1}: {sc['text']}\n")

        # 🔊 STEP 4: Voice Generation
        print("🎙️ 4. สร้างเสียงพากย์...")
        full_voice = " . . . ".join([s['text'] for s in data['scenes']])
        subprocess.run(f'edge-tts --rate=-3% --voice "th-TH-NiwatNeural" --text "{full_voice}" --write-media "v.mp3"', shell=True, check=True)

        # 🎬 STEP 5: Image Generation (using Dynamic Character)
        print(f"🖼️ 5. วาดภาพตาม Video Plan (Character: {data['character_design']})...")
        for i, sc in enumerate(data['scenes']):
            fetch_image(sc['prompt'], data['character_design'], f"i_{i}.jpg", i+1)
            time.sleep(3)

        # ✂️ STEP 6: Editing Automation
        print("🎬 6. ประกอบวิดีโอ 60 วินาที...")
        font_family = install_and_get_font()
        
        with open("subs.ass", "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write(f"Style: MovieSub,{font_family},160,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,18,8,2,80,80,450,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            
            for i in range(SCENE_COUNT):
                start_time = i * SCENE_DURATION
                end_time = start_time + 3  # ซับเด้ง 3 วิแล้วหายไป
                f.write(f"Dialogue: 0,0:{start_time//60:02}:{start_time%60:02}.00,0:{end_time//60:02}:{end_time%60:02}.00,MovieSub,,0,0,0,,{data['scenes'][i]['caption']}\n")

        with open("l.txt", "w") as f:
            for i in range(SCENE_COUNT): f.write(f"file 'i_{i}.jpg'\nduration 10\n")
            f.write(f"file 'i_5.jpg'")

        has_bg = os.path.exists("bg.mp3")
        music_input = "-i bg.mp3" if has_bg else ""
        audio_filter = "-filter_complex \"[1:a]volume=1.0[a1];[2:a]volume=0.08[a2];[a1][a2]amix=inputs=2:duration=first[a]\" -map 0:v -map \"[a]\"" if has_bg else "-c:a aac"
        
        cmd = (
            f"ffmpeg -y -f concat -safe 0 -i l.txt -i v.mp3 {music_input} "
            f"-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles=subs.ass,zoompan=z='min(zoom+0.001,1.3)':d=250:s=1080x1920\" "
            f"{audio_filter} -c:v libx264 -crf 18 -pix_fmt yuv420p -r 25 -t 60 final.mp4"
        )
        subprocess.run(cmd, shell=True, check=True)

        # 📊 STEP 8: YouTube Upload
        print(f"🚀 8. อัปโหลดสู่ YouTube พร้อม SEO...")
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
            print("✨ ภารกิจสำเร็จ! ระบบ Autonomous ทำงานจบกระบวนการ!")

    except Exception as e:
        print(f"‼️ ขัดข้องที่: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_autonomous_system()
