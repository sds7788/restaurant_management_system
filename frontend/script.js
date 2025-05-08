// frontend/script.js

// 后端API的基础URL (确保Flask后端正在运行并且地址正确)
const API_BASE_URL = 'http://localhost:5000/api';

// DOM元素获取
const menuItemsDiv = document.getElementById('menuItems');
const cartItemsDiv = document.getElementById('cartItems');
const cartTotalSpan = document.getElementById('cartTotal');
const placeOrderBtn = document.getElementById('placeOrderBtn');
const clearCartBtn = document.getElementById('clearCartBtn');
const customerNameInput = document.getElementById('customerName');
const getSuggestionBtn = document.getElementById('getSuggestionBtn');
const userPreferencesInput = document.getElementById('userPreferences');
const llmSuggestionDiv = document.getElementById('llmSuggestion');

const messageModal = document.getElementById('messageModal');
const modalMessageText = document.getElementById('modalMessageText');

// 购物车状态
let cart = []; // 数组，每个元素是 {id, name, price, quantity}

// --- 消息提示 ---
function showModal(message, isError = false) {
    modalMessageText.textContent = message;
    modalMessageText.style.color = isError ? 'red' : 'black';
    messageModal.style.display = 'block';
}

function closeModal() {
    messageModal.style.display = 'none';
}
// 点击模态框外部区域关闭 (可选)
window.onclick = function(event) {
    if (event.target == messageModal) {
        closeModal();
    }
}


// --- 菜单加载 ---
async function fetchMenu() {
    try {
        const response = await fetch(`${API_BASE_URL}/menu`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const menu = await response.json();
        renderMenu(menu);
    } catch (error) {
        console.error('获取菜单失败:', error);
        menuItemsDiv.innerHTML = '<p class="text-red-500">加载菜单失败，请稍后再试。</p>';
        showModal(`加载菜单失败: ${error.message}`, true);
    }
}

function renderMenu(menu) {
    menuItemsDiv.innerHTML = ''; // 清空旧内容
    if (!menu || menu.length === 0) {
        menuItemsDiv.innerHTML = '<p>暂无可售菜品。</p>';
        return;
    }
    menu.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'menu-item bg-white shadow-md rounded-lg p-4 flex flex-col'; // 使用Tailwind类
        itemDiv.innerHTML = `
            <img src="${item.image_url || 'https://placehold.co/300x200/E2E8F0/A0AEC0?text=菜品图片'}" alt="${item.name}" class="w-full h-40 object-cover rounded-md mb-3" onerror="this.onerror=null;this.src='https://placehold.co/300x200/E2E8F0/A0AEC0?text=图片加载失败';">
            <div class="flex-grow">
                <h3 class="text-xl font-semibold text-purple-700">${item.name}</h3>
                <p class="text-sm text-gray-600 my-1">${item.description || '暂无描述'}</p>
                <p class="text-lg font-bold text-purple-600">¥${parseFloat(item.price).toFixed(2)}</p>
                <p class="text-xs text-gray-500">分类: ${item.category}</p>
            </div>
            <div class="mt-3">
                <label for="qty-${item.id}" class="text-sm mr-2">数量:</label>
                <input type="number" id="qty-${item.id}" value="1" min="1" class="w-16 p-1 border rounded-md text-sm">
                <button class="button text-sm py-1 px-2 ml-2" onclick="addToCart(${item.id}, '${item.name}', ${item.price}, 'qty-${item.id}')">加入餐车</button>
            </div>
        `;
        menuItemsDiv.appendChild(itemDiv);
    });
}

// --- 购物车操作 ---
function addToCart(id, name, price, quantityInputId) {
    const quantityInput = document.getElementById(quantityInputId);
    const quantity = parseInt(quantityInput.value);

    if (isNaN(quantity) || quantity <= 0) {
        showModal('请输入有效的数量!', true);
        return;
    }

    const existingItem = cart.find(cartItem => cartItem.id === id);
    if (existingItem) {
        existingItem.quantity += quantity;
    } else {
        cart.push({ id, name, price, quantity });
    }
    renderCart();
    quantityInput.value = "1"; // 重置数量输入
    showModal(`${name} 已添加到餐车!`);
}

function removeFromCart(itemId) {
    cart = cart.filter(item => item.id !== itemId);
    renderCart();
}

function updateCartQuantity(itemId, change) {
    const item = cart.find(cartItem => cartItem.id === itemId);
    if (item) {
        item.quantity += change;
        if (item.quantity <= 0) {
            removeFromCart(itemId);
        } else {
            renderCart();
        }
    }
}


