from pydantic import BaseModel

class Plugin(BaseModel):
    id: str
    display_name: str
    description: str|None

class SourcePlugin(Plugin):
    ...
