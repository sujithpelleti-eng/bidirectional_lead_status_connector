from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseParser(ABC):
    def __init__(self, system_config_id: str):
        self.system_config_id = system_config_id

    @abstractmethod
    def parse(self, raw_data: Any) -> Dict:
        pass
