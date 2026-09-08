from abc import ABC, abstractmethod


class GenerationProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        pass
