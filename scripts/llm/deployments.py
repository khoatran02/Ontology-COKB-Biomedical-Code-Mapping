# This file contains all deployed models.

# Open AI models hosted on Azure:
GPT_35_TURBO = "gpt-35-turbo-0613"
GPT_4 = "gpt-4"

AZURE_DEPLOYMENTS = [
    GPT_35_TURBO,
    GPT_4,
]

# Google Gemini models:
GEMINI_35_FLASH = "gemini-3.5-flash"
GEMINI_20_FLASH = "gemini-2.0-flash"
GEMINI_15_FLASH = "gemini-1.5-flash"
GEMINI_15_PRO = "gemini-1.5-pro"
GEMINI_FLASH = "gemini-flash"

GEMINI_DEPLOYMENTS = [
    GEMINI_35_FLASH,
    GEMINI_20_FLASH,
    GEMINI_15_FLASH,
    GEMINI_15_PRO,
    GEMINI_FLASH,
]

# Source: https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models @ 29 Sep 2023
MAX_TOKENS = {
    GPT_35_TURBO: 4096,
    GPT_4: 8192,
    'meta-llama/Meta-Llama-3-8B-Instruct': 8191, # Customizable
    GEMINI_35_FLASH: 1048576,
    GEMINI_20_FLASH: 1048576,
    GEMINI_15_FLASH: 1048576,
    GEMINI_15_PRO: 2097152,
    GEMINI_FLASH: 1048576,
}

# Huggingface models hosted on AWS:
FLAN_XXL = 'google/flan-t5-xxl'
AWS_MODEL_PATHS = {
    FLAN_XXL: 'flan-t5-xxl',
    'meta-llama/Meta-Llama-3-8B-Instruct': 'meta-llama3-instruct'
}
AWS_DEPLOYMENTS = list(AWS_MODEL_PATHS)

