from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import sqlite3
import datetime
import os

app = Flask(__name__)
app.secret_key = 'apple_rumor_super_secret_key'

# ==========================================
# 核心配置：云端绝对路径适配 (确保数据库安全)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'apple_rumor.db')

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn

# ==========================================
# 核心引擎：初始化与静默建表
# ==========================================
def init_system_data():
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
            # 开启外键约束，这里不直接写 ON DELETE CASCADE，保持默认安全策略
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rumors (
                    rumor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rumor_id INTEGER NOT NULL,
                    confidence_level INTEGER DEFAULT 0,
                    vote_type INTEGER DEFAULT 1,
                    FOREIGN KEY(rumor_id) REFERENCES rumors(rumor_id) ON DELETE CASCADE
                )
            """)

            # 初始高价值情报注入
            cursor.execute("SELECT COUNT(*) as cnt FROM rumors")
            if cursor.fetchone()['cnt'] < 6:
                cursor.execute("DELETE FROM rumors")
                core_data = [
                    ('核心算力 (SOC)', '将采用台积电 2nm 工艺的 A20 仿生芯片，NPU 算力提升 40%', '郭明錤 (Ming-Chi Kuo)'),
                    ('光学影像 (CAMERA)', '主摄升级为 1 英寸超大底，配备全新可变光圈与四棱镜长焦镜头', '彭博社 (Bloomberg)'),
                    ('显示面板 (DISPLAY)', '首发新一代微透镜 OLED 面板，峰值亮度突破 4000 尼特，极窄边框', 'DSCC (Ross Young)'),
                    ('机身架构 (DESIGN)', '彻底取消所有实体按键，采用固态马达阵列提供高精度触觉反馈', 'MacRumors'),
                    ('能源系统 (BATTERY)', '引入全新叠层电池技术，容量跃升至 5000mAh，支持 40W 高速闪充', '供应链内部线人'),
                    ('人工智能 (AI CORE)', '独占 Apple Intelligence 2.0 终极形态，纯端侧百亿参数大模型重构系统', 'Mark Gurman')
                ]
                for d in core_data:
                    cursor.execute("INSERT INTO rumors (category, content, source) VALUES (?, ?, ?)", d)
    except Exception as e:
        print(f"系统初始化失败: {e}")
    finally:
        if 'connection' in locals() and connection: connection.close()

init_system_data()

# ==========================================
# 独立物理爬虫接收接口 (SPIDER RECEIVER PROTOCOL)
# ==========================================
@app.route('/api/receive_spider_data', methods=['POST'])
def receive_spider_data():
    # 密钥验证，防止非法投毒
    secret_token = request.headers.get('X-Spider-Token')
    if secret_token != 'my_super_secret_spider_token_2026':
        return jsonify({"code": 403, "msg": "非法调用，拒绝接入"})

    incoming_data = request.json
    if not incoming_data:
        return jsonify({"code": 400, "msg": "空数据流"})

    try:
        connection = get_db_connection()
        success_count = 0
        duplicate_count = 0
        latest_item = None

        with connection:
            cursor = connection.cursor()
            for item in incoming_data:
                category = item.get('category', '未知')
                title = item.get('content', '')
                source = item.get('source', '未知信源')

                # 查重防冗余
                cursor.execute("SELECT rumor_id FROM rumors WHERE content = ?", (title,))
                if cursor.fetchone():
                    duplicate_count += 1
                    continue

                # 物理注入
                cursor.execute("INSERT INTO rumors (category, content, source) VALUES (?, ?, ?)",
                               (category, title, source))
                success_count += 1
                latest_item = {"category": category, "content": title}

        if success_count > 0:
            return jsonify({"code": 200, "msg": f"成功接收并写入 {success_count} 条物理情报！", "data": latest_item})
        else:
            return jsonify({"code": 200, "msg": f"矩阵已是最新，拦截重复流 {duplicate_count} 条。"})

    except Exception as e:
        return jsonify({"code": 500, "msg": f"云端数据库写入崩溃: {str(e)}"})

# ==========================================
# 路由逻辑 (WEB ROUTES)
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, password))
            user = cursor.fetchone()
            if user:
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            return render_template('login.html', error="系统拒绝访问：指令序列错误。")
        finally:
            if 'connection' in locals() and connection: connection.close()
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        try:
            connection = get_db_connection()
            with connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'user')", (username, password))
            return redirect(url_for('login'))
        except Exception:
            return render_template('register.html', error="注册失败，操作员代号已被占用。")
        finally:
            if 'connection' in locals() and connection: connection.close()
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session: return redirect(url_for('login'))
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM rumors ORDER BY created_at DESC")
        all_rumors = cursor.fetchall()
        for r in all_rumors:
            if r['created_at']: r['created_at'] = str(r['created_at'])
    finally:
        if 'connection' in locals() and connection: connection.close()
    return render_template('dashboard.html', username=session['username'], rumors=all_rumors)

@app.route('/add_rumor', methods=['POST'])
def add_rumor():
    if 'username' not in session: return redirect(url_for('login'))
    cat, con, src = request.form['category'], request.form['content'], request.form['source']
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
    if 'username' not in session: return redirect(url_for('login'))
    init_system_data()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)
