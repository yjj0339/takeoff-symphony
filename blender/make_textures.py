# -*- coding: utf-8 -*-
"""凌云起飞 · 贴图工厂  →  输出到 assets/tex/
机身贴图坐标约定（与 build_plane.py 放样 UV 配套）:
  贴图 X = UV.u = 沿机身长度（0=机头, 1=尾锥）
  贴图 Y = 图片坐标;  环向角 φ: 0=腹部(图底) 90°=右舷(图 y=0.75H) 180°=机背(图 y=0.5H) 270°=左舷(图 y=0.25H)
  左舷区域(图上半) 的文字需镜像绘制。
"""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, '..', 'assets', 'tex'))
os.makedirs(OUT, exist_ok=True)
random.seed(20260919); np.random.seed(20260919)

FONT_HEI = "C:/Windows/Fonts/msyhbd.ttc"
FONT_SONG = "C:/Windows/Fonts/msyh.ttc"

def font(path, size):
    try: return ImageFont.truetype(path, size)
    except Exception: return ImageFont.load_default()

# ---------------- 噪声工具 ----------------
def fbm(w, h, octaves=4, seed=0):
    rng = np.random.default_rng(seed)
    freq_acc = np.zeros((h, w), np.float32); amp_acc = 0.0
    for o in range(octaves):
        f = 2 ** o; amp = 0.55 ** o
        gw, gh = max(2, w // (32 * f) * 2), max(2, h // (32 * f) * 2)
        grid = rng.random((gh, gw)).astype(np.float32)
        # 双线性放大
        yi = (np.arange(h) * (gh - 1) / max(1, h - 1)).astype(np.float32)
        xi = (np.arange(w) * (gw - 1) / max(1, w - 1)).astype(np.float32)
        y0 = np.floor(yi).astype(int); x0 = np.floor(xi).astype(int)
        y1 = np.minimum(y0 + 1, gh - 1); x1 = np.minimum(x0 + 1, gw - 1)
        fy = yi - y0; fx = xi - x0
        fy = fy[:, None]; fx = fx[None, :]
        a = grid[np.ix_(y0, x0)]; b = grid[np.ix_(y0, x1)]
        c = grid[np.ix_(y1, x0)]; d = grid[np.ix_(y1, x1)]
        layer = (a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy)
        freq_acc += layer * amp; amp_acc += amp
    return freq_acc / amp_acc

def to_img(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))

# ---------------- 1. 机身涂装 4096x2048 ----------------
W, H = 4096, 2048
img = Image.new("RGB", (W, H), (245, 248, 250))
d = ImageDraw.Draw(img)

def ry(v_phi):  # 环向归一化 φ(0腹→0.5背) → 图 y
    return int((1 - v_phi) * H)

# --- 底色渐变（腹部浅灰） ---
grad = np.linspace(0, 1, H, dtype=np.float32)[:, None]
belly_top = 0.135; belly_soft = 0.06
belly_mask = np.clip((belly_top - np.minimum(grad, 1 - grad)) / belly_soft + 1, 0, 1)  # 上下边缘
base = np.zeros((H, W, 3), np.float32)
white = np.array([0.961, 0.973, 0.980]); grey = np.array([0.785, 0.808, 0.828])
for c in range(3):
    base[:, :, c] = white[c] * (1 - belly_mask) + grey[c] * belly_mask
# 轻微珍珠环境色（上部略偏暖）
warm = np.array([1.0, 0.985, 0.965]); cool = np.array([0.965, 0.985, 1.0])
tt = np.clip((grad - 0.35) / 0.3, 0, 1)
for c in range(3):
    base[:, :, c] *= (cool[c] * (1 - tt) + warm[c] * tt)[:, 0][:, None] if False else 1
img = to_img(base); d = ImageDraw.Draw(img)

