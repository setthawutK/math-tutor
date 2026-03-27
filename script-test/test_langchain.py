import requests
import os
from dotenv import load_dotenv
from langchain_ollama import OllamaLLM

load_dotenv()

llm_translate = OllamaLLM(model="llama3.2:3b", temperature=0)
llm_explain = OllamaLLM(model="llama3.1:8b")

def translate_to_wolfram(thai_query: str) -> str:
    result = llm_translate.invoke(f"""
You are a query translator. 
ALWAYS respond in English only.
NEVER respond in Thai.
NEVER explain. Output the query string only.
Convert this math problem to ONE Wolfram Alpha query only.
Reply with the query only. No explanation. No extra words.

Rules:
- LaTeX is allowed and encouraged for math expressions.
- Use standard math notation that Wolfram Alpha understands.
- Wolfram Alpha always plot graphs of functions, so if the query involves graphing, just write the function expression.
                                  
Input: {thai_query}
Output:""").strip()
    return result

def ask_wolfram(query: str):
    app_id = os.getenv("WOLFRAM_APP_ID")
    res = requests.get(
        "https://www.wolframalpha.com/api/v1/llm-api",
        params={"input": query, "appid": app_id}
    )
    print(f"Wolfram status: {res.status_code}")
    return None if res.status_code != 200 else res.text

def explain(thai_query: str, wolfram_result: str) -> str:
    return llm_explain.invoke(f"""
คุณคือติวเตอร์แคลคูลัส 1 สำหรับนักศึกษาวิศวกรรมปี 1 ไทย
โจทย์ที่นักศึกษาถาม: {thai_query}
Wolfram Alpha คำนวณได้: {wolfram_result}

อธิบาย step-by-step ภาษาไทย โดย:
1. บอกกฎหรือทฤษฎีที่ใช้ ใช้ชื่อภาษาไทย เช่น "ทฤษฎีบทลิมิต"
2. แสดงขั้นตอนสั้นๆ ตรงประเด็น ไม่ต้องอธิบายเกินจำเป็น
3. แสดงการคำนวณเป็น LaTeX
4. สรุปคำตอบ

ข้อห้าม:
- ห้ามอธิบายเกินขอบเขตโจทย์
- ใช้ภาษาเข้าใจง่ายสำหรับนักศึกษาปี 1
""")

# ทดสอบ
thai_query = "ให้ f(x) = |x| / x จงเขียนกราฟของ f และพิจารณาว่า f(x) มีค่าอย่างไรเมื่อ x เข้าใกล้ 0"
#thai_query = "plot graph and limit as x approaches 0 of (abs(x))/x"
#thai_query = "ให้ f(x) = 3x^2 - 1 เมื่อ x มีค่าเข้าใกล้ 1 แล้ว f(x) เป็นอย่างไร"


wolfram_query = translate_to_wolfram(thai_query)
print(f"โจทย์: {thai_query}")

print(f"แปลเป็น: {wolfram_query}")

wolfram_result = ask_wolfram(wolfram_query)
print(f"\nWolfram ตอบ: {wolfram_result}")

if wolfram_result is None:
    response = llm_explain.invoke("แจ้งนักศึกษาว่าลองพิมพ์โจทย์ใหม่ให้ชัดขึ้น")
else:
    response = explain(thai_query, wolfram_result)

print(f"\nLLM อธิบาย:\n{response}")