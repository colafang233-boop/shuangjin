# 环境素材提示词索引

## 第一波生成顺序

| 顺序 | 批次 | 文件 | 版式 | 主要用途 |
|---:|---|---|---|---|
| 1 | S00-09 | `s00-09-village-material-language.md` | 3×3 | 锁定寒霜村材质与建筑语言 |
| 2 | VIL-01 | `vil-01-wooden-props.md` | 4×4 | 木桶、木箱、柴薪、推车等木制杂物 |
| 3 | VIL-02 | `vil-02-ceramics-teaware.md` | 4×4 | 陶器、茶具、酒器与药罐 |
| 4A | VIL-03A | `vil-03a-ground-tiles.md` | 4×4 | 地面、雪地、冻土与过渡块 |
| 4B | VIL-03B | `vil-03b-stone-walls.md` | 3×3 | 石墙直线、转角、破损和入口模块 |

## 执行规则

1. 每次只处理一个提示词文件，不把多个批次混到同一张图。
2. 原图先提交到 `assets/source/generated/<batch>/`。
3. 在对应 Issue 中记录候选版本、问题和选中格子。
4. 通过 `tools/slice-grid/` 切图，并将结果放入 `assets/source/selected/<batch>/`。
5. 更新 `manifests/assets-manifest.json` 后，才进入游戏接入。
6. 未通过验收的图片保留版本记录，但不得放入 `assets/runtime/`。

## 第一波接入门槛

- S00-09 风格板通过人工确认；
- VIL-01 至少 12/16 可用；
- VIL-02 至少 12/16 可用；
- VIL-03A 至少 12/16 可用；
- VIL-03B 至少 7/9 可用；
- 所有正式切图无文字、无白边、锚点稳定。
