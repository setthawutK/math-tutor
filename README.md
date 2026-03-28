Math Tutor - Script Test Guide
1. Setup Environment (VS Code)
สร้าง venv: เปิด Terminal แล้วรัน python -m venv venv

เลือก Interpreter: * กด Ctrl + Shift + P (Cmd + Shift + P บน Mac)

พิมพ์ "Python: Select Interpreter" แล้วเลือกตัวที่มีคำว่า ('venv': venv)

ติดตั้ง Library: รัน pip install -r requirements.txt

2. API Configuration
สร้างไฟล์ .env ไว้ในโฟลเดอร์นี้ และใส่ Key ดังนี้:

Code snippet
WOLFRAM_ALPHA_APPID = "YOUR_APP_ID"
OPENAI_API_KEY = "YOUR_OPENAI_KEY"
(ไปขอ AppID ได้ที่ Wolfram Developer Portal https://developer.wolframalpha.com/)

3. Logic & Workflow
โปรเจคนี้ใช้การทำงานร่วมกัน 3 ขั้นตอน เพื่อความแม่นยำ:

LLM Translate: รับโจทย์ Thai Query -> แปลเป็น English Math Prompt

WolframAlpha: นำ Prompt ภาษาอังกฤษไปคำนวณหาคำตอบจริง (ป้องกัน AI มโนเลข)

LLM Ask: นำผลลัพธ์จาก Wolfram มาสรุปและอธิบายเป็น ภาษาไทย

4. Code Snippet (บรรทัดรับโจทย์)
Python
# แก้ไขโจทย์ภาษาไทยที่นี่
thai_query = "หาค่าดิฟของ x^2 + 5x" 

# ระบบจะแปล -> ส่ง Wolfram -> สรุปคำตอบให้ผ่าน LLM
Note: ถ้า Terminal ไม่ขึ้น (venv) ให้ลองปิดแล้วเปิด Terminal ใหม่ใน VS Code ครับ

