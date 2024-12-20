// 添加全局变量
let currentDate = new Date().toISOString().split('T')[0];
let currentEditId = null;

// 检查登录状态
async function checkAuth() {
    try {
        const response = await fetch('/api/user');
        if (!response.ok) {
            window.location.href = '/login';
            return;
        }
        const user = await response.json();
        document.getElementById('username').textContent = user.username;
    } catch (error) {
        window.location.href = '/login';
    }
}

// 登出函数
async function logout() {
    try {
        const response = await fetch('/api/logout', {
            method: 'POST'
        });
        
        if (response.ok) {
            window.location.href = '/login';
        }
    } catch (error) {
        alert('登出失败，请重试');
    }
}

// 页面加载时初始化日期选择器
document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();  // 先检查登录状态
    const dateSelector = document.getElementById('dateSelector');
    dateSelector.value = currentDate;
    fetchTodos();
});

// 日期改变处理函数
async function changeDate(date) {
    currentDate = date;
    fetchTodos();
}

// 获取所有待办事项的函数
async function fetchTodos() {
    try {
        const response = await fetch(`/api/todos/date/${currentDate}`);
        const todos = await response.json();
        displayTodos(todos);
    } catch (error) {
        alert('获取待办事项失败');
    }
}

// 显示待办事项列表的函数
function displayTodos(todos) {
    const todoList = document.getElementById('todoList');
    todoList.innerHTML = '';
    
    if (todos.length === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        emptyState.innerHTML = `
            <i class="bi bi-clipboard"></i>
            <p>今天还没有待办事项</p>
        `;
        todoList.appendChild(emptyState);
        return;
    }
    
    todos.forEach(todo => {
        const li = document.createElement('li');
        li.className = `list-group-item ${todo.completed ? 'completed' : ''}`;
        
        // 构建时间信息，使用更紧凑的格式
        const timeInfo = todo.start_time || todo.end_time ? `
            <span class="todo-time">
                ${todo.start_time || '--:--'}
                <i class="bi bi-arrow-right"></i>
                ${todo.end_time || '--:--'}
            </span>
        ` : '';
        
        li.innerHTML = `
            <div class="todo-content">
                <span class="todo-item" onclick="toggleTodo(${todo.id})">
                    <i class="bi ${todo.completed ? 'bi-check-circle-fill' : 'bi-circle'} me-2"></i>
                    <span class="todo-text">${todo.task}</span>
                </span>
                ${timeInfo}
            </div>
            <div class="todo-actions">
                <button class="btn btn-outline-primary btn-sm btn-action" title="编辑"
                        onclick="showEditModal(${todo.id}, '${todo.task.replace(/'/g, "\\'")}', '${todo.start_time || ''}', '${todo.end_time || ''}')">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-outline-danger btn-sm btn-action" title="删除"
                        onclick="deleteTodo(${todo.id})">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
        
        todoList.appendChild(li);
    });
}

// 添加新待办事项的函数
async function addTodo() {
    /**
     * 添加新的待办事项
     * 1. 获取输入内容
     * 2. 验证输入
     * 3. 发送到后端
     * 4. 处理响应
     */
    const input = document.getElementById('todoInput');
    const startTime = document.getElementById('startTime');
    const endTime = document.getElementById('endTime');
    const task = input.value.trim();
    
    // 输入验证
    if (!task) {
        alert('请输入待办事项内容！');
        return;
    }
    
    try {
        // 发送POST请求到后端API
        const response = await fetch('/api/todos', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                task: task,
                due_date: currentDate,
                start_time: startTime.value || null,
                end_time: endTime.value || null
            })
        });
        
        if (response.ok) {
            input.value = '';
            startTime.value = '';
            endTime.value = '';
            fetchTodos();      // 刷新列表
        } else {
            const data = await response.json();
            alert(data.error || '添加失败，请重试');
        }
    } catch (error) {
        alert('网络错误，请检查连接');
    }
}

// 切换待办事项状态的函数
async function toggleTodo(id) {
    const todoItem = document.querySelector(`[onclick="toggleTodo(${id})"]`);
    const listItem = todoItem.closest('.list-group-item');
    const icon = todoItem.querySelector('i');
    
    if (todoItem) {
        todoItem.style.pointerEvents = 'none'; // 防止重复点击
        
        // 立即更新UI
        const isCompleted = listItem.classList.contains('completed');
        listItem.classList.toggle('completed');
        icon.classList.toggle('bi-circle');
        icon.classList.toggle('bi-check-circle-fill');
    }
    
    try {
        const response = await fetch(`/api/todos/${id}`, {
            method: 'PUT'
        });
        
        if (!response.ok) {
            // 如果请求失败，恢复原始状态
            listItem.classList.toggle('completed');
            icon.classList.toggle('bi-circle');
            icon.classList.toggle('bi-check-circle-fill');
            
            const data = await response.json();
            alert(data.error || '更新状态失败，请重试');
        }
    } catch (error) {
        // 发生错误时恢复原始状态
        listItem.classList.toggle('completed');
        icon.classList.toggle('bi-circle');
        icon.classList.toggle('bi-check-circle-fill');
        
        console.error('切换状态错误:', error);
        alert('网络错误，请检查连接');
    } finally {
        if (todoItem) {
            todoItem.style.pointerEvents = 'auto'; // 恢复点击
        }
    }
}

// 删除待办事项
async function deleteTodo(id) {
    if (!confirm('确定要删除这个待办事项？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/todos/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            fetchTodos();
        } else {
            const data = await response.json();
            alert(data.error || '删除失败，请重试');
        }
    } catch (error) {
        alert('网络错误，请检查连接');
    }
}

// 显示编辑模态框
function showEditModal(id, task, startTime, endTime) {
    currentEditId = id;
    const modal = new bootstrap.Modal(document.getElementById('editModal'));
    const input = document.getElementById('editInput');
    const startTimeInput = document.getElementById('editStartTime');
    const endTimeInput = document.getElementById('editEndTime');
    
    input.value = task.replace(/['"]/g, '');
    startTimeInput.value = startTime || '';
    endTimeInput.value = endTime || '';
    modal.show();
}

// 关闭模态框
function closeModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('editModal'));
    if (modal) {
        modal.hide();
        currentEditId = null;
    }
}

// 保存编辑
async function saveEdit() {
    if (!currentEditId) {
        alert('编辑ID无效');
        return;
    }

    const input = document.getElementById('editInput');
    const startTime = document.getElementById('editStartTime');
    const endTime = document.getElementById('editEndTime');
    const task = input.value.trim();
    
    if (!task) {
        alert('任务内容不能为空！');
        return;
    }
    
    try {
        const response = await fetch(`/api/todos/${currentEditId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                task: task,
                start_time: startTime.value || null,
                end_time: endTime.value || null
            })
        });
        
        if (response.ok) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('editModal'));
            modal.hide();
            currentEditId = null;
            await fetchTodos(); // 等待获取最新数据
        } else {
            const data = await response.json();
            alert(data.error || '更新失败，请重试');
        }
    } catch (error) {
        console.error('编辑错误:', error);
        alert('网络错误，请检查连接');
    }
}

// 点击模态框外部关闭模态框
window.onclick = function(event) {
    const modal = document.getElementById('editModal');
    if (event.target == modal) {
        closeModal();
    }
}