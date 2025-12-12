from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..tables.collaborative_schedule import (
    CollaborativeSchedule,
    ScheduleCourse,
    ScheduleShare,
    ScheduleComment,
)
from ..tables.course import Course

ACCESS_RANK = {
    'viewer': 0,
    'commenter': 1,
    'editor': 2,
}

CAPABILITY_REQUIREMENTS = {
    'view': 0,
    'comment': 1,
    'edit': 2,
}


def _serialize_schedule(schedule: CollaborativeSchedule) -> Dict:
    data = schedule.to_dict()
    return data


def _get_schedule(db: Session, schedule_id: int) -> Optional[CollaborativeSchedule]:
    return db.query(CollaborativeSchedule).filter(CollaborativeSchedule.id == schedule_id).first()


def _get_share(db: Session, schedule_id: int, identifier: Optional[str]) -> Optional[ScheduleShare]:
    if not identifier:
        return None
    return (
        db.query(ScheduleShare)
        .filter(
            ScheduleShare.schedule_id == schedule_id,
            ScheduleShare.collaborator_identifier == identifier
        )
        .first()
    )


def _check_permission(
    db: Session,
    schedule: CollaborativeSchedule,
    requester_identifier: Optional[str],
    capability: str,
) -> Tuple[bool, Optional[str], Optional[ScheduleShare]]:
    if not requester_identifier:
        return False, "requester identifier is required", None

    if schedule.owner_identifier == requester_identifier:
        return True, None, None

    if capability == 'share':
        return False, "only the owner can share this schedule", None

    share = _get_share(db, schedule.id, requester_identifier)
    if not share:
        return False, "you do not have access to this schedule", None

    if share.is_admin_delegate:
        return True, None, share

    required_rank = CAPABILITY_REQUIREMENTS.get(capability, 0)
    if ACCESS_RANK.get(share.access_level, 0) >= required_rank:
        return True, None, share

    return False, "insufficient permissions for this action", share


def _validate_courses(db: Session, entries: List[Dict]) -> Tuple[bool, List[int]]:
    course_ids = {entry.get('course_id') for entry in entries if entry.get('course_id')}
    course_ids.discard(None)
    if not course_ids:
        return True, []

    rows = db.query(Course.id).filter(Course.id.in_(course_ids)).all()
    found = {row[0] for row in rows}
    missing = sorted(course_ids - found)
    return (len(missing) == 0), missing


def create_schedule(schedule_data: Dict, db: Session) -> Dict:
    try:
        schedule = CollaborativeSchedule(
            name=schedule_data['name'],
            description=schedule_data.get('description'),
            semester=schedule_data.get('semester'),
            owner_identifier=schedule_data['owner_identifier'],
            owner_display_name=schedule_data.get('owner_display_name'),
            visibility='private'
        )

        entries = schedule_data.get('courses') or []
        is_valid, missing = _validate_courses(db, entries)
        if not is_valid:
            return {"success": False, "error": f"courses not found: {missing}"}

        for entry in entries:
            schedule.courses.append(ScheduleCourse(
                course_id=entry['course_id'],
                color_hex=entry.get('color_hex'),
                note=entry.get('note'),
                order_index=entry.get('order_index')
            ))

        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return {"success": True, "schedule": _serialize_schedule(schedule)}
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}


