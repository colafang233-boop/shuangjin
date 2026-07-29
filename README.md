# 霜烬（Shuangjin）

一款中国古风仙侠题材的 2.5D 在线动作角色扮演游戏。当前开发目标是完成第一章《沉冰地宫》的完整垂直切片：村庄调查、雪原战斗、临时队友、地宫封印、三阶段 Boss 与支线驱动的双结局。

## 当前状态

- 已完成：原生 Canvas 灰盒原型
- 已验证：移动、战斗、任务、封印、Boss、双结局
- 正在进行：美术风格锁定与 RPG 贴图批量生产
- 当前章节：第一章《沉冰地宫》

## 项目原则

1. 本仓库是项目唯一事实源。
2. 游戏机制可以参考经典国产 ARPG，但角色、剧情、美术、音乐与地图表达全部原创。
3. 所有生成素材必须经过筛选、规范化、切图、入库和游戏内验收。
4. 聊天中形成的重要决定必须同步到代码、文档、清单或 Issue。

## 目录

```text
game/               可运行游戏与测试
content/            章节、任务、对话、敌人和结局数据
assets/             运行时素材、源素材与预览
prompts/            可复现的素材生成提示词
manifests/          机器可读资产与批次清单
docs/               设计、架构、美术规范与决策记录
tools/              切图、规范化、校验与图集工具
prototypes/         历史灰盒原型
```

## 本地运行

```bash
cd game
python3 -m http.server 8080
```

浏览器打开 `http://localhost:8080`。

## 当前工作入口

- [资产生产追踪表](docs/ASSET_TRACKER.md)
- [美术规范](docs/ART_BIBLE.md)
- [资产生产管线](docs/ASSET_PIPELINE.md)
- [架构说明](docs/ARCHITECTURE.md)
- [第一章设计](docs/CHAPTER_01.md)
- [资产清单](manifests/assets-manifest.json)

## 名称

- 游戏名：《霜烬》
- 英文仓库名：`shuangjin`
- 第一章：《沉冰地宫》
