from fastapi import APIRouter
from backend.db import engine
from sqlalchemy import text
from pydantic import BaseModel
from fastapi import Depends

from backend.routes.auth_routes import (
    get_current_user,
    oauth2_scheme
)

router = APIRouter()

class CommentCreate(BaseModel):
    issue_id: int
    comment: str

@router.post("/comments")
def add_comment(
    data: CommentCreate,
    token: str = Depends(oauth2_scheme)
):

    user = get_current_user(token)

    with engine.connect() as connection:

        connection.execute(
            text("""
                INSERT INTO comments
                (issue_id, user_id, comment)

                VALUES
                (:issue_id, :user_id, :comment)
            """),
            {
                "issue_id": data.issue_id,
                "user_id": user["user_id"],
                "comment": data.comment
            }
        )

        connection.commit()

        return {
            "message": "Comment added"
        }
    

@router.get("/comments/{issue_id}")
def get_comments(issue_id: int):

    with engine.connect() as connection:

        result = connection.execute(
            text("""

                SELECT
                    comments.id,
                    comments.comment,
                    comments.user_id,
                    comments.created_at,
                    users.name

                FROM comments

                JOIN users
                ON comments.user_id = users.id

                WHERE comments.issue_id = :issue_id
            """),
            {
                "issue_id": issue_id
            }
        )

        comments = []

        for row in result.mappings():

            comments.append({
                "id": row["id"],
                "comment": row["comment"],
                "name": row["name"],
                "created_at": str(row["created_at"])
            })

        return comments