from medizy_engine.dedupe import duplicate_reason
from medizy_engine.normalize import normalize_phone, normalize_text
from medizy_engine.store import insert_records


def test_normalize_text_handles_accents_and_spaces():
    assert normalize_text("  CLINIQUE   Médicale ") == "clinique médicale"


def test_normalize_phone_keeps_digits_and_plus():
    assert normalize_phone("+213 (0) 555-12-34") == "+21305551234"


def test_duplicate_requires_strong_evidence():
    a = {"name": "Clinique El Amal", "phone": "0555123456"}
    b = {"name": "clinique el amal", "phone": "0555123456"}
    assert duplicate_reason(a, b) == "same_phone_and_compatible_name"


def test_staging_insert_is_idempotent(tmp_path):
    db = tmp_path / "isolated.sqlite"
    record = {"source": "test", "source_id": "1", "name": "Clinic"}
    assert insert_records(db, [record]) == 1
    assert insert_records(db, [record]) == 0
    assert db.exists()
