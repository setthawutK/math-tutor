import os
import re
from typing import AsyncGenerator

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from tenacity import retry, wait_exponential, stop_after_attempt
from pydantic import SecretStr
from dotenv import load_dotenv

load_dotenv()

# llm_translate = ChatGoogleGenerativeAI(
#     model="gemini-2.0-flash",
#     google_api_key=SecretStr(os.getenv("GEMINI_KEY", "")),
#     temperature=0
# )

llm_translate = ChatOpenAI(
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    api_key=SecretStr(os.getenv("QWEN_TRANSLATE_KEY", "")),
    model="qwen-turbo",
    temperature=0.3
)

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
    # Few-shot examples
    ("human", "Translate: หาลิมิตของ sin(x)/x เมื่อ x เข้าใกล้ 0. Category: limit"),
    ("assistant", "limit of sin(x)/x as x->0"),
    ("human", "Translate: หาอนุพันธ์ของ x^2 + 3x. Category: diff"),
    ("assistant", "derivative of x^2 + 3x"),
    ("human", "Translate: หาปริพันธ์ของ e^x. Category: integral"),
    ("assistant", "integral of e^x"),
    # โจทย์จริง
    ("human", "Translate: {query}. Category: {category}")
])

# prompt = ChatPromptTemplate.from_messages([
#     ("system", system_instruction),
#     ("human", "Translate this to Wolfram query: {query}. Category: {category}")
# ])

chain = prompt | llm_translate

models = {
    "llama": ChatOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=SecretStr(os.getenv("QWEN_K7_KEY", "")),
        model="llama-3.1-8b-instant",
        temperature=0.3
    ),
    "gemini": ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=SecretStr(os.getenv("GEM_KEY", "")),
        temperature=0.3
    ),
    # "openai":  ChatOpenAI(
    #     base_url="https://api.groq.com/openai/v1",
    #     api_key=SecretStr(os.getenv("QWEN_K7_KEY", "")),
    #     model="llama-3.3-70b-versatile",
    #     temperature=0.3,
    #     max_tokens=3000
    # ),
    # "openai": ChatOpenAI(
    #     base_url="https://api.groq.com/openai/v1",
    #     api_key=SecretStr(os.getenv("OPENAI_KEY", "")),
    #     model="openai/gpt-oss-20b",
    #     temperature=0.3,
    #     max_tokens=3000
    # ),
    "deepseek": ChatOpenAI(
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        api_key=SecretStr(os.getenv("QWEN_CLOUD_KEY", "")),
        model="deepseek-v4-flash",
        temperature=0.3,
    ),
    "qwen": ChatOpenAI(
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        api_key=SecretStr(os.getenv("QWEN_CLOUD_KEY", "")),
        model="qwen3.6-flash",
        temperature=0.3,
        model_kwargs={"extra_body": {"enable_thinking": False}}
    )
}

matrix_example = r"$$ \begin{pmatrix}a & b\\c & d\end{pmatrix} $$"
MATRIX_RULE = r"- สมการที่มี matrix (\begin{pmatrix}) ห้ามใส่ใน $ ... $ (inline) เด็ดขาด ต้องใช้ $$ ... $$ (display) เท่านั้น"

