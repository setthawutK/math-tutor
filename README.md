# Math Tutor AI — Web Application for Mathematics Learning

> ระบบผู้ช่วยสอนคณิตศาสตร์สำหรับนักศึกษาวิศวกรรมปี 1 โดยบูรณาการ Wolfram Alpha เข้ากับแบบจำลองภาษาขนาดใหญ่ (LLMs) เพื่ออธิบายวิธีทำแบบ Step-by-Step ในภาษาไทย

---

## ภาพรวมของระบบ

โครงงานนี้พัฒนาเว็บแอปพลิเคชันแชทบอทคณิตศาสตร์ภายใต้แนวคิด **Hybrid Architecture** ที่แยกส่วนการคำนวณออกจากส่วนอธิบายอย่างชัดเจน โดย Wolfram Alpha ทำหน้าที่คำนวณเพื่อรับประกันความแม่นยำ และแบบจำลองภาษา (LLMs) ทำหน้าที่อธิบายวิธีทำเป็นภาษาที่นักศึกษาเข้าใจง่าย

---

## โครงสร้าง Repository

```
math-tutor/
├── math-tutor-backend/          # FastAPI Backend
│   ├── main.py                  # API endpoints (ask/stream, vote, results)
│   ├── database.py              # Firestore client
│   ├── models.py                # Pydantic models
│   │   
│   ├── services/
│   │   ├── llm.py               # LLM integration + Prompt Templates
│   │   └── wolfram.py           # Wolfram Alpha API
│   ├── Dockerfile
│   └── requirements.tx  
│   ├── eval.py                  # Evaluation script (Answer Accuracy)
│   ├── dataset-math-tutor.csv   # ชุดโจทย์ 30 ข้อ พร้อมเฉลย
│   └── results_evaluated.csv    # ผลลัพธ์การประเมินรายข้อ
│
├── math-tutor-webapp/           # Angular Frontend
│   ├── src/app/
│   │   └── chat-page/
│   │       ├── chat-page.ts     # Component logic (SSE streaming, vote)
│   │       └── chat-page.html   # UI (MathLive input, carousel, vote button)
│   └── package.json
│
│
└── README.md
```

---

## สถาปัตยกรรมระบบ

### Backend (Python / FastAPI)

| ไฟล์ | หน้าที่ |
|------|---------|
| `main.py` | REST API — `/ask/stream` (SSE), `/vote`, `/results` |
| `services/llm.py` | Prompt Template 1 (Few-shot แปลโจทย์) + Prompt Template 2 (Zero-shot + Plan-and-Solve) |
| `services/wolfram.py` | เรียก Wolfram Alpha LLM API |
| `database.py` | เชื่อมต่อ Cloud Firestore |

### Frontend (TypeScript / Angular)

| ไฟล์ | หน้าที่ |
|------|---------|
| `chat-page.ts` | รับโจทย์ → ส่ง SSE stream → รับ chunk → แสดงผล → โหวต |
| `chat-page.html` | MathLive input, Carousel แสดง 3 โมเดล, ปุ่มโหวต Blind Test |

### Evaluate

| ไฟล์ | หน้าที่ |
|------|---------|
| `eval.py` | ประเมิน Answer Accuracy ด้วย Regex และ LLM-based Evaluation |
| `dataset-math-tutor.csv` | ชุดโจทย์ครอบคลุม 3 หมวด ได้แก่ ลิมิต อนุพันธ์ และอินทิกรัล |
| `results_evaluated.csv` | คะแนนรายข้อของแต่ละโมเดล |

---


## Tech Stack

**Backend:** Python · FastAPI · LangChain · Wolfram Alpha API · Google Cloud Run · Cloud Firestore

**Frontend:** TypeScript · Angular · MathLive · ngx-markdown · KaTeX · Firebase Hosting

**LLMs:** Llama-3.1-8B (Groq) · Gemini-2.5-Flash (Google) · Qwen3.6-Flash (Alibaba)

---

## ผู้จัดทำ

| ชื่อ | รหัสนักศึกษา |
|------|------------|
| นางสาวอรุณฉัตร บุญยัง | 6652300109 |
| นายเสฎฐวุฒิ เบาวะนนท์ | 6652300923 |

**อาจารย์ที่ปรึกษา:** รศ.ดร.ปริญญา สงวนสัตย์ · ผศ.ดร.ติณณภพ ดินดำ

**สถาบันการจัดการปัญญาภิวัฒน์** · คณะวิศวกรรมศาสตร์และเทคโนโลยี · ปีการศึกษา 2568
