import httpx
import json
from typing import Dict, List, Optional
from datetime import datetime
import os

class AIIncidentAnalyzer:
    """
    Uses Ollama (local LLM) to perform root cause analysis on incidents
    This is your competitive moat - reasoning, not just pattern matching
    """
    
    def __init__(self, ollama_base_url: str = None, model: str = None):
        self.base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.client = httpx.Client(timeout=120.0)  # Longer timeout for local inference
        
        print(f"[AI] Using Ollama at {self.base_url} with model {self.model}")
    
    def analyze_incident(
        self,
        anomalies: List[Dict],
        recent_logs: List[Dict],
        recent_deployments: List[Dict],
        service_name: str
    ) -> Dict:
        """
        Perform comprehensive incident analysis using Ollama
        """
        
        # Build context for the LLM
        context = self._build_context(anomalies, recent_logs, recent_deployments, service_name)
        
        # Create the analysis prompt
        prompt = f"""You are an expert SRE analyzing a production incident for the {service_name} service.

## Current Situation

{context}

## Your Task

Analyze this incident and provide a JSON response with:

1. Root cause analysis (most likely cause with confidence 0-100%)
2. Contributing factors (what else might be involved)
3. Immediate actions (ranked by likelihood of success)
4. Preventive measures (how to avoid this in the future)

Respond ONLY with valid JSON in this EXACT format (no markdown, no explanations outside JSON):

{{
  "root_cause": {{
    "description": "concise description of the root cause",
    "confidence": 85,
    "reasoning": "technical explanation of why you believe this"
  }},
  "contributing_factors": [
    "factor 1",
    "factor 2"
  ],
  "recommended_actions": [
    {{
      "action": "rollback deployment to previous version",
      "reasoning": "deployment correlates with latency spike",
      "risk": "low",
      "expected_impact": "should restore normal latency within 2 minutes",
      "priority": 1
    }},
    {{
      "action": "scale up pods to handle load",
      "reasoning": "CPU usage is high",
      "risk": "medium",
      "expected_impact": "may reduce latency but won't fix root cause",
      "priority": 2
    }}
  ],
  "preventive_measures": [
    "add load testing to CI/CD pipeline",
    "implement gradual rollout strategy"
  ],
  "severity": "high",
  "estimated_customer_impact": "description of impact"
}}

JSON Response:"""

        try:
            # Call Ollama API
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",  # Request JSON output
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent output
                        "num_predict": 1000
                    }
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API returned {response.status_code}: {response.text}")
            
            # Parse response
            result = response.json()
            analysis_text = result.get("response", "")
            
            # Extract and parse JSON
            analysis = self._extract_json(analysis_text)
            
            # Add metadata
            analysis["analyzed_at"] = datetime.utcnow().isoformat()
            analysis["service"] = service_name
            analysis["model_used"] = self.model
            
            return analysis
            
        except Exception as e:
            print(f"[AI ERROR] Analysis failed: {e}")
            # Fallback response if AI fails
            return self._fallback_analysis(anomalies, service_name, str(e))
    
    def _build_context(
        self,
        anomalies: List[Dict],
        logs: List[Dict],
        deployments: List[Dict],
        service_name: str
    ) -> str:
        """
        Build a clear context string for the LLM
        """
        context_parts = []
        
        # Anomalies detected
        if anomalies:
            context_parts.append("### Anomalies Detected\n")
            for i, anomaly in enumerate(anomalies[:5], 1):  # Limit to 5 most recent
                metric = anomaly.get('metric_name', 'unknown')
                current = anomaly.get('current_value', 0)
                baseline = anomaly.get('baseline_mean', 0)
                deviation = anomaly.get('deviation_percent', 0)
                severity = anomaly.get('severity', 'unknown')
                
                context_parts.append(
                    f"{i}. **{metric}**: {current:.2f} (baseline: {baseline:.2f}, "
                    f"deviation: {deviation:+.1f}%, severity: {severity})"
                )
        
        # Recent deployments
        if deployments:
            context_parts.append("\n### Recent Deployments (last 30 min)\n")
            for i, deploy in enumerate(deployments[-3:], 1):  # Last 3 deployments
                version = deploy.get('version', 'unknown')
                status = deploy.get('status', 'unknown')
                timestamp = deploy.get('timestamp', 'unknown')
                
                context_parts.append(
                    f"{i}. Version {version} - Status: {status} - Time: {timestamp}"
                )
        else:
            context_parts.append("\n### Recent Deployments\nNo deployments in the last 30 minutes")
        
        # Error logs
        error_logs = [log for log in logs if log.get('level') in ['ERROR', 'CRITICAL']]
        if error_logs:
            context_parts.append("\n### Recent Error Logs\n")
            # Group similar errors
            error_messages = {}
            for log in error_logs:
                msg = log.get('message', 'No message')[:80]
                error_messages[msg] = error_messages.get(msg, 0) + 1
            
            for i, (msg, count) in enumerate(list(error_messages.items())[:5], 1):
                context_parts.append(f"{i}. [{count}x] {msg}")
        
        # System metrics summary
        context_parts.append("\n### Service Context\n")
        context_parts.append(f"- Service: {service_name}")
        context_parts.append(f"- Total anomalies detected: {len(anomalies)}")
        context_parts.append(f"- Error logs in window: {len(error_logs)}")
        context_parts.append(f"- Recent deployments: {len(deployments)}")
        
        return "\n".join(context_parts)
    
    def _extract_json(self, text: str) -> Dict:
        """
        Extract JSON from LLM response, handling various formats
        """
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                try:
                    return json.loads(text[start:end])
                except:
                    pass
            
            # Last resort - return structured fallback
            raise ValueError(f"Could not extract valid JSON from response: {text[:200]}")
    
    def _fallback_analysis(self, anomalies: List[Dict], service_name: str, error: str) -> Dict:
        """
        Provide a basic analysis if AI fails
        """
        # Try to do basic rule-based analysis
        severity = "medium"
        root_cause_desc = "Multiple anomalies detected"
        
        if anomalies:
            # Check severity
            critical_count = sum(1 for a in anomalies if a.get('severity') == 'critical')
            if critical_count > 0:
                severity = "critical"
                root_cause_desc = f"{critical_count} critical anomalies detected"
        
        return {
            "root_cause": {
                "description": root_cause_desc,
                "confidence": 50,
                "reasoning": f"AI analysis unavailable, basic rule-based detection triggered. Error: {error}"
            },
            "contributing_factors": [
                f"{len(anomalies)} anomalies detected",
                "Requires manual investigation"
            ],
            "recommended_actions": [
                {
                    "action": "investigate manually",
                    "reasoning": "automated analysis failed",
                    "risk": "n/a",
                    "expected_impact": "requires human review",
                    "priority": 1
                }
            ],
            "preventive_measures": ["Review AI analyzer configuration", "Check Ollama service"],
            "severity": severity,
            "estimated_customer_impact": "unknown - requires investigation",
            "analyzed_at": datetime.utcnow().isoformat(),
            "service": service_name,
            "error": error
        }
    
    def generate_incident_summary(self, analysis: Dict) -> str:
        """
        Generate a human-readable incident summary
        """
        root_cause = analysis.get('root_cause', {})
        severity = analysis.get('severity', 'unknown')
        service = analysis.get('service', 'unknown')
        
        summary = f"🚨 **{severity.upper()} Incident Detected - {service}**\n\n"
        
        summary += f"**Root Cause ({root_cause.get('confidence', 0)}% confidence)**\n"
        summary += f"{root_cause.get('description', 'Unknown')}\n\n"
        
        summary += f"**Reasoning**: {root_cause.get('reasoning', 'N/A')}\n\n"
        
        actions = analysis.get('recommended_actions', [])
        if actions:
            summary += "**Recommended Actions**\n"
            for i, action in enumerate(actions[:3], 1):
                summary += f"{i}. {action.get('action', 'Unknown')} "
                summary += f"(Risk: {action.get('risk', 'unknown')})\n"
                summary += f"   → {action.get('reasoning', 'N/A')}\n"
        
        impact = analysis.get('estimated_customer_impact', 'Unknown')
        summary += f"\n**Customer Impact**: {impact}\n"
        
        return summary
    
    def __del__(self):
        """Clean up HTTP client"""
        try:
            self.client.close()
        except:
            pass