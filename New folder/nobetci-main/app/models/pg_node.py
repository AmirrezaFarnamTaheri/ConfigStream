from pydantic import BaseModel


class PGNode(BaseModel):
    id: int
    name: str
    address: str
    port: int
    status: str
    message: str | None = None