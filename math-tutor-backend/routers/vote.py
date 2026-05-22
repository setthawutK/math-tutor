from fastapi import APIRouter
from pydantic import BaseModel
from database import db
from datetime import datetime, timezone

router = APIRouter()

class VoteRequest(BaseModel):
    tutor_label: str  # เช่น "tutor_1", "tutor_2", "tutor_3"
    question: str     # โจทย์ที่ถาม

@router.post("/vote")
async def vote(body: VoteRequest):
    doc_ref = db.collection("votes").document()
    doc_ref.set({
        "tutor_label": body.tutor_label,
        "question": body.question,
        "voted_at": datetime.now(timezone.utc),
    })
    return {"status": "ok"}

@router.get("/votes/summary")
async def get_summary():
    docs = db.collection("votes").stream()
    summary = {"tutor_1": 0, "tutor_2": 0, "tutor_3": 0}
    for doc in docs:
        label = doc.to_dict().get("tutor_label")
        if label in summary:
            summary[label] += 1
    return summary