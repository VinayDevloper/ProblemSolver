from fastapi import APIRouter
from backend.db import engine
from sqlalchemy import text
from pydantic import BaseModel
from fastapi import Depends
from fastapi import UploadFile, File
import shutil

from backend.routes.auth_routes import (
    get_current_user
)

router = APIRouter()

class IssueCreate(BaseModel):
    title: str 
    description: str 
    category: str 
    location: str 
    image_url: str | None = None


@router.post("/issues")
def create_issue(
    issue: IssueCreate,
    user = Depends(get_current_user)
):
    if issue.title.strip() == "":
        return {
            "message": "Title required"
        }

    if issue.description.strip() == "":
        return {
            "message": "Description required"
        }

    if issue.category.strip() == "":
        return {
            "message": "Category required"
        }

    if issue.location.strip() == "":
        return {
            "message": "Location required"
        }

    print(user)

    with engine.connect() as connection:
    
        connection.execute(
            text("""
                    INSERT INTO issues
                    (title, description, category, location, image_url, created_by)

                    VALUES
                    (:title, :description, :category, :location, :image_url, :created_by)
                """),

                {
                    "title": issue.title,
                    "description": issue.description,
                    "category": issue.category,
                    "location": issue.location,
                    "image_url": issue.image_url,
                    "created_by": user["user_id"]
                }
        )

        connection.commit()

        return {
            "message": "Issue create successfully"
        }
    

@router.get("/issues")
def get_issues(sort: str = "newest"):

    if sort == "trending":

        query = """
            SELECT
                issues.*,

                (
                    SELECT COUNT(*)
                    FROM comments
                    WHERE comments.issue_id = issues.id
                ) AS comment_count

            FROM issues

            ORDER BY upvotes DESC
        """

    elif sort == "oldest":

        query = """
        SELECT
            issues.*,

            (
                SELECT COUNT(*)
                FROM comments
                WHERE comments.issue_id = issues.id
            ) AS comment_count

        FROM issues

        ORDER BY created_at ASC
    """

    else:

        query = """
            SELECT
                issues.*,

                (
                    SELECT COUNT(*)
                    FROM comments
                    WHERE comments.issue_id = issues.id
                ) AS comment_count

            FROM issues

            ORDER BY created_at DESC
        """

    with engine.connect() as connection:

        result = connection.execute(
            text(query)
        )

        issues = []

        for row in result.mappings():

            issues.append({
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "category": row["category"],
                "location": row["location"],
                "image_url": row["image_url"],
                "status": row["status"],
                "upvotes": row["upvotes"],
                "comment_count": row["comment_count"],
                "created_by": row["created_by"],
                "created_at": str(row["created_at"])
            })

        return issues
    
@router.get("/issues/{issue_id}")
def get_single_issue(issue_id: int):

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT
                issues.*,
                users.name

                FROM issues

                JOIN users
                ON issues.created_by = users.id

                WHERE issues.id = :id
            """),
            {
                "id": issue_id
            }
        )

        issue = result.mappings().first()

        if issue is None:
            return {"message": "Issue not found"}

        return {
            "id": issue["id"],
            "title": issue["title"],
            "image_url": issue["image_url"],
            "description": issue["description"],
            "category": issue["category"],
            "location": issue["location"],
            "status": issue["status"],    
            "upvotes": issue["upvotes"],
            "created_by": issue["created_by"],
            "created_at": str(issue["created_at"]),
            "creator_name": issue["name"]
        }
    

    
@router.post("/upload")
def upload_image(
    file: UploadFile = File(...)
):
    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    return {
    "image_url": file_path
    }

@router.get("/trending-categories")
def trending_categories():

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT
                    category,
                    COUNT(*) as total

                FROM issues

                GROUP BY category

                ORDER BY total DESC

                LIMIT 5
            """)
        )

        return result.mappings().all()
