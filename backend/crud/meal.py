from sqlalchemy.orm import Session
from backend.models import MealORM
from backend.schemas import MealCreate
from typing import List, Optional
import logging

def create_meal(db: Session, meal: MealCreate) -> MealORM:
    logger = logging.getLogger("crud.meal")
    logger.info(f"[DEBUG] create_meal called with meal={meal}")
    db_meal = MealORM(
        meal_name=meal.meal_name,
        exist=meal.exist,
        meal_kind=meal.meal_kind,
        meal_date=meal.meal_date,
        dishes=','.join(meal.dishes) if meal.dishes else None
    )
    db.add(db_meal)
    db.commit()
    db.refresh(db_meal)
    logging.info(f"Created meal: {db_meal.meal_name} (ID: {db_meal.id})")
    return db_meal

def get_meals(db: Session) -> List[MealORM]:
    logger = logging.getLogger("crud.meal")
    logger.debug(f"[DEBUG] get_meals called")
    return db.query(MealORM).all()

def get_meal(db: Session, meal_id: int) -> Optional[MealORM]:
    logger = logging.getLogger("crud.meal")
    logger.info(f"[DEBUG] get_meal called with meal_id={meal_id}")
    return db.query(MealORM).filter(MealORM.id == meal_id).first()

def update_meal(db: Session, meal_id: int, meal: MealCreate) -> Optional[MealORM]:
    logger = logging.getLogger("crud.meal")
    logger.info(f"[DEBUG] update_meal called with meal_id={meal_id}, meal={meal}")
    db_meal = db.query(MealORM).filter(MealORM.id == meal_id).first()
    if not db_meal:
        return None
    db_meal.meal_name = meal.meal_name
    db_meal.exist = meal.exist
    db_meal.meal_kind = meal.meal_kind
    db_meal.meal_date = meal.meal_date
    db_meal.dishes = ','.join(meal.dishes) if meal.dishes else None
    db.commit()
    db.refresh(db_meal)
    logging.info(f"Updated meal: {db_meal.meal_name} (ID: {db_meal.id})")
    return db_meal

def delete_meal(db: Session, meal_id: int) -> bool:
    logger = logging.getLogger("crud.meal")
    logger.info(f"[DEBUG] delete_meal called with id={meal_id}")
    meal = db.query(MealORM).filter(MealORM.id == meal_id).first()
    logger.info(f"[DEBUG] delete_meal: meal before delete: {meal}")
    if not meal:
        logger.info(f"[DEBUG] delete_meal: meal not found, returning False")
        return False
    db.delete(meal)
    db.commit()
    logger.info(f"[DEBUG] delete_meal: meal deleted, returning True")
    return True 