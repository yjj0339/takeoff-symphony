# -*- coding: utf-8 -*-
"""凌云起飞 · 机场场景 → assets/airport.glb
坐标：+Y=北（对应 three.js -Z 前方）；飞机从南端(three +Z)进入向北起飞
包含：跑道+全套标线（几何）、边灯/滑行道灯/进近灯、滑行道、停机坪、
     航站楼、塔台、廊桥、车辆、风向袋、树带、草地、农田色块、河流、远山
"""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.normpath(os.path.join(HERE, '..', 'assets', 'tex'))
OUT = os.path.normpath(os.path.join(HERE, '..', 'assets', 'airport.glb'))
random.seed(42)

def clean_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m, do_unlink=True)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat, do_unlink=True)
    for img in list(bpy.data.images):
        if img.users == 0:
            bpy.data.images.remove(img)

def new_mat(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, emissive=None, emiss_str=0.0, double=True):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = [n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emissive is not None:
        for k in ('Emission Color', 'Emission'):
            if k in bsdf.inputs:
                bsdf.inputs[k].default_value = (*emissive, 1.0)
        if 'Emission Strength' in bsdf.inputs:
            bsdf.inputs['Emission Strength'].default_value = emiss_str
    m.use_backface_culling = not double
    return m

def tex_mat(name, tex_file, repeat_hint=8.0, rough=0.85, metal=0.0):
    m = new_mat(name, rough=rough, metal=metal)
    nt = m.node_tree
    bsdf = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    img = bpy.data.images.load(os.path.join(TEX, tex_file))
    img.colorspace_settings.name = 'sRGB'
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img
    tn.extension = 'REPEAT'
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
    return m

def mesh_from_bm(name, bm, mats, parent=None, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for m in mats:
        me.materials.append(m)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if parent is not None:
        ob.parent = parent
    return ob

def ground_rect(bm, x0, x1, y0, y1, z, mi, uv_scale=None, seg=1):
    before_v = len(bm.verts)
    vs = [bm.verts.new(Vector((x0, y0, z))), bm.verts.new(Vector((x1, y0, z))),
          bm.verts.new(Vector((x1, y1, z))), bm.verts.new(Vector((x0, y1, z)))]
    f = bm.faces.new(vs)
    f.material_index = mi
    if uv_scale:
        uvl = bm.loops.layers.uv.verify()
        for loop, (px, py) in zip(f.loops, ((x0, y0), (x1, y0), (x1, y1), (x0, y1))):
            loop[uvl].uv = (px / uv_scale, py / uv_scale)
    return f

def add_box(bm, cx, cy, cz, sx, sy, sz, mi, rot_z=0.0):
    before_v = len(bm.verts)
    bmesh.ops.create_cube(bm, size=1.0)
    bm.verts.ensure_lookup_table()
    vs = [v for v in bm.verts[before_v:]]
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=vs)
    if rot_z:
        bmesh.ops.rotate(bm, verts=vs, matrix=Matrix.Rotation(rot_z, 4, 'Z'))
    bmesh.ops.translate(bm, vec=(cx, cy, cz), verts=vs)
    vs_set = set(vs)
    for f in bm.faces:
        if all(v in vs_set for v in f.verts):
            f.material_index = mi

def add_cyl(bm, p0, p1, r0, r1, seg, mi):
    d = Vector(p1) - Vector(p0); L = max(0.01, d.length)
    before_v = len(bm.verts)
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=seg, radius1=r0, radius2=r1, depth=L)
    bm.verts.ensure_lookup_table()
    vs = [v for v in bm.verts[before_v:]]
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.rotate(bm, verts=vs, matrix=rot.to_matrix().to_4x4())
    bmesh.ops.translate(bm, vec=((Vector(p0) + Vector(p1)) / 2), verts=vs)
    vs_set = set(vs)
    for f in bm.faces:
        if all(v in vs_set for v in f.verts):
            f.material_index = mi

def add_cone_at(bm, cx, cy, cz, r, h, mi, seg=10, jitter=0.0):
    before_v = len(bm.verts)
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=seg, radius1=r, radius2=0.02, depth=h)
    bm.verts.ensure_lookup_table()
    vs = [v for v in bm.verts[before_v:]]
    if jitter:
        for v in vs:
            v.co.x += random.uniform(-jitter, jitter)
            v.co.y += random.uniform(-jitter, jitter)
    bmesh.ops.translate(bm, vec=(cx, cy, cz + h / 2), verts=vs)
    vs_set = set(vs)
    for f in bm.faces:
        if all(v in vs_set for v in f.verts):
            f.material_index = mi

