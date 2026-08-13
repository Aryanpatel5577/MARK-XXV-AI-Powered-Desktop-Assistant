import base64
import json
import logging
from pathlib import Path
import sys
import time
from typing import Optional

import requests

# Set up simple logging for console messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openrouter_client")


# ==========================================
# FILE PATH & CONFIGURATION HELPERS
# ==========================================

def get_base_directory() -> Path:
    """Returns the base folder directory whether running as a script or compiled exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR = get_base_directory()
API_KEY_PATH = BASE_DIR / "config" / "api_keys.json"


def load_api_key() -> str:
    """Loads the OpenRouter API key from the json config file."""
    try:
        with open(API_KEY_PATH, "r", encoding="utf-8") as file:
            config_data = json.load(file)

        api_key = config_data.get("openrouter_api_key", "").strip()
        if not api_key:
            raise ValueError("openrouter_api_key is empty in api_keys.json")

        return api_key

    except FileNotFoundError:
        raise RuntimeError(f"api_keys.json not found at: {API_KEY_PATH}")
    except Exception as error:
        raise RuntimeError(f"Failed to load OpenRouter API key: {error}")


# ==========================================
# MODEL LISTS AND API CONSTANTS
# ==========================================

TEXT_MODELS: list[str] = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "minimax/minimax-m2.5:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "qwen/qwen3-coder:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-3-27b-it:free",
    "arcee-ai/trinity-large-preview:free",
    "z-ai/glm-4.5-air:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "google/gemma-3-12b-it:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-3-4b-it:free",
    "google/gemma-3n-e4b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-3n-e2b-it:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
    "liquid/lfm-2.5-1.2b-thinking:free",
]

VISION_MODELS: list[str] = [
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/llama-nemotron-embed-vl-1b-v2:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-3n-e4b-it:free",
    "google/gemma-3n-e2b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7
REQUEST_TIMEOUT = 60          # Timeout per request in seconds
MAX_RETRIES_PER_MODEL = 2     # Attempts per model before moving to fallback
RETRY_DELAY = 2               # Seconds to wait between retries
RATE_LIMIT_COOLDOWN = 60      # Cooldown time in seconds for rate-limited models

# Global dictionary to track rate-limited models with timestamps
rate_limited_models: dict[str, float] = {}


# ==========================================
# OPENROUTER CLIENT CLASS
# ==========================================

class OpenRouterClient:
    """Handles communications with OpenRouter API with fallback support."""

    def __init__(self) -> None:
        self.api_key = load_api_key()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/mark-xxv",
            "X-Title": "MARK XXV",
        }

    def is_rate_limited(self, model_name: str) -> bool:
        """Checks if a model is currently cooling down from a rate limit."""
        last_limited_time = rate_limited_models.get(model_name)
        if last_limited_time is None:
            return False

        # If cooldown time has passed, remove from dictionary
        if time.time() - last_limited_time > RATE_LIMIT_COOLDOWN:
            del rate_limited_models[model_name]
            return False

        return True

    def mark_rate_limited(self, model_name: str) -> None:
        """Marks a model as rate-limited and records current timestamp."""
        rate_limited_models[model_name] = time.time()
        logger.warning(
            f"[OpenRouter] Rate limited: {model_name} — "
            f"cooling down for {RATE_LIMIT_COOLDOWN}s"
        )

    def execute_request(
        self,
        model_name: str,
        messages: list[dict],
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        """Makes a single HTTP POST request to OpenRouter API with retry logic."""
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
            try:
                response = requests.post(
                    API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )

                # HTTP 429 = Too Many Requests (Rate Limited)
                if response.status_code == 429:
                    self.mark_rate_limited(model_name)
                    return None

                # HTTP 200 = Success
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        return content.strip() if content else None
                    return None

                logger.warning(
                    f"[OpenRouter] {model_name} → HTTP {response.status_code} "
                    f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
                )

            except requests.exceptions.Timeout:
                logger.warning(
                    f"[OpenRouter] {model_name} → Timeout "
                    f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
                )
            except Exception as error:
                logger.error(f"[OpenRouter] {model_name} → Unexpected error: {error}")

            # Wait before retry
            if attempt < MAX_RETRIES_PER_MODEL:
                time.sleep(RETRY_DELAY)

        return None

    def execute_with_fallback(
        self,
        model_pool: list[str],
        messages: list[dict],
        requested_model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: Optional[dict] = None,
    ) -> str:
        """Tries the requested model first. If it fails, loops through available fallback models."""

        # 1. Try requested model first if provided
        if requested_model and not self.is_rate_limited(requested_model):
            result = self.execute_request(
                requested_model, messages, max_tokens, temperature, response_format
            )
            if result:
                return result
            logger.info(
                f"[OpenRouter] Requested model failed, "
                f"falling back to pool: {requested_model}"
            )

        # 2. Loop through fallback model pool
        for model in model_pool:
            if self.is_rate_limited(model):
                continue

            logger.info(f"[OpenRouter] Trying: {model}")
            result = self.execute_request(
                model, messages, max_tokens, temperature, response_format
            )
            if result:
                logger.info(f"[OpenRouter] ✓ Success: {model}")
                return result

        # 3. If everything failed
        raise RuntimeError(
            "[OpenRouter] All models failed or are rate-limited. "
            "Check your API key and network connection."
        )

    # ------------------------------------------
    # PUBLIC CHAT AND VISION METHODS
    # ------------------------------------------

    def chat(
        self,
        prompt: str,
        system: str = (
            "You are a component of MARK XXV, an AI assistant inspired by JARVIS. "
            "Be concise, helpful, and precise."
        ),
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        """Sends a text prompt to the model and returns text response."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        return self.execute_with_fallback(
            TEXT_MODELS, messages, model, max_tokens, temperature
        )

    def chat_json(
        self,
        prompt: str,
        system: str = (
            "Return ONLY valid JSON. "
            "No markdown fences, no extra text, no explanation."
        ),
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> dict:
        """Requests a JSON response from the model and parses it to a Python dict."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        raw_response = self.execute_with_fallback(
            TEXT_MODELS, messages, model, max_tokens, temperature=0.2
        )

        # Clean markdown code blocks if returned (e.g. ```json ... ```)
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]

        cleaned = cleaned.strip().rstrip("`").strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as error:
            logger.error(
                f"[OpenRouter] JSON parse failed: {error}\n"
                f"Raw response (first 300 chars): {raw_response[:300]}"
            )
            raise ValueError(
                f"Model returned unparseable JSON: {error}\n"
                f"Raw output: {raw_response[:200]}"
            )

    def vision(
        self,
        prompt: str,
        image_b64: str,
        mime: str = "image/png",
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        """Sends an image (in Base64 format) and prompt to vision models."""
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{image_b64}"
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        return self.execute_with_fallback(
            VISION_MODELS, messages, model, max_tokens, temperature=0.2
        )

    def vision_from_file(
        self,
        prompt: str,
        image_path: str,
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        """Loads an image file from disk, converts to base64, and sends it to vision models."""
        path = Path(image_path)
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        mime_type = mime_map.get(path.suffix.lower(), "image/png")

        with open(path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")

        return self.vision(prompt, base64_image, mime_type, system, model, max_tokens)

    def multi_turn(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        """Sends a conversation history list to the model."""
        return self.execute_with_fallback(
            TEXT_MODELS, messages, model, max_tokens, temperature
        )

    def available_models(self) -> dict:
        """Returns statistical overview of loaded model pools."""
        return {
            "text_models": TEXT_MODELS,
            "vision_models": VISION_MODELS,
            "rate_limited": list(rate_limited_models.keys()),
            "total_text": len(TEXT_MODELS),
            "total_vision": len(VISION_MODELS),
        }


# Global Client Instance
client = OpenRouterClient()


# ==========================================
# SELF-TEST RUNNER
# ==========================================

if __name__ == "__main__":
    print("=" * 55)
    print("  MARK XXV — OpenRouter Client Self-Test")
    print("=" * 55)

    print("\n[TEST 1] Basic chat...")
    try:
        reply = client.chat("Introduce yourself in one sentence.")
        print(f"  Response : {reply}")
        print(f"  Status   : PASS ✓")
    except Exception as e:
        print(f"  Status   : FAIL ✗ — {e}")

    print("\n[TEST 2] JSON mode...")
    try:
        data = client.chat_json(
            'List 3 programming languages. Format: {"languages": ["a", "b", "c"]}',
            system="Return only valid JSON. No extra text."
        )
        print(f"  Response : {data}")
        print(f"  Status   : PASS ✓")
    except Exception as e:
        print(f"  Status   : FAIL ✗ — {e}")

    print("\n[TEST 3] Multi-turn conversation...")
    try:
        history = [
            {"role": "system", "content": "You are a helpful assistant. Be brief."},
            {"role": "user", "content": "My name is Tony."},
            {"role": "assistant", "content": "Hello Tony, how can I help you?"},
            {"role": "user", "content": "What is my name?"},
        ]
        reply = client.multi_turn(history)
        print(f"  Response : {reply}")
        print(f"  Status   : PASS ✓")
    except Exception as e:
        print(f"  Status   : FAIL ✗ — {e}")

    print("\n[TEST 4] Model pool info...")
    info = client.available_models()
    print(f"  Text models   : {info['total_text']}")
    print(f"  Vision models : {info['total_vision']}")
    print(f"  Rate limited  : {info['rate_limited'] or 'none'}")
    print(f"  Status        : PASS ✓")

    print("\n" + "=" * 55)
    print("  All tests complete.")
    print("=" * 55)