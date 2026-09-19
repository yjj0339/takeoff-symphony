# -*- coding: utf-8 -*-
"""诊断 plane.glb：每个对象的尺寸/位置/父级/顶点数"""
import bpy, os, sys

GLB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'plane.glb'))
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=GLB)
bpy.context.view_layer.update()   # 强制刷新全矩阵，否则嵌套对象读到局部矩阵

rows = []
for ob in bpy.data.objects:
    if ob.type != 'MESH':
        rows.append((ob.name, 'EMPTY', ob.parent.name if ob.parent else '-', '', '', ''))
        continue
    me = ob.data
    n_v = len(me.vertices)
    ws = [ob.matrix_world @ v.co for v in me.vertices]
    xs = [v.x for v in ws]; ys = [v.y for v in ws]; zs = [v.z for v in ws]
    size = (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
    ctr = ((max(xs)+min(xs))/2, (max(ys)+min(ys))/2, (max(zs)+min(zs))/2)
    rows.append((ob.name, n_v, ob.parent.name if ob.parent else '-',
                 'x%7.2f y%7.2f z%7.2f' % size, '(%6.1f,%6.1f,%6.1f)' % ctr, ''))
for r in sorted(rows, key=lambda r: r[0]):
    print('%-22s %-7s parent=%-18s size=%s ctr=%s' % (r[0], r[1], r[2], r[3], r[4]))
