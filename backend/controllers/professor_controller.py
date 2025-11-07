from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from ..tables.professor import Professor

#functions that operate on the professor table
#currently has create, read, update, and delete functions. as well as bulk listing and populating functions

def create_professor(data: Dict, db: Session) -> Dict:
    """
    data: { "email": str, "name": str, "title": str, ... }
    """
    if not data.get("email"):
        return {"success": False, "error": "email is required"}
    try:
        existing = db.query(Professor).filter(Professor.email == data["email"]).first()
        if existing:
            return {"success": False, "error": "Professor already exists"}
        p = Professor(
            email=data["email"],
            name=data.get("name"),
            title=data.get("title"),
            phone_number=data.get("phone_number"),
            department=data.get("department"),
            portfolio_page=data.get("portfolio_page"),
            profile_page=data.get("profile_page"),
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return {"success": True, "professor": {"email": p.email, "name": p.name}}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

def get_professor_by_email(email: str, db: Session) -> Optional[Dict]:
    p = db.query(Professor).filter(Professor.email == email).first()
    if not p:
        return None
    return {
        "email": p.email,
        "name": p.name,
        "title": p.title,
        "phone_number": p.phone_number,
        "department": p.department,
        "portfolio_page": p.portfolio_page,
        "profile_page": p.profile_page,
    }

def list_professors(db: Session) -> List[Dict]:
    rows = db.query(Professor).all()
    return [
        {
            "email": r.email,
            "name": r.name,
            "title": r.title,
            "phone_number": r.phone_number,
            "department": r.department,
            "portfolio_page": r.portfolio_page,
            "profile_page": r.profile_page,
        }
        for r in rows
    ]

def update_professor(email: str, updates: Dict, db: Session) -> Dict:
    p = db.query(Professor).filter(Professor.email == email).first()
    if not p:
        return {"success": False, "error": "Professor not found"}
    try:
        for k in ("name", "title", "phone_number", "department", "portfolio_page", "profile_page"):
            if k in updates:
                setattr(p, k, updates[k])
        db.commit()
        db.refresh(p)
        return {"success": True, "professor": get_professor_by_email(email, db)}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

def delete_professor(email: str, db: Session) -> Dict:
    p = db.query(Professor).filter(Professor.email == email).first()
    if not p:
        return {"success": False, "error": "Professor not found"}
    try:
        db.delete(p)
        db.commit()
        return {"success": True, "message": f"Professor {email} deleted"}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

def populate_from_list(entries: List[Dict], db: Session) -> Dict:
    """
    entries: list of dicts with keys matching model fields.
    Inserts ignoring duplicates (skips existing emails).
    """
    try:
        inserted = 0
        for entry in entries:
            email = entry.get("email") or entry.get("Email")
            if not email:
                continue
            exists = db.query(Professor).filter(Professor.email == email).first()
            if exists:
                continue
            p = Professor(
                email=email,
                name=entry.get("name") or entry.get("Name"),
                title=entry.get("title") or entry.get("Title"),
                phone_number=entry.get("phone_number") or entry.get("Phone"),
                department=entry.get("department") or entry.get("Department"),
                portfolio_page=entry.get("portfolio_page") or entry.get("Portfolio"),
                profile_page=entry.get("profile_page") or entry.get("Profile_Page") or entry.get("Profile Page"),
            )
            db.add(p)
            inserted += 1
        db.commit()
        return {"success": True, "inserted": inserted}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
