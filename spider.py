import requests
import time
import re

# ==========================================
# 本地物理爬虫引擎 (iPhone 18 Pro Max 专属狙击版)
# 数据源：Bilibili (B站) 官方搜索 API 接口
# ==========================================

# 指向你在 PythonAnywhere 部署的真实接收接口
TARGET_API_URL = "http://mrge.pythonanywhere.com/api/receive_spider_data"
# 接口握手安全验证密钥 (必须和云端 app.py 里的一致)
SECRET_TOKEN = "my_super_secret_spider_token_2026"


def clean_html(raw_text):
    """清洗 B站 API 返回的标题中携带的高亮标签（比如 <em class="keyword">）"""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_text).replace('&quot;', '"')


def fetch_real_apple_rumors():
    print("\n[系统提示] 正在启动苹果 18 Pro Max 专属数据采集协议...")

    # 核心黑科技：直接调用 B站的搜索接口，锁定关键词！
    api_url = "https://api.bilibili.com/x/web-interface/search/all/v2?keyword=iPhone%2018%20Pro%20Max"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print(f"[网络链路] 正在直连 Bilibili 官方数据接口...")
        # 请求 JSON 数据，关闭本地代理防止报错
        response = requests.get(api_url, headers=headers, proxies={"http": None, "https": None}, timeout=15)
        response.raise_for_status()

        # 将获取到的数据直接转换为 Python 字典
        data = response.json()
        extracted_data = []

        # 在复杂的 JSON 结构中，精准定位到“视频”搜索结果的列表
        results = data.get('data', {}).get('result', [])
        video_results = next((item['data'] for item in results if item['result_type'] == 'video'), [])

        print(f"[数据处理] 成功拉取底层数据，正在过滤纯正的 18 Pro Max 爆料...")

        for video in video_results:
            raw_title = video.get('title', '')
            # 清洗掉标题里的 HTML 代码
            title = clean_html(raw_title)
            title_lower = title.lower()
            # 获取发这个爆料的 UP 主名字
            author = video.get('author', 'B站UP主')

            # 【终极严格过滤】：标题必须包含 18，且必须包含 iphone 或 苹果！否则直接丢弃！
            if '18' not in title_lower or ('iphone' not in title_lower and '苹果' not in title_lower):
                continue

            # 【大白话分类引擎】：根据标题里的关键词，自动分到你设定好的 5 个大类里
            if any(keyword in title_lower for keyword in ['屏', '外观', '设计', '按键', '模具']):
                category = '屏幕外观'
            elif any(keyword in title_lower for keyword in ['芯片', '处理器', 'a20', '台积电', '性能']):
                category = '处理器'
            elif any(keyword in title_lower for keyword in ['相机', '镜头', '拍照', '光圈', '长焦']):
                category = '拍照摄像'
            elif any(keyword in title_lower for keyword in ['电池', '充电', '快充', '续航', '容量']):
                category = '电池续航'
            else:
                category = '其他爆料'

            extracted_data.append({
                'category': category,
                'content': title,
                'source': f'B站视频: {author}'
            })

            # 抓满 8 条高价值情报，立刻撤退！
            if len(extracted_data) >= 8:
                break

        return extracted_data

    except Exception as e:
        print(f"[错误] 抓取失败啦，是不是网络问题: {e}")
        return []


def push_to_cloud_matrix(data_list):
    if not data_list:
        print("[系统提示] B站目前没有搜到符合严格要求的新爆料，停止推送。")
        return

    print(f"\n[数据同步] 正在将 {len(data_list)} 条纯正爆料推送给云端大屏...")

    headers = {
        'Content-Type': 'application/json',
        'X-Spider-Token': SECRET_TOKEN
    }

    try:
        response = requests.post(TARGET_API_URL, json=data_list, headers=headers, timeout=10)

        if response.status_code == 200:
            result = response.json()
            print(f"[云端回复] {result['msg']}")
        else:
            print(f"[上传错误] 云端拒绝了请求，状态码: {response.status_code}")

    except Exception as e:
        print(f"[网络错误] 连不上你的云端服务器: {e}")


if __name__ == '__main__':
    print("=" * 55)
    print("   iPhone 18 Pro Max 专属情报爬虫 (B站API版)")
    print("=" * 55)

    # 1. 执行抓取
    new_rumors = fetch_real_apple_rumors()

    time.sleep(1)  # 装作在努力计算的样子

    # 2. 推送大屏
    push_to_cloud_matrix(new_rumors)

    print("\n>>> 抓取任务圆满结束，快去网页大屏刷新看看吧！ <<<")
