# backend/database.py
import mysql.connector
from mysql.connector import Error
from backend.db_config import DB_CONFIG # 引入数据库配置

# 创建数据库连接
def create_connection():
    """创建并返回一个数据库连接对象"""
    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("成功连接到MySQL数据库")
    except Error as e:
        print(f"连接MySQL时发生错误: '{e}'")
        # 在实际应用中，这里可能需要更复杂的错误处理或日志记录
    return connection

# 执行查询操作 (SELECT)
def execute_read_query(query, params=None):
    """
    执行一个读取数据的SQL查询 (SELECT)
    :param query: SQL查询语句
    :param params: 查询参数 (元组)
    :return: 查询结果列表，每个元素是一个元组代表一行数据
    """
    connection = create_connection()
    if connection is None:
        return [] # 如果连接失败，返回空列表

    cursor = connection.cursor(dictionary=True) # 使用字典cursor，结果会是字典列表
    result = []
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchall()
        print("查询执行成功")
    except Error as e:
        print(f"执行查询时发生错误: '{e}'")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL连接已关闭")
    return result

# 执行修改操作 (INSERT, UPDATE, DELETE)
def execute_modify_query(query, params=None):
    """
    执行一个修改数据的SQL查询 (INSERT, UPDATE, DELETE)
    :param query: SQL查询语句
    :param params: 查询参数 (元组)
    :return: 如果是INSERT操作，返回最后插入行的ID；其他情况返回影响的行数。失败返回None。
    """
    connection = create_connection()
    if connection is None:
        return None

    cursor = connection.cursor()
    last_row_id = None
    affected_rows = None
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        connection.commit() # 提交事务
        last_row_id = cursor.lastrowid # 获取INSERT操作的自增ID
        affected_rows = cursor.rowcount # 获取影响的行数
        print("修改查询执行成功")
    except Error as e:
        print(f"执行修改查询时发生错误: '{e}'")
        if connection.is_connected():
            connection.rollback() # 如果发生错误，回滚事务
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL连接已关闭")
    
    if query.strip().upper().startswith("INSERT"):
        return last_row_id
    return affected_rows


# --- 菜品管理函数 ---
def get_all_menu_items():
    """获取所有菜品信息"""
    query = "SELECT id, name, description, price, category, image_url, is_available FROM menu_items WHERE is_available = TRUE"
    return execute_read_query(query)

def get_menu_item_by_id(item_id):
    """根据ID获取单个菜品信息"""
    query = "SELECT id, name, description, price, category, image_url, is_available FROM menu_items WHERE id = %s"
    items = execute_read_query(query, (item_id,))
    return items[0] if items else None

def add_menu_item(name, description, price, category, image_url=None):
    """添加新菜品"""
    query = """
    INSERT INTO menu_items (name, description, price, category, image_url) 
    VALUES (%s, %s, %s, %s, %s)
    """
    return execute_modify_query(query, (name, description, price, category, image_url))

# --- 订单管理函数 ---
def create_order(customer_name, total_amount, items):
    """
    创建新订单
    :param customer_name: 顾客名
    :param total_amount: 总金额
    :param items: 订单项列表, 每个项是 {'menu_item_id': id, 'quantity': qty, 'subtotal': subtotal}
    :return: 新订单的ID，如果失败返回None
    """
    connection = create_connection()
    if not connection:
        return None
    
    cursor = connection.cursor()
    try:
        # 1. 插入订单主表
        order_query = "INSERT INTO orders (customer_name, total_amount) VALUES (%s, %s)"
        cursor.execute(order_query, (customer_name, total_amount))
        order_id = cursor.lastrowid # 获取新订单的ID

        if not order_id:
            raise Exception("创建订单失败，未能获取订单ID")

        # 2. 插入订单详情表
        item_query = "INSERT INTO order_items (order_id, menu_item_id, quantity, subtotal) VALUES (%s, %s, %s, %s)"
        for item in items:
            cursor.execute(item_query, (order_id, item['menu_item_id'], item['quantity'], item['subtotal']))
        
        connection.commit()
        print(f"订单 {order_id} 创建成功")
        return order_id
    except Error as e:
        print(f"创建订单时发生数据库错误: '{e}'")
        if connection.is_connected():
            connection.rollback()
        return None
    except Exception as ex:
        print(f"创建订单时发生一般错误: '{ex}'")
        if connection.is_connected():
            connection.rollback()
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL连接已关闭")

def get_order_by_id(order_id):
    """获取订单及其详情"""
    order_query = "SELECT * FROM orders WHERE id = %s"
    order_details = execute_read_query(order_query, (order_id,))
    if not order_details:
        return None
    
    order_items_query = """
    SELECT oi.quantity, oi.subtotal, mi.name as item_name, mi.price as item_price
    FROM order_items oi
    JOIN menu_items mi ON oi.menu_item_id = mi.id
    WHERE oi.order_id = %s
    """
    items = execute_read_query(order_items_query, (order_id,))
    
    result = order_details[0]
    result['items'] = items
    return result

if __name__ == '__main__':
    # 测试数据库连接和操作
    print("测试数据库模块...")
    
    # 测试获取所有菜品
    # menu = get_all_menu_items()
    # if menu:
    #     print("\n当前菜单:")
    #     for item in menu:
    #         print(f"- {item['name']}: {item['price']}元 ({item['category']})")
    # else:
    #     print("未能获取到菜单信息或菜单为空。")

    # 测试添加菜品 (为避免重复添加，可以先注释掉)
    # new_item_id = add_menu_item("红烧牛肉", "精选牛肉，慢炖入味", 48.00, "主菜", "beef_stew.jpg")
    # if new_item_id:
    #     print(f"\n成功添加新菜品，ID: {new_item_id}")
    #     item = get_menu_item_by_id(new_item_id)
    #     if item:
    #         print(f"获取新菜品信息: {item}")
    # else:
    #     print("\n添加新菜品失败。")

    # 测试创建订单
    # print("\n测试创建订单...")
    # # 假设顾客点单: 宫保鸡丁 x1, 米饭 x2
    # # 1. 先获取菜品信息以计算价格 (实际应用中前端会传递这些信息)
    # gongbao = get_menu_item_by_id(1) # 假设宫保鸡丁ID为1
    # rice = get_menu_item_by_id(5)   # 假设米饭ID为5
    
    # if gongbao and rice:
    #     order_items_data = [
    #         {'menu_item_id': gongbao['id'], 'quantity': 1, 'subtotal': gongbao['price'] * 1},
    #         {'menu_item_id': rice['id'], 'quantity': 2, 'subtotal': rice['price'] * 2}
    #     ]
    #     total = sum(item['subtotal'] for item in order_items_data)
        
    #     new_order_id = create_order("张三", total, order_items_data)
    #     if new_order_id:
    #         print(f"订单创建成功，订单ID: {new_order_id}")
    #         # 查询并打印订单详情
    #         created_order = get_order_by_id(new_order_id)
    #         if created_order:
    #             print("订单详情:", created_order)
    #     else:
    #         print("订单创建失败。")
    # else:
    #     print("未能获取到用于创建订单的菜品信息。")
    pass
