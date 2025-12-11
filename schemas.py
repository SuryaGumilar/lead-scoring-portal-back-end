from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CustomerItem(BaseModel):
    customer_id: int
    name: str
    phone_number: str
    age: int
    contact_method: str
    subscription_probability: Optional[float] = None
    
    class Config:
        from_attributes = True  # Enables conversion from ORM objects

class ProbabilityDistributionItem(BaseModel):
    category: str
    count: int

class JobStatsItem(BaseModel):
    job: str
    avg_probability: float

class AgeBinItem(BaseModel):
    age_bin: str
    avg_probability: float

class WeekdayItem(BaseModel):
    weekday: str
    avg_probability: float

class MonthItem(BaseModel):
    month: str
    avg_probability: float

class ChartsResponse(BaseModel):
    probability_distribution: List[ProbabilityDistributionItem]
    job_stats: List[JobStatsItem]
    age_stats: List[AgeBinItem]
    weekday_stats: List[WeekdayItem]
    seasonal_stats: List[MonthItem]

class DashboardResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    charts: ChartsResponse
    items: List[CustomerItem]
    
    class Config:
        from_attributes = True