"""
OLA Analysis Engine
Analyzes Windows Server, SQL Server, and Oracle licensing optimization
"""
import pandas as pd
from typing import Dict, List, Tuple, Optional
import json


class OLAAnalyzer:
    """Main OLA analysis engine"""
    
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.servers = []
        self.databases = []
        self.analysis_results = {}
        
    def parse_rvtools(self, file_path: str) -> pd.DataFrame:
        """Parse RVTools CSV or Excel export"""
        try:
            # Check file extension
            if file_path.lower().endswith('.xlsx') or file_path.lower().endswith('.xls'):
                # Read Excel file - RVTools typically has data in 'vInfo' sheet
                try:
                    df = pd.read_excel(file_path, sheet_name='vInfo', engine='openpyxl')
                except ValueError:
                    # If vInfo sheet doesn't exist, try first sheet
                    df = pd.read_excel(file_path, sheet_name=0, engine='openpyxl')
            else:
                # Try CSV with multiple encodings and error handling
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                df = None
                last_error = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(
                            file_path, 
                            encoding=encoding,
                            on_bad_lines='skip',
                            engine='python',
                            quoting=1
                        )
                        break
                    except (UnicodeDecodeError, pd.errors.ParserError) as e:
                        last_error = e
                        continue
                
                if df is None:
                    raise ValueError(f"Could not parse file. Last error: {last_error}")
            
            # Map RVTools columns to standard names
            column_mapping = {
                'os according to the vmware tools': 'os',
                'os according to the configuration file': 'os_config',
                'vm': 'vm_name',
                'powerstate': 'power_state',
                'dns name': 'dns_name'
            }
            
            # Standardize column names
            df.columns = df.columns.str.strip().str.lower()
            
            # Apply mapping
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df[new_col] = df[old_col]
            
            # Ensure 'os' column exists
            if 'os' not in df.columns and 'os_config' in df.columns:
                df['os'] = df['os_config']
            
            return df
        except Exception as e:
            raise ValueError(f"Error parsing RVTools: {str(e)}")
    
    def parse_database_inventory(self, file_path: str) -> pd.DataFrame:
        """Parse database inventory CSV or Excel"""
        try:
            # Check file extension
            if file_path.lower().endswith('.xlsx') or file_path.lower().endswith('.xls'):
                # Read Excel file - use first sheet
                df = pd.read_excel(file_path, sheet_name=0, engine='openpyxl')
            else:
                # Try CSV with multiple encodings and error handling
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                df = None
                last_error = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(
                            file_path, 
                            encoding=encoding,
                            on_bad_lines='skip',  # Skip malformed lines
                            engine='python',  # More flexible parser
                            quoting=1  # QUOTE_ALL - handle embedded commas
                        )
                        break
                    except (UnicodeDecodeError, pd.errors.ParserError) as e:
                        last_error = e
                        continue
                
                if df is None:
                    raise ValueError(f"Could not parse file. Last error: {last_error}")
            
            df.columns = df.columns.str.strip().str.lower()
            return df
        except Exception as e:
            raise ValueError(f"Error parsing database inventory: {str(e)}")
    
    def calculate_complexity_score(self, servers_df: pd.DataFrame, 
                                   databases_df: pd.DataFrame,
                                   sa_status: str) -> Tuple[int, Dict]:
        """
        Calculate complexity score (0-10)
        Returns: (score, breakdown)
        """
        breakdown = {}
        score = 0
        
        # 1. License Diversity (0-2)
        products = set()
        if len(servers_df[servers_df['os'].str.contains('Windows', case=False, na=False)]) > 0:
            products.add('Windows')
        if len(databases_df[databases_df['type'].str.contains('SQL', case=False, na=False)]) > 0:
            products.add('SQL Server')
        if len(databases_df[databases_df['type'].str.contains('Oracle', case=False, na=False)]) > 0:
            products.add('Oracle')
        
        diversity_score = min(len(products) - 1, 2) if len(products) > 1 else 0
        score += diversity_score
        breakdown['license_diversity'] = {
            'score': diversity_score,
            'products': list(products)
        }
        
        # 2. SA Status (0-2)
        sa_score = {
            'all_active': 0,
            'mixed': 1,
            'none_unknown': 2,
            'need_verify': 1
        }.get(sa_status, 2)
        score += sa_score
        breakdown['sa_status'] = {
            'score': sa_score,
            'status': sa_status
        }
        
        # 3. Feature Dependencies (0-2)
        enterprise_features = databases_df[
            databases_df['features'].str.contains('Always On|Partitioning|RAC', 
                                                 case=False, na=False)
        ] if 'features' in databases_df.columns else pd.DataFrame()
        
        feature_score = 2 if len(enterprise_features) > 0 else 0
        score += feature_score
        breakdown['feature_dependencies'] = {
            'score': feature_score,
            'count': len(enterprise_features)
        }
        
        # 4. Environment Mix (0-2)
        prod_count = len(databases_df[databases_df['environment'].str.contains('Prod', case=False, na=False)])
        total_count = len(databases_df)
        prod_ratio = prod_count / total_count if total_count > 0 else 0
        
        env_score = 2 if prod_ratio > 0.5 else (1 if prod_ratio > 0 else 0)
        score += env_score
        breakdown['environment_mix'] = {
            'score': env_score,
            'production': prod_count,
            'total': total_count
        }
        
        # 5. Scale (0-2)
        total_resources = len(servers_df) + len(databases_df)
        scale_score = 2 if total_resources > 100 else (1 if total_resources > 25 else 0)
        score += scale_score
        breakdown['scale'] = {
            'score': scale_score,
            'total_resources': total_resources
        }
        
        return score, breakdown

    
    def calculate_arr(self, monthly_cost: float) -> float:
        """Calculate Annual Recurring Revenue"""
        return monthly_cost * 12
    
    def get_ola_recommendation(self, arr: float, complexity_score: int, 
                              has_databases: bool = False, has_windows: bool = False,
                              sa_status: str = 'need_verify') -> Dict:
        """
        Determine OLA recommendation based on ARR and complexity
        Returns: recommendation dict with level, rationale, next_steps, and fallback guidance
        """
        # Decision matrix
        if arr > 500000:
            if complexity_score >= 7:
                level = "OLA Required"
                priority = "critical"
            elif complexity_score >= 4:
                level = "OLA Strongly Recommended"
                priority = "high"
            else:
                level = "OLA Recommended"
                priority = "medium"
        elif arr > 100000:
            if complexity_score >= 7:
                level = "OLA Strongly Recommended"
                priority = "high"
            elif complexity_score >= 4:
                level = "OLA Recommended"
                priority = "medium"
            else:
                level = "OLA Optional"
                priority = "low"
        else:  # arr <= 100000
            if complexity_score >= 7:
                level = "OLA Recommended"
                priority = "medium"
            elif complexity_score >= 4:
                level = "OLA Optional"
                priority = "low"
            else:
                level = "Self-Service OK"
                priority = "none"
        
        # Generate rationale
        rationale = self._generate_rationale(arr, complexity_score, level)
        
        # Generate next steps
        next_steps = self._generate_next_steps(level)
        
        # Generate fallback recommendations for assumption-based decisions
        fallback_recommendations = self.generate_fallback_recommendations(
            arr, complexity_score, has_databases, has_windows, sa_status
        )
        
        return {
            'level': level,
            'priority': priority,
            'arr': arr,
            'complexity_score': complexity_score,
            'rationale': rationale,
            'next_steps': next_steps,
            'fallback_recommendations': fallback_recommendations
        }
    
    def _generate_rationale(self, arr: float, complexity: int, level: str) -> List[str]:
        """Generate rationale for OLA recommendation"""
        rationale = []
        
        # ARR assessment
        if arr > 500000:
            rationale.append(f"High ARR potential (${arr:,.0f}/year)")
        elif arr > 100000:
            rationale.append(f"Medium ARR potential (${arr:,.0f}/year)")
        else:
            rationale.append(f"Low ARR (${arr:,.0f}/year)")
        
        # Complexity assessment
        if complexity >= 7:
            rationale.append("High complexity (multiple products, features, production workloads)")
        elif complexity >= 4:
            rationale.append("Medium complexity (some licensing challenges)")
        else:
            rationale.append("Low complexity (straightforward configuration)")
        
        # Specific recommendations
        if level in ["OLA Required", "OLA Strongly Recommended"]:
            rationale.append("License compliance verification critical")
            rationale.append("Significant optimization opportunities")
            rationale.append("Risk mitigation needed")
        elif level == "OLA Recommended":
            rationale.append("Professional guidance beneficial")
            rationale.append("Cost optimization opportunities")
        elif level == "OLA Optional":
            rationale.append("Can proceed with self-service")
            rationale.append("OLA available if needed")
        else:  # Self-Service OK
            rationale.append("Simple migration suitable for self-service")
            rationale.append("AWS Migration Hub recommended")
        
        return rationale
    
    def _generate_next_steps(self, level: str) -> List[Dict]:
        """Generate next steps based on OLA recommendation"""
        if level in ["OLA Required", "OLA Strongly Recommended"]:
            return [
                {"step": "Export preliminary analysis report", "required": True},
                {"step": "Gather license agreements from customer", "required": True},
                {"step": "Contact AWS account team", "required": True},
                {"step": "Request official AWS OLA engagement", "required": True},
                {"step": "Share preliminary analysis with AWS OLA team", "required": True},
                {"step": "Schedule OLA kickoff meeting", "required": True}
            ]
        elif level == "OLA Recommended":
            return [
                {"step": "Export preliminary analysis report", "required": True},
                {"step": "Review with customer", "required": True},
                {"step": "Consider AWS OLA for detailed analysis", "required": False},
                {"step": "Gather license agreements if proceeding", "required": False},
                {"step": "Begin pilot migration planning", "required": True}
            ]
        elif level == "OLA Optional":
            return [
                {"step": "Export migration plan", "required": True},
                {"step": "Review AWS Migration Hub", "required": True},
                {"step": "Set up AWS environment", "required": True},
                {"step": "Consider AWS OLA if complexity increases", "required": False}
            ]
        else:  # Self-Service OK
            return [
                {"step": "Export migration plan", "required": True},
                {"step": "Use AWS Migration Hub", "required": True},
                {"step": "Leverage AWS documentation", "required": True},
                {"step": "Begin pilot migration", "required": True}
            ]

    
    def generate_fallback_recommendations(self, arr: float, complexity_score: int, 
                                         has_databases: bool, has_windows: bool,
                                         sa_status: str) -> List[Dict]:
        """
        Generate fallback recommendations when full OLA assessment cannot proceed
        
        These are assumption-based decisions for business case development when:
        - License details are unavailable
        - Customer cannot provide license agreements
        - Timeline doesn't allow for full OLA
        - ARR impact is minimal
        
        Returns: List of strategic recommendations
        """
        recommendations = []
        
        # Header recommendation
        recommendations.append({
            'type': 'guidance',
            'priority': 'info',
            'title': '⚠️ Assumption-Based Migration Strategy',
            'message': 'When full OLA assessment cannot proceed and licensing details are unavailable, use these strategic defaults for business case development. These recommendations balance cost, risk, and modernization benefits.'
        })
        
        # Database recommendation - Always prefer RDS
        if has_databases:
            recommendations.append({
                'type': 'database',
                'priority': 'high',
                'title': '🗄️ Databases: Migrate to RDS (License Included)',
                'recommendation': 'Move all SQL Server and Oracle databases to Amazon RDS with License Included',
                'rationale': [
                    'Eliminates license compliance risk - AWS manages all licensing',
                    'Modernization benefits: Automated backups, patching, and high availability',
                    'Reduced operational overhead - No database administration required',
                    'Predictable costs - No surprise license audits or true-ups',
                    'Faster migration - No license verification delays'
                ],
                'tradeoff': 'Higher monthly cost vs BYOL, but justified by operational savings and reduced risk',
                'action': 'Include RDS License Included pricing in business case'
            })
        
        # Windows Server recommendation - License Included for flexibility
        if has_windows:
            recommendations.append({
                'type': 'server',
                'priority': 'high',
                'title': '🖥️ Windows Servers: EC2 with License Included',
                'recommendation': 'Deploy Windows servers on EC2 with License Included',
                'rationale': [
                    'License flexibility - Scale up/down without license constraints',
                    'No Microsoft audit risk - AWS handles compliance',
                    'Faster migration - No license verification required',
                    'Pay-as-you-go - Only pay for what you use',
                    'No upfront license investment required'
                ],
                'tradeoff': 'Higher cost than BYOL, but provides maximum flexibility and zero license risk',
                'action': 'Include EC2 Windows License Included pricing in business case'
            })
        
        # Exception: SQL Server with confirmed SA
        if has_databases and sa_status in ['all_active', 'mixed']:
            recommendations.append({
                'type': 'exception',
                'priority': 'medium',
                'title': '💡 Exception: SQL Server with Active Software Assurance',
                'recommendation': 'If SQL Server licenses have confirmed active SA, consider Dedicated Hosts for BYOL',
                'rationale': [
                    'Maximize existing license investment',
                    'Significant cost savings vs License Included',
                    'License Mobility rights enable BYOL on AWS',
                    'Suitable for stable, long-term workloads'
                ],
                'requirements': [
                    'Must verify active Software Assurance',
                    'Must have License Mobility rights',
                    'Must be comfortable managing licenses on AWS',
                    'Workload must be stable (not highly elastic)'
                ],
                'action': 'If SA confirmed, calculate Dedicated Host BYOL option as alternative'
            })
        
        # ARR Impact Assessment
        if arr < 100000:
            recommendations.append({
                'type': 'arr_impact',
                'priority': 'low',
                'title': '📊 Low ARR Impact - Proceed with Assumptions',
                'message': f'Estimated ARR: ${arr:,.0f}/year - Low enough to proceed with assumption-based decisions',
                'guidance': 'The licensing cost difference has minimal impact on overall business case. Prioritize speed and risk reduction over cost optimization.'
            })
        elif arr < 500000:
            recommendations.append({
                'type': 'arr_impact',
                'priority': 'medium',
                'title': '📊 Medium ARR Impact - Consider OLA if Possible',
                'message': f'Estimated ARR: ${arr:,.0f}/year - Consider pursuing OLA if timeline allows',
                'guidance': 'Potential savings justify OLA effort, but assumption-based approach is acceptable if timeline is tight or license details unavailable.'
            })
        else:
            recommendations.append({
                'type': 'arr_impact',
                'priority': 'high',
                'title': '📊 High ARR Impact - OLA Strongly Recommended',
                'message': f'Estimated ARR: ${arr:,.0f}/year - Strong recommendation to pursue full OLA',
                'guidance': 'Significant potential savings. If full OLA not possible, clearly document assumptions and plan for license optimization post-migration.'
            })
        
        # Summary recommendation
        recommendations.append({
            'type': 'summary',
            'priority': 'info',
            'title': '✅ Recommended Approach for Business Case',
            'strategy': [
                '1. Use RDS License Included for all databases (modernization + risk reduction)',
                '2. Use EC2 License Included for Windows servers (flexibility + compliance)',
                '3. Exception: Use Dedicated Host BYOL only for SQL Server with confirmed active SA',
                '4. Document all assumptions clearly in business case',
                '5. Plan for license optimization review post-migration if ARR is significant'
            ],
            'benefits': [
                'Fastest path to migration',
                'Lowest risk approach',
                'Predictable costs',
                'Modernization benefits',
                'No license compliance concerns'
            ]
        })
        
        return recommendations
