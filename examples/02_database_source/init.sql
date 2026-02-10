-- Create and populate sample employees table
CREATE TABLE IF NOT EXISTS employees (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    department  TEXT NOT NULL,
    title       TEXT NOT NULL,
    salary      INTEGER NOT NULL,
    hire_date   DATE NOT NULL
);

INSERT INTO employees (name, department, title, salary, hire_date) VALUES
    ('Alice Chen',    'Engineering', 'Senior Engineer',   120000, '2022-03-15'),
    ('Bob Wang',      'Engineering', 'Staff Engineer',    150000, '2020-08-01'),
    ('Carol Li',      'Engineering', 'Junior Engineer',    80000, '2024-06-10'),
    ('David Lin',     'Marketing',   'Marketing Manager', 110000, '2021-01-20'),
    ('Eva Huang',     'Marketing',   'Content Specialist', 75000, '2023-09-01'),
    ('Frank Wu',      'Sales',       'Sales Director',    140000, '2019-11-15'),
    ('Grace Tsai',    'Sales',       'Account Executive',  90000, '2023-02-28'),
    ('Henry Liu',     'Sales',       'Account Executive',  85000, '2024-01-10'),
    ('Iris Chang',    'HR',          'HR Manager',        105000, '2021-07-01'),
    ('Jack Yang',     'HR',          'Recruiter',          70000, '2024-03-15'),
    ('Karen Su',      'Engineering', 'Engineering Manager',135000, '2020-05-20'),
    ('Leo Hsu',       'Engineering', 'Senior Engineer',   125000, '2021-12-01');
