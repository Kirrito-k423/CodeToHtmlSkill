# Blueprint 预合并语义审计

> 审计时间：2026-09-01；范围：`blueprint-batch-01..13.json`、`blueprint-batch-15.json`、`blueprint-batch-16.json`。按任务要求不审 `blueprint-batch-14.json`。源码 SHA-256：`e2e87f115784687ea8c91b370183001ab7a17198203faa38e530263536da96fc`。

## 结论

**整体结论：BLOCK。** 81 个函数中 78 个可直接进入预合并，3 个函数存在确定的合并门禁错误；未发现仅需提醒但不阻断的 FLAG。3 个 BLOCK 都不是 E2E 语义或调用图错误，而是 batch-03 的显式逐行记录使用了非法 `kind=return`。

- BLOCK：3 个函数。

- FLAG：0 个函数。

- PASS：78 个函数。

## BLOCK

1. `GetWindStateAddrByRankId`（源码 L492–495，`blueprint-batch-03.json`）：L494 的 `line_notes.kind` 为 `return`。当前合并器 `LINE_NOTE_KINDS` 只接受 `signature/statement/declaration/branch/loop/call/sync/comment/preprocessor/brace/blank`；L494 同时调用 `GetWindStateBaseAddrByRankId`，语义上应归入 `call`。

2. `GetSendBufferAddrByTokenId`（源码 L499–512，`blueprint-batch-03.json`）：L503 的 `line_notes.kind` 为 `return`；该行是 MC2 分支中的返回表达式，应归入 `statement`。

3. `GetStageDoneAddrByAivId`（源码 L514–523，`blueprint-batch-03.json`）：L518 的 `line_notes.kind` 为 `return`；该行是 MC2 分支中的返回表达式，应归入 `statement`。

上述三处会使 `reviewed_line_notes()` 在 HTML 数据合并前直接失败，因此必须先修复，不能让这三个函数进入最终 HTML。

## FLAG

无。没有发现“可合并但语义需人工确认”的函数。

## 横向审计证据

- 完整性：15 个 blueprint 共 81 个函数、290 个连续 segments；每个函数的 `id/name/start/end/inactive` 均与冻结 inventory 一致。

- 内部调用：共 106 个内部调用行；blueprint 中的 `(target, line)` 集合与 inventory 的 `callees[].id/lines[]` 逐函数完全一致，未发现漏边、错 target 或把注释调用当有效边。

- inactive：以构造函数、`Init`、`Process` 为外部根重算调用闭包，冻结 inventory 的 69 个 active / 13 个 inactive 定义完全匹配；本次排除 batch-14 后，审计集合为 68 active / 13 inactive。

- 模块：81 个函数的 `module_id` 均落在 E2E 模块声明的真实源码 range 内；未发现跨模块误挂。

- 具体性：81 条 summary、290 条 segment title/detail/mechanism/why 均非空；同字段没有任何完全重复文本；所有 segment 连续覆盖函数范围并引用本段真实源码标识符。没有发现“处理数据”“执行核心逻辑”一类空泛占位标题。

- 主路径/备选路径：当前路径正确标为 `SendToMoeExpertNew`、`get_sqs_and_cqs_xb`、`simt_write_wqe_v4`、`simt_nw_mj_vf/simt_nw_mj`；旧 `SendToMoeExpert` 及两项辅助、三个 UB context loader、v5/v3/v2/基础 WQE writer、两个 CQ poller 和 `RunPosRecord` 均正确标为 inactive/alternate。

- 关键同步/握手表述抽查通过：stageDone 的 clear→publish→wait、cumsum flag 的 publish→wait→clear、headReady→WQE head 预留→headRecord bitmap→doorbell 的顺序均与源码调用和同步行一致。

## 逐函数结果


