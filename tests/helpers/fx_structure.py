# coding: utf-8
from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class GetBaseNameData:
    sign: str
    value: str
    result: str
