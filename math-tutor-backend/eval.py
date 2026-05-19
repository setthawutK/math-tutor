import pandas as pd
import csv
import os
import re
import time
from tqdm import tqdm
from typing import cast
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

# นำเข้าฟังก์ชันจากโฟลเดอร์ services
from services.llm import translate_to_wolfram, explain
from services.wolfram import ask_wolfram

# ตั้ง LLM ตัวเล็ก (Llama 8B) มาเป็นผู้ช่วยตรวจสมการ
judge_llm = ChatOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=SecretStr(os.getenv("GROQ_KAFA_KEY", "")),  # ใช้ GROQ_KEY เพราะเป็น llama-3.1-8b-instant
    model="llama-3.1-8b-instant",
    temperature=0
)


def clean_math_string(text: str) -> str:
    """ฟังก์ชันสำหรับเคลียร์พวกฟอร์แมต LaTeX ให้เหลืออักขระคณิตศาสตร์พื้นฐาน เพื่อเปรียบเทียบง่ายขึ้น"""
    if not text:
        return ""
    text = str(text).strip()

    # แปลงฟอร์แมตเศษส่วน LaTeX เช่น \frac{1}{11} หรือ \dfrac{1}{11} ให้เป็น 1/11
    text = re.sub(r'\\(?:dfrac|frac)\{([^}]+)\}\{([^}]+)\}', r'\1/\2', text)

    # ตัด \[ \] และ \( \) delimiters (บาง model ใช้แทน $$)
    text = re.sub(r'\\\[|\\\]|\\\(|\\\)', '', text)

    # เคลียร์ฟอร์แมตสัญลักษณ์พิเศษของ LaTeX และช่องว่างให้เหลือน้อยที่สุด
    text = text.lower()
    for char in [" ", "$", "{", "}", "\\", "[", "]", "boxed", "displaystyle"]:
        text = text.replace(char, "")
    return text.strip()


def strip_think_blocks(text: str) -> str:
    """ตัด <think>...</think> ออกจาก output ของ thinking models เช่น Qwen"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def check_correctness(model_ans: str, expected: str) -> int:
    try:
        # 0. ตัด <think> block ออกก่อน (สำหรับ Qwen และ thinking models)
        model_ans = strip_think_blocks(model_ans)

        # 1. ตัดเอาเฉพาะส่วนสรุปคำตอบข้อ 5
        if "5. สรุปคำตอบ" in model_ans:
            final_section = model_ans.split("5. สรุปคำตอบ")[-1]
        else:
            final_section = model_ans

        # ทำความสะอาดข้อมูลทั้งสองฝั่งด้วยระบบจัดการ LaTeX
        clean_expected = clean_math_string(expected)
        clean_final = clean_math_string(final_section)

        # 2. ตรวจสอบเงื่อนไขหากเฉลยเป็น "ตัวเลข จำนวนเต็ม ทศนิยม หรือเศษส่วนพื้นฐาน"
        if re.match(r'^[-+]?\d*\.?\d+(?:/\d+)?$', clean_expected):
            # สกัดตัวเลข/เศษส่วนทั้งหมดที่อยู่ในคำตอบโมเดลออกมาเป็น Token เพื่อเช็ครายตัว
            # ป้องกันปัญหา False Positive เช่น เฉลย 3 แต่โมเดลตอบ 13 หรือ 0.3 แล้วระบบมองว่าถูก
            tokens = re.findall(r'[-+]?\d*\.?\d+(?:/\d+)?', clean_final)

            if clean_expected in tokens or clean_expected == clean_final:
                return 1
            return 0

        else:
            # 3. หากยังไม่ตรง หรือเป็นพจน์/สมการซับซ้อน ส่งให้ LLM ตรวจสอบความสมมูล
            prompt = f"""คุณคือผู้ช่วยตรวจข้อสอบคณิตศาสตร์ (Math Grader) ที่มีความละเอียดและแม่นยำสูง
จงตรวจสอบว่า "คำตอบของนักเรียน" มีค่าเท่ากันหรือสมมูลทางคณิตศาสตร์กับ "เฉลยที่ถูกต้อง" หรือไม่ 
(ระวัง: นักเรียนอาจสลับที่พจน์ หรือใช้ฟอร์แมต LaTeX ต่างกัน แต่ถ้าจัดรูปแล้วมีค่าเท่ากัน ถือว่าถูกต้อง)

เฉลยที่ถูกต้อง: {expected}
คำตอบของนักเรียน: {final_section}

กฎการให้คะแนน:
- หากคำตอบถูกต้องหรือมีความหมายเดียวกัน ให้ตอบ "1" (หรือ TRUE)
- หากคำตอบไม่ถูกต้อง ให้ตอบ "0" (หรือ FALSE)

