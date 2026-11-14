# 0312 无人值守真机方案：触摸分发和五秒绘图间隔

本轮用于确定五秒间隔发生在 HID 消费、SpringBoard 触摸分发、主循环
还是 C4 任务生成阶段。当前还没有证据证明原因，也未实现或验证 60fps。
无需用户在电脑或手机旁操作。0310 已执行并恢复，其一次性授权已使用；
0312 尚未获授权，也没有写入、启动或执行目录。

## 固定输入与行为

- 内核代码基于已运行的 0310，增加已提交的 0234 观测补丁。
  不包含未上机的 0311 待呈现帧修复。
- 镜像：20,054,016 字节，SHA256
  `1cf0fa2e2b0664575be7e17dcea44345b2c057d73931f32af077e0525f48bae9`。
- 内核：17,365,784 字节，SHA256
  `ca6f834ecbb0ba20d9b0a6e22e79b520c72288cb2a7b9045feab9f9d1373f8ca`；
  标识 `xnu-local312-4af69afdc08c4ec180dd2bbf152e576f`。
- 保留 60 Hz 软件呈现时钟、异步 GPU、`swp=3` 自动操作和 `touch_lat=1`。
  受启动参数长度限制，移除详细 `metal_fps=timeline` 汇总并增加 `sbp=1`；
  C4 每个已完成缓冲的 made/committed/done 日志仍由 `touch_lat=1` 输出。
- SpringBoard 观测库为 89,168 字节，SHA256
  `c829d5568ebf137b152e743db2e3147527b6d9bafddf43032cf4751e9d0ddb03`。
  只记录触摸入口/返回、类名、主循环阶段和刷新请求，不改变事件或刷新率。
- C4 前端仍为 0310 的同一已核验二进制，SHA256
  `560284ddda16936df1dd9c6003c8ef4c31096a7c41fcd72ade1051db8411d1d5`。

## 写入范围与顺序

1. 重新读取 recovery 身份、未挂载/无 holder 状态、31 个相关文件和 misc。
   当前根卷头必须匹配
   `492c57e711dcb89e40330f8c4ffce88fc63ceec09edb519ad3e24dc75740c8c0`。
   校验四个文件的 CNID、分配区、完整写前镜像和当前 catalog 位置。
2. userdata 内原位写入以下四个已有文件，四段数据加四个 catalog 块，
   合计 **1,814,528 字节**，每段写后读取核验：
   `/usr/local/lib/gauguin/libGauguinEAGL.dylib`（临时观测库）、
   `/System/Library/LaunchDaemons/com.apple.SpringBoard.plist`、
   `/System/Library/xpc/launchd.plist`（仅修改 SpringBoard 环境项）、
   `/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop`。
   其余 530 个 launchd 作业不变。不开新文件，不增加 HFSX 分配，不改 GPT。
3. misc 写入 **13 字节**恢复标记并核验；reboot bootloader 后，对固定镜像
   仅执行一次 `fastboot boot`，不重试启动。
4. 最多一次电源键按下/释放用于唤醒；必须观测到 display-on 才执行
   13 次合成滑动、442 份报告。物理触摸关闭。600 秒服务计时退出，
   主机观察窗口 780 秒。合成输入、队列成功均不能单独证明桌面响应。
5. 返回 TWRP 后采集本轮内核、backboardd 和 SpringBoard 日志。
   按实时 HFSX catalog 位置恢复四个原文件，最多写回 **1,814,528 字节**。
   只改所需逻辑长度字段，保留日志增长引起的无关 catalog 变化。
   核验完整原文件分配区、31 文件静态内容和原 misc 4 KiB。

正常 userdata 总写入 **3,629,056 字节**。包括失败写入、已验证回退和
最多一次恢复重试的 userdata 上限为 **9,072,640 字节**。
主机 misc 正常写入 13 字节；启动前失败时恢复该标记，合计最多 26 字节。
必要时最多一次 `fastboot reboot recovery`。安装失败回退不再重新安装；
恢复失败仅在完整回退核验成功后允许一次恢复重试。回退不完整则停止追加
写入并保留现场。原始分区备份、bootloader、recovery、modem、persist 保留。

## 已完成的校验

补丁回放、3 个 ARM64 编译单元、117 项实际 ObjC 观测器检查、47 项 AMFI
边界检查、20 项实际 HID 队列检查、iOS 原生库签名检查均通过。
独立镜像检查验证了 Mach-O 段、固件、启动封装、593 字节参数和已链接符号，
未增加未定义符号。没有使用 CI；沿用已核验基线对象作本地增量链接。

实际 HFSX 的内存覆盖模型验证了四文件安装和恢复；对八个写入位置分别模拟
部分写入失败，验证回退；另验证回退失败报告、最终 HFSX 验证拒绝后的回退
和无关 catalog 字节保留。所有模型手机写入为零。
无授权测试在任何 adb/fastboot 或执行目录创建前拒绝；唤醒日志解析通过
2 项有效样本和 12 项异常样本检查。

三次完整采集、日志副本、内核输出、恢复临时文件和元数据的静态上限
376,971,104 字节，预留 **512 MiB**。620 MB 构建/准备/测试批次已获存储预算
准入；生成镜像后，512 MiB 真机预留再次准入，计入量 499,393,937,408 字节。
执行前还会重新检查预算和全部 61 项固定输入。

私有材料：`research/tmp/sb-cadence-312/`。
trial-plan SHA256：
`e566a731b3df82ad5b8e390c125fec2113d51f99030a1479b79f3f35ddb65ea2`；
install-plan SHA256：
`6f182fd736b5ccc4d66b6acc277e358b52ca843e6a5d749de65bddc11c784a4f`；
ready SHA256：
`90918ac526306d91fb9706e33b068a74b2c25728157222aeb68ea6e18dc48a47`。

## 如何判读

分别看队列 head 是否前进、SpringBoard 是否进入并返回 `sendEvent:`、
主循环停在哪个观测阶段、C4 创建间隔。公共触摸入口不等同于手势被接受；
主循环阶段不是栈样本；零日志必须结合加载成功、覆盖范围、丢样及输出错误
判断。本轮不把 GPU 作业数、尝试呈现数或软件时钟设定直接当作物理 FPS。
