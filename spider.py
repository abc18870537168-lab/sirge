import requests
from bs4 import BeautifulSoup
import time
import re

# ==========================================
# 预测中台 - 多源物理爬虫引擎 (iPhone 18 系列终极精准版)
# 数据源 01: Bilibili 官方搜索 API
# 数据源 02: Bing 科技资讯 RSS
# ==========================================

TARGET_API_URL = "http://mrge.pythonanywhere.com/api/receive_spider_data"
SECRET_TOKEN = "my_super_secret_spider_token_2026"


def clean_html(raw_text):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_text).replace('&quot;', '"')


def get_bilibili_data():
    print("[跨站嗅探] 正在接入源 01: Bilibili 官方数据流...")
    # 搜索词已改为 iPhone 18
    url = "https://api.bilibili.com/x/web-interface/search/all/v2?keyword=iPhone%2018"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, headers=headers, proxies={"http": None, "https": None}, timeout=10)
        data = res.json()
        videos = next(
            (item['data'] for item in data.get('data', {}).get('result', []) if item['result_type'] == 'video'), [])
        return [{'title': clean_html(v.get('title', '')), 'source': f"B站视频: {v.get('author', '')}"} for v in videos]
    except Exception as e:
        print(f"[源 01 失败] {e}")
        return []


def get_bing_data():
    print("[跨站嗅探] 正在接入源 02: Bing 全网科技资讯 RSS...")
    # 搜索词已改为 iPhone 18
    url = "https://cn.bing.com/news/search?q=iPhone+18&format=rss"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, headers=headers, proxies={"http": None, "https": None}, timeout=10)
        soup = BeautifulSoup(res.content, 'xml')
        items = soup.find_all('item')
        return [{'title': item.title.text, 'source': "Bing 科技资讯"} for item in items]
    except Exception as e:
        print(f"[源 02 失败] {e}")
        return []


def fetch_real_apple_rumors():
    print("\n[系统提示] 启动多源聚合爬虫，开始执行【最高严格度】硬件特征过滤...")

    raw_data = get_bilibili_data() + get_bing_data()
    extracted_data = []
    seen_titles = set()

    for item in raw_data:
        title = item['title']
        compressed_title = title.lower().replace(" ", "").replace("-", "")

        # 核心拦截：必须严格包含 iphone18 或 苹果18 或 a20
        if "iphone18" not in compressed_title and "苹果18" not in compressed_title and "a20" not in compressed_title:
            continue

        if title in seen_titles:
            continue
        seen_titles.add(title)

        if any(k in compressed_title for k in ['屏', '外观', '设计', '按键', '模具']):
            category = '屏幕外观'
        elif any(k in compressed_title for k in ['芯片', '处理器', 'a20', '台积电', '性能']):
            category = '处理器'
        elif any(k in compressed_title for k in ['相机', '镜头', '拍照', '光圈', '长焦']):
            category = '拍照摄像'
        elif any(k in compressed_title for k in ['电池', '充电', '快充', '续航', '容量']):
            category = '电池续航'
        else:
            category = '其他爆料'

        extracted_data.append({
            'category': category,
            'content': title,
            'source': item['source']
        })

        if len(extracted_data) >= 8:
            break

    return extracted_data


def push_to_cloud_matrix(data_list):
    if not data_list:
        print("[系统提示] 严格过滤后，全网目前暂无符合要求的全新爆料。")
        return

    print(f"\n[数据同步] 成功提纯 {len(data_list)} 条纯正 18 系列情报，正在推送至云端大屏...")

    headers = {
        'Content-Type': 'application/json',
        'X-Spider-Token': SECRET_TOKEN
    }

    try:
        response = requests.post(TARGET_API_URL, json=data_list, headers=headers, timeout=10)

        if response.status_code == 200:
            print(f"[云端回复] {response.json()['msg']}")
        else:
            print(f"[上传错误] 云端拒绝了请求，状态码: {response.status_code}")

    except Exception as e:
        print(f"[网络错误] 连不上你的云端服务器: {e}")


if __name__ == '__main__':
    print("=" * 60)
    print("   iPhone 18 系列终极聚合爬虫 (双源防伪版)")
    print("=" * 60)

    new_rumors = fetch_real_apple_rumors()
    time.sleep(1)
    push_to_cloud_matrix(new_rumors)

    print("\n>>> 抓取任务圆满结束，快去网页大屏刷新看看吧！ <<<")
