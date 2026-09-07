from scripts.llm.clients import BaseLLMClient, AzureClient, TGIClient, GeminiClient
from scripts.llm.deployments import AZURE_DEPLOYMENTS, AWS_DEPLOYMENTS, GEMINI_DEPLOYMENTS
from scripts.llm.configs import IP, GEMINI_MODEL


MODEL_ALIASES = {
    "gpt-35": "gpt-35-turbo-0613",
    "flan-xxl": "google/flan-t5-xxl",
    "llama-3": "meta-llama/Meta-Llama-3-8B-Instruct",
    "gemini": GEMINI_MODEL or "gemini-3.5-flash",
    "gemini-flash": "gemini-3.5-flash",
    "gemini-3.5-flash": "gemini-3.5-flash",
    "gemini-3-flash": "gemini-3.5-flash",
    "gemini-2.0-flash": "gemini-2.0-flash",
    "gemini-1.5-flash": "gemini-1.5-flash",
    "gemini-1.5-pro": "gemini-1.5-pro",
}


class ModelLoader:
    """
    Utility class for loading and retrieving LLMs.
    """

    def __init__(self, model_name: str, ip: str = IP, temperature: float = 1):
        self.requested_model_name = model_name
        self.model_name = MODEL_ALIASES.get(model_name, model_name)
        self.ip = ip
        self.temperature = temperature
        """
        Args:
            model_name (str): Name of the model deployed on the server.
            ip (str): IP address of the text-generation-inference server.
        """

    def get_client(self) -> BaseLLMClient:
        """
        Creates a Client object based on the model specified.
        """
        if self.model_name in AZURE_DEPLOYMENTS:
            return AzureClient(self.model_name, temperature=self.temperature)
        elif self.model_name in AWS_DEPLOYMENTS:
            return TGIClient(self.ip, self.model_name, temperature=self.temperature)
        elif self.model_name in GEMINI_DEPLOYMENTS or "gemini" in self.model_name.lower():
            return GeminiClient(self.model_name, temperature=self.temperature)
        else:
            raise ValueError(f"Cannot find model with the name {self.model_name} deployed anywhere!")

    def get_deployment_type(self) -> str:
        if self.model_name in AZURE_DEPLOYMENTS:
            return "azure"
        elif self.model_name in AWS_DEPLOYMENTS:
            return "aws"
        elif self.model_name in GEMINI_DEPLOYMENTS or "gemini" in self.model_name.lower():
            return "gemini"
        else:
            raise ValueError(f"Cannot find model with the name {self.model_name} deployed anywhere!")

