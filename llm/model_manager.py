"""
LLM Model Manager - Manages Ollama models for sentiment analysis
"""
import os
import logging
import requests
from typing import Dict, List, Optional
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelManager:
    """Manages Ollama LLM models"""

    # Recommended models for financial sentiment analysis
    RECOMMENDED_MODELS = [
        'mistral:7b',           # General purpose, good for sentiment
        'llama2:7b',            # Alternative general purpose
        'neural-chat:7b',       # Fine-tuned for chat/analysis
        'orca-mini:7b',         # Smaller, faster
    ]

    def __init__(self, ollama_host: str = "http://localhost:11434"):
        """
        Initialize the model manager

        Args:
            ollama_host: URL of the Ollama API
        """
        self.ollama_host = ollama_host.rstrip('/')
        self.api_url = f"{self.ollama_host}/api"

        logger.info(f"Initialized ModelManager with host: {self.ollama_host}")

    def check_connectivity(self) -> bool:
        """
        Check if Ollama service is running

        Returns:
            True if service is reachable
        """
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("Ollama service is running")
                return True
            else:
                logger.warning(f"Ollama service returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Cannot connect to Ollama: {e}")
            return False

    def list_models(self) -> List[Dict]:
        """
        List all available models

        Returns:
            List of model information dictionaries
        """
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=10)
            response.raise_for_status()

            data = response.json()
            models = data.get('models', [])

            logger.info(f"Found {len(models)} models")
            return models

        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing models: {e}")
            return []

    def model_exists(self, model_name: str) -> bool:
        """
        Check if a specific model is installed

        Args:
            model_name: Name of the model

        Returns:
            True if model exists
        """
        models = self.list_models()
        for model in models:
            if model.get('name') == model_name:
                return True
        return False

    def pull_model(self, model_name: str, timeout: int = 600) -> bool:
        """
        Download a model from Ollama library

        Args:
            model_name: Name of the model to download
            timeout: Maximum time to wait (seconds)

        Returns:
            True if successful
        """
        if self.model_exists(model_name):
            logger.info(f"Model {model_name} already exists")
            return True

        logger.info(f"Pulling model {model_name}... This may take several minutes")

        try:
            response = requests.post(
                f"{self.api_url}/pull",
                json={"name": model_name},
                stream=True,
                timeout=timeout
            )
            response.raise_for_status()

            # Stream the response to show progress
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        status = data.get('status', '')
                        if 'total' in data and 'completed' in data:
                            progress = (data['completed'] / data['total']) * 100
                            logger.info(f"Progress: {progress:.1f}% - {status}")
                        else:
                            logger.info(f"Status: {status}")
                    except json.JSONDecodeError:
                        continue

            logger.info(f"Successfully pulled model {model_name}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False

    def test_model(self, model_name: str, test_prompt: str = "Hello") -> bool:
        """
        Test if a model is working correctly

        Args:
            model_name: Name of the model
            test_prompt: Test prompt to send

        Returns:
            True if model responds correctly
        """
        try:
            logger.info(f"Testing model {model_name}...")

            response = requests.post(
                f"{self.api_url}/generate",
                json={
                    "model": model_name,
                    "prompt": test_prompt,
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            if 'response' in data and data['response']:
                logger.info(f"Model {model_name} is working correctly")
                logger.debug(f"Test response: {data['response'][:100]}")
                return True
            else:
                logger.warning(f"Model {model_name} returned empty response")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error testing model {model_name}: {e}")
            return False

    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """
        Get detailed information about a model

        Args:
            model_name: Name of the model

        Returns:
            Dictionary with model information
        """
        try:
            response = requests.post(
                f"{self.api_url}/show",
                json={"name": model_name},
                timeout=10
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting model info for {model_name}: {e}")
            return None

    def ensure_model_available(
        self,
        model_name: Optional[str] = None,
        fallback_models: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Ensure a model is available, with fallback options

        Args:
            model_name: Preferred model name
            fallback_models: List of fallback models to try

        Returns:
            Name of available model, or None if none available
        """
        if not self.check_connectivity():
            logger.error("Ollama service is not running")
            return None

        # Try preferred model
        if model_name:
            if self.model_exists(model_name):
                logger.info(f"Using existing model: {model_name}")
                return model_name

            logger.info(f"Attempting to pull preferred model: {model_name}")
            if self.pull_model(model_name):
                if self.test_model(model_name):
                    return model_name

        # Try fallback models
        if fallback_models is None:
            fallback_models = self.RECOMMENDED_MODELS

        for fallback in fallback_models:
            logger.info(f"Trying fallback model: {fallback}")

            if self.model_exists(fallback):
                if self.test_model(fallback):
                    logger.info(f"Using existing fallback model: {fallback}")
                    return fallback
            else:
                if self.pull_model(fallback):
                    if self.test_model(fallback):
                        logger.info(f"Successfully pulled and tested: {fallback}")
                        return fallback

        logger.error("No models available")
        return None

    def delete_model(self, model_name: str) -> bool:
        """
        Delete a model from local storage

        Args:
            model_name: Name of the model to delete

        Returns:
            True if successful
        """
        try:
            response = requests.delete(
                f"{self.api_url}/delete",
                json={"name": model_name},
                timeout=30
            )
            response.raise_for_status()

            logger.info(f"Successfully deleted model {model_name}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting model {model_name}: {e}")
            return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    manager = ModelManager(ollama_host)

    # Check connectivity
    if manager.check_connectivity():
        # List existing models
        models = manager.list_models()
        print(f"\nInstalled models: {len(models)}")
        for model in models:
            print(f"  - {model.get('name')} ({model.get('size', 0) / 1e9:.2f} GB)")

        # Ensure a model is available
        model_name = os.getenv('OLLAMA_MODEL', 'mistral:7b')
        available_model = manager.ensure_model_available(model_name)

        if available_model:
            print(f"\nModel ready for use: {available_model}")

            # Get model info
            info = manager.get_model_info(available_model)
            if info:
                print(f"Model details: {json.dumps(info, indent=2)[:500]}")
        else:
            print("\nNo model available. Please check Ollama installation.")
    else:
        print("\nOllama service is not running. Please start it with:")
        print("docker-compose up -d")
