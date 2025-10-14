from typing import List, Dict, Optional
import uuid
from datetime import datetime

# In-memory storage for courses (replace with database later)
courses = []

def add_course(course_data: Dict) -> Dict:
    """
    Add a new course to the system.
    
    Args:
        course_data (Dict): Dictionary containing course information
                           Expected keys: name, cid, semester
    
    Returns:
        Dict: Response with success status and course data or error message
    """
    try:
        # Validate required fields
        required_fields = ['name', 'semester']
        for field in required_fields:
            if field not in course_data or not course_data[field]:
                return {"success": False, "error": f"Missing required field: {field}"}
        
        # Generate course ID if not provided
        if 'cid' not in course_data or not course_data['cid']:
            course_data['cid'] = str(uuid.uuid4())
        
        # Check if course already exists
        existing_course = next((c for c in courses if c['cid'] == course_data['cid'] and c['semester'] == course_data['semester']), None)
        if existing_course:
            return {"success": False, "error": "Course already exists for this semester"}
        
        # Add timestamp
        course_data['created_at'] = datetime.now().isoformat()
        
        # Add course to storage
        courses.append(course_data)
        
        return {
            "success": True, 
            "message": "Course added successfully",
            "course": course_data
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to add course: {str(e)}"}

def get_courses(semester: Optional[str] = None) -> Dict:
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
