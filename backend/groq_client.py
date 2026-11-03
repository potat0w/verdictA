import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def get_groq_api_key() -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in the environment")
    return api_key


def get_groq_model() -> str:
    model = os.getenv("GROQ_MODEL_NAME", "").strip().strip('"')
    if not model:
        raise ValueError("GROQ_MODEL_NAME is not set in the environment")
    return model


def get_groq_client() -> OpenAI:
    return OpenAI(
        api_key=get_groq_api_key(),
        base_url=GROQ_BASE_URL,
    )


def generate_text(
    prompt: str,
    *,
    temperature: float | None = None,
    json_mode: bool = False,
) -> str:
    """Completion call. Extra keyword arguments are optional and default off.

    Existing callers that pass only a prompt keep the previous request shape.
    """
    client = get_groq_client()
    model = get_groq_model()
    kwargs: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""
