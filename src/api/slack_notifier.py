import httpx
import json
from typing import Dict, Optional
from datetime import datetime

class SlackNotifier:
    """
    Send rich incident notifications to Slack
    """
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def send_incident_alert(
        self,
        analysis: Dict,
        anomalies: List[Dict],
        include_actions: bool = True
    ) -> bool:
        """
        Send formatted incident alert to Slack
        """
        try:
            root_cause = analysis.get('root_cause', {})
            severity = analysis.get('severity', 'unknown')
            service = analysis.get('service', 'unknown')
            confidence = root_cause.get('confidence', 0)
            
            # Choose emoji based on severity
            emoji_map = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }
            emoji = emoji_map.get(severity, '⚪')
            
            # Build Slack blocks for rich formatting
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {severity.upper()} Incident - {service}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Detected at:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Confidence:*\n{confidence}%"
                        }
                    ]
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Root Cause:*\n{root_cause.get('description', 'Unknown')}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Analysis:*\n{root_cause.get('reasoning', 'No reasoning provided')}"
                    }
                }
            ]
            
            # Add anomaly details
            if anomalies:
                anomaly_text = "*Detected Anomalies:*\n"
                for anomaly in anomalies[:3]:  # Show top 3
                    metric = anomaly.get('metric_name', 'unknown')
                    current = anomaly.get('current_value', 0)
                    baseline = anomaly.get('baseline_mean', 0)
                    deviation = anomaly.get('deviation_percent', 0)
                    
                    anomaly_text += f"• `{metric}`: {current:.2f} "
                    anomaly_text += f"(baseline: {baseline:.2f}, {deviation:+.1f}%)\n"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": anomaly_text
                    }
                })
            
            # Add recommended actions
            if include_actions:
                actions = analysis.get('recommended_actions', [])
                if actions:
                    blocks.append({"type": "divider"})
                    
                    action_text = "*Recommended Actions:*\n"
                    for i, action in enumerate(actions[:3], 1):
                        action_name = action.get('action', 'Unknown')
                        reasoning = action.get('reasoning', 'N/A')
                        risk = action.get('risk', 'unknown')
                        
                        risk_emoji = {'low': '✅', 'medium': '⚠️', 'high': '❌'}.get(risk, '❓')
                        
                        action_text += f"{i}. {risk_emoji} *{action_name}*\n"
                        action_text += f"   _{reasoning}_\n"
                        action_text += f"   Risk: {risk}\n\n"
                    
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": action_text
                        }
                    })
            
            # Add customer impact
            impact = analysis.get('estimated_customer_impact', 'Unknown')
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Customer Impact:*\n{impact}"
                }
            })
            
            # Add action buttons (for Phase 2)
            # blocks.append({
            #     "type": "actions",
            #     "elements": [
            #         {
            #             "type": "button",
            #             "text": {"type": "plain_text", "text": "View Details"},
            #             "style": "primary",
            #             "url": f"https://your-dashboard.com/incidents/{analysis.get('id', '')}"
            #         },
            #         {
            #             "type": "button",
            #             "text": {"type": "plain_text", "text": "Acknowledge"},
            #             "value": "ack"
            #         }
            #     ]
            # })
            
            # Send to Slack
            payload = {
                "blocks": blocks,
                "text": f"{emoji} {severity.upper()} incident detected in {service}"  # Fallback text
            }
            
            response = await self.client.post(
                self.webhook_url,
                json=payload
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"[ERROR] Failed to send Slack notification: {e}")
            return False
    
    async def send_resolution_alert(
        self,
        service: str,
        action_taken: str,
        duration_minutes: float,
        success: bool
    ) -> bool:
        """
        Send alert when incident is resolved
        """
        try:
            emoji = "✅" if success else "⚠️"
            status = "Resolved" if success else "Action Completed"
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} Incident {status} - {service}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Action Taken:*\n{action_taken}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Duration:*\n{duration_minutes:.1f} minutes"
                        }
                    ]
                }
            ]
            
            payload = {
                "blocks": blocks,
                "text": f"{status}: {service}"
            }
            
            response = await self.client.post(
                self.webhook_url,
                json=payload
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"[ERROR] Failed to send resolution notification: {e}")
            return False
    
    async def send_test_alert(self) -> bool:
        """
        Send a test notification to verify Slack integration
        """
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🧪 AI DevOps Autopilot - Test Alert"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "If you're seeing this, Slack integration is working! 🎉"
                    }
                }
            ]
            
            payload = {
                "blocks": blocks,
                "text": "Test alert from AI DevOps Autopilot"
            }
            
            response = await self.client.post(
                self.webhook_url,
                json=payload
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"[ERROR] Test notification failed: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()