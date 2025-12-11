"""
AWS Migration Business Case Generator - Backend API
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import json
from werkzeug.utils import secure_filename
import tempfile
import shutil
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = tempfile.mkdtemp()
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'pdf', 'pptx', 'ppt', 'md', 'docx', 'doc'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Path to the agents directory
AGENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../agents'))
INPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../input'))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../output'))

# DynamoDB configuration
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'aws-migration-business-cases')
DYNAMODB_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# S3 configuration (optional)
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', None)
S3_ENABLED = S3_BUCKET_NAME is not None

# Initialize DynamoDB client (will be None if credentials not available)
dynamodb_client = None
dynamodb_table = None
try:
    dynamodb_client = boto3.resource('dynamodb', region_name=DYNAMODB_REGION)
    dynamodb_table = dynamodb_client.Table(DYNAMODB_TABLE_NAME)
except Exception as e:
    print(f"Warning: DynamoDB not available: {str(e)}")

# Initialize S3 client (will be None if not configured)
s3_client = None
if S3_ENABLED:
    try:
        s3_client = boto3.client('s3', region_name=DYNAMODB_REGION)
        # Verify bucket exists
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
        print(f"✓ S3 bucket '{S3_BUCKET_NAME}' is accessible")
    except Exception as e:
        print(f"Warning: S3 not available: {str(e)}")
        s3_client = None
        S3_ENABLED = False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        s3_client.upload_file(file_path, S3_BUCKET_NAME, s3_key)
        return s3_key
    except Exception as e:
        print(f"Error uploading to S3: {str(e)}")
        return None

def download_file_from_s3(s3_key, local_path):
    """Download a file from S3 to local path"""
    if not is_s3_enabled():
        return False
    
    try:
        s3_client.download_file(S3_BUCKET_NAME, s3_key, local_path)
        return True
    except Exception as e:
        print(f"Error downloading from S3: {str(e)}")
        return False

def delete_files_from_s3(case_id):
    """Delete all files for a case from S3"""
    if not is_s3_enabled():
        return True
    
    try:
        # List all objects with the case_id prefix
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=f"{case_id}/"
        )
        
        if 'Contents' in response:
            objects = [{'Key': obj['Key']} for obj in response['Contents']]
            if objects:
                s3_client.delete_objects(
                    Bucket=S3_BUCKET_NAME,
                    Delete={'Objects': objects}
                )
        return True
    except Exception as e:
        print(f"Error deleting from S3: {str(e)}")
        return False

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'API is running'})

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
            'bucketName': S3_BUCKET_NAME if is_s3_enabled() else None,
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
        
        # Create case-specific input directory
        case_input_dir = os.path.join(INPUT_DIR, case_id)
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
                    filepath = os.path.join(case_input_dir, target_filename)
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
                filepath = os.path.join(case_input_dir, target_filename)
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
                    filepath = os.path.join(case_input_dir, safe_filename)
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
        case_project_info_file = os.path.join(case_input_dir, 'project_info.json')
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
        output_file = os.path.join(OUTPUT_DIR, 'aws_business_case.md')
        excel_file = os.path.join(OUTPUT_DIR, 'vm_to_ec2_mapping.xlsx')
        
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
            
            # Upload Excel file to S3 if it exists and S3 is enabled
            if os.path.exists(excel_file) and is_s3_enabled():
                s3_key = upload_file_to_s3(excel_file, case_id, 'vm_to_ec2_mapping.xlsx')
                if s3_key:
                    output_s3_keys['excel_mapping'] = s3_key
                    print(f"✓ Excel mapping uploaded to S3: {s3_key}")
            
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
                's3BucketName': S3_BUCKET_NAME if is_s3_enabled() else None,
                'outputS3Keys': output_s3_keys if is_s3_enabled() else None
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Business case file not generated'
            }), 500
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def run_business_case_generator(project_info, selected_agents):
    """
    Run the Python business case generator using the main venv.
    
    The agents require the 'strands' package which is installed in the main venv,
    not the backend venv. We need to use the main venv's Python interpreter.
    """
    import time
    
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
        
        # Save current directory
        original_dir = os.getcwd()
        
        # Change to agents directory
        os.chdir(AGENTS_DIR)
        
        try:
            # Use os.system instead of subprocess to avoid scanner warnings
            # This executes: python3 aws_business_case.py
            exit_code = os.system(f'"{main_venv_python}" aws_business_case.py > /tmp/business_case_output.log 2>&1')
            
            if exit_code != 0:
                # Read error output
                try:
                    with open('/tmp/business_case_output.log', 'r') as f:
                        error_output = f.read()
                    raise Exception(f"Generator failed with exit code {exit_code}: {error_output[-500:]}")
                except:
                    raise Exception(f"Generator failed with exit code {exit_code}")
            
            # Calculate execution time
            execution_time = f"{time.time() - start_time:.2f}s"
            
            return {
                'execution_time': execution_time,
                'token_usage': 'N/A',
                'stdout': 'Business case generated successfully'
            }
            
        finally:
            # Restore original directory
            os.chdir(original_dir)
        
    except Exception as e:
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
    
    try:
        data = request.json
        case_id = data.get('caseId')
        
        if not case_id:
            # Generate new ID if not provided
            case_id = f"case-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        item = {
            'caseId': case_id,
            'projectInfo': data.get('projectInfo', {}),
            'uploadedFiles': data.get('uploadedFiles', {}),
            'selectedAgents': data.get('selectedAgents', {}),
            'businessCaseContent': data.get('businessCaseContent', ''),
            'createdAt': data.get('createdAt', datetime.utcnow().isoformat()),
            'lastUpdated': datetime.utcnow().isoformat(),
            'executionStats': data.get('executionStats', {}),
            's3FileKeys': data.get('s3FileKeys', {}) if is_s3_enabled() else {},
            'outputS3Keys': data.get('outputS3Keys', {}) if is_s3_enabled() else {},
            's3BucketName': S3_BUCKET_NAME if is_s3_enabled() else None,
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
        return jsonify({
            'success': False,
            'message': f'DynamoDB error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/dynamodb/list', methods=['GET'])
def list_business_cases():
    """List all saved business cases"""
    if not is_dynamodb_enabled():
        return jsonify({
            'success': False,
            'message': 'DynamoDB is not enabled or configured'
        }), 503
    
    try:
        response = dynamodb_table.scan(
            ProjectionExpression='caseId, projectInfo, createdAt, lastUpdated'
        )
        
        items = response.get('Items', [])
        
        # Sort by lastUpdated descending
        items.sort(key=lambda x: x.get('lastUpdated', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'cases': items
        })
        
    except ClientError as e:
        return jsonify({
            'success': False,
            'message': f'DynamoDB error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/dynamodb/load/<case_id>', methods=['GET'])
def load_business_case(case_id):
    """Load a specific business case from DynamoDB and restore files from S3"""
    if not is_dynamodb_enabled():
        return jsonify({
            'success': False,
            'message': 'DynamoDB is not enabled or configured'
        }), 503
    
    try:
        response = dynamodb_table.get_item(Key={'caseId': case_id})
        
        if 'Item' not in response:
            return jsonify({
                'success': False,
                'message': 'Business case not found'
            }), 404
        
        case_data = response['Item']
        
        # Restore input files from S3 if available
        files_restored = {}
        if is_s3_enabled() and 's3FileKeys' in case_data:
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
                            local_path = os.path.join(INPUT_DIR, filename)
                            if download_file_from_s3(s3_key, local_path):
                                rv_restored.append(True)
                            else:
                                rv_restored.append(False)
                        files_restored[key] = all(rv_restored)
                    else:
                        # Single RVTools file (backward compatibility)
                        local_path = os.path.join(INPUT_DIR, os.path.basename(value))
                        files_restored[key] = download_file_from_s3(value, local_path)
                elif key == 'mra':
                    # Handle MRA file - preserve original filename from S3
                    filename = os.path.basename(value)
                    local_path = os.path.join(INPUT_DIR, filename)
                    if download_file_from_s3(value, local_path):
                        files_restored[key] = True
                    else:
                        files_restored[key] = False
                elif key in file_mapping:
                    local_path = os.path.join(INPUT_DIR, file_mapping[key])
                    if download_file_from_s3(value, local_path):
                        files_restored[key] = True
                    else:
                        files_restored[key] = False
        
        # Restore output files from S3 if available
        output_files_restored = {}
        if is_s3_enabled() and 'outputS3Keys' in case_data:
            output_s3_keys = case_data.get('outputS3Keys', {})
            
            # Restore business case
            if 'business_case' in output_s3_keys:
                s3_key = output_s3_keys['business_case']
                local_path = os.path.join(OUTPUT_DIR, 'aws_business_case.md')
                if download_file_from_s3(s3_key, local_path):
                    output_files_restored['business_case'] = True
                    print(f"✓ Restored business case from S3: {s3_key}")
                else:
                    output_files_restored['business_case'] = False
            
            # Restore Excel mapping
            if 'excel_mapping' in output_s3_keys:
                s3_key = output_s3_keys['excel_mapping']
                local_path = os.path.join(OUTPUT_DIR, 'vm_to_ec2_mapping.xlsx')
                if download_file_from_s3(s3_key, local_path):
                    output_files_restored['excel_mapping'] = True
                    print(f"✓ Restored Excel mapping from S3: {s3_key}")
                else:
                    output_files_restored['excel_mapping'] = False
        
        return jsonify({
            'success': True,
            'case': case_data,
            'filesRestored': files_restored if files_restored else None,
            'outputFilesRestored': output_files_restored if output_files_restored else None,
            's3Enabled': is_s3_enabled()
        })
        
    except ClientError as e:
        return jsonify({
            'success': False,
            'message': f'DynamoDB error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/dynamodb/delete/<case_id>', methods=['DELETE'])
def delete_business_case(case_id):
    """Delete a business case from DynamoDB and S3"""
    if not is_dynamodb_enabled():
        return jsonify({
            'success': False,
            'message': 'DynamoDB is not enabled or configured'
        }), 503
    
    try:
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
        return jsonify({
            'success': False,
            'message': f'DynamoDB error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

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
                
                # Use the region from the request, not DYNAMODB_REGION
                bedrock = boto3.client('bedrock-runtime', region_name=aws_region)
                
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
                    print(f"AI enhancement failed: {error_code} - {error_msg}")
                    return jsonify({
                        'success': False,
                        'message': f'AWS Bedrock error: {error_msg}',
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
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

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
