import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from tenacity import retry, wait_exponential, stop_after_attempt
from pydantic import SecretStr
from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt
import re


load_dotenv()

# llm_translate = ChatOpenAI(
#     base_url="https://api.groq.com/openai/v1",
#     api_key=SecretStr(os.getenv("GROQ_BAO_KEY", "")),
#     model="llama-3.1-8b-instant",
#     temperature=0
# )

llm_translate = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=SecretStr(os.getenv("GEMINI_KEY", "")),
        temperature=0
    )


# prompt = ChatPromptTemplate.from_messages([
#     ("system", """You are a math query generator for Wolfram Alpha.
#     Convert LaTeX to standard math syntax.
#     Use '*' for multiplication, '^' for exponent, and () for grouping.
#     Handle limits, derivatives, and integrals as per standard Wolfram syntax.
#     Output ONLY the raw query string."""),
#     ("human", "Translate this to Wolfram query: {query}. Category: {category}")
# ])

system_instruction = """You are a math query generator for Wolfram Alpha.
Follow these rules strictly:
1. Translate LaTeX math to standard Wolfram Alpha syntax.
2. Use '*' for multiplication, '^' for exponent, and () for proper grouping.
3. Output ONLY the raw query string. Do not explain.

4. SPECIAL RULE FOR DERIVATIVES: 
   - If the query simply asks for a derivative, use: "derivative of [EXPR]"
   - IF the query specifically asks to use the "definition of derivative" (e.g., "ใช้นิยาม", "โดยใช้นิยามของอนุพันธ์"), YOU MUST construct the limit formula: 
     "limit ((f(x+h) - f(x)) / h) as h->0"
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_instruction),
    ("human", "Translate this to Wolfram query: {query}. Category: {category}")
])

chain = prompt | llm_translate

models = {
    "llama": ChatOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=SecretStr(os.getenv("QWEN_K7_KEY", "")),
        model="llama-3.1-8b-instant",
        temperature=0.3
    ),
    "openai": ChatOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=SecretStr(os.getenv("OPENAI_KEY", "")),
        model="openai/gpt-oss-120b",
        temperature=0.3
    ),
    "gemini": ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=SecretStr(os.getenv("GEM_KEY", "")),
        temperature=0.3
    ),
    "qwen1": ChatOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=SecretStr(os.getenv("QWEN_K7_KEY", "")),
        model="qwen/qwen2.5-32b",
        temperature=0.3,
    ),
    "qwen": ChatOpenAI(
        # ใช้ URL สำหรับเรียกโมเดลปกติของฝั่ง International
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        api_key=SecretStr(os.getenv("QWEN_CLOUD_KEY", "")),
        # ใช้ชื่อโมเดลที่มีอยู่จริงบนระบบ
        model="qwen3.6-flash",
        temperature=0.3,
        model_kwargs={
            "extra_body": {
                "enable_thinking": False
            }
        }
    )
}



@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def translate_to_wolfram(thai_query: str, category: str = "") -> str:
    response = chain.invoke({"query": thai_query, "category": category})
    return response.content.strip()


@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
def _call_llm(model_name: str, prompt: str) -> str:
    try:
        response = models[model_name].invoke(prompt)
        content = str(response.content)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return content
    except Exception as e:
        print(f"\n  [_call_llm ERROR] model={model_name}")
        print(f"  type: {type(e).__name__}")
        print(f"  detail: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"  response body: {e.response.text}")
            except Exception:
                pass
        raise


def explain(thai_query: str, wolfram_result: str, model_name: str, history: str = "") -> str:
    history_section = f"บทสนทนาก่อนหน้า:\n{history}\n" if history else ""
    prompt = f"""
คุณคือติวเตอร์แคลคูลัส 1 สำหรับนักศึกษาวิศวกรรมปี 1
{history_section}

โจทย์ที่นักศึกษาถาม:
{thai_query}

ผลลัพธ์จาก Wolfram Alpha:
{wolfram_result}

จงอธิบายวิธีทำเป็นภาษาไทย โดยยึดผลลัพธ์จาก Wolfram Alpha เป็นคำตอบอ้างอิงหลัก
และอธิบายตามโครงสร้าง Plan-and-Solve ดังนี้:

1. ทำความเข้าใจโจทย์
- อธิบายสั้น ๆ ว่าโจทย์ต้องการหาอะไร

2. ระบุข้อมูลสำคัญ
- ระบุนิพจน์ ตัวแปร ค่าที่กำหนด หรือเงื่อนไขสำคัญจากโจทย์

3. วางแผนการแก้โจทย์
- บอกว่าจะใช้กฎ สูตร หรือทฤษฎีใด
- อธิบายว่าทำไมจึงเลือกใช้วิธีนั้น

4. แสดงวิธีทำทีละขั้นตอน
- แสดงการจัดรูปสมการและการแทนค่าตามกฎที่เลือกใช้อย่างเป็นลำดับขั้น
- อธิบายการเปลี่ยนแปลงของสมการในแต่ละขั้นด้วยภาษาที่นักศึกษาปี 1 เข้าใจง่าย

5. สรุปคำตอบ
- สรุปคำตอบสุดท้ายให้ชัดเจน

ข้อกำหนดสำคัญเรื่องฟอร์แมตสมการ:
- สมการคณิตศาสตร์ทั้งหมดต้องเขียนด้วย LaTeX
- สมการที่ต้องการให้ขึ้นบรรทัดใหม่ ต้องครอบด้วยเครื่องหมาย $$ ทั้งหน้าและหลัง เช่น $$ x^2 + 1 $$
- สมการที่แทรกอยู่ในประโยค ต้องครอบด้วยเครื่องหมาย $ ทั้งหน้าและหลัง เช่น ค่าของ $x=2$
- ห้ามใช้เครื่องหมาย \\( หรือ \\[ ในการครอบสมการเด็ดขาด ให้ใช้แค่ $ หรือ $$ เท่านั้น

ข้อห้าม:
- ในระหว่างที่คุณเขียนวิธีทำในข้อ 4 คุณต้องใช้ "ผลลัพธ์จาก Wolfram Alpha" เป็นตัวบังคับทิศทางเสมอ
- คำตอบสุดท้ายในข้อ 5 ต้องมีค่าเทียบเท่ากับผลลัพธ์จาก Wolfram Alpha เสมอ
- ห้ามเปลี่ยนคำตอบสุดท้ายเอง และห้ามเดาคำตอบใหม่ที่ขัดแย้งกับ Wolfram Alpha เด็ดขาด
- ห้ามมีคำว่า "Wolfram Alpha" หรือ "Wolfram" ปรากฏอยู่ในคำอธิบายของคุณโดยเด็ดขาด ให้ทำเสมือนว่าคุณคิดคำนวณทั้งหมดด้วยตัวเอง
- สมการคณิตศาสตร์ทั้งหมดต้องเขียนด้วย LaTeX
- ห้ามอธิบายเกินขอบเขตโจทย์
- ห้ามสร้างโจทย์ใหม่
- ห้ามเดาคำตอบใหม่ที่ขัดกับ Wolfram Alpha
- ใช้ภาษาเข้าใจง่ายสำหรับนักศึกษาปี 1
"""
    return _call_llm(model_name, prompt)
