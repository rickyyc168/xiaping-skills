# 🧠 人物知识库构建器

> 输入一个人物名称，自动搜集其相关文章和视频资料，构建结构化个人知识库。

## 功能概述

基于人物名称，自动完成以下流程：

1. **人物消歧** — 确认目标人物身份，避免同名混淆
2. **文章采集** — 多源搜索 + 去重，抓取该人物的相关文章、报道、访谈
3. **视频采集** — 字幕优先提取，支持 B站/YouTube/抖音/快手
4. **内容提取** — 金句、观点矩阵、时间线自动整理
5. **知识库生成** — 根据人物类型动态生成画像

## 模式说明

| 模式 | 依赖 | 视频处理能力 | 适合谁 |
|------|------|-------------|--------|
| **⚡ 轻量模式**（默认） | transcribe.py + yt-dlp + ffmpeg + requests | 字幕提取 + Bcut转录 + 截图 + 多平台下载 | 所有人，开箱即用 |
| **🚀 完整模式** | BiliNote Docker | + 快手/小宇宙下载 + AI笔记 + RAG问答 | 深度用户 |

> 轻量模式已覆盖 B站/YouTube/抖音，内置 Bcut 免费转写 + ffmpeg 截图。BiliNote 仅在需要快手/小宇宙和 RAG 问答时才需要。

## 触发词

- 建人物档案
- 人物知识库
- 收集人物资料
- person-kb
- 某人调研

## 使用方法

### 基本用法

```
用户：帮我调研一下 张三
用户：建人物档案：雷军
用户：收集 Elon Musk 的资料
```

### 完整流程

收到人物名称后，按以下步骤执行：

---

#### 第一步：人物消歧（关键步骤）

> **为什么重要**：同名问题严重。搜"张伟"有几百万个结果，必须先确认目标。

**消歧流程：**

```
输入：人物名称
  │
  ├─ 1. 初始搜索
  │   mimo_web_search "{人物名称}" + 个人简介
  │   → 取前5条结果，提取人物描述
  │
  ├─ 2. 身份识别
  │   从搜索结果中提取：
  │   - 身份标签（企业家/学者/演员/运动员...）
  │   - 所属机构（公司/大学/团队）
  │   - 代表作品/成就
  │   - 活跃领域（科技/金融/娱乐...）
  │
  ├─ 3. 多人判断
  │   ├─ 搜索结果指向同一人 → ✅ 确认，继续
  │   ├─ 搜索结果指向多人 → ⚠️ 询问用户确认目标
  │   │   回复格式：
  │   │   "找到多个同名人物，请确认你要调研的是：
  │   │    1. 张伟 — 阿里巴巴技术副总裁
  │   │    2. 张伟 — 北京大学物理系教授
  │   │    3. 张伟 — 演员，代表作《xxx》"
  │   └─ 搜索结果太少 → 扩大搜索词再试一次
  │
  └─ 4. 生成身份锚点
     输出确认信息，后续所有搜索围绕此身份：
     "目标人物：雷军，小米集团创始人兼CEO，科技领域"
```

**消歧搜索关键词：**

```
mimo_web_search "{人物名称} 个人简介"
mimo_web_search "{人物名称} 简历 背景"
```

---

#### 第二步：初始化知识库目录

在工作区创建目录结构：

```
workspace/person-kb/{人物名称}/
├── overview.md        # 📋 一页纸速览（边采集边更新）
├── articles/          # 文章资料
│   └── {来源}_{日期}_{标题}.md
├── videos/            # 视频资料
│   ├── transcripts/   # 字幕/转录文本
│   │   └── {来源}_{标题}.txt
│   ├── audio/         # 下载的音频文件（转录中间产物）
│   │   └── {标题}.mp3
│   ├── keyframes/     # 关键帧截图（无字幕视频）
│   │   └── {来源}_{标题}/
│   └── notes/         # 结构化视频笔记
│       └── {标题}.md
├── quotes/            # 金句/名言
│   └── quotes.md
├── opinions.md        # 观点矩阵（按话题整理）
├── cross-check.md     # 交叉验证报告（矛盾检测）
├── timeline.md        # 重要事件时间线
├── profile.md         # 综合人物画像（动态模板）
└── progress.json      # 进度追踪（支持断点续跑）
```

**初始化 `progress.json`：**

