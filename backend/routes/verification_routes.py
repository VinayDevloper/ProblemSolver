from fastapi import APIRouter
from backend.db import engine
from sqlalchemy import text
from pydantic import BaseModel
from fastapi import Depends

from backend.routes.auth_routes import (
    get_current_user
)

router = APIRouter()


class VerificationCreate(BaseModel):
    issue_id: int
    status: str


@router.post("/verify")
def verify_issue(
    data: VerificationCreate,
    user=Depends(get_current_user)
):
    with engine.connect() as connection:

        allowed_statuses = [
            "solved",
            "partial",
            "not solved"
        ]

        if data.status not in allowed_statuses:

            return {
                "message": "Invalid verification status"
            }

        existing_verification = connection.execute(
            text("""
                SELECT *
                FROM verification_votes
                WHERE issue_id = :issue_id
                AND user_id = :user_id
            """),
            {
                "issue_id": data.issue_id,
                "user_id": user["user_id"]
            }
        )

        verification_found = (
            existing_verification
            .mappings()
            .first()
        )

        if verification_found:

            connection.execute(
                text("""
                    UPDATE verification_votes
                    SET status = :status
                    WHERE issue_id = :issue_id
                    AND user_id = :user_id
                """),
                {
                    "status": data.status,
                    "issue_id": data.issue_id,
                    "user_id": user["user_id"]
                }
            )

        else:
            connection.execute(
                text("""
                    INSERT INTO verification_votes
                    (
                        issue_id,
                        user_id,
                        status
                    )

                    VALUES
                    (
                        :issue_id,
                        :user_id,
                        :status
                    )
                """),
                {
                    "issue_id": data.issue_id,
                    "user_id": user["user_id"],
                    "status": data.status
                }
            )

    

        

        verification_result = connection.execute(
            text("""
                SELECT
                    status,
                    COUNT(*) as total

                FROM verification_votes

                WHERE issue_id = :issue_id

                GROUP BY status
            """),
            {
                "issue_id": data.issue_id
            }
        )

        solved = 0
        partial = 0
        not_solved = 0

        for row in verification_result.mappings():

            if row["status"] == "solved":
                solved = row["total"]

            elif row["status"] == "partial":
                partial = row["total"]

            elif row["status"] == "not solved":
                not_solved = row["total"]

        total_votes = (
            solved +
            partial +
            not_solved
        )

        if total_votes >= 5:

            solved_percentage = (
                solved / total_votes
            ) * 100

            if solved_percentage >= 60:

                connection.execute(
                    text("""
                        UPDATE claims
                        SET status = 'resolved'
                        WHERE issue_id = :issue_id
                    """),
                    {
                        "issue_id": data.issue_id
                    }
                )

                connection.execute(
                    text("""
                        UPDATE issues
                        SET status = 'resolved'
                        WHERE id = :issue_id
                    """),
                    {
                        "issue_id": data.issue_id
                    }
                )

            else:

                connection.execute(
                    text("""
                        UPDATE claims
                        SET status = 'pending'
                        WHERE issue_id = :issue_id
                    """),
                    {
                        "issue_id": data.issue_id
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

        return {
            "message": "Verification submitted"
        }


@router.get("/verification/{issue_id}")
def get_verification_summary(issue_id: int):

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT
                    status,
                    COUNT(*) as total

                FROM verification_votes

                WHERE issue_id = :issue_id

                GROUP BY status
            """),
            {
                "issue_id": issue_id
            }
        )

        summary = {
            "solved": 0,
            "partial": 0,
            "not solved": 0
        }

        for row in result.mappings():
            summary[row["status"]] = row["total"]

        return summary