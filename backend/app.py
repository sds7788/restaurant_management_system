# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS # 用于处理跨域请求，方便前后端分离开发
import backend.database as db # 导入我们创建的数据库模块
import backend.llm_service as llm # 导入我们创建的LLM服务模块

app = Flask(__name__)
CORS(app) # 允许所有来源的跨域请求，生产环境应配置具体的来源

# --- API 端点 (Endpoints) ---

@app.route('/')
def home():
    return "欢迎来到餐饮管理系统后端API！"

# == 菜品API ==
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
    try:
        item = db.get_menu_item_by_id(item_id)
        if item:
            return jsonify(item), 200
        else:
            return jsonify({"error": "菜品未找到"}), 404
    except Exception as e:
        app.logger.error(f"获取菜品 {item_id} 失败: {e}")
        return jsonify({"error": f"获取菜品 {item_id} 失败", "message": str(e)}), 500

# 示例：添加菜品 (通常需要管理员权限，此处简化)
@app.route('/api/menu', methods=['POST'])
def add_new_menu_item():
    """添加新菜品"""
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ('name', 'price', 'category')):
            return jsonify({"error": "缺少必要参数 (name, price, category)"}), 400
        
        name = data['name']
        description = data.get('description', '')
        price = data['price']
        category = data['category']
        image_url = data.get('image_url')

        # 简单验证价格
        try:
            price = float(price)
            if price <= 0:
                raise ValueError("价格必须为正数")
        except ValueError as ve:
            return jsonify({"error": "价格格式无效", "message": str(ve)}), 400

        item_id = db.add_menu_item(name, description, price, category, image_url)
        if item_id:
            return jsonify({"message": "菜品添加成功", "item_id": item_id}), 201
        else:
            return jsonify({"error": "添加菜品失败"}), 500
    except Exception as e:
        app.logger.error(f"添加菜品失败: {e}")
        return jsonify({"error": "添加菜品时发生服务器错误", "message": str(e)}), 500


# == 订单API ==
@app.route('/api/orders', methods=['POST'])
def place_order():
    """创建新订单"""
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ('customer_name', 'items')):
            return jsonify({"error": "缺少必要参数 (customer_name, items)"}), 400

        customer_name = data['customer_name']
        order_items_data = data['items'] # 期望格式: [{'menu_item_id': id, 'quantity': qty}, ...]
        
        if not isinstance(order_items_data, list) or not order_items_data:
            return jsonify({"error": "订单项目(items)必须是非空列表"}), 400

        # 计算总价并验证菜品ID的有效性 (重要!)
        # 在实际应用中，应该从数据库重新获取菜品价格，而不是信任前端传递的价格
        detailed_items = []
        total_amount = 0
        for item_data in order_items_data:
            if not isinstance(item_data, dict) or not all(k in item_data for k in ('menu_item_id', 'quantity')):
                return jsonify({"error": "订单项目中缺少 menu_item_id 或 quantity"}), 400
            
            menu_item_id = item_data['menu_item_id']
            quantity = item_data['quantity']

            try:
                quantity = int(quantity)
                if quantity <= 0:
                     return jsonify({"error": f"菜品ID {menu_item_id} 的数量必须为正整数"}), 400
            except ValueError:
                return jsonify({"error": f"菜品ID {menu_item_id} 的数量格式无效"}), 400

            menu_item = db.get_menu_item_by_id(menu_item_id) # 从数据库获取菜品信息
            if not menu_item:
                return jsonify({"error": f"菜品ID {menu_item_id} 未找到或不可用"}), 404
            
            subtotal = menu_item['price'] * quantity
            total_amount += subtotal
            detailed_items.append({
                'menu_item_id': menu_item_id,
                'quantity': quantity,
                'subtotal': subtotal
            })

        order_id = db.create_order(customer_name, total_amount, detailed_items)
        if order_id:
            return jsonify({"message": "订单创建成功", "order_id": order_id, "total_amount": total_amount}), 201
        else:
            return jsonify({"error": "创建订单失败"}), 500
    except Exception as e:
        app.logger.error(f"创建订单失败: {e}")
        return jsonify({"error": "创建订单时发生服务器错误", "message": str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """获取订单详情"""
    try:
        order = db.get_order_by_id(order_id)
        if order:
            return jsonify(order), 200
        else:
            return jsonify({"error": "订单未找到"}), 404
    except Exception as e:
        app.logger.error(f"获取订单 {order_id} 失败: {e}")
        return jsonify({"error": f"获取订单 {order_id} 失败", "message": str(e)}), 500


# == LLM 餐谱建议API ==
@app.route('/api/recipe-suggestion', methods=['POST'])
def get_recipe_suggestion():
    """获取餐谱搭配建议"""
    try:
        data = request.get_json()
        current_dishes = data.get('current_dishes', []) # 例如: ["宫保鸡丁", "米饭"]
        preferences = data.get('preferences', "")     # 例如: "不吃辣"

        if not isinstance(current_dishes, list):
            return jsonify({"error": "current_dishes 必须是一个列表"}), 400
        
        # 调用LLM服务
        suggestion = llm.get_recipe_suggestion_from_qwen(current_dishes, preferences)
        
        return jsonify({"suggestion": suggestion}), 200
    except Exception as e:
        app.logger.error(f"获取餐谱建议失败: {e}")
        return jsonify({"error": "获取餐谱建议时发生服务器错误", "message": str(e)}), 500


if __name__ == '__main__':
    # 配置日志记录
    import logging
    logging.basicConfig(level=logging.INFO) # 设置日志级别
    # 你可以将日志输出到文件:
    # handler = logging.FileHandler('app.log')
    # handler.setLevel(logging.INFO)
    # app.logger.addHandler(handler)

    # 运行Flask应用
    # debug=True 只应在开发环境中使用
    # host='0.0.0.0' 使应用可以从网络中的其他机器访问
    app.run(host='0.0.0.0', port=5000, debug=True)
