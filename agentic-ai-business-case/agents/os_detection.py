"""
Shared OS detection logic for consistent classification across all modules
"""

def detect_os_type(os_string):
    """
    Detect OS type from OS string (Windows, Linux, or Other)
    
    Args:
        os_string: OS name from RVTools (e.g., "Microsoft Windows Server 2019 (64-bit)")
    
    Returns:
        'Windows', 'Linux', or 'Other'
    """
    if not os_string or str(os_string).strip().lower() in ['nan', 'none', '', 'unknown']:
        return 'Other'
    
    os_lower = str(os_string).lower()
    
    # Check for Windows (must be explicit to avoid false positives)
    if 'windows' in os_lower or 'microsoft' in os_lower:
        return 'Windows'
    
    # Check for Linux distributions
    linux_keywords = [
        'linux', 'red hat', 'redhat', 'centos', 'ubuntu', 
        'suse', 'debian', 'oracle linux', 'amazon linux', 'rhel'
    ]
    if any(keyword in os_lower for keyword in linux_keywords):
        return 'Linux'
    
    # Everything else is Other
    return 'Other'


def count_os_distribution(os_series):
    """
    Count Windows, Linux, and Other VMs from a pandas Series
    
    NOTE: "Other" VMs are treated as Linux for pricing and reporting purposes
    
    Args:
        os_series: pandas Series containing OS names
    
    Returns:
        dict with 'windows', 'linux', 'other' counts
        Note: 'other' count is kept for tracking but treated as Linux in totals
    """
    windows_count = 0
    linux_count = 0
    other_count = 0
    
    for os_value in os_series:
        os_type = detect_os_type(os_value)
        if os_type == 'Windows':
            windows_count += 1
        elif os_type == 'Linux':
            linux_count += 1
        else:
            # Treat "Other" as Linux for pricing purposes
            other_count += 1
            linux_count += 1  # Add to Linux count
    
    return {
        'windows': windows_count,
        'linux': linux_count,  # Includes "Other" VMs
        'other': other_count   # Tracked separately for reference
    }
