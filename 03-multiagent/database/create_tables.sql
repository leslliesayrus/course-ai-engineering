DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS products;

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    preco DECIMAL(10,2) NOT NULL,
    custo DECIMAL(10,2) NOT NULL
);

CREATE TABLE inventory (
    produto_id INT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    quantidade INT NOT NULL DEFAULT 0
);

CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    produto_id INT NOT NULL REFERENCES products(id),
    quantidade INT NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);