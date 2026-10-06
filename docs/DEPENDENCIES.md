# 依赖与验证范围

## 已收拢的资料

| 工程内位置 | 处理方式 |
| --- | --- |
| `references/DM-J4310-2EC/`、`references/DM-H6215/` | 从同级共享资料目录复制；仿真仍引用原资料来源，原目录保留 |
| `references/dm-tools/USB2CANFD_Dual/` | 从同级共享资料目录移动 |
| `references/user_supplied/3D_PCB1_2026-09-28.step` | 从 Downloads 移动 |
| `references/user_supplied/wheel_leg.png`、`wheel_leg_front.png` | 从 Downloads 移动 |
| `references/user_supplied/*user_drawing.png` | 临时剪贴板原图已不存在，从已保存的版本来源副本恢复 |

逐文件来源、目标、复制/移动方式和 SHA-256 见 [dependency_migration.json](dependency_migration.json)。当前 `tools/` 和 `configs/motors.json` 使用工程内相对路径；不读取原 Downloads、共享 references 或系统剪贴板目录。仿真不需要导入硬件工程。

## 无法恢复的历史输入

`/tmp/v82_validated_pre_routes.FCStd` 已不存在。遍历现有 CAD、FCBak 及发布 ZIP 内 CAD 后，未找到符合原报告 SHA-256 的文件：

```text
d35408105a0689bd59c183aedc95a6e91b170502f41906df2e71bff9944febaa
```

`tools/review_v82_final_delta.py` 因此不能重跑完整历史差异审查；如找回原文件，应放到 `references/audit_baselines/v82_validated_pre_routes.FCStd`。不使用当前 CAD 冒充原基线。检索记录见 [baseline_recovery.json](baseline_recovery.json)。

`/tmp/v82_hub_clamp_before_clearance.brep` 原文件也已不存在，但 `mechanical/v8_2/source/validation_before_cut_USB_hub_rear_clamp.brep` 和另两件切削前几何仍在，`review_v82_final_cuts.py` 优先读取这些已保存几何。仅当它们缺失、需要重新提取时，才需要上述完整基线和 `references/audit_baselines/v82_hub_clamp_before_clearance.brep`。

## 软件环境

按用户要求，软件保留原安装位置，不搬移或打包系统运行库：

- CAD：`/Applications/FreeCAD.app/Contents/Resources/bin/python`，以及 `Part`、`Mesh`、`MeshPart`。
- 渲染：FreeCAD GUI、Qt/PySide 和本机图形环境。
- 普通分析：Python 3；部分图表工具使用 NumPy、Matplotlib，按脚本导入配置。
- BOM：Node.js、`@oai/artifact-tool`；原工具使用 `~/.cache/codex-runtimes/codex-primary-runtime/dependencies`。工具重跑时会在临时工作目录链接该公共运行库，原临时目录已清理。
- 硬件工程不依赖 MuJoCo、仿真 `.venv` 或 `wheel_leg` 包。

## 清理策略

已删除 `tmp/`、`mechanical/workbench/`、字节码缓存、FreeCAD 自动备份、过程日志、工作簿中间检查以及未被最终报告使用的迭代诊断。`outputs/` 两份 BOM 与对应版本正式工作簿逐字节一致，因此删除重复输出。清单及删除前哈希见 [cleanup_manifest.json](cleanup_manifest.json)。最终预览、报告直接引用的证据和工具必需的基线保留。

## 历史记录与验证边界

原发布 ZIP、各阶段最终 CAD、BOM 数据、源脚本快照及最终数值审查结果保持不变；活动工具的本地资料路径和部分 Markdown 手册链接已更新。历史来源记录中的绝对路径保留用于追溯。版本 `source/` 中的脚本及 ZIP 是原始快照，不是本次适配后的运行入口。

旧打包工具中针对源代码哈希的冻结检查可能因本次路径修改而拒绝重新发布旧版本。这是正确的审计行为；没有修改旧验证报告来绕过检查。重新构建和发布应重新验证并生成新的版本证据。

拆分验证涵盖逐文件 SHA-256、链接目标、仿真原有 21 项测试、单腿/双腿模型检查、三份 MJCF 加载、硬件活动脚本语法及转换器本地来源解析。结果见 [split_validation.json](split_validation.json)。没有重生成各版 CAD、制造包或工作簿；这次文件拆分不构成新的结构强度、电气或实物装配验证。
