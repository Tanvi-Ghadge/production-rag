from __future__ import annotations

import os


def command_r_provider(prompt: str) -> tuple[str, int, int]:
    import cohere

    client = cohere.ClientV2(api_key=os.environ["COHERE_API_KEY"])
    response = client.chat(
        model=os.getenv("COHERE_MODEL", "command-r-08-2024"),
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.message.content[0].text
    usage = response.usage
    return text, int(usage.tokens.input_tokens), int(usage.tokens.output_tokens)
