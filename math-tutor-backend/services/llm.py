from langchain_ollama import OllamaLLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
import os

llm_translate = OllamaLLM(model="llama3.2:3b", temperature=0)

models = { "llama": OllamaLLM(model="llama3.1:8b", temperature=0.3)
}
    # "llama": OllamaLLM(model="llama3.1:8b", temperature=0.3),
    # "deepseek": ChatOpenAI(
    #     base_url="https://api.deepseek.com",
    #     api_key=os.getenv("DEEPSEEK_API_KEY"),
    #     model="deepseek-chat",
    #     temperature=0.3
    # ),
    # "gemini": ChatGoogleGenerativeAI(
    #     model="gemini-1.5-flash",
    #     google_api_key=os.getenv("GEMINI_API_KEY"),
    #     temperature=0.3
    # )

def translate_to_wolfram(thai_query: str) -> str:
    return llm_translate.invoke(f"""
You are a query translator. ALWAYS respond in English only.
NEVER respond in Thai. Output the query string only.

Convert this math problem to ONE Wolfram Alpha query only.
Rules:
- Use standard math notation that Wolfram Alpha understands.
- ONE query only, no comma, no "and"
- Wolfram Alpha always plot graphs of functions, so if the query involves graphing, just write the function expression.

Input: {thai_query}
Output:""").strip()

def explain(thai_query: str, wolfram_result: str, model_name: str, history: str) -> str:
    llm = models.get(model_name, models["llama"])
    return llm.invoke(f"""
คุณคือติวเตอร์แคลคูลัส 1 สำหรับนักศึกษาวิศวกรรมปี 1
โจทย์ที่นักศึกษาถาม: {thai_query}
Wolfram Alpha คำนวณได้: {wolfram_result}

อธิบาย step-by-step ภาษาไทย โดย:
**แบ่งวรรคให้สวยงามสำหรับ Fron end Response**
1. บอกกฎหรือทฤษฎีที่ใช้(ถ้ามี)
2. แสดงขั้นตอนเป็น step by step ตรงประเด็น ไม่ต้องอธิบายเกินจำเป็น
3. สรุปคำตอบ

ข้อห้าม:
- ห้ามอธิบายเกินขอบเขตโจทย์
- ใช้ภาษาเข้าใจง่ายสำหรับนักศึกษาปี 1
""")