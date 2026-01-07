"""
AWS Cost Explorer Integration
Fetches cost data from AWS using boto3
"""

import boto3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json


class AWSCostClient:
    """AWS Cost Explorer client for fetching cloud costs"""
    
    def __init__(self, access_key_id: str, secret_access_key: str, region: str = 'us-east-1'):
        """
        Initialize AWS Cost Explorer client
        
        Args:
            access_key_id: AWS Access Key ID
            secret_access_key: AWS Secret Access Key
            region: AWS region (default: us-east-1, required for Cost Explorer)
        """
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region
        self._client = None
    
    def _get_client(self):
        """Get or create boto3 Cost Explorer client"""
        if self._client is None:
            self._client = boto3.client(
                'ce',
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region
            )
        return self._client
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Test if credentials are valid
        
        Returns:
            Tuple of (success, message)
        """
        try:
            client = self._get_client()
            # Try to get cost for today to verify credentials
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)
            
            client.get_cost_and_usage(
                TimePeriod={
                    'Start': yesterday.isoformat(),
                    'End': today.isoformat()
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost']
            )
            return True, "AWS connection successful"
        except Exception as e:
            error_msg = str(e)
            if 'InvalidAccessKeyId' in error_msg:
                return False, "Invalid AWS Access Key ID"
            elif 'SignatureDoesNotMatch' in error_msg:
                return False, "Invalid AWS Secret Access Key"
            elif 'AccessDenied' in error_msg:
                return False, "Access denied - ensure IAM user has ce:GetCostAndUsage permission"
            else:
                return False, f"AWS connection failed: {error_msg}"
    
    def get_daily_costs(self, days: int = 30) -> Dict[str, Any]:
        """
        Get daily cost breakdown for the last N days
        
        Args:
            days: Number of days to fetch (default: 30)
            
        Returns:
            Dictionary with daily costs and totals
        """
        try:
            client = self._get_client()
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            response = client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.isoformat(),
                    'End': end_date.isoformat()
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost', 'UsageQuantity']
            )
            
            daily_costs = []
            total_cost = 0.0
            
            for result in response.get('ResultsByTime', []):
                cost = float(result['Total']['UnblendedCost']['Amount'])
                daily_costs.append({
                    'date': result['TimePeriod']['Start'],
                    'cost': round(cost, 2),
                    'currency': result['Total']['UnblendedCost']['Unit']
                })
                total_cost += cost
            
            return {
                'provider': 'aws',
                'period_days': days,
                'daily_costs': daily_costs,
                'total_cost': round(total_cost, 2),
                'average_daily_cost': round(total_cost / max(len(daily_costs), 1), 2),
                'currency': 'USD'
            }
        except Exception as e:
            return {
                'provider': 'aws',
                'error': str(e),
                'daily_costs': [],
                'total_cost': 0
            }
    
    def get_service_breakdown(self, days: int = 30) -> Dict[str, Any]:
        """
        Get cost breakdown by AWS service
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with service-level costs
        """
        try:
            client = self._get_client()
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            response = client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.isoformat(),
                    'End': end_date.isoformat()
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'}
                ]
            )
            
            services = {}
            for result in response.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    service_name = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    if service_name in services:
                        services[service_name] += cost
                    else:
                        services[service_name] = cost
            
            # Sort by cost descending
            sorted_services = sorted(
                [{'service': k, 'cost': round(v, 2)} for k, v in services.items()],
                key=lambda x: x['cost'],
                reverse=True
            )
            
            return {
                'provider': 'aws',
                'period_days': days,
                'services': sorted_services[:20],  # Top 20 services
                'total_services': len(services)
            }
        except Exception as e:
            return {
                'provider': 'aws',
                'error': str(e),
                'services': []
            }
    
    def get_current_month_summary(self) -> Dict[str, Any]:
        """Get current month cost summary"""
        try:
            client = self._get_client()
            today = datetime.utcnow().date()
            first_of_month = today.replace(day=1)
            
            response = client.get_cost_and_usage(
                TimePeriod={
                    'Start': first_of_month.isoformat(),
                    'End': today.isoformat()
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost']
            )
            
            current_spend = 0.0
            for result in response.get('ResultsByTime', []):
                current_spend += float(result['Total']['UnblendedCost']['Amount'])
            
            # Calculate projected month-end cost
            days_elapsed = (today - first_of_month).days + 1
            days_in_month = 30  # Approximate
            projected_cost = (current_spend / days_elapsed) * days_in_month if days_elapsed > 0 else 0
            
            return {
                'provider': 'aws',
                'current_month_spend': round(current_spend, 2),
                'projected_month_end': round(projected_cost, 2),
                'days_elapsed': days_elapsed,
                'currency': 'USD'
            }
        except Exception as e:
            return {
                'provider': 'aws',
                'error': str(e),
                'current_month_spend': 0
            }
