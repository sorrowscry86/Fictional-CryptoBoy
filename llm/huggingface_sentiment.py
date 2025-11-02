"""
Hugging Face Financial Sentiment Model Adapter
VoidCat RDC - CryptoBoy Trading System

Specialized adapter for using fine-tuned financial sentiment models from Hugging Face.
These models are specifically trained on financial news and provide superior accuracy
for crypto/stock sentiment analysis compared to general-purpose LLMs.

Recommended Models:
1. ProsusAI/finbert - 2.4M downloads, 997 likes (BEST OVERALL)
2. yiyanghkust/finbert-tone - 906K downloads, 203 likes
3. mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis - 506K downloads, 420 likes (FASTEST)
"""

import torch
from dotenv import load_dotenv
from transformers import AutoModelForSequenceClassification, AutoTokenizer

load_dotenv()


class HuggingFaceFinancialSentiment:
    """
    Adapter for Hugging Face financial sentiment models.

    These models output:
    - positive (bullish)
    - neutral
    - negative (bearish)

    We convert to -1.0 to +1.0 scale for consistency.
    """

    # Recommended models (in order of preference)
    RECOMMENDED_MODELS = {
        "finbert": "ProsusAI/finbert",  # Best overall, most downloads
        "finbert-tone": "yiyanghkust/finbert-tone",  # Good alternative
        "distilroberta-financial": "mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis",  # Fastest
    }

    def __init__(self, model_name: str = "finbert"):
        """
        Initialize the financial sentiment analyzer.

        Args:
            model_name: Short name or full model path
                       Options: 'finbert', 'finbert-tone', 'distilroberta-financial'
                       Or full HF path like 'ProsusAI/finbert'
        """
        # Resolve model name
        if model_name in self.RECOMMENDED_MODELS:
            self.model_path = self.RECOMMENDED_MODELS[model_name]
        else:
            self.model_path = model_name

        print(f"Loading financial sentiment model: {self.model_path}")
        print("This may take a moment on first run (downloading model)...")

        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)

        # Use GPU if available
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()  # Set to evaluation mode

        # Get label mapping
        self.id2label = self.model.config.id2label

        print(f"✓ Model loaded successfully on {self.device}")
        print(f"  Labels: {list(self.id2label.values())}")

    def analyze_sentiment(self, text: str, return_probabilities: bool = False) -> float:
        """
        Analyze sentiment of financial/crypto news text.

        Args:
            text: News article or text to analyze
            return_probabilities: If True, return dict with all label probabilities

        Returns:
            Sentiment score from -1.0 (bearish) to +1.0 (bullish)
            Or dict with probabilities if return_probabilities=True
        """
        # Tokenize input
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=-1)

        # Get probabilities for each class
        probs = probabilities[0].cpu().numpy()

        # Create probability dict
        prob_dict = {}
        for idx, label in self.id2label.items():
            prob_dict[label.lower()] = float(probs[idx])

        if return_probabilities:
            return prob_dict

        # Convert to -1.0 to +1.0 scale
        # Most models use: negative, neutral, positive
        negative_prob = prob_dict.get("negative", 0.0)
        neutral_prob = prob_dict.get("neutral", 0.0)
        positive_prob = prob_dict.get("positive", 0.0)

        # Calculate weighted score
        # positive = +1.0, neutral = 0.0, negative = -1.0
        score = (positive_prob * 1.0) + (neutral_prob * 0.0) + (negative_prob * -1.0)

        return score

    def analyze_batch(self, texts: list) -> list:
        """
        Analyze sentiment for multiple texts efficiently.

        Args:
            texts: List of news articles or texts

        Returns:
            List of sentiment scores
        """
        scores = []
        for text in texts:
            score = self.analyze_sentiment(text)
            scores.append(score)
        return scores


