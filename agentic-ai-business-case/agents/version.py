"""Version information for AWS Migration Business Case Generator"""

__version__ = "1.0.0"
__release_date__ = "2024-12-09"
__author__ = "AWS Migration Team"

# Feature flags for v1.0
FEATURES = {
    "dual_pricing": True,
    "deterministic_atx": True,
    "business_case_validation": True,
    "smart_agent_selection": True,
    "excel_export": True,
    "multi_stage_generation": True
}

def get_version():
    """Get version string"""
    return f"v{__version__}"

def get_features():
    """Get enabled features"""
    return {k: v for k, v in FEATURES.items() if v}
