import json
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from database import db
from models import AskRequest, AskResponse, VoteRequest
from services.wolfram import ask_wolfram
from services.llm import translate_to_wolfram, explain

load_dotenv()

@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield

app = FastAPI(title="Math Tutor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---

@app.get("/")
def root():
    return {"status": "Math Tutor API running"}

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    wolfram_query = translate_to_wolfram(req.question)

    wolfram_data = ask_wolfram(wolfram_query)
    images = wolfram_data["images"] if wolfram_data else []
    raw = wolfram_data["raw"] if wolfram_data else None
    wolfram_text = raw or "ไม่สามารถคำนวณได้"

    with ThreadPoolExecutor(max_workers=3) as executor:
        llama_future    = executor.submit(explain, req.question, wolfram_text, "llama")
        qwen_future     = executor.submit(explain, req.question, wolfram_text, "qwen")
        gemini_future = executor.submit(explain, req.question, wolfram_text, "gemini")

        gemini_res = gemini_future.result()
        llama_res    = llama_future.result()
        qwen_res     = qwen_future.result()



    now = datetime.now(timezone.utc)
    doc_ref = db.collection("responses").document()
    doc_ref.set({
        "question":          req.question,
        "wolfram_query":     wolfram_query,
        "wolfram_raw":       raw,
        "llama_response":    llama_res,
        "gemini_response": gemini_res,
        "qwen_response":     qwen_res,
        "voted_model":       None,
        "comment":           None,
        "created_at":        now,
    })

    return AskResponse(
        id=doc_ref.id,
        question=req.question,
        wolfram_query=wolfram_query,
        wolfram_raw=raw,
        images=images,
        llama_response=llama_res,
        gemini_response=gemini_res,
        qwen_response=qwen_res,
        created_at=now,
    )


def _is_not_math(text: str) -> bool:
    non_question_keywords = [
        "สวัสดี", "ขอบคุณ", "ดีจ้า", "หวัดดี", "เป็นยังไง",
        "hello", "hi", "hey", "thanks", "thank you", "bye",
    ]
    text_lower = text.lower().strip()
    if len(text_lower) < 3:
        return True
    if any(kw in text_lower for kw in non_question_keywords):
        return True
    return False


@app.post("/ask/stream")
async def ask_stream(req: AskRequest):
    print(f"[ask_stream] รับโจทย์: {req.question[:50]}")
    wolfram_query = translate_to_wolfram(req.question)
    print(f"[ask_stream] wolfram_query: {wolfram_query}")
    wolfram_data = ask_wolfram(wolfram_query)
    print(f"[ask_stream] wolfram_data is None: {wolfram_data is None}")
    raw = wolfram_data["raw"] if wolfram_data else "ไม่สามารถคำนวณได้"

    if not wolfram_query or wolfram_query.strip() == "" or _is_not_math(req.question):
        print(f"[ask_stream] → not_math branch")
        async def not_math():
            yield f"data: {json.dumps({'type': 'error', 'content': 'not_math'})}\n\n"
        return StreamingResponse(not_math(), media_type="text/event-stream")

    print(f"[ask_stream] → generate branch")

    async def generate():
        from services.llm import aexplain
        print(f"[generate] เริ่ม")
        try:
            now = datetime.now(timezone.utc)
            doc_ref = db.collection("responses").document()
            doc_ref.set({
                "question":   req.question,
                "wolfram_raw": raw,
                "voted_model": None,
                "created_at":  now,
            })

            print(f"✅ Saved to Firestore: {doc_ref.id}")
            yield f"data: {json.dumps({'type': 'response_id', 'content': doc_ref.id})}\n\n"

            images = wolfram_data.get('images', []) if wolfram_data else []
            print(f"[generate] images: {images}")
            yield f"data: {json.dumps({'type': 'wolfram_images', 'content': images})}\n\n"

            for model_name in ["llama", "gemini", "qwen"]:
                print(f"[stream] เริ่ม {model_name}")
                yield f"data: {json.dumps({'type': 'start', 'model': model_name})}\n\n"
                count = 0
                async for content in aexplain(req.question, raw, model_name):
                    safe_content = content.replace("\\", "\\\\")
                    count += 1
                    yield f"data: {json.dumps({'type': 'chunk', 'model': model_name, 'content': safe_content})}\n\n"
                print(f"[stream] จบ {model_name} chunks={count}")
                yield f"data: {json.dumps({'type': 'done', 'model': model_name})}\n\n"

        except Exception as e:
            print(f"[generate] ERROR: {e}")
            import traceback
            traceback.print_exc()

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/vote")
def vote(req: VoteRequest):
    doc_ref = db.collection("responses").document(req.response_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": "ไม่พบข้อมูล"}
    doc_ref.update({
        "voted_model": req.voted_model,
        "comment":     req.comment,
    })
    return {"status": "บันทึกโหวตสำเร็จ"}


@app.get("/results")
def results():
    docs = db.collection("responses")\
             .where("voted_model", "!=", None)\
             .stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]