# ---------------- 材质 ----------------
def build_materials():
    M = {}
    M['asph'] = tex_mat('M_Asphalt', 'asphalt.png', rough=0.92)
    M['conc'] = tex_mat('M_Concrete', 'concrete.png', rough=0.88)
    M['grass'] = tex_mat('M_Grass', 'grass.png', rough=0.95)
    M['lw'] = new_mat('M_LineWhite', (0.92, 0.93, 0.94), rough=0.55)
    M['ly'] = new_mat('M_LineYellow', (0.90, 0.72, 0.12), rough=0.55)
    M['glass'] = tex_mat('M_TermGlass', 'terminal_glass.png', rough=0.18, metal=0.35)
    M['roof'] = new_mat('M_Roof', (0.93, 0.94, 0.95), rough=0.4)
    M['wall'] = new_mat('M_Wall', (0.86, 0.88, 0.90), rough=0.6)
    M['metal'] = new_mat('M_Metal', (0.72, 0.75, 0.78), rough=0.35, metal=0.8)
    M['dark'] = new_mat('M_Dark', (0.16, 0.17, 0.18), rough=0.6)
    M['em_w'] = new_mat('M_LampWhite', (0.9, 0.9, 0.9), emissive=(1, 1, 0.96), emiss_str=7.0)
    M['em_b'] = new_mat('M_LampBlue', (0.15, 0.3, 0.9), emissive=(0.25, 0.5, 1.0), emiss_str=6.0)
    M['em_r'] = new_mat('M_LampRed', (0.8, 0.1, 0.1), emissive=(1, 0.15, 0.1), emiss_str=6.0)
    M['em_g'] = new_mat('M_LampGreen', (0.1, 0.7, 0.2), emissive=(0.2, 1, 0.3), emiss_str=6.0)
    M['trunk'] = new_mat('M_Trunk', (0.42, 0.33, 0.26), rough=0.9)
    M['tree'] = new_mat('M_Tree', (0.34, 0.55, 0.33), rough=0.9)
    M['tree2'] = new_mat('M_Tree2', (0.45, 0.62, 0.36), rough=0.9)
    M['mount'] = new_mat('M_Mount', (0.66, 0.76, 0.78), rough=0.95)
    M['mount2'] = new_mat('M_Mount2', (0.55, 0.66, 0.70), rough=0.95)
    M['field1'] = new_mat('M_Field1', (0.87, 0.83, 0.55), rough=0.95)
    M['field2'] = new_mat('M_Field2', (0.75, 0.84, 0.52), rough=0.95)
    M['field3'] = new_mat('M_Field3', (0.70, 0.81, 0.62), rough=0.95)
    M['river'] = new_mat('M_River', (0.58, 0.78, 0.87), rough=0.15, metal=0.1)
    M['orange'] = new_mat('M_Orange', (0.95, 0.45, 0.10), rough=0.7)
    M['truck'] = new_mat('M_Truck', (0.94, 0.95, 0.96), rough=0.4)
    M['truck2'] = new_mat('M_Truck2', (0.88, 0.80, 0.30), rough=0.5)
    return M

RWY_HALF_W = 22.5
RWY_Y0, RWY_Y1 = -1130, 1130     # Blender y（南→北）

