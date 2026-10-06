# NVIDIA Jetson Orin Nano 官方整套开发套件

原始文件来自[NVIDIA官方下载](https://developer.nvidia.com/downloads/assets/embedded/secure/jetson/orin_nano/docs/jetson_orin_nano_devkit_3d_step_model.zip/)，2026-09-22匿名下载HTTP200。当前[官方下载目录](https://developer.nvidia.com/embedded/downloads.json)标注版本 **20230320**、发布日期2023-03-21；STEP自身时间戳2023-02-03。目录原文及完整SHA256见[provenance.json](provenance.json)。

模型包含P3768 A04载板、P3767模块包络、散热器、风扇、塑料底座及WiFi/NVMe等装配内容。它是厂商发布的完整开发套件机械模型，其中SOM仍是厂商明确标注的组件包络，不是内部热分析/惯量模型；可选NVMe/WiFi内容不一定等于用户实际配置。

| 文件 | 用途 |
|---|---|
| jetson_orin_nano_devkit_3d_step_model.zip | 原始下载包，未改动 |
| P3766-P3768SKU4-P3767ENVELOPE.stp | 原始官方STEP，未改动 |
| jetson_devkit_native.brep | 原始几何原生缓存 |
| jetson_devkit_solids.brep | 保留全部1393个有效实体，去除527个非实体辅助壳；未缩放、重画或替换实体 |
| official_devkit_preview.png | 系统FreeCAD生成的实物几何预览，颜色仅用于辨认组件 |

原始BRep控制包围盒为103.379×91.066×34.905mm；实体缓存的控制包围盒为103.379×91.053×34.905mm。该包围盒最低Z−5.038511包含曲面控制点扩展，**不是底座实际承托面**；实际底面Z−4.9。

源坐标前方连接器朝−Y。建议绕Z轴+90°，再平移(1.663251,−46,37.9)mm，使原底座真实底面恰好接触机身托盘Z33、连接器朝机器人+X。此时实际高度范围Z33～67.766mm，BRep控制包围盒仍会延伸到Z32.861489，不应据此判断穿入托盘；应检查实际实体布尔交叠与面间距离。外部夹条防抬唇下表面Z40，相对原底座最高边缘Z39.5留0.5mm间隙。此修正只改变装配位姿，原厂STEP及两个缓存均未改形。

载板四孔D2.75、孔距86×58mm，但它们已用于原塑料底座装配。底座下方有盲孔/塑料成型细节，不能把载板孔直接当作整套贯通安装孔。保留原底座时采用外围托架/压块，新增M3仅连接托架本身。

可复现检查：`/Applications/FreeCAD.app/Contents/Resources/bin/python tools/inspect_v6_jetson.py --render`。脚本核对原始STEP哈希，保留厂商文件，输出原生缓存与几何来源记录。
