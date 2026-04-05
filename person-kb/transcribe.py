#!/usr/bin/env python3
"""
视频转写 CLI — 轻量模式下的 BiliNote 核心能力
源自 BiliNote (MIT License) 的 Bcut + Groq 转写器

用法:
  # Bcut 免费中文转录（默认，无需 API Key）
  python3 transcribe.py "https://www.bilibili.com/video/BV1xx411c7mD"
  
  # Groq Whisper 转录（需要 GROQ_API_KEY 环境变量）
  python3 transcribe.py --engine groq "https://www.youtube.com/watch?v=xxx"
  
  # 指定输出文件
  python3 transcribe.py -o output.txt "视频URL"
  
  # 转写本地音频文件
  python3 transcribe.py --local audio.mp3

支持的引擎:
  bcut   — B站必剪接口，免费，中文效果好，无需 API Key
  groq   — Groq Whisper API，速度快，需要 GROQ_API_KEY
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path



# ============================================================
# 沙箱隔离：下载文件自动存入临时目录，用完即清理
# ============================================================

import contextlib
import shutil as _shutil

@contextlib.contextmanager
def sandbox_downloads(prefix="personkb_"):
    """隔离沙箱上下文管理器
    
    创建临时目录存放下载文件，with 块结束后自动清理。
    
    用法:
        with sandbox_downloads() as sandbox_dir:
            filepath = download_audio(url, output_dir=sandbox_dir)
            # ... 处理文件 ...
        # 退出 with 后，sandbox_dir 及其内容已被删除
    """
    sandbox_dir = tempfile.mkdtemp(prefix=prefix)
    try:
        yield sandbox_dir
    finally:
        _shutil.rmtree(sandbox_dir, ignore_errors=True)

# ============================================================
# Bcut 转写器（源自 BiliNote，MIT License）
# ============================================================

BCUT_API_BASE = "https://member.bilibili.com/x/bcut/rubick-interface"

class BcutTranscriber:
    """B站必剪语音识别接口，无需 API Key"""
    
    HEADERS = {
        'User-Agent': 'Bilibili/1.0.0 (https://www.bilibili.com)',
        'Content-Type': 'application/json'
    }
    
    def __init__(self):
        import requests
        self.session = requests.Session()
        self.task_id = None
        self._etags = []
        self._in_boss_key = None
        self._resource_id = None
        self._upload_id = None
        self._upload_urls = []
        self._per_size = None
        self._clips = 0
        self._download_url = None
    
    def transcribe(self, file_path: str) -> dict:
        """执行转写，返回 {full_text, segments: [{start, end, text}]}"""
        import requests
        
        print(f"[Bcut] 上传音频: {file_path}", file=sys.stderr)
        self._upload(file_path)
        
        print("[Bcut] 创建转写任务...", file=sys.stderr)
        self._create_task()
        
        print("[Bcut] 等待转写结果...", file=sys.stderr)
        task_resp = None
        for i in range(500):
            task_resp = self._query_result()
            if task_resp["state"] == 4:
                break
            elif task_resp["state"] == 3:
                raise Exception(f"Bcut 转写失败，状态码: {task_resp['state']}")
            if i % 10 == 0:
                print(f"[Bcut] 转写中... ({i}s)", file=sys.stderr)
            time.sleep(1)
        
        if not task_resp or task_resp["state"] != 4:
            raise Exception("Bcut 转写超时")
        
        # 解析结果
        result_json = json.loads(task_resp["result"])
        segments = []
        full_text = ""
        
        for u in result_json.get("utterances", []):
            text = u.get("transcript", "").strip()
            start = float(u.get("start_time", 0)) / 1000.0
            end = float(u.get("end_time", 0)) / 1000.0
            full_text += text + " "
            segments.append({"start": start, "end": end, "text": text})
        
        return {
            "engine": "bcut",
            "language": result_json.get("language", "zh"),
            "full_text": full_text.strip(),
            "segments": segments
        }
    
    def _upload(self, file_path: str):
        import requests
        
        with open(file_path, 'rb') as f:
            file_binary = f.read()
        
        resp = self.session.post(
            f"{BCUT_API_BASE}/resource/create",
            json={
                "type": 2,
                "name": "audio.mp3",
                "size": len(file_binary),
                "ResourceFileType": "mp3",
                "model_id": "8",
            },
            headers=self.HEADERS
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        
        self._in_boss_key = data["in_boss_key"]
        self._resource_id = data["resource_id"]
        self._upload_id = data["upload_id"]
        self._upload_urls = data["upload_urls"]
        self._per_size = data["per_size"]
        self._clips = len(data["upload_urls"])
        
        print(f"[Bcut] 上传: {len(file_binary)//1024}KB, {self._clips}分片", file=sys.stderr)
        
        # 分片上传
        etags = []
        for clip in range(self._clips):
            start = clip * self._per_size
            end = min((clip + 1) * self._per_size, len(file_binary))
            resp = self.session.put(
                self._upload_urls[clip],
                data=file_binary[start:end],
                headers={'Content-Type': 'application/octet-stream'}
            )
            resp.raise_for_status()
            etags.append(resp.headers.get("Etag", "").strip('"'))
        
        # 提交上传
        resp = self.session.post(
            f"{BCUT_API_BASE}/resource/create/complete",
            json={
                "InBossKey": self._in_boss_key,
                "ResourceId": self._resource_id,
                "Etags": ",".join(etags),
                "UploadId": self._upload_id,
                "model_id": "8",
            },
            headers=self.HEADERS
        )
        resp.raise_for_status()
        self._download_url = resp.json()["data"]["download_url"]
    
    def _create_task(self):
        import requests
        resp = self.session.post(
            f"{BCUT_API_BASE}/task",
            json={"resource": self._download_url, "model_id": "8"},
            headers=self.HEADERS
        )
        resp.raise_for_status()
        self.task_id = resp.json()["data"]["task_id"]
    
    def _query_result(self):
        import requests
        resp = self.session.get(
            f"{BCUT_API_BASE}/task/result",
            params={"model_id": 7, "task_id": self.task_id},
            headers=self.HEADERS
        )
        resp.raise_for_status()
        return resp.json()["data"]


# ============================================================
# Groq Whisper 转写器（源自 BiliNote，MIT License）
# ============================================================

class GroqTranscriber:
    """Groq Whisper API 转写，需要 GROQ_API_KEY"""
    
    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo", base_url: str = "https://api.groq.com/openai/v1"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    def transcribe(self, file_path: str) -> dict:
        """执行转写"""
        # 压缩大文件
        file_size = os.path.getsize(file_path)
        if file_size > 18 * 1024 * 1024:
            print(f"[Groq] 文件 {file_size//1024//1024}MB > 18MB，压缩中...", file=sys.stderr)
            file_path = self._compress(file_path)
        
        print(f"[Groq] 调用 Whisper API: {self.model}", file=sys.stderr)
        with open(file_path, "rb") as f:
            transcription = self.client.audio.transcriptions.create(
                file=(os.path.basename(file_path), f.read()),
                model=self.model,
                response_format="verbose_json",
            )
        
        segments = []
        full_text = ""
        for seg in transcription.segments:
            text = seg.text.strip()
            full_text += text + " "
            segments.append({"start": seg.start, "end": seg.end, "text": text})
        
        return {
            "engine": "groq",
            "language": transcription.language,
            "full_text": full_text.strip(),
            "segments": segments
        }
    
    def _compress(self, input_path: str) -> str:
        output = tempfile.mktemp(suffix=".mp3")
        subprocess.run(
            ["ffmpeg", "-i", input_path, "-b:a", "64k", "-y", output],
            capture_output=True
        )
        return output


# ============================================================
# 下载 + 转写 工具函数
# ============================================================

def download_audio(url: str, output_dir: str = None) -> str:
    """用 yt-dlp 下载音频，返回文件路径
    
    如果未指定 output_dir，自动使用隔离的临时目录，处理完成后由调用方负责清理。
    """
    cleanup_dir = False
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="personkb_dl_")
        cleanup_dir = True
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp", "-x", "--audio-format", "mp3",
        "--audio-quality", "5",
        "-o", output_path,
        "--print", "after_move:filepath",  # 输出最终文件路径
        url
    ]
    print(f"[下载] yt-dlp -x --audio-format mp3 {url}", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if cleanup_dir:
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
        raise Exception(f"yt-dlp 下载失败: {result.stderr}")
    
    # 最后一行是文件路径
    filepath = result.stdout.strip().split('\n')[-1]
    return filepath


def download_subtitle(url: str, output_dir: str) -> str | None:
    """用 yt-dlp 提取字幕，返回字幕文件路径或 None"""
    output_path = os.path.join(output_dir, "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--write-auto-sub", "--sub-lang", "zh-Hans,zh,en",
        "--sub-format", "vtt", "--skip-download",
        "-o", output_path,
        "--print", "after_move:filepath",
        url
    ]
    print(f"[字幕] 尝试提取字幕...", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and result.stdout.strip():
        filepath = result.stdout.strip().split('\n')[-1]
        if os.path.exists(filepath):
            return filepath
    return None


def vtt_to_segments(vtt_path: str) -> list:
    """将 VTT 字幕文件解析为 segments"""
    segments = []
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = content.strip().split('\n\n')
    for block in blocks:
        lines = block.strip().split('\n')
        for i, line in enumerate(lines):
            if '-->' in line:
                times = line.split('-->')
                start = parse_vtt_time(times[0].strip())
                end = parse_vtt_time(times[1].strip())
                text = ' '.join(lines[i+1:]).strip()
                if text and not text.startswith('WEBVTT'):
                    segments.append({"start": start, "end": end, "text": text})
                break
    return segments


def parse_vtt_time(t: str) -> float:
    """解析 VTT 时间戳 00:01:23.456 → 秒"""
    t = t.replace(',', '.')
    parts = t.split(':')
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    return float(parts[0])


def format_time(seconds: float) -> str:
    """秒 → HH:MM:SS"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_output(result: dict, url: str = "") -> str:
    """格式化输出为带时间戳的文本"""
    lines = []
    lines.append(f"引擎: {result['engine']}")
    lines.append(f"语言: {result.get('language', 'unknown')}")
    if url:
        lines.append(f"来源: {url}")
    lines.append(f"段落数: {len(result['segments'])}")
    lines.append("")
    lines.append("--- 转录内容 ---")
    lines.append("")
    
    for seg in result["segments"]:
        ts = format_time(seg["start"])
        lines.append(f"[{ts}] {seg['text']}")
    
    return '\n'.join(lines)


