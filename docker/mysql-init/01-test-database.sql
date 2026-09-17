-- A separate database for the API tests, on the same MySQL 8 server.
CREATE DATABASE IF NOT EXISTS pte_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON pte_test.* TO 'pte'@'%';
FLUSH PRIVILEGES;
