import json
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlmodel import Session, select

from database import create_db, get_session
from models import ResponseVote
from services.wolfram import ask_wolfram
from services.llm import translate_to_wolfram, explain, models

load_dotenv()

# แทน on_event deprecated
@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db()
    yield

app = FastAPI(title="Math Tutor API", lifespan=lifespan)

# noinspection PyTypeChecker
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request/Response Models ---
class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    id: Optional[int]
    question: str
    wolfram_query: str
    wolfram_raw: Optional[str]
    images: List[str]
    llama_response: str
    deepseek_response: str
    qwen_response: str

class VoteRequest(BaseModel):
    response_id: int
    voted_model: str
    comment: Optional[str] = None

# --- Endpoints ---

@app.get("/")
def root():
    return {"status": "Math Tutor API running"}

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, db: Session = Depends(get_session)):
    # 1. แปลโจทย์
    wolfram_query = translate_to_wolfram(req.question)

    # 2. ถาม Wolfram
    wolfram_data = ask_wolfram(wolfram_query)
    images = wolfram_data["images"] if wolfram_data else []
    raw = wolfram_data["raw"] if wolfram_data else None
    wolfram_text = raw or "ไม่สามารถคำนวณได้"

    # 3. ถาม 3 models พร้อมกัน
    with ThreadPoolExecutor(max_workers=3) as executor:
        llama_future = executor.submit(explain, req.question, wolfram_text, "llama")
        deepseek_future = executor.submit(explain, req.question, wolfram_text, "deepseek")
        qwen_future = executor.submit(explain, req.question, wolfram_text, "qwen")

        llama_res = llama_future.result()
        deepseek_res = deepseek_future.result()
        qwen_res = qwen_future.result()

    # 4. บันทึกลง DB
    record = ResponseVote(
        question=req.question,
        wolfram_query=wolfram_query,
        wolfram_raw=raw,
        llama_response=llama_res,
        deepseek_response=deepseek_res,
        qwen_response=qwen_res,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return AskResponse(
        id=record.id,
        question=req.question,
        wolfram_query=wolfram_query,
        wolfram_raw=raw,
        images=images,
        llama_response=llama_res,
        deepseek_response=deepseek_res,
        qwen_response=qwen_res,
    )

@app.post("/ask/stream")
async def ask_stream(req: AskRequest):
    # 1. แปลโจทย์ + Wolfram
    wolfram_query = translate_to_wolfram(req.question)
    wolfram_data = ask_wolfram(wolfram_query)
    raw = wolfram_data["raw"] if wolfram_data else "ไม่สามารถคำนวณได้"

    async def generate():
        yield f"data: {json.dumps({'type': 'wolfram', 'content': raw})}\n\n"

        for model_name in ["llama", "deepseek", "qwen"]:
            yield f"data: {json.dumps({'type': 'start', 'model': model_name})}\n\n"

            llm = models[model_name]
            async for chunk in llm.astream(f"""
คุณคือติวเตอร์แคลคูลัส 1
โจทย์: {req.question}
Wolfram: {raw}
อธิบาย step-by-step ภาษาไทย
"""):
                yield f"data: {json.dumps({'type': 'chunk', 'model': model_name, 'content': chunk.content})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'model': model_name})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/vote")
def vote(req: VoteRequest, db: Session = Depends(get_session)):
    record = db.get(ResponseVote, req.response_id)
    if not record:
        return {"error": "ไม่พบข้อมูล"}
    record.voted_model = req.voted_model
    record.comment = req.comment
    db.commit()
    return {"status": "บันทึกโหวตสำเร็จ"}

@app.get("/results")
def results(db: Session = Depends(get_session)):
    records = db.exec(select(ResponseVote)).all()
    return records