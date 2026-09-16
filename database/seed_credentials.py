"""Seed demo staff credentials without storing plaintext passwords."""

from dataclasses import dataclass

import bcrypt

from database.db import SessionLocal, engine
from database.models import Base, StaffCredential


@dataclass(frozen=True)
class SeedIdentity:
    user_id: str
    role: str
    default_password: str
    technician_id: str | None = None


def _identities() -> list[SeedIdentity]:
    identities = [
        SeedIdentity("tech-demo", "technician", "TechDemo-2026", "TECH-101"),
        SeedIdentity("engineer-demo", "engineer", "EngineerDemo-2026"),
        SeedIdentity("supervisor-demo", "supervisor", "SupervisorDemo-2026"),
        SeedIdentity("executive-demo", "executive", "ExecutiveDemo-2026"),
    ]
    identities.extend(
        SeedIdentity(f"TECH-{number}", "technician", f"Tech-{number}-2026", f"TECH-{number}")
        for number in range(101, 121)
    )
    identities.extend(
        SeedIdentity(f"ENG-{number}", "engineer", f"Eng-{number}-2026")
        for number in range(1, 4)
    )
    identities.extend(
        SeedIdentity(f"SUP-{number}", "supervisor", f"Sup-{number}-2026")
        for number in range(1, 4)
    )
    identities.extend(
        SeedIdentity(f"EXEC-{number}", "executive", f"Exec-{number}-2026")
        for number in range(1, 4)
    )
    return identities


def seed_credentials() -> list[SeedIdentity]:
    """Create missing credentials and return only the rows inserted now."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    inserted: list[SeedIdentity] = []
    try:
        existing_ids = {row[0] for row in session.query(StaffCredential.user_id).all()}
        for identity in _identities():
            if identity.user_id in existing_ids:
                continue
            session.add(
                StaffCredential(
                    user_id=identity.user_id,
                    password_hash=bcrypt.hashpw(
                        identity.default_password.encode(), bcrypt.gensalt()
                    ).decode(),
                    role=identity.role,
                    technician_id=identity.technician_id,
                    must_change_password=True,
                )
            )
            inserted.append(identity)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return inserted


if __name__ == "__main__":
    seeded = seed_credentials()
    print(f"Seeded {len(seeded)} new staff credentials.")
    for identity in seeded:
        print(f"{identity.user_id}\t{identity.role}\t{identity.default_password}")