```json
{
  "person": "雷军",
  "identity": "小米集团创始人兼CEO",
  "domain": "科技",
  "profile_type": "entrepreneur",
  "started_at": "2026-04-05T14:52:00+08:00",
  "steps": {
    "disambiguate": "done",
    "init_dir": "done",
    "search_articles": "pending",
    "fetch_articles": "pending",
    "search_videos": "pending",
    "process_videos": "pending",
    "extract_quotes": "pending",
    "cross_validate": "pending",
    "build_opinions": "pending",
    "build_timeline": "pending",
    "generate_profile": "pending"
  },
  "collected": {
    "articles": [],
    "videos": [],
    "seen_urls": []
  }
}
```

> 每完成一步更新 `progress.json`，中断后可从断点继续。

---

#### 第三步：文章采集（去重优化）

**搜索策略（两阶段，减少重叠）：**

```
阶段一：身份锚定搜索（确定人物基本画像）
  mimo_web_search "{人物名称} {身份标签} 简介"

阶段二：深度定向搜索（基于身份信息精确搜索）
  以下搜索并行执行，取不重复结果：

  A. 观点类
     mimo_web_search "{人物名称}" + 观点/理念/方法论

  B. 访谈类
     mimo_web_search "{人物名称}" + 采访/访谈/对话

  C. 争议类
     mimo_web_search "{人物名称}" + 争议/批评/评价

  D. 动态类
     mimo_web_search "{人物名称} 2025 OR 2026" 最新

  E. 社交媒体（按人物类型选做）
     mimo_web_search site:zhihu.com "{人物名称}"                       # 知乎回答/专栏
     mimo_web_search site:weibo.com "{人物名称}"                        # 微博发言
     mimo_web_search site:x.com OR site:twitter.com "{人物名称}"        # Twitter/X
     mimo_web_search site:linkedin.com/in "{人物名称}"                  # LinkedIn（职场人物）
     mimo_web_search "{人物名称}" site:mp.weixin.qq.com                 # 微信公众号文章

  F. 学术类（仅学者/研究人员，profile_type=researcher 时自动启用）
     mimo_web_search "{人物名称}" site:scholar.google.com               # Google Scholar
     mimo_web_search "{人物名称}" site:cnki.net                         # 知网
     mimo_web_search "{人物名称}" site:arxiv.org                        # 预印本
     mimo_web_search "{人物名称}" 论文 OR 发表 OR 研究                  # 通用学术搜索
```

**去重规则：**

```python
# 在采集过程中维护 seen_urls 列表
seen_urls = progress["collected"]["seen_urls"]

for each search_result:
    url = normalize_url(result.url)  # 去掉 tracking 参数
    if url in seen_urls:
        skip  # 已采集过
    if domain_in(url, ["baijiahao", "sohu/a", "163/a"]):  # 低质量聚合站
        skip  # 跳过内容农场
    seen_urls.append(url)
    fetch_and_save(result)
```

**抓取规则：**

- 每个搜索取前 3-5 条结果
- URL 去重后使用 `web_fetch` 抓取全文
- 保存为 Markdown，保留来源 URL 和抓取日期
- 跳过付费墙、登录墙、内容农场
- 超过 10000 字的文章：保存全文 + 生成摘要

**文件命名：**
```
{来源域名}_{YYYY-MM-DD}_{文章标题前15字}.md
例：36kr_2026-01-15_雷军谈小米汽车的三个.md
```

---

#### 第四步：视频采集

> **轻量模式**（默认）：只提取有字幕的视频，无字幕视频记录 URL 标记"待处理"
> **完整模式**（BiliNote）：无字幕视频自动音频转录 + AI 笔记生成

**搜索策略（精准化，减少噪音）：**

```
# 基础搜索（结合消歧身份信息，避免同名干扰）
mimo_web_search "{人物名称} {公司/身份}" 演讲 OR 采访 OR 对话
mimo_web_search "{人物名称} {公司/身份}" site:bilibili.com
mimo_web_search "{人物名称} {公司/身份}" site:youtube.com

# 高价值场景补充（仅在基础搜索结果不足时启用）
mimo_web_search "{人物名称}" TED OR 毕业演讲 OR 年度演讲
mimo_web_search "{人物名称}" 深度对话 OR 长访谈
mimo_web_search "{人物名称}" site:douyin.com        # 抖音（yt-dlp原生支持）
```