# ============================================================
# B站字幕提取（直接调用 Bilibili API）
# ============================================================

def get_bilibili_subtitle(bvid: str) -> str | None:
    """尝试获取 B站视频的 AI 字幕"""
    import requests
    
    print(f"[B站] 获取视频信息: {bvid}", file=sys.stderr)
    
    # 获取 cid
    resp = requests.get(
        "https://api.bilibili.com/x/web-interface/view",
        params={"bvid": bvid}
    )
    data = resp.json()
    if data.get("code") != 0:
        print(f"[B站] 获取 cid 失败: {data.get('message')}", file=sys.stderr)
        return None
    
    cid = data["data"]["cid"]
    aid = data["data"]["aid"]
    
    # 获取字幕列表
    resp = requests.get(
        "https://api.bilibili.com/x/player/v2",
        params={"bvid": bvid, "cid": cid}
    )
    player_data = resp.json()
    subtitles = player_data.get("data", {}).get("subtitle", {}).get("subtitles", [])
    
    if not subtitles:
        print("[B站] 无 AI 字幕", file=sys.stderr)
        return None
    
    # 下载第一个字幕
    subtitle_url = subtitles[0]["subtitle_url"]
    if subtitle_url.startswith("//"):
        subtitle_url = "https:" + subtitle_url
    
    print(f"[B站] 下载字幕: {subtitle_url}", file=sys.stderr)
    resp = requests.get(subtitle_url)
    subtitle_data = resp.json()
    
    # 提取文本
    segments = []
    for item in subtitle_data.get("body", []):
        start = item.get("from", 0)
        end = item.get("to", 0)
        text = item.get("content", "").strip()
        if text:
            segments.append({"start": start, "end": end, "text": text})
    
    return json.dumps({
        "engine": "bilibili_subtitle",
        "language": "zh",
        "segments": segments,
        "full_text": " ".join(s["text"] for s in segments)
    }, ensure_ascii=False)


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="视频转写 CLI — BiliNote 核心能力轻量版")
    parser.add_argument("url", nargs="?", help="视频 URL 或本地文件路径（配合 --local）")
    parser.add_argument("--local", metavar="FILE", help="转写本地音频/视频文件")
    parser.add_argument("--engine", choices=["bcut", "groq"], default="bcut", help="转写引擎 (默认: bcut)")
    parser.add_argument("--groq-key", help="Groq API Key（或设置 GROQ_API_KEY 环境变量）")
    parser.add_argument("--groq-model", default="whisper-large-v3-turbo", help="Groq 模型名")
    parser.add_argument("--groq-base-url", default="https://api.groq.com/openai/v1", help="Groq API 地址")
    parser.add_argument("-o", "--output", help="输出文件路径（默认 stdout）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--keep-audio", action="store_true", help="保留下载的音频文件")
    parser.add_argument("--audio-dir", default=".", help="音频下载目录")
    parser.add_argument("--screenshot", action="store_true", help="提取视频截图（需配合 --local）")
    parser.add_argument("--screenshot-dir", default="./screenshots", help="截图输出目录")
    parser.add_argument("--screenshot-interval", type=int, default=30, help="截图间隔秒数（默认30）")
    parser.add_argument("--download-video", action="store_true", help="下载视频文件（用于截图）")
    
    args = parser.parse_args()
    
    if not args.url and not args.local:
        parser.print_help()
        sys.exit(1)
    
    # 截图模式（独立功能）
    if args.screenshot:
        video_path = args.local
        if not video_path and args.url:
            video_path = download_video(args.url, args.audio_dir)
        if not video_path:
            print("错误: 截图模式需要 --local 或 URL", file=sys.stderr)
            sys.exit(1)
        screenshots = extract_screenshots(video_path, args.screenshot_dir, args.screenshot_interval)
        if args.json:
            print(json.dumps({"screenshots": screenshots}, ensure_ascii=False, indent=2))
        else:
            print(f"提取了 {len(screenshots)} 张截图:")
            for s in screenshots:
                print(f"  {s}")
        return
    
    # 下载视频模式
    if args.download_video:
        if not args.url:
            print("错误: --download-video 需要 URL", file=sys.stderr)
            sys.exit(1)
        filepath = download_video(args.url, args.audio_dir)
        print(filepath)
        return
    
    # 确定输入文件
    audio_path = None
    source_url = ""
    temp_audio = False
    
    try:
        if args.local:
            audio_path = args.local
            source_url = args.local
        else:
            source_url = args.url
            
            # B站直接尝试字幕提取（跳过音频下载）
            if "bilibili.com" in args.url or "b23.tv" in args.url:
                import re
                bvid_match = re.search(r'BV[\w]+', args.url)
                if bvid_match:
                    bvid = bvid_match.group()
                    subtitle_json = get_bilibili_subtitle(bvid)
                    if subtitle_json:
                        result = json.loads(subtitle_json)
                        output_text = json.dumps(result, ensure_ascii=False, indent=2) if args.json else format_output(result, args.url)
                        if args.output:
                            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                            with open(args.output, 'w', encoding='utf-8') as f:
                                f.write(output_text)
                            print(f"[完成] B站字幕已保存: {args.output}", file=sys.stderr)
                        else:
                            print(output_text)
                        return
            
            # 下载音频
            audio_path = download_audio(args.url, args.audio_dir)
            temp_audio = not args.keep_audio
        
        # 转写
        if args.engine == "bcut":
            transcriber = BcutTranscriber()
            result = transcriber.transcribe(audio_path)
        elif args.engine == "groq":
            api_key = args.groq_key or os.environ.get("GROQ_API_KEY")
            if not api_key:
                print("错误: Groq 引擎需要 API Key，使用 --groq-key 或设置 GROQ_API_KEY", file=sys.stderr)
                sys.exit(1)
            transcriber = GroqTranscriber(api_key, args.groq_model, args.groq_base_url)
            result = transcriber.transcribe(audio_path)
        
        # 输出
        output_text = json.dumps(result, ensure_ascii=False, indent=2) if args.json else format_output(result, source_url)
        
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_text)
            print(f"[完成] 转录已保存: {args.output}", file=sys.stderr)
        else:
            print(output_text)
    
    finally:
        # 清理临时音频
        if temp_audio and audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"[清理] 已删除临时音频: {audio_path}", file=sys.stderr)


