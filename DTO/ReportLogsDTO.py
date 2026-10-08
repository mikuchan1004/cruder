from sqlmodel import SQLModel, Field

class ReportLogsDTO(SQLModel,table=True):
    report_id:int |None=Field(
        default=None,
        primary_key=True
    )
    report_reason:str | None=Field(
        default=None,
        max_length=120
    ) 
    user_id:str=Field(
        foreign_key='user.user_id',
        max_length=12
    )
    job_tip_no:int=Field(
        foreign_key='job_tip.job_tip_no'
    )