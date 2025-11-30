from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    """
    Abstract base class for all notification providers.
    """

    @abstractmethod
    async def send_message(self, message: str):
        """
        Send a message to the provider's platform.
        The input 'message' is expected to be in standard Markdown format.
        """
        pass
