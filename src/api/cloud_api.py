"""
Cloud API Router - Cloud cost integration endpoints for AWS, Azure, GCP
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from src.database import get_db_context
from src.rate_limiting import limiter

router = APIRouter(prefix="/api/cloud", tags=["Cloud Costs"])


# Data Models
class CloudConnectRequest(BaseModel):
    provider: str  # aws, azure, gcp
    credentials: dict  # Provider-specific credentials


class CloudCostRequest(BaseModel):
    days: Optional[int] = 30


@router.post("/connect")
@limiter.limit("10/minute")  # Cloud credential operations
async def connect_cloud_provider(request: Request, data: CloudConnectRequest):
    """Connect to a cloud provider and save encrypted credentials"""
    try:
        from src.cloud_costs.encryption import encrypt_credentials, validate_credentials_format
        from src.models import CloudCredential
        
        provider = data.provider.lower()
        
        # Validate provider
        if provider not in ['aws', 'azure', 'gcp']:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}. Use aws, azure, or gcp")
        
        # Validate credentials format
        is_valid, error_msg = validate_credentials_format(provider, data.credentials)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Test connection before saving
        test_success = False
        test_message = ""
        
        try:
            if provider == 'aws':
                from src.cloud_costs.aws_costs import AWSCostClient
                client = AWSCostClient(
                    data.credentials['access_key_id'],
                    data.credentials['secret_access_key']
                )
                test_success, test_message = client.test_connection()
                
            elif provider == 'azure':
                from src.cloud_costs.azure_costs import AzureCostClient
                client = AzureCostClient(
                    data.credentials['subscription_id'],
                    data.credentials['client_id'],
                    data.credentials['client_secret'],
                    data.credentials['tenant_id']
                )
                test_success, test_message = client.test_connection()
                
            elif provider == 'gcp':
                from src.cloud_costs.gcp_costs import GCPCostClient
                client = GCPCostClient(data.credentials['service_account_json'])
                test_success, test_message = client.test_connection()
        except ImportError as ie:
            # SDK not installed - save anyway and note the issue
            test_message = f"SDK not installed: {ie}. Credentials saved but cannot verify."
            test_success = True  # Allow saving anyway
        
        if not test_success:
            return {
                "success": False,
                "message": test_message,
                "connected": False
            }
        
        # Encrypt and save credentials
        encrypted = encrypt_credentials(data.credentials)
        
        # Use a default user ID for now
        user_id = "dashboard_user"
        
        with get_db_context() as db:
            existing = db.query(CloudCredential).filter(
                CloudCredential.user_id == user_id,
                CloudCredential.provider == provider
            ).first()
            
            if existing:
                existing.encrypted_credentials = encrypted
                existing.last_tested = datetime.now(timezone.utc)
                existing.last_test_success = test_success
                existing.last_error = None if test_success else test_message
                existing.is_active = True
            else:
                new_cred = CloudCredential(
                    user_id=user_id,
                    provider=provider,
                    encrypted_credentials=encrypted,
                    last_tested=datetime.now(timezone.utc),
                    last_test_success=test_success,
                    is_active=True
                )
                db.add(new_cred)
            
            db.commit()
        
        print(f"[CLOUD] ✓ Connected to {provider.upper()}")
        
        return {
            "success": True,
            "message": test_message or f"Successfully connected to {provider.upper()}",
            "connected": True,
            "provider": provider
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[CLOUD] Error connecting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_cloud_connection_status():
    """Get status of all cloud provider connections"""
    try:
        from src.models import CloudCredential
        
        user_id = "dashboard_user"
        
        with get_db_context() as db:
            credentials = db.query(CloudCredential).filter(
                CloudCredential.user_id == user_id,
                CloudCredential.is_active == True
            ).all()
            
            connections = []
            for cred in credentials:
                connections.append({
                    "provider": cred.provider,
                    "connected": True,
                    "last_tested": cred.last_tested.isoformat() if cred.last_tested else None,
                    "last_test_success": cred.last_test_success,
                    "last_error": cred.last_error
                })
            
            return {"connections": connections, "total_connected": len(connections)}
            
    except Exception as e:
        return {"connections": [], "total_connected": 0, "error": str(e)}


@router.get("/costs")
async def get_cloud_costs(days: int = 30):
    """Fetch real cloud costs from connected providers"""
    try:
        from src.models import CloudCredential
        from src.cloud_costs.encryption import decrypt_credentials
        
        user_id = "dashboard_user"
        
        with get_db_context() as db:
            credentials = db.query(CloudCredential).filter(
                CloudCredential.user_id == user_id,
                CloudCredential.is_active == True
            ).all()
            
            if not credentials:
                return {"connected": False, "message": "No cloud providers connected", "costs": {}}
            
            all_costs = {}
            total_spend = 0.0
            
            for cred in credentials:
                try:
                    decrypted = decrypt_credentials(cred.encrypted_credentials)
                    
                    if cred.provider == 'aws':
                        from src.cloud_costs.aws_costs import AWSCostClient
                        client = AWSCostClient(decrypted['access_key_id'], decrypted['secret_access_key'])
                        summary = client.get_current_month_summary()
                        services = client.get_service_breakdown(days)
                        
                    elif cred.provider == 'azure':
                        from src.cloud_costs.azure_costs import AzureCostClient
                        client = AzureCostClient(decrypted['subscription_id'], decrypted['client_id'], 
                                                  decrypted['client_secret'], decrypted['tenant_id'])
                        summary = client.get_current_month_summary()
                        services = client.get_service_breakdown(days)
                        
                    elif cred.provider == 'gcp':
                        from src.cloud_costs.gcp_costs import GCPCostClient
                        client = GCPCostClient(decrypted['service_account_json'])
                        summary = client.get_current_month_summary()
                        services = client.get_service_breakdown(days)
                    
                    all_costs[cred.provider] = {"summary": summary, "services": services}
                    total_spend += summary.get('current_month_spend', 0)
                    cred.last_cost_fetch = datetime.now(timezone.utc)
                    
                except Exception as e:
                    all_costs[cred.provider] = {"error": str(e)}
            
            db.commit()
            
            return {
                "connected": True,
                "providers": list(all_costs.keys()),
                "costs": all_costs,
                "total_month_spend": round(total_spend, 2)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/disconnect/{provider}")
async def disconnect_cloud_provider(provider: str):
    """Disconnect from a cloud provider"""
    try:
        from src.models import CloudCredential
        
        user_id = "dashboard_user"
        provider = provider.lower()
        
        with get_db_context() as db:
            cred = db.query(CloudCredential).filter(
                CloudCredential.user_id == user_id,
                CloudCredential.provider == provider
            ).first()
            
            if not cred:
                raise HTTPException(status_code=404, detail=f"No {provider} connection found")
            
            db.delete(cred)
            db.commit()
            
            return {"success": True, "message": f"Disconnected from {provider.upper()}"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
