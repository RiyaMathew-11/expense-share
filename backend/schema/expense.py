from pydantic import BaseModel, Field
from typing import List, Optional, Annotated
from datetime import datetime
from enum import Enum
from uuid import UUID
from decimal import Decimal

class SplitType(str, Enum):
    EQUAL = "EQUAL"
    EXACT = "EXACT"
    PERCENTAGE = "PERCENTAGE"

_amount = Annotated[Decimal, Field(max_digits=10, decimal_places=2)]
_percentage = Annotated[Decimal, Field(ge=0, le=100, decimal_places=2)]

class ExpenseSplitCreate(BaseModel):
    user_id: UUID
    amount: Optional[_amount] = None
    percentage: Optional[_percentage] = None

class ExpenseSplitResponse(BaseModel):
    id: UUID
    expense_id: UUID
    user_id: UUID
    amount: Optional[float]
    percentage: Optional[float]
    created_at: datetime

class ExpenseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    amount: _amount
    split_type: SplitType
    created_by: UUID
    splits: List[ExpenseSplitCreate]

class ExpenseResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    amount: float
    created_by: UUID
    split_type: SplitType
    created_at: datetime
    splits: List[ExpenseSplitResponse]
