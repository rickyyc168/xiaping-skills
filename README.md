# 🦞 小杨技能库 — XiaoYang Skill Collection

面向 OpenClaw / Claude Code Agent 的精品技能合集，已上架 [虾评Skill](https://xiaping.coze.site) 平台。

## 📦 技能列表

| 技能 | 目录 | 说明 | 下载 | 评分 |
|------|------|------|------|------|
| AI情感咨询与治愈助手 | [`emotion-master/`](emotion-master/) | 三级情绪分析 + 6维度关系评估 + 危机干预安全红线 | 28 | ⭐3.9 |
| 人物知识库助手：视频+文章全网采集 | [`person-kb/`](person-kb/) | B站/YouTube/公众号全网采集，9步流水线构建结构化知识库 | 34 | ⭐4.2 |
| 🏛️ 与马可·奥勒留对话——沉思录 | [`marcus-aurelius/`](marcus-aurelius/) | 基于《沉思录》的斯多葛哲学读书伙伴 | 52 | ⭐4.5 |
| Claude Code 源码架构分析助手 | [`claude-code-analysis/`](claude-code-analysis/) | Claude Code 源码分析 + OpenClaw 适配建议 | 17 | ⭐3.6 |
| 孙宇晨读书对话：残酷与温柔 | [`sun-yuchen-dialogue/`](sun-yuchen-dialogue/) | 基于《这世界既残酷也温柔》的深度读书伙伴 | 16 | ⭐3.0 |
| 🆕 百度网盘AI笔记知识库构建器 | [`baidu-ainote-kb/`](baidu-ainote-kb/) | 百度网盘AI笔记分享链接→结构化课程知识库，支持批量处理+断点续跑 | 3 | — |
| 🆕 与眉山剑客陈平对话 | [`chen-ping-dialogue/`](chen-ping-dialogue/) | 基于陈平教授公开演讲和B站视频的AI对话伙伴，22个核心观点+16条金句 | 9 | — |

## 🚀 安装方式

每个技能目录下的 `SKILL.md` 即为技能入口，遵循 [AgentSkills](https://agentskills.io) 开放标准。

**OpenClaw 安装：**
```bash
# 从虾评平台下载安装
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://xiaping.coze.site/api/skills/{skill_id}/download
```

**Claude Code 安装：**
```bash
# 克隆到技能目录
git clone https://github.com/rickyyc168/xiaping-skills.git
cp -r xiaping-skills/{skill-name} ~/.claude/skills/
```

## 🔗 相关链接

- 虾评平台：https://xiaping.coze.site
- Agent Skills 标准：https://agentskills.io
- OpenClaw：https://github.com/openclaw/openclaw

## 📄 License

MIT