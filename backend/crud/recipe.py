from sqlalchemy.orm import Session
from backend.models import RecipeORM
from backend.schemas import RecipeCreate
from sqlalchemy import or_

def create_recipe(db: Session, recipe: RecipeCreate):
    db_recipe = RecipeORM(**recipe.model_dump())
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    return db_recipe

def get_recipe(db: Session, recipe_id: int):
    return db.query(RecipeORM).filter(RecipeORM.id == recipe_id).first()

def get_recipes(db: Session):
    return db.query(RecipeORM).all()

def search_recipes(db: Session, query: str):
    # Fuzzy search by name (case-insensitive, partial match)
    return db.query(RecipeORM).filter(RecipeORM.name.ilike(f"%{query}%")).all()

def delete_recipe(db: Session, recipe_id: int):
    recipe = db.query(RecipeORM).filter(RecipeORM.id == recipe_id).first()
    if recipe:
        db.delete(recipe)
        db.commit()
        return True
    return False

def update_recipe(db: Session, recipe_id: int, recipe: RecipeCreate):
    db_recipe = db.query(RecipeORM).filter(RecipeORM.id == recipe_id).first()
    if not db_recipe:
        return None
    db_recipe.name = recipe.name
    db_recipe.kind = recipe.kind
    db_recipe.description = recipe.description
    db.commit()
    db.refresh(db_recipe)
    return db_recipe 