# wheel_leg_hardware — 轮腿机器人硬件工程

本工程保存完整机器人机械与电气结构、CAD 源文件、加工/打印文件、采购制造 BOM、装配说明、验证记录和生成工具。2026-10-06 从 `wheel_leg_mujoco` 拆分；保留各阶段最终交付与必要来源，过程临时文件已清理。

## 获取仓库

本仓库使用 Git LFS 保存大于等于 10 MiB 的现有 CAD、制造包等文件，并通过 Git 子模块固定两个电机资料库的版本。请先安装 Git 和 Git LFS，再执行：

```bash
git lfs install
git clone --recurse-submodules https://github.com/Stella-CN/wheel_leg_hardware.git
cd wheel_leg_hardware
git lfs pull
```

已有克隆可运行 `git submodule update --init --recursive` 补齐电机资料。子模块来自 Gitee，需要能够访问对应服务。完整工程包含数 GiB 数据；建议按上述方式克隆，以取得 LFS 实体文件和子模块内容。

查看设计从下方 V8.3 整机 CAD、打印试装包和装配说明开始。编辑 `.FCStd` 使用 FreeCAD；STEP/STL 用于几何交换与制造准备。生成工具还涉及 Python、FreeCAD Python API 和 Node.js，具体依赖见 [依赖说明](docs/DEPENDENCIES.md)。

## 当前工作入口

| 内容 | 入口 | 用途 |
| --- | --- | --- |
| V8.3 整机 CAD | [wheel_leg_v8_3.FCStd](mechanical/v8_3/wheel_leg_v8_3.FCStd) | 当前外壳与整机结构 |
| V8.3 变化记录 | [DESIGN_CHANGES.md](mechanical/v8_3/DESIGN_CHANGES.md) | 外观与分件变更 |
| V8.3 打印试装包 | [README](mechanical/v8_3_print_trial/README.md) | 打印清单、标准件采购及试装注意事项 |
| 整机装配 | [MODULE_ASSEMBLY.md](mechanical/v8_3/MODULE_ASSEMBLY.md) | 模块预装及总装 |
| 电气集成 | [ELECTRICAL_INTEGRATION.md](mechanical/v8_3/ELECTRICAL_INTEGRATION.md) | 电气设备安装与接口 |
| 关节配合 | [LEG_FITS.md](mechanical/v8_3/LEG_FITS.md) | 腿部装配配合 |
| 硬件 BOM 数据 | [bom_master.json](mechanical/v8_3/bom_master.json) | 结构化采购与制造数据 |
| V8.2 电气基线 | [mechanical/v8_2](mechanical/v8_2/) | 电气布置、走线、集成审查与 BOM |

V8.3 试装包包含原金属件的塑料试装版本，使用边界以包内说明为准；不是承载行走的最终制造包。版本号表示设计演进，不代表所有版本通过相同验证。

## 目录与版本

```text
wheel_leg_hardware/
├── mechanical/
│   ├── v1/ … v8/            # 历代设计、CAD、制造文件及验证记录
│   ├── v8_1/                # 模块化/电池集成基线
│   ├── v8_2/                # 电气集成基线
│   ├── v8_3/                # 当前外壳设计与整机 CAD
│   ├── v8_3_print_trial/    # 全定制件打印试装包
│   └── *.zip / *.sha256     # 原始历版发布包及校验文件
├── tools/                   # 95 个 CAD、审查、渲染、制造、BOM 工具
├── references/              # 已收拢的电机、板卡、用户图纸和外观参考
├── configs/motors.json      # 拆分时的电机资料参数和历史 CAD 来源
├── assets/meshes/           # 旧电机 STEP 转换网格，非当前仿真依赖
└── docs/                    # 工具/依赖说明及拆分校验清单
```

保留 `mechanical/<版本>` 和 `tools/` 的相对层级，使既有构建、版本继承与打包脚本继续按工程根目录定位。历版发布包、CAD、BOM、数值审查报告及其哈希未重写；活动工具路径及 Markdown 手册链接已适配本地资料；报告里的原绝对路径属于历史来源记录。运行工具请使用根目录 `tools/`，各版本 `source/` 中的脚本属于当时的来源快照。

各阶段最终预览、装配图和最终报告引用的证据属于交付内容，予以保留；临时工作区、自动备份、日志、迭代诊断及重复 BOM 输出已删除。正式 BOM 位于对应版本目录。

## 使用与依赖

- [工具分类与运行说明](docs/TOOLS.md)
- [资料依赖和验证范围](docs/DEPENDENCIES.md)
- [迁移前逐文件 SHA-256 清单](docs/migration_manifest.json)
- [过程文件清理记录](docs/cleanup_manifest.json)
- [拆分后的校验结果](docs/split_validation.json)

MuJoCo 仿真继续位于 [wheel_leg_simulation](https://github.com/Stella-CN/wheel_leg_simulation)。两个工程没有 Python 导入依赖或运行时目录链接。仿真尺寸、质量、惯量和控制参数保持独立快照；硬件修改后需另行评估并同步仿真参数，不应直接用制造 CAD 替换仿真碰撞/惯量模型。
