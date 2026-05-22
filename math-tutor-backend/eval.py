import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import csv
import re
import time
from tqdm import tqdm
from typing import cast
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from services.llm import translate_to_wolfram, explain
from services.wolfram import ask_wolfram

judge_llm = ChatOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=SecretStr(os.getenv("GROQ_KAFA_KEY", "")),
    model="llama-3.1-8b-instant",
    temperature=0
)


def clean_math_string(text: str) -> str:
    if not text:
        return ""
    text = str(text).strip()

    def replace_frac(m):
        return f"{m.group(1)}/{m.group(2)}"

    for _ in range(10):
        new_text = re.sub(r'\\(?:dfrac|frac)\{([^{}]+)\}\{([^{}]+)\}', replace_frac, text)
        if new_text == text:
            break
        text = new_text

    text = re.sub(r'\\\[|\\\]|\\\(|\\\)', '', text)
    text = text.lower()
    for char in [" ", "$", "{", "}", "\\", "[", "]", "boxed", "displaystyle"]:
        text = text.replace(char, "")
    return text.strip()


def strip_think_blocks(text: str) -> str:
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def extract_boxed(text: str):
    idx = text.find(r'\boxed{')
    if idx == -1:
        return None
    start = idx + len(r'\boxed{')
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
        i += 1
    return text[start:i-1] if depth == 0 else None


def check_correctness(model_ans: str, expected: str) -> int:
    try:
        if not model_ans or str(model_ans).strip() == "" or str(model_ans).strip().upper() == "NULL":
            return 0

        model_ans = strip_think_blocks(model_ans)

        boxed_content = extract_boxed(model_ans)
        if boxed_content:
            final_section = boxed_content.strip()
        elif "5. สรุปคำตอบ" in model_ans:
            final_section = model_ans.split("5. สรุปคำตอบ")[-1].strip()
        else:
            final_section = model_ans.strip()

        if not final_section:
            return 0

        clean_expected = clean_math_string(expected)
        clean_final    = clean_math_string(final_section)

        print(f"  expected     : {expected[:80]}")
        print(f"  final        : {final_section[:80]}")
        print(f"  clean_exp    : {clean_expected}")
        print(f"  clean_fin    : {clean_final}")

        if clean_expected and re.match(r'^[-+]?\d*\.?\d+(?:/\d+)?$', clean_expected):
            if not re.search(r'[a-z]', clean_final):
                tokens = re.findall(r'[-+]?\d*\.?\d+(?:/\d+)?', clean_final)
                score = 1 if (clean_expected in tokens or clean_expected == clean_final) else 0
                print(f"  → regex score: {score}")
                return score

        prompt = f"""คุณคือผู้ช่วยตรวจข้อสอบคณิตศาสตร์ (Math Grader) ที่มีความละเอียดและแม่นยำสูง
จงตรวจสอบว่า "คำตอบของนักเรียน" มีค่าเท่ากันหรือสมมูลทางคณิตศาสตร์กับ "เฉลยที่ถูกต้อง" หรือไม่

หมายเหตุสำคัญ:
- log(x) และ ln(x) ถือว่าเท่ากันในบริบทแคลคูลัส
- 2^(-x) เท่ากับ 1/2^x
- a(1-b) เท่ากับ -a(b-1)
- ln(4) = 2*ln(2) ดังนั้น 4^x/(2*ln(2)) เท่ากับ 4^x/ln(4)
- ln|x| และ ln(x) ถือว่าเท่ากันในบริบทนี้
- ค่าคงที่ C และ c ถือว่าเท่ากัน
- การสลับลำดับการคูณถือว่าถูกต้อง
- รูปแบบ LaTeX ที่ต่างกันแต่มีค่าเท่ากัน ถือว่าถูกต้อง
- \\frac{{1}}{{11}} เท่ากับ 1/11

เฉลยที่ถูกต้อง: {expected}
คำตอบของนักเรียน: {final_section}

กฎการให้คะแนน:
- หากคำตอบถูกต้องหรือสมมูลกันทางคณิตศาสตร์ ให้ตอบ "1"
- หากคำตอบไม่ถูกต้อง ให้ตอบ "0"
- ถ้าคำตอบของนักเรียนไม่สมบูรณ์หรือถูกตัดกลางคัน ให้ตอบ "0" เสมอ

ข้อบังคับ: ตอบเป็นตัวเลข "1" หรือ "0" เพียงตัวเดียวเท่านั้น ห้ามมีคำอธิบายใดๆ"""

        result_content = judge_llm.invoke(prompt).content
        result = str(result_content).strip().upper()
        match = re.search(r'\b(0|1)\b', result)
        score = int(match.group(1)) if match else 0
        print(f"  → LLM score  : {score}")
        return score

    except Exception as e_eval:
        print(f"  [Grader Error]: {e_eval}")
        return 0


