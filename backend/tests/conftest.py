import pytest
from app.database import engine, Base
from app.services.data_loader import init_db, seed_data

@pytest.fixture(autouse=True, scope="module")
def clean_database_per_module():
    """Ensure every test module starts with a fresh, clean seeded database."""
    Base.metadata.drop_all(bind=engine)
    init_db()
    seed_data()
    yield

