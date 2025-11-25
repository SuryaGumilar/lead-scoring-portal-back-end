from pydantic import BaseModel
from typing import List, Optional

class CustomerItem(BaseModel):
    customer_id: int
    name: str
    phone_number: str
    age: int
    contact_method: str
    subscription_probability: Optional[float] = None

    class Config:
        from_attributes = True

class PaginatedCustomerResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    items: List[CustomerItem]