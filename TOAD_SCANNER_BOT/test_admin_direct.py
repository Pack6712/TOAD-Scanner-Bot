import asyncio
import traceback

from fastapi import Response

from config import ADMIN_SECRET
from api.main import (
    admin_login,
    AdminLoginRequest,
)


async def main():
    try:
        response = Response()

        result = await admin_login(
            AdminLoginRequest(
                secret=ADMIN_SECRET
            ),
            response
        )

        print("✅ ADMIN LOGIN РАБОТАЕТ")
        print(result)

    except Exception:
        print("❌ ОШИБКА:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())