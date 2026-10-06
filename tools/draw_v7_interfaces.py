"""Dimensioned vector review drawings from the same CAD interface constants."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mechanical/v7'


def draw_display():
    p=json.loads((OUT/'display_interface.json').read_text())
    s=4.;x0,y0=165.,130.;width,height=165*s,110*s
    cx,cy=x0+width/2,y0+height/2
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="810" viewBox="0 0 1100 810">',
         '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 Z" fill="#506775"/></marker></defs>',
         '<rect width="1100" height="810" fill="#f5f7f8"/>',
         '<g font-family="Arial, sans-serif" fill="#233747">',
         '<text x="55" y="52" font-size="27">V7 / 7-inch display mounting reference</text>',
         '<text x="55" y="86" font-size="17">All dimensions in mm · User drawing, not supplier-certified CAD</text>',
         f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" rx="6" fill="#dce4e7" stroke="#334c59" stroke-width="2"/>',
         f'<rect x="{cx-155*s/2}" y="{cy-87*s/2}" width="{155*s}" height="{87*s}" fill="#243c4b"/>',
         f'<text x="{cx}" y="{cy-4}" text-anchor="middle" fill="white" font-size="23">155 × 87 active area</text>',
         f'<text x="{cx}" y="{cy+30}" text-anchor="middle" fill="#bcd5df" font-size="20">1024 × 600 px</text>']
    hy,hz=p['nominal_hole_pitch_yz']
    hx0,hx1=cx-hy*s/2,cx+hy*s/2
    hz0,hz1=cy-hz*s/2,cy+hz*s/2
    for xx in (hx0,hx1):
        for yy in (hz0,hz1):
            svg.append(f'<circle cx="{xx}" cy="{yy}" r="6" fill="white" stroke="#c57428" stroke-width="2"/>')
    def dim(x1,y1,x2,y2,label,tx,ty):
        svg.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#506775" marker-start="url(#arrow)" marker-end="url(#arrow)"/>')
        svg.append(f'<text x="{tx}" y="{ty}" text-anchor="middle" font-size="18">{label}</text>')
    dim(hx0,615,hx1,615,'150.6377 hole pitch',cx,606)
    dim(x0,663,x0+width,663,'165 overall',cx,651)
    dim(895,hz0,895,hz1,'93.3845',951,cy)
    dim(102,y0,102,y0+height,'110',65,cy)
    for xx in (hx0,hx1):svg.append(f'<path d="M{xx},{hz1+7} V624" stroke="#90a0a7"/>')
    svg += ['<text x="875" y="185" font-size="19">4 × Ø3</text>',
            '<text x="875" y="222" font-size="17">Depth: 20</text>',
            '<text x="875" y="252" font-size="17">Mass: ~265 g</text>',
            '<text x="55" y="715" font-size="18" fill="#a65f20">Hole-array centre assumed; carrier permits ±2 mm independently in both axes.</text>',
            '<text x="55" y="748" font-size="17">HDMI / USB exit to rear. Mounting-lug thickness and connector positions remain unmeasured.</text>',
            '<text x="55" y="779" font-size="17">Screenshot decimal digits are not manufacturing tolerances.</text>', '</g></svg>']
    (OUT/'previews/display_dimensions.svg').write_text('\n'.join(svg))


if __name__=='__main__':draw_display()
