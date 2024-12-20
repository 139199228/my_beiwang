# 导入所需的库
from flask import Flask, render_template, request, jsonify, session, redirect, url_for  # Flask框架相关组件
import sqlite3  # SQLite数据库
from datetime import datetime  # 处理日期时间
import hashlib
from functools import wraps
import random
import string
from io import BytesIO
import base64
import xml.etree.ElementTree as ET

app = Flask(__name__)  # 创建Flask应用实例

# 设置 Flask session 密钥
app.secret_key = 'your-secret-key-here'  # 在实际应用中使用安全的随机密钥

# 定义登录验证装饰器 - 移到最前面
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # 对于页面请求返回重定向，对于API请求返回JSON
            if request.path.startswith('/api/'):
                return jsonify({'error': '请先登录'}), 401
            else:
                return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# 密码加密函数
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 数���库初始化函数
def init_db():
    """
    初始化数据库：创建用户表和待办事项表
    """
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # 删除旧表
        c.execute('DROP TABLE IF EXISTS todos')
        c.execute('DROP TABLE IF EXISTS users')
        
        # 创建用户表
        c.execute('''CREATE TABLE users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE NOT NULL,
                      password TEXT NOT NULL,
                      created_at TIMESTAMP NOT NULL)
                  ''')
        
        # 创建待办事项表（添加user_id外键）
        c.execute('''CREATE TABLE todos
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER NOT NULL,
                      task TEXT NOT NULL,
                      created_at TIMESTAMP NOT NULL,
                      due_date DATE NOT NULL,
                      start_time TIME,
                      end_time TIME,
                      completed BOOLEAN NOT NULL DEFAULT 0,
                      FOREIGN KEY (user_id) REFERENCES users (id))
                  ''')
        
        conn.commit()
        print("数据库初始化成功！")
    except sqlite3.Error as e:
        print(f"数据库初始化错误: {e}")
        raise
    finally:
        if conn:
            conn.close()

