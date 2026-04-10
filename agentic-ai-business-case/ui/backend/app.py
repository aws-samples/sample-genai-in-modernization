"""
AWS Migration Business Case Generator - Backend API
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import json
import logging
import re
from werkzeug.utils import secure_filename
import tempfile
import shutil
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)


def safe_path(base_dir, filename):
    """Sanitize filename and ensure path stays within base_dir to prevent path traversal."""
    clean_name = os.path.basename(filename)
    if not clean_name:
        raise ValueError("Invalid filename")
    full_path = os.path.realpath(os.path.join(base_dir, clean_name))
    if not full_path.startswith(os.path.realpath(base_dir)):
        raise ValueError("Path traversal detected")
    return full_path


def safe_case_id(case_id):
    """Sanitize case_id to prevent path traversal. Only allow alphanumeric, hyphens, and underscores."""
    if not case_id or not re.match(r'^[a-zA-Z0-9_-]+$', case_id):
        raise ValueError("Invalid case ID")
    return case_id

# Environment detection
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
IS_PRODUCTION = FLASK_ENV == 'production'

# CORS only in development (frontend runs on different port)
if not IS_PRODUCTION:
    CORS(app)
    print("✓ Running in DEVELOPMENT mode - CORS enabled")
else:
    print("✓ Running in PRODUCTION mode - serving frontend from Flask")

# Cognito authentication (only when COGNITO_USER_POOL_ID is set)
from cognito_auth import is_cognito_enabled, register_auth_routes, get_user_from_session
if is_cognito_enabled():
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(32).hex())
    register_auth_routes(app)
    print("✓ Cognito authentication enabled")

# Register MAP Assessment routes
from map_routes import map_bp
app.register_blueprint(map_bp)
print("✓ MAP Assessment routes registered")

# Register OLA Analysis routes
from ola_routes import ola_bp
app.register_blueprint(ola_bp)
print("✓ OLA Analysis routes registered")

# Configuration
UPLOAD_FOLDER = tempfile.mkdtemp()
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'pdf', 'pptx', 'ppt', 'md', 'docx', 'doc'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Path to the project root and directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
AGENTS_DIR = os.path.join(PROJECT_ROOT, 'agents')

# Storage paths depend on environment
if IS_PRODUCTION:
    # In production, use /tmp for temporary storage (ECS Fargate)
    INPUT_DIR = '/tmp/input'
    OUTPUT_DIR = '/tmp/output'
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
else:
    # In development, use project directories
    INPUT_DIR = os.path.join(PROJECT_ROOT, 'input')
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')

# Frontend build directory (for production)
FRONTEND_BUILD_DIR = os.path.join(PROJECT_ROOT, 'ui', 'dist')

# Add project root to Python path so agents module can be imported
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# DynamoDB configuration
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'business-case-cases')
DYNAMODB_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AUTO_SAVE_TO_DYNAMODB = os.environ.get('AUTO_SAVE_TO_DYNAMODB', 'true').lower() == 'true'

# S3 configuration
S3_INPUT_BUCKET = os.environ.get('S3_INPUT_BUCKET', None)
S3_OUTPUT_BUCKET = os.environ.get('S3_OUTPUT_BUCKET', None)
S3_ENABLED = S3_INPUT_BUCKET is not None and S3_OUTPUT_BUCKET is not None

# Initialize DynamoDB client (will be None if credentials not available)
dynamodb_client = None
dynamodb_table = None
try:
    dynamodb_client = boto3.resource('dynamodb', region_name=DYNAMODB_REGION)
    dynamodb_table = dynamodb_client.Table(DYNAMODB_TABLE_NAME)
    print(f"✓ DynamoDB table '{DYNAMODB_TABLE_NAME}' configured")
except Exception as e:
    print(f"Warning: DynamoDB not available: {str(e)}")

# Initialize S3 client (will be None if not configured)
s3_client = None
if S3_ENABLED:
    try:
        s3_client = boto3.client('s3', region_name=DYNAMODB_REGION)
        # Verify buckets exist
        s3_client.head_bucket(Bucket=S3_INPUT_BUCKET)
        s3_client.head_bucket(Bucket=S3_OUTPUT_BUCKET)
        print(f"✓ S3 buckets configured: {S3_INPUT_BUCKET}, {S3_OUTPUT_BUCKET}")
    except Exception as e:
        print(f"Warning: S3 not available: {str(e)}")
        s3_client = None
        S3_ENABLED = False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_from_oidc():
    """
    Extract user info from ALB OIDC headers or Cognito session.
    ALB adds x-amzn-oidc-data header with JWT containing user info.
    Cognito session is set by cognito_auth.py when using Cognito login.
    """
    import base64
    import json
    
    # In development, return a mock user
    if not IS_PRODUCTION:
        return {
            'sub': 'dev-user-123',
            'email': 'developer@example.com',
            'name': 'Developer User',
            'given_name': 'Developer',
            'family_name': 'User'
        }
    
    # Check Cognito session first (from cognito_auth.py)
    if is_cognito_enabled():
        user = get_user_from_session()
        if user:
            return user
    
    # ALB adds x-amzn-oidc-data header with JWT
    oidc_data = request.headers.get('x-amzn-oidc-data')
    if not oidc_data:
        print("Warning: No OIDC data found in headers")
        # Log all headers for debugging
        print("Available headers:", dict(request.headers))
        return None
    
    try:
        # JWT format: header.payload.signature
        parts = oidc_data.split('.')
        if len(parts) != 3:
            print(f"Warning: Invalid JWT format (expected 3 parts, got {len(parts)})")
            return None
        
        # Decode payload (add padding if needed)
        payload_encoded = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_encoded) % 4
        if padding != 4:
            payload_encoded += '=' * padding
        
        payload = base64.urlsafe_b64decode(payload_encoded)
        user_data = json.loads(payload)
        
        # Log the full user data for debugging
        print(f"✓ OIDC user data: {json.dumps(user_data, indent=2)}")
        
        # Extract first name with multiple fallbacks (case-insensitive)
        # Try both lowercase and uppercase versions
        given_name = (user_data.get('given_name') or 
                     user_data.get('GIVEN_NAME') or 
                     user_data.get('givenName'))
        
        if not given_name:
            # Try to extract from 'name' field
            name = user_data.get('name') or user_data.get('NAME') or ''
            if name:
                given_name = name.split()[0] if ' ' in name else name
            else:
                # Fallback to email username
                email = user_data.get('email') or user_data.get('EMAIL') or ''
                given_name = email.split('@')[0] if email else 'User'
        
        # Extract family name (case-insensitive)
        family_name = (user_data.get('family_name') or 
                      user_data.get('FAMILY_NAME') or 
                      user_data.get('familyName'))
        
        return {
            'sub': user_data.get('sub') or user_data.get('SUB'),
            'email': user_data.get('email') or user_data.get('EMAIL'),
            'name': user_data.get('name') or user_data.get('NAME'),
            'given_name': given_name,
            'family_name': family_name
        }
    except Exception as e:
        print(f"Error decoding OIDC data: {e}")
        import traceback
        traceback.print_exc()
        return None

def is_dynamodb_enabled():
    """Check if DynamoDB is available and configured"""
    return dynamodb_table is not None

def is_s3_enabled():
    """Check if S3 is available and configured"""
    return s3_client is not None and S3_ENABLED

def upload_file_to_s3(file_path, case_id, file_key):
    """Upload a file to S3 and return the S3 key"""
    if not is_s3_enabled():
        return None
    
    try:
        s3_key = f"{case_id}/{file_key}"
        # Use output bucket for generated files, input bucket for uploaded files
        bucket = S3_OUTPUT_BUCKET if 'output' in file_path or 'aws_business_case' in file_key or 'mapping' in file_key else S3_INPUT_BUCKET
        s3_client.upload_file(file_path, bucket, s3_key)
        return s3_key
    except Exception as e:
        print(f"Error uploading to S3: {str(e)}")
        return None

def download_file_from_s3(s3_key, local_path):
    """Download a file from S3 to local path"""
    if not is_s3_enabled():
        return False
    
    try:
        # Try output bucket first, then input bucket
        try:
            s3_client.download_file(S3_OUTPUT_BUCKET, s3_key, local_path)
        except:
            s3_client.download_file(S3_INPUT_BUCKET, s3_key, local_path)
        return True
    except Exception as e:
        print(f"Error downloading from S3: {str(e)}")
        return False

def delete_files_from_s3(case_id):
    """Delete all files for a case from S3"""
    if not is_s3_enabled():
        return True
    
    try:
        # Delete from both buckets
        for bucket in [S3_INPUT_BUCKET, S3_OUTPUT_BUCKET]:
            # List all objects with the case_id prefix
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=f"{case_id}/"
            )
            
            if 'Contents' in response:
                objects = [{'Key': obj['Key']} for obj in response['Contents']]
                if objects:
                    s3_client.delete_objects(
                        Bucket=bucket,
                        Delete={'Objects': objects}
                    )
        return True
    except Exception as e:
        print(f"Error deleting from S3: {str(e)}")
        return False

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'API is running'})

@app.route('/api/user', methods=['GET'])
def get_current_user():
    """Get current user info from OIDC"""
    user = get_user_from_oidc()
    if user:
        return jsonify({'success': True, 'user': user})
    return jsonify({'success': False, 'message': 'Not authenticated'}), 401

@app.route('/api/storage/status', methods=['GET'])
def storage_status():
    """Check storage options status"""
    return jsonify({
        'dynamodb': {
            'enabled': is_dynamodb_enabled(),
            'tableName': DYNAMODB_TABLE_NAME if is_dynamodb_enabled() else None,
            'region': DYNAMODB_REGION if is_dynamodb_enabled() else None
        },
        's3': {
            'enabled': is_s3_enabled(),
            'inputBucket': S3_INPUT_BUCKET if is_s3_enabled() else None,
            'outputBucket': S3_OUTPUT_BUCKET if is_s3_enabled() else None,
            'region': DYNAMODB_REGION if is_s3_enabled() else None
        }
    })

@app.route('/api/generate', methods=['POST'])
def generate_business_case():
    try:
        # Get project info
        project_info = json.loads(request.form.get('projectInfo', '{}'))
        selected_agents = json.loads(request.form.get('selectedAgents', '[]'))
        case_id = request.form.get('caseId', None)
        
        # Generate case ID if not provided
        if not case_id:
            case_id = f"case-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        else:
            case_id = safe_case_id(case_id)
        
        # Create case-specific input directory
        case_input_dir = safe_path(INPUT_DIR, case_id)
        os.makedirs(case_input_dir, exist_ok=True)
        print(f"Created case-specific input directory: {case_input_dir}")
        
        # Save uploaded files
        file_mapping = {
            'itInventory': 'it-infrastructure-inventory.xlsx',
            'atxPptx': 'atx_business_case.pptx',
            'portfolio': 'application-portfolio.csv'
        }
        
        uploaded_files = {}
        s3_file_keys = {}
        
        # Handle single files - save to case-specific directory
        for key, target_filename in file_mapping.items():
            if key in request.files:
                file = request.files[key]
                if file and allowed_file(file.filename):
                    # Save to case-specific input directory ONLY
                    filepath = safe_path(case_input_dir, target_filename)
                    file.save(filepath)
                    uploaded_files[key] = filepath
                    print(f"✓ Saved {key} to case directory: {filepath}")
                    
                    # Upload to S3 if enabled
                    if is_s3_enabled():
                        s3_key = upload_file_to_s3(filepath, case_id, target_filename)
                        if s3_key:
                            s3_file_keys[key] = s3_key
        
        # Handle MRA file separately - preserve original extension
        if 'mra' in request.files:
            file = request.files['mra']
            if file and allowed_file(file.filename):
                # Get the file extension
                original_filename = secure_filename(file.filename)
                file_ext = original_filename.rsplit('.', 1)[1].lower()
                
                # Save with appropriate extension
                target_filename = f'mra-assessment.{file_ext}'
                
                # Save to case-specific directory ONLY
                filepath = safe_path(case_input_dir, target_filename)
                file.save(filepath)
                uploaded_files['mra'] = filepath
                print(f"✓ Saved MRA to case directory: {filepath}")
                
                # Upload to S3 if enabled
                if is_s3_enabled():
                    s3_key = upload_file_to_s3(filepath, case_id, target_filename)
                    if s3_key:
                        s3_file_keys['mra'] = s3_key
        
        # Handle multiple RVTools files - save to case-specific directory
        if 'rvTool' in request.files:
            rv_files = request.files.getlist('rvTool')
            print(f"DEBUG: Received {len(rv_files)} RVTools file(s)")
            rv_file_paths = []
            rv_s3_keys = []
            
            for idx, file in enumerate(rv_files):
                print(f"DEBUG: Processing RVTools file {idx}: {file.filename if file else 'None'}")
                if file and allowed_file(file.filename):
                    # Preserve original filename
                    safe_filename = secure_filename(file.filename)
                    
                    # Save to case-specific directory ONLY
                    filepath = safe_path(case_input_dir, safe_filename)
                    file.save(filepath)
                    rv_file_paths.append(filepath)
                    print(f"✓ Saved RVTools file to case directory: {filepath}")
                    
                    # Upload to S3 if enabled
                    if is_s3_enabled():
                        s3_key = upload_file_to_s3(filepath, case_id, safe_filename)
                        if s3_key:
                            rv_s3_keys.append(s3_key)
                else:
                    print(f"DEBUG: RVTools file rejected - file: {file}, allowed: {allowed_file(file.filename) if file else 'N/A'}")
            
            if rv_file_paths:
                uploaded_files['rvTool'] = rv_file_paths
                print(f"DEBUG: Total RVTools files uploaded: {len(rv_file_paths)}")
                if rv_s3_keys:
                    s3_file_keys['rvTool'] = rv_s3_keys
        else:
            print("DEBUG: No 'rvTool' field found in request.files")
        
        # Save project info and uploaded filenames to a file for agents to access
        project_info_with_files = project_info.copy()
        project_info_with_files['caseId'] = case_id
        project_info_with_files['uploadedFiles'] = {
            key: [os.path.basename(f) for f in files] if isinstance(files, list) else os.path.basename(files)
            for key, files in uploaded_files.items()
        }
        
        # Save to case-specific directory ONLY
        case_project_info_file = safe_path(case_input_dir, 'project_info.json')
        with open(case_project_info_file, 'w', encoding='utf-8') as f:
            json.dump(project_info_with_files, f, indent=2)
        print(f"✓ Saved project info to case directory: {case_project_info_file}")
        
        # ALSO save to main input directory so agents can find it
        # (agents look for project_info.json in base input/ to get case ID)
        project_info_file = os.path.join(INPUT_DIR, 'project_info.json')
        with open(project_info_file, 'w', encoding='utf-8') as f:
            json.dump(project_info_with_files, f, indent=2)
        print(f"✓ Saved project info to base directory: {project_info_file}")
        
        # Run the business case generator
        result = run_business_case_generator(project_info, selected_agents)
        
        # Read the generated business case
        # First check case-specific output folder, then fall back to root
        case_output_dir = safe_path(OUTPUT_DIR, case_id)
        output_file = safe_path(case_output_dir, 'aws_business_case.md')
        
        if not os.path.exists(output_file):
            # Fallback to root output folder
            output_file = os.path.join(OUTPUT_DIR, 'aws_business_case.md')
        
        output_s3_keys = {}
        
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Upload business case to S3 if enabled
            if is_s3_enabled():
                s3_key = upload_file_to_s3(output_file, case_id, 'aws_business_case.md')
                if s3_key:
                    output_s3_keys['business_case'] = s3_key
                    print(f"✓ Business case uploaded to S3: {s3_key}")
            
            # Upload all Excel files to S3 if they exist and S3 is enabled
            if is_s3_enabled():
                # Check for RVTools Excel file (check case folder first)
                excel_file = safe_path(case_output_dir, 'vm_to_ec2_mapping.xlsx')
                if not os.path.exists(excel_file):
                    excel_file = safe_path(OUTPUT_DIR, 'vm_to_ec2_mapping.xlsx')
                
                if os.path.exists(excel_file):
                    s3_key = upload_file_to_s3(excel_file, case_id, 'vm_to_ec2_mapping.xlsx')
                    if s3_key:
                        output_s3_keys['excel_mapping'] = s3_key
                        print(f"✓ Excel mapping uploaded to S3: {s3_key}")
                
                # Check for EKS Excel file (check case folder first)
                eks_excel_file = safe_path(case_output_dir, 'eks_migration_analysis.xlsx')
                if not os.path.exists(eks_excel_file):
                    eks_excel_file = safe_path(OUTPUT_DIR, 'eks_migration_analysis.xlsx')
                
                if os.path.exists(eks_excel_file):
                    s3_key = upload_file_to_s3(eks_excel_file, case_id, 'eks_migration_analysis.xlsx')
                    if s3_key:
                        output_s3_keys['eks_analysis'] = s3_key
                        print(f"✓ EKS analysis uploaded to S3: {s3_key}")
                
                # Check for IT Inventory Excel file (check case folder first, then root)
                import glob
                it_inventory_files = glob.glob(os.path.join(case_output_dir, 'it_inventory_aws_pricing_*.xlsx'))
                if not it_inventory_files:
                    it_inventory_files = glob.glob(os.path.join(OUTPUT_DIR, 'it_inventory_aws_pricing_*.xlsx'))
                
                if it_inventory_files:
                    # Upload the most recent IT inventory file
                    it_inventory_file = max(it_inventory_files, key=os.path.getmtime)
                    filename = os.path.basename(it_inventory_file)
                    s3_key = upload_file_to_s3(it_inventory_file, case_id, filename)
                    if s3_key:
                        output_s3_keys['it_inventory'] = s3_key
                        print(f"✓ IT Inventory uploaded to S3: {s3_key}")
            
            # Auto-save to DynamoDB if enabled
            saved_to_db = False
            if AUTO_SAVE_TO_DYNAMODB and is_dynamodb_enabled():
                try:
                    user = get_user_from_oidc()
                    if user:
                        item = {
                            'caseId': case_id,
                            'userId': user['sub'],
                            'userEmail': user.get('email', 'unknown'),
                            'projectInfo': project_info,
                            'uploadedFiles': list(uploaded_files.keys()),
                            'selectedAgents': selected_agents,
                            'businessCaseContent': content,
                            'createdAt': datetime.utcnow().isoformat(),
                            'lastUpdated': datetime.utcnow().isoformat(),
                            'executionStats': {
                                'agentsExecuted': len(selected_agents),
                                'executionTime': result.get('execution_time', 'N/A'),
                                'tokenUsage': result.get('token_usage', 'N/A')
                            },
                            's3FileKeys': s3_file_keys if is_s3_enabled() else {},
                            'outputS3Keys': output_s3_keys if is_s3_enabled() else {},
                            's3BucketName': S3_INPUT_BUCKET if is_s3_enabled() else None,
                            's3Enabled': is_s3_enabled()
                        }
                        dynamodb_table.put_item(Item=item)
                        saved_to_db = True
                        print(f"✓ Auto-saved to DynamoDB: {case_id}")
                except Exception as db_error:
                    print(f"Warning: Auto-save to DynamoDB failed: {str(db_error)}")
            
            return jsonify({
                'success': True,
                'content': content,
                'projectInfo': project_info,
                'agentsExecuted': len(selected_agents),
                'executionTime': result.get('execution_time', 'N/A'),
                'tokenUsage': result.get('token_usage', 'N/A'),
                'caseId': case_id,
                'uploadedFiles': list(uploaded_files.keys()),
                's3FileKeys': s3_file_keys if is_s3_enabled() else None,
                's3InputBucket': S3_INPUT_BUCKET if is_s3_enabled() else None,
                's3OutputBucket': S3_OUTPUT_BUCKET if is_s3_enabled() else None,
                'outputS3Keys': output_s3_keys if is_s3_enabled() else None,
                'autoSaved': saved_to_db
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Business case file not generated'
            }), 500
            
    except Exception as e:
        logging.error(f"Business case generation failed: {e}")
        return jsonify({
            'success': False,
            'message': 'An internal error occurred during business case generation'
        }), 500

def run_business_case_generator(project_info, selected_agents):
    """
    Run the Python business case generator using the main venv.
    
    The agents require the 'strands' package which is installed in the main venv,
    not the backend venv. We need to use the main venv's Python interpreter.
    """
    import time
    import subprocess
    
    start_time = time.time()
    
    try:
        # Get the main venv Python path (one level up from backend)
        main_venv_python = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            '../../venv/bin/python3'
        ))
        
        # Fallback to system Python if main venv doesn't exist
        if not os.path.exists(main_venv_python):
            main_venv_python = sys.executable
            print(f"Warning: Main venv not found, using system Python: {main_venv_python}")
        else:
            print(f"Using main venv Python: {main_venv_python}")
        
        # Path to the business case generator (now in agents/core/)
        generator_script = os.path.join(PROJECT_ROOT, 'agents', 'core', 'aws_business_case.py')
        print(f"Generator script: {generator_script}")
        print(f"Script exists: {os.path.exists(generator_script)}")
        
        # Set PYTHONPATH to include project root so agents module can be imported
        env = os.environ.copy()
        existing_pythonpath = env.get('PYTHONPATH', '')
        if existing_pythonpath:
            env['PYTHONPATH'] = f"{PROJECT_ROOT}:{existing_pythonpath}"
        else:
            env['PYTHONPATH'] = PROJECT_ROOT
        
        print(f"PYTHONPATH: {env['PYTHONPATH']}")
        print(f"Working directory: {PROJECT_ROOT}")
        
        # Use subprocess for better error handling
        result = subprocess.run(
            [main_venv_python, generator_script],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        # Log stdout and stderr
        if result.stdout:
            print(f"Generator stdout:\n{result.stdout}")
        if result.stderr:
            print(f"Generator stderr:\n{result.stderr}")
        
        if result.returncode != 0:
            error_msg = f"Generator failed with exit code {result.returncode}"
            if result.stderr:
                error_msg += f"\nError output: {result.stderr[-1000:]}"
            if result.stdout:
                error_msg += f"\nStdout: {result.stdout[-1000:]}"
            raise Exception(error_msg)
        
        # Calculate execution time
        execution_time = f"{time.time() - start_time:.2f}s"
        
        return {
            'execution_time': execution_time,
            'token_usage': 'N/A',
            'stdout': result.stdout if result.stdout else 'Business case generated successfully'
        }
        
    except subprocess.TimeoutExpired:
        raise Exception('Generator timed out after 10 minutes')
    except Exception as e:
        print(f"Generator error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise Exception(f'Failed to run generator: {str(e)}')

@app.route('/api/status/<job_id>', methods=['GET'])
def check_status(job_id):
    """Check the status of a generation job"""
    # This is a placeholder for async job tracking
    return jsonify({
        'jobId': job_id,
        'status': 'completed',
        'progress': 100
    })

@app.route('/api/dynamodb/status', methods=['GET'])
def dynamodb_status():
    """Check if DynamoDB is enabled and available"""
    enabled = is_dynamodb_enabled()
    return jsonify({
        'enabled': enabled,
        'tableName': DYNAMODB_TABLE_NAME if enabled else None,
        'region': DYNAMODB_REGION if enabled else None
    })

@app.route('/api/dynamodb/save', methods=['POST'])
def save_to_dynamodb():
    """Save a business case to DynamoDB"""
    if not is_dynamodb_enabled():
        return jsonify({
            'success': False,
            'message': 'DynamoDB is not enabled or configured'
        }), 503
    
    # Get current user
    user = get_user_from_oidc()
    if not user:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
    
    try:
        data = request.json
        case_id = data.get('caseId')
        
        if not case_id:
            # Generate new ID if not provided
            case_id = f"case-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        item = {
            'caseId': case_id,
            'userId': user['sub'],  # Add user ID for filtering
            'userEmail': user['email'],  # Add email for display
            'projectInfo': data.get('projectInfo', {}),
            'uploadedFiles': data.get('uploadedFiles', {}),
            'selectedAgents': data.get('selectedAgents', {}),
            'businessCaseContent': data.get('businessCaseContent', ''),
            'createdAt': data.get('createdAt', datetime.utcnow().isoformat()),
            'lastUpdated': datetime.utcnow().isoformat(),
            'executionStats': data.get('executionStats', {}),
            's3FileKeys': data.get('s3FileKeys', {}) if is_s3_enabled() else {},
            'outputS3Keys': data.get('outputS3Keys', {}) if is_s3_enabled() else {},
            's3BucketName': S3_INPUT_BUCKET if is_s3_enabled() else None,
            's3Enabled': is_s3_enabled()
        }
        
        dynamodb_table.put_item(Item=item)
        
        return jsonify({
            'success': True,
            'caseId': case_id,
            'lastUpdated': item['lastUpdated'],
            's3Enabled': is_s3_enabled()
        })
        
    except ClientError as e:
        logging.error(f"DynamoDB save error: {e}")
        return jsonify({
            'success': False,
            'message': 'A database error occurred'
        }), 500
    except Exception as e:
        logging.error(f"Save to DynamoDB failed: {e}")
        return jsonify({
            'success': False,
            'message': 'An internal error occurred'
        }), 500

@app.route('/api/dynamodb/list', methods=['GET'])
def list_business_cases():
    """List all saved business cases for the current user"""
    if not is_dynamodb_enabled():
        return jsonify({
            'success': False,
            'message': 'DynamoDB is not enabled or configured'
        }), 503
    
    # Get current user
    user = get_user_from_oidc()
    if not user:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
    
    try:
        # Scan with filter for current user
        response = dynamodb_table.scan(
            FilterExpression='userId = :userId',
            ExpressionAttributeValues={':userId': user['sub']},
            ProjectionExpression='caseId, projectInfo, createdAt, lastUpdated, userEmail'
        )
        
        items = response.get('Items', [])
        
        # Sort by lastUpdated descending
        items.sort(key=lambda x: x.get('lastUpdated', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'cases': items
        })
        
    except ClientError as e:
        logging.error(f"DynamoDB list error: {e}")
        return jsonify({
            'success': False,
            'message': 'A database error occurred'
        }), 500
    except Exception as e:
        logging.error(f"List business cases failed: {e}")
        return jsonify({
            'success': False,
            'message': 'An internal error occurred'
        }), 500

@app.route('/api/dynamodb/load/<case_id>', methods=['GET'])
def load_business_case(case_id):
    """Load a specific business case from DynamoDB and restore files from S3"""
    if not is_dynamodb_enabled():
        return jsonify({
            'success': False,
            'message': 'DynamoDB is not enabled or configured'
        }), 503
    
    # Sanitize case_id
    try:
        case_id = safe_case_id(case_id)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid case ID'}), 400
    
    # Get current user
    user = get_user_from_oidc()
    if not user:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
    
    try:
        # Query using UserIdIndex GSI (userId + createdAt)
        # Then filter by caseId since we can't use get_item with composite key
        response = dynamodb_table.query(
            IndexName='UserIdIndex',
            KeyConditionExpression='userId = :userId',
            FilterExpression='caseId = :caseId',
            ExpressionAttributeValues={
                ':userId': user['sub'],
                ':caseId': case_id
            }
        )
        
        if not response.get('Items'):
            return jsonify({
                'success': False,
                'message': 'Business case not found'
            }), 404
        
        case_data = response['Items'][0]  # Should only be one match
        
        # Verify user owns this case
        if case_data.get('userId') != user['sub']:
            return jsonify({
                'success': False,
                'message': 'Access denied: You do not own this business case'
            }), 403
        
        # Restore input files from S3 if available
        files_restored = {}
        if is_s3_enabled() and 's3FileKeys' in case_data:
            # Create case-specific input directory for restored files
            case_input_dir = safe_path(INPUT_DIR, case_id)
            os.makedirs(case_input_dir, exist_ok=True)
            print(f"Restoring files to case-specific directory: {case_input_dir}")
            
            file_mapping = {
                'itInventory': 'it-infrastructure-inventory.xlsx',
                'atxPptx': 'atx_business_case.pptx',
                'portfolio': 'application-portfolio.csv'
            }
            
            for key, value in case_data.get('s3FileKeys', {}).items():
                if key == 'rvTool':
                    # Handle multiple RVTools files
                    if isinstance(value, list):
                        rv_restored = []
                        for s3_key in value:
                            filename = os.path.basename(s3_key)
                            local_path = safe_path(case_input_dir, filename)
                            if download_file_from_s3(s3_key, local_path):
                                print(f"✓ Restored RVTools file: {filename}")
                                rv_restored.append(True)
                            else:
                                print(f"✗ Failed to restore RVTools file: {filename}")
                                rv_restored.append(False)
                        files_restored[key] = all(rv_restored)
                    else:
                        # Single RVTools file (backward compatibility)
                        filename = os.path.basename(value)
                        local_path = safe_path(case_input_dir, filename)
                        if download_file_from_s3(value, local_path):
                            print(f"✓ Restored RVTools file: {filename}")
                            files_restored[key] = True
                        else:
                            print(f"✗ Failed to restore RVTools file: {filename}")
                            files_restored[key] = False
                elif key == 'mra':
                    # Handle MRA file - preserve original filename from S3
                    filename = os.path.basename(value)
                    local_path = safe_path(case_input_dir, filename)
                    if download_file_from_s3(value, local_path):
                        print(f"✓ Restored MRA file: {filename}")
                        files_restored[key] = True
                    else:
                        print(f"✗ Failed to restore MRA file: {filename}")
                        files_restored[key] = False
                elif key in file_mapping:
                    filename = file_mapping[key]
                    local_path = safe_path(case_input_dir, filename)
                    if download_file_from_s3(value, local_path):
                        print(f"✓ Restored {key} file: {filename}")
                        files_restored[key] = True
                    else:
                        print(f"✗ Failed to restore {key} file: {filename}")
                        files_restored[key] = False
        
        # Restore output files from S3 if available
        output_files_restored = {}
        if is_s3_enabled() and 'outputS3Keys' in case_data:
            # Create case-specific output directory for restored files
            case_output_dir = safe_path(OUTPUT_DIR, case_id)
            os.makedirs(case_output_dir, exist_ok=True)
            print(f"Restoring output files to case-specific directory: {case_output_dir}")
            
            output_s3_keys = case_data.get('outputS3Keys', {})
            
            # Restore business case
            if 'business_case' in output_s3_keys:
                s3_key = output_s3_keys['business_case']
                local_path = safe_path(case_output_dir, 'aws_business_case.md')
                if download_file_from_s3(s3_key, local_path):
                    output_files_restored['business_case'] = True
                    print(f"✓ Restored business case from S3: {s3_key}")
                else:
                    output_files_restored['business_case'] = False
            
            # Restore Excel mapping
            if 'excel_mapping' in output_s3_keys:
                s3_key = output_s3_keys['excel_mapping']
                local_path = safe_path(case_output_dir, 'vm_to_ec2_mapping.xlsx')
                if download_file_from_s3(s3_key, local_path):
                    output_files_restored['excel_mapping'] = True
                    print(f"✓ Restored Excel mapping from S3: {s3_key}")
                else:
                    output_files_restored['excel_mapping'] = False
            
            # Restore EKS analysis if available
            if 'eks_analysis' in output_s3_keys:
                s3_key = output_s3_keys['eks_analysis']
                local_path = safe_path(case_output_dir, 'eks_migration_analysis.xlsx')
                if download_file_from_s3(s3_key, local_path):
                    output_files_restored['eks_analysis'] = True
                    print(f"✓ Restored EKS analysis from S3: {s3_key}")
                else:
                    output_files_restored['eks_analysis'] = False
            
            # Restore IT Inventory analysis if available
            if 'it_inventory' in output_s3_keys:
                s3_key = output_s3_keys['it_inventory']
                local_path = safe_path(case_output_dir, 'it_inventory_ec2_cost_analysis.xlsx')
                if download_file_from_s3(s3_key, local_path):
                    output_files_restored['it_inventory'] = True
                    print(f"✓ Restored IT Inventory analysis from S3: {s3_key}")
                else:
                    output_files_restored['it_inventory'] = False
        
        return jsonify({
            'success': True,
            'case': case_data,
            'filesRestored': files_restored if files_restored else None,
            'outputFilesRestored': output_files_restored if output_files_restored else None,
            's3Enabled': is_s3_enabled()
        })
        
    except ClientError as e:
        logging.error(f"DynamoDB load error: {e}")
        return jsonify({
            'success': False,
            'message': 'A database error occurred'
        }), 500
    except Exception as e:
        logging.error(f"Load business case failed: {e}")
        return jsonify({
            'success': False,
            'message': 'An internal error occurred'
        }), 500

@app.route('/api/dynamodb/delete/<case_id>', methods=['DELETE'])
def delete_business_case(case_id):
    """Delete a business case from DynamoDB and S3"""
    if not is_dynamodb_enabled():
        return jsonify({
            'success': False,
            'message': 'DynamoDB is not enabled or configured'
        }), 503
    
    # Sanitize case_id
    try:
        case_id = safe_case_id(case_id)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid case ID'}), 400
    
    # Get current user
    user = get_user_from_oidc()
    if not user:
        return jsonify({
            'success': False,
            'message': 'Not authenticated'
        }), 401
    
    try:
        # Query using UserIdIndex GSI to find and verify ownership
        response = dynamodb_table.query(
            IndexName='UserIdIndex',
            KeyConditionExpression='userId = :userId',
            FilterExpression='caseId = :caseId',
            ExpressionAttributeValues={
                ':userId': user['sub'],
                ':caseId': case_id
            }
        )
        
        if not response.get('Items'):
            return jsonify({
                'success': False,
                'message': 'Case not found or access denied'
            }), 404
        
        case_data = response['Items'][0]
        
        # Delete from S3 first if enabled
        if is_s3_enabled():
            delete_files_from_s3(case_id)
        
        # Delete from DynamoDB
        dynamodb_table.delete_item(Key={'caseId': case_id})
        
        return jsonify({
            'success': True,
            'message': 'Business case deleted successfully'
        })
        
    except ClientError as e:
        logging.error(f"DynamoDB delete error: {e}")
        return jsonify({
            'success': False,
            'message': 'A database error occurred'
        }), 500
    except Exception as e:
        logging.error(f"Delete business case failed: {e}")
        return jsonify({
            'success': False,
            'message': 'An internal error occurred'
        }), 500

@app.route('/api/download/<file_type>', methods=['GET'])
def download_file(file_type):
    """Generate presigned URL for downloading output files from S3"""
    case_id = request.args.get('caseId')
    s3_key_param = request.args.get('s3Key')  # Allow direct S3 key for unsaved cases
    
    if not case_id and not s3_key_param:
        return jsonify({'success': False, 'message': 'Case ID or S3 key is required'}), 400
    
    if not is_s3_enabled():
        return jsonify({'success': False, 'message': 'S3 storage is not enabled'}), 503
    
    # Get current user
    user = get_user_from_oidc()
    if not user:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    try:
        s3_key = None
        
        # If S3 key is provided directly (for unsaved cases), use it
        if s3_key_param:
            s3_key = s3_key_param
            print(f"Using direct S3 key: {s3_key}")
        # Otherwise, look up from DynamoDB (for saved cases)
        elif case_id and is_dynamodb_enabled():
            # Query using UserIdIndex GSI to verify ownership
            response = dynamodb_table.query(
                IndexName='UserIdIndex',
                KeyConditionExpression='userId = :userId',
                FilterExpression='caseId = :caseId',
                ExpressionAttributeValues={
                    ':userId': user['sub'],
                    ':caseId': case_id
                }
            )
            
            if not response.get('Items'):
                return jsonify({'success': False, 'message': 'Case not found in database'}), 404
            
            case_data = response['Items'][0]
            
            # Map file types to S3 keys
            output_s3_keys = case_data.get('outputS3Keys', {})
            
            file_mapping = {
                'business_case': output_s3_keys.get('business_case'),
                'excel_mapping': output_s3_keys.get('excel_mapping'),
                'eks_analysis': output_s3_keys.get('eks_analysis'),
                'it_inventory': output_s3_keys.get('it_inventory')
            }
            
            s3_key = file_mapping.get(file_type)
        
        if not s3_key:
            return jsonify({'success': False, 'message': f'File type "{file_type}" not found for this case'}), 404
        
        # Generate presigned URL (valid for 1 hour)
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_OUTPUT_BUCKET, 'Key': s3_key},
            ExpiresIn=3600
        )
        
        filename = s3_key.split('/')[-1]  # Get filename from S3 key
        
        return jsonify({
            'success': True,
            'url': url,
            'filename': filename
        })
        
    except ClientError as e:
        logging.error(f"S3 download error: {e}")
        return jsonify({'success': False, 'message': 'A storage error occurred'}), 500
    except Exception as e:
        logging.error(f"Download file failed: {e}")
        return jsonify({'success': False, 'message': 'An internal error occurred'}), 500

@app.route('/api/enhance-description', methods=['POST'])
def enhance_description():
    """Enhance project description using AI"""
    try:
        data = request.json
        project_name = data.get('projectName', '')
        customer_name = data.get('customerName', '')
        current_description = data.get('currentDescription', '')
        aws_region = data.get('awsRegion', 'us-east-1')
        
        # If there's existing description, enhance it using AI
        if current_description:
            # Use AWS Bedrock to enhance the description
            try:
                import boto3
                from botocore.exceptions import ClientError, NoCredentialsError
                from botocore.config import Config
                
                # Retry configuration for production reliability
                retry_config = Config(
                    retries={'max_attempts': 5, 'mode': 'adaptive'},
                    connect_timeout=10,
                    read_timeout=300
                )
                
                # Use the region from the request, not DYNAMODB_REGION
                bedrock = boto3.client('bedrock-runtime', region_name=aws_region, config=retry_config)
                
                prompt = f"""You are an AWS migration expert. Create a comprehensive project description for {customer_name}'s AWS migration project. 

