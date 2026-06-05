from fastapi import APIRouter
from backend.db import engine
from sqlalchemy import text
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import HTTPException



router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated = "auto"
)



def create_access_token(data:dict):

    to_encode = data.copy() 

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm= ALGORITHM
    )

    return encoded_jwt


def get_current_user(
    token: str = Depends(oauth2_scheme)
):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("user_id")

        email = payload.get("email")

        if user_id is None:

            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        return {
            "user_id": user_id,
            "email": email
        }

    except JWTError:
        raise HTTPException(
        status_code=401,
        detail="Invalid token"
    )


class UserCreate(BaseModel):
    name: str
    email: str
    password : str

class LoginData(BaseModel):
    email: str
    password: str


@router.get("/profile")
def profile(token: str = Depends(oauth2_scheme)):

    user = get_current_user(token)

    return{
        "current_user" : user
    }



@router.post("/login")
def login(data: OAuth2PasswordRequestForm = Depends()):
        
        print("AUTH ROUTER LOGIN RUNNING")
        
        with engine.connect() as connection:
            
            result = connection.execute(
                text("SELECT * FROM users WHERE email = :email "),
                {
                    "email": data.username
                }
            )

            user = result.mappings().first()

            if user is None:
                return {"message": "User not found"}
            
            if not pwd_context.verify(data.password, user["password"]):
                return {"message": "Invalid password"}
            



            token = create_access_token(
                {
                    "user_id" :  user["id"],
                    "email" : user["email"]
                }
            )

            return {
                "message" : "Login succeessful",
                "access_token" : token,
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"]
                }
            }
        

@router.post("/register")
def add_user(user: UserCreate):

    with engine.connect() as connection:

        result = connection.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {
                "email": user.email
            }
        )

        existing_user = result.mappings().first()

        if existing_user:
            return {"message": "Email already registered"}

        hashed_password = pwd_context.hash(user.password)

        connection.execute(
            text("""
                INSERT INTO users (name, email, password)
                VALUES (:name, :email, :password)
            """),
            {
                "name": user.name,
                "email": user.email,
                "password": hashed_password
            }
        )

        connection.commit()


        result = connection.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {
                "email": user.email
            }
        )

        new_user = result.mappings().first()


        token = create_access_token(
            {
                "user_id": new_user["id"],
                "email": new_user["email"]
            }
        )

    return {
        "message": "User registered successfully",
        "access_token": token,
        "user": {
            "id": new_user["id"],
            "name": new_user["name"],
            "email": new_user["email"]
        }
    }    


