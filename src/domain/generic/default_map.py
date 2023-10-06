from abc import abstractmethod


class DefaultMap:
    default: any

    @property
    @abstractmethod
    def _map(self) -> dict[str, any] | None:
        return

    def get(self, key: str):
        if self._map:
            value = self._map.get(key)
            if value:
                return value
        return self.default
