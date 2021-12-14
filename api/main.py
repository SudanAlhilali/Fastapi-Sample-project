from typing import List
from fastapi.encoders import jsonable_encoder

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security.oauth2 import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from pydantic.networks import EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import mode
from starlette.responses import Response
from api.hashing import Hasher

from . import  models, schemas
from .database import SessionLocal, engine

from api import config, crud, database

models.Base.metadata.create_all(bind=engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()

# middleware thing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.post("/users/", response_model=schemas.showUser , tags=["User"])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)


@app.get("/users/", response_model=List[schemas.User], tags=["User"])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User , tags=["User"])
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/users/usrEmail/{user_email}" , response_model=schemas.showUser, tags=["User"])
def read_user(user_email: EmailStr, db: Session = Depends(get_db) ):
    db_user = crud.get_user_by_email(db,user_email)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
    


# login routing



@app.post("/login")
def retrieve_token_for_authenticated_user(response: Response,form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username"
        )
    if not Hasher.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Password"
        )
    data = {"sub": form_data.username}
    jwt_token = jwt.encode(data, config.settings.SECRET_KEY, algorithm=config.Settings.ALGORITHM)
    response.set_cookie(key="access_token", value=f"Bearer {jwt_token}", httponly=True)
    return {"name": user.name, "email": user.email ,"id": user.id, "access_token": jwt_token, "token_type": "bearer"}


# item routing


def get_user_from_token(db, token):
    try:
        payload = jwt.decode(token, config.settings.SECRET_KEY, config.settings.ALGORITHM)
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate Credentials",
            )
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate Credetials",
        )
    user = db.query(models.User).filter(models.User.email == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    return user


@app.post("/item", tags=["item"], response_model=schemas.ItemCreate)
def create_item(
    item: schemas.ItemCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    user = get_user_from_token(db, token)
    owner_id = user.id
    item = models.Items(**item.dict(), owner_id=owner_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item






def create_user_item(db: Session, item: schemas.ItemCreate, user_id: int):
    db_item = models.Item(**item.dict(), owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.get("/items/", tags=["item"], response_model=List[schemas.Item])
def get_item_by_user_id(db: Session = Depends(get_db),token: str = Depends(oauth2_scheme)):
    user = get_user_from_token(db, token)
    item = db.query(models.Items).filter(models.Items.owner_id==user.id).all()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with {id} does not exists",
        )
    return item


@app.put("/item/update/{id}", tags=["item"])
def update_item_by_id(
    id: int,
    item: schemas.ItemCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    user = get_user_from_token(db, token)
    existing_item = db.query(models.Items).filter(models.Items.id == id)
    if not existing_item.first():
        return {"message": f"No Details found for Item ID {id}"}
    if existing_item.first().owner_id == user.id:
        existing_item.update(jsonable_encoder(item))
        db.commit()
        return {"message": f"Details successfully updated for Item ID {id}"}
    else:
        return {"message": "You are not authorized"}


@app.delete("/item/delete/{id}", tags=["item"])
def delete_item_by_id(
    id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    user = get_user_from_token(db, token)
    existing_item = db.query(models.Items).filter(models.Items.id == id)
    if not existing_item.first():
        return {"message": f"No Details found for Item ID {id}"}
    if existing_item.first().owner_id == user.id:
        existing_item.delete()
        db.commit()
        return {"message": f"Item ID {id} has been successfully deleted"}
    else:
        return {"message": "You are not authorized"}
