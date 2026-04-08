# 📚 百度网盘AI笔记知识库构建器 v2

> 输入百度网盘AI笔记分享链接，自动提取内容，构建结构化知识库。

## 功能概述

基于百度网盘AI笔记的分享链接，自动完成以下流程：

1. **链接访问** — 通过浏览器打开分享链接（无需登录）
2. **内容提取** — 自动提取AI笔记的完整文本内容
3. **结构整理** — 按章节、知识点、金句分类整理
4. **知识库生成** — 保存为结构化Markdown文件
5. **索引构建** — 自动生成目录索引和跨课程概念关联

## 触发词

- 笔记知识库
- 建知识库
- 提取笔记
- 网盘笔记
- AI笔记提取
- 课程笔记

## 使用方法

### 基本用法

```
用户：帮我提取这个笔记 https://pan.baidu.com/fcb/s?share_uk=xxx&share_id=xxx
用户：我用百度网盘分享了一篇笔记《标题》，链接：https://pan.baidu.com/fcb/s?...
```

### 批量用法

```
用户：
我用百度网盘分享了一篇笔记《01标题》，链接：https://...
我用百度网盘分享了一篇笔记《02标题》，链接：https://...
我用百度网盘分享了一篇笔记《03标题》，链接：https://...
```

---

## 完整处理流程

收到百度网盘AI笔记分享链接后，按以下步骤执行：

---

### 第一步：初始化与去重检查

**目录结构：**

```
workspace/knowledge-base/{课程名称}/
├── README.md                          ← 课程索引
├── progress.json                      ← 进度追踪（支持断点续跑）
├── cache/                             ← 提取缓存
│   └── {hash}.txt                     ← 原始提取文本缓存
├── {序号}-{标题}.md                    ← 各讲笔记
└── ...
```

**初始化 `progress.json`：**

```json
{
  "course": "课程名称",
  "created_at": "2026-04-07T20:55:00+08:00",
  "updated_at": "2026-04-07T20:55:00+08:00",
  "stats": {
    "total": 0,
    "success": 0,
    "failed": 0,
    "skipped": 0
  },
  "links": {
    "processed": [],
    "failed": [],
    "pending": []
  },
  "seen_hashes": []
}
```

**去重规则：**

```
1. URL 级去重：
   - 从 progress.json 读取已处理链接列表
   - 新链接在 processed/failed/pending 中存在 → 跳过

2. 内容级去重：
   - 对提取的文本计算简单 hash（前500字符的 md5）
   - hash 在 seen_hashes 中存在 → 跳过（同一篇笔记可能有多个分享链接）
```

---

### 第二步：批量链接预处理

**链接提取：**

从用户消息中提取所有 `pan.baidu.com/fcb/s` 链接，存入 `pending` 列表。

**去重过滤：**

```python
# 伪代码
pending = extract_links(user_message)
already = progress["links"]["processed"] + progress["links"]["failed"]
new_links = [l for l in pending if l not in already]
skipped = len(pending) - len(new_links)
progress["links"]["pending"] = new_links

if skipped > 0:
    log(f"跳过 {skipped} 个已处理链接")
```

**课程名称推断：**
- 从连续笔记标题中提取共同主题
- 如 "01供求关系"、"02分工和交易" → 课程名称 = "经济学课程"
- 如果无法推断，使用 "笔记知识库-{日期}" 作为默认名称

---

### 第三步：内容提取（核心优化）

#### 浏览器 Session 复用

**关键优化：不要为每个链接反复开关浏览器！**

```
旧流程（慢）：
  链接1: browser navigate → wait 8s → extract → close
  链接2: browser navigate → wait 8s → extract → close
  链接3: browser navigate → wait 8s → extract → close

新流程（快）：
  browser open (一次)
  链接1: browser navigate → wait 3-5s → extract
  链接2: browser navigate → wait 3-5s → extract   ← 复用浏览器，后续加载更快
  链接3: browser navigate → wait 3-5s → extract
  browser close (最后)
```

