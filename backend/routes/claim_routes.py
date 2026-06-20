from fastapi import APIRouter
from backend.db import engine
from sqlalchemy import text
from pydantic import BaseModel
from fastapi import Depends
from fastapi import UploadFile, File
import shutil
import cloudinary.uploader
from backend.cloudinary_config import *

from backend.routes.auth_routes import (
    get_current_user
)

router = APIRouter()

class ClaimCreate(BaseModel):
    issue_id: int


@router.post("/claim")
def claim_issue(
    data: ClaimCreate,
    user = Depends(get_current_user)
):

    with engine.connect() as connection:

        existing_claim = connection.execute(
            text("""
                SELECT * FROM claims
                WHERE issue_id = :issue_id
                """),
                {
                    "issue_id": data.issue_id
                }
        )

        claim_found = existing_claim.mappings().first()

        if claim_found:
            return{
                "message": "issue already claimed"
            }
        
        connection.execute(
            text("""
                INSERT INTO claims
                (issue_id, claimed_by, deadline)
                VALUES
                (
                    :issue_id,
                    :claimed_by,
                    NOW() + INTERVAL '3 days'
                )
                """),
                {
                    "issue_id": data.issue_id,
                    "claimed_by": user["user_id"]
                }
        )

        connection.execute(
            text("""
                    UPDATE issues
                    SET status = 'in_progress'
                    WHERE id = :issue_id
                """),
                {
                    "issue_id": data.issue_id
                }
        )

        connection.commit()

        return{
            "message": "Issue claimed successfully"
        }
    

@router.get("/claims/{issue_id}")
def get_claim(issue_id: int):

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT
                    claims.claimed_by,
                    claims.deadline,
                    claims.status,
                    claims.proof_image_url,
                    users.name

                FROM claims

                JOIN users
                ON claims.claimed_by = users.id

                WHERE issue_id = :issue_id
            """),
            {
                "issue_id": issue_id
            }
        )

        claim = result.mappings().first()

        if claim is None:
            return {
                "message": "No claim found"
            }

        return {
            "claimed_by": claim["name"],
            "deadline": str(claim["deadline"]),
            "status": claim["status"],
            "proof_image_url": claim["proof_image_url"]
        }
    
@router.post("/upload-proof")
def upload_proof(
    issue_id: int,
    file: UploadFile = File(...),
    user = Depends(get_current_user)
):

    with engine.connect() as connection:

        claim = connection.execute(
            text("""
                SELECT claimed_by
                FROM claims
                WHERE issue_id = :issue_id
            """),
            {
                "issue_id": issue_id
            }
        ).mappings().first()

        if not claim:
            return {
                "message": "Claim not found"
            }

        if claim["claimed_by"] != user["user_id"]:
            return {
                "message": "Only claimer can upload proof"
            }

        result = cloudinary.uploader.upload(
            file.file
        )

        connection.execute(
            text("""
                UPDATE claims
                SET proof_image_url = :proof_image_url
                WHERE issue_id = :issue_id
            """),
            {
                "proof_image_url": result["secure_url"],
                "issue_id": issue_id
            }
        )

        connection.commit()

        return {
    "proof_image_url": result["secure_url"]
    }

@router.delete("/delete-proof/{issue_id}")
def delete_proof(
    issue_id: int,
    user = Depends(get_current_user)
):

    with engine.connect() as connection:

        claim = connection.execute(
            text("""
                SELECT claimed_by
                FROM claims
                WHERE issue_id = :issue_id
            """),
            {
                "issue_id": issue_id
            }
        ).mappings().first()

        if not claim:
            return {
                "message": "Claim not found"
            }

        if claim["claimed_by"] != user["user_id"]:
            return {
                "message": "Only claimer can delete proof"
            }

        connection.execute(
            text("""
                UPDATE claims
                SET proof_image_url = NULL
                WHERE issue_id = :issue_id
            """),
            {
                "issue_id": issue_id
            }
        )

        connection.commit()

    return {
        "message": "Proof deleted"
    }

@router.get("/top-contributors")
def top_contributors():

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT
                    users.name,
                    COUNT(*) as resolved_count

                FROM claims

                JOIN users
                ON claims.claimed_by = users.id

                WHERE claims.status = 'resolved'

                GROUP BY users.id, users.name

                ORDER BY resolved_count DESC

                LIMIT 3
            """)
        )

        return result.mappings().all()
    

@router.get("/leaderboard")
def leaderboard():

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT
                    users.name,
                    COUNT(*) as issues_solved,
                    COUNT(*) * 50 as points

                FROM claims

                JOIN users
                ON claims.claimed_by = users.id

                WHERE claims.status = 'resolved'

                GROUP BY users.id, users.name

                ORDER BY points DESC
            """)
        )

        return result.mappings().all()
    
@router.get("/resolved-issues")
def get_resolved_issues(sort: str = "newest"):

    if sort == "trending":

        query = """
            SELECT *
            FROM issues
            WHERE status = 'resolved'
            ORDER BY upvotes DESC
        """

    elif sort == "oldest":

        query = """
            SELECT *
            FROM issues
            WHERE status = 'resolved'
            ORDER BY created_at ASC
        """

    else:

        query = """
            SELECT *
            FROM issues
            WHERE status = 'resolved'
            ORDER BY created_at DESC
        """

    with engine.connect() as connection:

        result = connection.execute(
            text(query)
        )

        return result.mappings().all()
    
@router.get("/pending-verification")
def pending_verification(
    user = Depends(get_current_user)
):

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT
                    issues.id,
                    issues.title,
                    users.name,
                    claims.proof_image_url

                FROM claims

                JOIN issues
                ON claims.issue_id = issues.id

                JOIN users
                ON claims.claimed_by = users.id

                WHERE claims.proof_image_url IS NOT NULL
                AND claims.status != 'resolved'

                AND issues.id NOT IN (

                    SELECT issue_id
                    FROM verification_votes
                    WHERE user_id = :user_id

                )

                ORDER BY claims.id DESC

                LIMIT 5
            """),
            {
                "user_id": user["user_id"]
            }
        )

        return result.mappings().all()