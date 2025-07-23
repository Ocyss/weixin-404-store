from datetime import datetime
from typing import Annotated, Any, Generic, Self, TypeVar, overload

from beanie import Document, Indexed
from pydantic import Field as PydanticField

T = TypeVar("T")


class KeyValue(Document, Generic[T]):
    key: Annotated[str, Indexed(unique=True)]
    value: T
    created_at: datetime = PydanticField(default_factory=datetime.now)
    updated_at: datetime = PydanticField(default_factory=datetime.now)

    @classmethod
    async def init_config(cls, key: str, default_value: Any) -> Self:
        config = await cls.find_one(cls.key == key)
        if not config:
            config = cls(key=key, value=default_value)
            await config.save()
        return config

    @overload
    @classmethod
    async def get_config(cls, key: str) -> "KeyValue[T] | None": ...

    @overload
    @classmethod
    async def get_config(cls, key: str, default_value: T) -> "KeyValue[T]": ...

    @classmethod
    async def get_config(
        cls, key: str, default_value: T | None = None
    ) -> "KeyValue[T] | None":
        config = await cls.find_one(cls.key == key)
        if config is None and default_value is not None:
            config = cls(key=key, value=default_value)
            await config.save()
        return config

    async def update_value(self, new_value: T) -> None:
        self.value = new_value
        self.updated_at = datetime.now()
        await self.save()
