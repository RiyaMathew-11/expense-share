# Expense Sharing Application

A FastAPI-based expense sharing application that helps users manage and split expenses, and generate balance sheets. Built with FastAPI and Supabase for the backend. Currently, this contains only backend.

## Features

- User Management
    - Create and manage users (edit user details)
    - View user details
- Expense Management
    - Add expenses with different split types:
        - Equal Split
        - Exact Amount Split
        - Percentage Split
- Balance Sheet
    - View overall balances between users
    - Download balance sheets

## Tech Stack

- **Backend**: FastAPI
- **Database**: Supabase (Postgres)
- **PDF Generation**: ReportLab
- **Dependencies Management**: Pipenv

## Project Structure
```
expense-share/
├── backend/
│   ├── api/
│   │   ├── balance_sheet.py
│   │   ├── expenses.py
│   │   └── users.py
│   ├── helpers/
│   │   └── utils.py
│   ├── schema/
│   │   ├── expense.py
│   │   └── user.py
│   ├── config.py
│   ├── database.py
│   └── main.py
├── supabase/
│   ├── config.toml
│   └── seed.sql
├── Pipfile
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.10 or higher
- Pipenv
- Supabase account


### 1. Project Setup

1. Clone the repository

```bash
git clone https://github.com/RiyaMathew-11/expense-share.git
```
2. Install dependencies 

```bash
pipenv install
```

3. Setup supabase (instructions included below)
3. Create a `.env` file in the backend directory

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```
4. Start the server

```bash
cd backend
uvicorn main:app --reload
```



### 2. Supabase Setup

1. Start supabase:
    ```bash
    supabase start
    ```
2. Open supabase studio via Studio URL
3. Run the database schema to create needed tables and RLS
   ```sql
   -- Copy contents from supabase/seed.sql and run in Supabase SQL editor
   ```

Note: For this case, anonymous access is given to all
