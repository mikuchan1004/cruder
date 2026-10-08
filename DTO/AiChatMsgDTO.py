from sqlmodel import SQLModel, Field

class AiChatMsg(SQLModel,table=True):
    ai_chat_message_id:int|None=Field(
        default=None,
        primary_key=True
    )
    ai_chat_detail:str|None=None
    ai_chat_id:int=Field(
        foreign_key='ai_chat_room.ai_chat_id'
    )