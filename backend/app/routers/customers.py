from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_tx
from app.models import RiskLevel
from app.schemas.common import Page
from app.schemas.customers import CustomerDetail, CustomerListItem, OrderOut, ReturnOut
from app.services import customers_service as svc

router = APIRouter(prefix="/api/customers", tags=["customers"])
DB = Annotated[Session, Depends(get_tx)]
PageNo = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.get("", response_model=Page[CustomerListItem], summary="Customer table with search, filters, sorting")
def list_customers(
    db: DB,
    page: PageNo = 1,
    page_size: PageSize = 20,
    search: Annotated[str | None, Query(max_length=100, description="Customer ID or name")] = None,
    risk_level: RiskLevel | None = None,
    min_score: Annotated[int | None, Query(ge=0, le=100)] = None,
    min_return_ratio: Annotated[float | None, Query(ge=0, le=1, description="e.g. 0.3 for above 30%")] = None,
    category: Annotated[str | None, Query(max_length=60)] = None,
    sort: svc.SortField = "risk_score",
    order: Literal["asc", "desc"] = "desc",
):
    return svc.list_customers(
        db,
        page=page,
        page_size=page_size,
        search=search,
        risk_level=risk_level,
        min_score=min_score,
        min_return_ratio=min_return_ratio,
        category=category,
        sort=sort,
        order=order,
    )


@router.get("/{customer_id}", response_model=CustomerDetail, summary="Customer profile")
def get_customer(customer_id: str, db: DB):
    return svc.customer_detail(db, customer_id)


@router.get("/{customer_id}/orders", response_model=Page[OrderOut], summary="Customer order history")
def get_orders(customer_id: str, db: DB, page: PageNo = 1, page_size: PageSize = 50):
    return svc.customer_orders(db, customer_id, page, page_size)


@router.get("/{customer_id}/returns", response_model=Page[ReturnOut], summary="Customer return history")
def get_returns(customer_id: str, db: DB, page: PageNo = 1, page_size: PageSize = 50):
    return svc.customer_returns(db, customer_id, page, page_size)
