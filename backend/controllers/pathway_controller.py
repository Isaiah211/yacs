from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..tables.pathway import Pathway, PathwayRequirement
from ..tables.database import get_db

router = APIRouter(prefix="/api/pathways", tags=["pathways"])

class RequirementBase(BaseModel):
    name: str
    description: Optional[str]
    credits_required: int
    course_count_required: Optional[int]

class RequirementCreate(RequirementBase):
    course_ids: List[str]

class RequirementResponse(RequirementBase):
    id: int
    pathway_id: int
    courses: List[dict]

    class Config:
        orm_mode = True

class PathwayBase(BaseModel):
    name: str
    code: str
    description: Optional[str]
    total_credits: int

class PathwayCreate(PathwayBase):
    requirements: List[RequirementCreate]

class PathwayResponse(PathwayBase):
    id: int
    requirements: List[RequirementResponse]

    class Config:
        orm_mode = True

@router.post("/", response_model=PathwayResponse)
def create_pathway(pathway: PathwayCreate, db: Session = Depends(get_db)):
    # Check if pathway with same code exists
    existing = db.query(Pathway).filter(Pathway.code == pathway.code).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Pathway with code {pathway.code} already exists"
        )

    # Create new pathway
    db_pathway = Pathway(
        name=pathway.name,
        code=pathway.code,
        description=pathway.description,
        total_credits=pathway.total_credits
    )
    db.add(db_pathway)
    db.flush()  # Get the ID without committing

    # Create requirements
    for req in pathway.requirements:
        db_requirement = PathwayRequirement(
            pathway_id=db_pathway.id,
            name=req.name,
            description=req.description,
            credits_required=req.credits_required,
            course_count_required=req.course_count_required
        )
        db.add(db_requirement)
        
        # Add courses to requirement
        for course_id in req.course_ids:
            db_requirement.courses.append(db.query(Course).get(course_id))

    try:
        db.commit()
        db.refresh(db_pathway)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return db_pathway

@router.get("/", response_model=List[PathwayResponse])
def get_pathways(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return db.query(Pathway).offset(skip).limit(limit).all()

@router.get("/{pathway_id}", response_model=PathwayResponse)
def get_pathway(pathway_id: int, db: Session = Depends(get_db)):
    pathway = db.query(Pathway).filter(Pathway.id == pathway_id).first()
    if not pathway:
        raise HTTPException(
            status_code=404,
            detail=f"Pathway with id {pathway_id} not found"
        )
    return pathway

@router.put("/{pathway_id}", response_model=PathwayResponse)
def update_pathway(
    pathway_id: int,
    pathway_update: PathwayCreate,
    db: Session = Depends(get_db)
):
    # Check if pathway exists
    db_pathway = db.query(Pathway).filter(Pathway.id == pathway_id).first()
    if not db_pathway:
        raise HTTPException(
            status_code=404,
            detail=f"Pathway with id {pathway_id} not found"
        )

    # Update pathway fields
    for key, value in pathway_update.dict(exclude={'requirements'}).items():
        setattr(db_pathway, key, value)

    # Update requirements
    # First, remove existing requirements
    db.query(PathwayRequirement).filter(
        PathwayRequirement.pathway_id == pathway_id
    ).delete()

    # Add new requirements
    for req in pathway_update.requirements:
        db_requirement = PathwayRequirement(
            pathway_id=pathway_id,
            name=req.name,
            description=req.description,
            credits_required=req.credits_required,
            course_count_required=req.course_count_required
        )
        db.add(db_requirement)
        
        # Add courses to requirement
        for course_id in req.course_ids:
            db_requirement.courses.append(db.query(Course).get(course_id))

    try:
        db.commit()
        db.refresh(db_pathway)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return db_pathway

@router.delete("/{pathway_id}")
def delete_pathway(pathway_id: int, db: Session = Depends(get_db)):
    pathway = db.query(Pathway).filter(Pathway.id == pathway_id).first()
    if not pathway:
        raise HTTPException(
            status_code=404,
            detail=f"Pathway with id {pathway_id} not found"
        )

    try:
        db.delete(pathway)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": f"Pathway {pathway_id} deleted successfully"}