# D435 官方模型与导入说明

`d435_official_ros.dae`来自[RealSense官方ROS仓库](https://github.com/realsenseai/realsense-ros/blob/ros2-master/realsense2_description/meshes/d435.dae)，原始时间戳2018-07-03、单位米。源文件保留不变；`d435_official_ros_mm.stl`仅把原始三角形坐标乘1000转为毫米，保持原顺序/绕向，未补洞、平滑、简化或重画。STL不保留DAE材质颜色。

官方较新的SolidWorks模型`D435_Solid.SLDPRT`另行保留；本机FreeCAD无法原生读取该格式，因此没有把ROS显示网格称作精确实体CAD。碰撞及质量仍采用明确标注的保守包络与75g质量，显示网格不重复计质量。

| 检查项 | 结果 |
|---|---:|
| 几何组 | 18 |
| 三角面 | 231186 |
| 边界边 | 80034 |
| 非流形边 | 0 |
| 退化三角面 | 56 |
| 朝向不一致面 | 5 |
| 是否闭合实体网格 | 否 |

装配变换为原毫米坐标`(x,y,z)→(z+100,x,y+19)`，前表面保持X100，相机中心Z19。源包络89.9143×25×25.0547mm。两后安装孔在源`(±22.5,0)`，孔口平面z−25.05，装配后为X74.95、Y±22.5、Z19。当前独立质量/碰撞解析模型为X74.95～100、Y±45.075、Z6.425～31.575mm；官方网格最后端有约0.0047mm局部凸出，此解析模型仍是名义尺寸近似，不能代替精密接触面计算。

2025版D400数据页140、图10-9标注D435/D435i总深26.05mm，与2018显示网格的25.05mm相差1mm。两者不能作为同一精确尺寸使用。当前支架后接触面X73.95，保留两个可拆1mm垫片：25.05mm模型配1mm垫片和M3×6，26.05mm实物移除垫片、换M3×5，两者名义进入深度均2mm。后一配置的解析模型应延伸至X73.95；实物按实际后安装面选择配置。后M3最大进入深度按官方图纸3mm，不能按ROS网格约1.60mm的孔内可见长度推定加工深度。推荐紧固力矩来自同图纸0.4N·m。

网格来源许可证为Apache License 2.0，已保存`LICENSE.realsense-ros`与包级`realsense2_description.package.xml`。转换说明见`NOTICE.conversion.txt`；完整哈希、拓扑检查和后安装面顶点证据见[mesh_inspection.json](mesh_inspection.json)。

可复现：`/Applications/FreeCAD.app/Contents/Resources/bin/python tools/inspect_v6_d435_mesh.py`。整机展示STL包含该官方开放网格时，不应宣称整机STL全部水密；加工件STL需单独验证。
