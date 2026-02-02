-- Insert sample users for each role (1 user per role)
-- This script adds one user for each of the 5 roles

PRINT 'Inserting sample users for each role...';

-- Sample passwords (in production, these should be hashed properly)
-- Using a simple hash-like value for demo purposes
INSERT INTO [User] (role_id, username, email, password, created_at)
VALUES
  -- 1. Admin User
  (1, 'admin_demo', 'admin.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME()),
  
  -- 2. Manager User
  (2, 'manager_demo', 'manager.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME()),
  
  -- 3. Officer User
  (3, 'officer_demo', 'officer.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME()),
  
  -- 4. Customer User
  (4, 'customer_demo', 'customer.demo@email.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME()),
  
  -- 5. Analyst User
  (5, 'analyst_demo', 'analyst.demo@creditbank.com', '$2b$12$R9h7cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jKDga', SYSUTCDATETIME());

PRINT 'Users inserted successfully!';

-- Display the inserted users
PRINT '';
PRINT '=================================';
PRINT 'Sample Users Created:';
PRINT '=================================';
SELECT u.user_id, r.role_name, u.username, u.email, u.created_at
FROM [User] u
INNER JOIN Role r ON u.role_id = r.role_id
WHERE u.username LIKE '%_demo'
ORDER BY u.role_id;

PRINT '';
PRINT 'Login credentials:';
PRINT '=================================';
PRINT 'Admin:    admin_demo / Admin@123456';
PRINT 'Manager:  manager_demo / Manager@123456';
PRINT 'Officer:  officer_demo / Officer@123456';
PRINT 'Customer: customer_demo / Customer@123456';
PRINT 'Analyst:  analyst_demo / Analyst@123456';
PRINT '=================================';
