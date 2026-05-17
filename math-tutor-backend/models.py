from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone  # เพิ่มการ import timezone เข้ามา


class ResponseVote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    question: str
    wolfram_query: str
    wolfram_raw: Optional[str] = None
    llama_response: str
    deepseek_response: str
    qwen_response: str
    voted_model: Optional[str] = None
    comment: Optional[str] = None

    # แก้ไขบรรทัดนี้โดยใช้ lambda เพื่อเรียก datetime.now พร้อมระบุโซนเวลา UTC
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))