# 获取数据库连接
def get_db():
    """
    创建数据库连接并设置行工厂
    返回: sqlite3.Connection对象
    """
    try:
        conn = sqlite3.connect('database.db', detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row  # 允许通过列名访问数据
        # 确保数据库支持中文
        conn.execute('PRAGMA encoding="UTF-8"')
        return conn
    except sqlite3.Error as e:
        print(f"数据库连接错误: {e}")
        raise

# 关闭数据库连接
def close_db(conn):
    """
    安全关闭数据库连接
    参数: conn - 数据库连接对象
    """
    if conn is not None:
        conn.close()

# 添加在其他路由前面
@app.route('/login')
def login_page():
    # 如果用户已登录，直接重定向到主页
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

# 修改首页路由，添加登录验证
@app.route('/')
@login_required
def index():
    """返回主页面"""
    return render_template('index.html')

# API路由：获取所有待办事项
@app.route('/api/todos', methods=['GET'])
def get_todos():
    """
    获取所有待办事，按创建时间降序排序
    返回: JSON格式的待办事列表
    """
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM todos ORDER BY created_at DESC')
        todos = [{'id': row[0], 
                 'task': row[1], 
                 'created_at': row[2], 
                 'completed': bool(row[3])} 
                for row in c.fetchall()]
        return jsonify(todos)
    finally:
        close_db(conn)

# API路由：添加新待办事项
@app.route('/api/todos', methods=['POST'])
def add_todo():
    """
    添加新的待办事项
    接收: JSON格式的task、due_date、start_time、end_time字段
    返回: 新创建的待办事项信息
    """
    task = request.json.get('task')
    due_date = request.json.get('due_date')
    start_time = request.json.get('start_time')
    end_time = request.json.get('end_time')
    
    if not task or not due_date:
        return jsonify({'error': '任务内容和日期不能为空'}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''INSERT INTO todos 
                    (user_id, task, created_at, due_date, start_time, end_time) 
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (session['user_id'], task, current_time, due_date, start_time, end_time))
        conn.commit()
        todo_id = c.lastrowid
        return jsonify({
            'id': todo_id, 
            'task': task, 
            'due_date': due_date,
            'start_time': start_time,
            'end_time': end_time,
            'completed': False
        }), 201
    except sqlite3.Error as e:
        return jsonify({'error': f'数据库错误: {str(e)}'}), 500
    finally:
        close_db(conn)

# API路由：切换待办事项状态
@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
@login_required
def toggle_todo(todo_id):
    """
    切换指定待办事项的完成状态
    参数: todo_id - 待办事项ID
    返回: 更新后的完成状态
    """
    try:
        conn = get_db()
        c = conn.cursor()
        # 确保只能修改自己的待办事项
        c.execute('''UPDATE todos 
                    SET completed = NOT completed 
                    WHERE id = ? AND user_id = ?''', 
                 (todo_id, session['user_id']))
        conn.commit()
        
        if c.rowcount == 0:
            return jsonify({'error': '待办事项不存在或无权限'}), 404
            
        # 获取更新后的状态
        c.execute('SELECT completed FROM todos WHERE id = ? AND user_id = ?', 
                 (todo_id, session['user_id']))
        row = c.fetchone()
        if row:
            completed = bool(row[0])
            return jsonify({'completed': completed, 'success': True})
        return jsonify({'error': '待办事项不存在'}), 404
    except sqlite3.Error as e:
        return jsonify({'error': f'更新失败: {str(e)}'}), 500
    finally:
        close_db(conn)

# API路由：删除待办事项
@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
@login_required
def delete_todo(todo_id):
    """
    删除指定的待办事项
    参数: todo_id - 待办事项ID
    返回: 删除操作的结果
    """
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM todos WHERE id = ? AND user_id = ?', 
                 (todo_id, session['user_id']))
        conn.commit()
        
        if c.rowcount == 0:
            return jsonify({'error': '待办事项不存在或无权限'}), 404
            
        return jsonify({'success': True, 'message': '删除成功'}), 200
    except sqlite3.Error as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500
    finally:
        close_db(conn)

