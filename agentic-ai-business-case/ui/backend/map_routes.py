"""
MAP Assessment API Routes
Endpoints for MAP assessment features including modernization, migration strategy,
resource planning, learning pathways, business case validation, and architecture diagrams.
"""
from flask import Blueprint, request, jsonify
import os
import sys
import tempfile
import pandas as pd
import json
from werkzeug.utils import secure_filename
from datetime import datetime
import io
import fitz  # PyMuPDF for PDF processing

# Add project root to Python path
# Get the absolute path to the agentic-ai-business-case directory (two levels up from this file)
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.dirname(BACKEND_DIR)
PROJECT_ROOT = os.path.dirname(UI_DIR)  # This is agentic-ai-business-case/

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    print(f"✓ Added PROJECT_ROOT to sys.path: {PROJECT_ROOT}")

# Import prompt library functions
from prompt_library.modernization_opportunity.inventory_analysis_prompt import get_invventory_analysis_prompt
from prompt_library.modernization_opportunity.onprem_architecture_prompt import get_onprem_architecture_prompt
from prompt_library.modernization_opportunity.modernization_pathways_prompt import get_modernization_pathways_prompt
from prompt_library.migration_patterns.migration_patterns_prompt import get_migration_patterns_prompt
from prompt_library.resource_planning.resource_planning_prompt import get_resource_planning_prompt
from prompt_library.learning_pathway.learning_pathway_prompt import get_learning_pathway_prompt
from prompt_library.business_case_validation.business_case_validation_prompt import get_business_case_validation_prompt
from prompt_library.architecture_diagram.architecture_diagram_prompt import get_architecture_diagram_prompt

# Import utility functions
from utils.bedrock_client import (
    invoke_bedrock_model_with_reasoning,
    invoke_bedrock_model_for_image_analysis,
    invoke_bedrock_model_without_reasoning,
    invoke_bedrock_model_claude_3_5
)
from utils.image_processor import resize_image, convert_image_to_base64, get_image_type
from utils.pdf_processor import convert_pdf_to_images, prepare_content_for_claude
from utils.file_handler import process_pdf_bytes

# Create Blueprint
map_bp = Blueprint('map', __name__, url_prefix='/api/map')

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'jpg', 'jpeg', 'png', 'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_size(file):
    """Validate file size"""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return False, f"File size exceeds {MAX_FILE_SIZE / (1024*1024)}MB limit"
    return True, "Valid"

# ============================================================================
# MODERNIZATION OPPORTUNITY ENDPOINTS
# ============================================================================

