from fastapi import APIRouter, Depends
from backend.db import engine
from sqlalchemy import text
from backend.routes.auth_routes import get_current_user, oauth2_scheme
from pydantic import BaseModel

router = APIRouter()

class ProfileUpdate(BaseModel):
    phone: str
    department: str
    year: str
    role: str
    group_name: str
    bio: str

@router.put("/update-profile")
def update_profile(
    profile: ProfileUpdate,
    token: str = Depends(oauth2_scheme)
):
    
    user = get_current_user(token)

    with engine.connect() as conn:

        conn.execute(
            text("""
                UPDATE users
                SET
                    phone = :phone,
                    department = :department,
                    year = :year,
                    role = :role,
                    group_name = :group_name,
                    bio = :bio
                WHERE id = :user_id
            """),
            {
                "phone": profile.phone,
                "department": profile.department,
                "year": profile.year,
                "role": profile.role,
                "group_name": profile.group_name,
                "bio": profile.bio,
                "user_id": user["user_id"]
            }
        )

        conn.commit()

    return {
        "message": "Profile updated successfully"
    }

@router.get("/me")
def get_me(token: str = Depends(oauth2_scheme)):
    user = get_current_user(token)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT
                id,
                name,
                email,
                phone,
                department,
                year,
                role,
                group_name,
                bio
            FROM users
            WHERE id = :id
        """),
            {"id": user["user_id"]}
        )
        row = result.mappings().first()
        if not row:
            return {"message": "User not found"}
        return {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "phone": row["phone"],
            "department": row["department"],
            "year": row["year"],
            "role": row["role"],
            "group_name": row["group_name"],
            "bio": row["bio"]
        }

@router.get("/my-issues")
def get_my_issues(token: str = Depends(oauth2_scheme)):
    user = get_current_user(token)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT issues.*,
                (SELECT COUNT(*) FROM comments WHERE comments.issue_id = issues.id) AS comment_count
                FROM issues
                WHERE created_by = :user_id
                ORDER BY created_at DESC
            """),
            {"user_id": user["user_id"]}
        )
        issues = []
        for row in result.mappings():
            issues.append({
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "category": row["category"],
                "location": row["location"],
                "status": row["status"],
                "upvotes": row["upvotes"],
                "comment_count": row["comment_count"],
                "created_at": str(row["created_at"])
            })
        return issues