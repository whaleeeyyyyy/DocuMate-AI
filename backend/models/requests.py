from pydantic import BaseModel
from typing import List, Optional

class QuestionRequest(BaseModel):
    document_id: str
    question: str

class SemanticSearchRequest(BaseModel):
    document_id: str
    query: str

class Entity(BaseModel):
    text: str
    label: str
    start: Optional[int] = None
    end: Optional[int] = None

class UploadPDFResponse(BaseModel):
    document_id: str
    extracted_text: str
    summary: str
    entities: List[Entity]

# --- NEW ---
class AgentQueryRequest(BaseModel):
    document_id: str
    query: str

class AgentQueryResponse(BaseModel):
    answer: str
    tool_calls: Optional[List[dict]] = None # Optional: to show what tools were called
    final_prompt: Optional[str] = None # Optional: to show the final prompt to Gemini

class DocumentListItem(BaseModel):
    id: str
    filename: str