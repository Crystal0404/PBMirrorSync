import sys
from pathlib import Path

from mcdreforged import *
from pydantic import BaseModel, ConfigDict, field_validator, Field

from pb_mirror_sync.constant import SI, PB_ID


class PBActionBase(BaseModel):
    model_config = ConfigDict(strict=True, extra='allow')

    python: str | None = None
    pb_path: str | None = None
    db_file: str = ''
    config_file: str | None = None

    @field_validator('python')
    @classmethod
    def python_validation(cls, value: str | None) -> str:
        if value is None:
            python = sys.executable
            if python == '' or python is None:
                raise ValueError
            else:
                return python

        path = Path(value)
        if not path.exists() or not path.is_file():
            raise ValueError

        return value

    @field_validator('pb_path')
    @classmethod
    def pb_validation(cls, value: str | None) -> str:
        if value is None:
            pb = SI.get_plugin_file_path(PB_ID)
            if pb is not None:
                return pb
            else:
                raise ValueError

        path = Path(value)
        if not path.exists() or not path.is_file():
            raise ValueError

        return value


class PBActionExport(PBActionBase):
    target: list[str] = Field(default_factory=lambda: ['world'])


class PBActionMake(PBActionBase):
    source_root: str = ''
    enabled: bool = False


class Config(BaseModel):
    model_config = ConfigDict(strict=True)

    prefix: str = '!!mirror'
    permission: int = PermissionLevel.HELPER
    sync: PBActionExport = Field(default_factory=PBActionExport)
    backup: PBActionMake = Field(default_factory=PBActionMake)
