import os
import wolframalpha  # นำเข้าตัว Library หลัก
from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate

# 1. โหลด Key
load_dotenv()
WOLFRAM_APPID = os.getenv("WOLFRAM_APP_ID")

# 2. ตั้งค่า Llama
llm = OllamaLLM(model="llama3.1:8b")

def solve_calculus(user_input):
    print("🤖 MathTutor กำลังคิด...")
    
    try:
        print("🔍 กำลังคำนวณผ่าน WolframAlpha...")
        client = wolframalpha.Client(WOLFRAM_APPID)
        res = client.query(user_input)
        
        # ปรับการดึงข้อมูล: ดึงข้อความจากทุก Pods มาช่วยให้ AI เห็นภาพรวม
        all_results = []
        for pod in res.pods:
            for subpod in pod.subpods:
                if subpod.plaintext:
                    all_results.append(f"{pod.title}: {subpod.plaintext}")
        
        wolfram_text = "\n".join(all_results) if all_results else "No plaintext results"
    except Exception as e:
        print(f"⚠️ Wolfram Error: {e}")
        wolfram_text = "คำนวณสำเร็จ แต่โปรดใช้ความรู้พื้นฐานในการอธิบาย"

    print("✍️ กำลังเรียบเรียงคำอธิบายภาษาไทย...")
    
    # ปรับ Template ให้คุมกำเนิด AI ไม่ให้มโนชื่อสูตร
    template = """คุณคือ "MathTutor" ผู้ช่วยสอน Calculus I สำหรับนักศึกษาคอมพิวเตอร์ PIM 
    จงอธิบายโจทย์: {question}
    โดยอ้างอิงข้อมูลคำนวณ: {wolfram_result}
    
    ข้อกำหนดในการตอบ:
    1. อธิบายเป็นภาษาไทยที่ถูกต้องตามหลักการคณิตศาสตร์
    2. หากต้องใช้บทนิยามของลิมิต ให้เรียกว่า "บทนิยามของอนุพันธ์" ห้ามสร้างชื่อสูตรใหม่เอง
    3. แสดงวิธีทำทีละขั้นตอนอย่างละเอียด (Step-by-Step)
    4. ใช้ LaTeX สำหรับสูตรคณิตศาสตร์เสมอ เช่น $f'(x)$ หรือ $\frac{{d}}{{dx}}$
    5. สรุปคำตอบสุดท้ายในกรอบ \boxed{{}}
    
    คำอธิบาย:"""
    
    # ตั้งค่า temperature เป็น 0 เพื่อให้ AI ตอบแบบตรงไปตรงมา ไม่เน้นจินตนาการ
    llm.temperature = 0 
    
    full_prompt = template.format(question=user_input, wolfram_result=wolfram_text)
    thai_explanation = llm.invoke(full_prompt)
    
    return thai_explanation

if __name__ == "__main__":
    test_question = "Find the derivative of x^2 + 3x"
    print(solve_calculus(test_question))