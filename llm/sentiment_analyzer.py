"""
Sentiment Analyzer - Uses LLM for crypto news sentiment analysis
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyzes sentiment of crypto news using LLM"""

    SENTIMENT_PROMPT_TEMPLATE = (
        "You are a cryptocurrency market sentiment analyzer. "
        "Analyze the following news headline and return ONLY a single number "
        "between -1.0 and 1.0 representing the sentiment:\n\n"
        "-1.0 = Very bearish (extremely negative for crypto prices)\n"
        "-0.5 = Bearish (negative)\n"
        " 0.0 = Neutral\n"
        " 0.5 = Bullish (positive)\n"
        " 1.0 = Very bullish (extremely positive for crypto prices)\n\n"
        "Consider factors like: regulation, adoption, technology, market sentiment, "
        "institutional involvement, security issues.\n\n"
        'Headline: "{headline}"\n\n'
        "Return only the number, no explanation:"
    )

    def __init__(
        self,
        model_name: str = "mistral:7b",
        ollama_host: str = "http://localhost:11434",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the sentiment analyzer

        Args:
            model_name: Name of the Ollama model to use
            ollama_host: URL of the Ollama API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries on failure
        """
        self.model_name = model_name
        self.ollama_host = ollama_host.rstrip("/")
        self.api_url = f"{self.ollama_host}/api"
        self.timeout = timeout
        self.max_retries = max_retries

        logger.info(f"Initialized SentimentAnalyzer with model: {model_name}")

    def _parse_sentiment_score(self, response_text: str) -> Optional[float]:
        """
        Parse sentiment score from LLM response

        Args:
            response_text: Raw response from LLM

        Returns:
            Sentiment score between -1.0 and 1.0, or None if invalid
        """
        # Try to extract a number from the response
        text = response_text.strip()

        # Remove common prefixes
        for prefix in ["score:", "sentiment:", "answer:"]:
            if text.lower().startswith(prefix):
                text = text[len(prefix):].strip()

        # Try to parse as float
        try:
            score = float(text.split()[0])  # Take first token
            # Clamp to [-1.0, 1.0]
            score = max(-1.0, min(1.0, score))
            return score
        except (ValueError, IndexError):
            logger.warning(f"Could not parse sentiment score from: {response_text[:100]}")
            return None

    def get_sentiment_score(self, headline: str, context: str = "") -> float:
        """
        Get sentiment score for a single headline

        Args:
            headline: News headline to analyze
            context: Additional context (optional)

        Returns:
            Sentiment score between -1.0 and 1.0 (0.0 on error)
        """
        if not headline or not headline.strip():
            logger.warning("Empty headline provided")
            return 0.0

        # Prepare prompt
        if context:
            full_headline = f"{headline}\nContext: {context}"
        else:
            full_headline = headline

        prompt = self.SENTIMENT_PROMPT_TEMPLATE.format(headline=full_headline)

        # Try with retries
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.api_url}/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,  # Lower temperature for more consistent results
                            "num_predict": 10,  # Short response expected
                        },
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()
                response_text = data.get("response", "")

                # Parse the score
                score = self._parse_sentiment_score(response_text)

                if score is not None:
                    logger.debug(f"Sentiment for '{headline[:50]}...': {score}")
                    return score
                else:
                    logger.warning(f"Invalid response, retrying... (attempt {attempt + 1})")

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                break

        # Return neutral on failure
        logger.warning(f"Failed to get sentiment for: {headline[:50]}... Returning neutral (0.0)")
        return 0.0

    def batch_sentiment_analysis(
        self, headlines: List[Union[str, Dict]], max_workers: int = 4, show_progress: bool = True
    ) -> List[Dict]:
        """
        Analyze sentiment for multiple headlines in parallel

        Args:
            headlines: List of headlines (str) or dicts with 'headline' key
            max_workers: Number of parallel workers
            show_progress: Whether to show progress logs

        Returns:
            List of dictionaries with headline and sentiment score
        """
        results = []

        def process_headline(item):
            if isinstance(item, dict):
                headline = item.get("headline", "")
                context = item.get("context", "")
                metadata = {k: v for k, v in item.items() if k not in ["headline", "context"]}
            else:
                headline = str(item)
                context = ""
                metadata = {}

            score = self.get_sentiment_score(headline, context)

            return {"headline": headline, "sentiment_score": score, **metadata}

        total = len(headlines)
        logger.info(f"Starting batch sentiment analysis for {total} headlines with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_headline, h): i for i, h in enumerate(headlines)}

            for i, future in enumerate(as_completed(futures)):
                try:
                    result = future.result()
                    results.append(result)

                    if show_progress and (i + 1) % 10 == 0:
                        logger.info(f"Progress: {i + 1}/{total} headlines processed")

                except Exception as e:
                    logger.error(f"Error processing headline: {e}")
                    # Add a failed result
                    idx = futures[future]
                    headline = headlines[idx]
                    if isinstance(headline, dict):
                        headline = headline.get("headline", "")
                    results.append({"headline": str(headline), "sentiment_score": 0.0, "error": str(e)})

        logger.info(f"Completed batch analysis: {len(results)}/{total} headlines")
        return results

    def analyze_dataframe(
        self, df: pd.DataFrame, headline_col: str = "headline", timestamp_col: str = "timestamp", max_workers: int = 4
    ) -> pd.DataFrame:
        """
        Analyze sentiment for headlines in a DataFrame

        Args:
            df: DataFrame with headlines
            headline_col: Name of the headline column
            timestamp_col: Name of the timestamp column
            max_workers: Number of parallel workers

        Returns:
            DataFrame with added sentiment_score column
        """
        if df.empty:
            logger.warning("Empty DataFrame provided")
            return df

        if headline_col not in df.columns:
            logger.error(f"Column '{headline_col}' not found in DataFrame")
            return df

        # Prepare headlines for batch processing
        headlines = []
        for idx, row in df.iterrows():
            item = {"headline": row[headline_col]}
            if timestamp_col in df.columns:
                item["timestamp"] = row[timestamp_col]
            item["original_index"] = idx
            headlines.append(item)

        # Process in batch
        results = self.batch_sentiment_analysis(headlines, max_workers=max_workers)

        # Merge back to original DataFrame
        df_with_sentiment = df.copy()
        df_with_sentiment["sentiment_score"] = 0.0

        for result in results:
            idx = result.get("original_index")
            if idx is not None and idx in df_with_sentiment.index:
                df_with_sentiment.at[idx, "sentiment_score"] = result["sentiment_score"]

        logger.info(f"Added sentiment scores to {len(df_with_sentiment)} rows")
        return df_with_sentiment

    def save_sentiment_scores(
        self, df: pd.DataFrame, output_file: str, timestamp_col: str = "timestamp", score_col: str = "sentiment_score"
    ):
        """
        Save sentiment scores to CSV

        Args:
            df: DataFrame with sentiment scores
            output_file: Output file path
            timestamp_col: Name of timestamp column
            score_col: Name of sentiment score column
        """
        if df.empty:
            logger.warning("Cannot save empty DataFrame")
            return

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Select relevant columns
        cols_to_save = [timestamp_col, score_col]
        if "headline" in df.columns:
            cols_to_save.insert(1, "headline")
        if "source" in df.columns:
            cols_to_save.append("source")

        df_to_save = df[cols_to_save].copy()
        df_to_save.to_csv(output_path, index=False)

        logger.info(f"Saved sentiment scores to {output_path}")

    def test_connection(self) -> bool:
        """
        Test connection to Ollama service

        Returns:
            True if connection is successful
        """
        try:
            test_score = self.get_sentiment_score("Bitcoin price rises sharply")
            if test_score != 0.0 or test_score is not None:
                logger.info("Sentiment analyzer connection test successful")
                return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
        return False


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # Initialize
    model_name = os.getenv("OLLAMA_MODEL", "mistral:7b")
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    analyzer = SentimentAnalyzer(model_name=model_name, ollama_host=ollama_host)

    # Test connection
    if analyzer.test_connection():
        # Test with sample headlines
        test_headlines = [
            "Bitcoin breaks all-time high as institutional adoption grows",
            "Major exchange hacked, millions of dollars stolen",
            "SEC approves Bitcoin ETF application",
            "China bans cryptocurrency mining operations",
            "Ethereum successfully completes major network upgrade",
        ]

        print("\nAnalyzing sample headlines:")
        print("-" * 80)

        results = analyzer.batch_sentiment_analysis(test_headlines, max_workers=2)

        for result in results:
            score = result["sentiment_score"]
            headline = result["headline"]
            sentiment_label = "BULLISH" if score > 0.3 else "BEARISH" if score < -0.3 else "NEUTRAL"
            print(f"\nScore: {score:+.2f} ({sentiment_label})")
            print(f"Headline: {headline}")

        print("\n" + "-" * 80)
        print(f"Average sentiment: {sum(r['sentiment_score'] for r in results) / len(results):+.2f}")
    else:
        print("\nCould not connect to Ollama. Please ensure:")
        print("1. Docker is running")
        print("2. Ollama container is started: docker-compose up -d")
        print("3. Model is downloaded (run llm/model_manager.py first)")
