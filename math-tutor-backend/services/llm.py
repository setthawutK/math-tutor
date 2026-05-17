import os
from langchain_openai import ChatOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt
from pydantic import SecretStr
from dotenv import load_dotenv

load_dotenv()

llm_translate = ChatOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=SecretStr(os.getenv("GROQ_KEY", "")),
    model="llama-3.1-8b-instant",
    temperature=0
)


models = {
    "llama": ChatOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=SecretStr(os.getenv("GROQ_KEY", "")),
        model="llama-3.1-8b-instant",
        temperature=0.3
    ),
    "deepseek": ChatOpenAI(
        base_url="https://api.deepseek.com",
        api_key=SecretStr(os.getenv("DEEPSEEK_KEY", "")),
        model="deepseek-chat",
        temperature=0.3
    ),
    "qwen": ChatOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=SecretStr(os.getenv("QWEN_KEY", "")),
        model="qwen-qwq-32b",
        temperature=0.3
    )
}

def translate_to_wolfram(thai_query: str) -> str:
    response = llm_translate.invoke(f"""
You are a query translator. ALWAYS respond in English only.
NEVER respond in Thai. Output the query string only.

Convert this math problem to ONE Wolfram Alpha query only.
Rules:
- Use standard math notation that Wolfram Alpha understands.
- ONE query only, no comma, no "and"

Examples:
Input: หา limit ของ sin(x)/x เมื่อ x→0
Output: limit of sin(x)/x as x->0

Input: หาอนุพันธ์ของ x^3 + 2x
Output: derivative of x^3 + 2x

Input: หา limit ของ 3x^2 - 1 เมื่อ x เข้าใกล้ 1
Output: limit of 3x^2 - 1 as x->1

Input: หาปริพันธ์ของ x^2 + 1
Output: integral of x^2 + 1

Input: {thai_query}
Output:""")
    return str(response.content).strip()


@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
def _call_llm(model_name: str, prompt: str) -> str:
    response = models[model_name].invoke(prompt)
    return str(response.content)

def explain(thai_query: str, wolfram_result: str, model_name: str, history: str = "") -> str:
    history_section = f"บทสนทนาก่อนหน้า:\n{history}\n" if history else ""
    prompt = f"""
คุณคือติวเตอร์แคลคูลัส 1 สำหรับนักศึกษาวิศวกรรมปี 1
{history_section}
โจทย์ที่นักศึกษาถาม: {thai_query}
Wolfram Alpha คำนวณได้: {wolfram_result}

อธิบาย step-by-step ภาษาไทย โดย:
1. บอกกฎหรือทฤษฎีที่ใช้
2. แสดงขั้นตอนเป็น LaTeX
3. สรุปคำตอบ

ข้อห้าม:
- ห้ามอธิบายเกินขอบเขตโจทย์
- ใช้ภาษาเข้าใจง่ายสำหรับนักศึกษาปี 1
"""
    return _call_llm(model_name, prompt)