from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Request, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status
from ..models import Todos
from ..database import session_local
from .auth import get_current_user
from starlette.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import jwt
from .auth import SECRET_KEY, ALGORITHM

templates = Jinja2Templates(directory="ToDoApp/templates")

router = APIRouter(
    prefix='/todos',
    tags=['todos'],
)


def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class ToDoRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=100)
    priority: int = Field(gt=0, lt=6)
    complete: bool


def redirect_to_login():
    redirect_response = RedirectResponse(url="/auth/login-page", status_code=status.HTTP_302_FOUND)
    redirect_response.delete_cookie(key="access_token")
    return redirect_response


@router.get("/todo-page")
async def get_todos(request: Request, db: db_dependency):
    print("Cookies:", request.cookies)
    try:
        token = request.cookies.get("access_token")
        print("TOKEN:", token)
        if token is None:
            return redirect_to_login()
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = {
            "username": payload.get("sub"),
            "user_id": payload.get("id"),
            "user_role": payload.get("role")
        }
        todos = db.query(Todos).filter(Todos.owner_id == user["user_id"]).all()
        return templates.TemplateResponse(request=request, name="todo.html", context={"todos": todos, "user": user})

    except Exception as e:
        print("JWT ERROR:", e)
        return redirect_to_login()

@router.get("/add-todo-page")
async def render_todo_page(request: Request):
    try:
        token = request.cookies.get("access_token")
        if token is None:
            return redirect_to_login()
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = {
            "username": payload.get("sub"),
            "user_id": payload.get("id"),
            "user_role": payload.get("role")
        }
        return templates.TemplateResponse(request=request, name="add-todo.html", context={"user": user})
    except Exception as e:
        print("ERROR:", e)
        return redirect_to_login()

@router.get("/edit-todo-page/{todo_id}")
async def render_edit_todo_page(request: Request, todo_id: int, db: db_dependency):
    try:
        token = request.cookies.get("access_token")
        if token is None:
            return redirect_to_login()
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = {
            "username": payload.get("sub"),
            "user_id": payload.get("id"),
            "user_role": payload.get("role")
        }
        todo = db.query(Todos).filter(Todos.id == todo_id).first()
        return templates.TemplateResponse(request=request, name="edit-todo.html", context={"todo":todo, "user": user})

    except:
        return redirect_to_login()


@router.get("/", status_code=status.HTTP_200_OK)
async def read_all(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication failed")
    return db.query(Todos).filter(Todos.owner_id == user.get('user_id')).all()


@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def read_by_id(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication failed")
    todo_model = db.query(Todos).filter(Todos.id == todo_id).filter(Todos.owner_id == user.get('user_id')).first()
    if todo_model is not None:
        return todo_model
    else:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo(user: user_dependency, db: db_dependency, todo_request: ToDoRequest):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication failed")
    todo_model = Todos(**todo_request.dict(), owner_id=user.get('user_id'))
    db.add(todo_model)
    db.commit()


@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user: user_dependency, db: db_dependency, todo_request: ToDoRequest, todo_id: int = Path(gt=0)):
    print(todo_request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication failed")
    todo_model = db.query(Todos).filter(Todos.id == todo_id, Todos.owner_id == user.get('user_id')).first()
    if todo_model is not None:
        todo_model.title = todo_request.title
        todo_model.description = todo_request.description
        todo_model.priority = todo_request.priority
        todo_model.complete = todo_request.complete
        db.add(todo_model)
        db.commit()
    else:
        raise HTTPException(status_code=404, detail="Not found")


@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication failed")
    todo_model = db.query(Todos).filter(Todos.id == todo_id).filter(Todos.owner_id == user.get('user_id')).first()
    if todo_model is None:
        raise HTTPException(status_code=404, detail="Not found")
    db.query(Todos).filter(Todos.id == todo_id).filter(Todos.owner_id == user.get('user_id')).delete()
    db.commit()
