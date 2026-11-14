# 0313 无人值守真机方案：恢复 SpringBoard 观测链路

0312 已完成并独立恢复；它确认 backboardd 持续读取 HID 队列，同时仍有
约五秒的 C4 绘图任务间隔。但 SpringBoard 观测器没有启用日志，尚不能判断
触摸是否到达它。本轮使用已检查的、限定到 SpringBoard 的内核 exec 加载入口，
并记录观测库初始化的成功或拒绝原因，以补齐触摸分发和刷新调度证据。
这不是已经验证的 60fps 修复。无需用户在电脑或手机旁操作。
0312 的一次性授权已使用；0313 尚未获授权、写入或启动。

## 固定输入与行为

- 内核代码基于已运行的 0312，增加已提交的 0235 SpringBoard 加载补丁。
  不包含未上机的 0311 待呈现帧修复。
- 镜像：20,054,016 字节，SHA256
  `455102e9b8052a9b41e2d208d62e205b01218fb45fc8c093a19784eabe3f63e2`。
- 内核：17,366,192 字节，SHA256
  `eb20c46690fdfecf76ec727217b30aa98b4395cd81a85f10799019ca14d9244d`；
  标识 `xnu-local313-406b28bcd77f44ceba6a5bd597da7fa2`。
- 保留 60 Hz 软件呈现时钟、异步 GPU、`swp=3` 自动操作和 `touch_lat=1`。
  593 字节启动参数与 0312 完全相同；`sbp=1` 启用新的限定加载入口。
  C4 每个已完成缓冲的 made/committed/done 日志仍由 `touch_lat=1` 输出。
- SpringBoard 观测库为 89,168 字节，SHA256
  `b0b49caf5ecf11619d6223455017f6668203ce61e0816dd70f599a6de9b800a4`。
  记录构造函数进入和初始化拒绝原因，以及触摸入口/返回、类名、主循环阶段
  和刷新请求。内核仅对 mobile UID 501、确切的受保护 SpringBoard 可执行文件
  及受保护观测库插入单个 DYLD 路径；已有同一路径不重复添加，冲突则拒绝添加。
- C4 前端仍为 0310 的同一已核验二进制，SHA256
  `560284ddda16936df1dd9c6003c8ef4c31096a7c41fcd72ade1051db8411d1d5`。

## 写入范围与顺序

1. 重新读取 recovery 身份、未挂载/无 holder 状态、31 个相关文件和 misc。
   当前根卷头必须匹配
   `7faaeed238ab8ad51846767eb8e6f98ecfd1d8a6243196f998bfd514892c522d`。
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

正常主机 userdata 总写入 **3,629,056 字节**。包括失败写入、已验证回退和
最多一次恢复重试的主机 userdata 上限为 **9,072,640 字节**。
主机 misc 正常写入 13 字节；启动前失败时恢复该标记，合计最多 26 字节。
必要时最多一次 `fastboot reboot recovery`。安装失败回退不再重新安装；
恢复失败仅在完整回退核验成功后允许一次恢复重试。回退不完整则停止追加
写入并保留现场。原始分区备份、bootloader、recovery、modem、persist 保留。

## 已完成的校验

补丁回放、ARM64 exec 编译单元、104 项实际参数复制与注入检查（含 37 项
SpringBoard 场景）、117 项实际 ObjC 观测器检查和 iOS 原生库签名检查通过。
0234 的队列观测与 AMFI 边界沿用 0312 已测版本。
独立镜像检查验证了 Mach-O 段、固件、启动封装、593 字节参数和已链接符号，
未增加未定义符号。没有使用 CI；沿用已核验基线对象作本地增量链接。

实际 HFSX 的内存覆盖模型验证了四文件安装和恢复；对八个写入位置分别模拟
部分写入失败，验证回退；另验证回退失败报告、最终 HFSX 验证拒绝后的回退
和无关 catalog 字节保留。所有模型手机写入为零。
无授权测试在任何 adb/fastboot 或执行目录创建前拒绝；唤醒日志解析通过
2 项有效样本和 12 项异常样本检查。

三次完整采集、日志副本、内核输出、恢复临时文件和元数据的静态上限
376,971,104 字节，预留 **512 MiB**。620 MB 构建/准备/测试批次已获存储预算
准入；生成镜像后，512 MiB 真机预留再次准入，计入量 499,432,296,448 字节。
执行前还会重新检查预算和全部 63 项固定输入。

私有材料：`research/tmp/sb-loader-313/`。
trial-plan SHA256：
`3a6f41020f85a09677f3602073939d3fbb37d249f82b17a2b238af6cc2e35436`；
install-plan SHA256：
`65f50d7d6a568ac01ccba7f30672861240a424d29600761e3d775bbeba4ffcea`；
ready SHA256：
`befac55d10f77f2a7581327ffc541a945ec4cacc780b228343729ffe66a12b3e`。

## 如何判读

分别看队列 head 是否前进、SpringBoard 是否进入并返回 `sendEvent:`、
主循环停在哪个观测阶段、C4 创建间隔。公共触摸入口不等同于手势被接受；
主循环阶段不是栈样本；零日志必须结合加载成功、覆盖范围、丢样及输出错误
判断。本轮不把 GPU 作业数、尝试呈现数或软件时钟设定直接当作物理 FPS。
