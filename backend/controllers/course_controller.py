from typing import List, Dict, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..tables.course import Course
from ..tables.course_corequisite import CourseCorequisite
from sqlalchemy.exc import IntegrityError
from ..tables.course_prerequisite import CoursePrerequisite

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
