"""实验二：解析安居客教学站首条房源的 8 个字段

运行方式：
    在线采集：python anjuke_parse.py
    网页快照：python anjuke_parse.py html/anjuke_snapshot.html
"""

import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "http://www.bspider.top/anjuke/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

FIELDS = ["title", "house", "address", "struct", "area", "floor", "maketime", "price"]


def load_soup(snapshot=None):
    """在线请求网页；传入快照路径时改为本地读取。"""
    if snapshot:
        html = Path(snapshot).read_text(encoding="utf-8")
        return BeautifulSoup(html, "html.parser")
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return BeautifulSoup(r.text, "html.parser")


def parse_first(soup):
    """解析首条房源，按固定顺序返回 8 个字段。"""
    rows = soup.select("div.property")          # select：取本页全部房源
    print("本页房源条数：", len(rows))
    if not rows:
        raise ValueError("未匹配到 div.property：页面可能是访问验证页，请改用快照")

    row = rows[0]                               # 只解析首条

    # 标题、楼盘：select_one 各取一个节点
    title = row.select_one("h3").get_text(strip=True)
    house = row.select_one(".property-content-info-comm-name").get_text(strip=True)

    # 地址：select 取多个 span，拼接完整，不额外插入空格
    address = "".join(s.get_text(strip=True)
                      for s in row.select(".property-content-info-comm-address span"))

    # 属性组：先打印每项，确认顺序
    attrs = [s.get_text(strip=True)
             for s in row.select(".property-content-info-attribute .property-content-info-text")]
    print("属性组原文：", attrs)

    # 户型、楼层按文字特征识别，不依赖固定下标
    struct = next((t for t in attrs if re.search(r"\d+室", t)), "")
    floor = next((t for t in attrs if re.search(r"(低层|中层|高层|底层|顶层)", t)), "")

    # 建造年代：取含四位年份的项；没有该项时返回空字符串
    maketime = next((t for t in attrs if re.search(r"\d{4}年", t)), "")

    # 面积：取属性组中带 ㎡ 的那一项，避免把朝向或楼层当面积
    area = next((t for t in attrs if "㎡" in t or "平米" in t), "")

    # 单价：只取均价 16465元/㎡，不能取右侧 148万 总价
    price = row.select_one(".property-price-average").get_text(strip=True)

    return {
        "title": title,
        "house": house,
        "address": address,
        "struct": struct,
        "area": area,
        "floor": floor,
        "maketime": maketime,
        "price": price,
    }


def main():
    snapshot = sys.argv[1] if len(sys.argv) > 1 else None
    soup = load_soup(snapshot)
    record = parse_first(soup)

    print("首条房源 8 个字段：")
    for key in FIELDS:
        print(f"  {key:9s}: {record[key]}")


if __name__ == "__main__":
    main()
