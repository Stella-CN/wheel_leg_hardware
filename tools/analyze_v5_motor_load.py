"""CAD mass budget and transparent first-pass motor sizing for the V5 robot.

Run with FreeCAD's Python after building V5. This is a concentrated-mass,
quasi-static calculation, not a replacement for multibody or impact testing.
The optional --plot-only mode runs with any Python providing matplotlib.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'mechanical/v5'
G, L, CRANK, WHEEL_R = 9.81, .130, .035, .050


def mass_budget():
    sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
    import FreeCAD as App
    import Part  # noqa: F401
    doc = App.openDocument(str(OUT/'wheel_leg_v5.FCStd'))
    rows = []
    for obj in doc.Objects:
        if obj.TypeId!='Part::Feature':
            continue
        mat = getattr(obj,'Material','')
        if mat=='motor':
            mass = 360 if 'H6215' in obj.Name else 300
            method = 'manufacturer approximate mass'
        elif mat=='payload':
            mass = obj.BudgetMassGrams
            method = obj.ManufacturingNote
        else:
            density = {'CNC':.0027, 'PETG':.00127, 'rubber':.0011, 'steel':.00785}.get(mat)
            if density is None:
                raise ValueError(f'Unbudgeted material {mat}: {obj.Name}')
            if 'bronze' in obj.Name:
                density = .0088
            mass = obj.Shape.Volume*density
            method = f'CAD volume x {density} g/mm3; nominal solid envelope'
        solids = obj.Shape.Solids
        volume = sum(s.Volume for s in solids)
        if volume <= 0:
            raise ValueError(f'Non-solid mass item: {obj.Name}')
        center = sum((s.CenterOfMass*s.Volume for s in solids), App.Vector())/volume
        local_center = obj.Placement.inverse().multVec(center)
        rows.append(dict(part=obj.Name, material=mat, mass_g=round(mass,3),
                         center_mm=[center.x,center.y,center.z],
                         local_center_mm=[local_center.x,local_center.y,local_center.z],
                         role=obj.KinematicRole, method=method))
    # Explicit allowance, separate from the devices and modelled hardware.
    # Missing screw thread segments, wiring, converters, straps and actual
    # electronic mounting hardware are not silently assumed massless.
    rows.append(dict(part='unmodelled_installation_allowance', material='allowance',
                     mass_g=200., center_mm=[0,0,5],
                     local_center_mm=[0,0,5], role='fixed',
                     method='engineering allowance: cables, DC/DC, connectors, retainers and unmodelled fasteners; range100..300g'))
    total = sum(r['mass_g'] for r in rows)/1000
    by_material = {}
    for row in rows:
        by_material[row['material']] = by_material.get(row['material'],0)+row['mass_g']/1000
    center = [sum(r['mass_g']*r['center_mm'][i] for r in rows)/(total*1000) for i in range(3)]
    return dict(total_kg=total, indicative_range_kg=[total-.2,total+.3],
                range_method='installation/device/tyre/printing uncertainty allowance; not statistical confidence',
                by_material_kg=by_material, nominal_center_from_hip_mm=center, parts=rows,
                notes=['PETG treated as full CAD solid, not a slicer mass prediction.',
                       'Steel bearing envelopes omit internal race/ball voids and are conservative mass approximations.',
                       'All six motor masses come from the supplied manuals; motor CAD volume is not used as solid steel.'])


def distributed_gravity(budget, lengths=None):
    """Virtual work with CAD centres, fixed chassis pitch and ground-held wheels.

    The common left/right coordinate perturbation divides work by two drives.
    This resolves link self-weight and unsprung mass, but does not establish
    balance, motor internal mass centres, inertia, friction or thermal duty.
    """
    def potential(qh, qk):
        qa=qh+qk; qo=qa+math.pi
        za=-CRANK*math.cos(qa); zb=-L*math.cos(qh)
        zw=zb-L*math.cos(qo)
        total=0.
        for row in budget['parts']:
            x,_,z=[v/1000 for v in row['local_center_mm']]
            role=row['role']
            if role=='fixed':
                zr=z
            else:
                angle={'hip':qh,'oa':qa,'ac':qh,'output':qo,'wheel':qo}[role]
                zr=x*math.sin(angle)+z*math.cos(angle)
                zr+={'hip':0.,'oa':0.,'ac':za,'output':zb,'wheel':zw}[role]
            total+=row['mass_g']/1000*G*(zr-zw)
        return total
    rows=[]
    for length in lengths or (.120,.160,math.sqrt(2)*L,.200,.225):
        a=math.acos(length/(2*L));q=[-a,2*a-math.pi];values=[];convergence=[]
        for j in (0,1):
            derivatives=[]
            for eps in (1e-5,1e-6):
                plus=q.copy();minus=q.copy();plus[j]+=eps;minus[j]-=eps
                derivatives.append((potential(*plus)-potential(*minus))/(4*eps))
            values.append(derivatives[-1]);convergence.append(abs(derivatives[0]-derivatives[1]))
        rows.append(dict(leg_length_mm=length*1000,hip_gravity_Nm=values[0],
                    knee_gravity_Nm=values[1],knee_magnitude_Nm=abs(values[1]),
                    finite_difference_convergence_Nm=max(convergence)))
    return dict(method='CAD distributed gravity virtual work, symmetric coordinates, fixed chassis pitch, wheel centres held at floor height',
                rows=rows, limitations='CAD motor uniform-volume centres approximate actual internal mass; balanced posture and thermal endurance are not established')


def jacobian(length):
    c = length/(2*L)
    s = math.sqrt(1-c*c)
    return ((length,0.), (length/2,L*s))


def check_jacobian():
    def forward(qh,qk):
        return (L*(math.sin(qh)-math.sin(qh+qk)),
                L*(-math.cos(qh)+math.cos(qh+qk)))
    errors=[]
    eps=1e-6
    for length in (.120,.160,math.sqrt(2)*L,.200,.225):
        alpha=math.acos(length/(2*L)); q=[-alpha,2*alpha-math.pi]
        for j,target in enumerate(jacobian(length)):
            plus=q.copy();minus=q.copy();plus[j]+=eps;minus[j]-=eps
            a,b=forward(*plus),forward(*minus)
            errors.extend(abs((a[i]-b[i])/(2*eps)-target[i]) for i in (0,1))
    assert max(errors)<1e-8
    return max(errors)


def analyze(mass):
    standing=[]
    for length in (.120,.160,math.sqrt(2)*L,.200,.225):
        arm=jacobian(length)[1][1]
        torque=mass*G/2*arm
        standing.append(dict(leg_length_mm=length*1000, knee_torque_Nm=torque,
            continuous_torque_utilization=torque/3,
            knee_with_25_percent_design_allowance_Nm=1.25*torque,
            total_mass_at_3Nm_kg=6/(G*arm),
            peak_vertical_force_multiple=14/(mass*G*arm)))
    drives=[]
    length=math.sqrt(2)*L
    for acceleration in (0.,.5,1.):
        # Flat ground sizing with a stated rolling-resistance allowance.
        fx=mass*(acceleration+.02*G)/2
        fz=mass*G/2
        wheel=fx*WHEEL_R
        drives.append(dict(acceleration_m_s2=acceleration, assumed_Crr=.02,
            hip_absolute_envelope_Nm=length*abs(fx)+abs(wheel),
            knee_absolute_envelope_Nm=length/2*abs(fx)+jacobian(length)[1][1]*fz+abs(wheel),
            wheel_torque_Nm=wheel,
            note='absolute-sum screening includes wheel housing reaction; omits wheel angular inertia and detailed link inertias'))
    slopes=[]
    for angle in (5,10,15):
        t=math.radians(angle)
        slopes.append(dict(slope_deg=angle,
             wheel_torque_Nm=mass*G*WHEEL_R/2*(math.sin(t)+.02*math.cos(t)),
             assumed_min_traction_coefficient=math.tan(t)+.02))
    landings=[]
    for height in (.05,.10,.20):
        for stroke in (.03,.05,.08):
            n=1+height/stroke
            end_length=.225-stroke
            fz=mass*G*n/2
            alpha=math.acos(end_length/(2*L))
            tendon=fz*L/(2*CRANK*math.cos(alpha))
            bforce=math.hypot(tendon*math.sin(alpha),tendon*math.cos(alpha)+fz)
            landings.append(dict(drop_height_m=height, stopping_stroke_m=stroke,
                displacement_average_force_multiple=n, end_leg_length_mm=end_length*1000,
                knee_torque_at_average_force_Nm=fz*L*math.sin(alpha),
                AC_force_at_average_N=tendon, B_reaction_at_average_N=bforce,
                C0r_over_B_average=885/bforce,
                note='displacement-average force times end-stroke lever arm; neither peak nor time-average torque; excludes link inertia, skew landing and compliance'))
    angular_stroke=2*(math.acos(.120/(2*L))-math.acos(.225/(2*L)))
    return dict(model='symmetric beta=0 concentrated-mass quasi-static screening',
        motor_specs=dict(J4310=dict(voltage_V=24,version='V1.1, confirmed by user',rated_Nm=3,peak_Nm=7,rated_rpm=120,no_load_rpm=200),
                         H6215=dict(rated_Nm=1,peak_Nm=2,rated_rpm=120,no_load_rpm=320)),
        standing=standing, flat_driving=drives, wheel_climbing=slopes, landing_scenarios=landings,
        takeoff_speed_scenarios=[dict(height_m=h, takeoff_leg_length_mm=225,
             vertical_speed_m_s=math.sqrt(2*G*h),
             knee_relative_rpm=math.sqrt(2*G*h)/jacobian(.225)[1][1]*60/(2*math.pi),
             hip_rpm=math.sqrt(2*G*h)/jacobian(.225)[1][1]*30/(2*math.pi))
             for h in (.05,.10,.20)],
        wheel_rated_speed_m_s=120*2*math.pi/60*WHEEL_R,
        wheel_no_load_speed_m_s=320*2*math.pi/60*WHEEL_R,
        ideal_constant_peak_work_J=2*7*angular_stroke,
        ideal_peak_energy_height_upper_m=max(0,2*7*angular_stroke/(mass*G)-.105),
        jacobian_finite_difference_max_error=check_jacobian(),
        equations=dict(alpha='acos(ell/(2L))',qhip='-alpha',qknee='2alpha-pi',
            J_columns='Jhip=(ell,0); Jknee=(ell/2,L sin(alpha))',
            actuator_effort='tau=-J^T F minus external wheel housing couple; absolute sums used for driving envelope',
            vertical_tendon_force='|T_AC|=Fz L/(2r cos(alpha))',
            B_reaction='sqrt((T sin(alpha))^2+(T cos(alpha)+Fz)^2)',
            landing_average='F_total_displacement_average=Mg(1+h/s)',
            knee_speed='abs(qdot_knee)=abs(ell_dot)/(L sin(alpha)); beta=0'),
        limitations=['No 7Nm full-speed assumption: the supplied 24V test image is near120rpm over0..4.5Nm, not a complete peak torque-speed envelope.',
             'Peak holding duration, drive current, battery voltage sag and thermal model are not established.',
             'Unsprung mass and distributed link gravity are approximated by total mass; balance and transient demands need multibody validation.',
             'No allowance was inferred from the motor gear ratio; published torque already refers to the output.',
             'C0r is a catalog static rating, not permissible shock load or a whole-joint safety certificate.'])


def write_markdown(budget, result):
    m=budget['total_kg'];nom=result['standing'][2];low=result['standing'][0]
    distributed=result['distributed_gravity']['rows']
    lines=['# V5 质量预算与电机负载初算','',
      f'CAD 与设备资料合计约 **{m:.2f} kg**；工程估计范围 {budget["indicative_range_kg"][0]:.2f}～{budget["indicative_range_kg"][1]:.2f} kg。质量区间不是统计置信区间。', '',
      '用户已确认采用 **J4310 24V、V1.1版本驱动**。采用实际130/35mm四杆和50mm轮半径；4310输出轴额定3、峰值7 N·m，额定120rpm、空载200rpm；H6215额定1、峰值2 N·m。不能再乘10:1减速比。本报告不采用48V型号的400rpm数据。', '',
      f'**平地低速运行具备初算可行性，跳跃能力尚不能确认。** 按CAD分布质量，183.85mm姿态每侧膝重力负载约 **{distributed[2]["knee_magnitude_Nm"]:.2f} N·m**，120mm低蹲约 **{distributed[0]["knee_magnitude_Nm"]:.2f} N·m**，均低于3N·m额定值，但低蹲控制余量较小。', '',
      f'另保留较粗的全质量集中筛查：标称姿态 **{nom["knee_torque_Nm"]:.2f} N·m**，低蹲 **{low["knee_torque_Nm"]:.2f} N·m**。两列差异主要来自轮端非簧载质量和连杆分布重力，不能将简化列超过额定直接等同于实机必然失效。', '',
      '首轮调试建议腿长约200mm、平地低速、加速度≤0.5m/s²，测实际电流与温升后再扩展范围；这是基于本次计算的调试起点，不是已验证控制限值。连续低蹲、快速平衡动作及跳跃需要额外余量。', '',
      '## 质量组成','', '| 类别 | kg |','|---|---:|']
    lines += [f'| {k} | {v:.3f} |' for k,v in budget['by_material_kg'].items()]
    lines += ['', '四台4310共1.20kg，两台H6215共0.72kg；Orin套件175g、D435按较新2025资料75g、电池400g、IMU暂20g。另留200g给线束、电源转换、接头、未建模紧固件及固定附件。PETG按实体体积计，实际切片和实称应替换预算。','',
      '## 站立和伸缩','', '| 腿长 mm | 膝转矩 N·m/侧 | 加25%余量 | 3N·m对应整机质量 kg |','|---:|---:|---:|---:|']
    lines += [f'| {r["leg_length_mm"]:.2f} | {r["knee_torque_Nm"]:.2f} | {r["knee_with_25_percent_design_allowance_Nm"]:.2f} | {r["total_mass_at_3Nm_kg"]:.2f} |' for r in result['standing']]
    lines += ['', '### 按CAD分布质量复核','',
      '进一步把每件实体重心、机构运动归属和轮端质量分别计入重力势能，固定机身俯仰，轮心保持地面高度；左右电机虚功均分。电机总质量采用原厂值，电机内部重心用STEP均匀体积重心近似。该列比全质量集中更贴近当前几何，但仍不包含平衡控制和动态惯量。','',
      '| 腿长 mm | 髋重力转矩绝对值 N·m/侧 | 膝重力转矩绝对值 N·m/侧 |','|---:|---:|---:|']
    lines += [f'| {r["leg_length_mm"]:.2f} | {abs(r["hip_gravity_Nm"]):.3f} | {r["knee_magnitude_Nm"]:.3f} |' for r in result['distributed_gravity']['rows']]
    lines += ['', '第一张表采用全质量集中等效；第二张CAD表已计入连杆分布重力与轮端非簧载质量，两表均未计转动惯量。只有重心对中、纯竖直的集中模型才给出髋支承力矩0；CAD分布自重、前后重心偏置、行驶反力矩和平衡纠偏都会要求髋输出。β=0也不自动满足整机静态平衡，实际姿态需让合力线通过支承点。','',
      '## 平地行驶','', '| 加速度 m/s² | 髋绝对和包络 N·m | 膝绝对和包络 N·m | 每轮 N·m |','|---:|---:|---:|---:|']
    lines += [f'| {r["acceleration_m_s2"]:.1f} | {r["hip_absolute_envelope_Nm"]:.2f} | {r["knee_absolute_envelope_Nm"]:.2f} | {r["wheel_torque_Nm"]:.3f} |' for r in result['flat_driving']]
    lines += ['', '采用标称腿长、滚阻系数0.02假设，表中把轮电机作用在CW上的反力矩按不利方向计入髋和膝。仍未包含轮转动惯量与姿态控制峰值。',
      f'120rpm对应轮缘速度约{result["wheel_rated_speed_m_s"]:.2f}m/s；320rpm对应约{result["wheel_no_load_speed_m_s"]:.2f}m/s空载速度，后者不能当作满载运行保证。', '',
      '| 坡度 | 每轮所需 N·m（滚阻0.02） | 最小切向附着系数近似 |','|---:|---:|---:|']
    lines += [f'| {r["slope_deg"]}° | {r["wheel_torque_Nm"]:.3f} | {r["assumed_min_traction_coefficient"]:.3f} |' for r in result['wheel_climbing']]
    lines += ['', '坡度表仅为轮端牵引筛查；未将坡面切向力错误地直接代入全局水平雅可比。轮胎实测附着、整机重心、姿态控制和电机温升仍限制爬坡。','',
      '## 跳跃与落地','', '| 落差 m | 缓冲 mm | 平均载荷/重力 | 对应膝 N·m | B平均反力 N |','|---:|---:|---:|---:|---:|']
    lines += [f'| {r["drop_height_m"]:.2f} | {r["stopping_stroke_m"]*1000:.0f} | {r["displacement_average_force_multiple"]:.2f} | {r["knee_torque_at_average_force_Nm"]:.2f} | {r["B_reaction_at_average_N"]:.0f} |' for r in result['landing_scenarios']]
    lines += ['', '按225mm开始缓冲、行程s结束时的力臂计算。**载荷是能量平衡得到的位移平均力；转矩是该力乘终点力臂，既非时间平均转矩，也非冲击峰值**。单腿先落地、结构弹性和控制延迟可进一步增大峰值。不得把表内低于7N·m视为已通过跳跃验证。',
      f'两侧膝电机若在120→225mm全行程始终提供7N·m，理想机械功上界约{result["ideal_constant_peak_work_J"]:.1f}J，对应扣除伸腿重力功后的理想抛升上界约{result["ideal_peak_energy_height_upper_m"]:.2f}m。该数值忽略扭矩速度限制、峰值时间、转子与杆件动能和损耗，不能作为跳高预测。','',
      '| 理想离地后跳高 mm | 离地竖直速度 m/s | 膝电机相对转速 rpm |','|---:|---:|---:|']
    lines += [f'| {r["height_m"]*1000:.0f} | {r["vertical_speed_m_s"]:.2f} | {r["knee_relative_rpm"]:.1f} |' for r in result['takeoff_speed_scenarios']]
    lines += ['', '以上固定225mm腿长离地，β=0；膝电机转子相对定子的角速度是OA绝对角速度的两倍。100mm理想跳高已需要约205rpm，略高于24V型4310标称200rpm空载转速。50mm虽低于空载转速，所需转矩与145rpm能否同时达到仍无完整原厂曲线证明；改变离地姿态会改变该限制。因此当前电机组合尚不能确认满足跳跃目标。','',
      '## 公式与证据','',
      '`α=acos(ℓ/2L)`；`q_hip=−α`；`q_knee=2α−π`。轮心位置为`[L sin(qh)−L sin(qh+qk), −L cos(qh)+L cos(qh+qk)]`。β=0时雅可比两列为`(ℓ,0)`与`(ℓ/2,L sinα)`，已用独立中心差分核对。', '',
      '- [完整数据与假设](motor_load_analysis.json)、[逐项质量](mass_budget.json)、[独立公式核对](motor_load_independent_review.md)、[结构初筛](STRUCTURAL_SCREENING.md)。',
      '- [4310用户手册](../../references/DM-J4310-2EC/说明书/DM-J4310-2EC%20V1.1%20Geared%20Motor%20User%20Manual%20V1.2%202026-09-08.pdf)，第7页：300g、3/7N·m、120/200rpm。',
      '- [H6215用户教程V2](../../references/DM-H6215/说明书/DM-H6215轮毂电机使用教程V2.pdf)，第1页：360g、1/2N·m、120/320rpm。',
      '- [Orin官方机械规格](https://developer.nvidia.com/downloads/assets/embedded/secure/jetson/orin_nano/docs/jetson_orin_nano_devkit_carrier_board_specification_sp.pdf)，第29～30页：175g，整套103×90.5×34.77mm及公差。',
      '- [D435官方2025资料](https://realsenseai.com/wp-content/uploads/2025/09/Intel-RealSense-D400-Series-Datasheet-October-2025.pdf)，第69、140页：75g与安装孔。', '',
      '## 电源约束','',
      '四台4310在3N·m、120rpm与两台H6215在1N·m、120rpm的机械功率算术合计约176W，相当于24V母线至少7.3A，实际还需加驱动损耗、铜耗和电子设备功耗。该数值是指定六电机工作点的功率预算，不能作为本机器人常态耗电预测。静态保持机械功为0也仍有绕组发热。', '',
      '4310手册的2.5/7.5A明确为额定/峰值相电流，不能直接把六台相电流相加当电池母线电流。400g仅给出了电池质量，电压、容量、放电倍率和BMS限流仍未知，因此本报告不能确认电源持续/峰值供电或续航。', '',
      '本报告没有修改原MuJoCo惯量、控制器或热模型；旧仿真结果不构成本版实机能力证明。']
    (OUT/'MOTOR_LOAD.md').write_text('\n'.join(lines)+'\n')


def plot():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    report=json.loads((OUT/'motor_load_analysis.json').read_text())
    mass=report['mass_kg']
    budget=json.loads((OUT/'mass_budget.json').read_text())
    lengths=[120+i for i in range(106)]
    torque=[mass*G/2*jacobian(v/1000)[1][1] for v in lengths]
    distributed=distributed_gravity(budget,[v/1000 for v in lengths])['rows']
    fig,ax=plt.subplots(figsize=(9,5))
    ax.plot(lengths,[r['knee_magnitude_Nm'] for r in distributed],label=f'CAD distributed gravity, {mass:.2f} kg',lw=2.4)
    ax.plot(lengths,torque,label='Total mass concentrated at hip (screening)',ls='--',lw=1.8)
    ax.plot(lengths,[r['knee_magnitude_Nm']*1.25 for r in distributed],label='CAD gravity + 25% allowance',ls='-.',lw=1.6)
    ax.axhline(3,color='#c54d3d',ls=':',label='J4310 rated: 3 Nm')
    ax.set(xlabel='Hip-to-wheel vertical length (mm)',ylabel='Knee output torque per side (Nm)',
           title='V5 motor sizing | symmetric support, beta=0')
    ax.grid(alpha=.2);ax.legend();fig.tight_layout()
    fig.savefig(OUT/'previews/motor_load.png',dpi=180)
    fig.savefig(OUT/'previews/motor_load.svg')
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plot-only',action='store_true')
    args=parser.parse_args()
    if args.plot_only:
        plot();return
    budget=mass_budget();result=analyze(budget['total_kg'])
    result['distributed_gravity']=distributed_gravity(budget)
    result['mass_kg']=budget['total_kg']
    (OUT/'mass_budget.json').write_text(json.dumps(budget,indent=2)+'\n')
    (OUT/'motor_load_analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    write_markdown(budget,result)
    print(json.dumps({'mass_kg':budget['total_kg'],'standing':result['standing'],
                      'flat_driving':result['flat_driving']},indent=2))


if __name__=='__main__':
    main()
