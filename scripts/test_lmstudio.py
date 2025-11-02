"""
Quick test script for LM Studio sentiment analysis
VoidCat RDC - CryptoBoy Trading System
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from llm.lmstudio_adapter import LMStudioAdapter  # noqa: E402


def test_lmstudio_sentiment():
    """Test LM Studio with current loaded model"""

    # Initialize adapter
    adapter = LMStudioAdapter(host="http://localhost:1234", model="qwen3-4b-thinking-2507@q8_0")

    # Test cases
    test_cases = [
        "Bitcoin hits new all-time high as institutional investors continue buying",
        "Major exchange hacked, millions in crypto stolen",
        "SEC approves Bitcoin ETF, marking historic regulatory milestone",
        "Regulatory uncertainty causes Bitcoin to trade sideways",
    ]

    print("=" * 80)
    print("LM Studio Sentiment Analysis Test")
    print(f"Model: {adapter.model}")
    print(f"Host: {adapter.host}")
    print("=" * 80)

    # Check connection
    if not adapter.check_connection():
        print("\n❌ LM Studio is not running or not accessible")
        print(f"   Make sure LM Studio is running on {adapter.host}")
        return

    print("\n✓ LM Studio connection verified")

    # Test each case
    for text in test_cases:
        print(f"\n📰 News: {text[:70]}...")
        print("   Analyzing...", end=" ", flush=True)

        sentiment = adapter.analyze_sentiment(text)

        if sentiment is not None:
            emoji = "🟢" if sentiment > 0.3 else "🔴" if sentiment < -0.3 else "⚪"
            sentiment_label = (
                "BULLISH"
                if sentiment > 0.5
                else (
                    "Somewhat Bullish"
                    if sentiment > 0
                    else "NEUTRAL" if sentiment == 0 else "Somewhat Bearish" if sentiment > -0.5 else "BEARISH"
                )
            )
            print(f"{emoji} Score: {sentiment:+.2f} ({sentiment_label})")
        else:
            print("❌ Failed to analyze")

    print("\n" + "=" * 80)
    print("✓ Test complete!")


if __name__ == "__main__":
    test_lmstudio_sentiment()