# --- 雷达罩（机头段） ---
NOSE_U = 0.033
d.rectangle([0, 0, int(NOSE_U * W), H], fill=(216, 221, 224))
d.line([(int(NOSE_U * W), 0), (int(NOSE_U * W), H)], fill=(60, 70, 78), width=4)

# --- 主飘带（天青→深青蓝渐变，双舷对称）---
# 环向方位（v=φ/2π, 图y=(1-v)*H）：右舷水平线 y=0.75H、左舷水平线 y=0.25H
# 窗带在舷侧偏上：右舷 y≈0.817H(φ66°)、左舷 y≈0.183H(φ294°)
# 飘带在窗带下方(靠机腹)：右舷中心 y≈0.70H、左舷 y≈0.30H
def ribbon(side):  # side: 'R' 右舷 / 'L' 左舷
    ov = Image.new("L", (W, H), 0); od = ImageDraw.Draw(ov)
    mid = 0.700 * H if side == 'R' else 0.300 * H
    sgn = 1 if side == 'R' else -1
    pts_top, pts_bot = [], []
    for i in range(0, W + 8, 8):
        u = i / W
        if u < 0.035: continue
        rise = 0.030 * ((u - 0.05) / 0.95) ** 2 * 4  # 后段上挑(向舷侧水平线方向)
        taper = 1.0 - 0.55 * max(0, (u - 0.55) / 0.45) ** 1.3
        halfw = 0.040 * H * taper
        cy = mid - sgn * rise * H
        pts_top.append((i, cy - halfw)); pts_bot.append((i, cy + halfw))
    if pts_top:
        od.polygon(pts_top + pts_bot[::-1], fill=255)
    return ov.filter(ImageFilter.GaussianBlur(2))

for side in ('R', 'L'):
    ov = ribbon(side)
    # 渐变色带（沿 u：天青→深青蓝）
    strip = np.zeros((H, W, 3), np.float32)
    c1 = np.array([77, 179, 232]); c2 = np.array([26, 105, 172])
    u = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    tt = np.clip((u - 0.05) / 0.75, 0, 1) ** 1.15
    for c in range(3):
        strip[:, :, c] = (c1[c] * (1 - tt) + c2[c] * tt)
    strip_img = Image.fromarray(np.clip(strip, 0, 255).astype(np.uint8))
    img.paste(strip_img, (0, 0), ov)
    # 橙色伴随细线（飘带下缘=靠机腹一侧）
    line_layer = Image.new("RGB", (W, H), (255, 158, 88))
    mask2 = Image.new("L", (W, H), 0); md = ImageDraw.Draw(mask2)
    arr_ov = np.array(ov)
    belly_dir = 1 if side == 'R' else -1   # 右舷下缘 y 更大；左舷下缘 y 更小
    for i in range(0, W, 4):
        col = np.where(arr_ov[:, i] > 40)[0]
        if len(col):
            yb = col[-1] if belly_dir > 0 else col[0]
            md.line([(i, yb + belly_dir * 7), (i + 4, yb + belly_dir * 7)], fill=255, width=9)
    img.paste(line_layer, (0, 0), mask2)

# --- 舷窗带（右舷 y=0.817H / 左舷 y=0.183H）---
def window_band(yc):
    door_u = [0.163, 0.475, 0.775]
    wx = int(0.15 * W)
    while wx < 0.815 * W:
        u = wx / W
        if any(abs(u - du) * W < 55 for du in door_u):
            wx += 46; continue
        lit = random.random() < 0.16
        col = (255, 233, 176) if lit else (36, 50, 64)
        d.rounded_rectangle([wx, yc - 12, wx + 17, yc + 12], radius=7, fill=col,
                            outline=(180, 190, 198), width=1)
        wx += 43

Y_R, Y_L = int(0.817 * H), int(0.183 * H)
window_band(Y_R)
window_band(Y_L)

