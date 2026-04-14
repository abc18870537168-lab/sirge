from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import sqlite3
import os
import traceback

app = Flask(__name__)
app.secret_key = 'apple_rumor_super_secret_key'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'apple_rumor.db')

# 全局变量：用于捕捉初始化时的致命错误
INIT_ERROR = None

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON") 
    return conn

def init_system_data():
    global INIT_ERROR
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
            
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
            
            # --- 智能注入初始数据 ---
            cursor.execute("SELECT user_id FROM users LIMIT 2")
            users = cursor.fetchall()
            if len(users) < 2:
                cursor.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('演示专家A', '123', 'admin')")
                cursor.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('演示专家B', '123', 'user')")
                cursor.execute("SELECT user_id FROM users LIMIT 2")
                users = cursor.fetchall()
            
            u1, u2 = users[0]['user_id'], users[1]['user_id'] if len(users) > 1 else users[0]['user_id']

            cursor.execute("SELECT COUNT(*) as cnt FROM rumors")
            if cursor.fetchone()['cnt'] == 0:
                # 【终极防弹装甲】直接动态获取最新插入的编号，彻底告别 0 字节崩溃！
                cursor.execute("INSERT INTO rumors (category, content, source) VALUES ('处理器', '全系标配台积电 2nm 工艺的 A20 芯片，性能提升巨大', '郭明錤')")
                r1_id = cursor.lastrowid # 获取这条新闻的真实 ID
                
                cursor.execute("INSERT INTO rumors (category, content, source) VALUES ('屏幕外观', '18 Pro Max 将彻底取消实体按键，采用全固态压感设计', '彭博社')")
                cursor.execute("INSERT INTO rumors (category, content, source) VALUES ('拍照摄像', '主摄升级为全新可变光圈，夜景能力史诗级提升', '数码闲聊站')")
                cursor.execute("INSERT INTO rumors (category, content, source) VALUES ('电池续航', '将采用全新高密度电池技术，支持更快的超级快充', 'MacRumors')")

                # 把打分精准绑定到第一条新闻上
                cursor.execute("INSERT INTO predictions (user_id, rumor_id, vote_type, confidence_level) VALUES (?, ?, 1, 4)", (u1, r1_id))
                cursor.execute("INSERT INTO predictions (user_id, rumor_id, vote_type, confidence_level) VALUES (?, ?, 1, 10)", (u2, r1_id))
                
    except Exception as e:
        INIT_ERROR = traceback.format_exc()
        print("初始化严重报错:", INIT_ERROR)

init_system_data()

# ==========================================
# 终极错误雷达：只要系统敢崩溃，直接把红字拍在脸上！
# ==========================================
@app.errorhandler(Exception)
def handle_exception(e):
    error_msg = traceback.format_exc()
    return f"""
    <div style="background:#111; color:white; padding:40px; font-family:sans-serif;">
        <h1 style="color:#ff4444;">🚨 警报：服务器内部崩溃啦！</h1>
        <p style="font-size:18px;">别慌！请把下面黑框里的红字全选，直接复制发给 AI：</p>
        <pre style="background:#000; color:#ff4444; padding:20px; border:1px solid #ff4444; border-radius:8px; overflow-x:auto;">{error_msg}</pre>
    </div>
    """, 500

# ==========================================
# 高级后台业务接口
# ==========================================

@app.route('/api/receive_spider_data', methods=['POST'])
def receive_spider_data():
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
                category = item.get('category', '其他爆料')
                title = item.get('content', '')
                source = item.get('source', '网络抓取')
                cursor.execute("SELECT rumor_id FROM rumors WHERE content = ?", (title,))
                if cursor.fetchone():
                    duplicate_count += 1
                    continue
                cursor.execute("INSERT INTO rumors (category, content, source) VALUES (?, ?, ?)", (category, title, source))
                success_count += 1
        if success_count > 0: return jsonify({"code": 200, "msg": f"成功抓取并写入 {success_count} 条苹果18新爆料！"})
        else: return jsonify({"code": 200, "msg": f"目前没有最新爆料，拦截了重复的 {duplicate_count} 条数据。"})
    except Exception as e: return jsonify({"code": 500})

@app.route('/api/purge_all', methods=['POST'])
def purge_all():
    if 'username' not in session: return jsonify({"code": 403})
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM rumors")
        return jsonify({"code": 200})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})

@app.route('/api/calculate_model', methods=['GET'])
def calculate_model():
    if 'username' not in session: return jsonify({"code": 403})
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM rumors")
        rumors = cursor.fetchall()
        report_data = []
        categories = set(r['category'] for r in rumors)
        
        for cat in categories:
            cat_rumors = [r for r in rumors if r['category'] == cat]
            node_count = len(cat_rumors)
            latest_content = cat_rumors[-1]['content'] 
            
            trust_score = 50.0 
            authoritative_sources = ['彭博社', '郭明錤', 'MacRumors', '数码闲聊站', '快科技', 'IT之家']
            core_keywords = ['2nm', '固态按键', '快充', '光圈', 'A20', '首发', '涨价']
            
            for r in cat_rumors:
                if any(s in (r['source'] or '') for s in authoritative_sources): trust_score += 15.0
                if any(k in r['content'] for k in core_keywords): trust_score += 8.0
                cursor.execute("SELECT AVG(confidence_level) as avg_conf FROM predictions WHERE rumor_id = ?", (r['rumor_id'],))
                pred = cursor.fetchone()
                if pred and pred['avg_conf']: trust_score += (pred['avg_conf'] * 2.0)
            
            trust_score = min(99.8, trust_score + (node_count * 2.0))
            
            report_data.append({
                "category": cat,
                "node_count": node_count,
                "latest_content": latest_content,
                "confidence": round(trust_score, 1),
                "details": cat_rumors 
            })
            
        return jsonify({"code": 200, "data": report_data})
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})
    finally:
        if 'connection' in locals() and connection: connection.close()

# ==========================================
# 网页路由部分 
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def login():
    if INIT_ERROR:
        return f"<div style='padding:40px;'><h1 style='color:red;'>🚨 数据库初始化失败！</h1><p>请把下面的红字发给 AI：</p><pre style='color:red;'>{INIT_ERROR}</pre></div>"
        
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
    if INIT_ERROR:
        return f"<div style='padding:40px;'><h1 style='color:red;'>🚨 数据库初始化失败！</h1><p>请把下面的红字发给 AI：</p><pre style='color:red;'>{INIT_ERROR}</pre></div>"
        
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
    try:
        connection = get_db_connection()
        with connection:
            cursor = connection.cursor()
            cursor.execute("DROP TABLE IF EXISTS predictions")
            cursor.execute("DROP TABLE IF EXISTS rumors")
    except:
        pass
    
    init_system_data() 
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)
