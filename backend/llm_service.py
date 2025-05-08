# backend/llm_service.py
import requests # 用于发送HTTP请求到大模型API
import json

# 假设Qwen API的配置
# QWEN_API_URL = "YOUR_QWEN_API_ENDPOINT"  # 替换为实际的Qwen API URL
# QWEN_API_KEY = "YOUR_QWEN_API_KEY"      # 替换为你的API密钥

# 注意：实际的API URL和认证方式请参考Qwen官方文档。
# 这里我们用一个模拟函数代替真实的API调用。

def get_recipe_suggestion_from_qwen(current_dishes, preferences=""):
    """
    从Qwen大模型获取餐谱搭配建议。
    这是一个模拟函数，你需要根据Qwen的实际API进行替换。

    :param current_dishes: 当前已点菜品列表 (例如: ['宫保鸡丁', '米饭'])
    :param preferences: 用户偏好 (例如: '不吃辣', '素食者')
    :return: 大模型返回的建议文本，或者错误信息。
    """
    print(f"准备向Qwen请求餐谱建议。当前菜品: {current_dishes}, 用户偏好: {preferences}")

    # 1. 构建Prompt
    # 这是非常关键的一步，Prompt的质量直接影响模型输出效果。
    prompt = f"我正在点餐，已经选择了以下菜品：{', '.join(current_dishes)}。\n"
    if preferences:
        prompt += f"我的饮食偏好是：{preferences}。\n"
    prompt += "请根据这些信息，为我推荐一些搭配的菜品或饮品，并简要说明理由。请以友好和专业的餐厅顾问口吻回答。"
    
    print(f"构建的Prompt: {prompt}")

    # --------------------------------------------------------------------
    # ---- 以下是模拟API调用的部分，你需要替换为真实的Qwen API调用 ----
    # --------------------------------------------------------------------
    # 假设Qwen API需要一个JSON payload
    # payload = {
    #     "prompt": prompt,
    #     "model": "qwen2.5-0.5b-instruct", # 确认模型名称
    #     "max_tokens": 150, # 根据需要调整
    #     # 其他可能的参数，如 temperature, top_p 等
    # }
    # headers = {
    #     "Authorization": f"Bearer {QWEN_API_KEY}", # 假设使用Bearer Token认证
    #     "Content-Type": "application/json"
    # }

    try:
        # print(f"发送请求到 Qwen API: {QWEN_API_URL}")
        # response = requests.post(QWEN_API_URL, json=payload, headers=headers, timeout=30) # 设置超时
        # response.raise_for_status() # 如果HTTP状态码是4xx或5xx，则抛出异常

        # result_data = response.json()
        # suggestion = result_data.get("choices", [{}])[0].get("text", "抱歉，暂时无法获取建议。") 
        # print(f"从Qwen API获取到响应: {result_data}")

        # ---- 模拟响应 ----
        if not current_dishes:
            return "您还没有选择任何菜品呢！可以先看看我们的招牌菜，比如宫保鸡丁、鱼香肉丝，或者告诉我您的口味偏好，我来给您推荐。"
        
        mock_suggestion = f"基于您选择的 {', '.join(current_dishes)}"
        if preferences:
            mock_suggestion += f" 和您的偏好 '{preferences}'"
        mock_suggestion += "，我为您推荐：\n"

        if "宫保鸡丁" in current_dishes and "酸辣汤" not in current_dishes:
            mock_suggestion += "- **酸辣汤**: 宫保鸡丁口味浓郁，搭配一碗酸辣汤可以很好地开胃解腻，丰富口感层次。\n"
        if "鱼香肉丝" in current_dishes and "米饭" not in current_dishes:
            mock_suggestion += "- **米饭**: 鱼香肉丝是非常下饭的菜，配上米饭是绝佳的选择。\n"
        if "可乐" not in current_dishes:
            mock_suggestion += "- **冰镇可乐**: 如果您喜欢饮品，冰镇可乐可以带来清爽的口感，尤其适合搭配川菜。\n"
        
        if mock_suggestion.endswith("推荐：\n"): # 如果没有匹配到具体推荐
             mock_suggestion += "这些菜品本身已经很棒了！如果您想尝试更多，可以考虑加一份清炒时蔬，平衡一下营养哦。"

        suggestion = mock_suggestion
        # ---- 模拟结束 ----

        return suggestion

    # except requests.exceptions.RequestException as e:
    #     print(f"请求Qwen API时发生网络错误: {e}")
    #     return "抱歉，连接餐谱建议服务时出现网络问题，请稍后再试。"
    # except Exception as e:
    #     print(f"处理Qwen API响应时发生错误: {e}")
    #     return "抱歉，获取餐谱建议时出现内部错误，请稍后再试。"
    except Exception as e: # 模拟部分的简单错误处理
        print(f"模拟Qwen服务时发生错误: {e}")
        return "抱歉，餐谱建议服务暂时不可用（模拟）。"


if __name__ == '__main__':
    print("测试LLM服务模块...")
    # 测试1: 有菜品，无偏好
    dishes1 = ["宫保鸡丁", "米饭"]
    suggestion1 = get_recipe_suggestion_from_qwen(dishes1)
    print(f"\n建议1 (菜品: {dishes1}):\n{suggestion1}")

    # 测试2: 有菜品，有偏好
    dishes2 = ["麻婆豆腐"]
    prefs2 = "不吃辣，喜欢清淡" # 这个偏好和麻婆豆腐有点冲突，看模型怎么说
    suggestion2 = get_recipe_suggestion_from_qwen(dishes2, prefs2)
    print(f"\n建议2 (菜品: {dishes2}, 偏好: {prefs2}):\n{suggestion2}")
    
    # 测试3: 无菜品
    dishes3 = []
    suggestion3 = get_recipe_suggestion_from_qwen(dishes3)
    print(f"\n建议3 (菜品: {dishes3}):\n{suggestion3}")
