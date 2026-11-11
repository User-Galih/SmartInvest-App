from pydantic import BaseModel
from typing import Optional


class PortfolioRequest(BaseModel):
    index_choice: str
    start_date: str
    end_date: str
    investment_amount: float
    model_choice: Optional[str] = "ALL"
    gemini_api_key: Optional[str] = None


class IHSGRequest(BaseModel):
    index_choice: str
    start_date: str
    end_date: str
    investment_amount: float
    user_id: Optional[str] = None
    gemini_api_key: Optional[str] = None
