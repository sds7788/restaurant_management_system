# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import backend.database as db
import backend.llm_service as llm
from datetime import datetime, timedelta # 用于JWT
import jwt # PyJWT库，需要 pip install PyJWT bcrypt
import bcrypt # 用于密码哈希

# --- 应用配置 ---
app = Flask(__name__)
CORS(app) # 允许所有来源的跨域请求

# JWT 配置 (在生产环境中应使用更安全的密钥并从环境变量读取)
app.config['SECRET_KEY'] = 'your-very-secret-and-strong-key' # 必须修改为一个强密钥!
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1) # Token有效期1小时
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30) # Refresh Token有效期30天 (如果使用)

# --- 辅助函数：JWT 和 权限装饰器 ---
from functools import wraps

def token_required(f):
    """装饰器：检查请求头中是否包含有效的JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        try:
            # 解码Token，获取当前用户信息
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = db.get_user_by_id(data['user_id'])
            if not current_user:
                return jsonify({"message": "Token is invalid, user not found!"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Token is invalid!"}), 401
        
        # 将当前用户信息传递给被装饰的函数
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    """装饰器：检查用户是否为管理员"""
    @wraps(f)
    @token_required # admin_required 必须在 token_required 之后
    def decorated(current_user, *args, **kwargs):
        if current_user['role'] != 'admin':
            return jsonify({"message": "Admin privilege required!"}), 403
        return f(current_user, *args, **kwargs)
    return decorated

# --- API 端点 ---

@app.route('/')
def home():
    return "欢迎来到餐饮管理系统后端API！ (v2)"

# == 用户认证API ==
@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """用户注册"""
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "用户名和密码不能为空"}), 400

    username = data['username']
    password = data['password']
    role = data.get('role', 'customer') # 默认为顾客，前端可以不传或传指定角色
    full_name = data.get('full_name')
    email = data.get('email')
    phone = data.get('phone')

    if db.get_user_by_username(username):
        return jsonify({"error": "用户名已存在"}), 409
    if email and db.execute_query("SELECT id FROM users WHERE email = %s", (email,), fetch_one=True): # 简单检查邮箱是否已存在
        return jsonify({"error": "邮箱已被注册"}), 409


    user_id = db.create_user(username, password, role, full_name, email, phone)
    if user_id:
        return jsonify({"message": "用户注册成功", "user_id": user_id}), 201
    else:
        app.logger.error(f"用户注册失败: {username}")
        return jsonify({"error": "用户注册失败，请稍后再试"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    """用户登录，成功则返回JWT"""
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "请输入用户名和密码"}), 400

    username = data['username']
    password = data['password']
    
    user = db.get_user_by_username(username)

    if not user or not db.verify_password(password, user['password_hash']):
        return jsonify({"error": "用户名或密码错误"}), 401

    # 更新最后登录时间
    db.update_user_last_login(user['id'])

    # 生成JWT
    token_payload = {
        'user_id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'exp': datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
    }
    access_token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({
        "message": "登录成功",
        "access_token": access_token,
        "user": { # 可以选择性返回一些用户信息给前端
            "id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "full_name": user.get('full_name')
        }
    }), 200

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user_profile(current_user):
    """获取当前登录用户的个人信息 (需要Token)"""
    # current_user 是由 @token_required 装饰器注入的
    # 从中移除敏感信息，如 password_hash
    profile_data = {key: value for key, value in current_user.items() if key != 'password_hash'}
    return jsonify(profile_data), 200


# == 菜品和分类API (基本不变，但添加菜品可能需要管理员权限) ==
@app.route('/api/categories', methods=['GET'])
def get_categories():
    """获取所有菜品分类"""
    try:
        categories = db.get_all_categories()
        return jsonify(categories), 200
    except Exception as e:
        app.logger.error(f"获取分类失败: {e}")
        return jsonify({"error": "获取分类失败", "message": str(e)}), 500

@app.route('/api/menu', methods=['GET'])
def get_menu():
    """获取所有可用菜品"""
    try:
        menu_items = db.get_all_menu_items()
        return jsonify(menu_items), 200
    except Exception as e:
        app.logger.error(f"获取菜单失败: {e}")
        return jsonify({"error": "获取菜单失败", "message": str(e)}), 500

@app.route('/api/menu/<int:item_id>', methods=['GET'])
def get_menu_item(item_id):
    """获取单个菜品详情"""
    # ... (代码与之前版本类似，此处省略以减少篇幅)
    try:
        item = db.get_menu_item_by_id(item_id)
        if item:
            return jsonify(item), 200
        else:
            return jsonify({"error": "菜品未找到"}), 404
    except Exception as e:
        app.logger.error(f"获取菜品 {item_id} 失败: {e}")
        return jsonify({"error": f"获取菜品 {item_id} 失败", "message": str(e)}), 500


@app.route('/api/admin/menu', methods=['POST'])
@admin_required # 只有管理员可以添加菜品
def admin_add_new_menu_item(current_admin_user):
    """管理员添加新菜品"""
    try:
        data = request.get_json()
        # 参数校验 (name, price, category_id 是必须的)
        required_fields = ['name', 'price', 'category_id']
        if not data or not all(k in data for k in required_fields):
            return jsonify({"error": f"缺少必要参数: {', '.join(required_fields)}"}), 400
        
        name = data['name']
        description = data.get('description', '')
        price = data['price']
        category_id = data['category_id']
        image_url = data.get('image_url')
        is_available = data.get('is_available', True)

        try:
            price = float(price)
            if price <= 0:
                raise ValueError("价格必须为正数")
            category_id = int(category_id)
        except ValueError as ve:
            return jsonify({"error": "价格或分类ID格式无效", "message": str(ve)}), 400

        # 检查分类是否存在
        if not db.get_category_by_id(category_id):
            return jsonify({"error": f"分类ID {category_id} 不存在"}), 404

        item_id = db.add_menu_item(name, description, price, category_id, image_url, is_available)
        if item_id:
            app.logger.info(f"管理员 {current_admin_user['username']} 添加菜品成功, ID: {item_id}")
            return jsonify({"message": "菜品添加成功", "item_id": item_id}), 201
        else:
            return jsonify({"error": "添加菜品失败"}), 500
    except Exception as e:
        app.logger.error(f"管理员 {current_admin_user.get('username', 'N/A')} 添加菜品失败: {e}", exc_info=True)
        return jsonify({"error": "添加菜品时发生服务器错误", "message": str(e)}), 500

# TODO: 实现管理员修改菜品、删除菜品API (@admin_required)

# == 订单API (重要修改) ==
@app.route('/api/orders', methods=['POST'])
@token_required # 用户下单需要登录 (也可以允许匿名，但逻辑会更复杂)
def place_order(current_user):
    """创建新订单 (用户必须登录)"""
    try:
        data = request.get_json()
        if not data or not data.get('items'): # customer_name 不再是必须，从token获取用户信息
            return jsonify({"error": "缺少必要参数 (items)"}), 400

        order_items_data_frontend = data['items'] # 期望格式: [{'menu_item_id': id, 'quantity': qty, 'special_requests': 'text'}, ...]
        
        if not isinstance(order_items_data_frontend, list) or not order_items_data_frontend:
            return jsonify({"error": "订单项目(items)必须是非空列表"}), 400

        # --- 后端重新计算价格和构建订单项 ---
        detailed_items_for_db = []
        total_amount = 0
        for item_data in order_items_data_frontend:
            if not isinstance(item_data, dict) or not all(k in item_data for k in ('menu_item_id', 'quantity')):
                return jsonify({"error": "订单项目中缺少 menu_item_id 或 quantity"}), 400
            
            menu_item_id = item_data['menu_item_id']
            quantity = item_data['quantity']
            special_requests = item_data.get('special_requests')

            try:
                quantity = int(quantity)
                if quantity <= 0:
                     return jsonify({"error": f"菜品ID {menu_item_id} 的数量必须为正整数"}), 400
            except ValueError:
                return jsonify({"error": f"菜品ID {menu_item_id} 的数量格式无效"}), 400

            menu_item_db = db.get_menu_item_by_id(menu_item_id) # 从数据库获取菜品信息
            if not menu_item_db or not menu_item_db['is_available']:
                return jsonify({"error": f"菜品 '{menu_item_db.get('name', menu_item_id)}' 未找到或不可用"}), 404
            
            unit_price = menu_item_db['price'] # 使用数据库中的当前价格作为单价
            subtotal = unit_price * quantity
            total_amount += subtotal
            
            detailed_items_for_db.append({
                'menu_item_id': menu_item_id,
                'quantity': quantity,
                'unit_price': unit_price,
                'subtotal': subtotal,
                'special_requests': special_requests
            })
        # --- 价格计算结束 ---

        order_id = db.create_order(
            user_id=current_user['id'], # 从Token中获取用户ID
            customer_name=current_user.get('full_name', current_user['username']), # 优先用全名
            total_amount=total_amount,
            items_data=detailed_items_for_db,
            payment_method=data.get('payment_method'),
            delivery_address=data.get('delivery_address'),
            notes=data.get('notes')
        )

        if order_id:
            app.logger.info(f"用户 {current_user['username']} (ID: {current_user['id']}) 创建订单成功, 订单ID: {order_id}")
            return jsonify({"message": "订单创建成功", "order_id": order_id, "total_amount": total_amount}), 201
        else:
            app.logger.error(f"用户 {current_user['username']} 创建订单失败")
            return jsonify({"error": "创建订单失败"}), 500
    except Exception as e:
        app.logger.error(f"用户 {current_user.get('username', 'N/A')} 创建订单时发生服务器错误: {e}", exc_info=True)
        return jsonify({"error": "创建订单时发生服务器错误", "message": str(e)}), 500

@app.route('/api/orders/my', methods=['GET'])
@token_required
def get_my_orders(current_user):
    """获取当前登录用户的历史订单 (分页)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        if page < 1: page = 1
        if per_page < 1: per_page = 1
        if per_page > 100: per_page = 100 # 防止一次请求过多数据

        orders_data = db.get_orders_by_user_id(current_user['id'], page, per_page)
        return jsonify(orders_data), 200
    except Exception as e:
        app.logger.error(f"用户 {current_user['username']} 获取历史订单失败: {e}", exc_info=True)
        return jsonify({"error": "获取历史订单失败", "message": str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['GET'])
@token_required # 用户只能看自己的订单，管理员可以看所有（下面有专门的管理员接口）
def get_single_order(current_user, order_id):
    """获取单个订单详情 (用户只能查看自己的，除非是管理员)"""
    try:
        order = db.get_order_details_by_id(order_id)
        if not order:
            return jsonify({"error": "订单未找到"}), 404
        
        # 权限检查：如果不是管理员，且订单不属于当前用户
        if current_user['role'] != 'admin' and order.get('user_id') != current_user['id']:
            return jsonify({"error": "无权访问此订单"}), 403
            
        return jsonify(order), 200
    except Exception as e:
        app.logger.error(f"获取订单 {order_id} 失败 (请求者: {current_user['username']}): {e}", exc_info=True)
        return jsonify({"error": f"获取订单 {order_id} 失败", "message": str(e)}), 500

# == 管理员订单管理API ==
@app.route('/api/admin/orders', methods=['GET'])
@admin_required
def admin_get_all_orders(current_admin_user):
    """管理员获取所有订单 (分页, 可筛选, 可排序)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status_filter = request.args.get('status')
        user_id_filter = request.args.get('user_id', type=int)
        sort_by = request.args.get('sort_by', 'order_time')
        sort_order = request.args.get('sort_order', 'DESC')

        if page < 1: page = 1
        if per_page < 1: per_page = 1
        if per_page > 100: per_page = 100

        orders_data = db.get_all_orders_admin(page, per_page, status_filter, user_id_filter, sort_by, sort_order)
        return jsonify(orders_data), 200
    except Exception as e:
        app.logger.error(f"管理员 {current_admin_user['username']} 获取所有订单失败: {e}", exc_info=True)
        return jsonify({"error": "获取所有订单失败", "message": str(e)}), 500

@app.route('/api/admin/orders/<int:order_id>/status', methods=['PUT'])
@admin_required
def admin_update_order_status(current_admin_user, order_id):
    """管理员更新订单状态"""
    data = request.get_json()
    new_status = data.get('status')
    if not new_status:
        return jsonify({"error": "缺少新状态 (status) 参数"}), 400
    
    # 你可能需要在这里验证 new_status 是否是合法的状态值
    valid_statuses = ['pending', 'confirmed', 'preparing', 'completed', 'cancelled', 'delivered']
    if new_status not in valid_statuses:
        return jsonify({"error": f"无效的订单状态: {new_status}. 合法状态为: {', '.join(valid_statuses)}"}), 400

    try:
        success = db.update_order_status_admin(order_id, new_status, current_admin_user['id'])
        if success:
            app.logger.info(f"管理员 {current_admin_user['username']} 更新订单 {order_id} 状态为 {new_status} 成功")
            return jsonify({"message": f"订单 {order_id} 状态已更新为 {new_status}"}), 200
        else:
            # database.py 中的函数会打印更详细的错误，这里返回通用错误
            return jsonify({"error": f"更新订单 {order_id} 状态失败，订单可能不存在或数据库错误"}), 404 # 或 500
    except Exception as e:
        app.logger.error(f"管理员 {current_admin_user['username']} 更新订单 {order_id} 状态失败: {e}", exc_info=True)
        return jsonify({"error": "更新订单状态时发生服务器错误", "message": str(e)}), 500


# == LLM 餐谱建议API (保持不变) ==
@app.route('/api/recipe-suggestion', methods=['POST'])
def get_recipe_suggestion():
    # ... (代码与之前版本相同，此处省略)
    try:
        data = request.get_json()
        current_dishes = data.get('current_dishes', []) 
        preferences = data.get('preferences', "")    

        if not isinstance(current_dishes, list):
            return jsonify({"error": "current_dishes 必须是一个列表"}), 400
        
        suggestion = llm.get_recipe_suggestion_from_qwen(current_dishes, preferences)
        return jsonify({"suggestion": suggestion}), 200
    except Exception as e:
        app.logger.error(f"获取餐谱建议失败: {e}", exc_info=True)
        return jsonify({"error": "获取餐谱建议时发生服务器错误", "message": str(e)}), 500


if __name__ == '__main__':
    import logging
    # 配置日志记录到文件和控制台
    # logging.basicConfig(level=logging.INFO) # 基础配置，只输出到控制台

    # 创建一个logger
    app_logger = logging.getLogger() # 获取root logger
    app_logger.setLevel(logging.INFO)

    # 创建控制台handler并设置级别
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建文件handler并设置级别
    file_handler = logging.FileHandler('restaurant_app.log', encoding='utf-8') # 指定UTF-8编码
    file_handler.setLevel(logging.INFO)

    # 创建formatter并将其添加到handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 将handler添加到logger
    if not app_logger.handlers: # 防止重复添加handlers
        app_logger.addHandler(console_handler)
        app_logger.addHandler(file_handler)
    
    app.logger.info("餐饮管理系统后端API启动...") # 使用app.logger记录
    app.run(host='0.0.0.0', port=5000, debug=True) # debug=True仅用于开发