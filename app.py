from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import pymysql
import datetime
import os  # 新增导入 os 模块，用于读取云端环境变量

app = Flask(__name__)
app.secret_key = 'apple_rumor_super_secret_key'

# 修改为动态获取环境变量：如果在云端，读取云端配置；如果在本地，默认使用你的本地配置
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', '123456'),  # 你的本地 MySQL 密码
    'database': os.environ.get('DB_NAME', 'apple_rumor_db'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


# ==========================================
# 核心引擎：自动建表与注入测试数据
# ==========================================
def init_system_data():
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # 1. 自动建表逻辑 (防止云端全新数据库没有表导致崩溃)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(100) NOT NULL,
                    role VARCHAR(20) DEFAULT 'user'
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rumors (
                    rumor_id INT AUTO_INCREMENT PRIMARY KEY,
                    category VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 补充 predictions 表，防止底部关联查询 API 报错
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    rumor_id INT NOT NULL,
                    confidence_level INT DEFAULT 0,
                    vote_type INT DEFAULT 1
                )
            """)

            # 2. 自动注入 6 条高价值测试数据
            cursor.execute("SELECT COUNT(*) as cnt FROM rumors")
            if cursor.fetchone()['cnt'] < 6:
                # 如果数据太少，先清空，再注入顶级预测数据
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
                    cursor.execute("INSERT INTO rumors (category, content, source) VALUES (%s, %s, %s)", d)
                connection.commit()
    except Exception as e:
        print("数据初始化失败:", e)
    finally:
        if 'connection' in locals() and connection.open: connection.close()


# ==========================================
# 路由逻辑
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            connection = pymysql.connect(**db_config)
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE username = %s AND password_hash = %s"
                cursor.execute(sql, (username, password))
                user = cursor.fetchone()
                if user:
                    session['username'] = user['username']
                    return redirect(url_for('dashboard'))
                else:
                    return render_template('login.html', error="系统拒绝访问：指令序列错误。")
        finally:
            if 'connection' in locals() and connection.open: connection.close()
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            connection = pymysql.connect(**db_config)
            with connection.cursor() as cursor:
                sql = "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'user')"
                cursor.execute(sql, (username, password))
            connection.commit()
            return redirect(url_for('login'))
        except Exception:
            return render_template('register.html', error="注册失败，操作员代号已被占用。")
        finally:
            if 'connection' in locals() and connection.open: connection.close()
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'username' not in session: return redirect(url_for('login'))
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM rumors ORDER BY created_at DESC")
            all_rumors = cursor.fetchall()
            for r in all_rumors:
                if 'created_at' in r and r['created_at']:
                    r['created_at'] = str(r['created_at'])
    finally:
        if 'connection' in locals() and connection.open: connection.close()
    return render_template('dashboard.html', username=session['username'], rumors=all_rumors)


@app.route('/add_rumor', methods=['POST'])
def add_rumor():
    if 'username' not in session: return redirect(url_for('login'))
    category, content, source = request.form['category'], request.form['content'], request.form['source']
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO rumors (category, content, source) VALUES (%s, %s, %s)",
                           (category, content, source))
        connection.commit()
    finally:
        if 'connection' in locals() and connection.open: connection.close()
    return redirect(url_for('dashboard'))


@app.route('/delete_rumor/<int:rumor_id>')
def delete_rumor(rumor_id):
    if 'username' not in session: return redirect(url_for('login'))
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM rumors WHERE rumor_id = %s", (rumor_id,))
        connection.commit()
    finally:
        if 'connection' in locals() and connection.open: connection.close()
    return redirect(url_for('dashboard'))


# ==========================================
# 核心新增：一键恢复初始快照数据
# ==========================================
@app.route('/restore_data')
def restore_data():
    if 'username' not in session: return redirect(url_for('login'))
    init_system_data()  # 重新触发注入 6 条顶级情报的逻辑
    return redirect(url_for('dashboard'))


@app.route('/api/rumor/<int:rumor_id>')
def get_rumor_data(rumor_id):
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = """
                SELECT r.content AS 'rumor_content', COALESCE(SUM(p.confidence_level), 0) AS 'total_weight',
                COALESCE(SUM(CASE WHEN p.vote_type = 1 THEN p.confidence_level ELSE 0 END), 0) AS 'reliable_score',
                COALESCE(ROUND((SUM(CASE WHEN p.vote_type = 1 THEN p.confidence_level ELSE 0 END) / NULLIF(SUM(p.confidence_level), 0)) * 100, 2), 0) AS 'credibility_percentage'
                FROM rumors r LEFT JOIN predictions p ON r.rumor_id = p.rumor_id WHERE r.rumor_id = %s GROUP BY r.rumor_id, r.content;
            """
            cursor.execute(sql, (rumor_id,))
            result = cursor.fetchone()
        return jsonify({"code": 200, "data": result})
    finally:
        if 'connection' in locals() and connection.open: connection.close()


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    # 启动前自动执行注入 6 条数据
    init_system_data()
    app.run(debug=True, port=8000)