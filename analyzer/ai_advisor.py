import requests
import logging
from config import OLLAMA_MODEL, OLLAMA_URL

logger = logging.getLogger(__name__)


def get_advice(report_text):
    """Send the waste report to Ollama and get optimization recommendations."""
    prompt = f"""You are an AWS cost optimization expert. 
Here is a waste report from an AWS account:

{report_text}

Give a clear, ranked action plan:
1. What to delete immediately (no risk)
2. What to review before deleting
3. Estimated monthly savings if all actions taken
4. Any additional recommendations for cost optimization

Keep it short, direct, and actionable. Use bullet points."""

    try:
        logger.info(f"Sending report to Ollama ({OLLAMA_MODEL})...")
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }, timeout=120)

        response.raise_for_status()
        advice = response.json().get("response", "No response from AI.")
        logger.info("AI advice received successfully.")
        return advice

    except requests.exceptions.ConnectionError:
        msg = "❌ Cannot connect to Ollama. Make sure it's running: ollama serve"
        logger.error(msg)
        return msg
    except requests.exceptions.Timeout:
        msg = "❌ Ollama request timed out. The model may be loading — try again."
        logger.error(msg)
        return msg
    except Exception as e:
        msg = f"❌ AI advisor error: {e}"
        logger.error(msg)
        return msg
