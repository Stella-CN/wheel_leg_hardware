# V8.2 制造与采购清单

一台样机净用量；采购备件比例在工作簿中默认0%。V8.1腿部制造件沿用。本版新增电气安装件并更新两片机壳及电器盘。

|类别|型号数|已定义数量|
|---|---:|---:|
|3D打印件|14|15|
|定制金属件|24|62|
|标准件|19|210|
|厂家目录件|4|64|
|外购设备|13|18|
|外购耗材|4|9|
|待选型附件|5|部分待定|

新增设备质量为工程预算，不能替代称重。布线占位体不计为已采购线缆或实物质量。

## 3D打印件

|编号|名称|单机数量|规格/工艺|
|---|---|---:|---|
|P05|[前主壳](manufacturing/print/P05_chassis_front_shell.step)|1|141.0 × 172.0 × 155.0 mm 包络；详见STEP|
|P06|[后检修壳](manufacturing/print/P06_chassis_rear_cover.step)|1|74.0 × 172.0 × 155.0 mm 包络；详见STEP|
|P07|[屏幕相机前脸板](manufacturing/print/P07_display_front_bezel.step)|1|144.0 × 148.0 × 3.0 mm 包络；详见STEP|
|P08|[左右通用肩罩](manufacturing/print/P08_shoulder_fairing_right.step)|2|106.989 × 38.5 × 51.8 mm 包络；详见STEP|
|P09|[电池托](manufacturing/print/P09_battery_tray.step)|1|153.993 × 54.0 × 14.4 mm 包络；详见STEP|
|P10|[电器托盘](manufacturing/print/P10_electronics_tray.step)|1|152.0 × 108.0 × 3.0 mm 包络；详见STEP|
|P11|[Jetson右夹座](manufacturing/print/P11_Jetson_base_retainer_right.step)|1|125.5 × 22.2 × 9.4 mm 包络；详见STEP|
|P12|[Jetson左夹座](manufacturing/print/P12_Jetson_base_retainer_left.step)|1|125.5 × 22.2 × 9.4 mm 包络；详见STEP|
|P13|[D435一体后座](manufacturing/print/P13_D435_embedded_bracket.step)|1|24.0 × 108.0 × 28.05 mm 包络；详见STEP|
|P15|[屏幕右托夹](manufacturing/print/P15_display_case_cradle_right.step)|1|81.5 × 16.0 × 17.5 mm 包络；详见STEP|
|P16|[屏幕左托夹](manufacturing/print/P16_display_case_cradle_left.step)|1|81.5 × 16.0 × 17.5 mm 包络；详见STEP|
|P30|[配电通信一体安装架](manufacturing/print/P30_electrical_service_carrier.step)|1|59.0 × 110.996 × 70.0 mm 包络；详见STEP|
|P31|[背部USB扩展坞压托](manufacturing/print/P31_USB_hub_rear_clamp.step)|1|12.5 × 104.5 × 13.0 mm 包络；详见STEP|
|P32|[后充电口可换安装板](manufacturing/print/P32_DC_charge_replaceable_plate.step)|1|2.5 × 34.0 × 22.0 mm 包络；详见STEP|

## 定制金属件

|编号|名称|单机数量|规格/工艺|
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

|编号|名称|单机数量|规格/工艺|
|---|---|---:|---|
|LH01|内六角圆柱头螺钉|46|ISO4762 M3×8|
|LH02|内六角圆柱头螺钉|14|ISO4762 M3×16|
|LH06|沉头内六角螺钉|8|DIN7991 M3×10；头≤Ø6×1.7，90°，内六角2|
|LH07|沉头内六角螺钉|12|DIN7991 M3×6；头≤Ø6×1.7，90°，内六角2|
|LH08|沉头内六角螺钉|8|DIN7991 M4×12；头≤Ø8×2.3，90°，内六角2.5|
|LH09|普通平垫圈|8|ISO7089 M4；Ø4.3/Ø9×0.8|
|LH10|六角螺母|8|ISO4032 M4；AF7×3.2|
|LH11|定位圆柱销|6|DIN6325 Ø4m6×10（Norelem03320-04X10）|
|BH01|沉头内六角螺钉|16|DIN7991 M3x0.5 x 8|
|BH03|内六角圆柱头螺钉|10|ISO4762 M3x0.5 x 10|
|BH04|内六角圆柱头螺钉|16|ISO4762 M3x0.5 x 12|
|BH05|内六角圆柱头螺钉|8|ISO4762 M3x0.5 x 20|
|BH06|内六角圆柱头螺钉|2|ISO4762 M2.5x0.45 x 16|
|BH07|六角螺母|26|ISO4032 M3x0.5; AF5.5 x t2.4|
|BH08|六角螺母|6|ISO4032 M2.5x0.45; AF5 x t2|
|BH09|普通平垫圈|4|ISO7089 M3; ID3.2 x OD7 x t0.5|
|EH01|内六角圆柱头螺钉|4|ISO4762 M1.6×10|
|EH02|六角螺母|4|ISO4032 M1.6；AF3.2×1.3|
|EH03|内六角圆柱头螺钉|4|ISO4762 M2.5×12|

