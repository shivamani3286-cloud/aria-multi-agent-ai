from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# ─── Task Schemas ────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    due_date: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(pending|in_progress|completed|cancelled)$")
    priority: Optional[str] = Field(default=None, pattern="^(low|medium|high)$")
    due_date: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    priority: str
    due_date: Optional[str]
    created_at: str
    updated_at: str

# ─── Calendar Schemas ─────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    location: Optional[str] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None

class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    start_time: str
    end_time: str
    location: Optional[str]
    created_at: str

# ─── Notes Schemas ────────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    title: str
    content: str
    tags: Optional[str] = None

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[str] = None

class NoteResponse(BaseModel):
    id: int
    title: str
    content: str
    tags: Optional[str]
    created_at: str
    updated_at: str

# ─── Agent Schemas ────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class AgentResponse(BaseModel):
    session_id: str
    response: str
    actions_taken: List[dict] = []
    agent_used: str