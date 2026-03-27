from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from services.wolfram import ask_wolfram
from services.llm import translate_to_wolfram, explain
from langchain.memory import ConversationBufferMemory
from typing import Optional, List

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# เก็บ memory แยกตาม session
sessions = {}

def get_memory(session_id: str) -> ConversationBufferMemory:
    if session_id not in sessions:
        sessions[session_id] = ConversationBufferMemory()
    return sessions[session_id]

# Request/Response models
class AskRequest(BaseModel):
    session_id: str
    question: str
    model: str = "llama"  # default llama

class AskResponse(BaseModel):
    explanation: str
    images: list[str]
    wolfram_raw: Optional[str]

# --- Endpoints ---

@app.get("/")
def root():
    return {"status": "Math Tutor API running"}

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    memory = get_memory(req.session_id)
    
    # 1. แปลโจทย์
    wolfram_query = translate_to_wolfram(req.question)
    
    # 2. ถาม Wolfram
    wolfram_data = ask_wolfram(wolfram_query)
    
    # 3. อธิบาย
    if wolfram_data is None:
        explanation = "ไม่สามารถคำนวณได้ กรุณาลองพิมพ์โจทย์ใหม่ให้ชัดขึ้น"
        images = []
        raw = None
    else:
        # เพิ่ม context จาก memory
        history = memory.buffer if memory.buffer else ""
        explanation = explain(
            thai_query=req.question,
            wolfram_result=wolfram_data["raw"],
            model_name=req.model,
            history=history
        )
        images = wolfram_data["images"]
        raw = wolfram_data["raw"]
    
    # 4. บันทึก memory
    memory.chat_memory.add_user_message(req.question)
    memory.chat_memory.add_ai_message(explanation)
    
    return AskResponse(
        explanation=explanation,
        images=images,
        wolfram_raw=raw
    )

@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "cleared"}