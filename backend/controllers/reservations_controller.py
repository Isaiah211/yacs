from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..tables.database import get_db
from ..tables.reservation import Reservation
from ..tables.course_offering import CourseOffering

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


class ReservationCreate(BaseModel):
    offering_id: int
    user_id: Optional[int] = None
    hold_minutes: Optional[int] = 15


class ReservationOut(BaseModel):
    id: int
    offering_id: int
    user_id: Optional[int]
    status: str
    created_at: Optional[str]
    expires_at: Optional[str]
    seats: int
    notes: Optional[str]


@router.post("/", response_model=ReservationOut)
def create_reservation(req: ReservationCreate, allow_overfull: bool = Query(False), db: Session = Depends(get_db)):
    now = datetime.utcnow()
    hold_until = now + timedelta(minutes=req.hold_minutes or 15)

    offering = db.query(CourseOffering).filter(CourseOffering.id == req.offering_id).with_for_update().first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")

    capacity = offering.capacity
    enrolled = offering.enrolled or 0

    # count active held reservations for this offering
    active_reserved = db.query(Reservation).filter(
        Reservation.offering_id == offering.id,
        Reservation.status == 'held',
        Reservation.expires_at > now
    ).count()

    if capacity is not None:
        available = capacity - enrolled - active_reserved
        if available <= 0 and not allow_overfull:
            raise HTTPException(status_code=400, detail="No seats available")

    r = Reservation(
        offering_id=offering.id,
        user_id=req.user_id,
        status='held',
        created_at=now,
        expires_at=hold_until,
        seats=1,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r.to_dict()


@router.post("/{reservation_id}/commit", response_model=ReservationOut)
def commit_reservation(reservation_id: int, allow_overfull: bool = Query(False), db: Session = Depends(get_db)):
    now = datetime.utcnow()
    r = db.query(Reservation).filter(Reservation.id == reservation_id).with_for_update().first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if r.status != 'held':
        raise HTTPException(status_code=400, detail=f"Reservation not in held state: {r.status}")
    if r.expires_at and r.expires_at < now:
        r.status = 'expired'
        db.add(r)
        db.commit()
        raise HTTPException(status_code=400, detail="Reservation expired")

    offering = db.query(CourseOffering).filter(CourseOffering.id == r.offering_id).with_for_update().first()
    if not offering:
        raise HTTPException(status_code=404, detail="Offering not found")

    capacity = offering.capacity
    enrolled = offering.enrolled or 0
    # count other active held reservations (excluding this one)
    active_reserved = db.query(Reservation).filter(
        Reservation.offering_id == offering.id,
        Reservation.status == 'held',
        Reservation.expires_at > now,
        Reservation.id != r.id
    ).count()

    if capacity is not None:
        available = capacity - enrolled - active_reserved
        if available <= 0 and not allow_overfull:
            raise HTTPException(status_code=400, detail="No seats available to commit")

    # commit: increment enrolled and mark reservation committed
    offering.enrolled = enrolled + (r.seats or 1)
    r.status = 'committed'
    db.add(offering)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r.to_dict()


@router.delete("/{reservation_id}")
def release_reservation(reservation_id: int, db: Session = Depends(get_db)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if r.status == 'committed':
        raise HTTPException(status_code=400, detail="Cannot release a committed reservation")
    r.status = 'released'
    db.add(r)
    db.commit()
    return {"status": "released", "id": reservation_id}
