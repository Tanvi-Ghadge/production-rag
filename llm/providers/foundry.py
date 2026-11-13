from __future__ import annotations

import os


def foundry_provider(prompt: str) -> tuple[str, int, int]:
    """Azure AI Foundry/OpenAI-compatible chat provider."""
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_FOUNDRY_ENDPOINT"],
        api_key=os.environ["AZURE_FOUNDRY_API_KEY"],
        api_version=os.getenv("AZURE_FOUNDRY_API_VERSION", "2024-10-21"),
    )
    response = client.chat.completions.create(
        model=os.environ["AZURE_FOUNDRY_DEPLOYMENT"],
        messages=[{"role": "user", "content": prompt}], temperature=0,
    )
    usage = response.usage
    return response.choices[0].message.content or "", int(usage.prompt_tokens or 0), int(usage.completion_tokens or 0)