# --- 舱门（3 对，跨窗带） ---
def doors(yc):
    for du in (0.163, 0.475, 0.775):
        x0 = du * W - 34; x1 = du * W + 34
        y0, y1 = yc - 112, yc + 112
        d.rounded_rectangle([x0, y0, x1, y1], radius=18, outline=(168, 178, 186), width=3)
        d.rounded_rectangle([x0 + 5, y0 + 5, x1 - 5, y1 - 5], radius=14, outline=(205, 212, 218), width=2)
        d.line([(x0 + 24, yc), (x0 + 44, yc)], fill=(120, 132, 142), width=4)
        d.ellipse([x0 + 20, yc - 4, x0 + 28, yc + 4], fill=(90, 100, 110))

doors(Y_R); doors(Y_L)
# 货舱门（右前腹 y=0.60H / 左后腹 y=0.41H）
d.rounded_rectangle([0.335 * W, 0.600 * H, 0.335 * W + 120, 0.600 * H + 78], radius=8, outline=(168, 178, 186), width=3)
d.rounded_rectangle([0.62 * W, 0.388 * H, 0.62 * W + 120, 0.388 * H + 78], radius=8, outline=(168, 178, 186), width=3)

# --- 文字 ---
def draw_text(txt, fnt, cx, cy, fill, mirror=False, anchor="mm"):
    if mirror:
        tmp = Image.new("RGBA", (int(W / 2), int(H / 2)), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        td.text((tmp.width / 2 if anchor == "mm" else 20, tmp.height / 2), txt, font=fnt, fill=fill, anchor="mm")
        tmp = tmp.transpose(Image.FLIP_LEFT_RIGHT)
        img.paste(tmp.crop(tmp.getbbox() or (0, 0, 1, 1)) if False else tmp, (int(cx - tmp.width / 2), int(cy - tmp.height / 2)), tmp)
    else:
        d.text((cx, cy), txt, font=fnt, fill=fill, anchor=anchor)

f_title = font(FONT_HEI, 92)
f_cn    = font(FONT_HEI, 54)
f_reg_s = font(FONT_HEI, 44)
f_reg   = font(FONT_HEI, 96)
NAVY = (22, 67, 111)

# 右舷（y≈0.84-0.86H 窗带上沿）→ 观察视角镜像 → 需镜像绘制
draw_text("SKYLINE AIR", f_title, 0.245 * W, 0.868 * H, NAVY, mirror=True)
draw_text("凌云航空", f_cn, 0.128 * W, 0.868 * H, NAVY, mirror=True)
draw_text("B-2026", f_reg_s, 0.205 * W, 0.775 * H, NAVY, mirror=True)
draw_text("B-2026", f_reg,   0.735 * W, 0.858 * H, NAVY, mirror=True)
# 左舷（y≈0.14-0.17H）正常字
draw_text("SKYLINE AIR", f_title, 0.245 * W, 0.132 * H, NAVY)
draw_text("凌云航空", f_cn, 0.128 * W, 0.132 * H, NAVY)
draw_text("B-2026", f_reg_s, 0.205 * W, 0.225 * H, NAVY)
draw_text("B-2026", f_reg,   0.735 * W, 0.142 * H, NAVY)

# --- 面板缝线 + 微细节 ---
lines = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lines)
for x in range(int(0.05 * W), int(0.97 * W), 112):
    ld.line([(x, 0.16 * H), (x, 0.84 * H)], fill=(120, 132, 140, 26), width=2)
for yy in (Y_R - 46, Y_R + 46, Y_L - 46, Y_L + 46):
    ld.line([(0.06 * W, yy), (0.86 * W, yy)], fill=(120, 132, 140, 22), width=2)
# 检修口（舷侧偏腹）
for (mx, my, mw, mh) in ((0.30 * W, 0.615 * H, 46, 34), (0.52 * W, 0.395 * H, 40, 30),
                          (0.66 * W, 0.605 * H, 52, 36), (0.24 * W, 0.405 * H, 38, 28)):
    ld.rounded_rectangle([mx, my, mx + mw, my + mh], radius=6, outline=(140, 150, 158, 90), width=2)
