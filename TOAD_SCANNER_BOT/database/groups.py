from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    String,
    select,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from database.database import (
    Base,
    Session,
)


class TelegramGroup(Base):
    __tablename__ = "telegram_groups"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    owner_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    guard_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    auto_check_members: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    warn_mode: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    mute_mode: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    ban_mode: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )


async def get_group(
    telegram_chat_id: int,
):
    async with Session() as session:
        result = await session.execute(
            select(TelegramGroup).where(
                TelegramGroup.telegram_chat_id
                == telegram_chat_id
            )
        )

        return result.scalar_one_or_none()


async def save_or_update_group(
    telegram_chat_id: int,
    title: str | None,
    username: str | None,
    owner_id: int | None,
):
    async with Session() as session:
        result = await session.execute(
            select(TelegramGroup).where(
                TelegramGroup.telegram_chat_id
                == telegram_chat_id
            )
        )

        group = result.scalar_one_or_none()

        if group is None:
            group = TelegramGroup(
                telegram_chat_id=telegram_chat_id,
                title=title,
                username=username,
                owner_id=owner_id,
                is_active=True,
                guard_enabled=False,
                auto_check_members=False,
                warn_mode=True,
                mute_mode=False,
                ban_mode=False,
            )

            session.add(group)

        else:
            group.title = title
            group.username = username

            if owner_id is not None:
                group.owner_id = owner_id

            group.is_active = True

        await session.commit()
        await session.refresh(group)

        return group


async def disable_group(
    telegram_chat_id: int,
):
    async with Session() as session:
        result = await session.execute(
            select(TelegramGroup).where(
                TelegramGroup.telegram_chat_id
                == telegram_chat_id
            )
        )

        group = result.scalar_one_or_none()

        if group is None:
            return False

        group.is_active = False
        group.guard_enabled = False

        await session.commit()

        return True


async def toggle_guard(
    telegram_chat_id: int,
):
    async with Session() as session:
        result = await session.execute(
            select(TelegramGroup).where(
                TelegramGroup.telegram_chat_id
                == telegram_chat_id
            )
        )

        group = result.scalar_one_or_none()

        if group is None:
            return None

        group.guard_enabled = not group.guard_enabled

        await session.commit()
        await session.refresh(group)

        return group


async def toggle_auto_check_members(
    telegram_chat_id: int,
):
    async with Session() as session:
        result = await session.execute(
            select(TelegramGroup).where(
                TelegramGroup.telegram_chat_id
                == telegram_chat_id
            )
        )

        group = result.scalar_one_or_none()

        if group is None:
            return None

        group.auto_check_members = (
            not group.auto_check_members
        )

        await session.commit()
        await session.refresh(group)

        return group


async def toggle_warn_mode(
    telegram_chat_id: int,
):
    async with Session() as session:
        result = await session.execute(
            select(TelegramGroup).where(
                TelegramGroup.telegram_chat_id
                == telegram_chat_id
            )
        )

        group = result.scalar_one_or_none()

        if group is None:
            return None

        group.warn_mode = not group.warn_mode

        await session.commit()
        await session.refresh(group)

        return group


async def toggle_mute_mode(
    telegram_chat_id: int,
):
    async with Session() as session:
        result = await session.execute(
            select(TelegramGroup).where(
                TelegramGroup.telegram_chat_id
                == telegram_chat_id
            )
        )

        group = result.scalar_one_or_none()

        if group is None:
            return None

        group.mute_mode = not group.mute_mode

        await session.commit()
        await session.refresh(group)

        return group


async def toggle_ban_mode(
    telegram_chat_id: int,
):
    async with Session() as session:
        result = await session.execute(
            select(TelegramGroup).where(
                TelegramGroup.telegram_chat_id
                == telegram_chat_id
            )
        )

        group = result.scalar_one_or_none()

        if group is None:
            return None

        group.ban_mode = not group.ban_mode

        await session.commit()
        await session.refresh(group)

        return group