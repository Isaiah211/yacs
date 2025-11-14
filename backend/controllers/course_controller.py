from typing import List, Dict, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..tables.course import Course
from ..tables.course_corequisite import CourseCorequisite
from sqlalchemy.exc import IntegrityError
from ..tables.course_prerequisite import CoursePrerequisite
from sqlalchemy import or_, and_, func
from datetime import datetime

def create_course(course_data: Dict, db: Session) -> Dict:
    """
    Create a new course.
    
    Args:
        course_data (Dict): Dictionary containing course information
        db (Session): Database session
    
    Returns:
        Dict: Response with success status and course data or error message
    """
    try:
        # Check if course already exists
        existing = db.query(Course).filter(
            Course.course_code == course_data["course_code"],
            Course.semester == course_data["semester"]
        ).first()
        
        if existing:
            return {"success": False, "error": "Course already exists for this semester"}
        
        # Create new course
        new_course = Course(**course_data)
        db.add(new_course)
        db.commit()
        db.refresh(new_course)
        
        return {
            "success": True,
            "message": "Course created successfully",
            "course": new_course.to_dict()
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

def get_courses(semester: Optional[str] = None, department: Optional[str] = None, db: Session = None) -> Dict:
    """
    Get all courses with optional filters.
    
    Args:
        semester (str, optional): Filter by semester
        department (str, optional): Filter by department
        db (Session): Database session
    
    Returns:
        Dict: Response with success status and list of courses
    """
    try:
        query = db.query(Course)
        
        if semester:
            query = query.filter(Course.semester == semester)
        if department:
            query = query.filter(Course.department == department)
            
        courses = query.all()
        return {
            "success": True,
            "courses": [course.to_dict() for course in courses]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_course(course_code: str, semester: str, db: Session) -> Dict:
    """
    Get a specific course by code and semester.
    
    Args:
        course_code (str): The course code
        semester (str): The semester
        db (Session): Database session
    
    Returns:
        Dict: Response with success status and course data
    """
    try:
        course = db.query(Course).filter(
            Course.course_code == course_code,
            Course.semester == semester
        ).first()
        
        if not course:
            return {"success": False, "error": "Course not found"}
            
        return {"success": True, "course": course.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_course(course_code: str, semester: str, updates: Dict, db: Session) -> Dict:
    """
    Update a course's details.
    
    Args:
        course_code (str): The course code
        semester (str): The semester
        updates (Dict): The fields to update
        db (Session): Database session
    
    Returns:
        Dict: Response with success status and updated course data
    """
    try:
        course = db.query(Course).filter(
            Course.course_code == course_code,
            Course.semester == semester
        ).first()
        
        if not course:
            return {"success": False, "error": "Course not found"}
            
        # Update allowed fields
        for key, value in updates.items():
            if hasattr(course, key) and value is not None:
                setattr(course, key, value)
                
        db.commit()
        db.refresh(course)
        return {
            "success": True,
            "message": "Course updated successfully",
            "course": course.to_dict()
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

def delete_course(course_code: str, semester: str, db: Session) -> Dict:
    """
    Delete a course.
    
    Args:
        course_code (str): The course code
        semester (str): The semester
        db (Session): Database session
    
    Returns:
        Dict: Response with success status
    """
    try:
        course = db.query(Course).filter(
            Course.course_code == course_code,
            Course.semester == semester
        ).first()
        
        if not course:
            return {"success": False, "error": "Course not found"}
            
        db.delete(course)
        db.commit()
        return {
            "success": True,
            "message": f"Course {course_code} for {semester} has been deleted"
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    """
    Get all courses or courses for a specific semester.
    
    Args:
        semester (Optional[str]): Filter courses by semester
    
    Returns:
        Dict: Response with success status and list of courses
    """
    try:
        if semester:
            filtered_courses = [c for c in courses if c.get('semester') == semester]
            return {
                "success": True,
                "courses": filtered_courses,
                "count": len(filtered_courses),
                "semester": semester
            }
        
        return {
            "success": True,
            "courses": courses,
            "count": len(courses)
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to get courses: {str(e)}"}

def get_course_by_id(course_id: str, semester: str) -> Dict:
    """
    Get a specific course by ID and semester.
    
    Args:
        course_id (str): Course ID
        semester (str): Semester
    
    Returns:
        Dict: Response with success status and course data
    """
    try:
        course = next((c for c in courses if c['cid'] == course_id and c['semester'] == semester), None)
        
        if not course:
            return {"success": False, "error": "Course not found"}
        
        return {
            "success": True,
            "course": course
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to get course: {str(e)}"}

def update_course(course_id: str, semester: str, update_data: Dict) -> Dict:
    """
    Update an existing course.
    
    Args:
        course_id (str): Course ID
        semester (str): Semester
        update_data (Dict): Dictionary containing fields to update
    
    Returns:
        Dict: Response with success status and updated course data
    """
    try:
        course_index = next((i for i, c in enumerate(courses) if c['cid'] == course_id and c['semester'] == semester), None)
        
        if course_index is None:
            return {"success": False, "error": "Course not found"}
        
        # Update course data
        courses[course_index].update(update_data)
        courses[course_index]['updated_at'] = datetime.now().isoformat()
        
        return {
            "success": True,
            "message": "Course updated successfully",
            "course": courses[course_index]
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to update course: {str(e)}"}

def delete_course(course_data: Dict) -> Dict:
    """
    Delete a course from the system.
    
    Args:
        course_data (Dict): Dictionary containing course identification
                           Expected keys: name, cid (optional), semester
    
    Returns:
        Dict: Response with success status and message
    """
    try:
        # Validate required fields
        if 'name' not in course_data or 'semester' not in course_data:
            return {"success": False, "error": "Missing required fields: name and semester"}
        
        name = course_data['name']
        semester = course_data['semester']
        cid = course_data.get('cid')
        
        # Find and remove the course
        course_to_remove = None
        for i, course in enumerate(courses):
            if (course['name'] == name and 
                course['semester'] == semester and 
                (cid is None or course['cid'] == cid)):
                course_to_remove = i
                break
        
        if course_to_remove is None:
            return {"success": False, "error": "Course not found"}
        
        removed_course = courses.pop(course_to_remove)
        
        return {
            "success": True,
            "message": "Course deleted successfully",
            "deleted_course": removed_course
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to delete course: {str(e)}"}

def delete_course_by_id(course_id: str, semester: str) -> Dict:
    """
    Delete a course by ID and semester.
    
    Args:
        course_id (str): Course ID
        semester (str): Semester
    
    Returns:
        Dict: Response with success status and message
    """
    try:
        course_index = next((i for i, c in enumerate(courses) if c['cid'] == course_id and c['semester'] == semester), None)
        
        if course_index is None:
            return {"success": False, "error": "Course not found"}
        
        removed_course = courses.pop(course_index)
        
        return {
            "success": True,
            "message": "Course deleted successfully",
            "deleted_course": removed_course
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to delete course: {str(e)}"}

def get_semesters() -> Dict:
    """
    Get all unique semesters from courses.
    
    Returns:
        Dict: Response with success status and list of semesters
    """
    try:
        semesters = list(set(course.get('semester') for course in courses if course.get('semester')))
        semesters.sort()
        
        return {
            "success": True,
            "semesters": semesters,
            "count": len(semesters)
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to get semesters: {str(e)}"}

def clear_all_courses() -> Dict:
    """
    Clear all courses from the system (useful for testing).
    
    Returns:
        Dict: Response with success status and message
    """
    global courses
    courses_count = len(courses)
    courses = []
    
    return {
        "success": True,
        "message": f"Cleared {courses_count} courses successfully"
    }

def get_course_with_prerequisites(course_id: int, db: Session):
    """get a course with all its prerequisites."""
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not course:
        return None
    
    #get all prerequisites
    prerequisites = db.query(Course).join(
        CoursePrerequisite,
        CoursePrerequisite.prerequisite_id == Course.id
    ).filter(
        CoursePrerequisite.course_id == course_id
    ).all()
    
    return {
        "id": course.id,
        "course_code": course.course_code,
        "title": course.title,
        "prerequisites": [
            {
                "id": prereq.id,
                "course_code": prereq.course_code,
                "title": prereq.title
            }
            for prereq in prerequisites
        ]
    }

def add_prerequisite(course_code: str, prerequisite_code: str, db: Session):
    """add a prerequisite to a course"""
    #find both courses
    course = db.query(Course).filter(Course.course_code == course_code).first()
    prerequisite = db.query(Course).filter(Course.course_code == prerequisite_code).first()
    
    if not course or not prerequisite:
        raise ValueError("Course or prerequisite not found")
    
    #create relationship (setup relationships in CoursePrerequisite table if want to use in future)
    prereq_relation = CoursePrerequisite(
        course_id=course.id,
        prerequisite_id=prerequisite.id
    )
    
    db.add(prereq_relation)
    db.commit()
    
    return {"message": f"Added {prerequisite_code} as prerequisite for {course_code}"}

def get_courses_requiring_prerequisite(prerequisite_code: str, db: Session):
    """find all courses that require a specific prerequisite"""
    prerequisite = db.query(Course).filter(
        Course.course_code == prerequisite_code
    ).first()
    
    if not prerequisite:
        return []
    
    courses = db.query(Course).join(
        CoursePrerequisite,
        CoursePrerequisite.course_id == Course.id
    ).filter(
        CoursePrerequisite.prerequisite_id == prerequisite.id
    ).all()
    
    return courses

def check_prerequisites_met(student_courses: list[str], target_course: str, db: Session):
    """check if student has completed all prerequisites for a course"""
    course = db.query(Course).filter(Course.course_code == target_course).first()
    
    if not course:
        return False
    
    #get required prerequisites
    required_prereqs = db.query(Course.course_code).join(
        CoursePrerequisite,
        CoursePrerequisite.prerequisite_id == Course.id
    ).filter(
        CoursePrerequisite.course_id == course.id
    ).all()
    
    required_codes = {prereq[0] for prereq in required_prereqs}
    student_codes = set(student_courses)
    
    missing = required_codes - student_codes
    
    return {
        "can_enroll": len(missing) == 0,
        "missing_prerequisites": list(missing)
    }

def get_course_with_corequisites(course_id: int, db: Session):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return None

    coreqs = (
        db.query(Course)
        .join(CourseCorequisite, CourseCorequisite.corequisite_id == Course.id)
        .filter(CourseCorequisite.course_id == course_id)
        .all()
    )

    return {
        "id": course.id,
        "course_code": course.course_code,
        "title": getattr(course, "title", None),
        "corequisites": [
            {
                "id": c.id,
                "course_code": c.course_code,
                "title": getattr(c, "title", None),
            }
            for c in coreqs
        ],
    }

def add_corequisite(course_code: str, corequisite_code: str, db: Session):
    course = db.query(Course).filter(Course.course_code == course_code).first()
    coreq = db.query(Course).filter(Course.course_code == corequisite_code).first()

    if not course or not coreq:
        raise ValueError("Course or corequisite not found")

    exists = (
        db.query(CourseCorequisite)
        .filter(
            CourseCorequisite.course_id == course.id,
            CourseCorequisite.corequisite_id == coreq.id,
        )
        .first()
    )
    if exists:
        return {"message": "Corequisite already exists"}

    db.add(CourseCorequisite(course_id=course.id, corequisite_id=coreq.id))
    db.commit()
    return {"message": f"Added {corequisite_code} as corequisite for {course_code}"}

def get_courses_requiring_corequisite(corequisite_code: str, db: Session):
    coreq = db.query(Course).filter(Course.course_code == corequisite_code).first()
    if not coreq:
        return []

    courses = (
        db.query(Course)
        .join(CourseCorequisite, CourseCorequisite.course_id == Course.id)
        .filter(CourseCorequisite.corequisite_id == coreq.id)
        .all()
    )
    return courses

def search_courses(
    db: Session,
    query: Optional[str] = None,
    semester: Optional[str] = None,
    department: Optional[str] = None,
    credits: Optional[int] = None,
    instructor: Optional[str] = None,
    min_credits: Optional[int] = None,
    max_credits: Optional[int] = None,
    level: Optional[str] = None, #1000-4000
    has_capacity: Optional[bool] = None,
    sort_by: Optional[str] = "course_code",
    sort_order: Optional[str] = "asc",
    limit: Optional[int] = 100,
    offset: Optional[int] = 0
) -> Dict:
    """
    search/filter for courses

    args:
        db: database session
        query: search text like searches in course code, name, description
        semester: filter by semester
        department: filter by department
        credits: how many credits
        instructor: instructor name
        min_credits: min credits
        max_credits: max credits
        level: course level
        has_capacity: courses with available seats
        sort_by: field to sort by (course code, name, credits, department)
        sort_order: sort direction
        limit: max results to return
        offset: number of results to skip

    returns dict with success status, courses list, and other data
    """
    try:
        base_query = db.query(Course)
    
        #apply filters
        filters = []
    
        #txt search across whatevr fields
        if query:
            search_term = f"%{query}%"
            filters.append(
                or_(
                    Course.course_code.ilike(search_term),
                    Course.name.ilike(search_term),
                    Course.description.ilike(search_term),
                    Course.instructor.ilike(search_term)
                )
            )
    
        #semester filter
        if semester:
            filters.append(Course.semester == semester)
    
        #department filter
        if department:
            filters.append(Course.department == department)
    
        #credits filters
        if credits is not None:
            filters.append(Course.credits == credits)
        if min_credits is not None:
            filters.append(Course.credits >= min_credits)
        if max_credits is not None:
            filters.append(Course.credits <= max_credits)
    
        #instructor filter
        if instructor:
            filters.append(Course.instructor.ilike(f"%{instructor}%"))
    
        #course level filter
        if level:
            #get level from course code by taking first digit for the level
            level_digit = level[0] if level else None
            if level_digit:
                filters.append(Course.course_code.ilike(f"%-{level_digit}___"))
    
        #capacity availability filter
        if has_capacity:
            filters.append(Course.capacity > 0)
    
        #apply filters
        if filters:
            base_query = base_query.filter(and_(*filters))
    
        #get total count before pagination
        total_count = base_query.count()
    
        #sorting
        sort_column = getattr(Course, sort_by, Course.course_code)
        if sort_order.lower() == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())
    
        #pagination
        base_query = base_query.limit(limit).offset(offset)
    
        #execute query
        courses = base_query.all()
    
        return {
            "success": True,
            "courses": [course.to_dict() for course in courses],
            "metadata": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "count": len(courses),
                "has_more": (offset + len(courses)) < total_count
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_departments(db: Session, semester: Optional[str] = None) -> Dict:
    """
    gets list of depts

    args:
        db: database session
        semester: semester filter

    returns dict with success status and list of depts
    """
    try:
        query = db.query(Course.department).distinct()
    
        if semester:
            query = query.filter(Course.semester == semester)
    
        departments = [dept[0] for dept in query.all()]
        departments.sort()
    
        return {
            "success": True,
            "departments": departments
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_instructors(db: Session, semester: Optional[str] = None, department: Optional[str] = None) -> Dict:
    """
    get list of instructors

    args:
        db: database session
        semester: semester filter
        department: department filter

    returns dict with success status and instructors
    """
    try:
        query = db.query(Course.instructor).distinct().filter(Course.instructor.isnot(None))
    
        if semester:
            query = query.filter(Course.semester == semester)
        if department:
            query = query.filter(Course.department == department)
    
        instructors = [instr[0] for instr in query.all()]
        instructors.sort()
    
        return {
            "success": True,
            "instructors": instructors
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_course_levels(db: Session, department: Optional[str] = None) -> Dict:
    """
    get available course levels

    args:
        db: database session
        department: department filter

    returns dict with success status and list of levels
    """
    try:
        query = db.query(Course.course_code)
    
        if department:
            query = query.filter(Course.department == department)
    
        course_codes = [code[0] for code in query.all()]
    
        #get level from course code by taking first digit for the level
        levels = set()
        for code in course_codes:
            if '-' in code:
                number_part = code.split('-')[1]
                if number_part and number_part[0].isdigit():
                    level = number_part[0] + "000"
                    levels.add(level)
    
        levels_list = sorted(list(levels))
    
        return {
            "success": True,
            "levels": levels_list
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_courses_by_department_level(db: Session, department: str, level: str, semester: Optional[str] = None) -> Dict:
    """
    get courses by department and level

    args:
        db: database session
        department: department code
        level: course level
        semester: semester filter

    returns dict with success status and list of courses
    """
    try:
        query = db.query(Course).filter(Course.department == department)
    
        if semester:
            query = query.filter(Course.semester == semester)
    
        #filter by level
        level_digit = level[0] if level else None
        if level_digit:
            query = query.filter(Course.course_code.ilike(f"%-{level_digit}___"))
    
        courses = query.order_by(Course.course_code).all()
    
        return {
            "success": True,
            "courses": [course.to_dict() for course in courses]
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

#conflict detection functions
def has_day_overlap(days1: str, days2: str) -> bool:
    """
    check if two day strings have any overlapping days
    args take strings like "MWR", "TF", etc
    returns true if theres at least one common day
    """
    if not days1 or not days2:
        return False
    
    #convert to sets and check intersection
    set1 = set(days1.upper())
    set2 = set(days2.upper())
    return bool(set1 & set2)


def has_time_overlap(start1, end1, start2, end2) -> bool:
    """
    check if two time ranges overlap
    args take start and end times of two courses
    returns true if time ranges overlap
    """
    if not all([start1, end1, start2, end2]):
        return False

    #convert to datetime.time if needed
    from datetime import time as dt_time
    
    def to_time(t):
        if isinstance(t, dt_time):
            return t
        if isinstance(t, str):
            parts = t.split(':')
            return dt_time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
        return t
    
    start1 = to_time(start1)
    end1 = to_time(end1)
    start2 = to_time(start2)
    end2 = to_time(end2)
    
    #check if ranges overlap
    return start1 < end2 and start2 < end1


def check_course_conflict(course1: Course, course2: Course) -> Dict:
    """
    check if two courses have a scheduling conflict
    returns dict with conflict status and details
    """
    #same course
    if course1.id == course2.id:
        return {
            "has_conflict": False,
            "reason": None
        }
    
    #different semesters
    if course1.semester != course2.semester:
        return {
            "has_conflict": False,
            "reason": None
        }
    
    #first check if both have schedule information
    if not (course1.days_of_week and course1.start_time and course1.end_time):
        return {
            "has_conflict": False,
            "reason": "course 1 has no schedule information"
        }
    
    if not (course2.days_of_week and course2.start_time and course2.end_time):
        return {
            "has_conflict": False,
            "reason": "course 2 has no schedule information"
        }
    
    #check for day overlap
    if not has_day_overlap(course1.days_of_week, course2.days_of_week):
        return {
            "has_conflict": False,
            "reason": "no overlapping days"
        }
    
    #check for time overlap
    if not has_time_overlap(course1.start_time, course1.end_time, course2.start_time, course2.end_time):
        return {
            "has_conflict": False,
            "reason": "no overlapping times"
        }
    
    #both day and time overlap; conflict
    overlapping_days = set(course1.days_of_week.upper()) & set(course2.days_of_week.upper())
    
    return {
        "has_conflict": True,
        "reason": f"Time conflict on {', '.join(sorted(overlapping_days))}",
        "details": {
            "course1": {
                "code": course1.course_code,
                "name": course1.name,
                "days": course1.days_of_week,
                "time": f"{course1.start_time} - {course1.end_time}",
                "location": course1.location
            },
            "course2": {
                "code": course2.course_code,
                "name": course2.name,
                "days": course2.days_of_week,
                "time": f"{course2.start_time} - {course2.end_time}",
                "location": course2.location
            }
        }
    }


def check_schedule_conflicts(course_ids: List[int], db: Session) -> Dict:
    #check for conflicts from course ids
    try:
        #get all courses
        courses = db.query(Course).filter(Course.id.in_(course_ids)).all()
        
        if len(courses) != len(course_ids):
            return {
                "success": False,
                "error": "One or more courses not found"
            }
        
        conflicts = []
        
        #check each pair of courses
        for i in range(len(courses)):
            for j in range(i + 1, len(courses)):
                result = check_course_conflict(courses[i], courses[j])
                if result["has_conflict"]:
                    conflicts.append(result)
        
        return {
            "success": True,
            "has_conflicts": len(conflicts) > 0,
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "courses_checked": [c.to_dict() for c in courses]
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_schedule_conflicts_by_codes(course_codes: List[str], semester: str, db: Session) -> Dict:
    #check for conflicts by course codes
    try:
        #get all courses
        courses = db.query(Course).filter(
            Course.course_code.in_(course_codes),
            Course.semester == semester
        ).all()
        
        if len(courses) != len(course_codes):
            found_codes = {c.course_code for c in courses}
            missing = set(course_codes) - found_codes
            return {
                "success": False,
                "error": f"Courses not found: {', '.join(missing)}"
            }
        
        conflicts = []
        
        #check each pair of courses
        for i in range(len(courses)):
            for j in range(i + 1, len(courses)):
                result = check_course_conflict(courses[i], courses[j])
                if result["has_conflict"]:
                    conflicts.append(result)
        
        return {
            "success": True,
            "has_conflicts": len(conflicts) > 0,
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "courses_checked": [c.to_dict() for c in courses]
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def find_non_conflicting_courses(enrolled_course_ids: List[int], semester: str, db: Session, department: Optional[str] = None, level: Optional[str] = None) -> Dict:
    #find courses that dont conflict with currently enrolled courses
    try:
        #get enrolled courses
        enrolled_courses = db.query(Course).filter(
            Course.id.in_(enrolled_course_ids)
        ).all()
        
        #build query for available courses
        query = db.query(Course).filter(Course.semester == semester)
        
        if department:
            query = query.filter(Course.department == department)
        
        if level:
            level_digit = level[0] if level else None
            if level_digit:
                query = query.filter(Course.course_code.ilike(f"%-{level_digit}___"))
        
        #exclude already enrolled courses
        if enrolled_course_ids:
            query = query.filter(~Course.id.in_(enrolled_course_ids))
        
        available_courses = query.all()
        
        #check each available course for conflicts
        non_conflicting = []
        conflicting = []
        
        for course in available_courses:
            has_conflict = False
            conflict_with = []
            
            for enrolled in enrolled_courses:
                result = check_course_conflict(enrolled, course)
                if result["has_conflict"]:
                    has_conflict = True
                    conflict_with.append({
                        "course_code": enrolled.course_code,
                        "course_name": enrolled.name,
                        "reason": result["reason"]
                    })
            
            if has_conflict:
                conflicting.append({
                    "course": course.to_dict(),
                    "conflicts_with": conflict_with
                })
            else:
                non_conflicting.append(course.to_dict())
        
        return {
            "success": True,
            "semester": semester,
            "enrolled_courses": [c.to_dict() for c in enrolled_courses],
            "non_conflicting_courses": non_conflicting,
            "conflicting_courses": conflicting,
            "stats": {
                "total_available": len(available_courses),
                "non_conflicting": len(non_conflicting),
                "conflicting": len(conflicting)
            }
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}
    