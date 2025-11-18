from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    user_id: int = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password: str

class Customer(SQLModel, table=True):
    customer_id: int = Field(default=None, primary_key=True, sa_type="BIGINT")
    name: str
    phone_number: str
    age: int = Field(sa_type="SMALLINT")
    job: str
    marital_status: str
    education: str
    has_default_credit: str
    has_housing_loan: str
    has_personal_loan: str
    contact_method: str
    last_contact_month: str
    last_contact_weekday: str
    last_call_duration_sec: int
    current_campaign_contacts: int = Field(sa_type="SMALLINT")
    days_since_last_campaign: int = Field(sa_type="SMALLINT")
    previous_campaign_contacts: int = Field(sa_type="SMALLINT")
    previous_campaign_outcome: str
    employment_variation_rate: float = Field(nullable=True)
    consumer_price_index: float = Field(nullable=True)
    consumer_confidence_index: float = Field(nullable=True)
    euribor_3m_rate: float = Field(nullable=True)
    number_of_employed: int = Field(nullable=True)
    subscription_probability: Optional[float] = Field(default=None, sa_type="REAL")