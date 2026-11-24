from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.deps import get_tx
from app.models import RiskLevel
from app.services import data_service as svc

router = APIRouter(prefix="/api/data", tags=["data"])
DB = Annotated[Session, Depends(get_tx)]
MAX_BYTES = 5 * 1024 * 1024


@router.post("/import", summary="Import orders and returns from CSV (all-or-nothing), then rescore")
async def import_data(
    db: DB, file: Annotated[UploadFile, File(description="CSV with the documented columns")]
):
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "File larger than 5 MB")
    return svc.import_csv(db, content)


@router.get("/import/template", summary="Empty CSV template with the required columns")
def template():
    return Response(
        ",".join(svc.IMPORT_COLUMNS) + "\n",
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="import_template.csv"'},
    )


@router.get("/export/flagged-customers", summary="CSV of flagged customers (no contact details)")
def export_flagged(
    db: DB,
    risk_level: Annotated[
        Literal["LOW", "MEDIUM", "HIGH", "ALL"], Query(description="ALL = every scored customer")
    ] = "HIGH",
    min_score: Annotated[int | None, Query(ge=0, le=100)] = None,
):
    level = None if risk_level == "ALL" else RiskLevel(risk_level)
    csv_text = svc.export_flagged_csv(db, level, min_score)
    return Response(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="flagged_customers.csv"'},
    )
