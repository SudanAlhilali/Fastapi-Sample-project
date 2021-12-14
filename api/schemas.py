from typing import ContextManager, List, Optional

from pydantic import BaseModel
from pydantic import EmailStr



class Item(BaseModel):
    content: str
    category: str
    done: bool
    id: int
    class Config():
     orm_mode = True
     
class ItemCreate(BaseModel):
    content: str
    category: str
    done: bool = False
    
    class Config():
        orm_mode = True

class UserBase(BaseModel):
    name: str
    email: EmailStr
    
    class Config():
        orm_mode = True


class UserCreate(UserBase):
    password: str

class showUser(BaseModel):
    name: str
    email: EmailStr
    
    class Config():
        orm_mode = True
        
class loginUser(BaseModel):
    email: EmailStr
    password: str

    class Config():
        orm_mode=True

class User(UserBase):
    id: int
    items: List[Item] = []

    class Config():
        orm_mode = True
