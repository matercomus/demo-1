from sqlalchemy.orm import Session
from backend.models import FamilyMemberORM
from backend.schemas import FamilyMemberCreate
from typing import List, Optional
import logging

def create_member(db: Session, member: FamilyMemberCreate) -> FamilyMemberORM:
    db_member = FamilyMemberORM(
        name=member.name,
        gender=member.gender,
        avatar=member.avatar
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    logging.info(f"Created member: {db_member.name} (ID: {db_member.id})")
    return db_member

def get_members(db: Session) -> List[FamilyMemberORM]:
    return db.query(FamilyMemberORM).all()

def get_member(db: Session, member_id: int) -> Optional[FamilyMemberORM]:
    return db.query(FamilyMemberORM).filter(FamilyMemberORM.id == member_id).first()

def update_member(db: Session, member_id: int, member: FamilyMemberCreate) -> Optional[FamilyMemberORM]:
    db_member = db.query(FamilyMemberORM).filter(FamilyMemberORM.id == member_id).first()
    if not db_member:
        return None
    db_member.name = member.name
    db_member.gender = member.gender
    db_member.avatar = member.avatar
    db.commit()
    db.refresh(db_member)
    logging.info(f"Updated member: {db_member.name} (ID: {db_member.id})")
    return db_member

def delete_member(db: Session, member_id: int) -> bool:
    db_member = db.query(FamilyMemberORM).filter(FamilyMemberORM.id == member_id).first()
    if not db_member:
        return False
    db.delete(db_member)
    db.commit()
    logging.info(f"Deleted member ID: {member_id}")
    return True 