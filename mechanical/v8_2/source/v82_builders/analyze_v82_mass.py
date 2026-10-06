"""Update the mass budget without double-counting newly represented devices."""
import json
import hashlib
import build_printable_robot as cad
import analyze_v8_motor_load as loads
from analyze_v6_proportions import Geometry
from analyze_v6_motor_load import com

OUT=cad.ROOT/'mechanical/v8_2'
BASE=cad.ROOT/'mechanical/v8_1'


def main():
    doc=cad.App.openDocument(str(OUT/'wheel_leg_v8_2.FCStd'))
    old=json.loads((BASE/'mass_budget.json').read_text())
    rows=[]
    for o in doc.Objects:
        if o.TypeId!='Part::Feature' or getattr(o,'Material','')=='routing_allowance':continue
        material=o.Material
        if material=='payload':
            mass=o.BudgetMassGrams
            method='Device BudgetMassGrams; new five device values are unweighed engineering assumptions'
        elif material=='motor':
            mass=360 if 'H6215' in o.Name else 300
            method='Supplier nominal motor mass'
        else:
            density={'PETG':.00127,'CNC':.0027,'steel':.00785,'rubber':.0011}[material]
            if o.Name.startswith('flanged_bush_'):
                material='bronze';density=.0088
            mass=o.Shape.Volume*density
            method='CAD solid volume times nominal density; not slicer/scale mass'
        c,_=com(o.Shape,cad.App)
        local=o.Placement.inverse().multVec(c)
        rows.append(dict(part=o.Name,material=material,mass_g=round(mass,3),center_mm=list(c),local_center_mm=list(local),role=o.KinematicRole,method=method))
    rows.append(dict(part='unmodelled_installation_allowance',material='allowance',mass_g=100.,
        center_mm=[0,0,30],local_center_mm=[0,0,30],role='fixed',
        method='100g assumption for remaining wires/extensions/plugs/straps/pads/protection. Old200g allowance included DC/DC; it is replaced, not added again.'))
    total=sum(r['mass_g'] for r in rows)/1000
    categories={}
    for r in rows:categories[r['material']]=categories.get(r['material'],0)+r['mass_g']/1000
    center=[sum(r['mass_g']*r['center_mm'][i] for r in rows)/(total*1000) for i in range(3)]
    budget=dict(total_kg=total,by_material_kg=categories,nominal_center_from_hip_mm=center,parts=rows,
                baseline_v81_kg=old['total_kg'],allowance_replacement_g=[200,100],
                scope='Estimated masses and rigid CAD density. Routing volumes excluded. No measured finished robot mass.')
    (OUT/'mass_budget.json').write_text(json.dumps(budget,ensure_ascii=False,indent=2)+'\n')
    screen=next(r['part'] for r in rows if r['part'].startswith('Display_'))
    report=loads.analyze(budget,screen,Geometry('V8.2 preserved legs',.130,.105,.045))
    report.update(version='V8.2',scope='Inherited static rigid-body calculations with new mass estimates. Not jump qualification or electrical power validation.')
    (OUT/'motor_load_analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# V8.2 质量与负载更新','',f'整机工程预算 **{total:.3f} kg**。未称重的新设备暂估：裸CAN18g、配电板18g、转换器65g、开关35g、USB坞60g。屏幕仍200g、电池含底座仍400g。','',
        '原V8.1的200g杂件预算包含转换器；本版设备单列后，将剩余线束、延长线、保护附件、软垫和束带改为100g独立假设，避免重复计数。不是质量上界。','',
        '| 类别 | kg |','|---|---:|']
    lines += [f'|{key}|{value:.3f}|' for key,value in categories.items()]
    lines += ['',f'名义180mm姿态每膝静力矩 {report["nominal"]["knee_magnitude_Nm"]:.3f} N·m；100～215mm取样最大 {report["worst_sample"]["knee_magnitude_Nm"]:.3f} N·m。',
        '', '这是固定机身姿态下的静力计算，不能确认动态平衡、连续温升或跳跃。V8.2新增线束示意不参与动力学质量；新设备预算已计入。',
        '', '电池6A持续、开关DC分断额定值未知、转换器规格未知仍是独立限制。四台J4310同时3N·m/120rpm的机械功率约150.8W，已超过E626S标称133.2W持续电功率。详见[ELECTRICAL_INTEGRATION.md](ELECTRICAL_INTEGRATION.md)。',
        '', 'PETG以实体体积计重，钢件/轴承是简化实体，供应商CAD的质量中心用均匀体积近似。生产前以切片与实测替换；未更新MuJoCo惯量或控制参数。']
    (OUT/'MASS_AND_LOAD.md').write_text('\n'.join(lines)+'\n')
    cad.App.closeDocument(doc.Name)
    print('V82_MASS',total,flush=True)


if __name__=='__main__':main()
