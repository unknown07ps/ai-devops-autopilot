"""
AI Security Safeguards Module
Protects against prompt injection, unsafe reasoning, and unintended execution
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone


class AISecurityGuard:
    """
    Security layer for AI-driven decisions and actions.
    
    Protects against:
    - Prompt injection attacks
    - Malicious input in context data
    - Unsafe or unexpected AI outputs
    - Actions outside allowed boundaries
    - Reasoning that violates safety policies
    """
    
    def __init__(self):
        # Prompt injection patterns to detect
        self.injection_patterns = [
            # Direct instruction overrides
            r"ignore\s+(previous|all|above)\s+(instructions?|prompts?)",
            r"disregard\s+(your|the)\s+(rules?|instructions?|guidelines?)",
            r"forget\s+(everything|all|what)\s+(you|was)",
            r"new\s+instructions?:",
            r"system\s*prompt:",
            r"</?(system|assistant|user)>",
            
            # Role manipulation
            r"you\s+are\s+now\s+a",
            r"act\s+as\s+(if|a|an)",
            r"pretend\s+(to\s+be|you\s+are)",
            r"roleplay\s+as",
            r"jailbreak",
            r"DAN\s+mode",
            
            # Output manipulation
            r"output\s+only",
            r"respond\s+(only\s+)?with",
            r"print\s+(exactly|only)",
            r"reveal\s+(your|the)\s+(prompt|instructions?)",
            
            # Code execution attempts
            r"execute\s+(this\s+)?code",
            r"run\s+(this\s+)?(command|script)",
            r"eval\s*\(",
            r"exec\s*\(",
            r"import\s+os",
            r"subprocess\.",
            r"__import__",
            
            # Data exfiltration
            r"api[_\s]?key",
            r"secret[_\s]?key",
            r"password",
            r"credentials?",
            r"send\s+to\s+(url|http)",
        ]
        
        # Allowed action types that AI can recommend
        self.allowed_actions = {
            "restart_service",
            "scale_up",
            "scale_down",
            "rollback",
            "clear_cache",
            "increase_memory",
            "add_replicas",
            "remove_replicas",
            "update_config",
            "enable_circuit_breaker",
            "flush_connections",
            "rotate_logs",
            "trigger_gc",
            "adjust_timeout",
            "enable_debug",
            "disable_debug",
        }
        
        # Dangerous patterns in AI output
        self.dangerous_output_patterns = [
            r"rm\s+-rf",
            r"delete\s+all",
            r"drop\s+database",
            r"truncate\s+table",
            r"sudo\s+",
            r"chmod\s+777",
            r"curl\s+.*\|\s*sh",
            r"wget\s+.*\|\s*bash",
        ]
        
        # Maximum values for AI-recommended parameters
        self.parameter_limits = {
            "replicas": (1, 50),
            "memory_mb": (128, 32768),
            "cpu_cores": (0.1, 16),
            "timeout_seconds": (1, 300),
            "scale_factor": (0.5, 5),
            "retry_count": (0, 10),
        }
    
    # =========================================================================
    # Input Sanitization
    # =========================================================================
    
    def sanitize_prompt_input(self, text: str) -> Tuple[str, List[str]]:
        """
        Sanitize input text before sending to LLM.
        
        Returns:
            (sanitized_text, list of detected issues)
        """
        issues = []
        sanitized = text
        
        # Check for injection patterns
        for pattern in self.injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(f"Potential injection: matched pattern '{pattern}'")
                # Escape or remove the suspicious content
                sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)
        
        # Check for excessive special characters (obfuscation attempt)
        special_char_ratio = len(re.findall(r'[^\w\s]', text)) / max(len(text), 1)
        if special_char_ratio > 0.3:
            issues.append("High special character ratio - possible obfuscation")
        
        # Check for unicode tricks
        if any(ord(c) > 127 for c in text):
            # Allow some unicode but flag excessive use
            unicode_ratio = sum(1 for c in text if ord(c) > 127) / max(len(text), 1)
            if unicode_ratio > 0.1:
                issues.append("High unicode character ratio")
        
        return sanitized, issues
    
    def sanitize_context(self, context: Dict) -> Tuple[Dict, List[str]]:
        """
        Sanitize context data before including in prompts.
        
        Returns:
            (sanitized_context, list of detected issues)
        """
        issues = []
        sanitized = {}
        
        for key, value in context.items():
            if isinstance(value, str):
                clean_value, value_issues = self.sanitize_prompt_input(value)
                sanitized[key] = clean_value
                for issue in value_issues:
                    issues.append(f"In field '{key}': {issue}")
            elif isinstance(value, dict):
                clean_value, value_issues = self.sanitize_context(value)
                sanitized[key] = clean_value
                issues.extend(value_issues)
            elif isinstance(value, list):
                sanitized[key] = []
                for item in value:
                    if isinstance(item, str):
                        clean_item, item_issues = self.sanitize_prompt_input(item)
                        sanitized[key].append(clean_item)
                        issues.extend(item_issues)
                    elif isinstance(item, dict):
                        clean_item, item_issues = self.sanitize_context(item)
                        sanitized[key].append(clean_item)
                        issues.extend(item_issues)
                    else:
                        sanitized[key].append(item)
            else:
                sanitized[key] = value
        
        return sanitized, issues
    
    # =========================================================================
    # Output Validation
    # =========================================================================
    
    def validate_ai_response(self, response: Dict) -> Tuple[bool, List[str]]:
        """
        Validate AI response for safety and correctness.
        
        Returns:
            (is_valid, list of validation errors)
        """
        errors = []
        
        # Response must be a dict
        if not isinstance(response, dict):
            return False, ["Response is not a dictionary"]
        
        # Check for required fields based on response type
        if "recommended_actions" in response:
            action_errors = self._validate_recommended_actions(
                response["recommended_actions"]
            )
            errors.extend(action_errors)
        
        if "root_cause" in response:
            cause_errors = self._validate_root_cause(response["root_cause"])
            errors.extend(cause_errors)
        
        # Check for dangerous content in any string field
        dangerous = self._check_dangerous_content(response)
        errors.extend(dangerous)
        
        return len(errors) == 0, errors
    
    def _validate_recommended_actions(self, actions: List) -> List[str]:
        """Validate recommended actions from AI"""
        errors = []
        
        if not isinstance(actions, list):
            return ["recommended_actions must be a list"]
        
        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                errors.append(f"Action {i}: not a dictionary")
                continue
            
            # Check action type is allowed
            action_type = action.get("action", action.get("action_type", ""))
            if action_type:
                # Normalize action type
                normalized = action_type.lower().replace(" ", "_").replace("-", "_")
                
                if normalized not in self.allowed_actions:
                    errors.append(f"Action {i}: '{action_type}' is not an allowed action")
            
            # Validate parameters are within limits
            params = action.get("params", action.get("parameters", {}))
            if isinstance(params, dict):
                param_errors = self._validate_parameters(params, i)
                errors.extend(param_errors)
        
        return errors
    
    def _validate_parameters(self, params: Dict, action_index: int) -> List[str]:
        """Validate action parameters are within safe limits"""
        errors = []
        
        for param_name, (min_val, max_val) in self.parameter_limits.items():
            for key, value in params.items():
                if param_name in key.lower():
                    try:
                        num_value = float(value)
                        if num_value < min_val or num_value > max_val:
                            errors.append(
                                f"Action {action_index}: {key}={value} outside "
                                f"safe range [{min_val}, {max_val}]"
                            )
                    except (ValueError, TypeError):
                        pass
        
        return errors
    
    def _validate_root_cause(self, root_cause: Dict) -> List[str]:
        """Validate root cause analysis from AI"""
        errors = []
        
        if not isinstance(root_cause, dict):
            return ["root_cause must be a dictionary"]
        
        # Check confidence is reasonable
        confidence = root_cause.get("confidence", 50)
        try:
            conf_num = float(confidence)
            if conf_num < 0 or conf_num > 100:
                errors.append(f"Confidence {confidence} outside valid range [0, 100]")
        except (ValueError, TypeError):
            errors.append(f"Invalid confidence value: {confidence}")
        
        return errors
    
    def _check_dangerous_content(self, obj: Any, path: str = "") -> List[str]:
        """Recursively check for dangerous content in response"""
        errors = []
        
        if isinstance(obj, str):
            for pattern in self.dangerous_output_patterns:
                if re.search(pattern, obj, re.IGNORECASE):
                    errors.append(f"Dangerous pattern at {path}: {pattern}")
        elif isinstance(obj, dict):
            for key, value in obj.items():
                errors.extend(self._check_dangerous_content(value, f"{path}.{key}"))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                errors.extend(self._check_dangerous_content(item, f"{path}[{i}]"))
        
        return errors
    
    # =========================================================================
    # Action Verification
    # =========================================================================
    
    def verify_action_safe(
        self,
        action: Dict,
        incident: Dict,
        reasoning: str
    ) -> Tuple[bool, str]:
        """
        Verify that an AI-recommended action is safe to execute.
        
        Returns:
            (is_safe, reason)
        """
        action_type = action.get("action_type", action.get("action", ""))
        
        # Check action is in allowed list
        normalized = action_type.lower().replace(" ", "_").replace("-", "_")
        if normalized not in self.allowed_actions:
            return False, f"Action '{action_type}' is not in allowed list"
        
        # Check risk level
        risk = action.get("risk", "medium")
        if risk == "critical":
            return False, "Critical risk actions require manual approval"
        
        # Check reasoning is present and reasonable
        if not reasoning or len(reasoning) < 20:
            return False, "Insufficient reasoning provided for action"
        
        # Verify action matches incident type
        incident_type = incident.get("type", incident.get("anomaly_type", ""))
        if not self._action_matches_incident(action_type, incident_type):
            return False, f"Action '{action_type}' doesn't match incident type '{incident_type}'"
        
        return True, "Action verified safe"
    
    def _action_matches_incident(self, action_type: str, incident_type: str) -> bool:
        """Check if action is appropriate for incident type"""
        # Define valid action-incident mappings
        valid_mappings = {
            "memory": ["restart_service", "increase_memory", "trigger_gc", "scale_up"],
            "cpu": ["scale_up", "add_replicas", "adjust_timeout"],
            "latency": ["scale_up", "enable_circuit_breaker", "adjust_timeout", "clear_cache"],
            "error_rate": ["rollback", "restart_service", "enable_circuit_breaker"],
            "disk": ["rotate_logs", "clear_cache"],
            "connection": ["flush_connections", "scale_up", "restart_service"],
            "deployment": ["rollback"],
        }
        
        action_normalized = action_type.lower().replace("-", "_")
        incident_lower = incident_type.lower()
        
        for incident_keyword, allowed_actions in valid_mappings.items():
            if incident_keyword in incident_lower:
                if action_normalized in [a.replace("-", "_") for a in allowed_actions]:
                    return True
        
        # Default: allow action if we can't determine incident type
        return True
    
    # =========================================================================
    # Logging & Audit
    # =========================================================================
    
    def log_security_event(
        self,
        event_type: str,
        details: Dict,
        severity: str = "medium"
    ):
        """Log AI security event for audit"""
        event = {
            "type": event_type,
            "severity": severity,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"[AI SECURITY] {event_type}: {json.dumps(details)}")
        
        # Could store in Redis/DB for audit
        return event


# ============================================================================
# Secure LLM Wrapper
# ============================================================================

class SecureLLMWrapper:
    """
    Wrapper around LLM adapter that adds security checks.
    Use this instead of LLMAdapter directly for production.
    """
    
    def __init__(self, llm_adapter, security_guard: AISecurityGuard = None):
        self.llm = llm_adapter
        self.guard = security_guard or AISecurityGuard()
    
    async def analyze(self, prompt: str, context: Dict = None) -> Dict:
        """
        Secure analyze with input sanitization and output validation
        """
        # 1. Sanitize input
        clean_prompt, prompt_issues = self.guard.sanitize_prompt_input(prompt)
        if prompt_issues:
            self.guard.log_security_event("prompt_sanitization", {
                "issues": prompt_issues,
                "original_length": len(prompt)
            })
        
        # 2. Sanitize context
        clean_context = context
        if context:
            clean_context, context_issues = self.guard.sanitize_context(context)
            if context_issues:
                self.guard.log_security_event("context_sanitization", {
                    "issues": context_issues
                })
        
        # 3. Call LLM with sanitized input
        response = await self.llm.analyze(clean_prompt, clean_context)
        
        # 4. Validate output
        is_valid, validation_errors = self.guard.validate_ai_response(response)
        if not is_valid:
            self.guard.log_security_event("invalid_ai_response", {
                "errors": validation_errors
            }, severity="high")
            
            # Return safe fallback
            return {
                "error": "AI response failed validation",
                "validation_errors": validation_errors,
                "fallback": True
            }
        
        return response
    
    def verify_action(
        self,
        action: Dict,
        incident: Dict,
        reasoning: str
    ) -> Tuple[bool, str]:
        """Verify AI-recommended action is safe"""
        return self.guard.verify_action_safe(action, incident, reasoning)


# Global instance
ai_security_guard = AISecurityGuard()


def get_secure_llm_wrapper(llm_adapter) -> SecureLLMWrapper:
    """Get secure wrapper for an LLM adapter"""
    return SecureLLMWrapper(llm_adapter, ai_security_guard)