## 厂家目录件

|编号|名称|单机数量|规格/工艺|
|---|---|---:|---|
|LH03|低头小头螺钉|20|NBK SLH-M3-6-SD；头Ø4.5×2，内六角2|
|LH04|低头小头螺钉|8|NBK SLH-M3-8-SD；头Ø4.5×2，内六角2|
|LH05|超薄头内六角花形螺钉|30|NBK SETS-M2-4；头Ø4×0.5，TX4|
|LH12|深沟球轴承|6|NSK626ZZ1；6×19×6；金属防尘盖|

## 外购设备

|编号|名称|单机数量|规格/工艺|
|---|---|---:|---|
|E01|J4310关节电机|4|DM-J4310-2EC，24V，V1.1驱动|
|E02|轮毂电机|2|DM-H6215|
|E03|开发套件|1|Jetson Orin Nano官方开发套件|
|E04|深度相机|1|RealSense D435|
|E05|惯性测量单元|1|超核HI13R2 USB版|
|E06|5寸显示器|1|GK-HD V3，122×78×14.5 mm|
|E07|E626S电池包及磁吸底座|1|用户确认24V等级E626S；本体85.6×61.6×42 mm，含磁底44.5 mm|
|E08|弹性轮胎|2|外径100/内径86/宽32 mm|
|E09|顶部自锁电源开关及插接座|1|M16×1，法兰Ø17.8，AF19螺母；带插接座深47.5 mm|
|E10|背部四口USB扩展坞|1|104×30×10 mm；一体USB-A上行线150 mm，线径约4.8 mm|
|E11|达妙双路USB2CANFD裸板|1|DM-USB2CANFD Dual；使用提供模型中的裸板|
|E12|用户配电转接板|1|3D_PCB1_2026-09-28.step 对应板组件|
|E13|24→19 V电源转换模块|1|主体45×25×20 mm；总长58 mm；孔距51 mm，孔Ø4 mm|

## 外购耗材

|编号|名称|单机数量|规格/工艺|
|---|---|---:|---|
|C01|屏幕后软垫|4|4×8×0.5 mm，4块|
|C02|电池束带|2|10×300 mm；底部单层厚≤1.0 mm|
|C03|扩展坞防响软垫|2|2×15×0.5 mm；两片，0.5为装配间隙目标|
|C04|USB3数据延长线|1|USB-A公→USB-A母；250 mm|

## 待选型附件

|编号|名称|单机数量|规格/工艺|
|---|---|---:|---|
|T01|电源保护与主回路分断器件|待定|依电气额定值选型，不能由AC开关标称替代|
|T02|后部充电DC母座|1|插合DC5.5×2.1；面板安装孔/螺纹/载流待确定|
|T03|线束、插头与绝缘护线件|待定|待电气方案与实物确认|
|T04|螺纹防松与标记耗材|待定|待电气方案与实物确认|
|T05|机壳及托盘护线套|3|适用Ø10面板孔、3mm板厚；净孔≥7mm|

## 制造分工与装配

- 主承力杆、法兰、机架、轮辋与刚性IMU桥仍用金属加工；腿部销套及精密薄片沿用已审查V8.1工艺。
- 电气安装架、扩展坞压托和充电接口板可PETG打印；安装架应力、转换器温升及打印孔公差需首件验收。
- 前主壳增加顶部开关安装；后壳增加扩展坞窗口/托架与可换DC接口板；电器盘增加模块安装孔。使用本版更新导出，不从baseline_v81取旧件生产。
- DC接口板导孔不能直接作为母座最终安装孔；主开关DC能力、转换器功率、分配板网络未确认，见ELECTRICAL_INTEGRATION.md。
- 新增模块先在机外组装，再与电子盘/后盖装配；具体螺钉位置按装配体和模块说明。
