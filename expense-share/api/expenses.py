from fastapi import APIRouter, HTTPException
from schema.expense import (
    ExpenseCreate, 
    ExpenseResponse, 
    SplitType
)
from database import supabase

router = APIRouter()

@router.post("/expenses", response_model=ExpenseResponse)
async def create_expense(expense: ExpenseCreate):
    try:
        # Validate splits based on split_type
        if not expense.splits:
            raise HTTPException(
                status_code=400,
                detail="At least one split is required"
            )

        if expense.split_type == SplitType.PERCENTAGE:
            total_percentage = sum(split.percentage or 0 for split in expense.splits)
            if abs(total_percentage - 100) > 0.01:
                raise HTTPException(
                    status_code=400, 
                    detail="Percentage splits must sum to 100%"
                )
        elif expense.split_type == SplitType.EXACT:
            total_amount = sum(split.amount or 0 for split in expense.splits)
            if abs(total_amount - expense.amount) > 0.01:
                raise HTTPException(
                    status_code=400, 
                    detail="Exact splits must sum to total amount"
                )

        # Create an expense
        expense_data = {
            "name": expense.name,
            "description": expense.description,
            "amount": float(expense.amount),
            "created_by": str(expense.created_by),
            "split_type": expense.split_type
        }

        expense_response = supabase.table('expenses').insert(expense_data).execute()
        
        if not expense_response.data:
            raise HTTPException(
                status_code=400,
                detail="Failed to create expense"
            )
        
        created_expense = expense_response.data[0]
        expense_id = created_expense['id']

        # Create splits
        splits_data = []
        if expense.split_type == SplitType.EQUAL:
            split_amount = float(expense.amount) / len(expense.splits)
            for split in expense.splits:
                splits_data.append({
                    "expense_id": expense_id,
                    "user_id": str(split.user_id),
                    "amount": split_amount
                })
        else:
            for split in expense.splits:
                split_data = {
                    "expense_id": expense_id,
                    "user_id": str(split.user_id)
                }
                if expense.split_type == SplitType.EXACT:
                    split_data["amount"] = float(split.amount)
                else:  # for percentage
                    split_data["percentage"] = float(split.percentage)
                    split_data["amount"] = float(expense.amount) * float(split.percentage) / 100
                splits_data.append(split_data)

        splits_response = supabase.table('expense_splits').insert(splits_data).execute()

        return {
            **created_expense,
            "splits": splits_response.data
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error creating expense: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Error creating expense: {str(e)}"
        )
    