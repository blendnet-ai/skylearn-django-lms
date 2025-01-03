from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class TelegramMessage:
    chat_id: str
    text: str
    parse_mode: Optional[str] = 'HTML'
    reply_markup: Optional[Dict] = None

class TelegramInterface(ABC):
    @abstractmethod
    async def send_message(self, message: TelegramMessage) -> bool:
        pass