def list_user_schedules(requester_identifier: str, include_shared: bool, db: Session) -> Dict:
    try:
        owned = db.query(CollaborativeSchedule).filter(
            CollaborativeSchedule.owner_identifier == requester_identifier
        ).all()

        data = []
        for schedule in owned:
            payload = _serialize_schedule(schedule)
            payload['access_level'] = 'owner'
            payload['permissions'] = {'can_view': True, 'can_comment': True, 'can_edit': True}
            data.append(payload)

        shared_count = 0
        if include_shared:
            shared_rows = (
                db.query(CollaborativeSchedule, ScheduleShare)
                .join(ScheduleShare, ScheduleShare.schedule_id == CollaborativeSchedule.id)
                .filter(ScheduleShare.collaborator_identifier == requester_identifier)
                .all()
            )
            for schedule, share in shared_rows:
                payload = schedule.to_dict(include_relationships=False)
                payload['access_level'] = share.access_level
                payload['is_admin_delegate'] = share.is_admin_delegate
                payload['share_id'] = share.id
                shared_count += 1
                data.append(payload)

        return {
            "success": True,
            "schedules": data,
            "metadata": {
                "owned": len(owned),
                "shared": shared_count
            }
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def get_schedule(schedule_id: int, requester_identifier: str, db: Session) -> Dict:
    schedule = _get_schedule(db, schedule_id)
    if not schedule:
        return {"success": False, "error": "schedule not found"}

    allowed, error, share = _check_permission(db, schedule, requester_identifier, 'view')
    if not allowed:
        return {"success": False, "error": error}

    data = _serialize_schedule(schedule)
    data['permissions'] = {
        'can_view': True,
        'can_comment': True,
        'can_edit': True if schedule.owner_identifier == requester_identifier or (share and (share.is_admin_delegate or ACCESS_RANK.get(share.access_level, 0) >= 2)) else False,
        'is_admin_delegate': bool(share.is_admin_delegate) if share else False,
    }
    return {"success": True, "schedule": data}


def update_schedule(schedule_id: int, requester_identifier: str, updates: Dict, db: Session) -> Dict:
    schedule = _get_schedule(db, schedule_id)
    if not schedule:
        return {"success": False, "error": "schedule not found"}

    allowed, error, _ = _check_permission(db, schedule, requester_identifier, 'edit')
    if not allowed:
        return {"success": False, "error": error}

    try:
        for field in ['name', 'description', 'semester', 'visibility', 'is_locked']:
            if field in updates and updates[field] is not None:
                setattr(schedule, field, updates[field])
        db.commit()
        db.refresh(schedule)
        return {"success": True, "schedule": _serialize_schedule(schedule)}
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}


def replace_schedule_courses(schedule_id: int, requester_identifier: str, entries: List[Dict], db: Session) -> Dict:
    schedule = _get_schedule(db, schedule_id)
    if not schedule:
        return {"success": False, "error": "schedule not found"}

    allowed, error, _ = _check_permission(db, schedule, requester_identifier, 'edit')
    if not allowed:
        return {"success": False, "error": error}

    is_valid, missing = _validate_courses(db, entries)
    if not is_valid:
        return {"success": False, "error": f"courses not found: {missing}"}

    try:
        schedule.courses.clear()
        for entry in entries:
            schedule.courses.append(ScheduleCourse(
                course_id=entry['course_id'],
                color_hex=entry.get('color_hex'),
                note=entry.get('note'),
                order_index=entry.get('order_index')
            ))
        db.commit()
        db.refresh(schedule)
        return {"success": True, "schedule": _serialize_schedule(schedule)}
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}


def share_schedule(schedule_id: int, requester_identifier: str, payload: Dict, db: Session) -> Dict:
    schedule = _get_schedule(db, schedule_id)
    if not schedule:
        return {"success": False, "error": "schedule not found"}

    if schedule.owner_identifier != requester_identifier:
        return {"success": False, "error": "only the owner can manage sharing"}

    collaborator_identifier = payload['collaborator_identifier']
    if collaborator_identifier == requester_identifier:
        return {"success": False, "error": "cannot share a schedule with yourself"}

    try:
        share = _get_share(db, schedule_id, collaborator_identifier)
        if not share:
            share = ScheduleShare(
                schedule_id=schedule_id,
                collaborator_identifier=collaborator_identifier,
            )
            db.add(share)

        share.collaborator_name = payload.get('collaborator_name')
        share.access_level = payload.get('access_level', 'viewer')
        share.is_admin_delegate = bool(payload.get('is_admin_delegate'))
        share.granted_by = requester_identifier

        db.commit()
        db.refresh(share)
        return {
            "success": True,
            "share": share.to_dict()
        }
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}


def add_comment(schedule_id: int, requester_identifier: str, payload: Dict, db: Session) -> Dict:
    schedule = _get_schedule(db, schedule_id)
    if not schedule:
        return {"success": False, "error": "schedule not found"}

    allowed, error, share = _check_permission(db, schedule, requester_identifier, 'comment')
    if not allowed:
        return {"success": False, "error": error}

    if payload['author_identifier'] != requester_identifier:
        return {"success": False, "error": "author identifier must match requester"}

    try:
        comment = ScheduleComment(
            schedule_id=schedule_id,
            author_identifier=payload['author_identifier'],
            author_display_name=payload.get('author_display_name'),
            content=payload['content'],
            is_admin_note=True if schedule.owner_identifier == requester_identifier else bool(share.is_admin_delegate) if share else False
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return {
            "success": True,
            "comment": comment.to_dict()
        }
    except Exception as exc:
        db.rollback()
        return {"success": False, "error": str(exc)}
