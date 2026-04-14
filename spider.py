import requests
from bs4 import BeautifulSoup
import time

# ==========================================
# 本地物理爬虫引擎 (NEXUS-18 SPIDER NODE)
# 适配源: IT之家 (中文前沿科技情报)
# ==========================================

# 指向你在 PythonAnywhere 部署的真实接收接口
TARGET_API_URL = "http://mrge.pythonanywhere.com/api/receive_spider_data"

# 接口握手安全验证密钥
SECRET_TOKEN = "my_super_secret_spider_token_2026"

def fetch_real_apple_rumors():
    print("\n[SYSTEM] 正在启动 NEXUS-18 数据采集协议...")
    
    # 更换为 IT之家的中文 RSS 源
    target_url = "https://www.ithome.com/rss/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print(f"[NETWORK] 正在建立与【IT之家】情报节点的高速链路: {target_url}")
        # 关闭代理防冲突
        response = requests.get(target_url, headers=headers, proxies={"http": None, "https": None}, timeout=15)
        response.raise_for_status()

        # 解析 XML 格式
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')

        extracted_data = []
        print(f"[PROCESS] 链路握手成功，截获 {len(items)} 条原始流，正在进行特征解构...")

        # 遍历所有新闻，寻找符合我们需要的情报
        for item in items:
            title = item.title.text.strip()
            title_lower = title.lower()
            
            # 【中文智能分类引擎】
            if any(keyword in title_lower for keyword in ['苹果', 'iphone', 'ios', '手机']):
                category = '手机终端 (IPHONE)'
            elif any(keyword in title_lower for keyword in ['芯片', '处理', '算力', '台积电', 'm3', 'a18']):
                category = '核心算力 (SOC)'
            elif any(keyword in title_lower for keyword in ['屏', 'oled', '显示', '亮度']):
                category = '视觉面板 (DISPLAY)'
            elif any(keyword in title_lower for keyword in ['相机', '镜头', '影像', '像素']):
                category = '光学影像 (CAMERA)'
            elif any(keyword in title_lower for keyword in ['电池', '充电', '容量', '续航']):
                category = '能源系统 (BATTERY)'
            else:
                # 不是上面这些核心科技的，统统划分为生态
                category = '前沿生态 (ECOSYSTEM)'

            extracted_data.append({
                'category': category,
                'content': title,
                'source': 'IT之家 (ITHome)'
            })
            
            # 满足 8 条我们就收手，撤退！
            if len(extracted_data) >= 8:
                break

        return extracted_data

    except Exception as e:
        print(f"[FATAL ERROR] 截获协议执行失败: {e}")
        return []

def push_to_cloud_matrix(data_list):
    if not data_list:
        print("[SYSTEM] 警告：暂无高价值数据流入，终止推送。")
        return

    print(f"\n[NETWORK] 正在将 {len(data_list)} 条加密数据推送至云端主脑...")
    
    headers = {
        'Content-Type': 'application/json',
        'X-Spider-Token': SECRET_TOKEN
    }

    try:
        response = requests.post(TARGET_API_URL, json=data_list, headers=headers, timeout=10)
        
        # 处理云端返回的 JSON 结果
        if response.status_code == 200:
            result = response.json()
            print(f"[CLOUD_RESPONSE] {result['msg']}")
        else:
            print(f"[UPLOAD ERROR] 云端主脑拒绝请求，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"[UPLOAD ERROR] 与云端主脑失联: {e}")

if __name__ == '__main__':
    print("=" * 50)
    print("      NEXUS-18 独立物理爬虫终端 V4.0 (中文特供版)")
    print("=" * 50)

    # 1. 本地执行真实物理抓取
    new_rumors = fetch_real_apple_rumors()
    
    time.sleep(1) # 增加演算的视觉沉浸感
    
    # 2. 推送给远程服务器
    push_to_cloud_matrix(new_rumors)

    print("\n>>> 所有自动化防卫任务结束 [STANDBY] <<<")
