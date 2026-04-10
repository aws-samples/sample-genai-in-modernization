"""
OLA Analysis API Routes
"""
from flask import Blueprint, request, jsonify
import pandas as pd
import sys
import os
import logging
import tempfile
from werkzeug.utils import secure_filename

# Add project root to path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.dirname(BACKEND_DIR)
PROJECT_ROOT = os.path.dirname(UI_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.ola.ola_analyzer import OLAAnalyzer
from agents.ola.ola_pricing import OLAPricingEngine
from utils.bedrock_client import invoke_bedrock_model_without_reasoning

ola_bp = Blueprint('ola', __name__, url_prefix='/api/map/ola')

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@ola_bp.route('/analyze', methods=['POST'])
def analyze_ola():
    """
    Main OLA analysis endpoint
    Accepts: RVTools CSV, Database Inventory CSV, SA status
    Returns: Complete OLA analysis with recommendations
    """
    try:
        # Validate files
        if 'rvtools' not in request.files or 'database_inventory' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Both RVTools and Database Inventory files required'
            }), 400
        
        rvtools_file = request.files['rvtools']
        db_file = request.files['database_inventory']
        
        if not allowed_file(rvtools_file.filename) or not allowed_file(db_file.filename):
            return jsonify({
                'success': False,
                'message': 'Invalid file type. Only CSV/Excel files allowed'
            }), 400
        
        # Get parameters
        sa_status = request.form.get('sa_status', 'need_verify')
        region = request.form.get('region', 'us-east-1')
        
        # Save files temporarily with correct extensions
        rv_ext = os.path.splitext(secure_filename(rvtools_file.filename))[1]
        db_ext = os.path.splitext(secure_filename(db_file.filename))[1]
        
        # Validate extensions are in allowed set
        allowed_exts = {'.csv', '.xlsx', '.xls'}
        if rv_ext.lower() not in allowed_exts:
            rv_ext = '.csv'
        if db_ext.lower() not in allowed_exts:
            db_ext = '.csv'
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=rv_ext) as rv_temp:
            rvtools_file.save(rv_temp.name)
            rv_path = rv_temp.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=db_ext) as db_temp:
            db_file.save(db_temp.name)
            db_path = db_temp.name
        
        try:
            # Initialize analyzer
            analyzer = OLAAnalyzer(region=region)
            
            # Parse files
            servers_df = analyzer.parse_rvtools(rv_path)
            databases_df = analyzer.parse_database_inventory(db_path)
            
            # Calculate complexity
            complexity_score, complexity_breakdown = analyzer.calculate_complexity_score(
                servers_df, databases_df, sa_status
            )
            
            # Initialize pricing engine
            pricing_engine = OLAPricingEngine(region=region)
            
            # Calculate real pricing for all options
            pricing_results = pricing_engine.analyze_migration_options(
                servers_df=servers_df,
                databases_df=databases_df,
                sa_status=sa_status
            )
            
            # Extract costs from pricing results
            estimated_monthly_cost = pricing_results['summary']['license_included_monthly']
            arr = pricing_results['summary']['license_included_annual']
            
            # Get detailed breakdown for all 3 options
            cost_breakdown = {
                'option_1_ec2_shared_li': {
                    'name': 'Windows/SQL on EC2 Shared (License Included)',
                    'windows_monthly': pricing_results['servers']['costs']['shared_ec2_li'],
                    'sql_monthly': 0,  # SQL on EC2 included in windows cost
                    'total_monthly': pricing_results['servers']['costs']['shared_ec2_li'],
                    'total_annual': pricing_results['servers']['costs']['shared_ec2_li'] * 12,
                    'description': 'Windows and SQL Server on shared EC2 with AWS-provided licenses',
                    'windows_count': pricing_results['servers']['windows'],
                    'linux_count': pricing_results['servers']['linux']
                },
                'option_2_dedicated_host_byol': {
                    'name': 'Windows/SQL on Dedicated Hosts (BYOL)',
                    'windows_monthly': pricing_results['servers']['costs']['dedicated_host_byol'],
                    'sql_monthly': pricing_results['databases']['costs']['dedicated_host_byol'],
                    'total_monthly': pricing_results['summary']['dedicated_host_byol_monthly'],
                    'total_annual': pricing_results['summary']['dedicated_host_byol_annual'],
                    'description': 'Windows and SQL Server on Dedicated Hosts with BYOL (requires active SA)',
                    'host_count': pricing_results['servers']['dedicated_host_allocation']['hosts_needed'] if pricing_results['servers']['dedicated_host_allocation'] else 0,
                    'vms_per_host': pricing_results['servers']['dedicated_host_allocation']['utilization']['average'] if pricing_results['servers']['dedicated_host_allocation'] else 0,
                    'sql_host_count': pricing_results['databases']['dedicated_host_allocation']['hosts_needed'] if pricing_results['databases']['dedicated_host_allocation'] else 0,
                    'savings_vs_li': pricing_results['summary']['potential_savings_annual'],
                    'savings_percentage': pricing_results['summary']['savings_percentage']
                },
                'option_3_rds_li': {
                    'name': 'Databases on RDS (License Included)',
                    'sql_monthly': pricing_results['databases']['costs']['rds_li'],
                    'oracle_monthly': 0,  # Included in sql_monthly
                    'total_monthly': pricing_results['databases']['costs']['rds_li'],
                    'total_annual': pricing_results['databases']['costs']['rds_li'] * 12,
                    'description': 'SQL Server and Oracle databases on RDS with AWS-provided licenses',
                    'sql_count': pricing_results['databases']['sql_server'],
                    'oracle_count': pricing_results['databases']['oracle']
                },
                'version_breakdown': {
                    'windows_pre_2019': pricing_results['servers']['windows_pre_2019'],
                    'windows_post_2019': pricing_results['servers']['windows_post_2019'],
                    'windows_unknown': pricing_results['servers']['windows_unknown'],
                    'sql_pre_2019': pricing_results['databases']['sql_pre_2019'],
                    'sql_post_2019': pricing_results['databases']['sql_post_2019'],
                    'sql_unknown': pricing_results['databases']['sql_unknown']
                }
            }
            
            # Get OLA recommendation with fallback guidance
            ola_recommendation = analyzer.get_ola_recommendation(
                arr, 
                complexity_score,
                has_databases=len(databases_df) > 0,
                has_windows=len(servers_df[servers_df['os'].str.contains('Windows', case=False, na=False)]) > 0,
                sa_status=sa_status
            )
            
            # Generate summary
            summary = {
                'total_servers': pricing_results['servers']['total'],
                'windows_servers': pricing_results['servers']['windows'],
                'linux_servers': pricing_results['servers']['linux'],
                'total_databases': pricing_results['databases']['total'],
                'sql_server': pricing_results['databases']['sql_server'],
                'oracle': pricing_results['databases']['oracle'],
                'estimated_monthly_cost': estimated_monthly_cost,
                'estimated_annual_arr': arr,
                'cost_breakdown': cost_breakdown,
                'server_details': pricing_results['servers']['details'],
                'database_details': pricing_results['databases']['details'],
                'complexity_score': complexity_score,
                'complexity_breakdown': complexity_breakdown,
                'ola_recommendation': ola_recommendation,
                'pricing_note': 'Costs calculated using AWS Pricing API with 3-year Reserved Instance (No Upfront) pricing. Includes rightsizing and bin-packing for Dedicated Hosts.',
                'pricing_source': 'AWS Pricing API',
                'recommendations': pricing_results['recommendations']
            }
            
            return jsonify({
                'success': True,
                'summary': summary
            })
            
        finally:
            # Cleanup temp files
            os.unlink(rv_path)
            os.unlink(db_path)
    
    except Exception as e:
        logging.error(f"OLA analysis failed: {e}")
        return jsonify({
            'success': False,
            'message': 'An internal error occurred during OLA analysis'
        }), 500


@ola_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for OLA routes"""
    return jsonify({
        'success': True,
        'message': 'OLA Analysis API is running'
    })
