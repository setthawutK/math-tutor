from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
from sqlmodel import Session, select
from concurrent.futures import ThreadPoolExecutor
from database import create_db, get_session
from models import ResponseVote
from services.wolfram import ask_wolfram
from services.llm import translate_to_wolfram, explain

load_dotenv()

app = FastAPI(title="Math Tutor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    create_db()

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

@app.get("/")
def root():
    return {"status": "Math Tutor API running"}

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, session: Session = Depends(get_session)):
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
    session.add(record)
    session.commit()
    session.refresh(record)

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

@app.post("/vote")
def vote(req: VoteRequest, session: Session = Depends(get_session)):
    record = session.get(ResponseVote, req.response_id)
    if not record:
        return {"error": "ไม่พบข้อมูล"}
    record.voted_model = req.voted_model
    record.comment = req.comment
    session.commit()
    return {"status": "บันทึกโหวตสำเร็จ"}

@app.get("/results")
def results(session: Session = Depends(get_session)):
    records = session.exec(select(ResponseVote)).all()
    return records