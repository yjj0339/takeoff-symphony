# -*- coding: utf-8 -*-
"""凌云起飞 · 宽体客机建模（A350 级）→ assets/plane.glb
坐标系：+Y 机头 / +Z 上 / +X 右舷（导出 glTF 后即 three.js 的 -Z 前方）
地面在 z = -5.68（机身轴心离地高度，A350 实际值）
命名规范供 three.js 驱动：*Pivot* 转轴, Wheel* 轮, FanPivot* 风扇,
Flap*/Slat*/Spoil* 可动翼面, Door* 舱门, Beacon/Strobe/Nav 灯锚点
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.normpath(os.path.join(HERE, '..', 'assets', 'tex'))
OUT = os.path.normpath(os.path.join(HERE, '..', 'assets', 'plane.glb'))

GROUND_Z = -5.68      # 地面（相对机身轴线）
# ---------------- 基础工具 ----------------
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

def sm(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def new_mat(name, color=(0.8, 0.8, 0.8), rough=0.4, metal=0.0, emissive=None, emiss_str=0.0):
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
    return m

def tex_mat(name, tex_file, mr_file=None, rough=0.4, metal=0.05):
    m = new_mat(name, rough=rough, metal=metal)
    nt = m.node_tree
    bsdf = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    img = bpy.data.images.load(os.path.join(TEX, tex_file))
    img.colorspace_settings.name = 'sRGB'
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img
    nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
    if mr_file:
        mimg = bpy.data.images.load(os.path.join(TEX, mr_file))
        mimg.colorspace_settings.name = 'Non-Color'
        tn2 = nt.nodes.new('ShaderNodeTexImage'); tn2.image = mimg
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(tn2.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
        nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
    return m

def world_loc(o):
    """累加 location 链得到世界位置（所有 pivot 均无旋转）"""
    v = Vector(o.location)
    p = o.parent
    while p is not None:
        v += Vector(p.location)
        p = p.parent
    return v

def mesh_from_bm(name, bm, mats, parent=None, smooth=True, local_space=False):
    """local_space=False: 顶点为世界坐标 → ob.location 抵消父级世界位移
       local_space=True : 顶点已是父坐标系局部坐标（pivot 原点建模）"""
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
        if not local_space:
            ob.location = -world_loc(parent)
    return ob

def empty_at(name, loc, parent=None):
    """loc 为世界位置（内部换算为相对父级的局部 location，链上无旋转）"""
    o = bpy.data.objects.new(name, None)
    o.empty_display_size = 0.4
    if parent is not None:
        o.parent = parent
        o.location = Vector(loc) - world_loc(parent)
    else:
        o.location = loc
    bpy.context.scene.collection.objects.link(o)
    return o

def add_cyl(bm, p0, p1, r0, r1, seg, mi):
    d = Vector(p1) - Vector(p0); L = max(0.01, d.length)
    before_v = len(bm.verts)
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=seg, radius1=r0, radius2=r1, depth=L)
    bm.verts.ensure_lookup_table()
    vs = [v for v in bm.verts[before_v:]]
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.rotate(bm, verts=vs, matrix=rot.to_matrix().to_4x4())
    bmesh.ops.translate(bm, vec=((Vector(p0) + Vector(p1)) / 2), verts=vs)
    bm.faces.ensure_lookup_table()
    after_f = len(bm.faces)
    for f in bm.faces:
        if all(v in vs for v in f.verts):
            f.material_index = mi

def cylinder_obj(name, p0, p1, r0, r1, seg, mat, parent=None):
    bm = bmesh.new()
    add_cyl(bm, p0, p1, r0, r1, seg, 0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_from_bm(name, bm, [mat], parent=parent)

def add_tube(bmx, y0, y1, r0, r1, mi, segs=24, rings=5, x=0.0, z=0.0):
    g = []
    for i in range(rings + 1):
        t = i / rings
        y = y0 + (y1 - y0) * t
        r = r0 + (r1 - r0) * t
        g.append([bmx.verts.new(Vector((x + r * math.cos(j / segs * 2 * math.pi), y,
                                        z + r * math.sin(j / segs * 2 * math.pi)))) for j in range(segs)])
    for i in range(rings):
        for j in range(segs):
            j2 = (j + 1) % segs
            f = bmx.faces.new((g[i][j], g[i][j2], g[i + 1][j2], g[i + 1][j]))
            f.material_index = mi

def flip_x(bm):
    for v in bm.verts:
        v.co.x = -v.co.x
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

# ---------------- 材质 ----------------
def build_materials():
    M = {}
    M['fus'] = tex_mat('M_Fuselage', 'fuselage.png', 'fuselage_mr.png', rough=0.4, metal=0.08)
    M['fin'] = tex_mat('M_Fin', 'fin.png', 'fin_mr.png', rough=0.4, metal=0.05)
    M['fair']  = new_mat('M_Fairing', (0.80, 0.83, 0.86), rough=0.42, metal=0.1)
    M['wingT'] = new_mat('M_WingTop', (0.82, 0.85, 0.88), rough=0.38, metal=0.15)
    M['wingB'] = new_mat('M_WingBot', (0.93, 0.95, 0.96), rough=0.4, metal=0.1)
    M['eng']   = new_mat('M_Engine', (0.88, 0.90, 0.92), rough=0.3, metal=0.2)
    M['lip']   = new_mat('M_Lip', (0.93, 0.95, 0.96), rough=0.12, metal=0.9)
    M['inner'] = new_mat('M_Inner', (0.13, 0.14, 0.15), rough=0.7, metal=0.3)
    M['blade'] = new_mat('M_Blade', (0.34, 0.36, 0.38), rough=0.35, metal=0.9)
    M['spin']  = new_mat('M_Spinner', (0.16, 0.17, 0.18), rough=0.5, metal=0.4)
    M['nozzle']= new_mat('M_Nozzle', (0.32, 0.33, 0.35), rough=0.4, metal=0.85)
    M['tire']  = new_mat('M_Tire', (0.16, 0.165, 0.17), rough=0.95, metal=0.0)
    M['hub']   = new_mat('M_Hub', (0.75, 0.77, 0.79), rough=0.2, metal=0.9)
    M['chrome']= new_mat('M_Chrome', (0.72, 0.74, 0.77), rough=0.22, metal=0.95)
    M['strut'] = new_mat('M_Strut', (0.80, 0.82, 0.85), rough=0.35, metal=0.7)
    M['glass'] = new_mat('M_Glass', (0.045, 0.06, 0.08), rough=0.06, metal=0.85)
    M['em_r']  = new_mat('M_LightRed', (0.55, 0.02, 0.02), rough=0.3, emissive=(1.0, 0.05, 0.05), emiss_str=8.0)
    M['em_g']  = new_mat('M_LightGreen', (0.02, 0.5, 0.06), rough=0.3, emissive=(0.1, 1.0, 0.2), emiss_str=8.0)
    M['em_w']  = new_mat('M_LightWhite', (0.9, 0.9, 0.9), rough=0.3, emissive=(1.0, 1.0, 0.98), emiss_str=10.0)
    M['em_warm'] = new_mat('M_LightWarm', (0.95, 0.9, 0.7), rough=0.3, emissive=(1.0, 0.95, 0.8), emiss_str=14.0)
    M['dark']  = new_mat('M_Dark', (0.12, 0.13, 0.14), rough=0.6, metal=0.2)
    M['fan_disc'] = tex_mat('M_FanDisc', 'fan_disc.png', rough=0.5, metal=0.1)
    try:
        M['fan_disc'].blend_method = 'BLEND'
    except Exception:
        pass
    return M

# ---------------- 机身 ----------------
FUS_L = 66.8
Y0 = FUS_L / 2.0
FUS_W, FUS_H = 2.98, 2.95

def fus_section(u):
    """u:0 机头尖 → 1 尾锥尖 → (width, height, center_z)"""
    if u < 0.115:
        s = sm(0.0, 1.0, u / 0.115) ** 0.45
        return FUS_W * (0.18 + 0.82 * s), FUS_H * (0.16 + 0.84 * s), 0.0
    if u < 0.70:
        b = math.sin(math.pi * (u - 0.115) / 0.585) * 0.012
        return FUS_W * (1 + b), FUS_H * (1 + b), 0.0
    t = sm(0.70, 1.0, u)
    return (FUS_W * (1 - 0.87 * t ** 1.3), FUS_H * (1 - 0.86 * t ** 1.35), 2.05 * t ** 1.8)

def fus_point(u, phi):
    w, h, cy = fus_section(u)
    P = 0.93
    sx, cz = math.sin(phi), -math.cos(phi)
    return Vector((w * math.copysign(abs(sx) ** P, sx),
                   Y0 - u * FUS_L,
                   cy - h * math.copysign(abs(cz) ** P, cz)))

def build_fuselage(M, root):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    RINGS, SEGS = 88, 32
    grid = []
    for i in range(RINGS + 1):
        u = i / RINGS
        grid.append([bm.verts.new(fus_point(u, j / SEGS * 2 * math.pi)) for j in range(SEGS)])
    for i in range(RINGS):
        for j in range(SEGS):
            j2 = (j + 1) % SEGS
            f = bm.faces.new((grid[i][j], grid[i][j2], grid[i + 1][j2], grid[i + 1][j]))
            f.material_index = 0
            uvs = ((i / RINGS, j / SEGS), (i / RINGS, j2 / SEGS),
                   ((i + 1) / RINGS, j2 / SEGS), ((i + 1) / RINGS, j / SEGS))
            for loop, (uu, vv) in zip(f.loops, uvs):
                loop[uvl].uv = (uu, vv)
    tail = bm.verts.new(fus_point(1.0, 0))
    for j in range(SEGS):
        j2 = (j + 1) % SEGS
        f = bm.faces.new((grid[RINGS][j2], tail, grid[RINGS][j])); f.material_index = 1
    nose = bm.verts.new(fus_point(0.0, 0))
    for j in range(SEGS):
        j2 = (j + 1) % SEGS
        f = bm.faces.new((nose, grid[0][j], grid[0][j2])); f.material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh_from_bm('Fuselage', bm, [M['fus'], M['dark']], parent=root)

    # 翼身整流罩：以 (0,-2.4) 为中心的下垂椭圆环，上半埋入机身
    bm = bmesh.new()
    RINGS, SEGS = 26, 24
    for i in range(RINGS):
        t = i / (RINGS - 1)
        y = 6.5 - t * 21.5
        env = math.sin(math.pi * min(1, t * 1.02)) ** 0.5
        w = 4.05 * env
        dip = 1.05 * env
        for j in range(SEGS):
            a = j / SEGS * 2 * math.pi
            bm.verts.new(Vector((w * math.sin(a), y, -2.40 + dip * math.cos(a))))
    bm.verts.ensure_lookup_table()
    for i in range(RINGS - 1):
        for j in range(SEGS):
            j2 = (j + 1) % SEGS
            f = bm.faces.new((bm.verts[i * SEGS + j], bm.verts[i * SEGS + j2],
                              bm.verts[(i + 1) * SEGS + j2], bm.verts[(i + 1) * SEGS + j]))
            f.material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh_from_bm('Fairing', bm, [M['fair']], parent=root)

# ---------------- 驾驶舱窗 ----------------
def build_cockpit(M, root):
    bm = bmesh.new()
    base_u = 0.062
    wins = [(base_u + 0.013, math.radians(56), 0.017, math.radians(15)),
            (base_u + 0.013, math.radians(304), 0.017, math.radians(15)),
            (base_u + 0.045, math.radians(49), 0.010, math.radians(11)),
            (base_u + 0.045, math.radians(311), 0.010, math.radians(11)),
            (base_u + 0.063, math.radians(46), 0.008, math.radians(9)),
            (base_u + 0.063, math.radians(314), 0.008, math.radians(9))]
    for (uc, pc, du, dp) in wins:
        pts = []
        for (su, sp) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            u, phi = uc + su * du / 2, pc + sp * dp / 2
            p = fus_point(u, phi)
            n = Vector((math.sin(phi), 0, -math.cos(phi)))
            pts.append(bm.verts.new(p + n * 0.035))
        f = bm.faces.new(pts)
        f.material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh_from_bm('CockpitGlass', bm, [M['glass']], parent=root)

# ---------------- 机翼 ----------------
X_ROOT, X_TIP = 1.7, 30.0
LE_SLOPE = math.tan(math.radians(35.0))
DIHED = math.tan(math.radians(5.5))
INCID = math.tan(math.radians(1.8))

def wing_le(x):   return 3.4 - LE_SLOPE * (x - X_ROOT)
def wing_te(x):
    if x <= 11.0: return -8.6 + (x - X_ROOT) / (11.0 - X_ROOT) * 0.4
    return -8.2 - (x - 11.0) / (X_TIP - 11.0) * 10.8
def wing_z(x):    return -1.1 + DIHED * (x - X_ROOT)
def wing_thick(x):
    s = (x - X_ROOT) / (X_TIP - X_ROOT)
    return 1.62 * (1 - 0.86 * s ** 1.05) + 0.05

def naca_thick(xc):
    return (0.2969 * math.sqrt(xc) - 0.1260 * xc - 0.3516 * xc * xc
            + 0.2843 * xc ** 3 - 0.1036 * xc ** 4)
def camber(xc, m=0.018, p=0.4):
    if xc < p:
        return m / p ** 2 * (2 * p * xc - xc * xc)
    return m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * xc - xc * xc)

def airfoil_ring(x, N=14, m=0.018, th_scale=1.0, sweep_extra=0.0, z_extra=0.0, le_shift=0.0):
    yle, yte = wing_le(x) + le_shift, wing_te(x) + le_shift
    chord = yle - yte
    z = wing_z(x) + z_extra
    th = wing_thick(x) * th_scale   # wing_thick 已是绝对厚度(米)
    up = [(0.5 * (1 - math.cos(math.pi * i / N)), +1) for i in range(N + 1)]
    dn = [(0.5 * (1 + math.cos(math.pi * i / N)), -1) for i in range(1, N)]
    pts = []
    for (xc, sgn) in up + dn:
        yt = naca_thick(xc) / 0.2 * th / 2
        yc = camber(xc, m=m) * chord
        pts.append(Vector((x, yle - chord * xc - sweep_extra * xc,
                           z + yc + sgn * yt + INCID * chord * (1 - xc) * 0.25)))
    return pts, chord

def loft_rings(bm, rings, mats_split=True):
    """rings: [[Vector,...], ...] 已 new 为 verts 的二维数组"""
    n = len(rings[0])
    for i in range(len(rings) - 1):
        for j in range(n - 1):
            f = bm.faces.new((rings[i][j], rings[i][j + 1], rings[i + 1][j + 1], rings[i + 1][j]))
            f.material_index = 0 if (mats_split and j < n // 2) else (1 if mats_split else 0)
    f = bm.faces.new(rings[-1]); f.material_index = 0
    f2 = bm.faces.new(rings[0]); f2.material_index = 0

def build_wing(M, root, side=1):
    sn = 'R' if side > 0 else 'L'
    bm = bmesh.new()
    ST = [X_ROOT + (X_TIP - X_ROOT) * (i / 12.0) ** 1.25 for i in range(13)]
    rings = []
    for x in ST:
        pts, _ = airfoil_ring(x)
        rings.append([bm.verts.new(p) for p in pts])
    loft_rings(bm, rings)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    # 翼梢小翼（向后掠+上弯）
    wb = bmesh.new()
    x0 = X_TIP
    N = 10
    grid2 = []
    for k in range(6):
        t = k / 5
        xi = x0 + t * 0.95
        yle = wing_le(x0) - 0.55 * t - 0.25 * t * t
        chord = 2.55 * (1 - 0.52 * t)
        z = wing_z(x0) + 0.12 + 1.72 * math.sin(math.radians(58) * t)
        th = 0.10 * chord + 0.06
        up = [(0.5 * (1 - math.cos(math.pi * i / N)), +1) for i in range(N + 1)]
        dn = [(0.5 * (1 + math.cos(math.pi * i / N)), -1) for i in range(1, N)]
        pts = []
        for (xc, sgn) in up + dn:
            yt = naca_thick(xc) / 0.2 * th / 2
            pts.append(Vector((xi, yle - chord * xc, z + sgn * yt)))
        grid2.append([wb.verts.new(p) for p in pts])
    loft_rings(wb, grid2)
    bmesh.ops.recalc_face_normals(wb, faces=wb.faces)

    if side < 0:
        flip_x(bm); flip_x(wb)
    mesh_from_bm(f'Wing{sn}', bm, [M['wingT'], M['wingB']], parent=root)
    mesh_from_bm(f'Winglet{sn}', wb, [M['wingT'], M['wingB']], parent=root)

# ---------------- 襟翼 / 缝翼 / 扰流板 ----------------
def build_flaps(M, root, side=1):
    sn = 'R' if side > 0 else 'L'
    # 后缘襟翼 ×2
    for (xa, xb, tag) in ((3.4, 8.6, 'In'), (13.6, 24.2, 'Out')):
        bm = bmesh.new()
        xmid = (xa + xb) / 2
        yle = wing_te(xmid) + 0.45
        ztop = wing_z(xmid) - 0.30
        chord = 1.65 if tag == 'In' else 1.45
        ring = []
        for xx in (xa, xb):
            taper = 1 - 0.14 * (xx - xa) / (xb - xa)
            c = chord * taper
            z0 = ztop - 0.10
            ring.append([bm.verts.new(Vector((xx, yle, z0 + 0.17))),
                         bm.verts.new(Vector((xx, yle - c * 0.92, z0 - c * 0.07))),
                         bm.verts.new(Vector((xx, yle - c, z0 - c * 0.14))),
                         bm.verts.new(Vector((xx, yle - c * 0.30, z0 - 0.16))),
                         bm.verts.new(Vector((xx, yle - c * 0.60, z0 - 0.05)))])
        for j in range(4):
            f = bm.faces.new([ring[0][j], ring[0][j + 1], ring[1][j + 1], ring[1][j]])
            f.material_index = 0
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if side < 0: flip_x(bm)
        piv = empty_at(f'FlapPivot{tag}{sn}', (side * xmid, yle, ztop + 0.08), parent=root)
        mesh_from_bm(f'Flap{tag}{sn}', bm, [M['wingT']], parent=piv)
    # 前缘缝翼 ×2
    for (xa, xb, tag) in ((3.4, 8.6, 'In'), (13.6, 27.6, 'Out')):
        bm = bmesh.new()
        xmid = (xa + xb) / 2
        yle = wing_le(xmid) + 0.06
        zc = wing_z(xmid) - 0.08
        c = 0.62
        ring = []
        for xx in (xa, xb):
            ring.append([bm.verts.new(Vector((xx, yle + c * 0.25, zc + 0.30))),
                         bm.verts.new(Vector((xx, yle - c * 0.35, zc + 0.27))),
                         bm.verts.new(Vector((xx, yle - c, zc + 0.04))),
                         bm.verts.new(Vector((xx, yle - c * 0.55, zc - 0.09))),
                         bm.verts.new(Vector((xx, yle + c * 0.15, zc - 0.01)))])
        for j in range(4):
            f = bm.faces.new([ring[0][j], ring[0][j + 1], ring[1][j + 1], ring[1][j]])
            f.material_index = 0
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if side < 0: flip_x(bm)
        piv = empty_at(f'SlatPivot{tag}{sn}', (side * xmid, yle, zc), parent=root)
        mesh_from_bm(f'Slat{tag}{sn}', bm, [M['wingB']], parent=piv)
    # 扰流板 ×5
    for i in range(5):
        xa = 4.2 + i * 4.4; xb = xa + 3.4
        xmid = (xa + xb) / 2
        yle = wing_te(xmid) + 2.35
        yte = yle + 0.95
        zt = wing_z(xmid) + 0.235
        bm = bmesh.new()
        r0 = [bm.verts.new(p) for p in (Vector((xa, yle, zt + 0.05)), Vector((xa, yte, zt + 0.10)),
              Vector((xa, yte + 0.05, zt - 0.04)), Vector((xa, yle + 0.05, zt - 0.02)))]
        r1 = [bm.verts.new(p) for p in (Vector((xb, yle, zt + 0.05)), Vector((xb, yte, zt + 0.10)),
              Vector((xb, yte + 0.05, zt - 0.04)), Vector((xb, yle + 0.05, zt - 0.02)))]
        for j in range(3):
            f = bm.faces.new([r0[j], r0[j + 1], r1[j + 1], r1[j]]); f.material_index = 0
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if side < 0: flip_x(bm)
        piv = empty_at(f'SpoilPivot{i+1}{sn}', (side * xmid, yle, zt + 0.05), parent=root)
        mesh_from_bm(f'Spoil{i+1}{sn}', bm, [M['wingT']], parent=piv)

# ---------------- 发动机 ----------------
def build_engine(M, root, side=1):
    sn = 'R' if side > 0 else 'L'
    XE = 11.4
    YE = wing_le(XE) + 0.6
    ZE = -3.30
    eng = empty_at(f'EngineMount{sn}', (side * XE, YE, ZE), parent=root)

    def shell_r(u):
        r = 1.42 + 0.36 * sm(0.0, 0.10, u) ** 0.8      # 唇口鼓出
        r -= 0.76 * sm(0.55, 1.0, u) ** 1.4            # 尾段收细
        return r                                        # 0:1.42 → 0.10:1.78 → 1:1.02

    bm = bmesh.new()
    RINGS, SEGS = 34, 28
    for i in range(RINGS + 1):
        u = i / RINGS
        y = 3.8 - u * 7.6
        r = shell_r(u)
        for j in range(SEGS):
            a = j / SEGS * 2 * math.pi
            bm.verts.new(Vector((r * math.cos(a), y, r * math.sin(a))))
    bm.verts.ensure_lookup_table()
    for i in range(RINGS):
        for j in range(SEGS):
            j2 = (j + 1) % SEGS
            f = bm.faces.new((bm.verts[i * SEGS + j], bm.verts[i * SEGS + j2],
                              bm.verts[(i + 1) * SEGS + j2], bm.verts[(i + 1) * SEGS + j]))
            f.material_index = 1 if (i / RINGS) < 0.075 else 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bi = bmesh.new()
    add_tube(bi, 3.30, -2.2, 1.40, 0.86, 0)
    bmesh.ops.recalc_face_normals(bi, faces=bi.faces)
    bn = bmesh.new()
    add_tube(bn, -2.35, -4.15, 1.02, 0.72, 0)
    add_tube(bn, -2.4, -4.3, 0.02, 0.42, 0, segs=18)
    bmesh.ops.recalc_face_normals(bn, faces=bn.faces)

    if side < 0:
        flip_x(bm); flip_x(bi); flip_x(bn)
    mesh_from_bm(f'Nacelle{sn}', bm, [M['eng'], M['lip']], parent=eng, local_space=True)
    mesh_from_bm(f'EngineDuct{sn}', bi, [M['eng'], M['inner']], parent=eng, local_space=True)
    mesh_from_bm(f'Nozzle{sn}', bn, [M['nozzle']], parent=eng, local_space=True)

    # 风扇（pivot 旋转）
    fan = empty_at(f'FanPivot{sn}', (side * XE, YE, ZE), parent=eng)
    bf = bmesh.new()
    add_tube(bf, 2.68, 1.85, 0.02, 0.46, 0, segs=20, rings=6)
    NB = 22
    for b in range(NB):
        ang = b / NB * 2 * math.pi
        seg_verts = []
        for k in range(7):
            t = k / 6
            rr = 0.48 + t * 1.00
            twist = math.radians(50 - 34 * t)
            sweep = 0.32 * t ** 1.6
            chord = 0.44 - 0.13 * t
            tang = Vector((-math.sin(ang), 0, math.cos(ang)))
            radial = Vector((math.cos(ang), 0, math.sin(ang)))
            center = Vector((math.cos(ang) * rr, 2.40 - t * 0.55 - sweep, math.sin(ang) * rr))
            rot = Matrix.Rotation(twist, 4, radial.normalized())
            p_le = rot @ (-tang * chord / 2) + center
            p_te = rot @ (tang * chord / 2) + center
            seg_verts.append((bf.verts.new(p_le), bf.verts.new(p_te)))
        for k in range(6):
            a0, a1 = seg_verts[k]; b0, b1 = seg_verts[k + 1]
            f = bf.faces.new((a0, a1, b1, b0))
            f.material_index = 1
    bmesh.ops.recalc_face_normals(bf, faces=bf.faces)
    if side < 0: flip_x(bf)
    mesh_from_bm(f'Fan{sn}', bf, [M['spin'], M['blade']], parent=fan, local_space=True)

    # 模糊盘（three 高速切换）
    bd = bmesh.new()
    bmesh.ops.create_grid(bd, x_segments=4, y_segments=4, size=1.0)
    bmesh.ops.scale(bd, vec=(1.44, 1.44, 1), verts=bd.verts)
    bmesh.ops.rotate(bd, verts=bd.verts, matrix=Matrix.Rotation(math.radians(90), 4, 'X'))
    bmesh.ops.translate(bd, vec=(0, 2.35, 0), verts=bd.verts)
    if side < 0: flip_x(bd)
    dob = mesh_from_bm(f'FanDisc{sn}', bd, [M['fan_disc']], parent=fan, local_space=True)

    # 吊挂
    bp = bmesh.new()
    zp = wing_z(XE) - 0.5
    prof0 = [Vector((XE - 0.40, YE + 3.3, ZE + 1.30)), Vector((XE - 0.28, YE + 3.3, ZE + 1.74)),
             Vector((XE + 0.28, YE + 2.1, ZE + 1.72)), Vector((XE + 0.40, YE + 0.9, ZE + 1.52)),
             Vector((XE + 0.40, YE + 0.5, ZE + 1.18)), Vector((XE - 0.40, YE + 0.5, ZE + 1.02))]
    prof1 = [Vector((XE - 0.28, YE + 1.9, zp + 1.10)), Vector((XE - 0.20, YE + 1.9, zp + 1.30)),
             Vector((XE + 0.20, YE + 1.5, zp + 1.26)), Vector((XE + 0.28, YE + 0.3, zp + 1.05)),
             Vector((XE + 0.28, YE - 0.5, zp + 0.50)), Vector((XE - 0.28, YE - 0.5, zp + 0.42))]
    v0 = [bp.verts.new(p) for p in prof0]
    v1 = [bp.verts.new(p) for p in prof1]
    for j in range(5):
        bp.faces.new([v0[j], v0[j + 1], v1[j + 1], v1[j]])
    bmesh.ops.recalc_face_normals(bp, faces=bp.faces)
    if side < 0: flip_x(bp)
    mesh_from_bm(f'Pylon{sn}', bp, [M['strut']], parent=eng)

# ---------------- 尾翼 ----------------
def build_empennage(M, root):
    # 垂尾（贴图）
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    ST = [(0.0, 2.45, -21.4, -30.55), (0.35, 5.6, -23.9, -29.9),
          (0.7, 9.2, -26.2, -29.5), (1.0, 12.85, -28.3, -29.3)]
    N = 12
    def fin_row(t, z, yle, yte):
        chord = yle - yte
        th = 0.10 * chord + 0.04
        up = [(0.5 * (1 - math.cos(math.pi * i / N)), +1) for i in range(N + 1)]
        dn = [(0.5 * (1 + math.cos(math.pi * i / N)), -1) for i in range(1, N)]
        pts = []
        for (xc, sgn) in up + dn:
            yt = naca_thick(xc) / 0.2 * th / 2
            pts.append(Vector((sgn * yt, yle - chord * xc - 0.35 * xc, z + (1 - xc) * 0.30)))
        return pts
    rows_t = ST
    rows = [fin_row(*st) for st in ST]
    fine = [rows[0]]
    fine_t = [ST[0][0]]
    for i in range(len(rows) - 1):
        for k in (0.34, 0.67):
            fine.append([rows[i][j].lerp(rows[i + 1][j], k) for j in range(len(rows[i]))])
            fine_t.append(ST[i][0] + (ST[i + 1][0] - ST[i][0]) * k)
        fine.append(rows[i + 1]); fine_t.append(ST[i + 1][0])
    n = 2 * N
    vr = [[bm.verts.new(p) for p in row] for row in fine]
    def uv_u(j):
        if j <= N:
            return 0.12 + 0.34 * (j / N)          # 上表面 LE→TE
        xc = 0.5 * (1 + math.cos(math.pi * (j - N) / N))
        return 0.54 + 0.34 * xc                   # 下表面 TE→LE
    for i in range(len(vr) - 1):
        for j in range(n - 1):
            f = bm.faces.new((vr[i][j], vr[i][j + 1], vr[i + 1][j + 1], vr[i + 1][j]))
            f.material_index = 0
            v0 = 0.04 + 0.92 * (i / (len(vr) - 1))
            v1 = 0.04 + 0.92 * ((i + 1) / (len(vr) - 1))
            for loop, (uu, vv) in zip(f.loops, ((uv_u(j), v0), (uv_u(j + 1), v0),
                                                (uv_u(j + 1), v1), (uv_u(j), v1))):
                loop[uvl].uv = (uu, vv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh_from_bm('VerticalStab', bm, [M['fin']], parent=root)

    # 平尾
    for side in (1, -1):
        sn = 'R' if side > 0 else 'L'
        bm = bmesh.new()
        ST2 = [(0.6, 0.92, -26.4, -31.0), (5.2, 1.0, -28.4, -30.6), (10.4, 1.35, -30.3, -30.3)]
        N = 10
        rows = []
        for (xx, z, yle, yte) in ST2:
            chord = yle - yte
            th = 0.09 * chord + 0.03
            up = [(0.5 * (1 - math.cos(math.pi * i / N)), +1) for i in range(N + 1)]
            dn = [(0.5 * (1 + math.cos(math.pi * i / N)), -1) for i in range(1, N)]
            pts = []
            for (xc, sgn) in up + dn:
                yt = naca_thick(xc) / 0.2 * th / 2
                pts.append(Vector((side * xx, yle - chord * xc, z + sgn * yt + (1 - xc) * 0.18)))
            rows.append(pts)
        fine = [rows[0]]
        for i in range(len(rows) - 1):
            for k in (0.36, 0.7):
                fine.append([rows[i][j].lerp(rows[i + 1][j], k) for j in range(len(rows[i]))])
            fine.append(rows[i + 1])
        vr = [[bm.verts.new(p) for p in row] for row in fine]
        loft_rings(bm, vr)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh_from_bm(f'HStab{sn}', bm, [M['wingT'], M['wingB']], parent=root)

# ---------------- 起落架 ----------------
def add_wheel(bm, r, w, hub_r, mi_tire, mi_hub, seg=22):
    # 轮轴沿 X：create_cone 默认 +Z → 绕 Y 转 90°
    def _cone(rr, ww, mi):
        before_v = len(bm.verts)
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=seg, radius1=rr, radius2=rr, depth=ww)
        bm.verts.ensure_lookup_table()
        vs = [v for v in bm.verts[before_v:]]
        bmesh.ops.rotate(bm, verts=vs, matrix=Matrix.Rotation(math.radians(90), 4, 'Y'))
        vs_set = set(vs)
        for f in bm.faces:
            if all(v in vs_set for v in f.verts):
                f.material_index = mi
    _cone(r, w, mi_tire)
    _cone(hub_r, w * 1.14, mi_hub)

def build_gear(M, root):
    # ===== 前起落架（y=前后 NY=24，z=高度）=====
    NY = 24.0
    AXLE_Z = GROUND_Z + 0.555          # -5.125 前轮轴高度
    gp = empty_at('GearNPivot', (0, NY + 0.5, -2.60), parent=root)
    steer = empty_at('NoseSteerPivot', (0, NY, -2.60), parent=gp)
    bm = bmesh.new()
    add_cyl(bm, (0, NY, -2.50), (0, NY, AXLE_Z + 0.02), 0.10, 0.10, 14, 0)          # 主支柱(竖直向下)
    add_cyl(bm, (0, NY + 0.05, -2.50), (0, NY - 0.9, -2.58), 0.19, 0.155, 14, 1)    # 上段加粗
    add_cyl(bm, (0.15, NY - 0.5, -2.58), (0.13, NY - 1.9, -2.90), 0.055, 0.055, 10, 0)
    add_cyl(bm, (0.13, NY - 1.9, -2.90), (0.11, NY - 3.2, -3.30), 0.05, 0.05, 10, 0)  # 扭力臂
    add_cyl(bm, (0.16, NY + 0.35, -2.30), (0.30, NY - 1.2, -2.62), 0.04, 0.04, 10, 2) # 转向作动筒
    add_cyl(bm, (-0.46, NY, AXLE_Z), (0.46, NY, AXLE_Z), 0.075, 0.075, 10, 1)       # 轮轴
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh_from_bm('NoseStrut', bm, [M['chrome'], M['strut'], M['dark']], parent=steer)
    for sx, nm in ((-1, 'L'), (1, 'R')):
        wp = empty_at(f'WheelN{nm}', (sx * 0.30, NY, AXLE_Z), parent=steer)
        bwm = bmesh.new()
        add_wheel(bwm, 0.555, 0.30, 0.36, 0, 1)
        bmesh.ops.recalc_face_normals(bwm, faces=bwm.faces)
        mesh_from_bm(f'NoseWheel{nm}', bwm, [M['tire'], M['hub']], parent=wp, local_space=True)
    # 前着陆灯（支柱前侧）
    lb = bmesh.new()
    before_v = len(lb.verts)
    bmesh.ops.create_icosphere(lb, subdivisions=1, radius=0.08)
    lb.verts.ensure_lookup_table()
    vs = [v for v in lb.verts[before_v:]]
    bmesh.ops.translate(lb, vec=(0.30, NY - 2.0, -2.70), verts=vs)
    for f in lb.faces: f.material_index = 0
    bmesh.ops.recalc_face_normals(lb, faces=lb.faces)
    mesh_from_bm('GearLightN', lb, [M['em_warm']], parent=steer)
    # 前舱门（左右, 铰链 Y 轴）
    for sx, nm in ((-1, 'L'), (1, 'R')):
        dp = empty_at(f'DoorNPivot{nm}', (sx * 0.55, NY + 2.0, -2.75), parent=root)
        dbm = bmesh.new()
        bmesh.ops.create_cube(dbm, size=1.0)
        bmesh.ops.scale(dbm, vec=(0.04, 3.6, 1.15), verts=dbm.verts)
        bmesh.ops.translate(dbm, vec=(sx * 0.60, NY, -3.05), verts=dbm.verts)
        bmesh.ops.recalc_face_normals(dbm, faces=dbm.faces)
        mesh_from_bm(f'GearDoorN{nm}', dbm, [M['strut']], parent=dp)

    # ===== 主起落架 ×2 =====
    MY = -2.4
    MAXLE_Z = GROUND_Z + 0.625         # -5.055 主轮轴高度
    for side, sn in ((1, 'R'), (-1, 'L')):
        gpM = empty_at(f'GearM{sn}Pivot', (side * 3.6, MY, -2.80), parent=root)
        bm = bmesh.new()
        add_cyl(bm, (side * 3.6, MY, -2.76), (side * 3.6, MY, MAXLE_Z + 0.30), 0.13, 0.13, 14, 0)  # 主支柱
        add_cyl(bm, (side * 3.6, MY + 0.05, -2.74), (side * 3.6, MY - 0.6, -2.82), 0.22, 0.175, 14, 1)
        add_cyl(bm, (side * 3.6, MY - 0.5, -2.88), (side * 2.2, MY + 0.6, -3.30), 0.06, 0.06, 10, 2)  # 侧撑杆
        add_cyl(bm, (side * 3.6, MY + 0.5, -2.58), (side * 2.0, MY + 1.1, -2.95), 0.055, 0.055, 10, 2)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh_from_bm(f'MainStrut{sn}', bm, [M['chrome'], M['strut'], M['dark']], parent=gpM)
        bp = empty_at(f'BogieM{sn}', (side * 3.6, MY, MAXLE_Z + 0.30), parent=gpM)
        bm = bmesh.new()
        add_cyl(bm, (0, 0.30, 0), (0, -0.30, 0), 0.085, 0.085, 10, 0)                # bogie 纵梁(局部)
        add_cyl(bm, (-0.46, 0.30, 0), (0.46, 0.30, 0), 0.08, 0.08, 10, 0)
        add_cyl(bm, (-0.46, -0.30, 0), (0.46, -0.30, 0), 0.08, 0.08, 10, 0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh_from_bm(f'BogieFrame{sn}', bm, [M['chrome']], parent=bp, local_space=True)
        for (ox, oy, i) in ((-0.46, 0.30, 1), (0.46, 0.30, 2), (-0.46, -0.30, 3), (0.46, -0.30, 4)):
            wp = empty_at(f'WheelM{sn}{i}', (side * 3.6 + ox, MY + oy, MAXLE_Z + 0.30), parent=bp)
            bwm = bmesh.new()
            add_wheel(bwm, 0.625, 0.34, 0.385, 0, 1)
            bmesh.ops.recalc_face_normals(bwm, faces=bwm.faces)
            mesh_from_bm(f'MainWheel{sn}{i}', bwm, [M['tire'], M['hub']], parent=wp, local_space=True)
        # 主舱门
        dp = empty_at(f'DoorM{sn}Pivot', (side * 3.6, MY + 1.7, -3.35), parent=root)
        dbm = bmesh.new()
        bmesh.ops.create_cube(dbm, size=1.0)
        bmesh.ops.scale(dbm, vec=(1.15, 3.6, 0.05), verts=dbm.verts)
        bmesh.ops.translate(dbm, vec=(side * 3.6, MY - 0.3, -3.46), verts=dbm.verts)
        bmesh.ops.recalc_face_normals(dbm, faces=dbm.faces)
        mesh_from_bm(f'GearDoorM{sn}', dbm, [M['strut']], parent=dp)

# ---------------- 灯光 ----------------
def build_lights(M, root):
    xt, zt = 30.8, wing_z(X_TIP) + 1.85
    ylt = wing_le(X_TIP) - 0.55
    spec = [((0, 6.0, 3.02), 0.10, 0), ((0, -6.0, -3.0), 0.10, 0),           # 防撞红
            ((-xt, ylt - 0.7, zt - 0.05), 0.075, 1),                          # 左航行红
            ((xt, ylt - 0.7, zt - 0.05), 0.075, 2),                           # 右航行绿
            ((-xt, ylt - 1.45, zt - 0.22), 0.06, 3), ((xt, ylt - 1.45, zt - 0.22), 0.06, 3),  # 频闪白
            ((0, -33.35, 1.90), 0.07, 3),                                     # 尾白灯
            ((-2.9, 7.5, -3.42), 0.11, 4), ((2.9, 7.5, -3.42), 0.11, 4),      # 着陆灯
            ((0, -30.8, -2.98), 0.15, 5)]                                     # 尾橇
    bm = bmesh.new()
    for (c, r, mi) in spec:
        before_v = len(bm.verts)
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
        bm.verts.ensure_lookup_table()
        vs = [v for v in bm.verts[before_v:]]
        bmesh.ops.translate(bm, vec=Vector(c), verts=vs)
        vs_set = set(vs)
        for f in bm.faces:
            if all(v in vs_set for v in f.verts):
                f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh_from_bm('AircraftLights', bm,
                 [M['em_r'], M['em_r'], M['em_g'], M['em_w'], M['em_warm'], M['dark']], parent=root)
    empty_at('BeaconTop', (0, 6.0, 3.05), parent=root)
    empty_at('BeaconBottom', (0, -6.0, -3.05), parent=root)
    empty_at('StrobeL', (-xt, ylt - 1.45, zt - 0.22), parent=root)
    empty_at('StrobeR', (xt, ylt - 1.45, zt - 0.22), parent=root)

# ---------------- 细节 ----------------
def build_details(M, root):
    for (y, z, h) in ((16.0, 3.0, 0.42), (-14.0, 3.0, 0.38), (10.0, -3.0, 0.34), (-9.0, -3.05, 0.34)):
        bm = bmesh.new()
        before_v = 0
        bmesh.ops.create_cone(bm, cap_ends=False, cap_tris=False, segments=4, radius1=0.16, radius2=0.03, depth=h)
        bm.verts.ensure_lookup_table()
        vs = [v for v in bm.verts[before_v:]]
        bmesh.ops.scale(bm, vec=(0.35, 1, 1), verts=vs)
        bmesh.ops.translate(bm, vec=(0, y, z + h * 0.15), verts=vs)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh_from_bm(f'Antenna{y:+.0f}', bm, [M['dark']], parent=root)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.05, 0.5, 0.30), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, -28.2, 13.02), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh_from_bm('AntennaHF', bm, [M['dark']], parent=root)
    for sx in (1, -1):
        cylinder_obj(f'Pitot{"R" if sx > 0 else "L"}',
                     (sx * 0.72, 30.8, -0.30), (sx * 1.05, 31.35, -0.22), 0.022, 0.016, 8, M['dark'], parent=root)
    for (y, z) in ((2.0, -2.99), (-3.0, -2.99), (20.0, -2.98)):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.3, 0.5, 0.12), verts=bm.verts)
        bmesh.ops.translate(bm, vec=(0, y, z), verts=bm.verts)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh_from_bm(f'BellyBump{y:+.0f}', bm, [M['fair']], parent=root)

# ---------------- 主流程 ----------------
def main():
    clean_scene()
    M = build_materials()
    root = empty_at('Aircraft', (0, 0, 0))
    build_fuselage(M, root)
    build_cockpit(M, root)
    for side in (1, -1):
        build_wing(M, root, side)
        build_flaps(M, root, side)
        build_engine(M, root, side)
    build_empennage(M, root)
    build_gear(M, root)
    build_lights(M, root)
    build_details(M, root)

    bpy.ops.object.select_all(action='DESELECT')
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
    print('PLANE_EXPORTED', OUT, os.path.getsize(OUT) // 1024, 'KB')

if __name__ == '__main__':
    main()
