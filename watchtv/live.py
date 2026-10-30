import requests
import re
import os
# ========== 填写源的地址 ==========
URL_LIST = [
    "https://raw.githubusercontent.com/ssili126/tv/refs/heads/main/itvlist.txt",
    "https://raw.githubusercontent.com/807080747/iptv-txt-conve/refs/heads/main/live.txt"
]
# ========== 分组映射：左边是源里的分组名，右边是输出时改后的分组名 ==========
GROUP_MAP = {
    "央视频道": "HS央视频道",
    "卫视频道": "HS卫视频道",
    # ========== 以下为807080747线路 ==========
    "央卫频道": "HSali云",
    "内网穿透": "lihansong央卫",
    "央视备用": "lihansong央视备用",
    "备用线路": "lihansong央卫备用",
    "咪-世-界": "咪-世-界",

    "阿里云服1": "HSali云",
    "阿里云服2": "HSali云",
    "阿里云服3": "HSali云",
    "阿里云服4": "HSali云",
    "备用线路": "HSali云",
    "ysp-live": "HSali云",
}

# 黑名单：只按频道名精确屏蔽
BLOCK_CHANNEL_NAMES = {
    "萌萌家-NAS"
}

def parse_any(text: str):
    res = []
    extinf_line = None
    current_group = None
    for raw_line in text.splitlines():
        ln = raw_line.strip()
        if not ln:
            continue
        if ln.startswith("#EXTINF:"):
            extinf_line = ln
            continue
        if extinf_line is not None and not ln.startswith("#"):
            res.append((extinf_line, ln))
            extinf_line = None
            continue
        if ',' in ln and not ln.startswith("#"):
            sp = ln.split(',',1)
            name_part = sp[0].strip()
            url_part = sp[1].strip()
            if url_part == "#genre#":
                current_group = name_part
                continue
            if current_group:
                fake_ext = f'#EXTINF:-1 group-title="{current_group}",{name_part}'
            else:
                fake_ext = f'#EXTINF:-1,{name_part}'
            res.append((fake_ext, url_part))
    return res

def get_channel_name(extinf):
    if "," in extinf:
        return extinf.split(",")[-1].strip()
    return ""

def get_group_title(extinf):
    m = re.search(r'group-title="([^"]+)"', extinf)
    if m:
        return m.group(1).strip()
    return ""

def main():
    group_bucket = {v: [] for v in GROUP_MAP.values()}
    seen = set()
    for url in URL_LIST:
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            channels = parse_any(resp.text)
            for extinf, play_url in channels:
                ch_name = get_channel_name(extinf)
                ch_group = get_group_title(extinf)

                if ch_group not in GROUP_MAP:
                    continue
                # 命中频道名直接屏蔽，链接更新不受影响
                if ch_name in BLOCK_CHANNEL_NAMES:
                    print(f"🚫 屏蔽频道：{ch_name}")
                    continue

                output_group = GROUP_MAP[ch_group]
                item_key = (ch_name, play_url)
                if item_key not in seen:
                    seen.add(item_key)
                    group_bucket[output_group].append((ch_name, play_url))
        except Exception as e:
            print(f"⚠️拉取 {url} 失败：{e}")

    total_cnt = sum(len(v) for v in group_bucket.values())
    print(f"✅筛选结束，共提取 {total_cnt} 个频道")
    for gname, ch_list in group_bucket.items():
        print(f"  - {gname}: {len(ch_list)} 个频道")

    out_dir = os.path.dirname(os.path.abspath(__file__))
    output_m3u = ["#EXTM3U"]
    for gname, ch_list in group_bucket.items():
        for cname, curl in ch_list:
            fake_ext = f'#EXTINF:-1 group-title="{gname}",{cname}'
            output_m3u.append(fake_ext)
            output_m3u.append(curl)

    m3u8_path = os.path.join(out_dir, "live.m3u8")
    with open(m3u8_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_m3u))
    print(f"✅已输出 m3u8：{m3u8_path}")

if __name__ == "__main__":
    main()
