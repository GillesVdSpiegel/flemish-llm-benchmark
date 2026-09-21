from flembench.adapters.base import Adapter, Completion


def make_adapter(provider: str) -> Adapter:
    if provider == "anthropic":
        from flembench.adapters.anthropic_adapter import AnthropicAdapter

        return AnthropicAdapter()
    if provider == "openai":
        from flembench.adapters.openai_adapter import OpenAIAdapter

        return OpenAIAdapter()
    if provider == "gemini":
        from flembench.adapters.gemini_adapter import GeminiAdapter

        return GeminiAdapter()
    if provider == "ollama":
        from flembench.adapters.ollama_adapter import OllamaAdapter

        return OllamaAdapter()
    raise ValueError(f"unknown provider {provider!r}")


__all__ = ["Adapter", "Completion", "make_adapter"]
