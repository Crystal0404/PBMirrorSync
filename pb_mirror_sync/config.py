from pydantic import BaseModel, ConfigDict
from mcdreforged import *


class Config(BaseModel):
    model_config = ConfigDict(strict=True)

    prefix: str = "!!mirror"
    permission: int = PermissionLevel.HELPER