function renderCart() {
    cartItemsDiv.innerHTML = ''; // 清空
    let total = 0;
    if (cart.length === 0) {
        cartItemsDiv.innerHTML = '<p class="text-gray-500">餐车是空的。</p>';
    } else {
        cart.forEach(item => {
            const itemTotal = item.price * item.quantity;
            total += itemTotal;
            const cartItemDiv = document.createElement('div');
            cartItemDiv.className = 'cart-item flex justify-between items-center py-2 border-b border-gray-200';
            cartItemDiv.innerHTML = `
                <div>
                    <span class="font-medium">${item.name}</span>
                    <span class="text-sm text-gray-600">(¥${parseFloat(item.price).toFixed(2)} x ${item.quantity})</span>
                </div>
                <div class="flex items-center">
                    <span class="font-semibold mr-3">¥${itemTotal.toFixed(2)}</span>
                    <button class="text-xs bg-yellow-400 hover:bg-yellow-500 text-yellow-800 py-1 px-1 rounded mr-1" onclick="updateCartQuantity(${item.id}, -1)">-</button>
                    <button class="text-xs bg-red-500 hover:bg-red-600 text-white py-1 px-1 rounded" onclick="removeFromCart(${item.id})">移除</button>
                </div>
            `;
            cartItemsDiv.appendChild(cartItemDiv);
        });
    }
    cartTotalSpan.textContent = total.toFixed(2);
}

function clearCart() {
    cart = [];
    renderCart();
    showModal('餐车已清空。');
}

// --- 下单操作 ---
async function placeOrder() {
    const customerName = customerNameInput.value.trim();
    if (!customerName) {
        showModal('请输入顾客姓名!', true);
        return;
    }
    if (cart.length === 0) {
        showModal('餐车是空的，请先添加菜品!', true);
        return;
    }

    const orderData = {
        customer_name: customerName,
        items: cart.map(item => ({
            menu_item_id: item.id,
            quantity: item.quantity
        }))
        // 后端会根据这些信息计算总价并从数据库获取单价，更安全
    };

    try {
        placeOrderBtn.disabled = true;
        placeOrderBtn.textContent = '正在下单...';
        const response = await fetch(`${API_BASE_URL}/orders`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(orderData),
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || `HTTP error! status: ${response.status}`);
        }
        
        showModal(`订单创建成功! 订单ID: ${result.order_id}, 总金额: ¥${parseFloat(result.total_amount).toFixed(2)}`);
        clearCart(); // 清空购物车
        customerNameInput.value = "顾客"; // 重置顾客名
    } catch (error) {
        console.error('下单失败:', error);
        showModal(`下单失败: ${error.message}`, true);
    } finally {
        placeOrderBtn.disabled = false;
        place_order_btn.textContent = '下单';
    }
}

// --- LLM建议 ---
async function fetchRecipeSuggestion() {
    if (cart.length === 0) {
        llmSuggestionDiv.innerHTML = '<p class="text-orange-600">请先选择一些菜品，我才能给您更好的搭配建议哦！</p>';
        return;
    }

    const currentDishNames = cart.map(item => item.name);
    const preferences = userPreferencesInput.value.trim();

    const requestData = {
        current_dishes: currentDishNames,
        preferences: preferences,
    };

    try {
        getSuggestionBtn.disabled = true;
        getSuggestionBtn.textContent = '正在思考...';
        llmSuggestionDiv.innerHTML = '<p>正在向大厨顾问请求建议...</p>';

        const response = await fetch(`${API_BASE_URL}/recipe-suggestion`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData),
        });
        
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || `HTTP error! status: ${response.status}`);
        }

        llmSuggestionDiv.innerHTML = `<p class="font-semibold mb-2">大厨搭配建议:</p><div class="whitespace-pre-wrap">${result.suggestion}</div>`;
    } catch (error) {
        console.error('获取建议失败:', error);
        llmSuggestionDiv.innerHTML = `<p class="text-red-500">获取建议失败: ${error.message}</p>`;
        showModal(`获取建议失败: ${error.message}`, true);
    } finally {
        getSuggestionBtn.disabled = false;
        getSuggestionBtn.textContent = '获取建议';
    }
}


// --- 事件监听器 ---
document.addEventListener('DOMContentLoaded', () => {
    fetchMenu(); // 页面加载时获取菜单
    renderCart(); // 初始化购物车显示

    if (placeOrderBtn) {
        placeOrderBtn.addEventListener('click', placeOrder);
    }
    if (clearCartBtn) {
        clearCartBtn.addEventListener('click', clearCart);
    }
    if (getSuggestionBtn) {
        getSuggestionBtn.addEventListener('click', fetchRecipeSuggestion);
    }
});
