from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class FamilyMemberBase(BaseModel):
    name: str
    gender: Optional[str] = None
    avatar: Optional[str] = None

class FamilyMemberCreate(FamilyMemberBase):
    pass

class FamilyMemberRead(FamilyMemberBase):
    id: int
    model_config = dict(from_attributes=True)

class ChoreBase(BaseModel):
    chore_name: str
    icon: Optional[str] = None
    assigned_members: List[str]
    start_date: date
    end_date: Optional[date] = None
    due_time: Optional[str] = "23:59"
    repetition: str
    reminder: Optional[str] = None
    type: Optional[str] = None

class ChoreCreate(ChoreBase):
    pass

class ChoreRead(ChoreBase):
    id: int
    model_config = dict(from_attributes=True)

class MealBase(BaseModel):
    meal_name: str
    exist: bool
    meal_kind: str
    meal_date: date
    dishes: Optional[List[str]] = None

class MealCreate(MealBase):
    pass

class MealRead(MealBase):
    id: int
    model_config = dict(from_attributes=True)

class RecipeBase(BaseModel):
    name: str
    kind: str
    description: Optional[str] = None

class RecipeCreate(RecipeBase):
    pass

class RecipeRead(RecipeBase):
    id: int
    model_config = dict(from_attributes=True) 