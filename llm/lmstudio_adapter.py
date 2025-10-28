"""
LM Studio API Adapter for CryptoBoy Trading Bot
VoidCat RDC - Production Grade LLM Integration

This adapter enables seamless switching between Ollama and LM Studio
for sentiment analysis operations.
"""

import os
import requests
import json
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class LMStudioAdapter:
    """
    Adapter for LM Studio's OpenAI-compatible API.
    
    LM Studio runs a local server (default: http://localhost:1234)
    that implements OpenAI's chat completions API format.
    """
    
    def __init__(
        self,
        host: str = None,
        model: str = None,
        timeout: int = 30
    ):
        """
        Initialize LM Studio adapter.
        
        Args:
            host: LM Studio server URL (default: from env or localhost:1234)
            model: Model identifier (default: from env or first available)
            timeout: Request timeout in seconds
        """
        self.host = host or os.getenv("LMSTUDIO_HOST", "http://localhost:1234")
        self.model = model or os.getenv("LMSTUDIO_MODEL", "mistral-7b-instruct")
        self.timeout = timeout
        self.base_url = f"{self.host}/v1"
        
    def check_connection(self) -> bool:
        """Verify LM Studio server is running and accessible."""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def list_models(self) -> list:
        """Get list of loaded models from LM Studio."""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return [model["id"] for model in data.get("data", [])]
        except requests.exceptions.RequestException as e:
            print(f"Error listing models: {e}")
            return []
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Generate text using LM Studio's chat completions endpoint.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system instruction
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text or None on error
        """
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
            
        except requests.exceptions.RequestException as e:
            print(f"LM Studio API error: {e}")
            return None
    
    def analyze_sentiment(
        self,
        text: str,
        context: Optional[str] = None
    ) -> Optional[float]:
        """
        Analyze sentiment of cryptocurrency news/text.
        
        Args:
            text: News article or text to analyze
            context: Optional additional context
            
        Returns:
            Sentiment score from -1.0 (bearish) to +1.0 (bullish)
        """
        system_prompt = """You are a cryptocurrency market sentiment analyzer.
Analyze the provided text and determine the market sentiment.

Score range:
-1.0 = Extremely bearish (strong sell signal)
-0.5 = Bearish (caution)
 0.0 = Neutral (no clear direction)
+0.5 = Bullish (positive)
+1.0 = Extremely bullish (strong buy signal)

Consider: price predictions, regulatory news, adoption metrics, technical developments, 
market fear/greed, institutional moves, and overall tone.

