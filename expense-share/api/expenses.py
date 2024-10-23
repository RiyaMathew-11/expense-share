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

@router.post("/expenses", response_model=ExpenseResponse)
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
        users_response = supabase.table('users').select('*').execute()
        users = {user['id']: user['name'] for user in users_response.data}
        expenses_response = supabase.table('expenses').select('*').execute()
        splits_response = supabase.table('expense_splits').select('*').execute()

        balances = defaultdict(lambda: defaultdict(float))
        
        # Calculate balances
        for expense in expenses_response.data:
            expense_splits = [
                split for split in splits_response.data 
                if split['expense_id'] == expense['id']
            ]
            
            payer_id = expense['created_by']
            
            for split in expense_splits:
                user_id = split['user_id']
                if user_id != payer_id:  # Skip if user is the payer
                    balances[user_id][payer_id] += split['amount']

        # Format balances - Modified this part
        formatted_balances = []
        processed_pairs = set()  # To avoid duplicate processing

        for user1, user_balances in balances.items():
            for user2, amount in user_balances.items():
                pair_key = tuple(sorted([user1, user2]))
                if pair_key not in processed_pairs and abs(amount) > 0.01:
                    processed_pairs.add(pair_key)
                    formatted_balances.append({
                        "from_user": {
                            "id": user1,
                            "name": users[user1]
                        },
                        "to_user": {
                            "id": user2,
                            "name": users[user2]
                        },
                        "amount": abs(amount),
                        "direction": "owes"  # Since we're only storing positive owes amounts
                    })

        return formatted_balances

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error generating balance sheet: {str(e)}"
        )

@router.get("/balance-sheet/u/{user_id}")
async def get_user_balance_sheet(user_id: UUID):
    try:
        
        user_response = supabase.table('users').select('*').eq('id', str(user_id)).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")

        # Get all expenses where user is involved
        expenses_response = supabase.table('expenses').select('*').execute()
        splits_response = supabase.table('expense_splits').select('*').execute()

        # Get all involved users
        involved_users = set()
        for expense in expenses_response.data:
            involved_users.add(expense['created_by'])
            expense_splits = [s for s in splits_response.data if s['expense_id'] == expense['id']]
            for split in expense_splits:
                involved_users.add(split['user_id'])

        users_response = supabase.table('users').select('*').in_('id', list(involved_users)).execute()
        users = {user['id']: user['name'] for user in users_response.data}

        # Calculate balances with expense details
        paid = 0
        owed = 0
        balances_by_user = defaultdict(lambda: {
            "total": 0,
            "expenses": []
        })

        for expense in expenses_response.data:
            expense_splits = [s for s in splits_response.data if s['expense_id'] == expense['id']]
            
            if expense['created_by'] == str(user_id):
                # User paid for this expense
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
                # User owes money in another user's expense
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
        # Detailed balances with user, amount, owe-direction and minimal expense details
        detailed_balances = [
            {
                "user": {
                    "id": user_id,
                    "name": users[user_id]
                },
                "total_amount": abs(user_data["total"]),
                "direction": "owes_you" if user_data["total"] > 0 else "you_owe",
                "expense_details": [
                    {
                        "expense_name": expense['expense_name'],
                        "amount": expense['split_amount'],
                        "type": "owes_you" if user_data["total"] > 0 else "you_owe"
                    }
                    for expense in sorted(
                        user_data["expenses"],
                        key=lambda x: x['date'],
                        reverse=True
                    )
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

@router.get("/balance-sheet/e/all")
async def get_overall_expenses():
    try:
        users_response = supabase.table('users').select('*').execute()
        users = {user['id']: user['name'] for user in users_response.data}
        expenses_response = supabase.table('expenses').select('*').execute()
        splits_response = supabase.table('expense_splits').select('*').execute()

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
