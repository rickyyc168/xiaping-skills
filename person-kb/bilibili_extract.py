#!/usr/bin/env python3
"""
B站视频字幕提取器 — 绕过 yt-dlp 反爬
使用 Bilibili API 直接获取视频列表和音频，通过 Bcut 转写

用法:
  python3 bilibili_extract.py <mid> [--count N] [--output DIR]
  python3 bilibili_extract.py 526559715 --count 5 --output videos/transcripts
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse

try:
    import requests
except ImportError:
    print("Error: requests module required. pip install requests", file=sys.stderr)
    sys.exit(1)


# Bilibili 移动端 API 签名参数
APPKEY = '4409e2ce8ffd12b8'
APPSEC = '59b43e04ad6965f34319062b478f83dd'

HEADERS_WEB = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com'
}

HEADERS_MOBILE = {
    'User-Agent': 'Mozilla/5.0 BiliDroid/7.0.0'
}


def sign_params(params: dict) -> dict:
    """Bilibili 移动端 API 签名"""
    params['appkey'] = APPKEY
    params['ts'] = str(int(time.time()))
    sign = hashlib.md5((urllib.parse.urlencode(sorted(params.items())) + APPSEC).encode()).hexdigest()
    params['sign'] = sign
    return params


def get_video_list(mid: str, count: int = 20) -> list:
    """获取UP主视频列表（移动端API，绕过反爬）"""
    videos = []
    seen_bvids = set()
    pn = 1
    
    while len(videos) < count:
        params = sign_params({
            'vmid': mid,
            'ps': '20',
            'pn': str(pn),
            'order': 'pubdate'
        })
        resp = requests.get(
            'https://app.bilibili.com/x/v2/space/archive/cursor',
            params=params,
            headers=HEADERS_MOBILE
        )
        data = resp.json()
        
        if data.get('code') != 0 or not data.get('data', {}).get('item'):
            break
        
        items = data['data']['item']
        new_items = 0
        for item in items:
            bvid = item.get('bvid', '')
            if bvid and bvid not in seen_bvids:
                seen_bvids.add(bvid)
                videos.append({
                    'bvid': bvid,
                    'title': item.get('title', ''),
                    'duration': item.get('duration', 0),
                })
                new_items += 1
        
        if new_items == 0:
            break
        pn += 1
        time.sleep(0.5)
    
    return videos[:count]


def get_video_info(bvid: str) -> dict:
    """获取视频详情（web API，无需反爬）"""
    resp = requests.get(
        'https://api.bilibili.com/x/web-interface/view',
        params={'bvid': bvid},
        headers=HEADERS_WEB
    )
    data = resp.json()
    if data.get('code') != 0:
        return None
    return data['data']


def download_audio(bvid: str, aid: int, cid: int, output_path: str) -> bool:
    """下载视频音频（web playurl API）"""
    resp = requests.get(
        'https://api.bilibili.com/x/player/playurl',
        params={
            'bvid': bvid,
            'cid': cid,
            'qn': '32',
            'fnval': '16',  # DASH
            'fnver': '0',
            'fourk': '0'
        },
        headers={
            **HEADERS_WEB,
            'Referer': f'https://www.bilibili.com/video/{bvid}'
        }
    )
    data = resp.json()
    if data.get('code') != 0:
        return False
    
    dash = data.get('data', {}).get('dash')
    if not dash or not dash.get('audio'):
        return False
    
    audio_url = dash['audio'][0]['baseUrl']
    audio_resp = requests.get(audio_url, headers={
        'User-Agent': 'Mozilla/5.0',
        'Referer': f'https://www.bilibili.com/video/{bvid}'
    })
    
    if audio_resp.status_code != 200:
        return False
    
    # Save m4s first
    m4s_path = output_path + '.m4s'
    with open(m4s_path, 'wb') as f:
        f.write(audio_resp.content)
    
    # Convert to mp3
    result = subprocess.run(
        ['ffmpeg', '-i', m4s_path, '-acodec', 'libmp3lame', '-q:a', '4', output_path, '-y'],
        capture_output=True, timeout=60
    )
    os.remove(m4s_path)
    return result.returncode == 0


def transcribe_audio(audio_path: str, transcribe_script: str) -> str:
    """使用 Bcut 转写音频"""
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
        tmp_path = tmp.name
    
    result = subprocess.run(
        ['python3', transcribe_script, '--local', audio_path, '-o', tmp_path],
        capture_output=True, text=True, timeout=120,
        cwd=os.path.dirname(transcribe_script) or '.'
    )
    
    if os.path.exists(tmp_path):
        with open(tmp_path, 'r') as f:
            content = f.read()
        os.remove(tmp_path)
        return content
    return result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser(description='B站视频字幕提取器')
    parser.add_argument('mid', help='UP主的用户ID')
    parser.add_argument('--count', type=int, default=5, help='处理视频数量（默认5）')
    parser.add_argument('--output', default='.', help='输出目录')
    parser.add_argument('--transcribe', default=None, help='transcribe.py 路径')
    parser.add_argument('--skip-transcribe', action='store_true', help='只下载不转写')
    args = parser.parse_args()
    
    transcribe_script = args.transcribe or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'transcribe.py'
    )
    
    os.makedirs(args.output, exist_ok=True)
    os.makedirs(os.path.join(args.output, 'transcripts'), exist_ok=True)
    
    print(f"[1/4] 获取UP主 {args.mid} 的视频列表...", file=sys.stderr)
    videos = get_video_list(args.mid, args.count)
    print(f"  找到 {len(videos)} 个视频", file=sys.stderr)
    
    for i, video in enumerate(videos):
        bvid = video['bvid']
        title = video['title']
        safe_title = "".join(c if c.isalnum() or c in '-_ ' else '_' for c in title)[:40]
        transcript_file = os.path.join(args.output, 'transcripts', f'{bvid}_{safe_title}.txt')
        
        # Skip if already transcribed
        if os.path.exists(transcript_file):
            print(f"[{i+1}/{len(videos)}] 跳过（已存在）: {title}", file=sys.stderr)
            continue
        
        print(f"[{i+1}/{len(videos)}] 处理: {title} ({video['duration']}s)", file=sys.stderr)
        
        # Get video info
        info = get_video_info(bvid)
        if not info:
            print(f"  ⚠️ 获取视频信息失败", file=sys.stderr)
            continue
        
        cid = info['cid']
        aid = info['aid']
        
        if args.skip_transcribe:
            print(f"  跳过转写（--skip-transcribe）", file=sys.stderr)
            continue
        
        # Download audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            audio_path = tmp.name
        
        print(f"  [2/4] 下载音频...", file=sys.stderr)
        if not download_audio(bvid, aid, cid, audio_path):
            print(f"  ⚠️ 下载失败", file=sys.stderr)
            continue
        
        # Transcribe
        print(f"  [3/4] Bcut 转写中...", file=sys.stderr)
        transcript = transcribe_audio(audio_path, transcribe_script)
        
        # Save transcript
        with open(transcript_file, 'w') as f:
            f.write(f"# {title}\n")
            f.write(f"BV: {bvid}\n")
            f.write(f"时长: {video['duration']}s\n")
            f.write(f"URL: https://www.bilibili.com/video/{bvid}\n\n")
            f.write(transcript)
        
        print(f"  [4/4] 已保存: {transcript_file}", file=sys.stderr)
        
        # Cleanup
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        time.sleep(1)  # Rate limit
    
    print(f"\n完成！转写文件保存在 {args.output}/transcripts/", file=sys.stderr)


if __name__ == '__main__':
    main()