class UnifiedSentimentAnalyzer:
    """
    Unified sentiment analyzer that can use:
    1. Hugging Face specialized models (RECOMMENDED)
    2. LM Studio
    3. Ollama

    With automatic fallback.
    """

    def __init__(self, prefer_huggingface: bool = True, hf_model: str = "finbert"):
        """
        Initialize unified sentiment analyzer.

        Args:
            prefer_huggingface: Use HF models first (recommended for accuracy)
            hf_model: Which HF model to use ('finbert', 'finbert-tone', or 'distilroberta-financial')
        """
        self.backends = []
        self.active_backend = None

        # Try Hugging Face first
        if prefer_huggingface:
            try:
                hf_analyzer = HuggingFaceFinancialSentiment(hf_model)
                self.backends.append(("Hugging Face", hf_analyzer))
                print("✓ Hugging Face model loaded as primary backend")
            except Exception as e:
                print(f"⚠ Hugging Face model failed to load: {e}")

        # Fallback to LM Studio / Ollama
        try:
            from llm.lmstudio_adapter import UnifiedLLMClient

            llm_client = UnifiedLLMClient()
            self.backends.append(("LLM", llm_client))
            print("✓ LLM backend available as fallback")
        except Exception as e:
            print(f"⚠ LLM backend failed: {e}")

        if not self.backends:
            raise RuntimeError("No sentiment analysis backend available!")

        self.active_backend = self.backends[0]
        print(f"\n🎯 Active backend: {self.active_backend[0]}")

    def analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment using the best available backend.

        Returns:
            Sentiment score from -1.0 to +1.0
        """
        name, backend = self.active_backend

        try:
            if name == "Hugging Face":
                return backend.analyze_sentiment(text)
            else:
                return backend.analyze_sentiment(text) or 0.0
        except Exception as e:
            print(f"Error with {name} backend: {e}")

            # Try fallback
            if len(self.backends) > 1:
                print(f"Falling back to {self.backends[1][0]}...")
                self.active_backend = self.backends[1]
                return self.analyze_sentiment(text)

            return 0.0  # Neutral on complete failure


def test_financial_models():
    """Test the financial sentiment models"""

    print("=" * 80)
    print("Hugging Face Financial Sentiment Model Test")
    print("=" * 80)

    # Test cases
    test_cases = [
        "Bitcoin hits new all-time high as institutional investors continue buying",
        "Major exchange hacked, millions in crypto stolen",
        "SEC approves Bitcoin ETF, marking historic regulatory milestone",
        "Regulatory uncertainty causes Bitcoin to trade sideways",
        "Ethereum upgrade successfully completed, network fees drop 90%",
    ]

    # Test with FinBERT
    print("\n📊 Testing ProsusAI/finbert (Most Downloaded)")
    print("-" * 80)

    try:
        analyzer = HuggingFaceFinancialSentiment("finbert")

        for text in test_cases:
            score = analyzer.analyze_sentiment(text)
            probs = analyzer.analyze_sentiment(text, return_probabilities=True)

            emoji = "🟢" if score > 0.3 else "🔴" if score < -0.3 else "⚪"
            sentiment_label = (
                "BULLISH"
                if score > 0.5
                else (
                    "Somewhat Bullish"
                    if score > 0
                    else "NEUTRAL" if score == 0 else "Somewhat Bearish" if score > -0.5 else "BEARISH"
                )
            )

            print(f"\n{emoji} News: {text[:65]}...")
            print(f"   Score: {score:+.2f} ({sentiment_label})")
            print(
                f"   Breakdown: Pos={probs.get('positive', 0):.2f}, "
                f"Neu={probs.get('neutral', 0):.2f}, "
                f"Neg={probs.get('negative', 0):.2f}"
            )

        print("\n" + "=" * 80)
        print("✓ Test complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nNote: First run will download the model (~440MB)")
        print("Ensure you have transformers and torch installed:")
        print("  pip install transformers torch")


if __name__ == "__main__":
    test_financial_models()
