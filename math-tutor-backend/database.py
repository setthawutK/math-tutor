import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

load_dotenv()  # เพิ่มตรงนี้

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mathtutor.db")
engine = create_engine(DATABASE_URL)

def create_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session