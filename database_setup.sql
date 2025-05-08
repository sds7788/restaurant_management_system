-- database_setup.sql
-- 创建数据库 (如果不存在)
CREATE DATABASE IF NOT EXISTS restaurant_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE restaurant_db;

-- 菜品表
CREATE TABLE IF NOT EXISTS menu_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE, -- 菜品名称
    description TEXT,                   -- 描述
    price DECIMAL(10, 2) NOT NULL,      -- 价格
    category VARCHAR(50),               -- 分类 (如: 主菜, 汤, 饮品)
    image_url VARCHAR(255),             -- 图片链接 (可选)
    is_available BOOLEAN DEFAULT TRUE   -- 是否可供应
);

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(100),         -- 顾客名称 (简化处理, 实际可能需要用户表)
    order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 下单时间
    total_amount DECIMAL(10, 2) NOT NULL, -- 总金额
    status VARCHAR(20) DEFAULT 'pending' -- 订单状态 (pending, confirmed, preparing, completed, cancelled)
);

-- 订单详情表 (一个订单可以包含多个菜品)
CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    menu_item_id INT NOT NULL,
    quantity INT NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,   -- 小计金额
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
);

-- (可选) 用户表 (如果需要用户登录等功能)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL, -- 存储哈希后的密码
    role VARCHAR(20) DEFAULT 'customer'  -- 角色 (customer, admin)
);

-- 插入一些示例菜品数据
INSERT INTO menu_items (name, description, price, category, is_available) VALUES
('宫保鸡丁', '经典川菜，鸡肉、花生、辣椒等', 38.00, '主菜', TRUE),
('鱼香肉丝', '经典川菜，猪肉、木耳、笋丝等', 35.00, '主菜', TRUE),
('麻婆豆腐', '经典川菜，豆腐、牛肉末、豆瓣酱等', 28.00, '主菜', TRUE),
('酸辣汤', '开胃汤品', 18.00, '汤品', TRUE),
('米饭', '主食', 2.00, '主食', TRUE),
('可乐', '碳酸饮料', 5.00, '饮品', TRUE);

-- 插入一个示例用户 (密码是 'admin123' 的哈希，实际应使用安全的哈希算法)
-- 这里仅为示例，实际项目中密码哈希应在后端代码中生成
-- 例如 bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
-- INSERT INTO users (username, password_hash, role) VALUES
-- ('admin', '$2b$12$abcdefghijklmnopqrstuv', 'admin'); -- 这是一个bcrypt哈希的示例格式

COMMIT;
