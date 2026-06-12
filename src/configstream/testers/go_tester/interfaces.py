# SPDX-License-Identifier: AGPL-3.0-or-later
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ITester(ABC):
    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def test_batch(self, proxies: List[Any]) -> Dict[str, Any]:
        pass
