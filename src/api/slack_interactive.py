"""
Interactive Slack Notifications - Phase 2
Adds approval buttons and rich interactions
"""

import httpx
import json
from typing import Dict, List
from datetime import datetime, timezone

class InteractiveSlackNotifier:
    """
    Enhanced Slack notifier with interactive buttons for action approval
    """
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def send_incident_with_actions(
        self,
        incident_id: str,
        analysis: Dict,
        anomalies: List[Dict],
        proposed_actions: List[Dict],
        similar_incidents: List[Dict] = None
    ) -> bool:
        """
        Send incident alert with interactive action buttons
        """
        try:
            root_cause = analysis.get('root_cause', {})
            severity = analysis.get('severity', 'unknown')
            service = analysis.get('service', 'unknown')
            confidence = root_cause.get('confidence', 0)
            
            emoji_map = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }
            emoji = emoji_map.get(severity, '⚪')
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {severity.upper()} Incident Detected - {service}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Incident ID:*\n`{incident_id}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Confidence:*\n{confidence}%"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Detected:*\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Anomalies:*\n{len(anomalies)} detected"
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
                        "text": f"*🔍 Root Cause:*\n{root_cause.get('description', 'Unknown')}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*💡 Analysis:*\n{root_cause.get('reasoning', 'No reasoning provided')[:300]}..."
                    }
                }
            ]
            
            # Add anomaly details
            if anomalies:
                anomaly_text = "*📊 Anomalies Detected:*\n"
                for anomaly in anomalies[:3]:
                    metric = anomaly.get('metric_name', 'unknown')
                    current = anomaly.get('current_value', 0)
                    baseline = anomaly.get('baseline_mean', 0)
                    deviation = anomaly.get('deviation_percent', 0)
                    severity_icon = "🔴" if anomaly.get('severity') == 'critical' else "🟠"
                    
                    anomaly_text += f"{severity_icon} `{metric}`: {current:.2f} "
                    anomaly_text += f"(baseline: {baseline:.2f}, {deviation:+.1f}%)\n"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": anomaly_text
                    }
                })
            
            # Add similar incidents section
            if similar_incidents and len(similar_incidents) > 0:
                blocks.append({"type": "divider"})
                similar_text = "*🔄 Similar Past Incidents:*\n"
                for inc in similar_incidents[:2]:
                    similar_text += f"• {inc['root_cause']['description']} "
                    similar_text += f"(similarity: {inc['similarity_score']*100:.0f}%, "
                    similar_text += f"resolved in {inc['resolution_time_seconds']/60:.1f}min)\n"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": similar_text
                    }
                })
            
            # Add proposed actions with approval buttons
            if proposed_actions:
                blocks.append({"type": "divider"})
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*🛠️ Recommended Actions:*"
                    }
                })
                
                for i, action in enumerate(proposed_actions[:3], 1):
                    risk_emoji = {
                        'low': '✅',
                        'medium': '⚠️',
                        'high': '❌'
                    }.get(action.get('risk', 'unknown'), '❓')
                    
                    action_text = f"*{i}. {action.get('action_type', 'Unknown Action')}*\n"
                    action_text += f"{risk_emoji} Risk: {action.get('risk', 'unknown')} | "
                    action_text += f"Reasoning: {action.get('reasoning', 'N/A')[:150]}\n"
                    
                    # Add success rate if available
                    if action.get('success_rate'):
                        action_text += f"📈 Success rate: {action['success_rate']:.0f}% ({action.get('success_count', 0)} past uses)\n"
                    
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": action_text
                        },
                        "accessory": {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✓ Approve & Execute"
                            },
                            "style": "primary" if action.get('risk') == 'low' else "danger" if action.get('risk') == 'high' else None,
                            "value": json.dumps({
                                "action_id": action.get('id'),
                                "incident_id": incident_id,
                                "action_type": action.get('action_type')
                            }),
                            "action_id": f"approve_action_{action.get('id')}"
                        }
                    })
            
            # Add customer impact
            blocks.append({"type": "divider"})
            impact = analysis.get('estimated_customer_impact', 'Unknown')
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*👥 Customer Impact:*\n{impact}"
                }
            })
            
            # Add action buttons
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📊 View Dashboard"
                        },
                        "url": f"http://localhost:8000/dashboard",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "👀 View Details"
                        },
                        "value": incident_id,
                        "action_id": f"view_details_{incident_id}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Acknowledge"
                        },
                        "value": incident_id,
                        "action_id": f"acknowledge_{incident_id}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ Dismiss"
                        },
                        "style": "danger",
                        "value": incident_id,
                        "action_id": f"dismiss_{incident_id}"
                    }
                ]
            })
            
            # Send to Slack
            payload = {
                "blocks": blocks,
                "text": f"{emoji} {severity.upper()} incident in {service}"
            }
            
            response = await self.client.post(
                self.webhook_url,
                json=payload
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"[SLACK ERROR] Failed to send interactive notification: {e}")
            return False
    
    async def send_action_result(
        self,
        action: Dict,
        result: Dict,
        incident_id: str
    ) -> bool:
        """
        Send notification about action execution result
        """
        try:
            success = result.get('success', False)
            emoji = "✅" if success else "❌"
            status = "Successfully Completed" if success else "Failed"
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} Action {status}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Incident ID:*\n`{incident_id}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Action:*\n{action.get('action_type', 'Unknown')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Service:*\n{action.get('service', 'Unknown')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Duration:*\n{result.get('duration_seconds', 0):.1f}s"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Result:*\n{result.get('message', 'No message')}"
                    }
                }
            ]
            
            # Add dry run notice if applicable
            if result.get('dry_run'):
                blocks.insert(1, {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "⚠️ *DRY RUN MODE* - No actual changes were made"
                        }
                    ]
                })
            
            payload = {
                "blocks": blocks,
                "text": f"{status}: {action.get('action_type')}"
            }
            
            response = await self.client.post(
                self.webhook_url,
                json=payload
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"[SLACK ERROR] Failed to send action result: {e}")
            return False
    
    async def send_learning_update(
        self,
        service: str,
        insights: Dict
    ) -> bool:
        """
        Send weekly learning insights
        """
        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📚 Weekly Learning Report - {service}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Incidents:*\n{insights.get('total_incidents', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Success Rate:*\n{insights.get('success_rate', 0):.1f}%"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Avg Resolution:*\n{insights.get('avg_resolution_time_minutes', 0):.1f}min"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Recent (7d):*\n{insights.get('recent_incidents_7_days', 0)} incidents"
                        }
                    ]
                }
            ]
            
            # Add top causes
            if insights.get('top_root_causes'):
                cause_text = "*Top Root Causes:*\n"
                for cause in insights['top_root_causes'][:3]:
                    cause_text += f"• {cause['cause']} ({cause['count']}x)\n"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": cause_text
                    }
                })
            
            # Add effective actions
            if insights.get('most_effective_actions'):
                action_text = "*Most Effective Actions:*\n"
                for action in insights['most_effective_actions'][:3]:
                    action_text += f"• {action['action_type']}: {action['success_rate']:.0f}% success ({action['usage_count']} uses)\n"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": action_text
                    }
                })
            
            payload = {
                "blocks": blocks,
                "text": f"Weekly learning report for {service}"
            }
            
            response = await self.client.post(
                self.webhook_url,
                json=payload
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"[SLACK ERROR] Failed to send learning update: {e}")
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()