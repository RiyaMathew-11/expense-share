from database import supabase
from collections import defaultdict

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