**支持的视频平台（轻量模式）：**

| 平台 | 字幕 | 转录 | 截图 | 下载方式 |
|------|------|------|------|----------|
| B站 | ✅ AI字幕接口 | ✅ Bcut | ✅ ffmpeg | yt-dlp |
| YouTube | ✅ yt-dlp字幕 | ✅ Bcut/Groq | ✅ ffmpeg | yt-dlp |
| 抖音 | ❌ | ✅ Bcut | ✅ ffmpeg | yt-dlp（原生支持Douyin） |
| 本地视频 | 看srt | ✅ Bcut | ✅ ffmpeg | 直接读取 |

> 快手、小宇宙播客需要 BiliNote 完整模式（有专用下载器）。

**视频质量过滤规则：**

采集到视频 URL 后，按以下规则筛选，不符合的跳过：

| 过滤条件 | 规则 | 原因 |
|----------|------|------|
| 时长 < 1分钟 | ❌ 跳过 | 多为片段/剪辑，信息量低 |
| 时长 > 2小时 | ⚠️ 仅提取前30分钟 | 完整处理成本过高 |
| 标题含"混剪""盘点""合集" | ⚠️ 降权 | 二手编辑，非原始素材 |
| 频道粉丝 < 1000 | ⚠️ 谨慎 | 可能是搬运/低质内容 |
| 与目标人物相关性低 | ❌ 跳过 | 标题/简介中未明确提及目标人物 |
| 同一视频多个分P | ✅ 仅处理主P | 避免重复 |

**优先级排序（同平台内）：**

```
1. 🎯 官方频道/账号发布（最高优先级）
2. 🎤 正式采访/对话/演讲（一手素材）
3. 📰 媒体报道中的视频片段（二手但可靠）
4. 🎬 粉丝剪辑/解说（参考价值，降权处理）
```

**处理流程：**

```
视频URL
  │
  ├─ B站视频？
  │   └─ 直接调用 Bilibili AI 字幕接口（零成本，最快）
  │       ├─ 有字幕 → ✅ 直接输出
  │       └─ 无字幕 → 降级到音频转录
  │
  ├─ YouTube 视频？
  │   └─ yt-dlp 提取字幕
  │       ├─ 有字幕 → ✅ 直接输出
  │       └─ 无字幕 → 降级到音频转录
  │
  ├─ 音频转录（无字幕时）
  │   ├─ 轻量模式：transcribe.py --engine bcut（免费，B站接口）
  │   ├─ 有 Groq Key：transcribe.py --engine groq（最快）
  │   └─ 完整模式：调用 BiliNote Docker API
  │
  ├─ 截图提取（新增，轻量模式可用）
  │   └─ 下载视频 → ffmpeg 按间隔提取关键帧
  │       python3 transcribe.py --screenshot --local video.mp4
  │       → 保存到 videos/screenshots/
  │
  └─ BiliNote Docker 可用？
      └─ 是 → 调用 API 生成完整 AI 笔记（含截图+摘要+要点）
```

**轻量模式 CLI 调用方式（Agent 直接 bash 执行）：**

```bash
# === B站视频：自动提取字幕（无需下载音频）===
python3 skills/person-kb/transcribe.py "https://www.bilibili.com/video/BV1xx411c7mD"
# 自动：先尝试 B站 AI 字幕 → 无字幕则下载音频用 Bcut 转写

# === YouTube 视频：字幕优先，降级转录 ===
python3 skills/person-kb/transcribe.py "https://www.youtube.com/watch?v=xxx"

# === 指定输出文件 ===
python3 skills/person-kb/transcribe.py -o videos/transcripts/output.txt "视频URL"

# === 使用 Groq 加速（需 GROQ_API_KEY）===
python3 skills/person-kb/transcribe.py --engine groq "视频URL"

# === 转写本地音频文件 ===
python3 skills/person-kb/transcribe.py --local audio.mp3

# === JSON 格式输出（含精确时间戳）===
python3 skills/person-kb/transcribe.py --json -o result.json "视频URL"

# === 截图提取（从本地视频，每30秒一帧）===
python3 skills/person-kb/transcribe.py --screenshot --local video.mp4 --screenshot-dir videos/screenshots/

# === 截图+转录一步完成 ===
# 先下载视频
python3 skills/person-kb/transcribe.py --download-video -o video.mp4 "视频URL"
# 然后转录+截图
python3 skills/person-kb/transcribe.py --local video.mp4 -o transcript.txt
python3 skills/person-kb/transcribe.py --screenshot --local video.mp4
```

