# backend/database.py
import mysql.connector
from mysql.connector import Error
import bcrypt # 用于密码哈希
from backend.db_config import DB_CONFIG # 引入数据库配置

# --- 数据库连接辅助函数 ---
def create_connection():
    """创建并返回一个数据库连接对象"""
    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        # print("成功连接到MySQL数据库") # 开发时可以取消注释
    except Error as e:
        print(f"连接MySQL时发生错误: '{e}'")
    return connection

def execute_query(query, params=None, fetch_one=False, fetch_all=False, is_modify=False, dictionary_cursor=True):
    """
    通用查询执行函数
    :param query: SQL查询语句
    :param params: 查询参数 (元组)
    :param fetch_one: 是否获取单条记录
    :param fetch_all: 是否获取所有记录
    :param is_modify: 是否为修改操作 (INSERT, UPDATE, DELETE)
    :param dictionary_cursor: 是否使用字典类型的游标 (True 表示结果为字典列表, False 表示结果为元组列表)
    :return: 根据操作类型返回结果
    """
    connection = create_connection()
    if not connection:
        return None if is_modify or fetch_one else []

    cursor = None
    # 根据 dictionary_cursor 参数决定创建何种类型的游标
    if dictionary_cursor:
        cursor = connection.cursor(dictionary=True)
    else:
        cursor = connection.cursor() # 默认游标，返回元组

    result = None
    last_row_id = None
    row_count = None

    try:
        cursor.execute(query, params or ()) # params为空时传递空元组
        if is_modify:
            connection.commit()
            last_row_id = cursor.lastrowid
            row_count = cursor.rowcount
            print(f"修改查询执行成功，影响行数: {row_count}, 最后插入ID: {last_row_id}")
            result = last_row_id if query.strip().upper().startswith("INSERT") else row_count
        elif fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        # print("查询执行成功") # 开发时可以取消注释
    except Error as e:
        print(f"执行查询 '{query[:100]}...' 时发生错误: '{e}'")
        if is_modify and connection.is_connected():
            connection.rollback()
    finally:
        if connection.is_connected():
            if cursor:
                cursor.close()
            connection.close()
            # print("MySQL连接已关闭") # 开发时可以取消注释
    return result

# --- 用户管理函数 ---
def create_user(username, password, role='customer', full_name=None, email=None, phone=None):
    """创建新用户，密码会自动哈希处理"""
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    query = """
    INSERT INTO users (username, password_hash, role, full_name, email, phone)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = (username, hashed_password, role, full_name, email, phone)
    return execute_query(query, params, is_modify=True)

def get_user_by_username(username):
    """根据用户名获取用户信息"""
    query = "SELECT id, username, password_hash, role, full_name, email, phone, created_at, last_login FROM users WHERE username = %s"
    return execute_query(query, (username,), fetch_one=True, dictionary_cursor=True)

def get_user_by_id(user_id):
    """根据用户ID获取用户信息"""
    query = "SELECT id, username, password_hash, role, full_name, email, phone, created_at, last_login FROM users WHERE id = %s"
    # 注意：get_user_by_id 返回的 user 对象在 app.py 的 token_required 中被直接使用，
    # 它期望的是字典。所以这里 dictionary_cursor 保持 True。
    return execute_query(query, (user_id,), fetch_one=True, dictionary_cursor=True)


def verify_password(plain_password, hashed_password):
    """验证明文密码是否与哈希密码匹配"""
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

def update_user_last_login(user_id):
    """更新用户最后登录时间"""
    query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s"
    return execute_query(query, (user_id,), is_modify=True)

# --- 菜品管理函数 ---
def get_all_menu_items():
    """获取所有可用菜品信息，并包含分类名称"""
    query = """
    SELECT mi.id, mi.name, mi.description, mi.price, mi.image_url, mi.is_available, c.name as category_name
    FROM menu_items mi
    LEFT JOIN categories c ON mi.category_id = c.id
    WHERE mi.is_available = TRUE
    ORDER BY c.display_order, mi.name
    """
    return execute_query(query, fetch_all=True, dictionary_cursor=True)

def get_menu_item_by_id(item_id):
    """根据ID获取单个菜品信息，并包含分类名称"""
    query = """
    SELECT mi.id, mi.name, mi.description, mi.price, mi.category_id, mi.image_url, mi.is_available, c.name as category_name
    FROM menu_items mi
    LEFT JOIN categories c ON mi.category_id = c.id
    WHERE mi.id = %s
    """
    return execute_query(query, (item_id,), fetch_one=True, dictionary_cursor=True)

def add_menu_item(name, description, price, category_id, image_url=None, is_available=True):
    """添加新菜品"""
    query = """
    INSERT INTO menu_items (name, description, price, category_id, image_url, is_available)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = (name, description, price, category_id, image_url, is_available)
    return execute_query(query, params, is_modify=True)