ข้อบังคับ: ตอบเป็นตัวเลข "1" หรือ "0" เพียงตัวเดียวเท่านั้น ห้ามมีคำอธิบายใดๆ ทั้งสิ้น"""

            result_content = judge_llm.invoke(prompt).content
            result = str(result_content).strip().upper()

            if "1" in result or "TRUE" in result:
                return 1
            return 0

    except Exception as e_eval:
        print(f"  [Grader Error]: {e_eval}")
        return 0


def run_evaluation():
    input_file = "dataset-math-tutor-15.csv"
    output_file = "results_evaluated.csv"

    try:
        # ใช้ cast() เพื่อยืนยันกับ IDE ว่านี่คือ DataFrame 100%
        df = cast(pd.DataFrame, pd.read_csv(input_file))
    except FileNotFoundError:
        print(f"ไม่พบไฟล์ {input_file} กรุณาตรวจสอบให้แน่ใจว่าวางไฟล์ไว้ถูกที่")
        return

    if not os.path.exists(output_file):
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "category", "question", "expected", "wolfram_raw",
                "llama_ans", "gem_ans", "qwen_ans",
                "llama_score", "gem_score", "qwen_score"
            ])

    processed_ids = set()
    if os.path.exists(output_file):
        try:
            processed_df = cast(pd.DataFrame, pd.read_csv(output_file))
            processed_ids = set(processed_df['id'].tolist())
        except pd.errors.EmptyDataError:
            pass

    for index, row in tqdm(df.iterrows(), total=len(df.index), desc="กำลังประเมินผล AI"):
        q_id = row['id']

        if q_id in processed_ids:
            continue

        category = row['category']
        question = row['question']
        expected = str(row['expected_answer'])

        try:
            w_query = translate_to_wolfram(question)
            wolfram_data = ask_wolfram(w_query)

            wolfram_raw = wolfram_data.get("raw", expected) if isinstance(wolfram_data, dict) else expected

            # Truncate wolfram_raw เพื่อป้องกัน prompt เกิน context limit ของ Groq
            # ตัด image URL และบรรทัดที่ไม่จำเป็นออกก่อน แล้วจำกัดความยาว
            wolfram_lines = [
                line for line in wolfram_raw.splitlines()
                if not line.strip().startswith("image:") and not line.strip().startswith("Wolfram Language code:")
            ]
            wolfram_trimmed = "\n".join(wolfram_lines).strip()
            if len(wolfram_trimmed) > 2000:
                wolfram_trimmed = wolfram_trimmed[:2000] + "\n...(truncated)"

            ans_llama = explain(question, wolfram_trimmed, "llama")
            ans_openai = explain(question, wolfram_trimmed, "gemini")
            ans_qwen = explain(question, wolfram_trimmed, "qwen")

            score_llama = check_correctness(ans_llama, expected)
            score_openai = check_correctness(ans_openai, expected)
            score_qwen = check_correctness(ans_qwen, expected)

            with open(output_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    q_id, category, question, expected, wolfram_raw,
                    ans_llama, ans_openai, ans_qwen,
                    score_llama, score_openai, score_qwen
                ])

            # หน่วงเวลาเล็กน้อยเพื่อป้องกันปัญหา Rate Limit ของ API (ปรับเปลี่ยนได้ตามความเหมาะสม)
            time.sleep(0.5)

        except Exception as e_api:
            import traceback
            print(f"\n[Error] ข้อที่ {q_id} มีปัญหาการเรียก API: {e_api}")
            traceback.print_exc()
            continue


if __name__ == "__main__":
    print("=== เริ่มการประเมินผล Math Tutor AI ===")
    run_evaluation()
    print("\nเสร็จสิ้นกระบวนการประเมินผลทั้งหมด!")

    # คำนวณ Accuracy โชว์บน Terminal
    # คำนวณ Accuracy โชว์บน Terminal
    try:
        # แก้ตรงนี้: ชื่อไฟล์ต้องเป็น "results_evaluated.csv" เท่านั้น
        df_result = cast(pd.DataFrame, pd.read_csv("results_evaluated.csv"))
        total_questions = len(df_result.index)

        if total_questions > 0:
            acc_llama = (df_result['llama_score'].sum() / total_questions) * 100
            acc_gemini = (df_result['gem_score'].sum() / total_questions)  * 100
            acc_qwen = (df_result['qwen_score'].sum() / total_questions) * 100

            print("\n=== 📊 สรุปผลความแม่นยำ (Accuracy) ===")
            print(f"จำนวนโจทย์ทั้งหมดที่รันเสร็จ: {total_questions} ข้อ")
            print(f"Llama 3.1 (8B)  : {acc_llama:.2f}%")
            print(f"Gemini 2.5 flash  : {acc_gemini:.2f}%")
            print(f"qwen-2.5-32b  : {acc_qwen:.2f}%")
            print("======================================")
    except Exception as e_calc:
        print(f"ไม่สามารถคำนวณ Accuracy ได้: {e_calc}")