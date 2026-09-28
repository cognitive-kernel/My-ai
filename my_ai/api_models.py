from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl

from .config import settings
from .chat_transport_context import set_attachments


class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None
    attachments: list[dict[str, object]] = Field(default_factory=list)

    def model_post_init(self, __context) -> None:
        set_attachments(self.attachments)


class SelfUpdateRequest(BaseModel):
    health_url: HttpUrl | None = None


class RepairRequest(BaseModel):
    issue: str = ""
    proposal_id: str | None = None
    approved: bool = False


class AuthRegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class KnowledgeUpdateRequest(BaseModel):
    title: str
    content: str
    topic: str
    source_url: str | None = None


class BackupRequest(BaseModel):
    path: str
    password: str | None = None
    destination: str | None = None


class PermissionRequest(BaseModel):
    user_id: int
    tool_name: str
    action: str
    allowed: bool


class AdminUserRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""
    active: bool = True


class SkillEvidenceRequest(BaseModel):
    skill_id: int
    kind: str
    passed: bool
    details: dict[str, object] = Field(default_factory=dict)


class SkillRevalidateRequest(BaseModel):
    skill_id: int
    version: str


class VoiceTranscribeRequest(BaseModel):
    audio_path: str
    model_path: str = ""
    language: str = "fa"


class VoiceSynthesizeRequest(BaseModel):
    text: str
    model_path: str = ""
    output_path: str


class URLRequest(BaseModel):
    url: HttpUrl
    topic: str = "Python"


class ProjectRequest(BaseModel):
    goal: str


class CodeRequest(BaseModel):
    code: str
    confirmed: bool = False


class ProgramRequest(BaseModel):
    request: str
    language: str = "Python"


class LanguageRequest(BaseModel):
    language: str = "Python"


class SecurityRequest(BaseModel):
    project_path: str | None = None
    target_url: str | None = None
    code: str | None = None
    language: str = "Python"
    fix: bool = False
    headers: dict[str, str] = Field(default_factory=dict)


class GitRequest(BaseModel):
    repository: str
    path: str | None = None
    ref: str | None = None
    branch: str | None = None
    content: str | None = None
    message: str | None = None
    allow_write: bool = False


class SchedulerRequest(BaseModel):
    language: str = "Python"
    interval_seconds: int = settings.scheduler_interval_seconds


class LearnRequest(BaseModel):
    language: str = "Python"
    interval_seconds: int = settings.scheduler_interval_seconds


class ToolRequest(BaseModel):
    language: str = "Python"
    operation: str = "test"
    cwd: str | None = None
    timeout: int = 120
    confirmed: bool = False


class PythonToolRequest(BaseModel):
    code: str
    confirmed: bool = False


class SQLQueryRequest(BaseModel):
    sql: str
    limit: int = 1000


class SQLiteQueryRequest(BaseModel):
    path: str
    sql: str
    limit: int = 1000


class SystemPrerequisiteRequest(BaseModel):
    names: list[str] = Field(default_factory=list)
    confirmed: bool = False


class ProjectBuildRequest(BaseModel):
    goal: str
    language: str = "Python"
    timeout: int = 300
    repair_attempts: int = 2
    confirmed: bool = False
