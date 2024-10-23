from uuid import UUID
from collections import defaultdict
from fastapi import APIRouter, HTTPException
from schema.expense import (
    ExpenseCreate, 
    ExpenseResponse, 
    SplitType
)
from database import supabase

router = APIRouter()

@router.post("/add-expense", response_model=ExpenseResponse)
async def create_expense(expense: ExpenseCreate):
    try:
        # splits based on split_type
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

        # Creating splits
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
                else:  # for percentage splits
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
    
@router.get("/balance-sheet")
async def get_balance_sheet():
    try:
        users = get_users()
        expenses = get_expenses().data
        splits = get_splits().data
        
        balances = calculate_balances(expenses, splits)
        formatted_balances = format_balances(balances, users)
        
        return formatted_balances

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error generating balance sheet: {str(e)}"
        )

@router.get("/e/{user_id}")
async def get_user_balance_sheet(user_id: UUID):
    try:
        expenses = get_expenses().data
        splits = get_splits().data
        user = get_users()[str(user_id)]
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        paid, owed, balances_by_user = calculate_user_expense_details(expenses, splits, user_id)

        detailed_balances = [
            {
                "user": {"id": user_id, "name": user},
                "total_amount": abs(user_data["total"]),
                "direction": "owes_you" if user_data["total"] > 0 else "you_owe",
                "expense_details": [
                    {
                        "expense_name": expense['expense_name'],
                        "amount": expense['split_amount'],
                        "type": "owes_you" if user_data["total"] > 0 else "you_owe"
                    }
                    for expense in sorted(user_data["expenses"], key=lambda x: x['date'], reverse=True)
                ]
            }
            for user_id, user_data in balances_by_user.items()
            if abs(user_data["total"]) > 0.01
        ]

        return {
            "summary": {
                "total_paid": paid,
                "total_owed": owed,
                "net_balance": paid - owed
            },
            "detailed_balances": detailed_balances
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error generating user balance sheet: {str(e)}"
        )

@router.get("/e/all")
async def get_overall_expenses():
    try:
        users = get_users()
        expenses_response = get_expenses()
        splits_response = get_splits()

        expense_summaries = []
        total_amount = 0

        for expense in expenses_response.data:
            expense_splits = [
                split for split in splits_response.data 
                if split['expense_id'] == expense['id']
            ]

            split_details = []
            for split in expense_splits:
                split_details.append({
                    "user_name": users[split['user_id']],
                    "amount": split['amount'],
                    "percentage": split['percentage'],
                    "type": "paid" if split['user_id'] == expense['created_by'] else "owes"
                })

            # Add to total amount
            total_amount += expense['amount']

            # Create expense summary
            expense_summaries.append({
                "expense_id": expense['id'],
                "name": expense['name'],
                "description": expense['description'],
                "amount": expense['amount'],
                "date": expense['created_at'],
                "split_type": expense['split_type'],
                "paid_by": users[expense['created_by']],
                "splits": split_details
            })

        # Sort expenses by date (most recent first)
        expense_summaries.sort(key=lambda x: x['date'], reverse=True)

        return {
            "overview": {
                "total_expenses": len(expense_summaries),
                "total_amount": total_amount,
                "average_amount": round(total_amount / len(expense_summaries), 2) if expense_summaries else 0
            },
            "expenses": expense_summaries
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error getting overall expenses: {str(e)}"
        )

def get_users():
    users_response = supabase.table('users').select('*').execute()
    return {user['id']: user['name'] for user in users_response.data}

def get_expenses():
    return supabase.table('expenses').select('*').execute()

def get_splits():
    return supabase.table('expense_splits').select('*').execute()

def calculate_balances(expenses, splits, user_id=None):
    balances = defaultdict(lambda: defaultdict(float))
    for expense in expenses:
        expense_splits = [split for split in splits if split['expense_id'] == expense['id']]
        payer_id = expense['created_by']
        
        for split in expense_splits:
            split_user_id = split['user_id']
            if user_id is None or split_user_id == user_id or payer_id == user_id:
                if split_user_id != payer_id:
                    balances[split_user_id][payer_id] += split['amount']
    
    return balances

def format_balances(balances, users):
    formatted_balances = []
    processed_pairs = set()
    
    for user1, user_balances in balances.items():
        for user2, amount in user_balances.items():
            pair_key = tuple(sorted([user1, user2]))
            if pair_key not in processed_pairs and abs(amount) > 0.01:
                processed_pairs.add(pair_key)
                formatted_balances.append({
                    "from_user": {"id": user1, "name": users[user1]},
                    "to_user": {"id": user2, "name": users[user2]},
                    "amount": abs(amount),
                    "direction": "owes"
                })
    
    return formatted_balances

def calculate_user_expense_details(expenses, splits, user_id):
    paid = 0
    owed = 0
    balances_by_user = defaultdict(lambda: {"total": 0, "expenses": []})
    
    for expense in expenses:
        expense_splits = [s for s in splits if s['expense_id'] == expense['id']]
        
        if expense['created_by'] == str(user_id):
            paid += expense['amount']
            for split in expense_splits:
                if split['user_id'] != str(user_id):
                    balances_by_user[split['user_id']]["total"] += split['amount']
                    balances_by_user[split['user_id']]["expenses"].append({
                        "expense_name": expense['name'],
                        "description": expense['description'],
                        "date": expense['created_at'],
                        "total_amount": expense['amount'],
                        "split_amount": split['amount'],
                        "split_type": expense['split_type']
                    })
        else:
            for split in expense_splits:
                if split['user_id'] == str(user_id):
                    owed += split['amount']
                    balances_by_user[expense['created_by']]["total"] -= split['amount']
                    balances_by_user[expense['created_by']]["expenses"].append({
                        "expense_name": expense['name'],
                        "description": expense['description'],
                        "date": expense['created_at'],
                        "total_amount": expense['amount'],
                        "split_amount": split['amount'],
                        "split_type": expense['split_type']
                    })
    
    return paid, owed, balances_by_user
