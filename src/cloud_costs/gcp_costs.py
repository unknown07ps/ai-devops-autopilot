"""
GCP Cloud Billing Integration
Fetches cost data from Google Cloud Platform
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json


class GCPCostClient:
    """GCP Cloud Billing client for fetching cloud costs"""
    
    def __init__(self, service_account_json: str):
        """
        Initialize GCP Cloud Billing client
        
        Args:
            service_account_json: Service account JSON key (as string or dict)
        """
        if isinstance(service_account_json, str):
            try:
                self.credentials_info = json.loads(service_account_json)
            except json.JSONDecodeError:
                # Assume it's a file path
                self.credentials_info = service_account_json
        else:
            self.credentials_info = service_account_json
        
        self._credentials = None
        self._client = None
        self._project_id = None
    
    def _get_credentials(self):
        """Get GCP credentials from service account"""
        if self._credentials is None:
            try:
                from google.oauth2 import service_account
                
                if isinstance(self.credentials_info, dict):
                    self._credentials = service_account.Credentials.from_service_account_info(
                        self.credentials_info,
                        scopes=['https://www.googleapis.com/auth/cloud-billing.readonly',
                               'https://www.googleapis.com/auth/cloud-platform']
                    )
                    self._project_id = self.credentials_info.get('project_id')
                else:
                    self._credentials = service_account.Credentials.from_service_account_file(
                        self.credentials_info,
                        scopes=['https://www.googleapis.com/auth/cloud-billing.readonly',
                               'https://www.googleapis.com/auth/cloud-platform']
                    )
            except ImportError:
                raise ImportError("google-auth package required. Install with: pip install google-auth")
        return self._credentials
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Test if credentials are valid
        
        Returns:
            Tuple of (success, message)
        """
        try:
            credentials = self._get_credentials()
            
            # Verify the credentials by checking if they can be refreshed
            if credentials.valid or credentials.expired:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
            
            return True, "GCP connection successful"
        except Exception as e:
            error_msg = str(e)
            if 'invalid_grant' in error_msg.lower():
                return False, "Invalid GCP service account credentials"
            elif 'not found' in error_msg.lower():
                return False, "GCP project not found"
            else:
                return False, f"GCP connection failed: {error_msg}"
    
    def get_daily_costs(self, days: int = 30) -> Dict[str, Any]:
        """
        Get daily cost breakdown for the last N days
        
        Note: GCP BigQuery export is required for detailed billing data.
        This uses the Cloud Billing API for basic information.
        
        Args:
            days: Number of days to fetch (default: 30)
            
        Returns:
            Dictionary with daily costs and totals
        """
        try:
            from google.cloud import bigquery
            
            credentials = self._get_credentials()
            client = bigquery.Client(credentials=credentials, project=self._project_id)
            
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            # Query billing export table (requires BigQuery billing export to be set up)
            query = f"""
                SELECT
                    DATE(usage_start_time) as date,
                    SUM(cost) as daily_cost
                FROM `{self._project_id}.billing_export.gcp_billing_export_v1_*`
                WHERE DATE(usage_start_time) >= '{start_date.isoformat()}'
                AND DATE(usage_start_time) < '{end_date.isoformat()}'
                GROUP BY date
                ORDER BY date
            """
            
            try:
                results = client.query(query).result()
                daily_costs = []
                total_cost = 0.0
                
                for row in results:
                    cost = float(row.daily_cost or 0)
                    daily_costs.append({
                        'date': row.date.isoformat(),
                        'cost': round(cost, 2),
                        'currency': 'USD'
                    })
                    total_cost += cost
                
                return {
                    'provider': 'gcp',
                    'period_days': days,
                    'daily_costs': daily_costs,
                    'total_cost': round(total_cost, 2),
                    'average_daily_cost': round(total_cost / max(len(daily_costs), 1), 2),
                    'currency': 'USD'
                }
            except Exception as query_error:
                # BigQuery export might not be set up, return placeholder
                return {
                    'provider': 'gcp',
                    'period_days': days,
                    'daily_costs': [],
                    'total_cost': 0,
                    'message': 'BigQuery billing export not configured. Set up billing export for detailed costs.',
                    'setup_url': 'https://cloud.google.com/billing/docs/how-to/export-data-bigquery'
                }
                
        except ImportError:
            return {
                'provider': 'gcp',
                'error': 'google-cloud-bigquery package required. Install with: pip install google-cloud-bigquery',
                'daily_costs': [],
                'total_cost': 0
            }
        except Exception as e:
            return {
                'provider': 'gcp',
                'error': str(e),
                'daily_costs': [],
                'total_cost': 0
            }
    
    def get_service_breakdown(self, days: int = 30) -> Dict[str, Any]:
        """
        Get cost breakdown by GCP service
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with service-level costs
        """
        try:
            from google.cloud import bigquery
            
            credentials = self._get_credentials()
            client = bigquery.Client(credentials=credentials, project=self._project_id)
            
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            query = f"""
                SELECT
                    service.description as service_name,
                    SUM(cost) as total_cost
                FROM `{self._project_id}.billing_export.gcp_billing_export_v1_*`
                WHERE DATE(usage_start_time) >= '{start_date.isoformat()}'
                AND DATE(usage_start_time) < '{end_date.isoformat()}'
                GROUP BY service_name
                ORDER BY total_cost DESC
                LIMIT 20
            """
            
            try:
                results = client.query(query).result()
                services = []
                
                for row in results:
                    services.append({
                        'service': row.service_name,
                        'cost': round(float(row.total_cost or 0), 2)
                    })
                
                return {
                    'provider': 'gcp',
                    'period_days': days,
                    'services': services,
                    'total_services': len(services)
                }
            except Exception:
                return {
                    'provider': 'gcp',
                    'services': [],
                    'message': 'BigQuery billing export not configured'
                }
                
        except Exception as e:
            return {
                'provider': 'gcp',
                'error': str(e),
                'services': []
            }
    
    def get_current_month_summary(self) -> Dict[str, Any]:
        """Get current month cost summary"""
        try:
            result = self.get_daily_costs(days=30)
            
            today = datetime.utcnow()
            first_of_month = today.replace(day=1)
            days_elapsed = (today - first_of_month).days + 1
            days_in_month = 30
            
            current_spend = result.get('total_cost', 0)
            projected_cost = (current_spend / days_elapsed) * days_in_month if days_elapsed > 0 else 0
            
            return {
                'provider': 'gcp',
                'current_month_spend': round(current_spend, 2),
                'projected_month_end': round(projected_cost, 2),
                'days_elapsed': days_elapsed,
                'currency': 'USD',
                'message': result.get('message')
            }
        except Exception as e:
            return {
                'provider': 'gcp',
                'error': str(e),
                'current_month_spend': 0
            }
