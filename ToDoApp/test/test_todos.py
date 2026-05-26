from fastapi import status
from ..routers.todos import get_db, get_current_user
from .utils import *

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

def test_read_all_authenticated(test_todo):
    response = client.get("/todos")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{'complete':False, 'title':'Learn to code', 'description':'Need to learn everyday', 'id':1, 'priority':5, 'owner_id':1}]

def test_read_one_authenticated(test_todo):
    response = client.get("/todos/todo/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {'complete':False, 'title':'Learn to code', 'description':'Need to learn everyday', 'id':1, 'priority':5, 'owner_id':1}

def test_create_todo(test_todo):
    request_data = {
        'title': 'New Todo',
        'description': 'New todo description',
        'complete': False,
        'priority': 5,
    }
    response = client.post("/todos/todo/", json=request_data)
    assert response.status_code == status.HTTP_201_CREATED

    db = TestingSessionLocal()
    model = db.query(Todos).filter(Todos.id == 2).first()
    assert model.title == request_data['title']
    assert model.description == request_data['description']
    assert model.complete == request_data['complete']
    assert model.priority == request_data['priority']

def test_update_todo(test_todo):
    request_data = {
        'title': 'change the title of Todo',
        'description': 'Need to learn everyday',
        'complete': False,
        'priority': 5,
    }
    response = client.put('/todos/todo/1', json=request_data)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    db = TestingSessionLocal()
    model = db.query(Todos).filter(Todos.id == 1).first()
    assert model.title == 'change the title of Todo'

def test_delete_todo(test_todo):
    response = client.delete('/todos/todo/1')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    db = TestingSessionLocal()
    model = db.query(Todos).filter(Todos.id == 1).first()
    assert model is None

