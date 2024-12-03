from abc import ABC, abstractmethod
from typing import Dict


class BaseDestination(ABC):
    @abstractmethod
    def send(self, data: Dict, file_name: str = None):
        pass
