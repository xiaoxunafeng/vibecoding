from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(
        None, description="会话 ID，为空则自动创建新会话"
    )
    message: str = Field(..., min_length=1, description="用户输入内容")
    thinking: bool | None = Field(
        None, description="是否开启思考模式，不传则使用服务器默认值"
    )


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    reasoning_content: str = ""
    created_at: str


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class ConversationUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
