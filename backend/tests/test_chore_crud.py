from backend.schemas import ChoreCreate
from backend.crud.chore import create_chore, get_chore, get_chores, update_chore, delete_chore
from datetime import date

def test_chore_crud(db_session):
    # Create
    chore = ChoreCreate(
        chore_name="Laundry",
        icon="🧺",
        assigned_members=["Alex", "Jamie"],
        start_date=date.today(),
        due_time="23:59",
        repetition="weekly",
        reminder=None,
        type="rotate"
    )
    db_chore = create_chore(db_session, chore)
    assert db_chore.id is not None
    assert db_chore.chore_name == "Laundry"
    # Get by id
    got = get_chore(db_session, db_chore.id)
    assert got is not None
    assert got.chore_name == "Laundry"
    # List
    all_chores = get_chores(db_session)
    assert any(c.id == db_chore.id for c in all_chores)
    # Update
    updated = update_chore(db_session, db_chore.id, chore.copy(update={"chore_name": "Laundry Updated"}))
    assert updated.chore_name == "Laundry Updated"
    # Delete
    ok = delete_chore(db_session, db_chore.id)
    assert ok
    assert get_chore(db_session, db_chore.id) is None 