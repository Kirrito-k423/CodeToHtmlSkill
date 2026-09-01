# DeepEP MoE Full-Mesh Dispatch：独立 E2E 架构与函数定义清单

## 1. 分析基线

- 源码：`samples/deepep_moe_dis_dispatch.h`
- SHA-256：`e2e87f115784687ea8c91b370183001ab7a17198203faa38e530263536da96fc`
- 源码行数：4357
- 函数定义：82
- 入口调用闭包可达定义：69（包含 public 构造、`Init` 和 `Process`）
- 从 `Init`/`Process` 不可达定义：13
- E2E 模块：15
- 模块源码覆盖：4357 / 4357，无缺口

这里把 `Init` 和 `Process` 都视为 public 入口。源码没有直接出现 `Init()` 调用 `Process()`；“外部 kernel 先初始化，再执行 Process”属于 public API 生命周期，而不是文件内调用边。

## 2. 文件解决的问题

输入是本 Rank 的 token `x`、每个 token 的 Top-K `expertIds`，以及可选 scale、token mask、expert mask 和 elastic rank 映射。内核需要完成：

1. 筛掉不参与计算的 token/expert 路由。
2. 把 token、量化信息、源 rank/token/top-k 反向索引和到达 flag 打成统一线格式。
3. Shared Expert 直接写目标窗口；MoE Expert 先写本地 staging buffer。
4. 并行交换每专家 token 数，得到接收侧前缀和及专家 token 数。
5. 对远端 MoE 目标生成 URMA WRITE WQE，对本 Rank MoE 目标做本地复制。
6. 通过独立 doorbell 核确保只有连续、完整写好的 WQE 被提交。
7. 接收侧按 cumsum 定位输出位置，按通信块 ready flag 检查完整性，写出 `expandXOut`、dynamic scale、`expandIdxOut`、`expertTokenNumsOut` 和 `sendCountsOut`。

`FillTriple` 第 1018–1025 行保存源 rank、源 token、初始 top-k slot 和完整 Top-K expert 列表；`CopyInAndOut` 第 2076–2096 行在二次按 expert 转发后恢复真实 top-k slot。

## 3. E2E 模块与完整行归属

| 模块 | 行范围 | 入口状态 | 作用 |
|---|---:|---|---|
| `source-contract` | 1–121, 348–722, 2480–2518, 2892–2934, 2943–2968 | 支持 | 依赖、常量、模板、主类、窗口布局、SQ/CQ/WQE 数据结构 |
| `routing-simt` | 122–347 | 可达 | expert 分组排序、WQE 描述、rank token 计数、全局 flag 初始化 |
| `initialization` | 723–1013 | 可达 | tiling、elastic、双缓冲状态、通信包尺寸、核职责划分 |
| `stage-pack` | 1014–1423 | 可达 | token 打包、shared 直发、MoE staging |
| `count-control` | 1424–1893 | 可达 | token 计数交换、等待状态、前缀和、计数输出 |
| `receive-format` | 1894–2253 | 可达 | 到达检测、窗口连续化、最终输出 |
| `mask-routing` | 2254–2479 | 可达 | token/expert/zero-compute mask |
| `urma-context-active` | 2519–2595 | 可达 | 当前启用的 UDMA SQ/CQ 上下文加载 |
| `urma-context-alternates` | 2596–2891 | 入口不可达 | 三个 UB SQ/CQ 加载备选版本 |
| `wqe-active` | 2935–2942, 3032–3093, 3277–3459 | 可达 | 当前 v4 WQE writer、批量 head 预留和 bitmap 发布 |
| `wqe-alternates` | 2969–3031, 3094–3276, 3460–3517 | 入口不可达 | 其他 WQE writer 和 CQ poll 备选实现 |
| `remote-send` | 3518–3891 | 可达 | 远端 expert 分核、WQE 构造与 SQ 写入 |
| `self-copy` | 3892–4000 | 可达 | 本 Rank expert 的 staging→window 复制 |
| `doorbell` | 4001–4277 | 可达 | SQ/CQ 初始化、headReady、bitmap 扫描和 doorbell 提交 |
| `process-entry` | 4278–4357 | 入口 | 顶层核角色分派与汇合 |

