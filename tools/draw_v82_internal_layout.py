"""Annotate actual V8.2 FreeCAD views; no illustrative replacement geometry.

Run --render-cad with FreeCAD Python after geometry freeze. Run --annotate
with a Pillow-enabled Python and reviewed pixel anchors in the source JSON.
The native assembly is opened read-only and never saved by this script.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'mechanical/v8_2'
PREVIEWS = OUT / 'previews'
CONFIG = OUT / 'source/internal_layout_annotations.json'


def render_cad():
    sys.modules['flatmesh'] = None
    import render_nested_robot as view
    import render_modular_robot as style
    App, Gui = view.App, view.Gui
    view.OUT, view.PREVIEWS = OUT, PREVIEWS
    view.EXACT_CAPTURE_ORIENTATION = True
    view.FRAME_MARGIN = 1.12
    native = OUT / 'wheel_leg_v8_2.FCStd'
    digest = hashlib.sha256(native.read_bytes()).hexdigest()
    Gui.showMainWindow()
    import PartGui, MeshGui  # noqa: F401
    doc = App.openDocument(str(native))
    for g in doc.Objects:
        if g.TypeId in ('App::Part', 'App::DocumentObjectGroup'):
            g.ViewObject.Visibility = True
    wanted = {o.Name for key in ('M04', 'M07', 'M08') for o in doc.getObject(key).Group}
    wanted.update(('Power_switch_M16_latching', 'DC_charge_replaceable_plate', 'USB_hub_rear_clamp'))
    colors = {'electrical_service_carrier':(.21,.40,.45),
              'USB_hub_rear_clamp':(.25,.34,.39), 'USB_hub_104x30x10':(.38,.42,.48),
              'Power_switch_M16_latching':(.58,.62,.66),
              'USB2CANFD_Dual_bare_official':(.12,.43,.30),
              'Distribution_PCB1_user_STEP':(.15,.35,.67),
              'DCDC_24_to_19_drawing_envelope':(.49,.51,.54),
              'DC_charge_replaceable_plate':(.19,.25,.28)}
    for o in doc.Objects:
        if o.TypeId not in ('Part::Feature', 'Mesh::Feature'):
            continue
        style.color(o)
        o.ViewObject.Visibility = (o.Name in wanted and
            getattr(o, 'Material', '') != 'routing_allowance' and
            getattr(o, 'ExportRole', '') != 'collision_and_mass_proxy_only')
        if o.Name in colors:
            o.ViewObject.ShapeColor = colors[o.Name]
        if o.Name == 'electronics_tray':
            o.ViewObject.Transparency = 72
    front = App.Rotation(App.Vector(-1,1.35,0), App.Vector(-.7425,-.55,2.8225),
                         App.Vector(1.35,1,.55), 'ZXY').Q
    rear = App.Rotation(App.Vector(1,-1.2,0), App.Vector(.8,.67,2.44),
                        App.Vector(-1.2,-1,.8), 'ZXY').Q
    for name, rotation in (('internal_cutaway.png', front),
                           ('internal_cutaway_rear.png', rear)):
        view.save_view(doc, name, rotation, 2200, 1700)
    metadata = {'native_sha256': digest, 'visible_objects': sorted(wanted),
                'hidden_for_observation': ['external shells', 'front-face module', 'structural frame', 'legs'],
                'transparent_for_observation': {'electronics_tray': 72},
                'positions_unchanged': True, 'native_saved': False}
    (OUT / 'source/internal_layout_render_source.json').write_text(json.dumps(metadata, indent=2))
    App.closeDocument(doc.Name)
    assert hashlib.sha256(native.read_bytes()).hexdigest() == digest
    print('V82_INTERNAL_CUTAWAY_RENDERED', flush=True)


def annotate():
    from PIL import Image, ImageChops, ImageDraw, ImageFont
    config = json.loads(CONFIG.read_text())
    width, height = 3000, 2290
    canvas = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(canvas)
    font_path = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
    font = lambda size: ImageFont.truetype(font_path, size)
    ink, muted, accent = '#183345', '#506775', '#137C8B'
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="white"/>']

    def text(x, y, value, size=32, color=ink):
        draw.text((x,y), value, fill=color, font=font(size))
        svg.append(f'<text x="{x}" y="{y+size}" font-size="{size}" fill="{color}" font-family="Arial Unicode MS, PingFang SC, sans-serif">{html.escape(value)}</text>')

    def line(points, color=accent, stroke=3):
        draw.line(points, fill=color, width=stroke, joint='curve')
        svg.append('<polyline points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="{stroke}"/>')

    text(75,45,'V8.2 机体内部结构',60)
    text(78,128,'真实 CAD 装配位置 · 模块化安装与接口布置',31,muted)
    line([(75,186),(2920,186)], '#CCD8DD', 2)
    projectors = {}
    image_qa = []
    for key, spec in config['panels'].items():
        source = PREVIEWS / spec['source_image']
        picture = Image.open(source).convert('RGB')
        difference=ImageChops.difference(picture,Image.new('RGB',picture.size,'white'))
        bbox=difference.point(lambda p:255 if p>20 else 0).getbbox()
        if bbox is None:raise ValueError('Empty CAD image')
        pad=125
        crop=tuple(spec.get('crop_box',(max(0,bbox[0]-pad),max(0,bbox[1]-pad),min(picture.width,bbox[2]+pad),min(picture.height,bbox[3]+pad))))
        cut=picture.crop(crop)
        px,py,pw,ph=spec['viewport']
        scale=min(pw/cut.width,ph/cut.height)
        newsize=(round(cut.width*scale),round(cut.height*scale))
        origin=(px+(pw-newsize[0])//2,py+(ph-newsize[1])//2)
        canvas.paste(cut.resize(newsize,Image.Resampling.LANCZOS),origin)
        encoded=base64.b64encode(source.read_bytes()).decode('ascii')
        svg.append(f'<defs><clipPath id="cadClip_{key}"><rect x="{origin[0]}" y="{origin[1]}" width="{newsize[0]}" height="{newsize[1]}"/></clipPath></defs>')
        image_x,image_y=origin[0]-crop[0]*scale,origin[1]-crop[1]*scale
        svg.append(f'<image x="{image_x}" y="{image_y}" width="{picture.width*scale}" height="{picture.height*scale}" clip-path="url(#cadClip_{key})" xlink:href="data:image/png;base64,{encoded}"/>')
        projectors[key]=(origin,crop,scale)
        text(px+20,py-42,spec['title'],30,muted)
        image_qa.append({'source_image':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'crop_box':crop})
    for item in config['annotations']:
        origin,crop,scale=projectors[item['panel']]
        project=lambda p:(origin[0]+(p[0]-crop[0])*scale,origin[1]+(p[1]-crop[1])*scale)
        target, badge = project(item['target']), project(item['badge'])
        dx,dy=target[0]-badge[0],target[1]-badge[1]
        distance=math.hypot(dx,dy)
        ux,uy=dx/distance,dy/distance
        start=(badge[0]+27*ux,badge[1]+27*uy)
        line([start,target])
        tip=[target,(target[0]-14*ux+6*uy,target[1]-14*uy-6*ux),
                    (target[0]-14*ux-6*uy,target[1]-14*uy+6*ux)]
        draw.polygon(tip,fill=accent)
        svg.append('<polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in tip)+f'" fill="{accent}"/>')
        bx,by=badge;r=27
        draw.ellipse((bx-r,by-r,bx+r,by+r),fill='white',outline=accent,width=3)
        svg.append(f'<circle cx="{bx}" cy="{by}" r="{r}" fill="white" stroke="{accent}" stroke-width="3"/>')
        label=str(item['number']);fs=font(27)
        tb=draw.textbbox((0,0),label,font=fs)
        draw.text((bx-(tb[2]-tb[0])/2,by-(tb[3]-tb[1])/2-tb[1]),label,font=fs,fill=accent)
        svg.append(f'<text x="{bx}" y="{by+9}" text-anchor="middle" font-size="27" fill="{accent}" font-family="Arial Unicode MS, sans-serif">{label}</text>')
    line([(1910,225),(1910,1450)],'#D7E0E4',2)
    text(1980,1385,'观察用隐藏，不代表拆移或悬空安装。',27,muted)
    text(1980,1430,'箭头指向实件；线束规划另见接线图。',27,muted)
    line([(75,1530),(2920,1530)],'#CCD8DD',2)
    for i,item in enumerate(config['annotations']):
        x=80+(i%3)*970
        y=1570+(i//3)*135
        text(x,y,f"{item['number']:02d}  {item['title']}",35)
        for j,detail in enumerate(item.get('details',[])):
            text(x+60,y+51+j*36,detail,27,muted)
    line([(75,2120),(2920,2120)],'#CCD8DD',2)
    notes=config.get('notes',[
        '为观察内部，隐藏外壳、前脸、框架及腿部，托盘半透明；零件保持原装配位置。',
        '开关、变压模块和 USB Hub 按已知尺寸建模；实际接插件与线束弯曲余量需实物复核。'])
    for i,note in enumerate(notes):text(80,2150+i*48,note,28,muted)
    text(2700,2240,'单位：mm',26,muted)
    svg.append('</svg>')
    svg_path=PREVIEWS/'internal_structure_annotated.svg'
    png_path=PREVIEWS/'internal_structure_annotated.png'
    svg_path.write_text('\n'.join(svg))
    canvas.save(png_path)
    qa={'source_images':image_qa,
        'annotation_count':len(config['annotations']),'canvas_size':[width,height],
        'anchors_reviewed_in_source_pixels':True,'svg':str(svg_path),'png':str(png_path)}
    (OUT/'source/internal_layout_annotation_qa.json').write_text(json.dumps(qa,indent=2))
    print('V82_INTERNAL_DIAGRAM_WRITTEN',flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--render-cad',action='store_true')
    parser.add_argument('--annotate',action='store_true')
    args=parser.parse_args()
    if args.render_cad:render_cad()
    if args.annotate:annotate()
    if not (args.render_cad or args.annotate):parser.error('Select --render-cad or --annotate')
    if args.render_cad:
        # The macOS bundled FreeCAD/Qt runtime may crash during Python's GUI
        # destructor teardown. Documents and output files are already closed;
        # avoid that teardown only after all rendering/hash assertions pass.
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
