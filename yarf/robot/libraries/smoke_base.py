from abc import ABC, abstractmethod


class SmokeBase(ABC):
    @abstractmethod
    def print_smoke(self) -> None:
        raise NotImplementedError