#### 智能等待（替代固定等待）

不要用固定 `wait 8000ms`，用动态检测：

```
1. browser navigate → 分享链接
2. browser wait → 3000ms（初始等待）
3. browser evaluate → 检查内容是否加载完成：
   - 检查 [role="textbox"] 是否存在且有内容
   - 检查是否显示"笔记正在加载中"
   - 检查是否显示"登录后浏览完整笔记"
4. 如果未加载完成 → 再等 2000ms → 重试检测（最多 3 次）
5. 如果加载完成 → 立即提取，跳过剩余等待时间
```

**加载检测 JS：**

```javascript
// 返回 { loaded: boolean, content: string, reason: string }
(function() {
  // 检查 textbox 编辑器
  var textbox = document.querySelector('[role="textbox"]');
  if (textbox && textbox.textContent.length > 50) {
    return { loaded: true, content: textbox.innerText, reason: 'textbox' };
  }
  
  // 检查笔记内容区域
  var noteContent = document.querySelector('.note-content, .article-content, [class*="note-body"]');
  if (noteContent && noteContent.textContent.length > 50) {
    return { loaded: true, content: noteContent.innerText, reason: 'note-content' };
  }
  
  // 检查是否在加载中
  var loading = document.querySelector('[class*="loading"], [class*="Loading"]');
  if (loading) {
    return { loaded: false, content: '', reason: 'still-loading' };
  }
  
  // 检查是否需要登录
  var body = document.body.innerText;
  if (body.includes('登录后浏览完整笔记')) {
    return { loaded: false, content: '', reason: 'login-required' };
  }
  
  // fallback: 取 body 文本
  if (body.length > 100) {
    return { loaded: true, content: body, reason: 'body-fallback' };
  }
  
  return { loaded: false, content: '', reason: 'unknown' };
})()
```

#### 提取策略（分级降级）

```
优先级 1：[role="textbox"] 编辑器内容（最完整）
  ↓ 失败
优先级 2：笔记内容区域 DOM（.note-content 等）
  ↓ 失败
优先级 3：document.body.innerText（兜底）
  ↓ 失败
标记失败，记录原因，继续下一个
```

#### 缓存原始提取结果

提取成功后，将原始文本存入 `cache/{hash}.txt`：

```
优点：
1. 后续重新处理时无需再打开浏览器
2. 结构化模板调整时可直接从缓存重新生成
3. 出错时只影响结构化步骤，不需要重新提取
```

---

### 第四步：内容清洗与结构化

**清洗规则：**

```
1. 去除页面头部元信息：
   - 去掉 "以下为AI生成的图文笔记的内容" 前缀
   - 去掉分享者信息行
   - 去掉 "只能查看"、"去登录" 等UI文本

2. 保留时间戳标记：
   - 格式：﻿00:15﻿ → 转换为 (00:15)
   - 用于章节定位和视频跳转参考

3. 处理数学公式：
   - 原始格式：﻿𝑀𝑈=Δ𝑈/Δ𝑄﻿ → 转换为可读格式 MU = ΔU/ΔQ
   - 保留公式的语义含义

4. 处理图片引用：
   - 原始格式包含 img 标签 → 替换为 [图示] 或删除
```

**结构化模板：**

```markdown
# {序号}-{标题}

> 来源：百度网盘AI笔记 | {课程系列名}
> 提取时间：{YYYY-MM-DD}

## 一、{大章节名} (时间戳)

### 1. {小节名} (时间戳)

**子主题：**
- 要点1
- 要点2
  - 细节a
  - 细节b

## 二、知识小结

| 知识点 | 核心内容 | 考试重点/易混淆点 | 难度 |
|--------|----------|-------------------|------|
| ... | ... | ... | ⭐⭐ |

## 核心金句

1. "金句内容"
2. "金句内容"
```

---

### 第五步：保存与索引更新

**文件命名规则：**

