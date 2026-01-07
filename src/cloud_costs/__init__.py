"""
Cloud Cost Integration Module
Supports AWS, Azure, and GCP cost fetching with secure credential management
"""

# Use lazy imports to avoid requiring all cloud SDKs at startup
# Individual modules will raise ImportError with helpful messages if SDK is missing

__all__ = [
    'AWSCostClient',
    'AzureCostClient', 
    'GCPCostClient',
    'encrypt_credentials',
    'decrypt_credentials',
    'assess_action',
    'get_cost_guard'
]

def __getattr__(name):
    """Lazy loader for module components"""
    if name == 'AWSCostClient':
        from .aws_costs import AWSCostClient
        return AWSCostClient
    elif name == 'AzureCostClient':
        from .azure_costs import AzureCostClient
        return AzureCostClient
    elif name == 'GCPCostClient':
        from .gcp_costs import GCPCostClient
        return GCPCostClient
    elif name in ('encrypt_credentials', 'decrypt_credentials'):
        from .encryption import encrypt_credentials, decrypt_credentials
        return encrypt_credentials if name == 'encrypt_credentials' else decrypt_credentials
    elif name in ('assess_action', 'get_cost_guard'):
        from .cost_guard import assess_action, get_cost_guard
        return assess_action if name == 'assess_action' else get_cost_guard
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