上述区间按行号合并后精确等于 `1..4357`。

## 4. 顶层真实执行结构

```text
外部调用方
  │
  ├─ Init
  │    ├─ SetTilingDataAndCal
  │    │    ├─ SetTilingData
  │    │    └─ InitElasticInfo（条件）
  │    ├─ ClearStageDoneFlags
  │    └─ SetDataStatus / 双缓冲窗口偏移
  │
  └─ Process
       │
       ├─ aivId < aivUsedStage_
       │    ├─ AllToAllDispatch
       │    │    ├─ ExpIdsCopyAndMaskCal
       │    │    ├─ SendToSharedExpert：直写目标窗口
       │    │    └─ SendToMoeExpertNew：写本地 staging
       │    ├─ PublishStageDone
       │    └─ aivId < aivUsedRemoteWqe_
       │         ├─ 是：URMASendToken
       │         └─ 否：SelfCopyToken
       │
       ├─ aivUsedStage_ <= aivId < aivCumSumStart_
       │    └─ RingDoorbell（当前 aivUsedDoorbell_ = 1）
       │
       └─ aivId >= aivCumSumStart_
            └─ CalCumSum

       所有分支随后调用 LocalWindowCopy
            ├─ WaitCumSumFlag
            ├─ SetValidExpertInfo
            └─ WaitAndFormatOutput
                 ├─ CheckDataArriveWithFlag
                 └─ CopyInAndOut
```

关键点：这不是“先 stage，再 remote，再 count，再 output”的全局线性流程。三组核并行工作，原来的全核 `SyncAll` 在第 4284–4286、4325–4327 行已注释。每条分支依赖自己的 flag/handshake 达成正确性。

## 5. 数据、同步与握手边

### 5.1 路由和线格式

- `AllToAllDispatch → ExpIdsCopyAndMaskCal`：第 1401 行。
- `CalCumSum → ExpIdsCopyAndMaskCal`：第 1838 行。
- `RingDoorbell → ExpIdsCopyAndMaskCal`：第 4116 行。
- 三条职责路径都复用同一 mask 语义，但各自在自己的 UB buffer 中重新计算。
- 每个通信块为 512B，其中 480B payload，尾部存到达 flag；常量在第 68–72 行，打包在第 1098–1107 行，检查在第 2008–2048 行。

### 5.2 Stage payload 到达

- Stage 核写完本轮 payload 后调用 `PublishStageDone`：第 4303 行。
- `SelfCopyToken` 等待全部有效 stage 核：第 3965 行。
- `RingDoorbell` 在真正敲铃前等待全部有效 stage 核：第 4158 行。
- `URMASendToken` 自身不等待全部 stage；它可以提前写 WQE，但 doorbell 不会在 payload 全部就绪前启动 DMA。

### 5.3 `headReady` 握手

1. Doorbell 核读取所有远端 SQ 的旧 head：第 4077–4085 行。
2. Doorbell 核为每个 remote-WQE 核发布 `headReadyFlag`：第 4097–4104 行。
3. `URMASendToken` 轮询自己对应的 `headReady`：第 3768–3781 行。

该握手防止 WQE 核先修改 head，导致 doorbell 核丢失本批次的起始 head。

### 5.4 WQE 完成 bitmap

`simt_nw_mj_vf` 的三阶段协议：

1. 每条 WQE 选择目标 SQ 并按 SQ 计数：第 3319–3330 行。
2. 每个活跃 SQ 只做一次 `atomicAdd(headAddr, count)`，批量预留连续 head：第 3333–3341 行。
3. 写 WQE、执行 `asc_threadfence`，再设置 `HeadRecordGM` 的对应 bit：第 3344–3376 行。

Doorbell 核从旧 head 开始扫描 bitmap，只统计连续的置位前缀：第 4174–4224 行；随后用 `st_dev` 提交新 head：第 4244–4264 行。后面的 WQE 即使先完成，也不会跨过中间未完成槽被提交。

### 5.5 计数控制面到接收格式化

