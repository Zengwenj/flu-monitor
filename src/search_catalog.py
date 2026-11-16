# -*- coding: utf-8 -*-
"""A2 搜索版目录契约（S1 数据层）。

职责：加载并校验 data/locations.csv 与 data/location_product_map.csv，
产出可嵌入 index.html 的目录 JSON，以及"查到某单位后按什么顺序展示哪些
固定结果片段"的配方（recipe）。数值、来源、状态一律由 build_site 在构建期
渲染进固定模板片段；本模块不生成 HTML，JS 不算任何数据。

契约来源：.trellis/tasks/11-12-regional-monitor/design.md §2、implement.md S1。
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCATIONS_CSV = ROOT / "data" / "locations.csv"
PRODUCT_MAP_CSV = ROOT / "data" / "location_product_map.csv"

# 可查询总数契约（评审 A2-CATALOG-COUNT-ASSERTIONS）
EXPECTED_TOTAL = 400          # 行数
EXPECTED_QUERYABLE = 397      # monitor_coverage=true
EXPECTED_PLACEHOLDERS = 3     # 港澳台占位，不可查询
EXPECTED_BY_TYPE = {"province": 31, "prefecture": 333, "province_direct_county": 33}
CAOHU_ID = "659013"           # 用户批准的单条 dmfw 补正
CHENGDU_ID = "510100"

# 当地产品绑定：只有明确绑定的单位才有"当地数据"卡（诚实性：未绑定≠0）
# hlj_flu  = 黑龙江省 B1 流感摘要（heilongjiang_flu.csv）
# hlj_sent = 黑龙江省 B2 哨点部分观测（heilongjiang_sentinel.csv）
# cq_links = 重庆官方入口（无本地数值，仅链接）
LOCAL_BINDINGS = {
    "230000": ["hlj_flu", "hlj_sent"],
    "500000": ["cq_links"],
    "510100": ["chengdu_default"],
}


class CatalogError(RuntimeError):
    pass


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_catalog():
    """读取并校验目录；任何契约不符抛 CatalogError。"""
    locs = _read(LOCATIONS_CSV)
    pmap = {}
    for r in _read(PRODUCT_MAP_CSV):
        if r["id"] in pmap:
            raise CatalogError(f"产品映射重复 id {r['id']}")
        pmap[r["id"]] = r
    if len(locs) != EXPECTED_TOTAL:
        raise CatalogError(f"目录行数 {len(locs)} != {EXPECTED_TOTAL}")
    if len(pmap) != len(locs):
        raise CatalogError("locations 与 product_map 行数不一致")
    by_id = {}
    for r in locs:
        rid = r["id"]
        if rid in by_id:
            raise CatalogError(f"重复 id {rid}")
        if len(rid) != 6 or not rid.isdigit():
            raise CatalogError(f"非法区划码 {rid}")
        m = pmap.get(rid)
        if m is None:
            raise CatalogError(f"{rid} 缺产品映射行")
        by_id[rid] = {
            "id": rid,
            "name": r["name"],
            "type": r["type"],
            "parent_id": r["parent_id"] or None,
            "direct": r["direct_under_province"] == "true",
            "aliases": [a for a in r["aliases"].split("|") if a],
            "queryable": r["monitor_coverage"] == "true",
            "source": r["source"],
            "flu_region": m["flu_region"],
            "sentinel_region": m["sentinel_region"],
            "_src_flu_region_source": m["flu_region_source"],
            "_src_sentinel_region_source": m["sentinel_region_source"],
        }
    n_q = sum(1 for u in by_id.values() if u["queryable"])
    if n_q != EXPECTED_QUERYABLE or len(by_id) - n_q != EXPECTED_PLACEHOLDERS:
        raise CatalogError(f"可查询 {n_q}/占位 {len(by_id)-n_q} 契约不符")
    by_type = {}
    for u in by_id.values():
        if u["queryable"]:
            by_type[u["type"]] = by_type.get(u["type"], 0) + 1
    if by_type != EXPECTED_BY_TYPE:
        raise CatalogError(f"分类计数 {by_type} != {EXPECTED_BY_TYPE}")
    if by_id[CAOHU_ID]["source"] != "dmfw":
        raise CatalogError("草湖市必须为 dmfw 单条补正")
    for u in by_id.values():
        # 父级契约：省级无父级；地级/省直辖县级必须有父级且父级为省级
        if u["type"] == "province" and u["parent_id"]:
            raise CatalogError(f"{u['id']} 省级不得有父级")
        if u["type"] in ("prefecture", "province_direct_county"):
            if not u["parent_id"]:
                raise CatalogError(f"{u['id']} {u['type']} 缺父级")
            if u["parent_id"] not in by_id:
                raise CatalogError(f"{u['id']} 父级不存在")
            if by_id[u["parent_id"]]["type"] != "province":
                raise CatalogError(f"{u['id']} 父级 {u['parent_id']} 非省级")
        if u["type"] == "province_direct_county" and not u["direct"]:
            raise CatalogError(f"{u['id']} 省直辖县级必须 direct=true")
        for key, skey in (("flu_region", "flu_region_source"),
                          ("sentinel_region", "sentinel_region_source")):
            if u[key] not in ("south", "north", "unknown"):
                raise CatalogError(f"{u['id']} {key}={u[key]} 非法")
            if u[key] != "unknown" and not u["_src_" + skey].strip():
                raise CatalogError(f"{u['id']} {key} 非 unknown 但来源为空")
            if not u["queryable"] and u[key] != "unknown":
                raise CatalogError(f"{u['id']} 占位单位映射必须 unknown")
    return by_id


def embedded_json(by_id):
    """构建期嵌入页面的目录 JSON（占位行保留 queryable=false，JS 端过滤）。"""
    rows = [
        {
            "i": u["id"],
            "n": u["name"],
            "t": u["type"],
            "p": u["parent_id"] or "",
            "d": 1 if u["direct"] else 0,
            "a": u["aliases"],
            "q": 1 if u["queryable"] else 0,
            "f": u["flu_region"],
            "s": u["sentinel_region"],
        }
        for u in sorted(by_id.values(), key=lambda x: x["id"])
    ]
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))


def recipe(unit_id, by_id):
    """查询结果的固定片段顺序契约：local → provincial → zone → national。

    返回 list[str] 片段槽位名（build_site/JS 按白名单映射到模板 ID）：
    chengdu_default / local_nodata / local_hlj_flu / local_hlj_sent /
    cq_links / prov_nodata / zone_flu_south / zone_flu_north /
    zone_names_south / zone_names_north / national_rank
    """
    if unit_id not in by_id:
        raise CatalogError(f"未知单位 {unit_id}")
    u = by_id[unit_id]
    if not u["queryable"]:
        raise CatalogError(f"{u['name']} 为占位单位，不可查询")
    slots = []
    for prod in LOCAL_BINDINGS.get(unit_id, []):
        if prod == "chengdu_default":
            return ["chengdu_default"]          # 成都市：恢复默认，无查询结果卡
        slots.append({"cq_links": "cq_links", "hlj_flu": "local_hlj_flu",
                      "hlj_sent": "local_hlj_sent"}[prod])
    if not slots:
        slots.append("local_nodata")            # 本工具未取得当地数据
    if u["type"] in ("prefecture", "province_direct_county"):
        pid = u["parent_id"]
        prov_prods = LOCAL_BINDINGS.get(pid, [])
        prov_slots = [
            {"cq_links": "cq_links", "hlj_flu": "prov_hlj_flu",
             "hlj_sent": "prov_hlj_sent", "chengdu_default": None}[p]
            for p in prov_prods if p != "cq_links"
        ]
        slots.extend(s for s in prov_slots if s)
        if not prov_slots:
            slots.append("prov_nodata")         # 省级参考未取得（隐藏级配说明由页面给）
    # 省级单位自身的观测已作 local；不再插省级层
    # 两产品片区映射独立（A2-SEARCH-02）：流感卡跟 flu_region，
    # 哨点名称卡跟 sentinel_region，各自 unknown 则各自缺卡，互不派生
    if u["flu_region"] == "south":
        slots.append("zone_flu_south")
    elif u["flu_region"] == "north":
        slots.append("zone_flu_north")
    if u["sentinel_region"] == "south":
        slots.append("zone_names_south")
    elif u["sentinel_region"] == "north":
        slots.append("zone_names_north")
    slots.append("national_rank")
    return slots


if __name__ == "__main__":  # 构建期自检：契约不符即失败
    by_id = load_catalog()
    assert len(embedded_json(by_id)) > 1000
    assert recipe(CHENGDU_ID, by_id) == ["chengdu_default"]
    r = recipe("230000", by_id)
    assert r[0] == "local_hlj_flu" and "zone_flu_north" in r and r[-1] == "national_rank"
    assert "prov_hlj_flu" in recipe("230100", by_id)          # 哈尔滨市 → 省级参考
    assert "cq_links" in recipe("500000", by_id)[0:1]
    assert recipe("440000", by_id)[0] == "local_nodata"       # 广东省
    assert recipe("220200", by_id).count("prov_nodata") == 1  # 吉林市
    assert recipe(CAOHU_ID, by_id)[0] == "local_nodata"       # 草湖市
    # A2-SEARCH-02：哨点名称卡跟 sentinel_region 独立走（内存夹具验证）
    fake = dict(by_id)
    fake["440000"] = dict(by_id["440000"], sentinel_region="north")   # 流感 south / 哨点 north
    r = recipe("440000", fake)
    assert "zone_flu_south" in r and "zone_names_north" in r and "zone_names_south" not in r
    u2 = dict(by_id["440000"], sentinel_region="unknown")
    fake["440000"] = u2
    r2 = recipe("440000", fake)
    assert "zone_flu_south" in r2 and not any(s.startswith("zone_names") for s in r2)
    print("search_catalog OK:", EXPECTED_QUERYABLE, "queryable /", EXPECTED_PLACEHOLDERS, "placeholders")