def main():
    clean_scene()
    M = build_materials()
    root = bpy.data.objects.new('Airport', None)
    bpy.context.scene.collection.objects.link(root)

    # ============ 地形 ============
    bm = bmesh.new()
    ground_rect(bm, -5000, 5000, -5000, 5000, 0.0, 0, uv_scale=16.0)
    mesh_from_bm('Ground', bm, [M['grass']], parent=root)
    # 农田色块（西侧）
    bm = bmesh.new()
    flds = [(-1500, -800, -2200, -1300, 1), (-2400, -1600, -500, 500, 2),
            (-1200, -300, 500, 1400, 3), (-2600, -1800, -2100, -1200, 2),
            (-700, -250, -1400, -600, 3), (-2300, -1500, 700, 1500, 1)]
    for (x0, x1, y0, y1, k) in flds:
        ground_rect(bm, x0, x1, y0, y1, 0.02, k - 1)
    mesh_from_bm('Fields', bm, [M['field1'], M['field2'], M['field3']], parent=root)
    # 河流（蜿蜒带，两段）
    bm = bmesh.new()
    river_pts = [(-620, -2200), (-560, -1200), (-660, -300), (-580, 600), (-680, 1600), (-620, 2300)]
    for i in range(len(river_pts) - 1):
        (xa, ya), (xb, yb) = river_pts[i], river_pts[i + 1]
        dx, dy = xb - xa, yb - ya
        L = math.hypot(dx, dy); nx, ny = -dy / L * 24, dx / L * 24
        vs = [bm.verts.new(Vector((xa + nx, ya + ny, 0.04))), bm.verts.new(Vector((xa - nx, ya - ny, 0.04))),
              bm.verts.new(Vector((xb - nx, yb - ny, 0.04))), bm.verts.new(Vector((xb + nx, yb + ny, 0.04)))]
        f = bm.faces.new(vs); f.material_index = 0
    mesh_from_bm('River', bm, [M['river']], parent=root)
    # 远山（西北/北，浅色低多边形）
    bm = bmesh.new()
    mounts = [(-2400, 2600, 620, 190, 0), (-1400, 2900, 500, 150, 1), (-300, 3100, 680, 210, 0),
              (900, 2800, 560, 170, 1), (2000, 2600, 480, 140, 0), (-3200, 1700, 540, 160, 1),
              (3000, 1400, 500, 150, 0)]
    for (mx, my, r, h, k) in mounts:
        add_cone_at(bm, mx, my, 0, r, h, k, seg=11, jitter=r * 0.16)
    mesh_from_bm('Mountains', bm, [M['mount'], M['mount2']], parent=root, smooth=True)
    # 树带（跑道两侧围界内）
    bm = bmesh.new()
    for i in range(38):
        x = 132 + (i % 2) * 6 + random.uniform(-2, 2)
        y = -1050 + i * 46 + random.uniform(-8, 8)
        add_cyl(bm, (x, y, 0), (x, y, 1.6), 0.14, 0.10, 6, 0)
        add_cone_at(bm, x, y, 1.4, 1.5, 3.4, 1 if i % 3 else 2, seg=8, jitter=0.2)
    for i in range(40):
        x = -132 - (i % 2) * 6 + random.uniform(-2, 2)
        y = -1000 + i * 50 + random.uniform(-8, 8)
        add_cyl(bm, (x, y, 0), (x, y, 1.6), 0.14, 0.10, 6, 0)
        add_cone_at(bm, x, y, 1.4, 1.5, 3.4, 2 if i % 3 else 1, seg=8, jitter=0.2)
    mesh_from_bm('Trees', bm, [M['trunk'], M['tree'], M['tree2']], parent=root, smooth=True)

    # ============ 跑道 + 标线 ============
    bm = bmesh.new()
    ground_rect(bm, -RWY_HALF_W, RWY_HALF_W, RWY_Y0, RWY_Y1, 0.06, 0, uv_scale=7.5)
    mesh_from_bm('Runway', bm, [M['asph']], parent=root)
    bm = bmesh.new()
    # 边线
    ground_rect(bm, -22.05, -21.15, RWY_Y0 + 12, RWY_Y1 - 12, 0.09, 0)
    ground_rect(bm, 21.15, 22.05, RWY_Y0 + 12, RWY_Y1 - 12, 0.09, 0)
    # 中线虚线（30 段 20 隙）
    y = RWY_Y0 + 30
    while y < RWY_Y1 - 30:
        ground_rect(bm, -0.45, 0.45, y, y + 30, 0.09, 0)
        y += 50
    # 两端 threshold 条纹（12 条）
    for (ye, d) in ((RWY_Y0 + 22, 1), (RWY_Y1 - 22, -1)):
        for k in range(6):
            for sgn in (-1, 1):
                xc = sgn * (2.2 + k * 3.6)
                ground_rect(bm, xc - 0.9, xc + 0.9, ye if d > 0 else ye - 14, ye + 14 * d, 0.09, 0)
    # 接地带标志（南端 4 组，双侧各 3 条）
    for gi in range(4):
        yc = RWY_Y0 + 150 + gi * 150
        for sgn in (-1, 1):
            for k in range(3 - (gi // 2)):
                xc = sgn * (7 + k * 3.0)
                ground_rect(bm, xc - 0.75, xc + 0.75, yc, yc + 15, 0.09, 0)
    mesh_from_bm('RunwayMark', bm, [M['lw']], parent=root)
    # 跑道号 36（南端，头朝南可读）与 18（北端）
    for (txt, cy, flip) in (('36', RWY_Y0 + 68, False), ('18', RWY_Y1 - 68, True)):
        tc = bpy.data.curves.new('rwy_num', type='FONT')
        tc.body = txt
        tc.size = 15.0
        tc.space_character = 2.0
        tc.align_x = 'CENTER'
        try:
            tc.font = bpy.data.fonts.load('C:/Windows/Fonts/arialbd.ttf')
        except Exception:
            pass
        tob = bpy.data.objects.new('RwyNum', tc)
        bpy.context.scene.collection.objects.link(tob)
        bpy.context.view_layer.objects.active = tob
        tob.select_set(True)
        bpy.ops.object.convert(target='MESH')
        me = tob.data
        bm2 = bmesh.new()
        bm2.from_mesh(me)
        # 字面 XY → 躺地（RX90: 字头→+Y；法线朝下→翻面）
        for v in bm2.verts:
            v.co = Vector((v.co.x, -v.co.z, v.co.y))
            if flip:
                v.co.y = -v.co.y
        bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
        ob = mesh_from_bm(f'RwyNum_{txt}', bm2, [M['lw']], parent=root)
        ob.location = (0, cy if not flip else -cy if False else cy, 0.10)
        bpy.data.objects.remove(tob, do_unlink=True)
        bpy.data.curves.remove(tc)

    # ============ 滑行道 ============
    bm = bmesh.new()
    ground_rect(bm, 68.5, 91.5, -1128, 178, 0.05, 0, uv_scale=7.5)       # A 滑行道
    ground_rect(bm, 22.5, 68.5, -1141, -1118, 0.05, 1, uv_scale=7.5)     # 联络道 B1（南跑道头）
    ground_rect(bm, 22.5, 68.5, 1118, 1141, 0.05, 1, uv_scale=7.5)       # 联络道 B0（北跑道头）
    ground_rect(bm, 22.5, 100.0, 88, 111, 0.05, 1, uv_scale=7.5)         # 联络道 B2（停机坪）
    mesh_from_bm('Taxiways', bm, [M['asph'], M['conc']], parent=root)
    bm = bmesh.new()
    ground_rect(bm, 79.85, 80.15, -1120, 172, 0.08, 0)                    # A 中线
    ground_rect(bm, 22.5, 68.5, -1119.85, -1119.55, 0.08, 0)             # B1 中线
    ground_rect(bm, 22.5, 68.5, 1119.55, 1119.85, 0.08, 0)               # B0 中线
    ground_rect(bm, 22.5, 100.0, 99.85, 100.15, 0.08, 0)                 # B2 中线
    mesh_from_bm('TaxiMark', bm, [M['ly']], parent=root)

    # ============ 停机坪 ============
    bm = bmesh.new()
    ground_rect(bm, 91.5, 195, 830, 1075, 0.04, 0, uv_scale=9.0)
    mesh_from_bm('Apron', bm, [M['conc']], parent=root)
    bm = bmesh.new()
    for cx in (116, 143, 170):
        ground_rect(bm, cx - 0.2, cx + 0.2, 845, 1055, 0.07, 0)          # 站位中线
        ground_rect(bm, cx - 8, cx + 8, 1002.8, 1003.4, 0.07, 0)         # 停止横杠
    mesh_from_bm('ApronMark', bm, [M['ly']], parent=root)

    # ============ 灯光 ============
    bm = bmesh.new()
    y = RWY_Y0
    while y <= RWY_Y1:
        for sgn in (-1, 1):
            add_box(bm, sgn * 23.4, y, 0.22, 0.22, 0.22, 0.16, 0)         # 跑道边灯白
        y += 60
    y = -1148
    while y >= -1448:
        add_box(bm, 0, y, 1.1, 0.3, 0.3, 0.9, 2)                          # 进近灯（白，杆上）
        y -= 60
    for k in range(4):
        add_box(bm, -28, -990 - k * 8, 0.55, 0.5, 0.9, 0.35, 0)           # PAPI 白
    y = -1120
    while y <= 170:
        for sgn in (-1, 1):
            add_box(bm, sgn * 92.0 if sgn > 0 else sgn * 68.0, y, 0.2, 0.2, 0.2, 0.15, 1)
        y += 60
    mesh_from_bm('AirfieldLights', bm, [M['em_w'], M['em_b'], M['metal']], parent=root)

    # ============ 航站楼 ============
    bm = bmesh.new()
    add_box(bm, 221, 955, 8.5, 52, 268, 17, 0)                            # 主体
    add_box(bm, 221, 890, 10.5, 46, 42, 21, 0)                            # 塔侧高段
    add_box(bm, 221, 1020, 10.5, 46, 42, 21, 0)                           # 另一侧高段
    mesh_from_bm('TerminalBody', bm, [M['wall']], parent=root)
    bm = bmesh.new()
    add_box(bm, 221, 955, 17.6, 54, 270, 1.6, 0)                          # 挑檐屋顶
    add_box(bm, 221, 890, 21.2, 48, 44, 1.4, 0)
    add_box(bm, 221, 1020, 21.2, 48, 44, 1.4, 0)
    mesh_from_bm('TerminalRoof', bm, [M['roof']], parent=root)
    # 玻璃幕墙（西面贴片，带 UV）
    bm = bmesh.new()
    for (cy, sy) in ((955, 268), (890, 42), (1020, 42)):
        v0 = bm.verts.new(Vector((194.8, cy - sy / 2, 1.2)))
        v1 = bm.verts.new(Vector((194.8, cy + sy / 2, 1.2)))
        v2 = bm.verts.new(Vector((194.8, cy + sy / 2, 15.2)))
        v3 = bm.verts.new(Vector((194.8, cy - sy / 2, 15.2)))
        f = bm.faces.new((v0, v1, v2, v3)); f.material_index = 0
        uvl = bm.loops.layers.uv.verify()
        for loop, (uu, vv) in zip(f.loops, ((0, 0), (sy / 4.2, 0), (sy / 4.2, 3.3), (0, 3.3))):
            loop[uvl].uv = (uu, vv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh_from_bm('TerminalGlass', bm, [M['glass']], parent=root)
    # 廊桥 ×3
    bm = bmesh.new()
    for cy in (890, 955, 1020):
        add_box(bm, 183, cy, 4.6, 24, 3.4, 3.2, 0, rot_z=0.03 * (cy - 955))
        add_cyl(bm, (176, cy, 0), (176, cy, 3.2), 0.35, 0.3, 10, 1)
        add_box(bm, 172.5, cy + 5.5, 3.4, 7, 3.0, 3.4, 0)                  # 桥头舱
    mesh_from_bm('JetBridges', bm, [M['metal'], M['wall']], parent=root)

    # ============ 塔台 ============
    bm = bmesh.new()
    add_cyl(bm, (232, 780, 0), (232, 780, 26), 5.2, 3.4, 14, 0)
    add_cyl(bm, (232, 780, 26), (232, 780, 31), 6.8, 6.2, 14, 1)          # 玻璃层
    add_cyl(bm, (232, 780, 31), (232, 780, 32.6), 6.4, 3.0, 14, 2)        # 顶帽
    add_cyl(bm, (232, 780, 32.6), (232, 780, 37), 0.12, 0.06, 6, 0)       # 避雷针
    mesh_from_bm('Tower', bm, [M['wall'], M['glass'], M['roof']], parent=root, smooth=True)

    # ============ 地勤车辆 ============
    bm = bmesh.new()
    def bus(x, y, rot):
        add_box(bm, x, y, 1.5, 2.6, 7.5, 2.6, 0, rot_z=rot)
        add_box(bm, x, y, 2.6, 2.62, 6.6, 0.7, 1, rot_z=rot)
    bus(108, 880, 0.2); bus(152, 1042, -0.15)
    add_box(bm, 168, 905, 1.8, 2.4, 9.0, 3.2, 2)                           # 加油车
    add_cyl(bm, (168, 903, 1.2), (168, 906, 1.2), 1.0, 1.0, 12, 3)        # 油罐
    add_box(bm, 128, 1020, 0.8, 1.8, 4.5, 1.4, 0)                          # 行李拖车
    mesh_from_bm('Vehicles', bm, [M['truck'], M['dark'], M['truck2'], M['metal']], parent=root)

    # ============ 风向袋 ============
    bm = bmesh.new()
    add_cyl(bm, (46, -880, 0), (46, -880, 7), 0.09, 0.07, 8, 0)
    add_cyl(bm, (46, -880, 6.9), (46 + 2.6, -880, 6.75), 0.5, 0.18, 10, 1)
    mesh_from_bm('Windsock', bm, [M['metal'], M['orange']], parent=root)

    # 导出
    for ob in bpy.data.objects:
        ob.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=OUT, export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_animations=False,
        export_materials='EXPORT', export_image_format='AUTO',
        export_texcoords=True, export_normals=True,
        export_cameras=False, export_lights=False,
        export_skins=False, export_morph=False, export_extras=False,
    )
    print('AIRPORT_EXPORTED', OUT, os.path.getsize(OUT) // 1024, 'KB')

if __name__ == '__main__':
    main()