Think through your analysis, then provide your final score at the end."""

        user_prompt = f"Analyze this crypto news:\n\n{text}"
        if context:
            user_prompt += f"\n\nAdditional context: {context}"
        user_prompt += "\n\nProvide your sentiment analysis and end with: Final score: [number]"
        
        response = self.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temp for more consistent scoring
            max_tokens=500  # Increased for thinking models
        )
        
        if not response:
            return None
        
        try:
            # Try to extract numeric value from response
            import re
            
            # Look for "Final score: X.X" pattern first
            final_score_match = re.search(r'[Ff]inal\s+score:\s*(-?\d+\.?\d*)', response)
            if final_score_match:
                score = float(final_score_match.group(1))
                return max(-1.0, min(1.0, score))
            
            # Look for standalone numbers in the last line
            lines = response.strip().split('\n')
            for line in reversed(lines):
                numbers = re.findall(r'(-?\d+\.?\d+)', line)
                if numbers:
                    score = float(numbers[-1])
                    if -1.0 <= score <= 1.0:
                        return score
            
            # Fallback: find any number in valid range
            all_numbers = re.findall(r'-?\d+\.?\d*', response)
            for num_str in reversed(all_numbers):
                score = float(num_str)
                if -1.0 <= score <= 1.0:
                    return score
            
            print(f"Could not extract valid sentiment score from: {response[:200]}")
            return None
            
        except (ValueError, AttributeError) as e:
            print(f"Failed to parse sentiment score: {e}")
            print(f"Response: {response[:200]}")
            return None


class UnifiedLLMClient:
    """
    Unified client that can use either Ollama or LM Studio.
    Automatically falls back if primary service is unavailable.
    """
    
    def __init__(self, prefer_lmstudio: bool = True):
        """
        Initialize unified LLM client.
        
        Args:
            prefer_lmstudio: If True, try LM Studio first, then Ollama.
                           If False, try Ollama first, then LM Studio.
        """
        self.prefer_lmstudio = prefer_lmstudio
        self.lmstudio = None
        self.ollama = None
        self.active_backend = None
        
        # Initialize both backends
        try:
            self.lmstudio = LMStudioAdapter()
        except Exception as e:
            print(f"LM Studio initialization failed: {e}")
        
        try:
            from llm.model_manager import OllamaManager
            self.ollama = OllamaManager()
        except Exception as e:
            print(f"Ollama initialization failed: {e}")
        
        # Determine active backend
        self._select_backend()
    
    def _select_backend(self):
        """Select the active LLM backend based on availability."""
        backends = []
        
        if self.prefer_lmstudio:
            backends = [
                ("LM Studio", self.lmstudio, lambda: self.lmstudio.check_connection()),
                ("Ollama", self.ollama, lambda: hasattr(self.ollama, 'client'))
            ]
        else:
            backends = [
                ("Ollama", self.ollama, lambda: hasattr(self.ollama, 'client')),
                ("LM Studio", self.lmstudio, lambda: self.lmstudio.check_connection())
            ]
        
        for name, backend, check_func in backends:
            if backend and check_func():
                self.active_backend = (name, backend)
                print(f"✓ Using {name} as LLM backend")
                return
        
        raise RuntimeError("No LLM backend available. Please start Ollama or LM Studio.")
    
    def analyze_sentiment(self, text: str, context: Optional[str] = None) -> Optional[float]:
        """Analyze sentiment using the active backend."""
        if not self.active_backend:
            raise RuntimeError("No active LLM backend")
        
        name, backend = self.active_backend
        
        if name == "LM Studio":
            return backend.analyze_sentiment(text, context)
        else:
            # Use existing Ollama sentiment analyzer
            from llm.sentiment_analyzer import analyze_sentiment
            return analyze_sentiment(text)


# Quick test function
def test_lmstudio():
    """Test LM Studio connection and sentiment analysis."""
    print("Testing LM Studio Adapter...")
    print("=" * 60)
    
    adapter = LMStudioAdapter()
    
    # Test connection
    print("\n1. Testing connection...")
    if adapter.check_connection():
        print("✓ LM Studio is running")
    else:
        print("✗ LM Studio is not accessible")
        print(f"  Make sure LM Studio is running on {adapter.host}")
        return
    
    # List models
    print("\n2. Available models:")
    models = adapter.list_models()
    if models:
        for model in models:
            print(f"  - {model}")
    else:
        print("  No models loaded")
        print("  Load a model in LM Studio first")
        return
    
    # Test sentiment analysis
    print("\n3. Testing sentiment analysis...")
    test_texts = [
        "Bitcoin hits new all-time high as institutions continue buying",
        "Major exchange hacked, millions in crypto stolen",
        "SEC approves Bitcoin ETF, marking historic regulatory milestone"
    ]
    
    for text in test_texts:
        sentiment = adapter.analyze_sentiment(text)
        if sentiment is not None:
            emoji = "🟢" if sentiment > 0 else "🔴" if sentiment < 0 else "⚪"
            print(f"\n  {emoji} Text: {text[:50]}...")
            print(f"     Score: {sentiment:+.2f}")
        else:
            print(f"\n  ✗ Failed to analyze: {text[:50]}...")
    
    print("\n" + "=" * 60)
    print("Test complete!")


if __name__ == "__main__":
    test_lmstudio()
