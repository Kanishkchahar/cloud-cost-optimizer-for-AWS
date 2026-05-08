import os
import requests
import logging
import time
import re

logger = logging.getLogger(__name__)


def generate_fallback_advice(report_text):
    """Generate rule-based developer advice when AI API fails."""
    advice = ["⚠️ **Note:** AI API offline. Returning local rule heuristics optimized for Developers:\n"]

    actions = []
    
    if "ElasticIP" in report_text:
        actions.append("""
### 🌐 Unattached Elastic IP
- **Dev Analogy:** Open Socket / Dangling Pointer.
- **The Problem:** Allocated IPv4 address without an attachment map.
- **CLI Remediation:** `aws ec2 release-address --allocation-id <ID>`
""")
        
    if "EBS" in report_text and "unattached" in report_text.lower():
        actions.append("""
### 💾 Unattached EBS Volume
- **Dev Analogy:** Memory Leak.
- **The Problem:** Allocated block storage sitting idle.
- **CLI Remediation:** `aws ec2 delete-volume --volume-id <ID>`
""")

    if "EC2" in report_text and "stopped" in report_text.lower():
        actions.append("""
### 🖥️ Stopped EC2 Node
- **Dev Analogy:** Zombie Thread / Dead Code.
- **The Problem:** Stopped compute compute cycles, but underlying EBS charges continue.
- **CLI Remediation:** `aws ec2 terminate-instances --instance-ids <ID>`
""")

    if actions:
        advice.extend(actions)
    else:
        advice.append("- No severe developer waste anomalies mapped.")
        
    return "\n".join(advice)


def get_advice(report_text):
    """Get optimization recommendations using Cloud Groq API or Cloud Gemini API."""
    prompt = f"""You are an AWS Cloud Architect speaking to software developers. 
Analyze the following AWS waste report:

{report_text}

Format your advice strictly for software engineers. For each wasted resource:
- **Resource:** [Type] `ID` (Region: `Region`)
- **Dev Analogy:** Map the cost waste to a programming concept (e.g., memory leak, dangling pointer, zombie thread, dead code).
- **The Problem:** Explain the AWS billing mechanism briefly.
- **CLI Remediation:** Provide the exact `aws ...` CLI command required to clean this up.

Keep sections punchy, technical, and highly actionable."""





    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    # Auto-detect Groq keys mapped incorrectly
    if gemini_key and gemini_key.startswith("gsk_"):
        groq_key = gemini_key

    if groq_key:
        max_retries = 3
        base_delay = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"Generating AI recommendations via Groq (Attempt {attempt + 1})...")
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "You are an AWS cost optimization expert."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.5
                }
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        time.sleep(base_delay ** attempt)
                        continue
                    return generate_fallback_advice(report_text)
                if response.status_code != 200:
                    return generate_fallback_advice(report_text)
                    
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"Groq advice failed: {e}")
                return generate_fallback_advice(report_text)
                
    elif gemini_key:
        max_retries = 3
        base_delay = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"Generating AI recommendations via Gemini (Attempt {attempt + 1})...")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        time.sleep(base_delay ** attempt)
                        continue
                    return generate_fallback_advice(report_text)
                if response.status_code != 200:
                    return generate_fallback_advice(report_text)
                    
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.error(f"Gemini advice failed: {e}")
                return generate_fallback_advice(report_text)

    return generate_fallback_advice(report_text)


def chat_with_ai(user_message, history=None, context_report=None):
    """Chat with AI using either Groq or Gemini APIs depending on setup."""
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if gemini_key and gemini_key.startswith("gsk_"):
        groq_key = gemini_key

    system_directive = "You are a Cloud DevOps Engineer. Explain AWS cost optimization opportunities to developers by mapping them to CS analogies (like dangling pointers, memory leaks). Provide exact AWS CLI commands for all fixes."




    if groq_key:
        messages = [{"role": "system", "content": system_directive}]
        if context_report:
            messages.append({"role": "user", "content": f"Here is the context report:\n\n{context_report}"})
            messages.append({"role": "assistant", "content": "Understood. I will use this data to answer queries."})
        if history:
            for msg in history:
                role = "user" if msg.get("sender") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("message", "")})
        messages.append({"role": "user", "content": user_message})

        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            payload = {"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.7}
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            elif response.status_code == 429:
                return "⚠️ Rate Limit Hit."
            return f"⚠️ Error {response.status_code}"
        except Exception as e:
            return f"⚠️ Error: {str(e)}"

    elif gemini_key:
        messages = []
        if context_report:
            messages.append({"role": "user", "parts": [{"text": f"Context:\n\n{context_report}"}]})
            messages.append({"role": "model", "parts": [{"text": "Understood."}]})
        if history:
            for msg in history:
                role = "user" if msg.get("sender") == "user" else "model"
                messages.append({"role": role, "parts": [{"text": msg.get("message", "")}]})
        messages.append({"role": "user", "parts": [{"text": user_message}]})

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            payload = {"contents": messages, "systemInstruction": {"parts": [{"text": system_directive}]}}
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            elif response.status_code == 429:
                return "⚠️ Rate Limit Hit."
            return f"⚠️ Error {response.status_code}"
        except Exception as e:
            return f"⚠️ Error: {str(e)}"

    return "⚠️ No API credentials found in environment."


