from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional
from datetime import datetime, timezone

sqlite_url = "sqlite:///./analysis.db"
engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})

class Analysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: Optional[str] = Field(default=None, index=True)
    filename: str
    query: str
    file_path: str
    status: str = "queued"
    analysis_text: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

def init_db():
    SQLModel.metadata.create_all(engine)

def save_new(job_id: str, filename: str, query: str, file_path: str):
    with Session(engine) as s:
        rec = Analysis(job_id=job_id, filename=filename, query=query, file_path=file_path)
        s.add(rec)
        s.commit()
        s.refresh(rec)
        return rec.id

def update_result(job_id: str, analysis_text: str, status: str = "finished"):
    with Session(engine) as s:
        rec = s.exec(select(Analysis).where(Analysis.job_id == job_id)).first()
        if rec:
            rec.analysis_text = analysis_text
            rec.status = status
            rec.updated_at = datetime.now(timezone.utc)
            s.add(rec)
            s.commit()

def get_by_job(job_id: str):
    with Session(engine) as s:
        return s.exec(select(Analysis).where(Analysis.job_id == job_id)).first()