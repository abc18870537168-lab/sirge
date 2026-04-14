# 导入我们需要的工具包
from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import sqlite3
import datetime
import os

app = Flask(__name__)
# 设置一个用于加密用户登录状态的密钥
app.secret_key = 'apple_rumor_super_secret_key'

# ==========================================
# 数据库配置部分
# ==========================================
# 获取当前代码所在的绝对路径，防止云服务器找不到数据库文件
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'apple_rumor.db')

def dict_factory(cursor, row):
    """把数据库查出来的死板数据变成字典格式，方便前端网页读取"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_connection():
    """连接到 SQLite 数据库的函数"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn

def init_system_data():
    """系统初始化函数：如果没有表就建表，如果没有数据就塞几条初始数据进去"""
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
            # 建用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user'
                )
            """)
            # 建情报数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rumors (
                    rumor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 检查一下数据库里有没有数据，少于6条就自动补齐，方便页面展示
            cursor.execute("SELECT COUNT(*) as cnt FROM rumors")
            if cursor.fetchone()['cnt'] < 6:
                cursor.execute("DELETE FROM rumors") # 先清空再放，防止重复
                core_data = [
                    ('核心算力 (SOC)', '将采用台积电 2nm 工艺的 A20 仿生芯片，NPU 算力提升 40%', '郭明錤 (Ming-Chi Kuo)'),
                    ('光学影像 (CAMERA)', '主摄升级为 1 英寸超大底，配备全新可变光圈与四棱镜长焦镜头', '彭博社 (Bloomberg)'),
                    ('显示面板 (DISPLAY)', '首发新一代微透镜 OLED 面板，峰值亮度突破 4000 尼特，极窄边框', 'DSCC (Ross Young)'),
                    ('机身架构 (DESIGN)', '彻底取消所有实体按键，采用固态马达阵列提供高精度触觉反馈', 'MacRumors'),
                    ('能源系统 (BATTERY)', '引入全新叠层电池技术，容量跃升至 5000mAh，支持 40W 高速闪充', '供应链内部线人'),
                    ('人工智能 (AI CORE)', '独占 Apple Intelligence 2.0 终极形态，纯端侧大模型重构系统', 'Mark Gurman')
                ]
                for d in core_data:
                    cursor.execute("INSERT INTO rumors (category, content, source) VALUES (?, ?, ?)", d)
    except Exception as e:
        print(f"系统初始化失败啦: {e}")
    finally:
        if 'connection' in locals() and connection: connection.close()

# 每次启动程序时，都检查一遍数据库
init_system_data()

# ==========================================
# 接收本地爬虫数据的接口 (不影响前端展示，默默在后台工作)
# ==========================================
@app.route('/api/receive_spider_data', methods=['POST'])
def receive_spider_data():
    # 为了防止别人乱发数据，搞个简单的密钥验证
    secret_token = request.headers.get('X-Spider-Token')
    if secret_token != 'my_super_secret_spider_token_2026':
        return jsonify({"code": 403, "msg": "密码不对，不给你存！"})

    incoming_data = request.json
    if not incoming_data:
        return jsonify({"code": 400, "msg": "传过来的数据是空的哦"})

    try:
        connection = get_db_connection()
        success_count = 0
        duplicate_count = 0

        with connection:
            cursor = connection.cursor()
            # 遍历传过来的数据，一条条存进去
            for item in incoming_data:
                category = item.get('category', '未知')
                title = item.get('content', '')
                source = item.get('source', '未知信源')

                # 存之前先查一下，如果标题一样就跳过，防止大屏上出现一堆重复的新闻
                cursor.execute("SELECT rumor_id FROM rumors WHERE content = ?", (title,))
                if cursor.fetchone():
                    duplicate_count += 1
                    continue

                # 把新数据存进数据库
                cursor.execute("INSERT INTO rumors (category, content, source) VALUES (?, ?, ?)", 
                               (category, title, source))
                success_count += 1

        if success_count > 0:
            return jsonify({"code": 200, "msg": f"太棒了，成功存进去了 {success_count} 条新数据！"})
        else:
            return jsonify({"code": 200, "msg": f"数据库里都有了，拦截了重复的 {duplicate_count} 条。"})

    except Exception as e:
        return jsonify({"code": 500, "msg": f"后端出错了: {str(e)}"})

# ==========================================
# 网页路由部分 (决定用户访问哪个网址看到什么页面)
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def login():
    """登录页面的逻辑"""
    if request.method == 'POST':
        # 拿到用户输入的账号密码
        username = request.form['username']
        password = request.form['password']
        
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            # 去数据库里找有没有这个人和这个密码
            cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, password))
            user = cursor.fetchone()
            if user:
                # 登录成功，记录状态并跳转到大屏
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            # 失败就返回错误提示
            return render_template('login.html', error="账号或密码不对哦！")
        finally:
            if 'connection' in locals() and connection: connection.close()
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面的逻辑"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            connection = get_db_connection()
            with connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password))
            # 注册完跳回登录页
            return redirect(url_for('login'))
        except Exception:
            return render_template('register.html', error="这个名字已经有人用了。")
        finally:
            if 'connection' in locals() and connection: connection.close()
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    """核心大屏页面的逻辑"""
    # 没登录不让进
    if 'username' not in session: return redirect(url_for('login'))
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        # 把所有新闻按时间倒序拿出来，最新的在最前面
        cursor.execute("SELECT * FROM rumors ORDER BY created_at DESC")
        all_rumors = cursor.fetchall()
    finally:
        if 'connection' in locals() and connection: connection.close()
        
    # 把当前用户名和查到的数据送给网页去显示
    return render_template('dashboard.html', username=session['username'], rumors=all_rumors)

@app.route('/add_rumor', methods=['POST'])
def add_rumor():
    """页面上那个手动添加情报的接口"""
    if 'username' not in session: return redirect(url_for('login'))
    cat = request.form['category']
    con = request.form['content']
    src = request.form['source']
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO rumors (category, content, source) VALUES (?, ?, ?)", (cat, con, src))
    finally:
        if 'connection' in locals() and connection: connection.close()
    return redirect(url_for('dashboard'))

@app.route('/delete_rumor/<int:rumor_id>')
def delete_rumor(rumor_id):
    """点击卡片右下角 PURGE 按钮删除单条数据的接口"""
    if 'username' not in session: return redirect(url_for('login'))
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM rumors WHERE rumor_id = ?", (rumor_id,))
    finally:
        if 'connection' in locals() and connection: connection.close()
    return redirect(url_for('dashboard'))

@app.route('/restore_data')
def restore_data():
    """设置页面里的恢复数据接口"""
    if 'username' not in session: return redirect(url_for('login'))
    init_system_data()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    """退出登录"""
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)
