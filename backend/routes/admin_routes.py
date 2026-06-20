from fastapi import APIRouter, Depends, HTTPException
from backend.db import engine
from sqlalchemy import text
from backend.routes.auth_routes import get_current_user

router = APIRouter(prefix="/admin")

# ─── SIMPLE ADMIN CHECK ────────────────────────────────────────────────────
# Add is_admin column to users table:
# ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
# UPDATE users SET is_admin = TRUE WHERE email = 'admin@campus.edu';

ADMIN_EMAIL = "sawantvinay289@gmail.com"  # Change to your admin email

def require_admin(user=Depends(get_current_user)):
    if user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ─── DELETE ISSUE ──────────────────────────────────────────────────────────
@router.delete("/delete-issue/{issue_id}")
def delete_issue(issue_id: int, admin=Depends(require_admin)):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM comments WHERE issue_id = :id"), {"id": issue_id})
        conn.execute(text("DELETE FROM votes WHERE issue_id = :id"), {"id": issue_id})
        conn.execute(text("DELETE FROM claims WHERE issue_id = :id"), {"id": issue_id})
        conn.execute(text("DELETE FROM verification_votes WHERE issue_id = :id"), {"id": issue_id})
        conn.execute(text("DELETE FROM issue_reports WHERE issue_id = :id"), {"id": issue_id})
        conn.execute(text("DELETE FROM issues WHERE id = :id"), {"id": issue_id})
        conn.commit()
    return {"message": f"Issue #{issue_id} deleted successfully"}


# ─── DELETE COMMENT ────────────────────────────────────────────────────────
@router.delete("/delete-comment/{comment_id}")
def delete_comment(comment_id: int, admin=Depends(require_admin)):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM comment_reports WHERE comment_id = :id"), {"id": comment_id})
        conn.execute(text("DELETE FROM comments WHERE id = :id"), {"id": comment_id})
        conn.commit()
    return {"message": f"Comment #{comment_id} deleted successfully"}


# ─── DELETE USER ───────────────────────────────────────────────────────────
@router.delete("/delete-user/{user_id}")
def delete_user(user_id: int, admin=Depends(require_admin)):
    with engine.connect() as conn:
        # Delete user's activity first
        conn.execute(text("DELETE FROM votes WHERE user_id = :id"), {"id": user_id})
        conn.execute(text("DELETE FROM comments WHERE user_id = :id"), {"id": user_id})
        conn.execute(text("DELETE FROM claims WHERE claimed_by = :id"), {"id": user_id})
        conn.execute(text("DELETE FROM verification_votes WHERE user_id = :id"), {"id": user_id})
        conn.execute(text("DELETE FROM issue_reports WHERE reported_by = :id"), {"id": user_id})
        conn.execute(text("DELETE FROM comment_reports WHERE reported_by = :id"), {"id": user_id})
        conn.execute(text("DELETE FROM issues WHERE created_by = :id"), {"id": user_id})
        conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        conn.commit()
    return {"message": f"User #{user_id} deleted successfully"}


# ─── BAN USER ──────────────────────────────────────────────────────────────
# Requires: ALTER TABLE users ADD COLUMN banned BOOLEAN DEFAULT FALSE;
@router.post("/ban-user/{user_id}")
def ban_user(user_id: int, admin=Depends(require_admin)):
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE users SET banned = TRUE WHERE id = :id"),
            {"id": user_id}
        )
        conn.commit()
    return {"message": f"User #{user_id} has been banned"}


@router.post("/unban-user/{user_id}")
def unban_user(user_id: int, admin=Depends(require_admin)):
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE users SET banned = FALSE WHERE id = :id"),
            {"id": user_id}
        )
        conn.commit()
    return {"message": f"User #{user_id} has been unbanned"}


# ─── GET REPORTED ISSUES ───────────────────────────────────────────────────
@router.get("/issue-reports")
def get_issue_reports(admin=Depends(require_admin)):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                issue_reports.*,
                issues.title as issue_title,
                users.name as reporter_name
            FROM issue_reports
            LEFT JOIN issues
                ON issue_reports.issue_id = issues.id
            LEFT JOIN users
                ON issue_reports.reported_by = users.id
            ORDER BY issue_reports.id DESC
        """))
        rows = result.mappings().all()
        return [dict(r) for r in rows]


# ─── GET REPORTED COMMENTS ─────────────────────────────────────────────────
@router.get("/comment-reports")
def get_comment_reports(admin=Depends(require_admin)):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                comment_reports.*,
                comments.comment AS comment_text,
                comments.issue_id,
                users.name AS reporter_name
            FROM comment_reports
            LEFT JOIN comments
                ON comment_reports.comment_id = comments.id
            LEFT JOIN users
                ON comment_reports.reported_by = users.id
            ORDER BY comment_reports.id DESC
        """))

        rows = result.mappings().all()
        return [dict(r) for r in rows]


# ─── DISMISS REPORT ────────────────────────────────────────────────────────
@router.delete("/dismiss-report/issue/{report_id}")
def dismiss_issue_report(report_id: int, admin=Depends(require_admin)):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM issue_reports WHERE id = :id"), {"id": report_id})
        conn.commit()
    return {"message": "Report dismissed"}


@router.delete("/dismiss-report/comment/{report_id}")
def dismiss_comment_report(report_id: int, admin=Depends(require_admin)):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM comment_reports WHERE id = :id"), {"id": report_id})
        conn.commit()
    return {"message": "Report dismissed"}