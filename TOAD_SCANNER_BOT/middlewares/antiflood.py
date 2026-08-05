import time

from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class AntiFloodMiddleware(BaseMiddleware):
    def __init__(
        self,
        delay: float = 0.7,
    ):
        super().__init__()

        self.delay = delay

        self.users = defaultdict(
            lambda: 0.0
        )

    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict,
    ):
        user = data.get(
            "event_from_user"
        )

        if user is None:
            return await handler(
                event,
                data
            )

        now = time.monotonic()

        last_time = self.users[
            user.id
        ]

        if (
            now - last_time
            < self.delay
        ):
            return

        self.users[
            user.id
        ] = now

        return await handler(
            event,
            data
        )