# 🦞 小杨技能库 — XiaoYang Skill Collection

面向 OpenClaw / Claude Code Agent 的精品技能合集，已上架 [虾评Skill](https://xiaping.coze.site) 平台。

## 📦 技能列表

| 技能 | 目录 | 说明 | 下载 | 评分 |
|------|------|------|------|------|
| 💗 情感大师 | [`emotion-master/`](emotion-master/) | AI 情感咨询与治愈，三级情绪分析 + 6维度关系评估 | 16 | ⭐4.9 |
| 🏛️ 与马可·奥勒留对话 | [`marcus-aurelius/`](marcus-aurelius/) | 基于《沉思录》的斯多葛哲学读书伙伴 | 5 | ⭐4.0 |
| 🦞 Claude Code 架构精华 | [`claude-code-analysis/`](claude-code-analysis/) | Claude Code 源码分析 + OpenClaw 适配建议 | 7 | ⭐4.6 |
| 💗 与孙宇晨对话 | [`sun-yuchen-dialogue/`](sun-yuchen-dialogue/) | 基于《这世界既残酷也温柔》的深度读书伙伴 | 4 | ⭐3.0 |

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
