from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from sqlalchemy import Column, Integer, String, Date, Boolean, Text
from backend.database import Base

class FamilyMember(BaseModel):
    name: str
    gender: Optional[str] = Field(None, description="male, female, or other")
    avatar: Optional[str] = Field(None, description="Image URL")

class Chore(BaseModel):
    id: int
    chore_name: str
    icon: Optional[str] = None
    assigned_members: List[str]
    start_date: date
    end_date: Optional[date] = None
    due_time: str = "23:59"
    repetition: str = Field(..., description="daily, weekly, one-time")
    reminder: Optional[str] = None
    type: Optional[str] = Field(None, description="individual, rotate, compete")

class Meal(BaseModel):
    id: int
    meal_name: str
    exist: bool
    meal_kind: str = Field(..., description="breakfast, lunch, dinner, snack")
    meal_date: date
    dishes: Optional[List[str]] = None

class ChoreORM(Base):
    __tablename__ = "chores"
    id = Column(Integer, primary_key=True, index=True)
    chore_name = Column(String, nullable=False)
    icon = Column(String, nullable=True)
    assigned_members = Column(Text, nullable=False)  # Comma-separated
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    due_time = Column(String, default="23:59")
    repetition = Column(String, nullable=False)
    reminder = Column(String, nullable=True)
    type = Column(String, nullable=True)

class MealORM(Base):
    __tablename__ = "meals"
    id = Column(Integer, primary_key=True, index=True)
    meal_name = Column(String, nullable=False)
    exist = Column(Boolean, nullable=False)
    meal_kind = Column(String, nullable=False)
    meal_date = Column(Date, nullable=False)
    dishes = Column(Text, nullable=True)  # Comma-separated

class FamilyMemberORM(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    gender = Column(String, nullable=True)
    avatar = Column(String, nullable=True)

class RecipeORM(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    description = Column(String, nullable=True)