```
格式：{两位序号}-{简化标题}.md
示例：01-供求关系-Switch和海底捞涨价合理吗.md
```

**保存路径：**

```
/root/.openclaw/workspace/knowledge-base/{课程名称}/
```

**每处理完一篇笔记，立即更新 README.md 索引：**

```markdown
# {课程名称}知识库索引

> 来源：百度网盘AI笔记系列
> 构建时间：{YYYY-MM-DD}
> 总计：{N}讲
> 状态：✅ 已完成 / ⏳ 进行中 ({已完成}/{总计})

## 课程目录

| 讲次 | 文件 | 核心主题 | 关键概念 |
|------|------|----------|----------|
| 01 | [标题](文件名.md) | 主题 | 概念1、概念2 |
| 02 | [标题](文件名.md) | 主题 | 概念1、概念2 |

## 知识脉络

（根据课程内容自动生成层级关系）

## 跨课程核心概念索引

| 概念 | 出现课程 |
|------|----------|
| 机会成本 | 03, 04, 06 |
| 信息不对称 | 05, 08, 09 |
```

---

### 第六步：进度维护与反馈

**每处理一个链接后更新 progress.json：**

```json
{
  "updated_at": "2026-04-07T20:58:00+08:00",
  "stats": {
    "total": 5,
    "success": 3,
    "failed": 0,
    "skipped": 2
  },
  "links": {
    "processed": ["url1", "url2", "url3"],
    "failed": [],
    "pending": ["url4", "url5"]
  }
}
```

**批量处理完成后的汇报：**

```
✅ 批量处理完成

📊 处理统计：
- 总链接：5 个
- 成功提取：3 篇
- 跳过（已处理）：2 篇
- 失败：0 篇

📚 已保存文件：
1. ✅ 01-供求关系.md → knowledge-base/经济学课程/
2. ✅ 02-分工和交易.md → knowledge-base/经济学课程/
3. ✅ 03-选择和歧视.md → knowledge-base/经济学课程/

📈 知识库状态：3/? 讲
🔗 继续发新链接，我接着收
```

---

## 性能优化要点（对比 v1）

| 优化项 | v1 (旧) | v2 (新) | 提升 |
|--------|---------|---------|------|
| 浏览器启动 | 每个链接开关一次 | 全程复用一个 session | 减少 ~3s/链接 |
| 等待策略 | 固定 8s | 智能检测 3-5s（动态） | 平均节省 ~4s/链接 |
| 去重机制 | 无 | URL + 内容 hash 双重去重 | 避免重复处理 |
| 缓存机制 | 无 | 原始文本缓存 | 支持重新结构化 |
| 进度追踪 | 无 | progress.json | 支持断点续跑 |
| 批量汇报 | 逐个汇报 | 完成后统一汇报 | 减少消息干扰 |

---

## 批量处理策略

```
1. 预处理：提取所有链接 → 去重 → 写入 pending
2. 一次性打开浏览器（browser open）
3. 按顺序逐个处理：
   a. browser navigate → 分享链接
   b. 智能等待 → 检测加载完成
   c. 提取内容 → 清洗 → 结构化 → 保存
   d. 更新 progress.json
4. 处理完所有链接后关闭浏览器
5. 统一汇报结果
```

**注意事项：**
- 多个链接可能被拆分成多条消息收到
- 已处理过的链接（通过 progress.json 判断）自动跳过
- 如果中途失败，保留已处理的进度，可断点续跑

---

## 断点续跑

如果批量处理中途中断（超时、错误等），再次收到相同课程的链接时：

```
1. 读取 progress.json
2. 从 pending 中恢复未处理的链接
3. 跳过已在 processed 中的链接
4. 继续处理剩余链接
```

用户也可以主动触发：
```
用户：继续提取之前没处理完的笔记
用户：重新处理第 3 讲（从缓存重新结构化）
```

---

## 高级功能

### 跨课程概念关联

