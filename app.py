from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import sqlite3
import datetime
import os
import time
import random

app = Flask(__name__)
app.secret_key = 'apple_rumor_super_secret_key'

# ==========================================
# 核心配置：云端绝对路径适配 (确保数据库不迷路)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'apple_rumor.db')


def dict_factory(cursor, row):
    """将数据库查询结果转换为字典格式，方便前端读取"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db_connection():
    """建立与 SQLite 数据库的连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn


# ==========================================
# 核心引擎：自动建表与初始数据注入
# ==========================================
def init_system_data():
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
            # 1. 创建用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user'
                )
            """)
            # 2. 创建情报表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rumors (
                    rumor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 3. 创建预测关联表 (用于 API 兼容)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rumor_id INTEGER NOT NULL,
                    confidence_level INTEGER DEFAULT 0,
                    vote_type INTEGER DEFAULT 1
                )
            """)

            # 4. 如果是新系统，注入 6 条初始高价值情报
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
        print(f"系统初始化失败: {e}")
    finally:
        if 'connection' in locals() and connection: connection.close()


# 只要程序启动（不论是本地还是云端），强制执行一次初始化
init_system_data()


# ==========================================
# 虚拟全网爬虫模块 (VIRTUAL SPIDER ENGINE - 完美绕过云端防火墙)
# ==========================================
@app.route('/api/run_spider', methods=['POST'])
def run_spider():
    if 'username' not in session:
        return jsonify({"code": 403, "msg": "未授权的终端连接"})

    # 1. 模拟真实爬虫在全网扫描的物理延迟 (停顿 1.5 秒)
    time.sleep(1.5)

    # 2. 虚拟暗网情报池（专门为了大屏展示准备的逼真数据）
    spider_sources = ['MacRumors (Global)', '彭博社内部邮件', '供应链深喉', 'X 加密频道', '台积电产能报表']
    spider_categories = ['手机终端 (IPHONE)', '核心算力 (SILICON)', '穿戴设备 (WEARABLE)', '视觉面板 (DISPLAY)',
                         '前沿生态 (ECOSYSTEM)']
    spider_contents = [
        "拦截到加密邮件：内部正在测试基于脑机接口的无感解锁技术，彻底废除 FaceID。",
        "供应链异常波动：苹果包下了全球 90% 的透明自发光纳米陶瓷材料，疑用于全玻璃机身。",
        "代工厂流出图纸：充电口完全消失，将采用磁吸式隔空微波充电技术。",
        "最新芯片架构图曝光：A20 仿生芯片将集成独立量子加密模块。",
        "穿戴设备重大突破：下一代 Vision Pro 将缩减至普通黑框眼镜大小，续航突破24小时。"
    ]

    # 3. 随机生成一条截获的情报
    category = random.choice(spider_categories)
    title = f"[自动抓取] {random.choice(spider_contents)}"
    source = random.choice(spider_sources)

    # 4. 悄悄注入你的 SQLite 数据库
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()

            # 查重拦截（虽然是随机的，但也走个真实的流程）
            cursor.execute("SELECT rumor_id FROM rumors WHERE content = ?", (title,))
            if cursor.fetchone():
                return jsonify({"code": 200, "msg": "矩阵已是最新，拦截重复流 1 条。"})

            # 执行物理注入
            cursor.execute("INSERT INTO rumors (category, content, source) VALUES (?, ?, ?)",
                           (category, title, source))

            latest_item = {"category": category, "content": title}
            return jsonify({"code": 200, "msg": "成功截获 1 条新情报！", "data": latest_item})

    except Exception as e:
        return jsonify({"code": 500, "msg": f"矩阵写入失败: {str(e)}"})


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
                cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'user')",
                               (username, password))
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
        # 格式化日期，防止前端显示问题
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
