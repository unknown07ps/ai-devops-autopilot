"""
LLM Adapter - Provider-agnostic interface for LLM calls
Supports: Ollama (local), Claude (Anthropic), OpenAI
Your training intelligence stays in YOUR database - LLM is just a tool
"""

import httpx
import json
import os
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from enum import Enum


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    CLAUDE = "claude"
    OPENAI = "openai"


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def analyze(self, prompt: str, context: Dict = None) -> Dict:
        """Send prompt to LLM and get structured response"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is available"""
        pass


class OllamaProvider(BaseLLMProvider):
    """Ollama (local) LLM provider"""
    
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def analyze(self, prompt: str, context: Dict = None) -> Dict:
        """Send prompt to Ollama"""
        try:
            full_prompt = self._build_prompt(prompt, context)
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 2000
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_response(result.get("response", ""))
            else:
                return {"error": f"Ollama returned {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e), "provider": "ollama"}
    
    async def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except (httpx.RequestError, httpx.TimeoutException):
            return False
    
    def _build_prompt(self, prompt: str, context: Dict = None) -> str:
        """Build full prompt with context"""
        if context:
            context_str = json.dumps(context, indent=2)
            return f"Context:\n{context_str}\n\n{prompt}"
        return prompt
    
    def _parse_response(self, text: str) -> Dict:
        """Extract JSON from LLM response"""
        try:
            # Try to find JSON in response
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
            return {"raw_response": text}
        except json.JSONDecodeError:
            return {"raw_response": text}


class ClaudeProvider(BaseLLMProvider):
    """Claude (Anthropic) LLM provider"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229")
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def analyze(self, prompt: str, context: Dict = None) -> Dict:
        """Send prompt to Claude"""
        if not self.api_key:
            return {"error": "ANTHROPIC_API_KEY not configured"}
        
        try:
            full_prompt = self._build_prompt(prompt, context)
            
            response = await self.client.post(
                self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 2000,
                    "messages": [
                        {"role": "user", "content": full_prompt}
                    ]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("content", [{}])[0].get("text", "")
                return self._parse_response(content)
            else:
                return {"error": f"Claude returned {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e), "provider": "claude"}
    
    async def is_available(self) -> bool:
        """Check if Claude API is configured"""
        return bool(self.api_key)
    
    def _build_prompt(self, prompt: str, context: Dict = None) -> str:
        if context:
            context_str = json.dumps(context, indent=2)
            return f"Context:\n{context_str}\n\n{prompt}\n\nRespond with valid JSON only."
        return f"{prompt}\n\nRespond with valid JSON only."
    
    def _parse_response(self, text: str) -> Dict:
        """Extract JSON from Claude response"""
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
            return {"raw_response": text}
        except json.JSONDecodeError:
            return {"raw_response": text}


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def analyze(self, prompt: str, context: Dict = None) -> Dict:
        """Send prompt to OpenAI"""
        if not self.api_key:
            return {"error": "OPENAI_API_KEY not configured"}
        
        try:
            full_prompt = self._build_prompt(prompt, context)
            
            response = await self.client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a DevOps expert. Always respond with valid JSON."},
                        {"role": "user", "content": full_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return self._parse_response(content)
            else:
                return {"error": f"OpenAI returned {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e), "provider": "openai"}
    
    async def is_available(self) -> bool:
        """Check if OpenAI API is configured"""
        return bool(self.api_key)
    
    def _build_prompt(self, prompt: str, context: Dict = None) -> str:
        if context:
            context_str = json.dumps(context, indent=2)
            return f"Context:\n{context_str}\n\n{prompt}"
        return prompt
    
    def _parse_response(self, text: str) -> Dict:
        """Extract JSON from OpenAI response"""
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
            return {"raw_response": text}
        except json.JSONDecodeError:
            return {"raw_response": text}


class LLMAdapter:
    """
    Provider-agnostic LLM adapter with automatic fallback
    
    Usage:
        adapter = LLMAdapter(provider="ollama")  # or "claude", "openai"
        result = await adapter.analyze_incident(anomalies, logs)
        
        # Switch provider anytime:
        adapter.set_provider("claude")
    """
    
    def __init__(self, provider: str = "ollama", fallback_providers: List[str] = None):
        self.provider_name = provider
        self.fallback_providers = fallback_providers or ["ollama"]
        self.providers = {
            "ollama": OllamaProvider(),
            "claude": ClaudeProvider(),
            "openai": OpenAIProvider()
        }
        self.current_provider = self.providers.get(provider, self.providers["ollama"])
    
    def set_provider(self, provider: str):
        """Switch LLM provider at runtime"""
        if provider in self.providers:
            self.provider_name = provider
            self.current_provider = self.providers[provider]
    
    async def analyze(self, prompt: str, context: Dict = None) -> Dict:
        """
        Send analysis request to LLM with automatic fallback
        Your intelligence is in context (from YOUR database), not in the LLM
        """
        # Try primary provider
        result = await self.current_provider.analyze(prompt, context)
        
        if "error" not in result:
            return result
        
        # Try fallback providers
        for fallback_name in self.fallback_providers:
            if fallback_name != self.provider_name:
                fallback = self.providers.get(fallback_name)
                if fallback and await fallback.is_available():
                    result = await fallback.analyze(prompt, context)
                    if "error" not in result:
                        result["_used_fallback"] = fallback_name
                        return result
        
        return result
    
    async def analyze_incident(
        self,
        anomalies: List[Dict],
        logs: List[Dict] = None,
        deployments: List[Dict] = None,
        service: str = "unknown",
        similar_incidents: List[Dict] = None
    ) -> Dict:
        """
        Analyze incident with full context from YOUR knowledge base
        
        Args:
            anomalies: Detected anomalies
            logs: Recent error logs
            deployments: Recent deployments
            service: Service name
            similar_incidents: Similar past incidents from YOUR database
        """
        
        # Build context from YOUR database (this is where intelligence lives)
        context = {
            "service": service,
            "anomalies": anomalies[:10] if anomalies else [],
            "recent_logs": logs[:20] if logs else [],
            "recent_deployments": deployments[:5] if deployments else [],
            "similar_past_incidents": similar_incidents[:5] if similar_incidents else []
        }
        
        prompt = """Analyze this DevOps incident and provide root cause analysis.

Based on the anomalies, logs, and similar past incidents provided, determine:
1. Most likely root cause
2. Confidence level (0-100)
3. Recommended actions in priority order
4. Blast radius (low/medium/high)
5. Whether this can be auto-remediated safely

Respond with this JSON structure:
{
    "root_cause": "description of root cause",
    "confidence": 85,
    "category": "memory|cpu|network|database|deployment|application",
    "subcategory": "more specific category",
    "recommended_actions": [
        {"action": "action_name", "priority": 1, "confidence": 90, "params": {}},
        {"action": "action_name2", "priority": 2, "confidence": 75, "params": {}}
    ],
    "blast_radius": "low|medium|high",
    "auto_remediate_safe": true,
    "reasoning": "explanation of analysis",
    "contributing_factors": ["factor1", "factor2"]
}"""
        
        return await self.analyze(prompt, context)
    
    async def suggest_actions(
        self,
        incident: Dict,
        available_actions: List[str],
        past_success_rates: Dict[str, float]
    ) -> List[Dict]:
        """
        Get action suggestions with confidence scores
        
        Args:
            incident: Current incident details
            available_actions: List of available action types
            past_success_rates: Success rates from YOUR learning database
        """
        
        context = {
            "incident": incident,
            "available_actions": available_actions,
            "historical_success_rates": past_success_rates
        }
        
        prompt = """Based on the incident and historical success rates from our database,
rank the available actions by effectiveness.

Respond with JSON:
{
    "ranked_actions": [
        {"action": "action_name", "confidence": 95, "reason": "why this action"},
        {"action": "action_name2", "confidence": 80, "reason": "why this action"}
    ],
    "reasoning": "overall analysis"
}"""
        
        result = await self.analyze(prompt, context)
        return result.get("ranked_actions", [])
    
    async def get_provider_status(self) -> Dict:
        """Get status of all configured LLM providers"""
        status = {}
        for name, provider in self.providers.items():
            status[name] = {
                "available": await provider.is_available(),
                "is_current": name == self.provider_name
            }
        return status


# Singleton instance for easy import
_adapter_instance = None

def get_llm_adapter(provider: str = None) -> LLMAdapter:
    """Get or create LLM adapter singleton"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = LLMAdapter(
            provider=provider or os.getenv("LLM_PROVIDER", "ollama")
        )
    elif provider and provider != _adapter_instance.provider_name:
        _adapter_instance.set_provider(provider)
    return _adapter_instance
