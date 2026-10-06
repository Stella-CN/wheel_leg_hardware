# V8.1 制造与采购分类清单

数量按一台样机净用量。制造目录中的共用件只保留一份几何，按BOM数量制造，勿重复计算左右装配导出。

|类别|型号数|件数|
|---|---:|---:|
|3D打印件|11|12|
|定制金属件|24|62|
|标准件|16|174|
|厂家目录件|4|64|
|外购设备|8|13|
|外购耗材|2|6|
|待选型附件|4|待定|

电池按用户确认的24V等级E626S及新图纸；接口核对见BATTERY_SOURCE_REVIEW.md。未知附件数量不伪记为零。

## 3D打印件

|编号|零件|数量|规格/工艺|
|---|---|---:|---|
|P05|[前主壳](manufacturing/print/P05_chassis_front_shell.step)|1|155.0 × 172.0 × 141.0 mm 包络；详见STEP|
|P06|[后检修壳](manufacturing/print/P06_chassis_rear_cover.step)|1|155.0 × 172.0 × 74.0 mm 包络；详见STEP|
|P07|[屏幕相机前脸板](manufacturing/print/P07_display_front_bezel.step)|1|144.0 × 148.0 × 3.0 mm 包络；详见STEP|
|P08|[左右通用肩罩](manufacturing/print/P08_shoulder_fairing_right.step)|2|106.989 × 38.5 × 51.8 mm 包络；详见STEP|
|P09|[电池托](manufacturing/print/P09_battery_tray.step)|1|153.993 × 54.0 × 14.4 mm 包络；详见STEP|
|P10|[电器托盘](manufacturing/print/P10_electronics_tray.step)|1|152.0 × 108.0 × 3.0 mm 包络；详见STEP|
|P11|[Jetson右夹座](manufacturing/print/P11_Jetson_base_retainer_right.step)|1|125.5 × 22.2 × 9.4 mm 包络；详见STEP|
|P12|[Jetson左夹座](manufacturing/print/P12_Jetson_base_retainer_left.step)|1|125.5 × 22.2 × 9.4 mm 包络；详见STEP|
|P13|[D435一体后座](manufacturing/print/P13_D435_embedded_bracket.step)|1|24.0 × 108.0 × 28.05 mm 包络；详见STEP|
|P15|[屏幕右托夹](manufacturing/print/P15_display_case_cradle_right.step)|1|81.5 × 16.0 × 17.5 mm 包络；详见STEP|
|P16|[屏幕左托夹](manufacturing/print/P16_display_case_cradle_left.step)|1|81.5 × 16.0 × 17.5 mm 包络；详见STEP|

## 定制金属件