**transcribe.py 内置能力（源自 BiliNote，MIT License）：**

| 能力 | 来源 | 说明 |
|------|------|------|
| Bcut 转写 | bcut.py | B站免费 ASR 接口，中文效果好，无需 API Key |
| Groq 转写 | groq.py | Groq Whisper API，英文/多语言效果好 |
| B站字幕 | bilibili_downloader.py | 直接调用 Bilibili AI 字幕接口 |
| VTT 解析 | — | 自动解析 yt-dlp 下载的 VTT 字幕 |
| 截图提取（新增） | ffmpeg | 按间隔从视频提取关键帧 |
| 视频下载 | yt-dlp | 支持 B站/YouTube/抖音，720p 节省空间 |

---

**AI 笔记生成（轻量模式，Agent 自动执行）：**

转录完成后，Agent 按以下模板自动生成结构化笔记：

```markdown
# 视频笔记：{标题}

> 🔗 {平台} | ⏱ {时长} | 📅 {日期} | 🔧 {引擎}

## 摘要（3-5句话概括核心内容）

## 与{人物名称}直接相关的内容
### 关键观点
1. [00:02:30] 观点一
2. [00:05:15] 观点二
### 直接引用（🔴A级）
- [00:03:20] "原话"

## 截图分析（如有）
（对关键帧进行场景识别和文字OCR）
```

> 转录由 transcribe.py 做（工具），笔记生成由 Agent 自己做（基于理解）。与 BiliNote 完整模式的区别：BiliNote 用 GPT API 自动生成，轻量模式用 Agent 自身能力——效果相当，速度稍慢。

#### 第五步：金句提取（带可信度标注）

从所有文章和视频转录中提取，每条标注可信度等级：

**可信度分级标准：**

| 等级 | 标记 | 标准 | 示例 |
|------|------|------|------|
| A - 原话 | 🔴 | 带引号的直接引用，或视频中亲口说的 | "我从金山学到最重要的是坚持" |
| B - 转述 | 🟡 | 记者/他人转述，有具体来源 | 据《财经》报道，他曾表示... |
| C - 传闻 | 🟢 | 多手转述、坊间流传、无具体出处 | 据说他年轻时... |

**提取规则：**

1. 优先提取带引号的直接引用（🔴A级）
2. 区分"本人原话"和"记者转述"（🟡B级）
3. 传闻类信息谨慎收录，必须标注来源
4. 同一句话多次出现 → 标注最早出处，后续标注"多处引用"
5. **不同来源对同一句话表述不一致** → 同时收录，标注差异（交叉验证）

**输出格式：**

```markdown
# {人物名称} 金句集

> 共收录 N 条 | 🔴A级 X 条 | 🟡B级 Y 条 | 🟢C级 Z 条

## 核心理念
- 🔴 "xxx" — 来源：{出处} [时间]
- 🟡 xxx — 来源：{记者}报道于{媒体} [时间]

## 商业/专业观点
- 🔴 "xxx" — 来源：{视频平台} [00:05:30]
- 🟡 xxx — 来源：{媒体} [时间]

## 个人经历
- 🔴 "xxx" — 来源：{出处} [时间]
- 🟢 xxx — 来源：{出处}（未经本人确认）[时间]

## 争议言论
- 🔴 "xxx" — 来源：{出处}，背景：{简要背景}
  ⚠️ 此言论引发争议：{争议方观点}

## ⚠️ 存疑信息
> 以下信息来源单一或可信度存疑，仅供参考

- 🟢 xxx — 仅来源：{出处}，无法交叉验证
```

---

#### 第六步：交叉验证（冲突检测）

> 从所有采集资料中提取关键事实，检测不同来源的矛盾说法。

**验证维度：**

| 维度 | 检查内容 | 示例冲突 |
|------|----------|----------|
| 时间 | 出生日期、事件时间 | A文"1992年加入金山" vs B文"1991年" |
| 身份 | 职位、头衔、学历 | A文"清华硕士" vs B文"武大学士" |
| 数据 | 金额、人数、排名 | A文"融资1亿" vs B文"融资8000万" |
| 观点 | 对同一话题的态度 | A文"看好AI" vs B文"对AI持谨慎态度" |
| 关系 | 与他人关系描述 | A文"师从X" vs B文"与X是同学" |

