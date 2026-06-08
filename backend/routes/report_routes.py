from fastapi import APIRouter, Depends
from backend.db import engine
from sqlalchemy import text
from pydantic import BaseModel
from backend.routes.auth_routes import get_current_user

router = APIRouter()

class IssueReportCreate(BaseModel):
    issue_id: int
    reason: str

class CommentReportCreate(BaseModel):
    comment_id: int
    reason: str

@router.post("/report-issue")
def report_issue(data: IssueReportCreate, user=Depends(get_current_user)):
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO issue_reports (issue_id, reported_by, reason)
                VALUES (:issue_id, :reported_by, :reason)
            """),
            {"issue_id": data.issue_id, "reported_by": user["user_id"], "reason": data.reason}
        )
        conn.commit()
    return {"message": "Issue reported successfully"}

@router.post("/report-comment")
def report_comment(data: CommentReportCreate, user=Depends(get_current_user)):
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO comment_reports (comment_id, reported_by, reason)
                VALUES (:comment_id, :reported_by, :reason)
            """),
            {"comment_id": data.comment_id, "reported_by": user["user_id"], "reason": data.reason}
        )
        conn.commit()
    return {"message": "Comment reported successfully"}

@router.get("/test-report")
def test_report():
    return {"message": "Report route working"}