User's input:
{current_description}

Instructions:
- Expand on the user's key points naturally
- Add relevant AWS migration details
- Keep the user's original requirements prominent
- Target region: {aws_region}
- Write in paragraph form, naturally flowing from the user's input
- Be thorough but focused (aim for 150-200 words)

Enhanced description:"""

                response = bedrock.invoke_model(
                    modelId='anthropic.claude-3-haiku-20240307-v1:0',
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 500,  # Allow longer descriptions
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    })
                )
                
                response_body = json.loads(response['body'].read())
                enhanced = response_body['content'][0]['text'].strip()
                
                # No truncation - keep full AI response
                print(f"AI enhanced description: {len(enhanced.split())} words")
                
            except NoCredentialsError:
                error_msg = "AWS credentials not found. Please configure AWS credentials."
                print(f"AI enhancement failed: {error_msg}")
                return jsonify({
                    'success': False,
                    'message': error_msg,
                    'details': 'Run: aws configure or aws sso login'
                }), 401
                
            except ClientError as ce:
                error_code = ce.response.get('Error', {}).get('Code', 'Unknown')
                error_msg = ce.response.get('Error', {}).get('Message', str(ce))
                
                if error_code == 'ExpiredTokenException':
                    print(f"AI enhancement failed: AWS credentials expired")
                    return jsonify({
                        'success': False,
                        'message': 'AWS credentials have expired',
                        'details': 'Please refresh your credentials: aws sso login --profile <your-profile>',
                        'errorCode': 'EXPIRED_CREDENTIALS'
                    }), 401
                elif error_code == 'UnrecognizedClientException':
                    print(f"AI enhancement failed: Invalid AWS credentials")
                    return jsonify({
                        'success': False,
                        'message': 'Invalid AWS credentials',
                        'details': 'Please check your AWS credentials: aws configure',
                        'errorCode': 'INVALID_CREDENTIALS'
                    }), 401
                else:
                    logging.error(f"AI enhancement failed: {error_code} - {error_msg}")
                    return jsonify({
                        'success': False,
                        'message': 'An error occurred with the AI service',
                        'errorCode': error_code
                    }), 500
                    
            except Exception as ai_error:
                print(f"AI enhancement failed: {str(ai_error)}")
                # Fallback: Comprehensive template
                enhanced = f"This project aims to assess and plan {customer_name}'s migration to AWS in the {aws_region} region. The assessment will analyze the current IT environment, including VMware workloads, infrastructure dependencies, and organizational readiness for cloud adoption. We will develop a comprehensive migration strategy using the 6Rs framework (Rehost, Replatform, Repurchase, Refactor, Retire, Retain) aligned with AWS Migration Acceleration Program (MAP) methodology. Deliverables include a detailed TCO comparison between on-premises and AWS costs, a phased migration roadmap with wave planning, risk assessment and mitigation strategies, and technical recommendations for successful cloud transformation."
        else:
            # Generate new comprehensive description from scratch
            enhanced = f"This project aims to assess and plan {customer_name}'s on-premises infrastructure migration to AWS. The assessment will include a comprehensive analysis of the current IT environment, VMware workloads, application portfolio, and organizational readiness for cloud adoption. We will develop a detailed migration strategy using the 6Rs framework and AWS MAP methodology, targeting the {aws_region} region. Deliverables include TCO comparison, migration roadmap with wave planning, risk assessment, and technical recommendations for successful cloud transformation."
        
        return jsonify({
            'success': True,
            'enhancedDescription': enhanced
        })
        
    except Exception as e:
        logging.error(f"Enhance description failed: {e}")
        return jsonify({
            'success': False,
            'message': 'An internal error occurred'
        }), 500

@app.route('/api/config/schema', methods=['GET'])
def get_config_schema_endpoint():
    """Get configuration schema with metadata for UI."""
    try:
        import agents.config.config_manager as config_manager
        schema = config_manager.get_config_schema()
        
        # Use json.dumps with sort_keys=False to preserve order
        response = app.response_class(
            response=json.dumps(schema, sort_keys=False),
            status=200,
            mimetype='application/json'
        )
        return response
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logging.error(f"Config schema error: {error_details}")
        return jsonify({'error': 'An internal error occurred'}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration (defaults + overrides)."""
    try:
        import agents.config.config_manager as config_manager
        schema = config_manager.get_config_schema()
        overrides = config_manager.load_overrides()
        
        # Merge defaults with overrides
        config_data = {}
        for group_key, group in schema.items():
            config_data[group_key] = {}
            for setting_key, setting in group['settings'].items():
                # Use override if exists, otherwise use default
                override_key = f"{group_key}.{setting_key}"
                config_data[group_key][setting_key] = overrides.get(override_key, setting['default'])
        
        # Use json.dumps with sort_keys=False to preserve order
        response = app.response_class(
            response=json.dumps(config_data, sort_keys=False),
            status=200,
            mimetype='application/json'
        )
        return response
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logging.error(f"Config get error: {error_details}")
        return jsonify({'error': 'An internal error occurred'}), 500

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration overrides."""
    try:
        import agents.config.config_manager as config_manager
        data = request.json
        
        # Flatten nested config to dot notation
        flat_overrides = {}
        for group_key, settings in data.items():
            for setting_key, value in settings.items():
                flat_overrides[f"{group_key}.{setting_key}"] = value
        
        config_manager.save_overrides(flat_overrides)
        return jsonify({'message': 'Configuration updated successfully'}), 200
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logging.error(f"Config update error: {error_details}")
        return jsonify({'error': 'An internal error occurred'}), 500

@app.route('/api/config/reset', methods=['POST'])
def reset_config():
    """Reset configuration to defaults (clear overrides)."""
    try:
        override_file = os.path.join(OUTPUT_DIR, 'config_overrides.json')
        if os.path.exists(override_file):
            os.remove(override_file)
        return jsonify({'message': 'Configuration reset to defaults'}), 200
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logging.error(f"Config reset error: {error_details}")
        return jsonify({'error': 'An internal error occurred'}), 500

# ============================================================================
# Frontend Serving (Production Only)
# ============================================================================

if IS_PRODUCTION:
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """
        Serve React frontend in production mode.
        In development, Vite dev server handles this.
        """
        # If path is a file and exists, serve it (validate path stays within build dir)
        if path:
            full_path = os.path.realpath(os.path.join(FRONTEND_BUILD_DIR, path))
            if full_path.startswith(os.path.realpath(FRONTEND_BUILD_DIR)) and os.path.exists(full_path):
                return send_from_directory(FRONTEND_BUILD_DIR, path)
        
        # Otherwise serve index.html (for client-side routing)
        return send_from_directory(FRONTEND_BUILD_DIR, 'index.html')
    
    print(f"✓ Frontend serving enabled from: {FRONTEND_BUILD_DIR}")

if __name__ == '__main__':
    # This application requires Gunicorn to run
    # Do not use Flask's built-in server
    
    print("=" * 60)
    print("ERROR: This application must be run with Gunicorn")
    print("=" * 60)
    print("")
    print("Usage:")
    print("  ./start-all.sh                    # Start everything")
    print("  cd ui/backend && ./start-gunicorn.sh  # Backend only")
    print("")
    print("Direct Gunicorn command:")
    print("  cd ui/backend")
    print("  source venv/bin/activate")
    print("  gunicorn -c gunicorn.conf.py app:app")
    print("")
    print("=" * 60)
    import sys
    sys.exit(1)