# API路由：编辑待办事项
@app.route('/api/todos/<int:todo_id>', methods=['PATCH'])
@login_required
def edit_todo(todo_id):
    """
    编辑待办事项的内
    参数: todo_id - 待办事项ID
    请求体: {'task': '新的任务内容', 'start_time': '开始时间', 'end_time': '结束时间'}
    返回: 更新后的待办事项信息
    """
    task = request.json.get('task')
    start_time = request.json.get('start_time')
    end_time = request.json.get('end_time')
    
    if not task:
        return jsonify({'error': '任务内容不能为空'}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''UPDATE todos 
                    SET task = ?, start_time = ?, end_time = ? 
                    WHERE id = ? AND user_id = ?''', 
                 (task, start_time, end_time, todo_id, session['user_id']))
        conn.commit()
        
        if c.rowcount == 0:
            return jsonify({'error': '待办事项不存在或无权限'}), 404
        
        # 获取更新后的完整数据
        c.execute('SELECT * FROM todos WHERE id = ?', (todo_id,))
        row = c.fetchone()
        updated_todo = {
            'id': row[0],
            'task': row[2],
            'created_at': row[3],
            'due_date': row[4],
            'start_time': row[5],
            'end_time': row[6],
            'completed': bool(row[7])
        }
        return jsonify(updated_todo), 200
    except sqlite3.Error as e:
        return jsonify({'error': f'更新失败: {str(e)}'}), 500
    finally:
        close_db(conn)

# 添加验证码生成函数
def generate_captcha():
    """生成验证码及其SVG图像"""
    # 生成随机验证���
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(chars) for _ in range(4))
    
    # 创建SVG
    svg = ET.Element('svg', {
        'width': '120',
        'height': '40',
        'xmlns': 'http://www.w3.org/2000/svg'
    })
    
    # 添加背景
    ET.SubElement(svg, 'rect', {
        'width': '120',
        'height': '40',
        'fill': '#f8f9fa'
    })
    
    # 添加干扰线
    for _ in range(4):
        x1 = str(random.randint(0, 120))
        y1 = str(random.randint(0, 40))
        x2 = str(random.randint(0, 120))
        y2 = str(random.randint(0, 40))
        ET.SubElement(svg, 'line', {
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2,
            'stroke': '#dee2e6',
            'stroke-width': '1'
        })
    
    # 添加文字
    for i, char in enumerate(code):
        x = 20 + i * 25
        y = random.randint(25, 35)
        rotation = random.randint(-15, 15)
        ET.SubElement(svg, 'text', {
            'x': str(x),
            'y': str(y),
            'fill': '#0d6efd',
            'font-size': '24',
            'transform': f'rotate({rotation} {x} {y})',
            'font-family': 'Arial'
        }).text = char
    
    # 转换为字符串
    svg_str = ET.tostring(svg, encoding='unicode')
    svg_base64 = base64.b64encode(svg_str.encode()).decode()
    
    return code, f'data:image/svg+xml;base64,{svg_base64}'

# 添加获取验证码的路由
@app.route('/api/captcha', methods=['GET'])
def get_captcha():
    """获取验证码"""
    code, image = generate_captcha()
    session['captcha'] = code
    return jsonify({'image': image})

# 修改注册路由，添加验证码验证
@app.route('/api/register', methods=['POST'])
def register():
    username = request.json.get('username')
    password = request.json.get('password')
    captcha = request.json.get('captcha')
    
    if not username or not password or not captcha:
        return jsonify({'error': '所有字段都必须填写'}), 400
    
    # 验证码验证（不区分大小写）
    if 'captcha' not in session or captcha.upper() != session['captcha']:
        return jsonify({'error': '验证码错误'}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        hashed_password = hash_password(password)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        c.execute('INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
                 (username, hashed_password, current_time))
        conn.commit()
        
        # 清除验证码
        session.pop('captcha', None)
        return jsonify({'message': '注册成功'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': '用户名已存在'}), 400
    except sqlite3.Error as e:
        return jsonify({'error': f'注册失败: {str(e)}'}), 500
    finally:
        close_db(conn)

# 登录路由
@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, password FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        
        if user and user[1] == hash_password(password):
            session['user_id'] = user[0]
            session['username'] = username
            return jsonify({'message': '登录成功', 'username': username}), 200
        else:
            return jsonify({'error': '用户名或密码错误'}), 401
    except sqlite3.Error as e:
        return jsonify({'error': f'登录失败: {str(e)}'}), 500
    finally:
        close_db(conn)

# 登出路由
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': '已登出'}), 200

# 获取当��用户信息
@app.route('/api/user', methods=['GET'])
def get_user():
    if 'user_id' in session:
        return jsonify({
            'user_id': session['user_id'],
            'username': session['username']
        })
    return jsonify({'error': '未登录'}), 401

# 修改获取待办事项的路由
@app.route('/api/todos/date/<date>', methods=['GET'])
@login_required
def get_todos_by_date(date):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''SELECT * FROM todos 
                    WHERE user_id = ? AND due_date = ? 
                    ORDER BY created_at DESC''', 
                 (session['user_id'], date))
        todos = [{'id': row[0], 
                 'task': row[2], 
                 'created_at': row[3],
                 'due_date': row[4],
                 'start_time': row[5],
                 'end_time': row[6],
                 'completed': bool(row[7])} 
                for row in c.fetchall()]
        return jsonify(todos)
    except sqlite3.Error as e:
        return jsonify({'error': f'数据库错误: {str(e)}'}), 500
    finally:
        close_db(conn)

# 确保在应用启动时初始化数据库
if __name__ == '__main__':
    print("正在初始化数据库...")
    init_db()  # 始化数据库
    print("启动Flask应用...")
    app.run(debug=True)  # 以调试模式运行服务器