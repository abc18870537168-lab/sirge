from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import sqlite3
import datetime
import os
import requests
from bs4 import BeautifulSoup
import time

app = Flask(__name__)
app.secret_key = 'apple_rumor_super_secret_key'

# ==========================================
# 核心配置：云端路径适配 (确保数据库不迷路)
# ==========================================
# 获取当前文件所在的绝对目录，确保在 PythonAnywhere 上能准确找到数据库
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
# 真实全网爬虫模块 (SPIDER ENGINE)
# ==========================================
@app.route('/api/run_spider', methods=['POST'])
def run_spider():
    """
    触发真实爬虫协议：
    从 MacRumors RSS 抓取最新情报并注入数据库
    """
    if 'username' not in session:
        return jsonify({"code": 403, "msg": "未授权的终端连接"})

    target_url = "https://feeds.macrumors.com/MacRumors-All"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # 1. 建立物理链路
        response = requests.get(target_url, headers=headers, timeout=10)
        response.raise_for_status()

        # 2. 解析截获的加密流 (RSS XML)
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')

        connection = get_db_connection()
        success_count = 0
        duplicate_count = 0
        latest_item = None

        with connection:
            cursor = connection.cursor()

            # 只处理最新的 5 条，保证响应速度
            for item in items[:5]:
                title = item.title.text.strip()
                title_lower = title.lower()

                # 战术分类引擎
                if 'iphone' in title_lower or 'ios' in title_lower:
                    category = '手机终端 (IPHONE)'
                elif 'mac' in title_lower or 'chip' in title_lower or 'm' in title_lower:
                    category = '核心算力 (SILICON)'
                elif 'watch' in title_lower or 'vision' in title_lower:
                    category = '穿戴设备 (WEARABLE)'
                elif 'display' in title_lower or 'oled' in title_lower or 'screen' in title_lower:
                    category = '视觉面板 (DISPLAY)'
                else:
                    category = '前沿生态 (ECOSYSTEM)'

                # 查重机制：避免重复注入
                cursor.execute("SELECT rumor_id FROM rumors WHERE content = ?", (title,))
                if cursor.fetchone():
                    duplicate_count += 1
                    continue

                # 执行物理注入
                cursor.execute("INSERT INTO rumors (category, content, source) VALUES (?, ?, ?)",
                               (category, title, 'MacRumors (Global)'))
                success_count += 1
                latest_item = {"category": category, "content": title}

        # 返回执行简报
        if success_count > 0:
            return jsonify({"code": 200, "msg": f"成功截获 {success_count} 条新情报！", "data": latest_item})
        else:
            return jsonify({"code": 200, "msg": f"矩阵已是最新，拦截重复流 {duplicate_count} 条。"})

    except Exception as e:
        return jsonify({"code": 500, "msg": f"链路建立失败: {str(e)}"})


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
