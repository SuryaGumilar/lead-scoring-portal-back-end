from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import List, Optional
from datetime import timedelta
from sqlalchemy import desc, nulls_last, func
from math import ceil
from schemas import PaginatedCustomerResponse, CustomerItem

from models import User, Customer
from database import engine, get_session, create_db_and_tables
from seed import create_users
from auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from prediction import run_prediction_and_update_db
import os

is_dev = os.getenv("ENV") == "development"

app = FastAPI(
    title="Lead Scoring Backend API",
    docs_url="/docs" if is_dev else None,
    redoc_url="/redoc" if is_dev else None,
    openapi_url="/openapi.json" if is_dev else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    create_users()  

@app.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Helper: Filter customers by name or marital status
@app.get("/", response_model=PaginatedCustomerResponse)
def list_customers(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    name: Optional[str] = Query(None),
    job: Optional[str] = Query(None),
    marital_status: Optional[str] = Query(None),
    education: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
):
    # Build base query with filters
    query = select(Customer)
    if name:
        query = query.where(Customer.name.icontains(name))
    if job:
        query = query.where(Customer.job.icontains(job))
    if marital_status:
        query = query.where(Customer.marital_status == marital_status)
    if education:
        query = query.where(Customer.education == education)
    if min_age is not None:
        query = query.where(Customer.age >= min_age)
    if max_age is not None:
        query = query.where(Customer.age <= max_age)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()

    # Apply stable ordering
    ordered_query = query.order_by(
        nulls_last(desc(Customer.subscription_probability)),
        Customer.customer_id
    )

    # Paginate
    offset = (page - 1) * page_size
    customers = session.exec(ordered_query.offset(offset).limit(page_size)).all()

    total_pages = ceil(total / page_size) if total > 0 else 1
    
    return PaginatedCustomerResponse(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        items=customers
    )

@app.get("/customers/{customer_id}")
def get_customer(
    customer_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

# One-time prediction trigger endpoint (protected)
@app.post("/predict")
def trigger_prediction(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    run_prediction_and_update_db(session)
    return {"message": "Prediction completed and database updated."}