def _build_prompt(thai_query: str, wolfram_result: str, history: str = "") -> str:
    history_section = f"บทสนทนาก่อนหน้า:\n{history}\n" if history else ""
    return f"""
คุณคือติวเตอร์แคลคูลัส 1 สำหรับนักศึกษาวิศวกรรมปี 1
{history_section}

โจทย์ที่นักศึกษาถาม:
{thai_query}

ผลลัพธ์จากการคำนวณ:
{wolfram_result}

จงอธิบายวิธีทำเป็นภาษาไทย โดยยึดผลลัพธ์จากการคำนวณเป็นคำตอบอ้างอิงหลัก
อธิบายครบทั้ง 5 ข้อตามโครงสร้างนี้:

**1. ทำความเข้าใจโจทย์**
> อธิบายสั้น ๆ ว่าโจทย์ต้องการหาอะไร

**2. ระบุข้อมูลสำคัญ**
> ระบุนิพจน์ ตัวแปร ค่าที่กำหนด หรือเงื่อนไขสำคัญ

**3. วางแผนการแก้โจทย์**
> บอกแนวทางที่จะใช้แก้โจทย์ และเหตุผลสั้น ๆ

**4. แสดงวิธีทำทีละขั้นตอน**
> ใช้แนวทางจากข้อ 3 เท่านั้น ห้ามเปลี่ยนแนวทางกลางคัน
> แสดงขั้นตอนไม่เกิน 5 ขั้น ห้ามแยกอินทิกรัลออกเป็นชิ้นย่อยโดยไม่จำเป็น

**5. สรุปคำตอบ**
> สรุปคำตอบสุดท้ายในกรอบนี้เสมอ:
> $$\\boxed{{คำตอบ}}$$

=== กฎการจัดรูปแบบ (บังคับ 100%) ===

**การย่อหน้า:**
- เนื้อหาใต้หัวข้อทุกข้อ ต้องขึ้นต้นด้วย > (blockquote) ทุกบรรทัด
- สมการ $$ ที่อยู่ใต้หัวข้อ ก็ต้องขึ้นต้นด้วย > ด้วย
- ถ้าจะเว้นบรรทัดภายใน blockquote ให้ใช้ >  (> + space) แทนบรรทัดว่าง

ตัวอย่างรูปแบบที่ถูกต้อง:

**1. ทำความเข้าใจโจทย์**
> โจทย์ต้องการหาค่าลิมิตของ $\\frac{{\\sin(x)}}{{x}}$ เมื่อ $x$ เข้าใกล้ $0$

**4. แสดงวิธีทำทีละขั้นตอน**
>
> **ขั้นที่ 1:** ตรวจสอบรูปแบบไม่กำหนด เมื่อแทน $x = 0$ จะได้ $\\frac{{0}}{{0}}$
>
> **ขั้นที่ 2:** ใช้กฎของโลปีตาล หาอนุพันธ์ของตัวเศษและตัวส่วน
>
> $$ \\frac{{d}}{{dx}}[\\sin(x)] = \\cos(x) $$
>
> $$ \\frac{{d}}{{dx}}[x] = 1 $$
>
> **ขั้นที่ 3:** นำมาแทนในลิมิต
>
> $$ \\lim_{{x \\to 0}} \\frac{{\\cos(x)}}{{1}} = \\cos(0) = 1 $$

**สมการ:**
- สมการในประโยค → $ ... $ เช่น $x = 0$
- สมการขึ้นบรรทัดใหม่ → $$ ... $$ พร้อม > นำหน้า และมีบรรทัดว่าง (>) คั่นก่อนและหลัง
- ห้ามใช้ \\( \\) หรือ \\[ \\] เด็ดขาด
- ห้ามเขียน LaTeX ลอยๆ นอก $ เช่น \\frac, \\lim, \\sin
- สมการ matrix ให้ใช้ {matrix_example}
- สมการ $$ ต้องขึ้นต้นด้วย > เพียงตัวเดียว ไม่มีอะไรอื่น
- {MATRIX_RULE}


**การเขียนข้อความ:**
- ห้ามใช้ emoji ทุกกรณี
- ใช้ภาษาเป็นทางการแต่เข้าใจง่าย ไม่ต้องมีคำทักทาย


=== ข้อห้ามเนื้อหา ===
- ห้ามมีคำว่า "Wolfram" ในคำอธิบาย
- คำตอบสุดท้ายต้องตรงกับผลลัพธ์จากการคำนวณ
- ห้ามอธิบายเกินขอบเขตโจทย์
- ห้ามสร้างโจทย์ใหม่
- ห้ามวนซ้ำขั้นตอนที่ทำไปแล้ว
- ขั้นที่ 4 มีได้ไม่เกิน 5 ขั้นย่อยเท่านั้น
- ห้ามใช้ > ซ้อนกัน 2 ชั้น (> >) เด็ดขาด ให้ใช้ > ชั้นเดียวเท่านั้นทุกกรณี
"""


@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def translate_to_wolfram(thai_query: str, category: str = "") -> str:
    response = chain.invoke({"query": thai_query, "category": category})
    return response.content.strip()


@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
def _call_llm(model_name: str, p: str) -> str:
    try:
        response = models[model_name].invoke(p)
        content = str(response.content)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return content
    except Exception as e:
        print(f"\n  [_call_llm ERROR] model={model_name}: {e}")
        raise


def explain(thai_query: str, wolfram_result: str, model_name: str, history: str = "") -> str:
    try:
        p = _build_prompt(thai_query, wolfram_result, history)
        return _call_llm(model_name, p)
    except Exception as e:
        print(f"[explain error - {model_name}]: {type(e).__name__}: {e}")  # เพิ่ม type
        return ""


async def aexplain(thai_query: str, wolfram_result: str, model_name: str) -> AsyncGenerator[str, None]:
    p = _build_prompt(thai_query, wolfram_result)
    full_response = ""
    try:
        async for chunk in models[model_name].astream(p):
            content = str(chunk.content)
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            if content:
                full_response += content
                yield content
    except Exception:
        result = await models[model_name].ainvoke(p)
        content = re.sub(r'<think>.*?</think>', '', str(result.content), flags=re.DOTALL)
        if content:
            full_response += content
            yield content

    # fix \\ หายใน matrix
    print(f"\n[{model_name} FULL RESPONSE]\n{full_response}\n{'='*50}")


