from abc import ABC, abstractmethod


class BaseEntity(ABC):
    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    def get(self):
        pass

    @abstractmethod
    def list(self):
        pass