### Batch 01

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `simt_prepare_mapping` | L122–246 | `routing-simt` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `buildRemoteWqeDesc` | L250–299 | `routing-simt` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `calc_rank_token_cnt` | L301–332 | `routing-simt` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `set_gm_value` | L334–347 | `routing-simt` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `MoeDistributeDispatchV2FullMesh` | L367–367 | `source-contract` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `GetHeadRecordRegionSize` | L431–437 | `source-contract` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 02

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `GetUrmaCtrlReserveSize` | L439–445 | `source-contract` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `GetStageDoneRegionSize` | L447–450 | `source-contract` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `GetActiveStageNum` | L452–455 | `source-contract` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `GetActiveMoeStageNum` | L457–460 | `source-contract` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `GetWindAddrByRankId` | L462–479 | `source-contract` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `GetWindStateBaseAddrByRankId` | L481–490 | `source-contract` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 03

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `GetWindStateAddrByRankId` | L492–495 | `source-contract` | 否 | **BLOCK**：L494 `line_notes.kind=return`，合并器仅接受 call/statement 等枚举。 |
| `GetSendBufferAddrByTokenId` | L499–512 | `source-contract` | 否 | **BLOCK**：L503 `line_notes.kind=return`，合并器枚举不含 return。 |
| `GetStageDoneAddrByAivId` | L514–523 | `source-contract` | 否 | **BLOCK**：L518 `line_notes.kind=return`，合并器枚举不含 return。 |
| `GetHeadReadyAddr` | L526–530 | `source-contract` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `GetHeadRecordAddr` | L532–536 | `source-contract` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `GetSqsAddr` | L538–542 | `source-contract` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 04

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `InitElasticInfo` | L723–741 | `initialization` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `SetTilingData` | L743–770 | `initialization` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `SetTilingDataAndCal` | L772–831 | `initialization` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `ClearStageDoneFlags` | L833–850 | `initialization` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `PublishStageDone` | L852–871 | `initialization` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `WaitAllStageDone` | L873–895 | `initialization` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 05

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `SetDataStatus` | L923–956 | `initialization` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `Init` | L958–1012 | `initialization` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `FillTriple` | L1014–1028 | `stage-pack` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `TokenToExpertInQuant` | L1030–1070 | `stage-pack` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `TokenToExpert` | L1072–1110 | `stage-pack` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `SplitToCore` | L1112–1137 | `stage-pack` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 06

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `SendToSharedExpert` | L1139–1174 | `stage-pack` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `CalExpertSendNum` | L1176–1200 | `stage-pack` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `SplitExpertNumToCore` | L1202–1219 | `stage-pack` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `SendToMoeExpert` | L1221–1275 | `stage-pack` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `SendToMoeExpertNew` | L1278–1363 | `stage-pack` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `AllToAllDispatch` | L1365–1422 | `stage-pack` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 07

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `CalTokenSendExpertCnt` | L1424–1447 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `CalAndSendCnt` | L1449–1512 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `BufferInit` | L1513–1556 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `WaitDispatchClearStatus` | L1558–1571 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `GatherSumRecvCnt` | L1573–1609 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `GetCumSum` | L1611–1668 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 08

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `WaitDispatch` | L1670–1726 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `CalRecvAndSetFlag` | L1728–1764 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `SetExpertTokenNums` | L1766–1798 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `RecordRankCommDuration` | L1800–1824 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `CalCumSum` | L1826–1857 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `WaitCumSumFlag` | L1859–1892 | `count-control` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 09

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `SetValidExpertInfo` | L1894–1919 | `receive-format` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `CheckDataArriveWithFlag` | L1921–2049 | `receive-format` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `CopyInAndOut` | L2051–2098 | `receive-format` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `WaitAndFormatOutput` | L2100–2182 | `receive-format` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `RunPosRecord` | L2184–2193 | `receive-format` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `LocalWindowCopy` | L2195–2252 | `receive-format` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 10

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `TokenActiveMaskCal` | L2254–2277 | `mask-routing` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `CalValidBSCnt` | L2279–2309 | `mask-routing` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `CalValidExpIdx` | L2311–2334 | `mask-routing` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `ExpertActiveMaskInit` | L2336–2346 | `mask-routing` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `ExpertActiveMaskCal` | L2348–2365 | `mask-routing` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `MaskZeroComputeExpert` | L2367–2402 | `mask-routing` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 11

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `GenerateGatherMaskTensor` | L2404–2411 | `mask-routing` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `ZeroComputeExpertMaskCal` | L2413–2427 | `mask-routing` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `ExpIdsCopyAndMaskCal` | L2429–2478 | `mask-routing` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `get_sqs_and_cqs_xb` | L2519–2594 | `urma-context-active` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `get_sqs_and_cqs_xb_ub` | L2596–2715 | `urma-context-alternates` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `get_sqs_and_cqs_xb_ub_v2` | L2717–2833 | `urma-context-alternates` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 12

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `get_sqs_and_cqs_xb_ub_v3` | L2836–2891 | `urma-context-alternates` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `get_wqe_content` | L2935–2942 | `wqe-active` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `simt_write_wqe_v5` | L2969–3030 | `wqe-alternates` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `simt_write_wqe_v4` | L3032–3093 | `wqe-active` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `simt_write_wqe_v3` | L3095–3158 | `wqe-alternates` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `simt_write_wqe_v2` | L3160–3231 | `wqe-alternates` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 13

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `simt_write_wqe` | L3233–3275 | `wqe-alternates` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `simt_nw_mj_vf` | L3277–3408 | `wqe-active` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `simt_nw_mj` | L3411–3444 | `wqe-active` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `cacheWriteThrough` | L3447–3458 | `wqe-active` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `URMAPollCQ（双参数）` | L3460–3498 | `wqe-alternates` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `URMAPollCQ（多端口 wrapper）` | L3501–3515 | `wqe-alternates` | 是 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 15

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `SelfCopyToken` | L3892–3998 | `self-copy` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |
| `RingDoorbell` | L4001–4276 | `doorbell` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

### Batch 16

| 函数 | 源码范围 | 模块 | inactive | 结论 |
|---|---:|---|:---:|---|
| `Process` | L4278–4354 | `process-entry` | 否 | **PASS**：summary/segments 具体；metadata、内部调用、模块归属一致。 |

## 合并建议

先修正 batch-03 的三处 `line_notes.kind`，然后重跑 `review_from_blueprint`、`validate_segments` 与 `reviewed_line_notes` 三组门禁。修正后，当前已审 81 个函数在 summary/segments、inactive、内部调用和模块归属四个语义维度上均可判 PASS；待 batch-14 完成后还需对 `URMASendToken` L3518–3889 单独执行同级审计，才能形成 82/82 的最终合并结论。
