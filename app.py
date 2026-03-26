from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import sqlite3
import datetime
import os

app = Flask(__name__)
app.secret_key = 'apple_rumor_super_secret_key'

# 核心修复 1：获取云端服务器的绝对路径，确保数据库文件永远不会“迷路”
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'apple_rumor.db')


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db_connection():
    # 使用绝对路径连接数据库
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn


# ==========================================
# 核心引擎：自动建表与注入测试数据
# ==========================================
def init_system_data():
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
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
                    vote_type INTEGER DEFAULT 1
                )
            """)

            cursor.execute("SELECT COUNT(*) as cnt FROM rumors")
            if cursor.fetchone()['cnt'] < 6:
                cursor.execute("DELETE FROM rumors")
                core_data = [
                    (
                    '核心算力 (SOC)', '将采用台积电 2nm 工艺的 A20 仿生芯片，NPU 算力提升 40%', '郭明錤 (Ming-Chi Kuo)'),
                    ('光学影像 (CAMERA)', '主摄升级为 1 英寸超大底，配备全新可变光圈与四棱镜长焦镜头',
                     '彭博社 (Bloomberg)'),
                    ('显示面板 (DISPLAY)', '首发新一代微透镜 OLED 面板，峰值亮度突破 4000 尼特，极窄边框',
                     'DSCC (Ross Young)'),
                    ('机身架构 (DESIGN)', '彻底取消所有实体按键，采用固态马达阵列提供高精度触觉反馈', 'MacRumors'),
                    ('能源系统 (BATTERY)', '引入全新叠层电池技术，容量跃升至 5000mAh，支持 40W 高速闪充',
                     '供应链内部线人'),
                    ('人工智能 (AI CORE)', '独占 Apple Intelligence 2.0 终极形态，纯端侧百亿参数大模型重构系统',
                     'Mark Gurman')
                ]
                for d in core_data:
                    cursor.execute("INSERT INTO rumors (category, content, source) VALUES (?, ?, ?)", d)
    except Exception as e:
        print("数据初始化失败:", e)
    finally:
        if 'connection' in locals() and connection: connection.close()


# 核心修复 2：把初始化数据的函数提出来，只要云端加载代码，就强制执行建表！
init_system_data()


# ==========================================
# 路由逻辑
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            sql = "SELECT * FROM users WHERE username = ? AND password_hash = ?"
            cursor.execute(sql, (username, password))
            user = cursor.fetchone()
            if user:
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="系统拒绝访问：指令序列错误。")
        finally:
            if 'connection' in locals() and connection: connection.close()
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            connection = get_db_connection()
            with connection:
                cursor = connection.cursor()
                sql = "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'user')"
                cursor.execute(sql, (username, password))
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
            if 'created_at' in r and r['created_at']:
                r['created_at'] = str(r['created_at'])
    finally:
        if 'connection' in locals() and connection: connection.close()
    return render_template('dashboard.html', username=session['username'], rumors=all_rumors)


@app.route('/add_rumor', methods=['POST'])
def add_rumor():
    if 'username' not in session: return redirect(url_for('login'))
    category = request.form['category']
    content = request.form['content']
    source = request.form['source']
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO rumors (category, content, source) VALUES (?, ?, ?)",
                           (category, content, source))
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


@app.route('/api/rumor/<int:rumor_id>')
def get_rumor_data(rumor_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        sql = """
            SELECT r.content AS 'rumor_content', COALESCE(SUM(p.confidence_level), 0) AS 'total_weight',
            COALESCE(SUM(CASE WHEN p.vote_type = 1 THEN p.confidence_level ELSE 0 END), 0) AS 'reliable_score',
            COALESCE(ROUND((SUM(CASE WHEN p.vote_type = 1 THEN p.confidence_level ELSE 0 END) * 1.0 / NULLIF(SUM(p.confidence_level), 0)) * 100, 2), 0) AS 'credibility_percentage'
            FROM rumors r LEFT JOIN predictions p ON r.rumor_id = p.rumor_id WHERE r.rumor_id = ? GROUP BY r.rumor_id, r.content;
        """
        cursor.execute(sql, (rumor_id,))
        result = cursor.fetchone()
        return jsonify({"code": 200, "data": result})
    finally:
        if 'connection' in locals() and connection: connection.close()


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, port=8000)