在索引中维护一个跨课程概念表：

```markdown
## 跨课程核心概念索引

| 概念 | 出现课程 | 说明 |
|------|----------|------|
| 机会成本 | 03, 04, 06 | 核心经济学概念，贯穿多讲 |
| 边际效用递减 | 03, 05 | 消费者行为基础 |
| 信息不对称 | 05, 08, 09, 10 | 市场失灵的重要原因 |
| "天下没有免费午餐" | 01, 03, 05, 06 | 反复出现的核心原理 |
```

### 知识脉络自动生成

根据课程序号和主题自动推断知识层级：

```
基础原理层（01-03）：供需、分工、理性选择
个人决策层（04-06）：机会成本、保险、投资
企业市场层（07-09）：创新、激励、治理
社会行为层（10+）：行为偏差、博弈、垄断、公平
```

### 从缓存重新结构化

如果结构调整后需要重新生成：

```
1. 读取 cache/{hash}.txt（原始提取文本）
2. 用新模板重新清洗和结构化
3. 覆盖保存 .md 文件
4. 更新索引
```

---

## 使用示例

### 示例 1：提取单篇笔记

```
用户：帮我提取这个笔记 https://pan.baidu.com/fcb/s?share_uk=12345&share_id=abcdef

Agent：正在提取笔记内容...
✅ 已保存到 knowledge-base/经济学课程/01-供求关系.md

核心知识点：
- 供需关系决定市场价格
- 需求曲线向右下方倾斜
- 供给曲线向右上方倾斜
- 均衡价格由供需交点决定

📚 知识库当前状态：1/?? 讲
🔗 继续发新链接，我接着收
```

### 示例 2：批量提取系列课程

```
用户：
我用百度网盘分享了一篇笔记《01供求关系》，链接：https://pan.baidu.com/fcb/s?share_uk=123&share_id=aaa
我用百度网盘分享了一篇笔记《02分工和交易》，链接：https://pan.baidu.com/fcb/s?share_uk=123&share_id=bbb
我用百度网盘分享了一篇笔记《03选择和歧视》，链接：https://pan.baidu.com/fcb/s?share_uk=123&share_id=ccc

Agent：检测到 3 个链接，正在批量处理...
📊 处理统计：
- 总链接：3 个
- 成功提取：3 篇
- 跳过：0 篇
- 失败：0 篇

已保存文件：
1. ✅ 01-供求关系.md
2. ✅ 02-分工和交易.md
3. ✅ 03-选择和歧视.md

📚 知识库「经济学课程」：3 讲
🔗 继续发新链接
```

### 示例 3：断点续跑

```
用户：之前处理到一半断了，继续提取

Agent：检测到未完成的任务，从断点继续...
  pending 中还有 5 个链接待处理
✅ 处理完成，新增 5 篇笔记

📚 知识库「经济学课程」：8 讲
```

### 示例 4：跳过已处理链接

```
用户：帮我提取这个链接 https://pan.baidu.com/fcb/s?share_uk=123&share_id=aaa

Agent：该链接已处理过（01-供求关系.md），自动跳过。
如需重新提取，请告诉我。
```

### 示例 5：从缓存重新结构化

```
用户：之前提取的第3讲格式不太好，重新整理一下

Agent：从缓存重新结构化 03-选择和歧视.md...
✅ 已更新，新增了「知识小结」表格和「核心金句」板块
```

---

## 注意事项

1. **链接有效性**：百度网盘分享链接可能有过期时间，过期后需重新分享
2. **内容完整性**：AI笔记可能不完整（需要登录查看完整内容的情况）
3. **动态渲染**：必须使用浏览器工具，web_fetch 无法获取内容
4. **加载时间**：百度网盘页面加载较慢，智能等待通常 3-5 秒
5. **批量限制**：大量链接处理时注意浏览器资源占用，建议每批不超过 20 个
6. **浏览器复用**：不要频繁开关浏览器，全程复用一个 session
