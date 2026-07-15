# ReconFlow 图标包

三套方案都保留 SVG 源文件，并生成独立的 Tauri 图标包：

- `variants/core/`：黑色主体＋蓝色匹配笔画。
- `variants/apex/`：单色硬朗轮廓。
- `variants/signal/`：单色蓝色连续轨迹。

每套的 `tauri/` 目录都包含项目当前需要的：

- `32x32.png`
- `128x128.png`
- `128x128@2x.png`
- `icon.png`
- `icon-source.png`
- `icon.icns`
- `icon.ico`
- 其他通用 PNG 和 Windows Square Logo 尺寸

以后需要切换时，在项目根目录执行：

```bash
outputs/logos/reconflow-svg/switch_variant.sh apex
```

参数可选 `core`、`apex`、`signal`。脚本会同时切换 Tauri 桌面端图标、
`frontend/src/assets/icon-source.png` 和 Web favicon；替换前会把当前图标备份到
`outputs/logos/reconflow-svg/backups/`。

重新生成全部图标包：

```bash
python3 outputs/logos/reconflow-svg/build_icon_packs.py
```