**输出格式：**

```markdown
# {人物名称} 交叉验证报告

## ✅ 已验证一致的事实
> 多个来源交叉确认，可信度高

| 事实 | 来源数 | 来源 |
|------|--------|------|
| 1969年出生于湖北仙桃 | 5 | 百度百科、36kr、知乎、... |
| 创立小米公司 | 所有来源 | — |

## ⚠️ 存在矛盾的事实
> 不同来源说法不一，需要人工判断

### 矛盾1：加入金山的时间
- **说法A**（36kr、百度百科）：1992年
- **说法B**（金山官网、自传）：1991年底
- **分析**：可能是入职时间和正式编制时间的差异
- **建议**：采用"1991年底加入，1992年正式任职"

### 矛盾2：xxx
- **说法A** ...
- **说法B** ...

## ❌ 已排除的错误信息
> 经交叉验证确认为错误的说法

| 错误说法 | 正确事实 | 错误来源 |
|----------|----------|----------|
| xxx | xxx | {来源} |
```

> **处理原则**：不一致的信息不要直接丢弃，记录所有版本让用户自行判断。时间线中采用可信度最高的版本，矛盾处标注脚注。

---

#### 第七步：观点矩阵

从文章和视频中提取该人物对各话题的立场：

```markdown
# {人物名称} 观点矩阵

| 话题 | 立场 | 原话/摘要 | 来源 |
|------|------|----------|------|
| AI 发展 | 乐观，认为是最大机遇 | "AI将重塑所有行业" | 2025演讲 |
| 创业 | 务实派，强调现金流 | "先活下来再说理想" | 36kr采访 |
| 管理 | 扁平化，反对996 | "效率不靠加班" | 知乎回答 |
| ... | ... | ... | ... |
```

**话题自动识别：**
从采集内容中自动归纳话题标签（技术、商业、管理、人生、社会...）

---

#### 第八步：时间线整理

```markdown
# {人物名称} 时间线

| 时间 | 事件 | 类型 | 来源 |
|------|------|------|------|
| 1969年 | 出生于湖北仙桃 | 个人 | 百度百科 |
| 1992年 | 加入金山软件 | 职业 | 36kr |
| 2010年 | 创立小米公司 | 创业 | 官网 |
| ... | ... | ... | ... |
```

**事件类型标签：** 个人 / 教育 / 职业 / 创业 / 成就 / 争议 / 转折

---

#### 第九步：生成人物画像（动态模板）

根据第一步识别的人物类型，选择对应模板：

**🧑‍💼 企业家模板（profile_type: entrepreneur）：**

```markdown
# {人物名称} 人物画像

## 基本信息
- 姓名 / 出生 / 教育背景
- 当前身份：{公司} {职位}
- 代表成就：{核心成就}

## 创业历程
（按时间线梳理关键决策和转折点）

## 商业理念
（从观点矩阵中提取，按主题分组）

## 管理风格
（从访谈和他人评价中提取）

## 产品哲学
（对产品的理解、设计理念）

## 争议与批评
（客观记录，标注各方立场）

## 最新动态
（近6个月的重要事件）

## 信息来源统计
- 文章：N 篇 | 视频：M 条 | 社交媒体：K 条
- 采集时间：{日期}
```

**🎓 学者模板（profile_type: researcher）：**

```markdown
# {人物名称} 人物画像

## 基本信息
- 姓名 / 出生 / 学位
- 当前机构：{大学/研究所} {职位}
- 研究方向：{方向1}、{方向2}

## 学术成就
- 代表论文（按引用量排序）
- H指数 / 总引用
- 主要贡献

## 学术观点
（对领域内关键问题的立场）

## 教学与培养
（学生评价、教学理念）

## 争议与学术争论
```

**🎭 艺术家/创作者模板（profile_type: creator）：**

```markdown
# {人物名称} 人物画像

## 基本信息
- 姓名 / 出生 / 领域
- 代表作品

## 艺术风格
（从作品分析和评论中提取）

## 创作理念
（对创作的理解和方法论）

## 成长轨迹
（从素人到成名的关键节点）

## 评价与影响
（同行评价、粉丝文化、行业影响）
```

**❓ 通用模板（profile_type: general）：**
当无法判断具体类型时使用，包含基本信息、核心观点、重要事件、社会评价。

