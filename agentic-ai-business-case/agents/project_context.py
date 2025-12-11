"""
Utility to read and provide project context to all agents
"""
import os
import json
from config import input_folder_dir_path

def get_project_context():
    """
    Read project information from the input folder.
    Returns a formatted string with project context.
    """
    project_info_file = os.path.join(input_folder_dir_path, 'input', 'project_info.json')
    
    if not os.path.exists(project_info_file):
        return ""
    
    try:
        with open(project_info_file, 'r', encoding='utf-8') as f:
            project_info = json.load(f)
        
        context = f"""
**PROJECT CONTEXT:**
- Project Name: {project_info.get('projectName', 'N/A')}
- Customer Name: {project_info.get('customerName', 'N/A')}
- Target AWS Region: {project_info.get('awsRegion', 'N/A')}
- Project Description: {project_info.get('projectDescription', 'N/A')}

**IMPORTANT: All analysis, recommendations, and outputs must align with the project description and objectives stated above.**
"""
        return context
    except Exception as e:
        print(f"Warning: Could not read project context: {str(e)}")
        return ""

def get_project_info_dict():
    """
    Read project information and return as dictionary.
    Includes uploaded filenames if available.
    """
    project_info_file = os.path.join(input_folder_dir_path, 'input', 'project_info.json')
    
    if not os.path.exists(project_info_file):
        return {}
    
    try:
        with open(project_info_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not read project info: {str(e)}")
        return {}

def get_case_input_directory():
    """
    Get the case-specific input directory path.
    Returns case-specific path if caseId exists, otherwise returns base input directory.
    
    IMPORTANT: Files should ONLY exist in case-specific subdirectories.
    Base directory is only used as fallback for backward compatibility.
    """
    project_info = get_project_info_dict()
    case_id = project_info.get('caseId')
    
    if case_id:
        case_dir = os.path.join(input_folder_dir_path, 'input', case_id)
        if os.path.exists(case_dir):
            print(f"✓ Using case-specific input directory: {case_dir}")
            return case_dir
        else:
            print(f"⚠ Case directory does not exist: {case_dir}")
    
    # Fallback to base input directory (backward compatibility only)
    base_dir = os.path.join(input_folder_dir_path, 'input')
    print(f"⚠ Using base input directory (no case ID found): {base_dir}")
    return base_dir

def get_input_file_path(filename):
    """
    Get the full path to an input file from case-specific directory.
    
    Args:
        filename: Name of the file (e.g., 'RVTools_Export.xlsx')
    
    Returns:
        Full path to the file in case-specific directory
    
    IMPORTANT: Files should ONLY be read from case-specific subdirectories.
    No fallback to base directory for uploaded files.
    """
    case_dir = get_case_input_directory()
    file_path = os.path.join(case_dir, filename)
    
    # Return the case-specific path (will fail if file doesn't exist, which is correct)
    return file_path
