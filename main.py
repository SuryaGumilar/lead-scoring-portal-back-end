from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from sqlalchemy import func, case, and_, or_, desc, nulls_last
from sqlalchemy.sql import expression
from typing import List, Optional, Tuple, Dict
from datetime import timedelta, datetime
from sqlalchemy import desc, nulls_last, func
from math import ceil
from schemas import (
    DashboardResponse, 
    CustomerItem,
    ChartsResponse,
    ProbabilityDistributionItem,
    JobStatsItem,
    AgeBinItem,
    WeekdayItem,
    MonthItem
)

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

WEEKDAY_ORDER = ["mon", "tue", "wed", "thu", "fri"]
MONTH_ORDER = ["jan", "feb", "mar", "apr", "may", "jun", 
               "jul", "aug", "sep", "oct", "nov", "dec"]

def build_filter_conditions(
    name: Optional[str] = None,
    job: Optional[str] = None,
    marital_status: Optional[str] = None,
    education: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None
) -> list:
    """Build SQLAlchemy filter conditions from query parameters"""
    conditions = []
    if name:
        conditions.append(Customer.name.icontains(name))
    if job:
        conditions.append(Customer.job.icontains(job))
    if marital_status:
        conditions.append(Customer.marital_status == marital_status)
    if education:
        conditions.append(Customer.education == education)
    if min_age is not None:
        conditions.append(Customer.age >= min_age)
    if max_age is not None:
        conditions.append(Customer.age <= max_age)
        
    return conditions

@app.get("/", response_model=DashboardResponse)
def get_dashboard(
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
    # Build shared filter conditions
    filters = build_filter_conditions(name, job, marital_status, education, min_age, max_age)

    # Get total count for pagination
    count_query = select(func.count()).select_from(Customer)
    for condition in filters:
        count_query = count_query.where(condition)
    total = session.exec(count_query).one()
    total_pages = ceil(total / page_size) if total > 0 else 1

    # Get paginated customer records
    base_query = select(Customer)
    for condition in filters:
        base_query = base_query.where(condition)

    ordered_query = base_query.order_by(
        nulls_last(desc(Customer.subscription_probability)),
        Customer.customer_id
    )

    offset = (page - 1) * page_size
    customers = session.exec(
        ordered_query.offset(offset).limit(page_size)
    ).all()

    # Generate chart data from FULL filtered dataset
    charts = _generate_chart_data(session, filters)

    # Convert SQLModel objects to Pydantic models
    customer_items = [
        CustomerItem(
            customer_id=c.customer_id,
            name=c.name,
            phone_number=c.phone_number,
            age=c.age,
            contact_method=c.contact_method,
            subscription_probability=round(c.subscription_probability, 3) if c.subscription_probability is not None else None
        )
        for c in customers
    ]

    # Create chart response with proper Pydantic models
    charts_response = ChartsResponse(
        probability_distribution=[
            ProbabilityDistributionItem(
                category=item["category"], 
                count=item["count"]
            ) for item in charts["probability_distribution"]
        ],
        job_stats=[
            JobStatsItem(
                job=item["job"],
                avg_probability=item["avg_probability"]
            ) for item in charts["job_stats"]
        ],
        age_stats=[
            AgeBinItem(
                age_bin=item["age_bin"],
                avg_probability=item["avg_probability"]
            ) for item in charts["age_stats"]
        ],
        weekday_stats=[
            WeekdayItem(
                weekday=item["weekday"],
                avg_probability=item["avg_probability"]
            ) for item in charts["weekday_stats"]
        ],
        seasonal_stats=[
            MonthItem(
                month=item["month"],
                avg_probability=item["avg_probability"]
            ) for item in charts["seasonal_stats"]
        ]
    )

    # Construct final response
    return DashboardResponse(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        charts=charts_response,
        items=customer_items
    )

def _generate_chart_data(session: Session, filters: list) -> Dict[str, List[Dict]]:
    """Generate all chart data from the full filtered dataset"""
    # Base conditions for charts (non-null probabilities only)
    chart_conditions = [
        Customer.subscription_probability.isnot(None),
        *filters
    ]
    
    # 1. Probability Distribution (Donut Chart)
    high_count = func.sum(case(
        (Customer.subscription_probability >= 70, 1),
        else_=0
    )).label("high")
    
    medium_count = func.sum(case(
        (and_(
            Customer.subscription_probability >= 30,
            Customer.subscription_probability < 70
        ), 1),
        else_=0
    )).label("medium")
    
    low_count = func.sum(case(
        (Customer.subscription_probability < 30, 1),
        else_=0
    )).label("low")
    
    prob_dist_query = select(high_count, medium_count, low_count).where(*chart_conditions)
    high, medium, low = session.exec(prob_dist_query).first()
    prob_distribution = [
        {"category": "High", "count": high or 0},
        {"category": "Medium", "count": medium or 0},
        {"category": "Low", "count": low or 0}
    ]

    # 2. Job Stats (Horizontal Bar Chart) - Top 5 jobs by avg probability
    job_stats_query = (
        select(
            Customer.job,
            func.avg(Customer.subscription_probability).label("avg_prob"),
            func.count().label("count")
        )
        .where(*chart_conditions)
        .group_by(Customer.job)
        .having(func.count() >= 3)  # Minimum 3 records per job
        .order_by(desc("avg_prob"))
        .limit(5)
    )
    job_results = session.exec(job_stats_query).all()
    job_stats = [
        {
            "job": job,
            "avg_probability": round(float(avg_prob), 1)
        }
        for job, avg_prob, _ in job_results
    ]

    # 3. Age Stats (Histogram) - 10-year bins
    bin_expr = (func.floor(Customer.age / 10) * 10).label("age_bin_start")
    age_stats_query = (
        select(
            bin_expr,
            func.avg(Customer.subscription_probability).label("avg_prob"),
            func.count().label("count")
        )
        .where(*chart_conditions)
        .group_by("age_bin_start")
        .order_by("age_bin_start")
    )
    age_results = session.exec(age_stats_query).all()
    age_stats = [
        {
            "age_bin": f"{int(start)}-{int(start)+9}",
            "avg_probability": round(float(avg_prob), 1)
        }
        for start, avg_prob, _ in age_results
        if start is not None and avg_prob is not None
    ]

    # 4. Weekday Stats (Column Chart) - Chronological order
    weekday_stats_query = (
        select(
            Customer.last_contact_weekday,
            func.avg(Customer.subscription_probability).label("avg_prob")
        )
        .where(*chart_conditions)
        .group_by(Customer.last_contact_weekday)
    )
    weekday_results = {row[0]: round(float(row[1]), 1) for row in session.exec(weekday_stats_query)}
    weekday_stats = [
        {
            "weekday": day, 
            "avg_probability": weekday_results.get(day, 0.0)
        }
        for day in WEEKDAY_ORDER
    ]

    # 5. Seasonal Stats (Line Chart) - Chronological order
    seasonal_stats_query = (
        select(
            Customer.last_contact_month,
            func.avg(Customer.subscription_probability).label("avg_prob")
        )
        .where(*chart_conditions)
        .group_by(Customer.last_contact_month)
    )
    seasonal_results = {row[0]: round(float(row[1]), 1) for row in session.exec(seasonal_stats_query)}
    seasonal_stats = [
        {
            "month": month,
            "avg_probability": seasonal_results.get(month, 0.0)
        }
        for month in MONTH_ORDER
    ]

    return {
        "probability_distribution": prob_distribution,
        "job_stats": job_stats,
        "age_stats": age_stats,
        "weekday_stats": weekday_stats,
        "seasonal_stats": seasonal_stats
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