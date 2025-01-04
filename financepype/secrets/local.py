import json
import os
from typing import Any

from pydantic import BaseModel

from financepype.secrets.base import ExchangeSecrets, ExchangesSecrets


class LocalExchangeSecrets(ExchangesSecrets):
    file_path: str

    class LocalFormatter(BaseModel):
        exchange_secrets: dict[str, ExchangeSecrets]

    def retrieve_secrets(self, exchange_name: str, **kwargs: Any) -> ExchangeSecrets:
        secrets = self.LocalFormatter.model_validate(self.get_local_secrets())
        return secrets.exchange_secrets[exchange_name]

    def get_local_secrets(self) -> dict[str, dict[str, Any]]:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File {self.file_path} not found")

        with open(self.file_path) as file:
            secrets: dict[str, dict[str, Any]] = json.load(file)
        return secrets
