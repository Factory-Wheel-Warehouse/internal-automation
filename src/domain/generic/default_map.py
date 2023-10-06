from abc import abstractmethod


class DefaultMap:
    default: any

    @property
    @abstractmethod
    def _map(self) -> dict[str, any] | None:
        return

    def get(self, key: str):
        return self._map.get(key, self.default)
