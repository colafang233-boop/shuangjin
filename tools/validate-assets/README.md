# 资产 Manifest 校验器

校验 `manifests/assets-manifest.json` 与仓库文件是否一致，避免资产状态、提示词路径和交付文件静默分叉。

## 运行

```bash
python3 tools/validate-assets/validate_manifest.py
```

指定其他仓库根目录或 Manifest：

```bash
python3 tools/validate-assets/validate_manifest.py \
  --repo-root . \
  --manifest manifests/assets-manifest.json
```

## 当前校验规则

- Manifest 根节点和 `assets` 结构合法
- `statusFlow` 非空且无重复值
- asset ID 唯一
- `name`、`category`、`chapter`、`batch` 非空
- `status` 必须出现在 `statusFlow`
- 所有非空的 `promptFile`、`sourceFile`、`runtimeFiles` 必须存在
- 活跃的非工具资产必须声明 `promptFile`
- `DONE` 资产必须至少声明一个交付路径
- Issue 编号必须为正整数

## 测试

```bash
python3 -m unittest discover -s tools/validate-assets/tests -p 'test_*.py'
```

校验器只使用 Python 标准库，不需要安装额外依赖。