|编号|零件|数量|规格/工艺|
|---|---|---:|---|
|P01|[机架底板](manufacturing/metal/P01_chassis_belly_plate.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P02|[右承力侧框](manufacturing/metal/P02_chassis_hip_frame_right.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P03|[左承力侧框](manufacturing/metal/P03_chassis_hip_frame_left.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P04|[前后通用横框](manufacturing/metal/P04_chassis_front_crossframe.step)|2|CNC铣削/车铣；6061-T6铝合金|
|P14|[IMU刚性安装桥](manufacturing/metal/P14_HI13R2_rigid_bridge.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P17|[左右通用髋定子座](manufacturing/metal/P17_hip_stator_mount.step)|2|CNC铣削/车铣；6061-T6铝合金|
|P18|[左右通用髋转子法兰](manufacturing/metal/P18_hip_rotor_cnc.step)|2|CNC铣削/车铣；6061-T6铝合金|
|P19|[右膝定子套杯](manufacturing/metal/P19_knee_stator_cnc.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P20|[左膝定子套杯](manufacturing/metal/P20_knee_stator_cnc_left.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P21|[右OB内框](manufacturing/metal/P21_OB_inner_carrier.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P22|[左OB内框](manufacturing/metal/P22_OB_inner_carrier_left.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P23|[右OB外包主臂](manufacturing/metal/P23_OB_outer_shell.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P24|[左OB外包主臂](manufacturing/metal/P24_OB_outer_shell_left.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P25|[左右通用OA曲柄](manufacturing/metal/P25_OA_one_piece.step)|2|CNC铣削/车铣；6061-T6铝合金|
|P26|[左右通用AC轴承连杆](manufacturing/metal/P26_AC_bearing_link.step)|2|CNC铣削/车铣；6061-T6铝合金|
|P27|[右CW下臂](manufacturing/metal/P27_CW_one_piece.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P28|[左CW下臂](manufacturing/metal/P28_CW_one_piece_left.step)|1|CNC铣削/车铣；6061-T6铝合金|
|P29|[通用轮辋](manufacturing/metal/P29_wheel_rim.step)|2|CNC铣削/车铣；6061-T6铝合金|
|LC01|[轴承外圈压盖](manufacturing/metal/LC01_bearing_keeper_D28_D16_8_t0_8.step)|6|精密薄板切割/整平；不锈钢板|
|LC02|[双端内螺纹关节轴销](manufacturing/metal/LC02_female_pin_D6_L14_05.step)|6|CNC车削/精磨/二次加工；40Cr调质后精磨；具体硬度按试验定|
|LC03|[内侧一体带肩衬套](manufacturing/metal/LC03_flanged_bush_inner_D8_D8p4_L3p75.step)|6|CNC车削/精磨/二次加工；轴承青铜CuSn12|
|LC04|[外侧一体带肩衬套](manufacturing/metal/LC04_flanged_bush_outer_D8_D8p4_L4p20.step)|6|CNC车削/精磨/二次加工；轴承青铜CuSn12|
|LC05|[轴销薄防脱挡片](manufacturing/metal/LC05_axis_washer_D9_d2_2_t0_2.step)|12|精密薄板切割/整平；钢精密垫片料|
|LC06|[OA装配限位肩销](manufacturing/metal/LC06_OA_angular_stop_M3_D4.step)|2|CNC车削/精磨/二次加工；钢；强度待验证|

## 标准件

|编号|零件|数量|规格/工艺|
|---|---|---:|---|
|LH01|内六角圆柱头螺钉|44|ISO4762 M3×8|
|LH02|内六角圆柱头螺钉|12|ISO4762 M3×16|
|LH06|沉头内六角螺钉|8|DIN7991 M3×10；头≤Ø6×1.7，90°，内六角2|
|LH07|沉头内六角螺钉|12|DIN7991 M3×6；头≤Ø6×1.7，90°，内六角2|
|LH08|沉头内六角螺钉|8|DIN7991 M4×12；头≤Ø8×2.3，90°，内六角2.5|
|LH09|普通平垫圈|8|ISO7089 M4；Ø4.3/Ø9×0.8|
|LH10|六角螺母|8|ISO4032 M4；AF7×3.2|
|LH11|定位圆柱销|6|DIN6325 Ø4m6×10（Norelem03320-04X10）|
|BH01|沉头内六角螺钉|16|DIN7991 M3x0.5 x 8|
|BH03|内六角圆柱头螺钉|8|ISO4762 M3x0.5 x 10|
|BH04|内六角圆柱头螺钉|12|ISO4762 M3x0.5 x 12|
|BH05|内六角圆柱头螺钉|8|ISO4762 M3x0.5 x 20|
|BH06|内六角圆柱头螺钉|2|ISO4762 M2.5x0.45 x 16|
|BH07|六角螺母|16|ISO4032 M3x0.5; AF5.5 x t2.4|
|BH08|六角螺母|2|ISO4032 M2.5x0.45; AF5 x t2|
|BH09|普通平垫圈|4|ISO7089 M3; ID3.2 x OD7 x t0.5|

## 厂家目录件

|编号|零件|数量|规格/工艺|
|---|---|---:|---|
|LH03|低头小头螺钉|20|NBK SLH-M3-6-SD；头Ø4.5×2，内六角2|
|LH04|低头小头螺钉|8|NBK SLH-M3-8-SD；头Ø4.5×2，内六角2|
|LH05|超薄头内六角花形螺钉|30|NBK SETS-M2-4；头Ø4×0.5，TX4|
|LH12|深沟球轴承|6|NSK626ZZ1；6×19×6；金属防尘盖|

## 外购设备

|编号|零件|数量|规格/工艺|
|---|---|---:|---|
|E01|J4310关节电机|4|DM-J4310-2EC，24V，V1.1驱动|
|E02|轮毂电机|2|DM-H6215|
|E03|开发套件|1|Jetson Orin Nano官方开发套件|
|E04|深度相机|1|RealSense D435|
|E05|惯性测量单元|1|超核HI13R2 USB版|
|E06|5寸显示器|1|GK-HD V3，122×78×14.5 mm|
|E07|E626S电池包及磁吸底座|1|用户确认24V等级E626S；本体85.6×61.6×42 mm，含磁底44.5 mm|
|E08|弹性轮胎|2|外径100/内径86/宽32 mm|

## 外购耗材

|编号|零件|数量|规格/工艺|
|---|---|---:|---|
|C01|屏幕后软垫|4|4×8×0.5 mm，4块|
|C02|电池束带|2|10×300 mm；底部单层厚≤1.0 mm|

## 待选型附件

|编号|零件|数量|规格/工艺|
|---|---|---:|---|
|T01|电源转换与配电|待定|待电气方案与实物确认|
|T02|保险丝、开关与急停|待定|待电气方案与实物确认|
|T03|线束、插头与绝缘护线件|待定|待电气方案与实物确认|
|T04|螺纹防松与标记耗材|待定|待电气方案与实物确认|

## 加工分工

- 承力杆、法兰、髋座、轮辋、机架和IMU桥使用6061-T6 CNC。轴承台阶、薄叉耳及包夹结构不能用普通板件下料直接代替。
- LC02轴销、LC03/LC04青铜带肩套、LC06限位肩销采用车削、精磨/钻攻及必要的二次铣削。
- LC01压盖和LC05薄防脱片适合精密薄板切割、去毛刺和整平；LC05仅0.20mm，需确认工艺能力。
- PETG文件已摆正并校核220×220×250mm包络；先做孔槽试片，壳体及托盘局部需可拆支撑。新电池托仍1件，保留4颗M3×8及2条束带。
- D435的26.05mm深备选后座位于alternates，只替换默认件，不增加单机数量。

配合见[腿部公差](LEG_FITS.md)、[机身细节](BODY_ASSEMBLY.md)和[电池安装](BATTERY.md)。装配顺序见[模块总装](MODULE_ASSEMBLY.md)。STEP单位mm，螺纹主要以底孔表达，必须按书面规格完成钻攻。
