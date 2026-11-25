# 稳定 60 fps 的供帧和呈现证据

0366 固定慢拖的硬件刷新为 60.18–60.31 Hz，78 个扫描中 77 个新画面、1 个重复，实测 59.41–59.54 新画面/秒。复核添加了第 8 次滑动的同帧拷贝结束回执。暖态第 3 至 13 次滑动共有 127 个新画面和 100 个重复帧，33.59–33.88 新画面/秒，更新间隔 p95 为 49.02–51.85 ms。该轮存在一次计分区外的拷贝结束边界无法验收。

## 普通滑动的供帧

| 截止时能确认的阶段 | 0366 暖态重复扫描 |
| --- | ---: |
| 尚无新 swap | 25 |
| 有 swap，目标版本缺少 writer 认领 | 35 |
| 已关联 Core，尚未 native issue | 11 |
| 已 native issue，未观测到缓存可见 | 28 |
| 缺少可靠扫描截止边沿 | 1 |

固定原 swap 和扫描时序，允许无限保留有效图像并把复制耗时设为零。在 227 个暖态扫描中，已接受的 swap 最多填 173 个，按已关联的 native issue 收紧后为 146 个，按观测到的缓存可见再收紧为 141 个。一个截止边沿缺失的扫描按成功算入上界。提高后段吞吐可以减少部分遗漏，达到稳定 60 fps 还需要改变前端提交时序。重放使用观测到的 GPU 完成时刻。

35 个缺少 writer 认领的重复扫描共涉及 16 个不同 swap。每个 swap 所指同一 surface 的前一个版本都有一个未认领 writer，10 个 writer 的 native issue 在对应 swap 前后 5 ms 内。用实测复制中位数、实际可见回执、原显示 fence 和未覆盖版本做重放，14 个不同 writer 可能赶上某个扫描。需先取得明确的渲染事务身份，才能把这些前序版本交给呈现。用经过时间差关联的候选替换会使图像内容身份不确定。

0366 中内核 framebuffer 输出的 130 条通知计数记录均为零注册、零发送。当前证据还没有确定 backboardd 实际消费的调度时钟。优先跟踪其帧提交与换帧请求之间的关联，软件计时器平均间隔只作为辅助。

## 整屏拷贝和缓冲区所有权

0366 的 658 次整屏拷贝区间中位数 2.88 ms，p95 约 4.98 ms，最长 8.89 ms。最长一次的结束回执跨过扫描边沿。后台完整准备加硬件整帧切换可以把复制移出当前扫描的消隐期限。旧缓冲区的回收必须等硬件切换完成。Xiaomi 视频模式以 vblank 和 CTL flush 确认提交，Linux KMS 也约定完成事件后才能复用旧缓冲区。[Xiaomi 视频模式实现](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/sde/sde_encoder_phys_vid.c#L440) · [Linux KMS](https://docs.kernel.org/6.10/gpu/drm-kms.html)

原扫描缓冲也是 `GetLayerDefaultSurface` 交给客户端的 IOSurface。后台呈现模型保留其原有归属，另用两块独占的显示缓冲。根据 0367 精确镜像的 DTB、恢复快照与 XNU 管理内存，连续显示预留区的几何空间能容纳两块各 10,371,072 字节的对齐范围，起点分别为 `0xa09e4000` 和 `0xa13c8000`。仍需核对固件所有权、DPU 地址翻译和硬件锁存后，才能使用这两个范围。

主机模型遍历 242 个状态、6,107 个转移，覆盖读保护、过期的写入完成回执、扫描号回绕、重复 vblank 和切换超时。超时后同时保留当前与等待切换的缓冲区。另有 9 个显示流路由模型用例，验证映射歧义、明确地址翻译和缺少匹配时的处理。依据恢复 DTB 中的非安全显示流和 Xiaomi 的 SMMU 寄存器定义，路由模型仅报告现有路径。候选范围可达性仍需实机证据。[Xiaomi SMMU 寄存器定义](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/drivers/iommu/arm-smmu-regs.h#L95)

分析工具为 `tools/audit-warm-frame-supply.py`、`tools/model-scanout-buffers.py` 和 `tools/model-display-address-routing.py`。本地产物在本工作树的 `research/tmp/stable60-host`。