def run_evaluation():
    input_file = "dataset-math-tutor.csv"
    output_file = "results_evaluated.csv"

    try:
        df = cast(pd.DataFrame, pd.read_csv(input_file))
    except FileNotFoundError:
        print(f"ไม่พบไฟล์ {input_file}")
        return

    if not os.path.exists(output_file):
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "category", "question", "expected", "wolfram_raw",
                "llama_ans", "gemini_ans", "qwen_ans",
                "llama_score", "gemini_score", "qwen_score"
            ])

    processed_ids = set()
    if os.path.exists(output_file):
        try:
            processed_df = cast(pd.DataFrame, pd.read_csv(output_file))
            processed_ids = set(processed_df['id'].tolist())
        except pd.errors.EmptyDataError:
            pass

    for _, row in tqdm(df.iterrows(), total=len(df.index), desc="กำลังประเมินผล AI"):
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

            wolfram_lines = [
                line for line in wolfram_raw.splitlines()
                if not line.strip().startswith("image:") and not line.strip().startswith("Wolfram Language code:")
            ]
            wolfram_trimmed = "\n".join(wolfram_lines).strip()
            if len(wolfram_trimmed) > 2000:
                wolfram_trimmed = wolfram_trimmed[:2000] + "\n...(truncated)"

            ans_llama  = explain(question, wolfram_trimmed, "llama")
            ans_openai = explain(question, wolfram_trimmed, "openai")
            ans_qwen   = explain(question, wolfram_trimmed, "qwen")

            print(f"\n[Q{q_id}] {question[:60]}")
            print(f"  llama  : {ans_llama[:80] if ans_llama else 'NULL'}")
            print(f"  openai : {ans_openai[:80] if ans_openai else 'NULL'}")
            print(f"  qwen   : {ans_qwen[:80] if ans_qwen else 'NULL'}")

            score_llama  = check_correctness(ans_llama, expected)
            score_openai = check_correctness(ans_openai, expected)
            score_qwen   = check_correctness(ans_qwen, expected)

            with open(output_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    q_id, category, question, expected, wolfram_raw,
                    ans_llama, ans_openai, ans_qwen,
                    score_llama, score_openai, score_qwen
                ])

            time.sleep(0.5)

        except Exception as e_api:
            import traceback
            print(f"\n[Error] ข้อที่ {q_id}: {e_api}")
            traceback.print_exc()
            continue


if __name__ == "__main__":
    print("=== เริ่มการประเมินผล Math Tutor AI ===")
    run_evaluation()
    print("\nเสร็จสิ้นกระบวนการประเมินผลทั้งหมด!")

    try:
        df_result = cast(pd.DataFrame, pd.read_csv("results_evaluated.csv"))
        total = len(df_result.index)

        if total > 0:
            acc_llama  = (df_result['llama_score'].sum() / total) * 100
            acc_openai = (df_result['gemini_score'].sum() / total) * 100
            acc_qwen   = (df_result['qwen_score'].sum() / total) * 100

            print("\n=== สรุปผลความแม่นยำ (Accuracy) ===")
            print(f"จำนวนโจทย์: {total} ข้อ")
            print(f"Llama 3.1 8B     : {df_result['llama_score'].sum()}/{total} = {acc_llama:.2f}%")
            print(f"Gemini 2.5 Flash : {df_result['gemini_score'].sum()}/{total} = {acc_openai:.2f}%")
            print(f"Qwen3.6 Flash    : {df_result['qwen_score'].sum()}/{total} = {acc_qwen:.2f}%")
            print("=====================================")
    except Exception as e_calc:
        print(f"ไม่สามารถคำนวณ Accuracy ได้: {e_calc}")