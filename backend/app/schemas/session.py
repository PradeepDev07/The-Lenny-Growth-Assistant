from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code, e.g. NOT_FOUND")
    message: str = Field(..., description="Human-readable explanation of the error")


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SessionCreate(BaseModel):
    title: Optional[str] = Field(default="New Conversation", max_length=255)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class MessageCreate(BaseModel):
    role: str = Field(..., description="user, assistant, or system")
    content: str = Field(..., min_length=1)
    sources: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    model_info: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: str
    content: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    model_info: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class SessionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    user_metadata: Dict[str, Any] = Field(default_factory=dict)
    messages: List[MessageResponse] = Field(default_factory=list)


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="ID of the conversation session")
    message: str = Field(..., min_length=1, description="User's prompt or question")
    provider_override: Optional[str] = Field(default=None, description="Optional provider override: 'ollama', 'gemini', or 'openrouter'")


