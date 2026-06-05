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
    file: UploadFile = File(...)
):
        file_path = f"uploads/proof_{issue_id}.jpg"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

        with engine.connect() as connection:

            connection.execute(
                text("""
                    UPDATE claims
                    SET proof_image_url = :proof_image_url
                    WHERE issue_id = :issue_id
                """),
                {
                    "proof_image_url": file_path,
                    "issue_id": issue_id
                }
            )

            connection.commit()

        return {
            "proof_image_url": file_path
        }

@router.delete("/delete-proof/{issue_id}")
def delete_proof(issue_id: int):

    with engine.connect() as connection:

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
