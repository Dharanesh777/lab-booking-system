from app.core.database import init_indexes
from app.core.exceptions import ConflictError
from app.schemas.lab import LabIn
from app.services.lab_service import create_lab, list_labs

# EDIT THIS LIST: put your three real labs here
LABS = [
    LabIn(code="LAB1", name="CSE Lab 1", capacity=60),
    LabIn(code="LAB2", name="CSE Lab 2", capacity=60),
    LabIn(code="AI1", name="AI Lab", capacity=40),
]

init_indexes()

for lab in LABS:
    try:
        create_lab(lab)
        print(f"created: {lab.code} - {lab.name}")
    except ConflictError:
        print(f"skipped: {lab.code} already exists")

print("\nLabs in database:")
for lab in list_labs(active_only=False):
    print(f"  {lab['_id']:6} {lab['name']:20} capacity={lab['capacity']} active={lab['active']}")