@map_bp.route('/modernization/analyze-inventory', methods=['POST'])
def analyze_inventory():
    """Analyze IT inventory data"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        
        # Validate file size
        is_valid, error_msg = validate_file_size(file)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Read CSV data
        try:
            inventory_df = pd.read_csv(file)
            csv_text = inventory_df.to_string()
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error reading CSV: {str(e)}'}), 400
        
        # Check for custom prompt
        custom_prompt = request.form.get('custom_prompt')
        
        if custom_prompt:
            # Use custom prompt, replace placeholder with CSV data
            prompt = custom_prompt.replace('{inventory_csv}', csv_text)
            # Also try without placeholder if not found
            if '{inventory_csv}' not in custom_prompt:
                prompt = f"{custom_prompt}\n\nIT Inventory Data:\n{csv_text}"
        else:
            # Use default prompt
            prompt = get_invventory_analysis_prompt(inventory_df)
        
        # Generate analysis
        result = invoke_bedrock_model_with_reasoning(prompt)
        
        return jsonify({
            'success': True,
            'analysis': result['response'],
            'reasoning': result.get('reasoning', ''),
            'inventoryRecords': len(inventory_df),
            'usedCustomPrompt': bool(custom_prompt)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@map_bp.route('/modernization/analyze-architecture', methods=['POST'])
def analyze_architecture():
    """Analyze on-premises architecture from image"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        
        # Validate file size
        is_valid, error_msg = validate_file_size(file)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Process image
        image_bytes = file.read()
        image_bytes = resize_image(image_bytes)
        encoded_image = convert_image_to_base64(image_bytes)
        image_type = get_image_type(file.filename)
        
        # Generate analysis
        prompt = get_onprem_architecture_prompt()
        arch_description = invoke_bedrock_model_for_image_analysis(
            encoded_image, prompt, image_type
        )
        
        return jsonify({
            'success': True,
            'analysis': arch_description
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@map_bp.route('/modernization/recommend-pathways', methods=['POST'])
def recommend_pathways():
    """Generate modernization pathway recommendations"""
    try:
        data = request.json
        
        if 'inventoryData' not in data:
            return jsonify({'success': False, 'message': 'Inventory data required'}), 400
        
        # Convert inventory data back to DataFrame
        inventory_df = pd.DataFrame(data['inventoryData'])
        scope_text = data.get('scope', '')
        architecture_description = data.get('architectureDescription', None)
        
        # Generate recommendations
        prompt = get_modernization_pathways_prompt(
            inventory_df, architecture_description, scope_text
        )
        result = invoke_bedrock_model_with_reasoning(prompt)
        
        return jsonify({
            'success': True,
            'recommendations': result['response'],
            'reasoning': result.get('reasoning', '')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# MIGRATION STRATEGY ENDPOINTS
# ============================================================================

@map_bp.route('/migration-strategy/generate', methods=['POST'])
def generate_migration_strategy():
    """Generate migration strategy from AWS Calculator data"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        
        # Validate file size
        is_valid, error_msg = validate_file_size(file)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Parse AWS Calculator CSV
        csv_data = file.read().decode('utf-8')
        lines = csv_data.splitlines()
        
        # Find the start of the detailed estimate section
        # Look for common headers in English or German
        start_idx = 0
        header_patterns = [
            "Group hierarchy,Region,Description",
            "Gruppenhierarchie,Region,Beschreibung",
            "Group hierarchy",
            "Gruppenhierarchie"
        ]
        
        for i, line in enumerate(lines):
            if any(pattern in line for pattern in header_patterns):
                start_idx = i
                break
        
        # Read CSV with error handling for malformed lines
        try:
            calc_df = pd.read_csv(
                io.StringIO("\n".join(lines[start_idx:])), 
                encoding="utf-8",
                on_bad_lines='skip',  # Skip malformed lines
                quoting=1  # QUOTE_ALL to handle embedded commas
            )
        except Exception as e:
            # Fallback: try with different settings
            try:
                calc_df = pd.read_csv(
                    io.StringIO("\n".join(lines[start_idx:])), 
                    encoding="utf-8",
                    on_bad_lines='skip',
                    error_bad_lines=False
                )
            except:
                # Last resort: read with minimal parsing
                calc_df = pd.read_csv(
                    io.StringIO("\n".join(lines[start_idx:])), 
                    encoding="utf-8",
                    on_bad_lines='skip',
                    quoting=3  # QUOTE_NONE
                )
        
        # Get scope text
        scope_text = request.form.get('scope', '')
        
        # Check for custom prompt
        custom_prompt = request.form.get('custom_prompt')
        
        if custom_prompt:
            # Use custom prompt, replace placeholders
            services_summary = calc_df.to_string()
            prompt = custom_prompt.replace('{services_summary}', services_summary)
            prompt = prompt.replace('{scope_text}', scope_text if scope_text else '')
            # Also try without placeholders if not found
            if '{services_summary}' not in custom_prompt:
                prompt = f"{custom_prompt}\n\nAWS Calculator Data:\n{services_summary}\n\nScope: {scope_text}"
        else:
            # Use default prompt
            prompt = get_migration_patterns_prompt(calc_df, scope_text)
        
        # Generate strategy
        strategy_text = invoke_bedrock_model_without_reasoning(prompt)
        
        return jsonify({
            'success': True,
            'strategy': strategy_text,
            'recordsProcessed': len(calc_df),
            'usedCustomPrompt': bool(custom_prompt)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# RESOURCE PLANNING ENDPOINTS
# ============================================================================

@map_bp.route('/resource-planning/generate', methods=['POST'])
def generate_resource_planning():
    """Generate resource planning recommendations"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        
        # Validate file size
        is_valid, error_msg = validate_file_size(file)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Read resource profile CSV
        resource_df = pd.read_csv(file)
        
        # Get additional context
        migration_strategy = request.form.get('migrationStrategy', '')
        wave_planning = request.form.get('wavePlanning', '')
        
        # Check for custom prompt
        custom_prompt = request.form.get('custom_prompt')
        
        if custom_prompt:
            # Use custom prompt, replace placeholders
            resource_details = resource_df.to_string()
            prompt = custom_prompt.replace('{migration_strategy}', migration_strategy)
            prompt = prompt.replace('{wave_planning_data}', wave_planning)
            prompt = prompt.replace('{resource_details}', resource_details)
            # Also try without placeholders if not found
            if '{resource_details}' not in custom_prompt:
                prompt = f"{custom_prompt}\n\nResource Details:\n{resource_details}\n\nMigration Strategy:\n{migration_strategy}\n\nWave Planning:\n{wave_planning}"
        else:
            # Use default prompt
            prompt = get_resource_planning_prompt(resource_df, migration_strategy, wave_planning)
        
        # Generate resource plan
        result = invoke_bedrock_model_with_reasoning(prompt)
        
        return jsonify({
            'success': True,
            'resourcePlan': result['response'],
            'reasoning': result.get('reasoning', ''),
            'usedCustomPrompt': bool(custom_prompt)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# LEARNING PATHWAY ENDPOINTS
# ============================================================================

@map_bp.route('/learning-pathway/generate', methods=['POST'])
def generate_learning_pathway():
    """Generate personalized learning pathway"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        
        # Validate file size
        is_valid, error_msg = validate_file_size(file)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Read training data CSV
        training_df = pd.read_csv(file)
        
        # Get parameters
        target_role = request.form.get('targetRole', '')
        experience_level = request.form.get('experienceLevel', '')
        duration = request.form.get('duration', '')
        
        # Check for custom prompt
        custom_prompt = request.form.get('custom_prompt')
        
        if custom_prompt:
            # Use custom prompt, replace placeholders
            training_data = training_df.to_string()
            prompt = custom_prompt.replace('{training_data}', training_data)
            prompt = prompt.replace('{target_role}', target_role)
            prompt = prompt.replace('{target_experience}', experience_level)
            prompt = prompt.replace('{learning_duration}', duration)
            # Also try without placeholders if not found
            if '{training_data}' not in custom_prompt:
                prompt = f"{custom_prompt}\n\nTraining Data:\n{training_data}\n\nTarget Role: {target_role}\nExperience Level: {experience_level}\nDuration: {duration}"
        else:
            # Use default prompt
            prompt = get_learning_pathway_prompt(training_df, target_role, experience_level, duration)
        
        # Generate learning pathway
        result = invoke_bedrock_model_with_reasoning(prompt)
        
        return jsonify({
            'success': True,
            'learningPathway': result['response'],
            'reasoning': result.get('reasoning', ''),
            'usedCustomPrompt': bool(custom_prompt)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# BUSINESS CASE VALIDATION ENDPOINTS
# ============================================================================

@map_bp.route('/business-validation/validate', methods=['POST'])
def validate_business_case():
    """Validate business case document"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        
        # Validate file size
        is_valid, error_msg = validate_file_size(file)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Process PDF - read bytes directly from Flask file object
        max_pages = 10
        pdf_bytes = file.read()
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_images = convert_pdf_to_images(pdf_document, max_pages)
        pdf_document.close()
        
        # Check for custom prompt
        custom_prompt = request.form.get('custom_prompt')
        
        if custom_prompt:
            # Use custom prompt
            prompt = custom_prompt
        else:
            # Use default prompt
            prompt = get_business_case_validation_prompt()
        
        # Prepare content for Claude with images
        pdf_content_with_prompt = prepare_content_for_claude(page_images, prompt)
        
        # Generate validation
        validation_result = invoke_bedrock_model_without_reasoning(pdf_content_with_prompt)
        
        return jsonify({
            'success': True,
            'validation': validation_result,
            'pagesProcessed': len(page_images),
            'usedCustomPrompt': bool(custom_prompt)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# ARCHITECTURE DIAGRAM ENDPOINTS
# ============================================================================

@map_bp.route('/architecture-diagram/generate', methods=['POST'])
def generate_architecture_diagram():
    """Generate AWS architecture diagram in Draw.io XML format"""
    try:
        data = request.json
        
        if 'description' not in data:
            return jsonify({'success': False, 'message': 'Architecture description required'}), 400
        
        description = data['description']
        custom_prompt = data.get('custom_prompt')
        
        if custom_prompt:
            # Use custom prompt, replace placeholder
            prompt = custom_prompt.replace('{description}', description)
            # Also try without placeholder if not found
            if '{description}' not in custom_prompt:
                prompt = f"{custom_prompt}\n\nArchitecture Description:\n{description}"
        else:
            # Use default prompt
            prompt = get_architecture_diagram_prompt(description)
        
        # Generate diagram
        diagram_xml = invoke_bedrock_model_without_reasoning(prompt)
        
        return jsonify({
            'success': True,
            'diagramXml': diagram_xml,
            'usedCustomPrompt': bool(custom_prompt)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# CHAT ASSISTANT ENDPOINTS
# ============================================================================

@map_bp.route('/chat/message', methods=['POST'])
def chat_message():
    """Process chat message with context"""
    try:
        data = request.json
        
        if 'message' not in data:
            return jsonify({'success': False, 'message': 'Message required'}), 400
        
        user_message = data['message']
        context = data.get('context', {})
        chat_history = data.get('history', [])
        context_type = context.get('type', 'general')
        context_data = context.get('data', '')
        
        # Build system prompt based on context type
        system_prompts = {
            'general': "You are an AWS migration and modernization expert. Provide clear, actionable guidance on AWS cloud migration strategies, best practices, and solutions.",
            'modernization': "You are an AWS modernization specialist. Help analyze modernization opportunities, containerization strategies, and cloud-native transformations. Focus on practical recommendations based on the provided analysis.",
            'migration-strategy': "You are an AWS migration strategist specializing in the 6Rs framework (Rehost, Replatform, Repurchase, Refactor, Retire, Retain). Provide strategic guidance on migration approaches and wave planning.",
            'resource-planning': "You are an AWS resource planning expert. Help with team structure, skill requirements, timeline planning, and resource allocation for cloud migration projects.",
            'learning-pathway': "You are an AWS training and certification advisor. Guide users through learning paths, certification roadmaps, and skill development strategies for cloud migration teams.",
            'business-case': "You are an AWS business case analyst. Help review and discuss business case details, ROI calculations, cost analysis, and business value propositions for cloud migration.",
            'architecture': "You are an AWS solutions architect. Provide guidance on AWS architecture patterns, service selection, design best practices, and technical implementation details.",
            'service-analysis': "You are an AWS infrastructure completeness expert. Help analyze service gaps, identify missing infrastructure components across 6 critical categories (Backup, Storage, DR/HA, Network, Observability, Security), and provide specific recommendations to ensure production-ready, well-architected solutions. Focus on the production-ready benchmark of 56% compute / 44% non-compute infrastructure.",
            'ola-analysis': "You are an AWS licensing optimization expert. Help analyze Windows Server, SQL Server, and Oracle licensing strategies. Explain BYOL vs License Included options, Software Assurance requirements, Microsoft October 2019 licensing changes, Dedicated Hosts vs shared EC2, RDS alternatives, and Oracle Database@AWS (Exadata). Provide ARR impact analysis and OLA engagement recommendations. Focus on cost optimization while ensuring license compliance.",
            'knowledge-base': "You are an AWS documentation expert with access to comprehensive AWS knowledge. Search and provide accurate information from AWS documentation, whitepapers, best practices, and official guidance. Always cite sources when possible."
        }
        
        system_prompt = system_prompts.get(context_type, system_prompts['general'])
        
        # Build context string
        context_str = f"System: {system_prompt}\n\n"
        
        if context_data:
            context_str += f"Context Data from {context_type}:\n{context_data}\n\n"
        
        # Add conversation history
        history_str = ""
        if chat_history:
            history_str = "Conversation History:\n"
            for msg in chat_history[-5:]:  # Last 5 messages
                role = "User" if msg['role'] == 'user' else "Assistant"
                history_str += f"{role}: {msg['content']}\n"
            history_str += "\n"
        
        # Build full prompt
        full_prompt = f"{context_str}{history_str}User: {user_message}\n\nAssistant:"
        
        # For knowledge-base context, add instruction to search AWS documentation
        if context_type == 'knowledge-base':
            full_prompt = f"{context_str}{history_str}User Question: {user_message}\n\nPlease provide a comprehensive answer based on AWS documentation, best practices, and official guidance. Include specific AWS service recommendations and implementation details where relevant.\n\nAssistant:"
        
        # Get response
        response = invoke_bedrock_model_without_reasoning(full_prompt)
        
        return jsonify({
            'success': True,
            'response': response,
            'contextType': context_type
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# SERVICE ANALYSIS ENDPOINTS
# ============================================================================

@map_bp.route('/service-analysis/analyze', methods=['POST'])
def analyze_service_completeness():
    """Analyze AWS Calculator CSV for service completeness and infrastructure gaps"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        
        # Validate file size
        is_valid, error_msg = validate_file_size(file)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Parse AWS Calculator CSV
        csv_data = file.read().decode('utf-8')
        lines = csv_data.splitlines()
        
        # Find the start of the detailed estimate section
        start_idx = 0
        header_patterns = [
            "Group hierarchy,Region,Description",
            "Gruppenhierarchie,Region,Beschreibung",
            "Group hierarchy",
            "Gruppenhierarchie"
        ]
        
        for i, line in enumerate(lines):
            if any(pattern in line for pattern in header_patterns):
                start_idx = i
                break
        
        # Read CSV with error handling
        try:
            calc_df = pd.read_csv(
                io.StringIO("\n".join(lines[start_idx:])), 
                encoding="utf-8",
                on_bad_lines='skip',
                quoting=1
            )
        except Exception as e:
            try:
                calc_df = pd.read_csv(
                    io.StringIO("\n".join(lines[start_idx:])), 
                    encoding="utf-8",
                    on_bad_lines='skip',
                    quoting=3
                )
            except:
                return jsonify({'success': False, 'message': 'Failed to parse CSV file'}), 400
        
        # Get custom prompt (the comprehensive service analysis prompt)
        custom_prompt = request.form.get('custom_prompt')
        
        if not custom_prompt:
            return jsonify({'success': False, 'message': 'Analysis prompt required'}), 400
        
        # Prepare the data summary for analysis
        services_summary = calc_df.to_string()
        
        # Build the full prompt with CSV data
        full_prompt = f"{custom_prompt}\n\n**AWS Calculator CSV Data:**\n\n{services_summary}"
        
        # Generate analysis using Bedrock
        analysis_result = invoke_bedrock_model_without_reasoning(full_prompt)
        
        return jsonify({
            'success': True,
            'analysis': analysis_result,
            'recordsProcessed': len(calc_df)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# Health check endpoint
@map_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for MAP routes"""
    return jsonify({
        'success': True,
        'message': 'MAP Assessment API is running',
        'endpoints': {
            'modernization': 3,
            'migration': 1,
            'resource_planning': 1,
            'learning_pathway': 1,
            'business_validation': 1,
            'architecture_diagram': 1,
            'chat': 1,
            'service_analysis': 1,
            'ola_analysis': 1
        }
    })