if __name__ == "__main__":
    main()


# ============================================================
# 截图提取模块（新增）
# ============================================================

def extract_screenshots(video_path: str, output_dir: str, interval: int = 30, max_frames: int = 20) -> list:
    """
    用 ffmpeg 从视频中提取关键帧截图
    
    Args:
        video_path: 视频文件路径
        output_dir: 截图输出目录
        interval: 提取间隔（秒），默认30秒
        max_frames: 最大帧数，默认20
    
    Returns:
        截图文件路径列表
    """
    import subprocess
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取视频时长
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True
    )
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        duration = 0
    
    if duration == 0:
        print(f"[截图] 无法获取视频时长: {video_path}", file=sys.stderr)
        return []
    
    # 计算实际间隔（确保不超过 max_frames）
    actual_interval = max(interval, int(duration / max_frames))
    
    screenshots = []
    timestamp = 0
    count = 0
    
    while timestamp < duration and count < max_frames:
        output_file = os.path.join(output_dir, f"frame_{count:03d}_{int(timestamp)}s.jpg")
        cmd = [
            "ffmpeg", "-ss", str(timestamp), "-i", video_path,
            "-vframes", "1", "-q:v", "2", "-y", output_file
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0 and os.path.exists(output_file):
            screenshots.append(output_file)
            print(f"[截图] {timestamp:.0f}s → {output_file}", file=sys.stderr)
        timestamp += actual_interval
        count += 1
    
    print(f"[截图] 共提取 {len(screenshots)} 帧", file=sys.stderr)
    return screenshots


def download_video(url: str, output_dir: str = None) -> str:
    """用 yt-dlp 下载视频（用于截图），返回文件路径
    
    如果未指定 output_dir，自动使用隔离的临时目录，处理完成后由调用方负责清理。
    """
    cleanup_dir = False
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="personkb_vid_")
        cleanup_dir = True
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp", 
        "-f", "best[height<=720]",  # 720p 足够截图
        "--no-overwrites",
        "-o", output_path,
        "--print", "after_move:filepath",
        url
    ]
    print(f"[下载视频] yt-dlp -f best[height<=720] {url}", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if cleanup_dir:
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
        raise Exception(f"yt-dlp 视频下载失败: {result.stderr}")
    
    filepath = result.stdout.strip().split('\n')[-1]
    return filepath
