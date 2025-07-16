"""Provider names and configuration constants."""


# Provider names
class ProviderNames:
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    XAI = "xai"
    OLLAMA = "ollama"
    LOCAL = "local"
    SILENT = "silent"


# Provider model prefixes
class ModelPrefixes:
    ANTHROPIC = "claude"
    OPENAI = "gpt"
    GOOGLE = "gemini"
    XAI = "grok"
    OLLAMA = "ollama"
    LOCAL = "local"


# Special models
class SpecialModels:
    LOCAL_TEST = "local:test"
    OLLAMA_DEFAULT = "ollama:qwen2.5:0.5b"
    SILENT = "silent"


# Environment variable names
class EnvVars:
    ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
    OPENAI_API_KEY = "OPENAI_API_KEY"
    GOOGLE_API_KEY = "GOOGLE_API_KEY"
    GEMINI_API_KEY = "GEMINI_API_KEY"
    XAI_API_KEY = "XAI_API_KEY"
    GROK_API_KEY = "GROK_API_KEY"


# Collections
ALL_PROVIDERS = [
    ProviderNames.ANTHROPIC,
    ProviderNames.OPENAI,
    ProviderNames.GOOGLE,
    ProviderNames.XAI,
    ProviderNames.OLLAMA,
    ProviderNames.LOCAL,
    ProviderNames.SILENT,
]

API_PROVIDERS = [
    ProviderNames.ANTHROPIC,
    ProviderNames.OPENAI,
    ProviderNames.GOOGLE,
    ProviderNames.XAI,
]

LOCAL_PROVIDERS = [
    ProviderNames.OLLAMA,
    ProviderNames.LOCAL,
    ProviderNames.SILENT,
]
