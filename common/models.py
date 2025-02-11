from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class SystemConfiguration:
    system_config_id: int
    system_name: str
    partner_id: str
    partner_name: str
    file_type: str
    system_type: str
    config: Dict
    s3_bucket_name: str
    credentials_secret_id: str
    schedule: str
    is_active: str
    feature_flags: Dict


@dataclass
class RunHistory:
    run_id: int
    system_id: int
    step: str
    status: str
    details: Optional[str]
    start_time: str
    end_time: str


@dataclass
class ErrorLog:
    error_id: int
    run_id: int
    system_id: int
    error_message: str
    step: str
    occurred_at: str


@dataclass
class StatusUpdateQueue:
    execution_id: str
    system_config_id: int
    community_code: str
    lead_id: str
    status: str
    sub_status: str
    notes: str
    lead_json: Dict
    status_update_id: Optional[int] = None
    error_message: Optional[str] = None
    attempts: int = 0
    last_attempt: Optional[datetime] = field(default_factory=lambda: datetime.now())
    is_delivered: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now())
    updated_at: datetime = field(default_factory=lambda: datetime.now())

    def to_tuple(self):
        """
        Converts the instance to a tuple, excluding DB-managed fields for bulk insert.
        """
        return (
            self.execution_id,
            self.system_config_id,
            self.community_code,
            self.lead_id,
            self.status,
            self.sub_status,
            self.notes,
            self.lead_json,
            self.attempts,
            self.last_attempt,
            self.is_delivered,
            self.error_message,
        )