img = Image.alpha_composite(img.convert("RGBA"), lines).convert("RGB")

# --- 表面微噪声（喷漆颗粒） ---
noise = fbm(W // 4, H // 4, 4, seed=7)
noise = np.array(Image.fromarray((noise * 255).astype(np.uint8)).resize((W, H)), np.float32) / 255.0
arr = np.array(img, np.float32)
arr += (noise[:, :, None] - 0.5) * 7
img = to_img(arr / 255.0)

img.save(os.path.join(OUT, "fuselage.png"))

# --- 机身 metallic-roughness（G=roughness, B=metallic）---
mr = np.full((H, W, 3), 255, np.uint8)
mr[:, :, 1] = 100  # rough ~0.39 白漆
mr[:, :, 2] = 26   # metal 0.1
# 窗户更亮更金属
win_mask = (np.array(img)[:, :, 1] < 70) & (np.array(img)[:, :, 2] < 90)
mr[win_mask, 1] = 22; mr[win_mask, 2] = 215
# 深色飘带略光滑
band_mask = (np.array(img)[:, :, 2] > 100) & (np.array(img)[:, :, 0] < 120)
mr[band_mask, 1] = 80
Image.fromarray(mr).save(os.path.join(OUT, "fuselage_mr.png"))

# ---------------- 2. 垂尾 1024x1024 ----------------
FW, FH = 1024, 1024
fim = Image.new("RGB", (FW, FH), (248, 250, 251)); fd = ImageDraw.Draw(fim)

def fin_art(x_mirror):
    """x_mirror=False → 右面(x 0~0.5W, 字正); True → 左面(x 0.5W~W, 镜像字)"""
    x0 = 0 if not x_mirror else int(0.5 * FW)
    x1 = int(0.5 * FW) if not x_mirror else FW
    seg = x1 - x0
    # 云海日出：底部橙→青渐变弧带
    band = np.zeros((FH, seg, 3), np.float32)
    o1 = np.array([255, 158, 84]); o2 = np.array([255, 196, 120])
    b1 = np.array([64, 158, 214]); b2 = np.array([222, 240, 248])
    v = np.linspace(0, 1, FH)[:, None]  # numpy 首行=图顶；v=1(图底)=翼根
    band_h = 0.34
    tv = np.clip((v - (1 - band_h)) / band_h, 0, 1)  # 底部区
    for c in range(3):
        band[:, :, c] = b2[c] * (1 - tv) + b1[c] * tv
    inner = np.clip((tv - 0.52) / 0.48, 0, 1)
    for c in range(3):
        band[:, :, c] = band[:, :, c] * (1 - inner) + (o2[c] * (1 - inner) + o1[c] * inner) * inner
    bimg = to_img(band / 255.0)
    # 弧形顶缘蒙版
    msk = Image.new("L", (seg, FH), 0); md = ImageDraw.Draw(msk)
    arc_top = int((1 - band_h) * FH)
    pts = [(xx, arc_top + 70 * math.sin(math.pi * xx / seg) ** 1.5) for xx in range(seg)]
    md.polygon(pts + [(seg, FH), (0, FH)], fill=255)
    msk = msk.filter(ImageFilter.GaussianBlur(6))
    fim.paste(bimg, (x0, 0), msk)
    fd = ImageDraw.Draw(fim)
    # 文字（凌云 大字 + SKYLINE）
    if not x_mirror:
        cx0, cx1 = x0 + 0.05 * FW, x1 - 0.05 * FW
    else:
        cx0, cx1 = x0 + 0.05 * FW, x1 - 0.05 * FW
    tmp = Image.new("RGBA", (int(0.46 * FW), int(0.5 * FH)), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    f_big = font(FONT_HEI, 168)
    td.text((tmp.width / 2, tmp.height / 2 - 30), "凌云", font=f_big, fill=(24, 70, 116), anchor="mm")
    td.text((tmp.width / 2, tmp.height - 60), "SKYLINE AIR", font=font(FONT_HEI, 52), fill=(90, 120, 150), anchor="mm")
    # 右面区(x<0.5W)从外侧看是镜像视角 → 翻字；左面区正字
    if not x_mirror: tmp = tmp.transpose(Image.FLIP_LEFT_RIGHT)
    fim.paste(tmp, (int(cx0 + (cx1 - cx0 - tmp.width) / 2), int(0.40 * FH)), tmp)

fin_art(False); fin_art(True)
# 边缘前缘金属条
fd.line([(int(0.5*FW)-3, 0), (int(0.5*FW)-3, FH)], fill=(200, 208, 214), width=3)
noise = fbm(FW // 2, FH // 2, 3, seed=11)
noise = np.array(Image.fromarray((noise * 255).astype(np.uint8)).resize((FW, FH)), np.float32) / 255.0
arr = np.array(fim, np.float32); arr += (noise[:, :, None] - 0.5) * 5
to_img(arr / 255.0).save(os.path.join(OUT, "fin.png"))
fmr = np.full((FH, FW, 3), 255, np.uint8); fmr[:, :, 1] = 95; fmr[:, :, 2] = 22
Image.fromarray(fmr).save(os.path.join(OUT, "fin_mr.png"))

# ---------------- 3. 风扇模糊盘 512 ----------------
S = 512
fd_img = np.zeros((S, S, 4), np.float32)
yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
cx = cy = S / 2
r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (S / 2)
ang = np.arctan2(yy - cy, xx - cx)
radial = np.clip(1 - r, 0, 1)
alpha_edge = np.clip((1.0 - r) * 6, 0, 1)
# 中心锥
cone = np.clip(1 - r * 5.5, 0, 1)
# 18 叶片残影（旋转模糊的亮暗弧）
blades = 0.5 + 0.5 * np.sin(ang * 18 + r * 9)
blur = 0.35 + 0.65 * (blades * 0.55 + 0.45)
body = 0.16 + 0.5 * blur * np.clip(r * 1.15, 0, 1)
body = body * (1 - cone) + 0.30 * cone
for c in range(3):
    fd_img[:, :, c] = body * 255
fd_img[:, :, 3] = np.clip((alpha_edge * (r < 0.99)) * 255, 0, 255)
# 外缘深环
ring = (r > 0.90) & (r < 0.99)
fd_img[ring, 0:3] = 46; fd_img[ring, 3] = 235
Image.fromarray(fd_img.astype(np.uint8)).save(os.path.join(OUT, "fan_disc.png"))

# ---------------- 4. 云 sprite ×3 ----------------
def cloud_png(seed, out):
    """成团泡状云：多个径向渐变球叠出完整云团，边缘大范围衰减——绝无碎斑小点"""
    s = 256
    rng = random.Random(seed)
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    a = np.zeros((s, s), np.float32)
    nb = rng.randint(7, 10)
    for _ in range(nb):
        bx = s * 0.5 + (rng.random() - 0.5) * s * 0.50
        by = s * 0.56 + (rng.random() - 0.5) * s * 0.30
        br = s * (0.11 + rng.random() * 0.15)
        d = np.sqrt((xx - bx) ** 2 + (yy - by) ** 2)
        t = np.clip(1 - d / br, 0, 1)
        a = np.maximum(a, t * t * (3 - 2 * t))
    # 椭圆整体边缘衰减（防方形裁切感）
    rr = np.sqrt(((xx - s / 2) / (s * 0.52)) ** 2 + ((yy - s * 0.55) / (s * 0.40)) ** 2)
    a *= np.clip(1.08 - rr, 0, 1) ** 1.35
    a = np.array(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5)), np.float32) / 255.0
    cl = np.zeros((s, s, 4), np.float32)
    cl[:, :, 0] = 255; cl[:, :, 1] = 255; cl[:, :, 2] = 255
    cl[:, :, 3] = a * 255
    Image.fromarray(cl.astype(np.uint8)).save(os.path.join(OUT, out))

cloud_png(21, "cloud1.png"); cloud_png(37, "cloud2.png"); cloud_png(53, "cloud3.png")

# ---------------- 5. 平铺地面材质 ----------------
def tile_ground(out, base, spread, seam, seam_col, seed, stains=None, stones=None):
    s = 512
    n = fbm(s, s, 5, seed=seed)
    n2 = fbm(s, s, 4, seed=seed + 99)
    arr = np.tile(np.array(base, np.float32), (s, s, 1))
    arr += (n - 0.5)[:, :, None] * spread
    arr += (n2 - 0.5)[:, :, None] * spread * 0.6
    im = Image.fromarray((np.clip(arr, 0, 255)).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    if seam:
        for k in range(0, s, seam):
            dr.line([(k, 0), (k, s)], fill=seam_col, width=2)
            dr.line([(0, k), (s, k)], fill=seam_col, width=2)
    if stains:
        for _ in range(stains):
            x, y = random.randint(0, s), random.randint(0, s)
            rr = random.randint(8, 42)
            dr.ellipse([x - rr, y - rr * random.uniform(0.4, 0.8), x + rr, y + rr * random.uniform(0.4, 0.8)],
                       fill=tuple(int(c + random.uniform(-14, -2)) for c in base))
    if stones:
        for _ in range(stones):
            x, y = random.randint(0, s), random.randint(0, s)
            v = random.uniform(-26, 40)
            dr.point((x, y), fill=tuple(min(255, max(0, int(c + v))) for c in base))
            if random.random() < 0.4: dr.point((x + 1, y), fill=tuple(min(255, max(0, int(c + v))) for c in base))
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    im.save(os.path.join(OUT, out))

tile_ground("asphalt.png", (118, 122, 126), 26, 128, (96, 100, 104), seed=3, stains=14, stones=2600)
tile_ground("concrete.png", (205, 209, 212), 14, 170, (176, 181, 186), seed=5, stains=8, stones=900)
tile_ground("grass.png", (150, 190, 118), 34, None, None, seed=9, stains=26, stones=3600)

# 草地 color 调亮偏黄绿
g = np.array(Image.open(os.path.join(OUT, "grass.png")), np.float32)
g[:, :, 0] = np.clip(g[:, :, 0] * 1.06 + 6, 0, 255)
g[:, :, 1] = np.clip(g[:, :, 1] * 1.02, 0, 255)
g[:, :, 2] = np.clip(g[:, :, 2] * 0.92, 0, 255)
Image.fromarray(g.astype(np.uint8)).save(os.path.join(OUT, "grass.png"))

# ---------------- 6. 航站楼幕墙 512 ----------------
TW, TH = 512, 512
tg = np.zeros((TH, TW, 3), np.float32)
n = fbm(TW, TH, 3, seed=13)
b1 = np.array([191, 224, 238]); b2 = np.array([160, 199, 218])
for c in range(3):
    tg[:, :, c] = (b1[c] * (1 - n) + b2[c] * n)
# 高亮玻璃块（随机反光）
hi = (fbm(TW, TH, 2, seed=77) > 0.62)
tg[hi] = np.array([234, 246, 252])
im = Image.fromarray(np.clip(tg, 0, 255).astype(np.uint8))
dr = ImageDraw.Draw(im)
for y in range(0, TH, 56):    dr.line([(0, y), (TW, y)], fill=(128, 162, 182), width=3)
for x in range(0, TW, 26):    dr.line([(x, 0), (x, TH)], fill=(142, 174, 194), width=2)
im.save(os.path.join(OUT, "terminal_glass.png"))

print("textures ->", OUT)
for f in sorted(os.listdir(OUT)):
    print("  ", f, os.path.getsize(os.path.join(OUT, f)) // 1024, "KB")
