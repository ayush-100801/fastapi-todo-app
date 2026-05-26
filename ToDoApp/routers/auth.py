from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, Field
from starlette import status
from ..models import Users
from passlib.context import CryptContext
from typing import Annotated
from sqlalchemy.orm import Session
from ..database import session_local
from jose import jwt, JWTError
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from dotenv import load_dotenv
import os

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

load_dotenv()
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY=os.getenv("SECRET_KEY")
ALGORITHM=os.getenv("ALGORITHM")


def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
templates = Jinja2Templates(directory="ToDoApp/templates")


@router.get('/login-page')
def render_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"user": None})


@router.get('/register-page')
def render_register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={"user": None})


def authenticate_user(username: str, password: str, db):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user


def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id, 'role': role}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(request: Request):
    try:
        token = request.cookies.get("access_token")
        if token is None:
            raise HTTPException(status_code=401, detail="Could not validate user")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username = payload.get("sub")
        user_id = payload.get("id")
        user_role = payload.get("role")

        if username is None or user_id is None:
            raise HTTPException(status_code=401, detail="Could not validate user")

        return {"username": username, "user_id": user_id, "user_role": user_role}

    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate user")


class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str = Field(min_length=8, max_length=72)
    role: str
    phone_number: str


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, user: CreateUserRequest):
    existing_user = db.query(Users).filter((Users.username == user.username) | (Users.email == user.email) | (
                Users.phone_number == user.phone_number)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    if len(user.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="Password cannot exceed 72 bytes")

    user_model = Users(
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        hashed_password=bcrypt_context.hash(user.password),
        is_active=True,
        phone_number=user.phone_number
    )
    db.add(user_model)
    db.commit()


@router.post("/token")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(user.username, user.id, user.role, timedelta(minutes=20))
    response = RedirectResponse(url="/todos/todo-page", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=1200, expires=1200, secure=True, samesite="none", path="/")
    return response
