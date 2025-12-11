"""
Business Case Validator
Validates and fixes hallucinations in generated business cases
Runs after business case generation to ensure accuracy
"""

import re
import os
import pandas as pd
from typing import Dict, List, Tuple, Optional


class BusinessCaseValidator:
    """Validates business case against source data and fixes hallucinations"""
    
    def __init__(self, business_case_path: str, excel_path: Optional[str] = None):
        """
        Initialize validator
        
        Args:
            business_case_path: Path to generated business case markdown file
            excel_path: Path to Excel file with exact costs (if available)
        """
        self.business_case_path = business_case_path
        self.excel_path = excel_path
        self.issues_found = []
        self.fixes_applied = []
        
        # Load business case content
        # Security: Specify encoding explicitly to prevent encoding issues
        with open(business_case_path, 'r', encoding='utf-8') as f:
            self.content = f.read()
        
        # Load Excel data if available
        self.excel_data = None
        if excel_path and os.path.exists(excel_path):
            self.excel_data = self._load_excel_data(excel_path)
    
    def _load_excel_data(self, excel_path: str) -> Dict:
        """Load exact costs from Excel file"""
        try:
            xl = pd.ExcelFile(excel_path)
            
            # Check if this is RVTools or IT Inventory format
            if 'Pricing Comparison' in xl.sheet_names:
                # RVTools format
                df = pd.read_excel(excel_path, sheet_name='Pricing Comparison')
                return {
                    'type': 'rvtools',
                    'total_vms': df.iloc[0, 1] if len(df) > 0 else None,
                    'option1_monthly': df.iloc[3, 1] if len(df) > 3 else None,
                    'option1_annual': df.iloc[4, 1] if len(df) > 4 else None,
                    'option2_monthly': df.iloc[8, 1] if len(df) > 8 else None,
                    'option2_annual': df.iloc[9, 1] if len(df) > 9 else None,
                    'has_databases': False
                }
            elif 'Summary' in xl.sheet_names:
                # IT Inventory format
                df = pd.read_excel(excel_path, sheet_name='Summary')
                total_servers = df.iloc[0, 1] if len(df) > 0 else None
                total_databases = df.iloc[1, 1] if len(df) > 1 else None
                return {
                    'type': 'it_inventory',
                    'total_servers': total_servers,
                    'total_databases': total_databases,
                    'option1_monthly': df.iloc[4, 1] if len(df) > 4 else None,
                    'option1_annual': df.iloc[5, 1] if len(df) > 5 else None,
                    'has_databases': total_databases > 0 if total_databases else False
                }
            
            return None
        except Exception as e:
            print(f"Warning: Could not load Excel data: {e}")
            return None
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Run all validations
        
        Returns:
            Tuple of (is_valid, issues_found, fixes_applied)
        """
        print("="*80)
        print("BUSINESS CASE VALIDATION")
        print("="*80)
        
        # Run validation checks
        self._check_rds_hallucination()
        self._check_migration_cost_ramp()
        self._check_cost_consistency()
        self._check_vm_count_consistency()
        
        # Apply fixes if issues found
        if self.issues_found:
            print(f"\n⚠️  Found {len(self.issues_found)} issues")
            for issue in self.issues_found:
                print(f"   - {issue}")
            
            self._apply_fixes()
            
            if self.fixes_applied:
                print(f"\n✅ Applied {len(self.fixes_applied)} fixes")
                for fix in self.fixes_applied:
                    print(f"   - {fix}")
                
                # Save fixed content
                # Security: Specify encoding explicitly to prevent encoding issues
                with open(self.business_case_path, 'w', encoding='utf-8') as f:
                    f.write(self.content)
                print(f"\n✓ Updated business case saved: {self.business_case_path}")
            
            return False, self.issues_found, self.fixes_applied
        else:
            print("\n✅ No issues found - business case is valid")
            return True, [], []
    
    def _check_rds_hallucination(self):
        """Check for RDS hallucination in RVTools/ATX-only business cases"""
        # Check if this is RVTools or ATX without databases
        if self.excel_data:
            if self.excel_data['type'] == 'rvtools':
                # RVTools = no databases
                self._check_rds_mentions_rvtools()
            elif self.excel_data['type'] == 'it_inventory' and not self.excel_data['has_databases']:
                # IT Inventory with 0 databases
                self._check_rds_mentions_rvtools()
        else:
            # Check for ATX with 0 databases in the content
            # ATX business cases include the Assessment Scope in the document
            if 'SQL Servers: 0' in self.content or 'Total Databases: 0' in self.content:
                print("   Detected ATX with 0 databases - checking for RDS hallucinations")
                self._check_rds_mentions_rvtools()
            # Also check if this is ATX by looking at the title
            elif 'ATX' in self.content[:500]:  # Check first 500 chars for ATX mention
                # For ATX, check if there are database mentions in cost breakdown
                if 'RDS Monthly Cost' in self.content or 'databases' in self.content.lower():
                    # Need to verify if databases actually exist
                    # If we see "Based on X servers and Y databases" extract Y
                    db_match = re.search(r'Based on \d+ servers and (\d+) databases', self.content)
                    if db_match:
                        db_count = int(db_match.group(1))
                        if db_count == 0:
                            print(f"   Detected ATX with {db_count} databases but RDS costs present")
                            self._check_rds_mentions_rvtools()
                    else:
                        # Can't determine database count, but ATX with RDS costs is suspicious
                        print("   Detected ATX with RDS costs - checking for hallucinations")
                        self._check_rds_mentions_rvtools()
    
    def _check_rds_mentions_rvtools(self):
        """Check for inappropriate RDS mentions in EC2-only migrations"""
        # Find Cost Analysis section
        cost_section_match = re.search(
            r'## Cost Analysis.*?(?=\n## |\Z)',
            self.content,
            re.DOTALL
        )
        
        if not cost_section_match:
            return
        
        cost_section = cost_section_match.group(0)
        
        # Check for RDS in option titles
        if re.search(r'Option \d+:.*\+ RDS', cost_section):
            self.issues_found.append("RDS mentioned in option titles (EC2-only migration)")
        
        # Check for RDS upfront fees
        if 'RDS Upfront Fees' in cost_section:
            self.issues_found.append("RDS Upfront Fees mentioned (EC2-only migration)")
        
        # Check for database cost breakdowns
        if re.search(r'Databases?\s*\(RDS\)', cost_section):
            self.issues_found.append("Database (RDS) in cost breakdown (EC2-only migration)")
        
        # Check for RDS Monthly Cost
        if 'RDS Monthly Cost' in cost_section:
            self.issues_found.append("RDS Monthly Cost mentioned (EC2-only migration)")
        
        # Check for "for RDS" in notes
        if re.search(r'for RDS', cost_section, re.IGNORECASE):
            self.issues_found.append("'for RDS' mentioned in pricing notes (EC2-only migration)")
        
        # Check Executive Summary for RDS mentions
        exec_summary_match = re.search(
            r'## Executive Summary.*?(?=\n## |\Z)',
            self.content,
            re.DOTALL
        )
        if exec_summary_match:
            exec_section = exec_summary_match.group(0)
            if 'for RDS' in exec_section or 'RDS' in exec_section:
                self.issues_found.append("RDS mentioned in Executive Summary (EC2-only migration)")
    
    def _check_migration_cost_ramp(self):
        """Check if migration cost ramp is calculated correctly"""
        if not self.excel_data:
            return
        
        # Find migration cost ramp section
        ramp_match = re.search(
            r'Migration Cost Ramp.*?(?:\n\n|\n##)',
            self.content,
            re.DOTALL
        )
        
        if not ramp_match:
            return
        
        ramp_section = ramp_match.group(0)
        
        # Extract monthly cost from business case
        monthly_cost = self.excel_data.get('option1_monthly')
        if not monthly_cost:
            return
        
        # Ensure monthly_cost is a number
        if isinstance(monthly_cost, str):
            monthly_cost = float(monthly_cost.replace('$', '').replace(',', ''))
        
        # Extract ramp costs from business case
        ramp_costs = re.findall(r'\$[\d,]+\.?\d*', ramp_section)
        
        if ramp_costs:
            # Check if any ramp cost is way too high (>10x monthly cost)
            for cost_str in ramp_costs:
                cost_value = float(cost_str.replace('$', '').replace(',', ''))
                if cost_value > monthly_cost * 10:
                    self.issues_found.append(
                        f"Migration ramp cost ${cost_value:,.2f} is too high "
                        f"(monthly cost is ${monthly_cost:,.2f})"
                    )
                    break
    
    def _check_cost_consistency(self):
        """Check if costs are consistent throughout the document"""
        if not self.excel_data:
            return
        
        # Extract all monthly cost mentions
        monthly_pattern = r'Monthly.*?Cost.*?\$[\d,]+\.?\d*'
        monthly_mentions = re.findall(monthly_pattern, self.content, re.IGNORECASE)
        
        if len(monthly_mentions) > 1:
            # Extract just the numbers
            costs = []
            for mention in monthly_mentions:
                cost_match = re.search(r'\$([\d,]+\.?\d*)', mention)
                if cost_match:
                    cost_value = float(cost_match.group(1).replace(',', ''))
                    costs.append(cost_value)
            
            # Check if all costs are the same (within 1% tolerance)
            if costs:
                expected_cost = self.excel_data.get('option1_monthly')
                if expected_cost:
                    # Ensure expected_cost is a number
                    if isinstance(expected_cost, str):
                        expected_cost = float(expected_cost.replace('$', '').replace(',', ''))
                    
                    for cost in costs:
                        if abs(cost - expected_cost) / expected_cost > 0.01:
                            self.issues_found.append(
                                f"Inconsistent monthly cost: ${cost:,.2f} "
                                f"(expected ${expected_cost:,.2f})"
                            )
                            break
    
    def _check_vm_count_consistency(self):
        """Check if VM counts are consistent"""
        # Extract all VM count mentions
        vm_pattern = r'(?:Total VMs?|Total Servers?):\s*(\d+)'
        vm_mentions = re.findall(vm_pattern, self.content, re.IGNORECASE)
        
        if len(vm_mentions) > 1:
            # Check if all counts are the same
            counts = [int(count) for count in vm_mentions]
            if len(set(counts)) > 1:
                self.issues_found.append(
                    f"Inconsistent VM counts: {counts}"
                )
    
    def _apply_fixes(self):
        """Apply fixes to the business case content"""
        original_content = self.content
        
        # Fix 1: Remove RDS from option titles in Cost Analysis
        self.content = re.sub(
            r'(Option \d+:.*?)\s*\+\s*RDS[^-\n]*',
            r'\1',
            self.content
        )
        if self.content != original_content:
            self.fixes_applied.append("Removed '+ RDS' from option titles")
            original_content = self.content
        
        # Fix 2: Remove RDS Upfront Fees lines
        self.content = re.sub(
            r'-\s*RDS Upfront Fees.*?\n',
            '',
            self.content
        )
        if self.content != original_content:
            self.fixes_applied.append("Removed 'RDS Upfront Fees' lines")
            original_content = self.content
        
        # Fix 3: Remove "3-Year Total Cost (incl. upfront)" for EC2-only
        if self.excel_data and self.excel_data.get('type') == 'rvtools':
            self.content = re.sub(
                r'-\s*3-Year Total Cost \(incl\. upfront\).*?\n',
                '',
                self.content
            )
            if self.content != original_content:
                self.fixes_applied.append("Removed '3-Year Total Cost (incl. upfront)' for EC2-only")
                original_content = self.content
        
        # Fix 4: Remove "for RDS" from pricing notes
        self.content = re.sub(
            r'\s+for EC2 and[^.\n]*for RDS',
            ' for EC2',
            self.content
        )
        if self.content != original_content:
            self.fixes_applied.append("Removed 'for RDS' from pricing notes")
            original_content = self.content
        
        # Fix 5: Remove RDS Monthly Cost lines
        self.content = re.sub(
            r'-\s*RDS Monthly Cost:.*?\n',
            '',
            self.content
        )
        if self.content != original_content:
            self.fixes_applied.append("Removed 'RDS Monthly Cost' lines")
            original_content = self.content
        
        # Fix 6: Remove "and X databases" from server counts
        self.content = re.sub(
            r'(\d+ servers)\s+and\s+\d+\s+databases',
            r'\1',
            self.content
        )
        if self.content != original_content:
            self.fixes_applied.append("Removed database counts from server descriptions")
            original_content = self.content
        
        # Fix 7: Remove RDS/Aurora from service lists (but keep as generic recommendations)
        # Only remove from specific cost-related contexts
        self.content = re.sub(
            r'Cost Breakdown \(Option \d+ - EC2 Instance SP \+ RDS[^)]*\)',
            'Cost Breakdown (Option 1 - EC2 Instance SP)',
            self.content
        )
        if self.content != original_content:
            self.fixes_applied.append("Removed RDS from cost breakdown titles")
            original_content = self.content
        
        # Fix 4: Fix migration cost ramp if too high
        if self.excel_data:
            monthly_cost = self.excel_data.get('option1_monthly')
            if monthly_cost:
                # Ensure monthly_cost is a number
                if isinstance(monthly_cost, str):
                    monthly_cost = float(monthly_cost.replace('$', '').replace(',', ''))
                
                # Find and fix migration ramp section
                def fix_ramp_cost(match):
                    percentage_match = re.search(r'(\d+)%', match.group(0))
                    if percentage_match:
                        percentage = int(percentage_match.group(1)) / 100
                        correct_cost = monthly_cost * percentage
                        # Replace the cost in the line
                        fixed_line = re.sub(
                            r'\$[\d,]+\.?\d*',
                            f'${correct_cost:,.2f}',
                            match.group(0)
                        )
                        return fixed_line
                    return match.group(0)
                
                # Fix costs in migration ramp section
                ramp_pattern = r'(Months? \d+-?\d*.*?\(\d+%\).*?\$[\d,]+\.?\d*)'
                new_content = re.sub(ramp_pattern, fix_ramp_cost, self.content)
                
                if new_content != self.content:
                    self.fixes_applied.append("Fixed migration cost ramp calculations")
                    self.content = new_content


def validate_business_case(
    business_case_path: str,
    excel_path: Optional[str] = None
) -> Tuple[bool, List[str], List[str]]:
    """
    Validate and fix business case
    
    Args:
        business_case_path: Path to business case markdown file
        excel_path: Path to Excel file with exact costs (optional)
    
    Returns:
        Tuple of (is_valid, issues_found, fixes_applied)
    """
    validator = BusinessCaseValidator(business_case_path, excel_path)
    return validator.validate()


if __name__ == "__main__":
    # Test validation
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python business_case_validator.py <business_case.md> [excel_file.xlsx]")
        sys.exit(1)
    
    business_case_path = sys.argv[1]
    excel_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    is_valid, issues, fixes = validate_business_case(business_case_path, excel_path)
    
    if is_valid:
        print("\n✅ Business case is valid")
        sys.exit(0)
    else:
        print(f"\n⚠️  Business case had issues (fixed: {len(fixes)})")
        sys.exit(0 if fixes else 1)
