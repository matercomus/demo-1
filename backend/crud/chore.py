from sqlalchemy.orm import Session
from backend.models import ChoreORM
from backend.schemas import ChoreCreate
from typing import List, Optional
import logging

def create_chore(db: Session, chore: ChoreCreate) -> ChoreORM:
    db_chore = ChoreORM(
        chore_name=chore.chore_name,
        icon=chore.icon,
        assigned_members=','.join(chore.assigned_members),
        start_date=chore.start_date,
        end_date=chore.end_date,
        due_time=chore.due_time,
        repetition=chore.repetition,
        reminder=chore.reminder,
        type=chore.type
    )
    db.add(db_chore)
    db.commit()
    db.refresh(db_chore)
    logging.info(f"Created chore: {db_chore.chore_name} (ID: {db_chore.id})")
    return db_chore

def get_chores(db: Session) -> List[ChoreORM]:
    return db.query(ChoreORM).all()

def get_chore(db: Session, chore_id: int) -> Optional[ChoreORM]:
    return db.query(ChoreORM).filter(ChoreORM.id == chore_id).first()

def update_chore(db: Session, chore_id: int, chore: ChoreCreate) -> Optional[ChoreORM]:
    db_chore = db.query(ChoreORM).filter(ChoreORM.id == chore_id).first()
    if not db_chore:
        return None
    db_chore.chore_name = chore.chore_name
    db_chore.icon = chore.icon
    db_chore.assigned_members = ','.join(chore.assigned_members)
    db_chore.start_date = chore.start_date
    db_chore.end_date = chore.end_date
    db_chore.due_time = chore.due_time
    db_chore.repetition = chore.repetition
    db_chore.reminder = chore.reminder
    db_chore.type = chore.type
    db.commit()
    db.refresh(db_chore)
    logging.info(f"Updated chore: {db_chore.chore_name} (ID: {db_chore.id})")
    return db_chore

def delete_chore(db: Session, chore_id: int) -> bool:
    db_chore = db.query(ChoreORM).filter(ChoreORM.id == chore_id).first()
    if not db_chore:
        return False
    db.delete(db_chore)
    db.commit()
    logging.info(f"Deleted chore ID: {chore_id}")
    return True 