from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import List, Optional
from datetime import timedelta
from sqlalchemy import desc, nulls_last
from math import ceil

from models import User, Customer
from database import engine, get_session, create_db_and_tables
from auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from prediction import run_prediction_and_update_db

app = FastAPI(title="ML Prediction Service")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

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
@app.get("/", response_model=List[dict])
def list_customers(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    name: Optional[str] = Query(None),
    job: Optional[str] = Query(None),
    marital: Optional[str] = Query(None),
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
    if marital:
        query = query.where(Customer.marital == marital)
    if education:
        query = query.where(Customer.education == education)
    if min_age is not None:
        query = query.where(Customer.age >= min_age)
    if max_age is not None:
        query = query.where(Customer.age <= max_age)

    # Get total count
    total = session.exec(select([query.count()])).one()

    # Apply stable ordering: y_percentage DESC, NULLs last, then by customer_id
    ordered_query = query.order_by(
        nulls_last(desc(Customer.y_percentage)),
        Customer.customer_id
    )

    # Paginate
    offset = (page - 1) * page_size
    customers = session.exec(ordered_query.offset(offset).limit(page_size)).all()

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": ceil(total / page_size) if total else 1,
        "items": [
            {
                "name": c.name,
                "age": c.age,
                "phone_number": c.phone_number,
                "y_percentage": c.y_percentage
            }
            for c in customers
        ]
    }

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