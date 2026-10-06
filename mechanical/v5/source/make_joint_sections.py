"""Native FreeCAD sections of the released V5 leg; schematic colors only."""
from pathlib import Path
import sys,html
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import cad_v5_leg as leg
cad=leg.cad
cad.configure(ROOT/'mechanical/v5');cad.P.update(leg.configure())
pose=cad.pose(cad.P['leg_length'])
parts=leg.designs();hardware=leg.hardware()
colors={'OB_inner_full':'#80bd7b','OB_outer_full':'#a4d49a','OA_one_piece':'#9786d5',
        'AC_bearing_link':'#e78b86','CW_one_piece':'#6cc8c3'}
shapes=[(name,cad.transform(shape,role,pose),colors[name]) for name,(shape,role,_) in parts.items()]
for name,shape,role in hardware:
    col='#d4a251' if 'bronze' in name else '#aab6c2' if name.startswith('626') else '#5e6c7b'
    shapes.append((name,cad.transform(shape,role,pose),col))
a=pose['a'];b=pose['b'];c=(a[0]+b[0],a[1]+b[1])
s=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1020" viewBox="0 0 1600 1020">',
   '<style>text{font-family:"PingFang SC",Arial,sans-serif;fill:#233448} .edge{stroke:#334557;stroke-width:.7;stroke-linejoin:round}</style>',
   '<rect width="1600" height="1020" fill="#f5f7fa"/>']
def txt(x,y,text,size=19,weight=400):
    s.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}">{html.escape(text)}</text>')
def line(x,y,x1,y1,dash=''):
    s.append(f'<path d="M{x} {y}L{x1} {y1}" fill="none" stroke="#738699" stroke-width="1" {dash}/>')
txt(55,64,'V5 · A / B / C 真实 CAD 轴向剖面',36,650)
txt(55,105,'从 FreeCAD 实体截取，非手绘叠层；名义腿长 183.848 mm。轴向放大显示，单位 mm。',21)
txt(55,142,'基准 S = 膝前定子面 132.1；完整 OB 外盖位于所有 OA / CW 外耳之外。',21)
for ox,title,point,notes in (
    (50,'A · OA 一体叉夹 AC',a,['OB 两板完整覆盖 A 耳 / 轴端','A 内侧保持件先在框外装好','轴端到 OB：内 0.30 / 外 0.25']),
    (565,'B · OB 台阶支承 CW 舌',b,['两片 OB 局部凸台向内支撑钢轴','B 轴端可经 Ø9.2 沉台安装','外盖合拢时先对准 B 轴与铜套']),
    (1080,'C · CW 一体叉夹 AC',c,['C 叉通过 B 圆弧背桥连成一体','不再使用独立外帽或两根螺钉柱','外圈保持片在插入叉口前锁紧'])):
    s.append(f'<rect x="{ox}" y="175" width="470" height="625" rx="12" fill="white" stroke="#dae1e9"/>')
    txt(ox+18,213,title,23,600)
    px=ox+72;cy=441;sx=15;sr=8.5
    plane=leg.Part.makePlane(36,22,leg.V(point[0]-18,leg.S(),point[1]),leg.V(0,0,1))
    for name,shape,color in shapes:
        section=plane.common(shape)
        for face in section.Faces:
            paths=[]
            for wire in face.Wires:
                points=wire.discretize(Deflection=.015)
                if len(points)<3:continue
                path='M'+' L'.join(f'{px+(p.y-leg.S())*sx:.3f},{cy-(p.x-point[0])*sr:.3f}' for p in points)+' Z'
                paths.append(path)
            if paths:s.append(f'<path class="edge" fill="{color}" fill-rule="evenodd" d="{" ".join(paths)}"/>')
    line(px-16,cy,px+22*sx+16,cy,'stroke-dasharray="5 5"')
    for offset in (0,3,7,15,19,22):
        xx=px+offset*sx
        line(xx,603,xx,617)
        txt(xx-8,640,str(offset),15)
    line(px,611,px+330,611)
    txt(ox+24,669,'Y − S',16)
    for i,note in enumerate(notes):txt(ox+20,707+i*28,note,18,500 if i==0 else 400)
# Color and hardware key.
xx=65
for name,col,width in [('OB','#80bd7b',170),('OA','#9786d5',170),('AC','#e78b86',170),('CW','#6cc8c3',170),('626 轴承','#aab6c2',210),('铜套','#d4a251',170),('轴 / 保持件','#5e6c7b',240)]:
    s.append(f'<rect x="{xx}" y="833" width="28" height="22" fill="{col}" stroke="#334557"/>')
    txt(xx+39,853,name,19);xx+=width
for y,text in [(897,'单 626ZZ1：6×19×6；止肩 0.75 + 轴承 6 + 名义轴向隙 0.05 + 钢保持片 0.8。'),
               (931,'Ø6 钢短轴长 14.05；铜套各长 2.5；低头 M2 与 Ø9×0.2 垫片实现轴端机械防脱。'),
               (972,'本图证明剖面装配关系；不代表跳跃冲击、疲劳或装配公差已通过试验。')]:txt(55,y,text,20)
s.append('</svg>')
(ROOT/'mechanical/v5/previews/joint_sections.svg').write_text('\n'.join(s)+'\n')
print('joint_sections.svg created from native shape/plane intersections')
