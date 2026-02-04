#!/usr/bin/env python3
"""Simple LiteLLM test script for Gemini 3 Pro Preview."""

from dotenv import load_dotenv
load_dotenv()

import os
import requests

import litellm

def list_available_models():
    """List all available Gemini models and their info."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set!")
        return

    print("=" * 60)
    print("AVAILABLE GEMINI MODELS")
    print("=" * 60)

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Error fetching models: {response.status_code}")
        print(response.text)
        return

    data = response.json()
    models = data.get("models", [])

    # Filter for generateContent-capable models
    generate_models = [m for m in models if "generateContent" in m.get("supportedGenerationMethods", [])]

    print(f"\nFound {len(generate_models)} models with generateContent capability:\n")

    for model in sorted(generate_models, key=lambda x: x["name"]):
        name = model["name"].replace("models/", "")
        display_name = model.get("displayName", "N/A")
        input_limit = model.get("inputTokenLimit", "N/A")
        output_limit = model.get("outputTokenLimit", "N/A")

        print(f"  • {name}")
        print(f"    Display: {display_name}")
        print(f"    Tokens: {input_limit} in / {output_limit} out")
        print()


def test_model(model_name: str):
    """Test a specific model."""
    print("=" * 60)
    print(f"TESTING: {model_name}")
    print("=" * 60)

    try:
        response = litellm.completion(
            model=model_name,
            messages=[
                {"role": "user", "content": "Say hello in one sentence."}
            ],
        )

        print("\n✅ SUCCESS!")
        print(f"Response: {response.choices[0].message.content}")
        print(f"Model: {response.model}")
        print(f"Usage: {response.usage}")
        return True

    except litellm.exceptions.RateLimitError as e:
        print(f"\n❌ RATE LIMITED: {e.message[:200]}...")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)[:200]}...")
        return False


def main():
    # List available models
    list_available_models()

    # Test specific models
    print("\n" + "=" * 60)
    print("TESTING MODELS")
    print("=" * 60 + "\n")

    models_to_test = [
        "gemini/gemini-3-pro-preview",
        "gemini/gemini-2.5-pro-preview-05-06",
        "gemini/gemini-2.0-flash",
        "gemini/gemini-1.5-flash",
    ]

    for model in models_to_test:
        test_model(model)
        print()


if __name__ == "__main__":
    main()
