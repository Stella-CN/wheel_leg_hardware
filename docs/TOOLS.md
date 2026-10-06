# 工具分类与运行

所有命令从 `wheel_leg_hardware` 根目录执行。实际参数以对应脚本的 `--help` 或文件头说明为准；构建与打包会写入对应版本目录，应在需要重生成时运行。

| 工具类别 | 脚本 | 输出/作用 |
| --- | --- | --- |
| CAD 建模 | `build_*robot.py`、`cad_*.py` | 历版整机及零件结构 |
| V8.2 电气 | `build_v82_electrical.py`、`finish_v82_electrical.py` | 电气集成及导出 |
| V8.3 外壳 | `build_v83_shell.py` | 当前外壳与装配 |
| 几何、安装审查 | `review_*.py`、`inspect_*.py` | 接口、干涉、安装和版本差异 |
| 质量与负载 | `analyze_*.py` | 质量预算、机构比例、电机负载 |
| 渲染与图示 | `render_*.py`、`draw_*.py` | CAD 预览、接口与走线图 |
| 制造导出 | `export_*.py`、`orient_*.py`、`validate_*meshes.py` | STEP/STL、打印姿态和网格验证 |
| 打包 | `package_*.py` | 历版发布包与哈希 |
| BOM | `build_*bom_data.py`、`build_*bom.mjs` | BOM 数据与采购制造工作簿 |
| 历史电机网格 | `convert_cad_models.py` | 从工程内参考 STEP 转换到 `assets/meshes/` |

查看历史电机转换选项（只需 Python 标准库）：

```bash
python3 tools/convert_cad_models.py --help
```

转换需要 FreeCAD 或其 Gmsh，电机来源读取 `configs/motors.json`，不再导入仿真工程。

FreeCAD 构建脚本沿用 macOS 安装路径，例如：

```bash
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/build_v83_shell.py
```

运行前阅读 [依赖说明](DEPENDENCIES.md)。部分渲染需要 FreeCAD GUI/Qt；不能用普通 Python 代替 FreeCAD Python。BOM `.mjs` 工具使用 Node.js 和 `@oai/artifact-tool`，文件头列出输入输出参数；原脚本从用户目录的 Codex runtime 加载依赖。
