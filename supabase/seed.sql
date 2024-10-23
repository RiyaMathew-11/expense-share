-- Create users table
create table public.users (
    id uuid default gen_random_uuid() primary key,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    email text unique not null,
    name text not null,
    mobile text unique not null
);

-- Enable RLS (Row Level Security)
alter table public.users enable row level security;

-- Create policy to allow anonymous access (for testing)
create policy "Enable anonymous access"
    on users
    for all  -- this allows all operations (select, insert, update, delete)
    to anon
    using (true)
    with check (true);

-- split types enum
create type split_type as enum ('EQUAL', 'EXACT', 'PERCENTAGE');

-- Expenses table
create table public.expenses (
    id uuid default gen_random_uuid() primary key,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    name text not null,
    description text,
    amount decimal(10,2) not null,
    created_by uuid references public.users(id) not null,
    split_type split_type not null
);

-- Expense splits table
create table public.expense_splits (
    id uuid default gen_random_uuid() primary key,
    expense_id uuid references public.expenses(id) not null,
    user_id uuid references public.users(id) not null,
    amount decimal(10,2),  -- for Exact split
    percentage decimal(5,2), -- for Percentage split
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Add RLS policies
alter table public.expenses enable row level security;
alter table public.expense_splits enable row level security;

-- Policies for expenses
create policy "Enable anonymous access to expenses"
    on expenses for all
    to anon
    using (true)
    with check (true);

-- Policies for expense_splits
create policy "Enable anonymous access to expense_splits"
    on expense_splits for all
    to anon
    using (true)
    with check (true);