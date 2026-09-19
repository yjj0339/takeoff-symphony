# 凌云起飞 Takeoff Symphony — DEVLOG

大型宽体客机 3D 起飞全程：Blender 精细建模 → GLB → three.js 剧场式演出。
项目始于 2026-09-19。用户要求：最强建模、极致细节、完整起飞流程（陆地→天空）、多功能。

## 技术路线
- Blender 5.2 无头建模（`C:/Program Files/Blender Foundation/Blender 5.2/blender.exe`）
- three 0.170（根 node_modules 复制，自包含构建，无 three.core.js 依赖）
- importmap: `three` → `./vendor/three/three.module.js`，`three/addons/` → `./vendor/three/addons/`
- 部署 GitHub Pages yjj0339/takeoff-symphony

## 关键决定
- 坐标：Blender 里机头朝 +Y（导出 glTF 变换后 = three 的 -Z 前方）
- 飞机：A350/787 风格宽体双发，注册号 B-2026，虚构航司「凌云航空 SKYLINE AIR」
- 跑道标线用几何条带（非贴图）保证任意距离清晰；地面材质用平铺贴图
- 起落架收放/襟翼在 three 里程序化驱动（GLB 保留 pivot 层级命名）
- 浅色主题铁律：明亮天空、白机身、浅色 UI
- 机身贴图 4096x2048：UV.u=沿机身长度, UV.v=环向角

## 文件结构
- blender/make_textures.py — PIL 生成全部贴图 → assets/tex/
- blender/build_plane.py — 建模飞机 → assets/plane.glb
- blender/build_airport.py — 机场建筑/跑道/地形 → assets/airport.glb
- js/main.js 入口；flight.js 起飞状态机；cameras.js 导播；plane.js 部件联动；
  environment.js 天空云雾；hud.js 中文浅色 UI；audio.js WebAudio 合成引擎声

## 进度
- [x] 环境：Blender 5.2 / three 0.170 / PIL 11.3 / node 24
- [x] vendor 就绪（three.module.js + GLTFLoader + OrbitControls + BufferGeometryUtils）
- [x] 贴图生成（fuselage 4096 + fin + 云 + 地面材质 + 幕墙）
- [x] 飞机建模 plane.glb（1MB，五轮视觉评审 12/12 通过：飘带/文字方向/垂尾云海/起落架触地/金属反光/机头圆润）
- [x] 机场建模 airport.glb（跑道全套几何标线/灯光/航站楼/塔台/廊桥/地形，验收通过）
- [x] three.js 应用（155s 时间线纯函数求值/15 自动机位/8 手动/自由视角/合成音效/中文 HUD/穿云白幕）
- [x] 整场演出 9 时刻截图验收通过；手机竖屏验收通过
- [x] 部署 https://yjj0339.github.io/takeoff-symphony/ （200+MIME 全过；修线上抢点竞态；导航主页已加卡片+二维码）

## 交付后修复
- 线上竞态：__app 挂顶层早于 GLB 就绪，"开始"按钮 listener 在 ready() 才绑→加载中点击无效。
  修：listener 移顶层接住排队（按钮变"装载模型中…"），ready() 后自动 beginShow。

## 坑与教训（边做边记）
- Blender object 的 matrix_world 创建后不自动刷新，matrix_parent_inverse 拿到过时值 → 部件位移翻倍/丢失。终解：所有 pivot 无旋转，empty_at(loc) 显式局部=世界-父世界累加（world_loc helper）
- bmesh bm.verts[-n:] 尾部切片不可靠 → 一律 before/after 集合
- 机身贴图环向：Blender UV v=φ/2π（φ=0 腹），glTF 图 y=(1-v)H；右舷=图 y 0.66-0.83H 区
- 机身/垂尾右舷(面)文字需镜像绘制（左舷正）；垂尾贴图 numpy 首行=图顶（band 渐变方向坑）
- PIL to_img 期望 0-1 输入——飘带 0-255 数组被 clip 成全白带隐形四轮评审
- 机翼厚度是绝对值(米)不是相对弦长（曾 19.5m 厚巨翼）
- 起落架 y=前后 z=高度，别混槽；轮子/bogie/短舱/风扇是 pivot 局部建模 → mesh_from_bm(local_space=True)
- 金属材质必须配 scene.environment 否则渲染黑
- 视觉验收走 documents:visual-judge 子代理 + playwright 截图（Read 图片会传 CDN 看不了，子代理可以）
