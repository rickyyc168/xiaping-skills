#!/usr/bin/env python3
"""
B站视频字幕提取器 v2 — 流水线并行版
优化点：
  1. 跳过 ffmpeg 转换：直接传 m4s 给 Bcut（Bcut 接受任意音频格式）
  2. 流水线并行：下载下一个视频的同时，Bcut 正在转写上一个
  3. 去掉 sleep 等待，改为自然串行
  4. Bcut 轮询间隔从 1s 降到 0.5s

用法:
  python3 bilibili_extract_v2.py 526559715 --count 5
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

try:
    import requests
except ImportError:
    print("Error: pip install requests", file=sys.stderr)
    sys.exit(1)


# ─────────────────────────────────────────────
# Bilibili API
# ─────────────────────────────────────────────

APPKEY = '4409e2ce8ffd12b8'
APPSEC = '59b43e04ad6965f34319062b478f83dd'

HEADERS_WEB = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com'
}


def sign_params(params):
    params['appkey'] = APPKEY
    params['ts'] = str(int(time.time()))
    sign = hashlib.md5((urllib.parse.urlencode(sorted(params.items())) + APPSEC).encode()).hexdigest()
    params['sign'] = sign
    return params


def get_video_list(mid, count=20):
    videos, seen = [], set()
    pn = 1
    while len(videos) < count:
        params = sign_params({'vmid': mid, 'ps': '20', 'pn': str(pn), 'order': 'pubdate'})
        resp = requests.get('https://app.bilibili.com/x/v2/space/archive/cursor',
                           params=params, headers={'User-Agent': 'Mozilla/5.0 BiliDroid/7.0.0'})
        data = resp.json()
        if data.get('code') != 0 or not data.get('data', {}).get('item'):
            break
        new = 0
        for item in data['data']['item']:
            bv = item.get('bvid', '')
            if bv and bv not in seen:
                seen.add(bv)
                videos.append({'bvid': bv, 'title': item['title'], 'duration': item.get('duration', 0)})
                new += 1
        if not new:
            break
        pn += 1
    return videos[:count]


def get_video_info(bvid):
    resp = requests.get('https://api.bilibili.com/x/web-interface/view',
                       params={'bvid': bvid}, headers=HEADERS_WEB)
    d = resp.json()
    return d['data'] if d.get('code') == 0 else None


def download_audio_m4s(bvid, aid, cid):
    """下载音频，返回 m4s 二进制数据（跳过 ffmpeg 转换）"""
    resp = requests.get('https://api.bilibili.com/x/player/playurl', params={
        'bvid': bvid, 'cid': cid, 'qn': '32', 'fnval': '16', 'fnver': '0', 'fourk': '0'
    }, headers={**HEADERS_WEB, 'Referer': f'https://www.bilibili.com/video/{bvid}'})
    data = resp.json()
    if data.get('code') != 0:
        return None
    dash = data.get('data', {}).get('dash')
    if not dash or not dash.get('audio'):
        return None
    audio_url = dash['audio'][0]['baseUrl']
    r = requests.get(audio_url, headers={'User-Agent': 'Mozilla/5.0',
                                          'Referer': f'https://www.bilibili.com/video/{bvid}'})
    return r.content if r.status_code == 200 else None


# ─────────────────────────────────────────────
# Bcut 转写器（内联，减少依赖）
# ─────────────────────────────────────────────

BCUT_API = "https://member.bilibili.com/x/bcut/rubick-interface"

class BcutTranscriber:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            'User-Agent': 'Bilibili/1.0.0 (https://www.bilibili.com)',
            'Content-Type': 'application/json'
        })

    def transcribe(self, audio_bytes, filename='audio.m4s'):
        """转写音频字节，返回文本"""
        # 1. 申请上传
        resp = self.s.post(BCUT_API + "/resource/create", json={
            "type": 2, "name": filename, "size": len(audio_bytes),
            "ResourceFileType": "mp3", "model_id": "8"
        }).json()
        rd = resp['data']

        # 2. 分片上传
        etags = []
        for i, url in enumerate(rd['upload_urls']):
            start = i * rd['per_size']
            end = min((i + 1) * rd['per_size'], len(audio_bytes))
            r = self.s.put(url, data=audio_bytes[start:end],
                          headers={'Content-Type': 'application/octet-stream'})
            etags.append(r.headers.get("Etag", "").strip('"'))

        # 3. 提交
        resp = self.s.post(BCUT_API + "/resource/create/complete", json={
            "InBossKey": rd['in_boss_key'], "ResourceId": rd['resource_id'],
            "Etags": ",".join(etags), "UploadId": rd['upload_id'], "model_id": "8"
        }).json()

        # 4. 创建任务
        resp = self.s.post(BCUT_API + "/task", json={
            "resource": resp['data']['download_url'], "model_id": "8"
        }).json()
        task_id = resp['data']['task_id']

        # 5. 轮询结果（0.5s 间隔）
        for _ in range(600):
            time.sleep(0.5)
            resp = self.s.get(BCUT_API + "/task/result",
                            params={"model_id": 7, "task_id": task_id}).json()
            state = resp['data']['state']
            if state == 4:  # 完成
                result = json.loads(resp['data']['result'])
                return ' '.join(u['transcript'] for u in result.get('utterances', []))
            elif state == 3:  # 失败
                return None
        return None


# ─────────────────────────────────────────────
# 流水线并行处理
# ─────────────────────────────────────────────

def process_one(bvid, output_dir):
    """处理单个视频：下载 + 转写"""
    safe = "".join(c if c.isalnum() or c in '-_ ' else '_' for c in '')[:40]

    # 获取视频信息
    info = get_video_info(bvid)
    if not info:
        return None

    title = info['title']
    safe = "".join(c if c.isalnum() or c in '-_ ' else '_' for c in title)[:40]
    outpath = os.path.join(output_dir, 'transcripts', f'{bvid}_{safe}.txt')

    # 跳过已处理
    if os.path.exists(outpath):
        print(f'  ⏭ 跳过（已存在）: {title}', file=sys.stderr)
        return outpath

    # 下载音频
    audio = download_audio_m4s(bvid, info['aid'], info['cid'])
    if not audio:
        print(f'  ❌ 下载失败: {title}', file=sys.stderr)
        return None

    # Bcut 转写
    bcut = BcutTranscriber()
    text = bcut.transcribe(audio)
    if not text:
        print(f'  ❌ 转写失败: {title}', file=sys.stderr)
        return None

    # 保存
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, 'w') as f:
        f.write(f'# {title}\nBV: {bvid}\nURL: https://www.bilibili.com/video/{bvid}\n\n{text}\n')

    print(f'  ✅ 完成: {title} ({len(text)}字)', file=sys.stderr)
    return outpath


def main():
    parser = argparse.ArgumentParser(description='B站视频字幕提取 v2（流水线并行）')
    parser.add_argument('mid', help='UP主用户ID')
    parser.add_argument('--count', type=int, default=5, help='视频数量')
    parser.add_argument('--output', default='.', help='输出目录')
    parser.add_argument('--workers', type=int, default=2, help='并行数（下载+转写并行）')
    args = parser.parse_args()

    os.makedirs(os.path.join(args.output, 'transcripts'), exist_ok=True)

    print(f'[1/2] 获取视频列表 (UP: {args.mid})...', file=sys.stderr)
    videos = get_video_list(args.mid, args.count)
    print(f'  找到 {len(videos)} 个视频', file=sys.stderr)

    print(f'[2/2] 流水线处理（{args.workers}路并行）...', file=sys.stderr)
    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_one, v['bvid'], args.output): v for v in videos}
        for f in futures:
            r = f.result()
            if r:
                results.append(r)

    print(f'\n完成！{len(results)}/{len(videos)} 个视频已转写 → {args.output}/transcripts/', file=sys.stderr)


if __name__ == '__main__':
    main()