- `CalAndSendCnt` 把 `[flag=1, count]` 状态块写到目标专家 Rank：第 1460–1494 行。
- `WaitDispatch` 等待负责范围内所有 flag：第 1671–1726 行。
- `CalRecvAndSetFlag` 计算跨 cumsum 核的前缀并写 `sendCountsOut`/workspace：第 1729–1764 行。
- `LocalWindowCopy` 用 `WaitCumSumFlag` 等待该控制面完成：第 2211 行。
- `SetValidExpertInfo` 用前缀差恢复每个源块 token 数：第 1895–1919 行。

## 6. 条件编译和不可达实现

### 条件编译/模板分支

- `__NPU_ARCH__ == 3510`：FP4 输入输出类型、copy 维度和 overflow 控制，主要在第 352–366、779–787、964–966、1037–1043、1082–1091 行。
- `QuantMode`：量化与非量化打包路径，见 `TokenToExpertInQuant`、`TokenToExpert` 及 `AllToAllDispatch`。
- `IsSmoothScaleExist`：控制 scale 是否随 token 搬运。
- `DEBUG_CLOCK_ON`：当前第 19 行启用，在 `Process` 第 4337–4352 行把时间差写到 `sendTpCountOutGM_`。
- `DB_ON_UB`、`WQE_ON_UB` 当前启用；`JETTY_ON_UB`、`WQE_OUT_ON_UB` 当前未启用，见第 2896–2923 行。

### 从 `Init`/`Process` 调用闭包不可达的 13 个定义

1. `CalExpertSendNum`
2. `SplitExpertNumToCore`
3. `SendToMoeExpert`
4. `RunPosRecord`
5. `get_sqs_and_cqs_xb_ub`
6. `get_sqs_and_cqs_xb_ub_v2`
7. `get_sqs_and_cqs_xb_ub_v3`
8. `simt_write_wqe_v5`
9. `simt_write_wqe_v3`
10. `simt_write_wqe_v2`
11. `simt_write_wqe`
12. `URMAPollCQ(AiURMAWQ*, AiURMACQ*)`
13. `URMAPollCQ(uint32_t, uint32_t, uint32_t, AiURMAWQ*, AiURMACQ*)`

`SendToMoeExpert` 是旧直写路径；当前 `AllToAllDispatch` 第 1419–1420 行明确调用 `SendToMoeExpertNew`。`RunPosRecord` 的调用点均已注释。三个 UB loader、非 v4 writer 和 CQ poll 均无入口可达调用点。它们是“已定义但入口不可达”，并非一定被预处理器裁掉。

## 7. 完整函数定义清单

行范围包含紧邻的模板前缀；`签名行` 是出现函数限定名/函数名的行。

