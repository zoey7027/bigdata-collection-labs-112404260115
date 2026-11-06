"""实验二第二阶段：安居客教学站房源 8 个字段解析

用法：
    在线采集：python anjuke.py
    网页快照：python anjuke.py html/anjuke_snapshot.html
"""

import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://www.bspider.top/anjuke/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# 入库/CSV 使用的固定字段顺序
FIELDS = ["title", "house", "address", "struct", "area", "floor", "maketime", "price"]


def load_soup(snapshot=None):
    """在线请求网页；教师要求离线时改为读取快照 HTML 文件。"""
    if snapshot:
        html = Path(snapshot).read_text(encoding="utf-8")
        return BeautifulSoup(html, "html.parser"), str(snapshot)
    r = requests.get(BASE_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return BeautifulSoup(r.text, "html.parser"), r.url


def text_of(node):
    """节点文字（去首尾空白）；节点不存在时返回空字符串。"""
    return node.get_text(strip=True) if node else ""


def parse_property(row):
    """解析一条房源，按 title→house→address→struct→area→floor→maketime→price 返回。"""
    # 标题：标题名节点，退化时用 h3
    title = text_of(row.select_one(".property-content-title-name")) or text_of(row.select_one("h3"))

    # 楼盘
    house = text_of(row.select_one(".property-content-info-comm-name"))

    # 地址：可能拆在多个 span 中，逐个取值后直接拼接，不额外插入空格
    address_nodes = row.select(".property-content-info-comm-address span")
    if address_nodes:
        address = "".join(n.get_text(strip=True) for n in address_nodes)
    else:
        address = text_of(row.select_one(".property-content-info-comm-address"))

    # 属性组中同时有户型、面积、朝向、楼层、建造年代。
    # 按文字特征识别，不依赖固定下标：顺序变化或缺项时不会取错（如把朝向当楼层）
    struct = area = floor = maketime = ""
    attr_nodes = row.select(".property-content-info-attribute .property-content-info-text")
    if not attr_nodes:
        attr_nodes = row.select(".property-content-info-attribute span")

    for node in attr_nodes:
        t = node.get_text(strip=True)
        if not struct and re.search(r"\d+\s*室", t):
            struct = t
        elif not area and re.search(r"(㎡|平米|平方米)", t):
            area = t
        elif not maketime and re.search(r"\d{4}\s*年", t):
            maketime = t
        elif not floor and re.search(r"(低层|中层|高层|底层|顶层|地下)", t):
            floor = t

    # 单价：只取每平方米均价。右侧"148万"是总价，不能取
    price = text_of(row.select_one(".property-price-average"))
    if not price:
        m = re.search(r"\d[\d,.]*\s*元\s*/\s*(?:㎡|平米|平方米)",
                      text_of(row.select_one(".property-price")))
        price = m.group(0).replace(" ", "") if m else ""

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
    soup, page_url = load_soup(sys.argv[1] if len(sys.argv) > 1 else None)

    rows = soup.select("div.property")
    if not rows:
        raise SystemExit("未匹配到房源容器 div.property：页面可能是访问验证页，请记录并改用快照。")

    # 先打印首条房源的属性组原文，确认顺序后再取值
    print("首条房源属性组原文（核对顺序）：")
    print([n.get_text(strip=True) for n in
           rows[0].select(".property-content-info-attribute .property-content-info-text")])

    records = [parse_property(row) for row in rows]
    print(f"\n页面：{page_url}")
    print(f"本页房源条数：{len(records)}")

    # 逐字段核对首条和最后一条
    for label, rec in (("第一条", records[0]), ("最后一条", records[-1])):
        print(f"\n{label}房源的 8 个字段：")
        for key in FIELDS:
            print(f"  {key:9s}: {rec[key]}")

    return records


if __name__ == "__main__":
    main()
