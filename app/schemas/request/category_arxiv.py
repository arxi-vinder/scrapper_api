from pydantic import BaseModel
from typing import Dict

class CategoryArxivRequest(BaseModel):
    arxiv_fields: Dict[str, int]