# --- 订单管理函数 ---
def create_order(total_amount, items_data, user_id=None, customer_name="匿名用户", payment_method=None, delivery_address=None, notes=None):
    """
    创建新订单
    :param total_amount: 总金额
    :param items_data: 订单项列表, 每个项是 {'menu_item_id': id, 'quantity': qty, 'unit_price': price, 'subtotal': subtotal, 'special_requests': text}
    :param user_id: (可选) 用户ID
    :param customer_name: (可选) 顾客名，如果user_id为空则使用此值
    :param payment_method: (可选) 支付方式
    :param delivery_address: (可选) 配送地址
    :param notes: (可选) 订单备注
    :return: 新订单的ID，如果失败返回None
    """
    connection = create_connection()
    if not connection:
        return None
    
    cursor = connection.cursor() # 对于多步事务，手动管理游标和提交/回滚
    order_id = None
    try:
        # 1. 插入订单主表
        order_query = """
        INSERT INTO orders (user_id, customer_name, total_amount, payment_method, delivery_address, notes, status, payment_status)
        VALUES (%s, %s, %s, %s, %s, %s, 'pending', 'unpaid') 
        """
        actual_customer_name = customer_name
        if user_id:
            # 注意：这里调用 get_user_by_id，它内部使用 execute_query 并关闭连接。
            # 在一个事务中多次调用 execute_query 可能会导致问题或效率低下。
            # 更好的做法是，如果需要在事务中获取用户信息，应直接使用当前连接的游标。
            # 但为了保持模块化，暂时这样处理，但需注意其潜在影响。
            user_info_dict = get_user_by_id(user_id) # get_user_by_id 默认返回字典
            if user_info_dict:
                actual_customer_name = user_info_dict.get('full_name') or user_info_dict.get('username') or customer_name
        
        order_params = (user_id, actual_customer_name, total_amount, payment_method, delivery_address, notes)
        cursor.execute(order_query, order_params)
        order_id = cursor.lastrowid

        if not order_id:
            raise Exception("创建订单失败，未能获取订单ID")

        # 2. 插入订单详情表
        item_query = """
        INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price, subtotal, special_requests)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        order_items_to_insert = []
        for item in items_data:
            order_items_to_insert.append((
                order_id,
                item['menu_item_id'],
                item['quantity'],
                item['unit_price'], 
                item['subtotal'],
                item.get('special_requests', None)
            ))
        
        cursor.executemany(item_query, order_items_to_insert)
        
        connection.commit() # 事务提交
        print(f"订单 {order_id} 创建成功，包含 {len(order_items_to_insert)} 个订单项。")
        return order_id
    except Error as e:
        print(f"创建订单时发生数据库错误: '{e}'")
        if connection.is_connected():
            connection.rollback() # 事务回滚
        return None
    except Exception as ex: 
        print(f"创建订单时发生一般错误: '{ex}'")
        if connection.is_connected():
            connection.rollback()
        return None
    finally:
        if connection.is_connected():
            if cursor:
                cursor.close()
            connection.close()

def get_order_details_by_id(order_id):
    """获取单个订单的详细信息，包括订单项和用户信息(如果存在)"""
    order_query = """
    SELECT o.*, u.username as user_username, u.full_name as user_full_name, u.email as user_email, u.phone as user_phone
    FROM orders o
    LEFT JOIN users u ON o.user_id = u.id
    WHERE o.id = %s
    """
    order_data = execute_query(order_query, (order_id,), fetch_one=True, dictionary_cursor=True)
    
    if not order_data:
        return None
    
    items_query = """
    SELECT oi.quantity, oi.unit_price, oi.subtotal, oi.special_requests, mi.name as item_name, mi.image_url as item_image_url
    FROM order_items oi
    JOIN menu_items mi ON oi.menu_item_id = mi.id
    WHERE oi.order_id = %s
    """
    order_items = execute_query(items_query, (order_id,), fetch_all=True, dictionary_cursor=True)
    
    order_data['items'] = order_items
    return order_data

def get_orders_by_user_id(user_id, page=1, per_page=10):
    """获取特定用户的所有订单（分页）"""
    offset = (page - 1) * per_page
    query = """
    SELECT o.id, o.order_time, o.total_amount, o.status, o.payment_status
    FROM orders o
    WHERE o.user_id = %s
    ORDER BY o.order_time DESC
    LIMIT %s OFFSET %s
    """
    orders = execute_query(query, (user_id, per_page, offset), fetch_all=True, dictionary_cursor=True)
    
    count_query = "SELECT COUNT(*) as total_orders FROM orders WHERE user_id = %s"
    total_orders_result = execute_query(count_query, (user_id,), fetch_one=True, dictionary_cursor=True)
    total_orders = total_orders_result['total_orders'] if total_orders_result else 0
    
    return {"orders": orders, "total_orders": total_orders, "page": page, "per_page": per_page}

def get_all_orders_admin(page=1, per_page=10, status_filter=None, user_id_filter=None, sort_by='order_time', sort_order='DESC'):
    """管理员获取所有订单（分页，可筛选，可排序）"""
    offset = (page - 1) * per_page
    base_query = """
    SELECT o.id, o.order_time, o.total_amount, o.status, o.payment_status, o.customer_name, 
           u.username as user_username, u.id as user_id_from_user_table 
           /* Aliased user_id to avoid conflict if orders table also has user_id directly in select */
    FROM orders o
    LEFT JOIN users u ON o.user_id = u.id
    """
    count_base_query = "SELECT COUNT(*) as total_orders FROM orders o LEFT JOIN users u ON o.user_id = u.id"
    conditions = []
    params = []

    if status_filter:
        conditions.append("o.status = %s")
        params.append(status_filter)
    if user_id_filter:
        try: # 确保 user_id_filter 是整数
            user_id_val = int(user_id_filter)
            conditions.append("o.user_id = %s")
            params.append(user_id_val)
        except ValueError:
            print(f"警告: 无效的用户ID筛选值 '{user_id_filter}', 已忽略。")
            pass # 或者可以返回错误
    
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)
        base_query += where_clause
        count_base_query += where_clause

    allowed_sort_by = ['order_time', 'total_amount', 'status', 'id']
    # 检查 sort_by 是否在允许的列名中，防止SQL注入
    db_sort_by = 'o.order_time' # 默认值
    if sort_by in allowed_sort_by :
        db_sort_by = f"o.{sort_by}"
    elif sort_by == 'user_username' : # 允许按用户名排序
        db_sort_by = "u.username"
    else:
        print(f"警告: 不允许的排序字段 '{sort_by}', 使用默认排序 'o.order_time'.")


    if sort_order.upper() not in ['ASC', 'DESC']:
        sort_order_safe = 'DESC' 
    else:
        sort_order_safe = sort_order.upper()

    base_query += f" ORDER BY {db_sort_by} {sort_order_safe} LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    
    orders = execute_query(base_query, tuple(params), fetch_all=True, dictionary_cursor=True)
    
    # 对于COUNT查询，不需要LIMIT和OFFSET的参数
    count_params = tuple(params[:-2]) if len(params) > 1 else ()
    total_orders_result = execute_query(count_base_query, count_params, fetch_one=True, dictionary_cursor=True)
    total_orders = total_orders_result['total_orders'] if total_orders_result else 0
    
    return {"orders": orders, "total_orders": total_orders, "page": page, "per_page": per_page}


def update_order_status_admin(order_id, new_status, admin_user_id):
    """管理员更新订单状态，并记录到历史表"""
    connection = create_connection()
    if not connection:
        return False
    
    cursor = connection.cursor(dictionary=True) # 使用字典游标
    try:
        cursor.execute("SELECT status FROM orders WHERE id = %s", (order_id,))
        order = cursor.fetchone()
        if not order:
            print(f"更新状态失败：未找到订单ID {order_id}")
            return False
        old_status = order['status']

        if old_status == new_status:
            print(f"订单 {order_id} 状态未改变，仍为 {new_status}")
            return True 

        cursor.execute("UPDATE orders SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (new_status, order_id))
        
        history_query = """
        INSERT INTO order_status_history (order_id, previous_status, new_status, changed_by_user_id, notes)
        VALUES (%s, %s, %s, %s, %s)
        """
        notes_for_history = f"管理员 (ID: {admin_user_id}) 将状态从 '{old_status}' 修改为 '{new_status}'."
        cursor.execute(history_query, (order_id, old_status, new_status, admin_user_id, notes_for_history))
        
        connection.commit()
        print(f"订单 {order_id} 状态已由管理员 {admin_user_id} 从 {old_status} 更新为 {new_status}")
        return True
    except Error as e:
        print(f"管理员更新订单 {order_id} 状态时发生数据库错误: '{e}'")
        if connection.is_connected():
            connection.rollback()
        return False
    finally:
        if connection.is_connected():
            if cursor:
                cursor.close()
            connection.close()

# --- 分类管理函数 ---
def get_all_categories():
    """获取所有菜品分类"""
    query = "SELECT id, name, description, display_order FROM categories ORDER BY display_order, name"
    return execute_query(query, fetch_all=True, dictionary_cursor=True)

def get_category_by_id(category_id):
    """根据ID获取单个分类信息"""
    query = "SELECT id, name, description, display_order FROM categories WHERE id = %s"
    return execute_query(query, (category_id,), fetch_one=True, dictionary_cursor=True)


if __name__ == '__main__':
    print("测试数据库模块 (database.py)...")
    # ... (之前的测试代码可以保留或根据需要调整) ...
    # 例如，测试 get_all_menu_items
    # print("\n--- 测试获取所有菜单项 ---")
    # all_items = get_all_menu_items()
    # if all_items:
    #     print(f"成功获取 {len(all_items)} 个菜单项:")
    #     for item in all_items[:2]: # 打印前两个
    #         print(item)
    # else:
    #     print("未能获取到菜单项或菜单为空。")
    pass
