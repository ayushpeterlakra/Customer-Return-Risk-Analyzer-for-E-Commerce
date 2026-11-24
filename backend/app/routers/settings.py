from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_tx
from app.models import ScoringConfigRecord
from app.scoring import ScoringConfig, load_default_config
from app.services.notifications import email_enabled
from app.services.scoring_service import assess_all, get_active_config

router = APIRouter(prefix="/api/settings", tags=["settings"])
DB = Annotated[Session, Depends(get_tx)]


class SaveRules(BaseModel):
    config: ScoringConfig
    updated_by: str = Field(min_length=1, max_length=120)
    rescore: bool = True


class RulesResponse(BaseModel):
    config: ScoringConfig
    source: str
    email_alerts_enabled: bool


@router.get("/scoring-rules", response_model=RulesResponse)
def get_rules(db: DB):
    has_saved = db.scalar(select(ScoringConfigRecord.id).limit(1)) is not None
    return RulesResponse(
        config=get_active_config(db),
        source="database" if has_saved else "default file",
        email_alerts_enabled=email_enabled(),
    )


@router.put("/scoring-rules", response_model=RulesResponse, summary="Save a new rules version and rescore")
def save_rules(body: SaveRules, db: DB):
    version = datetime.now(UTC).strftime("v%Y%m%d-%H%M%S")
    if db.scalar(select(ScoringConfigRecord.id).where(ScoringConfigRecord.version == version)):
        raise HTTPException(409, "A version was saved this second; try again")
    config = body.config.model_copy(update={"version": version})
    db.add(
        ScoringConfigRecord(version=version, config=config.model_dump(), updated_by=body.updated_by.strip())
    )
    db.flush()
    if body.rescore:
        assess_all(db)
    return RulesResponse(config=config, source="database", email_alerts_enabled=email_enabled())


@router.post(
    "/scoring-rules/reset", response_model=RulesResponse, summary="Restore the default rules and rescore"
)
def reset_rules(db: DB, updated_by: str = "admin"):
    default = load_default_config()
    version = datetime.now(UTC).strftime("default-%Y%m%d-%H%M%S")
    db.add(
        ScoringConfigRecord(
            version=version,
            config=default.model_copy(update={"version": version}).model_dump(),
            updated_by=updated_by,
        )
    )
    db.flush()
    assess_all(db)
    return RulesResponse(
        config=get_active_config(db), source="database", email_alerts_enabled=email_enabled()
    )
