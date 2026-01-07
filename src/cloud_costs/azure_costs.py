"""
Azure Cost Management Integration
Fetches cost data from Azure using azure-mgmt-costmanagement
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json


class AzureCostClient:
    """Azure Cost Management client for fetching cloud costs"""
    
    def __init__(self, subscription_id: str, client_id: str, client_secret: str, tenant_id: str):
        """
        Initialize Azure Cost Management client
        
        Args:
            subscription_id: Azure Subscription ID
            client_id: Azure AD Application (Client) ID
            client_secret: Azure AD Client Secret
            tenant_id: Azure AD Tenant ID
        """
        self.subscription_id = subscription_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self._credential = None
        self._client = None
    
    def _get_credential(self):
        """Get Azure credential"""
        if self._credential is None:
            try:
                from azure.identity import ClientSecretCredential
                self._credential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            except ImportError:
                raise ImportError("azure-identity package required. Install with: pip install azure-identity")
        return self._credential
    
    def _get_client(self):
        """Get Azure Cost Management client"""
        if self._client is None:
            try:
                from azure.mgmt.costmanagement import CostManagementClient
                self._client = CostManagementClient(
                    credential=self._get_credential(),
                    subscription_id=self.subscription_id
                )
            except ImportError:
                raise ImportError("azure-mgmt-costmanagement package required. Install with: pip install azure-mgmt-costmanagement")
        return self._client
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Test if credentials are valid
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Try to get credential and verify it works
            credential = self._get_credential()
            # Get a token to verify credentials
            token = credential.get_token("https://management.azure.com/.default")
            if token:
                return True, "Azure connection successful"
            return False, "Failed to obtain Azure token"
        except Exception as e:
            error_msg = str(e)
            if 'AADSTS7000215' in error_msg:
                return False, "Invalid Azure Client Secret"
            elif 'AADSTS700016' in error_msg:
                return False, "Invalid Azure Client ID or Tenant ID"
            elif 'AADSTS90002' in error_msg:
                return False, "Invalid Azure Tenant ID"
            else:
                return False, f"Azure connection failed: {error_msg}"
    
    def get_daily_costs(self, days: int = 30) -> Dict[str, Any]:
        """
        Get daily cost breakdown for the last N days
        
        Args:
            days: Number of days to fetch (default: 30)
            
        Returns:
            Dictionary with daily costs and totals
        """
        try:
            from azure.mgmt.costmanagement.models import (
                QueryDefinition, QueryDataset, QueryTimePeriod,
                QueryAggregation, QueryGrouping, TimeframeType, GranularityType
            )
            
            client = self._get_client()
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            scope = f"/subscriptions/{self.subscription_id}"
            
            query = QueryDefinition(
                type="ActualCost",
                timeframe=TimeframeType.CUSTOM,
                time_period=QueryTimePeriod(
                    from_property=start_date,
                    to=end_date
                ),
                dataset=QueryDataset(
                    granularity=GranularityType.DAILY,
                    aggregation={
                        "totalCost": QueryAggregation(name="Cost", function="Sum")
                    }
                )
            )
            
            response = client.query.usage(scope=scope, parameters=query)
            
            daily_costs = []
            total_cost = 0.0
            
            for row in response.rows:
                cost = float(row[0])
                date = row[1] if len(row) > 1 else None
                daily_costs.append({
                    'date': str(date)[:10] if date else 'Unknown',
                    'cost': round(cost, 2),
                    'currency': 'USD'
                })
                total_cost += cost
            
            return {
                'provider': 'azure',
                'period_days': days,
                'daily_costs': daily_costs,
                'total_cost': round(total_cost, 2),
                'average_daily_cost': round(total_cost / max(len(daily_costs), 1), 2),
                'currency': 'USD'
            }
        except ImportError as e:
            return {
                'provider': 'azure',
                'error': f"Missing Azure SDK: {e}",
                'daily_costs': [],
                'total_cost': 0
            }
        except Exception as e:
            return {
                'provider': 'azure',
                'error': str(e),
                'daily_costs': [],
                'total_cost': 0
            }
    
    def get_service_breakdown(self, days: int = 30) -> Dict[str, Any]:
        """
        Get cost breakdown by Azure service
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with service-level costs
        """
        try:
            from azure.mgmt.costmanagement.models import (
                QueryDefinition, QueryDataset, QueryTimePeriod,
                QueryAggregation, QueryGrouping, TimeframeType
            )
            
            client = self._get_client()
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            scope = f"/subscriptions/{self.subscription_id}"
            
            query = QueryDefinition(
                type="ActualCost",
                timeframe=TimeframeType.CUSTOM,
                time_period=QueryTimePeriod(
                    from_property=start_date,
                    to=end_date
                ),
                dataset=QueryDataset(
                    aggregation={
                        "totalCost": QueryAggregation(name="Cost", function="Sum")
                    },
                    grouping=[
                        QueryGrouping(type="Dimension", name="ServiceName")
                    ]
                )
            )
            
            response = client.query.usage(scope=scope, parameters=query)
            
            services = []
            for row in response.rows:
                cost = float(row[0])
                service_name = row[1] if len(row) > 1 else 'Unknown'
                services.append({
                    'service': service_name,
                    'cost': round(cost, 2)
                })
            
            # Sort by cost descending
            services.sort(key=lambda x: x['cost'], reverse=True)
            
            return {
                'provider': 'azure',
                'period_days': days,
                'services': services[:20],
                'total_services': len(services)
            }
        except Exception as e:
            return {
                'provider': 'azure',
                'error': str(e),
                'services': []
            }
    
    def get_current_month_summary(self) -> Dict[str, Any]:
        """Get current month cost summary"""
        try:
            result = self.get_daily_costs(days=30)
            
            if 'error' in result:
                return result
            
            today = datetime.utcnow()
            first_of_month = today.replace(day=1)
            days_elapsed = (today - first_of_month).days + 1
            days_in_month = 30
            
            current_spend = result.get('total_cost', 0)
            projected_cost = (current_spend / days_elapsed) * days_in_month if days_elapsed > 0 else 0
            
            return {
                'provider': 'azure',
                'current_month_spend': round(current_spend, 2),
                'projected_month_end': round(projected_cost, 2),
                'days_elapsed': days_elapsed,
                'currency': 'USD'
            }
        except Exception as e:
            return {
                'provider': 'azure',
                'error': str(e),
                'current_month_spend': 0
            }
