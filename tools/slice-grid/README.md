# 资产板自动切图工具

将 GPT 生成的 2×2、3×3、4×4 RPG 资产板拆分为独立 PNG/WebP，并同时生成来源、格子坐标、尺寸和 SHA-256 记录。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r tools/slice-grid/requirements.txt
```

## 基础用法

```bash
python tools/slice-grid/slice_grid.py \
  assets/source/generated/vil-01-board-01.png \
  assets/source/selected/vil-01-board-01/ \
  --rows 4 \
  --cols 4 \
  --prefix env_village_props_wood_board01 \
  --contact-sheet assets/previews/vil-01-board-01-contact.png
```

输出文件名：

```text
env_village_props_wood_board01_a1.png
env_village_props_wood_board01_a2.png
...
env_village_props_wood_board01_d4.png
```

## 带边距与格间距

```bash
python tools/slice-grid/slice_grid.py board.png output/ \
  --rows 3 --cols 3 \
  --outer-margin 36,40,36,40 \
  --gutter 24,24 \
  --prefix env_snowfield_rocks_board01
```

`--outer-margin` 支持：

- `20`：四边都是20px
- `20,30`：上下20px、左右30px
- `10,20,30`：上10px、左右20px、下30px
- `10,20,30,40`：上、右、下、左

## 透明裁剪与统一锚点

角色、怪物和透明道具可以裁掉空白后放回统一画布：

```bash
python tools/slice-grid/slice_grid.py board.png output/ \
  --rows 4 --cols 4 \
  --trim-alpha \
  --trim-threshold 4 \
  --padding 6 \
  --canvas 256x256 \
  --anchor bottom-center \
  --prefix chr_lingshuang_idle
```

锚点：

- `center`：居中
- `bottom-center`：脚底或物体底部对齐
- `top-left`：左上对齐

如果裁剪结果大于目标画布，工具会报错，不会偷偷缩放素材。

## 输出 Manifest

默认在输出目录生成 `<prefix>.manifest.json`：

```json
{
  "source": { "path": "board.png", "sha256": "..." },
  "grid": { "rows": 4, "columns": 4 },
  "items": [
    {
      "cell": "a1",
      "filename": "env_props_a1.png",
      "cropBox": [0, 0, 384, 384],
      "width": 256,
      "height": 256,
      "sha256": "..."
    }
  ]
}
```

这个文件用于将生成母图、格子编号、筛选结果和游戏运行资产关联起来。

## 安全行为

- 默认拒绝覆盖已有切图、Manifest和联系表
- 使用 `--overwrite` 才会覆盖
- 文件前缀只允许英文、数字、下划线和连字符
- 不会自动缩放原始素材
- 输入支持 PNG 和 WebP，输出支持 PNG 和无损 WebP

## 测试

```bash
python -m unittest discover tools/slice-grid/tests -v
```
