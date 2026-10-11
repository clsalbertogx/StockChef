from __future__ import annotations

import json
import urllib.request

VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"
TIMEOUT_SECONDS = 5


class ViaCepError(Exception):
    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind  # "invalid" | "not_found" | "unavailable"


def lookup(cep: str) -> dict:
    digits = "".join(ch for ch in cep if ch.isdigit())
    if len(digits) != 8:
        raise ViaCepError("invalid")
    request = urllib.request.Request(
        VIACEP_URL.format(cep=digits), headers={"User-Agent": "StockChef/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise ViaCepError("unavailable") from exc
    if data.get("erro"):
        raise ViaCepError("not_found")
    return {
        "cep": digits,
        "street": data.get("logradouro", ""),
        "district": data.get("bairro", ""),
        "city": data.get("localidade", ""),
        "state": data.get("uf", ""),
    }
