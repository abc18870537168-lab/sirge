# 导入我们需要的工具包
from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
# 设置一个用于加密用户登录状态的密钥
app.secret_key = 'apple_rumor_super_secret_key'

# ==========================================
# 数据库配置部分
# ==========================================
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
    # SQLite 默认不开启外键约束，这里强制开启，保证级联删除生效！
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_system_data():
    """系统初始化：融合了你写的专业 SQL 建表语句和测试数据"""
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()

            # 1. 创建用户表 (完全复刻你的设计)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    accuracy_score REAL DEFAULT 0.00,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. 创建爆料信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rumors (
                    rumor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,
                    status TEXT DEFAULT 'pending',
                    heat_index INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. 创建预测打分表（关联表，支持级联删除 CASCADE）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    rumor_id INTEGER NOT NULL,
                    vote_type INTEGER NOT NULL,
                    confidence_level INTEGER CHECK (confidence_level BETWEEN 1 AND 10),
                    vote_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (rumor_id) REFERENCES rumors(rumor_id) ON DELETE CASCADE,
                    UNIQUE (user_id, rumor_id)
                )
            """)

            # --- 自动塞入你写的测试数据 ---
            # 检查有没有用户，没有就模拟你写的两个用户
            cursor.execute("SELECT COUNT(*) as cnt FROM users")
            if cursor.fetchone()['cnt'] == 0:
                cursor.execute("INSERT INTO users (username, password_hash, role) VALUES ('张三', 'hash123', 'user')")
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES ('极客李四', 'hash456', 'admin')")

            # 检查有没有爆料，如果没有就把你写的爆料，外加几条撑场面的数据塞进去
            cursor.execute("SELECT COUNT(*) as cnt FROM rumors")
            if cursor.fetchone()['cnt'] == 0:
                # 你的数据
                cursor.execute(
                    "INSERT INTO rumors (category, content, source) VALUES ('核心算力 (SOC)', '将采用台积电 2nm 工艺的 A20 芯片', '郭明錤')")
                cursor.execute(
                    "INSERT INTO rumors (category, content, source) VALUES ('机身架构 (DESIGN)', '将彻底取消实体按键，采用全固态设计', '彭博社')")
                # 撑场面的数据
                cursor.execute(
                    "INSERT INTO rumors (category, content, source) VALUES ('视觉面板 (DISPLAY)', '首发新一代微透镜 OLED 面板，峰值亮度突破 4000 尼特', 'DSCC')")
                cursor.execute(
                    "INSERT INTO rumors (category, content, source) VALUES ('能源系统 (BATTERY)', '引入全新叠层电池技术，容量跃升至 5000mAh', '供应链内部线人')")

                # 模拟你的预测打分：张三打4分，李四打10分 (都针对第一条爆料 rumor_id=1)
                cursor.execute(
                    "INSERT INTO predictions (user_id, rumor_id, vote_type, confidence_level) VALUES (1, 1, 1, 4)")
                cursor.execute(
                    "INSERT INTO predictions (user_id, rumor_id, vote_type, confidence_level) VALUES (2, 1, 1, 10)")
    except Exception as e:
        print(f"系统初始化失败啦: {e}")


init_system_data()


# ==========================================
# 高级后台业务接口 (供大屏上的炫酷按钮调用)
# ==========================================

@app.route('/api/receive_spider_data', methods=['POST'])
def receive_spider_data():
    """接收本地爬虫数据的接口 (没动它，保持原样)"""
    secret_token = request.headers.get('X-Spider-Token')
    if secret_token != 'my_super_secret_spider_token_2026': return jsonify({"code": 403})
    incoming_data = request.json
    if not incoming_data: return jsonify({"code": 400})

    try:
        connection = get_db_connection()
        success_count, duplicate_count = 0, 0
        with connection:
            cursor = connection.cursor()
            for item in incoming_data:
                category = item.get('category', '未知')
                title = item.get('content', '')
                source = item.get('source', '未知信源')
                cursor.execute("SELECT rumor_id FROM rumors WHERE content = ?", (title,))
                if cursor.fetchone():
                    duplicate_count += 1
                    continue
                cursor.execute("INSERT INTO rumors (category, content, source) VALUES (?, ?, ?)",
                               (category, title, source))
                success_count += 1
        if success_count > 0:
            return jsonify({"code": 200, "msg": f"成功存入 {success_count} 条情报！"})
        else:
            return jsonify({"code": 200, "msg": f"矩阵已是最新，拦截重复 {duplicate_count} 条。"})
    except Exception as e:
        return jsonify({"code": 500})


@app.route('/api/purge_all', methods=['POST'])
def purge_all():
    """【真】应急物理销毁接口：真正去数据库里把表清空！"""
    if 'username' not in session: return jsonify({"code": 403})
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
            # 你的级联删除在这里大显身手：只要把 rumors 删了，predictions 里的打分自动就没了！
            cursor.execute("DELETE FROM rumors")
        return jsonify({"code": 200, "msg": "数据库已被彻底清空！"})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/calculate_model', methods=['GET'])
def calculate_model():
    """【真】深度演算引擎：根据信源权威度和打分表，计算真实的置信度"""
    if 'username' not in session: return jsonify({"code": 403})

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        # 拿到所有的情报
        cursor.execute("SELECT * FROM rumors")
        rumors = cursor.fetchall()

        report_data = []
        # 按分类归纳总结
        categories = set(r['category'] for r in rumors)

        for cat in categories:
            cat_rumors = [r for r in rumors if r['category'] == cat]
            node_count = len(cat_rumors)
            latest_content = cat_rumors[-1]['content']  # 取最新的一条展示

            # --- 真实的算法逻辑开始 ---
            trust_score = 50.0  # 基础分50分
            authoritative_sources = ['彭博社', '郭明錤', 'MacRumors', 'DSCC']
            core_keywords = ['台积电', '2nm', 'OLED', '固态', '电池']

            for r in cat_rumors:
                # 1. 来源加分：如果是大佬爆料的，加 15 分
                if any(s in (r['source'] or '') for s in authoritative_sources):
                    trust_score += 15.0

                # 2. 内容加分：如果提到核心黑科技词汇，加 8 分
                if any(k in r['content'] for k in core_keywords):
                    trust_score += 8.0

                # 3. 关联预测加分：去查 predictions 表，如果有人给这条打了分，提取出来综合计算
                cursor.execute("SELECT AVG(confidence_level) as avg_conf FROM predictions WHERE rumor_id = ?",
                               (r['rumor_id'],))
                pred = cursor.fetchone()
                if pred and pred['avg_conf']:
                    # 自信度是 1-10 分，我们乘以 2，最高能给总分加上 20 分！
                    trust_score += (pred['avg_conf'] * 2.0)

            # 加上节点数量的权重，但最高不超过 99.8%
            trust_score = min(99.8, trust_score + (node_count * 2.0))

            report_data.append({
                "category": cat,
                "node_count": node_count,
                "latest_content": latest_content,
                "confidence": round(trust_score, 1)
            })

        return jsonify({"code": 200, "data": report_data})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})
    finally:
        if 'connection' in locals() and connection: connection.close()


# ==========================================
# 网页路由部分 (决定用户访问哪个网址看到什么页面)
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, password))
            user = cursor.fetchone()
            if user:
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            return render_template('login.html', error="账号或密码不对哦！")
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
                cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password))
            return redirect(url_for('login'))
        except Exception:
            return render_template('register.html', error="这个名字已经有人用了。")
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
    finally:
        if 'connection' in locals() and connection: connection.close()
    return render_template('dashboard.html', username=session['username'], rumors=all_rumors)


@app.route('/add_rumor', methods=['POST'])
def add_rumor():
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
    """【真】快照恢复：先把残余的数据删光，再调用初始化函数重新生成！"""
    if 'username' not in session: return redirect(url_for('login'))
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM rumors")  # 删空
    except:
        pass

    init_system_data()  # 重新生成初始数据
    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, port=8000)