---

## 依赖工具

| 工具 | 用途 | 模式 |
|------|------|------|
| mimo_web_search | 搜索文章和视频 | ⚡ 轻量 ✅ 完整 |
| web_fetch | 抓取文章全文 | ⚡ 轻量 ✅ 完整 |
| **transcribe.py** | **视频转写+截图 CLI** | **⚡ 轻量 ✅ 完整** |
| yt-dlp | 音频/视频下载+字幕 | ⚡ 轻量 ✅ 完整 |
| ffmpeg | 音频转码+视频截图 | ⚡ 轻量 ✅ 完整 |
| requests | HTTP 请求（Python） | ⚡ 轻量 ✅ 完整 |
| BiliNote (Docker) | 快手/小宇宙下载+RAG | 🚀 完整 |

### transcribe.py 使用说明（内置）

```bash
# Bcut 免费中文转录（默认引擎，零配置）
python3 skills/person-kb/transcribe.py "视频URL"

# Groq Whisper 加速（需 GROQ_API_KEY）
export GROQ_API_KEY=your_key
python3 skills/person-kb/transcribe.py --engine groq "视频URL"

# 转写本地音频
python3 skills/person-kb/transcribe.py --local audio.mp3

# 提取视频截图（每30秒一帧）
python3 skills/person-kb/transcribe.py --screenshot --local video.mp4

# 下载视频文件
python3 skills/person-kb/transcribe.py --download-video -o video.mp4 "视频URL"

# JSON 输出
python3 skills/person-kb/transcribe.py --json "视频URL"
```

## ⚠️ 数据安全与敏感内容处理

> 视频转录过程会将音频/视频数据发送至第三方服务，请注意以下事项：

### 数据流向说明

| 处理方式 | 数据去向 | 是否适合敏感内容 |
|----------|----------|:----------------:|
| B站 AI 字幕 | Bilibili 服务器（仅获取字幕） | ✅ 低风险 |
| Bcut 转录 | Bilibili Bcut API（上传音频） | ⚠️ 不推荐 |
| Groq Whisper | Groq API（上传音频） | ⚠️ 不推荐 |
| yt-dlp 下载 | 直接下载到本地 | ✅ 低风险 |
| ffmpeg 截图 | 纯本地处理 | ✅ 安全 |

### 敏感内容建议

当调研对象涉及**保密信息、内部资料、未公开录音**时，请遵循以下原则：

1. **优先使用 B站字幕提取**（纯 API 查询，不上传内容）
2. **优先使用 yt-dlp 字幕**（直接下载平台字幕，不上传音频）
3. **避免使用 Bcut/Groq 转录**（会将音频文件发送至第三方服务器）
4. **本地视频使用 `--local` 模式**，配合 ffmpeg 截图，全程本地处理
5. **涉密内容使用本地 Whisper 模型**（如 `faster-whisper`），不依赖任何外部 API

```bash
# ✅ 推荐：纯本地处理敏感内容
# 1. 手动下载视频到本地
# 2. 仅使用本地截图（不上传任何数据）
python3 transcribe.py --screenshot --local sensitive_video.mp4

# ❌ 不推荐：敏感内容使用 Bcut/Groq
python3 transcribe.py "https://example.com/sensitive_video"
```

### 文件隔离

transcribe.py 下载的音频/视频文件会自动存放在隔离的临时目录中，处理完成后自动清理，不会残留中间文件到工作区。

---

## 注意事项

1. **信息准确性** — 所有信息标注来源，不做无依据的推断
2. **隐私边界** — 仅采集公开信息，不涉及隐私数据
3. **客观中立** — 人物画像保持客观，正面负面信息均衡收录
4. **版权尊重** — 保存摘要和引用，不全文搬运受版权保护的内容
5. **大文件处理** — 视频超过 30 分钟，仅提取前 15 分钟的字幕/关键帧
6. **同名处理** — 搜索结果指向多人时必须询问用户确认

## 高级用法

### 指定信息来源
```
只从学术数据库收集 张三 的资料
重点关注 雷军 2024年以后的信息
```

### 指定语言
```
收集 Elon Musk 的英文资料
```

### 增量更新
```
更新 雷军 的人物档案（只补充新内容）
```

### 断点续跑
```
继续采集 雷军 的资料（读取 progress.json 从断点继续）
```