| # | 函数 | 完整范围 | 签名行 | 模块 | 入口可达性 |
|---:|---|---:|---:|---|---|
| 1 | `simt_prepare_mapping` | 122–246 | 122 | routing-simt | 可达 |
| 2 | `buildRemoteWqeDesc` | 250–299 | 250 | routing-simt | 可达 |
| 3 | `calc_rank_token_cnt` | 301–332 | 301 | routing-simt | 可达 |
| 4 | `set_gm_value` | 334–347 | 334 | routing-simt | 可达 |
| 5 | `MoeDistributeDispatchV2FullMesh()` | 367–367 | 367 | source-contract | public 入口 |
| 6 | `GetHeadRecordRegionSize` | 431–437 | 431 | source-contract | 可达 |
| 7 | `GetUrmaCtrlReserveSize` | 439–445 | 439 | source-contract | 可达 |
| 8 | `GetStageDoneRegionSize` | 447–450 | 447 | source-contract | 可达 |
| 9 | `GetActiveStageNum` | 452–455 | 452 | source-contract | 可达 |
| 10 | `GetActiveMoeStageNum` | 457–460 | 457 | source-contract | 可达 |
| 11 | `GetWindAddrByRankId` | 462–479 | 462 | source-contract | 可达 |
| 12 | `GetWindStateBaseAddrByRankId` | 481–490 | 481 | source-contract | 可达 |
| 13 | `GetWindStateAddrByRankId` | 492–495 | 492 | source-contract | 可达 |
| 14 | `GetSendBufferAddrByTokenId` | 499–512 | 499 | source-contract | 可达 |
| 15 | `GetStageDoneAddrByAivId` | 514–523 | 514 | source-contract | 可达 |
| 16 | `GetHeadReadyAddr` | 526–530 | 526 | source-contract | 可达 |
| 17 | `GetHeadRecordAddr` | 532–536 | 532 | source-contract | 可达 |
| 18 | `GetSqsAddr` | 538–542 | 538 | source-contract | 可达 |
| 19 | `InitElasticInfo` | 723–741 | 724 | initialization | 可达 |
| 20 | `SetTilingData` | 743–770 | 744 | initialization | 可达 |
| 21 | `SetTilingDataAndCal` | 772–831 | 773 | initialization | 可达 |
| 22 | `ClearStageDoneFlags` | 833–850 | 834 | initialization | 可达 |
| 23 | `PublishStageDone` | 852–871 | 853 | initialization | 可达 |
| 24 | `WaitAllStageDone` | 873–895 | 874 | initialization | 可达 |
| 25 | `SetDataStatus` | 923–956 | 924 | initialization | 可达 |
| 26 | `Init` | 958–1012 | 959 | initialization | 入口 |
| 27 | `FillTriple` | 1014–1028 | 1015 | stage-pack | 可达 |
| 28 | `TokenToExpertInQuant` | 1030–1070 | 1031 | stage-pack | 可达 |
| 29 | `TokenToExpert` | 1072–1110 | 1073 | stage-pack | 可达 |
| 30 | `SplitToCore` | 1112–1137 | 1113 | stage-pack | 可达 |
| 31 | `SendToSharedExpert` | 1139–1174 | 1140 | stage-pack | 可达 |
| 32 | `CalExpertSendNum` | 1176–1200 | 1177 | stage-pack | 不可达 |
| 33 | `SplitExpertNumToCore` | 1202–1219 | 1203 | stage-pack | 不可达 |
| 34 | `SendToMoeExpert` | 1221–1275 | 1222 | stage-pack | 不可达旧实现 |
| 35 | `SendToMoeExpertNew` | 1278–1363 | 1279 | stage-pack | 可达 |
| 36 | `AllToAllDispatch` | 1365–1422 | 1366 | stage-pack | 可达 |
| 37 | `CalTokenSendExpertCnt` | 1424–1447 | 1425 | count-control | 可达 |
| 38 | `CalAndSendCnt` | 1449–1512 | 1450 | count-control | 可达 |
| 39 | `BufferInit` | 1513–1556 | 1514 | count-control | 可达 |
| 40 | `WaitDispatchClearStatus` | 1558–1571 | 1559 | count-control | 可达 |
| 41 | `GatherSumRecvCnt` | 1573–1609 | 1574 | count-control | 可达 |
| 42 | `GetCumSum` | 1611–1668 | 1612 | count-control | 可达 |
| 43 | `WaitDispatch` | 1670–1726 | 1671 | count-control | 可达 |
| 44 | `CalRecvAndSetFlag` | 1728–1764 | 1729 | count-control | 可达 |
| 45 | `SetExpertTokenNums` | 1766–1798 | 1767 | count-control | 可达 |
| 46 | `RecordRankCommDuration` | 1800–1824 | 1801 | count-control | 可达 |
| 47 | `CalCumSum` | 1826–1857 | 1827 | count-control | 可达 |
| 48 | `WaitCumSumFlag` | 1859–1892 | 1860 | count-control | 可达 |
| 49 | `SetValidExpertInfo` | 1894–1919 | 1895 | receive-format | 可达 |
| 50 | `CheckDataArriveWithFlag` | 1921–2049 | 1922 | receive-format | 可达 |
| 51 | `CopyInAndOut` | 2051–2098 | 2052 | receive-format | 可达 |
| 52 | `WaitAndFormatOutput` | 2100–2182 | 2101 | receive-format | 可达 |
| 53 | `RunPosRecord` | 2184–2193 | 2185 | receive-format | 不可达 |
| 54 | `LocalWindowCopy` | 2195–2252 | 2196 | receive-format | 可达 |
| 55 | `TokenActiveMaskCal` | 2254–2277 | 2255 | mask-routing | 可达 |
| 56 | `CalValidBSCnt` | 2279–2309 | 2280 | mask-routing | 可达 |
| 57 | `CalValidExpIdx` | 2311–2334 | 2312 | mask-routing | 可达 |
| 58 | `ExpertActiveMaskInit` | 2336–2346 | 2337 | mask-routing | 可达 |
| 59 | `ExpertActiveMaskCal` | 2348–2365 | 2349 | mask-routing | 可达 |
| 60 | `MaskZeroComputeExpert` | 2367–2402 | 2368 | mask-routing | 可达 |
| 61 | `GenerateGatherMaskTensor` | 2404–2411 | 2405 | mask-routing | 可达 |
| 62 | `ZeroComputeExpertMaskCal` | 2413–2427 | 2414 | mask-routing | 可达 |
| 63 | `ExpIdsCopyAndMaskCal` | 2429–2478 | 2430 | mask-routing | 可达 |
| 64 | `get_sqs_and_cqs_xb` | 2519–2594 | 2520 | urma-context-active | 可达 |
| 65 | `get_sqs_and_cqs_xb_ub` | 2596–2715 | 2596 | urma-context-alternates | 不可达 |
| 66 | `get_sqs_and_cqs_xb_ub_v2` | 2717–2833 | 2717 | urma-context-alternates | 不可达 |
| 67 | `get_sqs_and_cqs_xb_ub_v3` | 2836–2891 | 2836 | urma-context-alternates | 不可达 |
| 68 | `get_wqe_content` | 2935–2942 | 2935 | wqe-active | 可达 |
| 69 | `simt_write_wqe_v5` | 2969–3030 | 2969 | wqe-alternates | 不可达 |
| 70 | `simt_write_wqe_v4` | 3032–3093 | 3032 | wqe-active | 可达 |
| 71 | `simt_write_wqe_v3` | 3095–3158 | 3095 | wqe-alternates | 不可达 |
| 72 | `simt_write_wqe_v2` | 3160–3231 | 3160 | wqe-alternates | 不可达 |
| 73 | `simt_write_wqe` | 3233–3275 | 3233 | wqe-alternates | 不可达 |
| 74 | `simt_nw_mj_vf` | 3277–3408 | 3279 | wqe-active | 可达 |
| 75 | `simt_nw_mj` | 3411–3444 | 3412 | wqe-active | 可达 |
| 76 | `cacheWriteThrough` | 3447–3458 | 3447 | wqe-active | 可达 |
| 77 | `URMAPollCQ(AiURMAWQ*, AiURMACQ*)` | 3460–3498 | 3460 | wqe-alternates | 不可达 |
| 78 | `URMAPollCQ(rank, ports, qps, ...)` | 3501–3515 | 3501 | wqe-alternates | 不可达 |
| 79 | `URMASendToken` | 3518–3889 | 3519 | remote-send | 可达 |
| 80 | `SelfCopyToken` | 3892–3998 | 3893 | self-copy | 可达 |
| 81 | `RingDoorbell` | 4001–4276 | 4002 | doorbell | 可达 |
| 82 | `Process` | 4278–4354 | 4279 | process-entry | 入口 |

## 8. 交叉核对注意事项

1. 模板前缀是否计入函数 `start` 容易产生一行偏差。本清单的 `start` 包含紧邻模板行，JSON 另外保存 `signature_line` 和 `body_line`。
2. 类声明中的十余个 inline 地址/尺寸 helper 是真实定义，不能只统计第 723 行之后的类外定义。
3. `__simt_vf__`、`__simt_callee__` 和 `ACLSHMEM_DEVICE` 定义不能依赖普通 `ctags` 发现；Apple 自带 ctags 对本文件只识别到了类型和宏。
4. `VF_CALL<simt_prepare_mapping>`、`VF_CALL<buildRemoteWqeDesc>`、`VF_CALL<calc_rank_token_cnt>` 和 `VF_CALL<set_gm_value>` 属于真实内部调用，简单的 `name(` 搜索会漏掉模板尖括号形式。
5. `InitHeadRecord` 第 898–921 行整体位于注释中，不是函数定义，因此不计入 82。
6. `if constexpr (...) {` 不是函数定义；基于“右括号后花括号”扫描时必须排除，否则会产生 10 个左右假阳性。
