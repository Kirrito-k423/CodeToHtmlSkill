# 全量函数事实清单

- 源码：`samples/deepep_moe_dis_dispatch.h`
- SHA-256：`e2e87f115784687ea8c91b370183001ab7a17198203faa38e530263536da96fc`
- 源码行数：4357
- 最终定义：82
- 类内声明站点：50，未配对 declaration-only：0
- 从构造/Init/Process 不可达定义：13

## 两种独立发现方法

| 方法 | 定义数 | 与最终集合精确匹配 | 结论 |
|---|---:|---:|---|
| 注释/字符串遮罩 + 括号/花括号扫描 | 82 | 82 | 原始源码边界权威来源 |
| Clang recovery AST | 82 | 82（81 原始一致 + 1 规范化配对） | 去除物理行偏移 43 后核对名称、declarator 与 end |
| Apple/BSD ctags（附加诊断） | 0 个函数名 | 不参与 | 只识别少量 struct/typedef/macro，无法穿透 Ascend 宏 |

Clang 无法获得下载文件所依赖的 Ascend/CANN 头文件，因此采用最小类型桩进入错误恢复模式；产生的诊断不用于推断语义。两条主方法的差异如下：

- 原始名称、declarator 起始行、结束行三者精确一致：81
- 规范化后两方法共同发现：82
- 唯一原始差异：Clang 将 L367 构造函数显示为带模板实参的类名，且 recovery AST 未给单行空函数体 end；按构造函数命名规则规范化名称，并由原始花括号确定 `end=367` 后完成配对。
- 未解决差异：0

类内 50 个无函数体声明均按 `name + parameter_count` 配对到定义；没有真正的 declaration-only。`#if constexpr` 被文本扫描明确排除为控制结构，不计作函数。

## inactive 判定

以类构造函数、`Init`、`Process` 为入口，沿真实函数名调用和 `VF_CALL<target>` 传播可达性；注释中的调用已在词法遮罩阶段移除。`inactive=true` 表示本文件当前入口调用图不可达，不等价于源码无法编译。

- `MoeDistributeDispatchV2FullMesh::CalExpertSendNum` L1176–L1200 · `m-moedistributedispatchv2fullmesh-calexpertsendnum-0ff9e62b02`
- `MoeDistributeDispatchV2FullMesh::SplitExpertNumToCore` L1202–L1219 · `m-moedistributedispatchv2fullmesh-splitexpertnumtocore-7e9378cdd9`
- `MoeDistributeDispatchV2FullMesh::SendToMoeExpert` L1221–L1275 · `m-moedistributedispatchv2fullmesh-sendtomoeexpert-388b5146c1`
- `MoeDistributeDispatchV2FullMesh::RunPosRecord` L2184–L2193 · `m-moedistributedispatchv2fullmesh-runposrecord-a1ffd8ca5e`
- `MoeDistributeDispatchV2FullMeshImpl::get_sqs_and_cqs_xb_ub` L2596–L2715 · `f-moedistributedispatchv2fullmeshimpl-get-sqs-and-cqs-xb-ub-2cc6fc9d77`
- `MoeDistributeDispatchV2FullMeshImpl::get_sqs_and_cqs_xb_ub_v2` L2717–L2833 · `f-moedistributedispatchv2fullmeshimpl-get-sqs-and-cqs-xb-ub-v2-76be68c05e`
- `MoeDistributeDispatchV2FullMeshImpl::get_sqs_and_cqs_xb_ub_v3` L2836–L2891 · `f-moedistributedispatchv2fullmeshimpl-get-sqs-and-cqs-xb-ub-v3-5d39e16cd7`
- `MoeDistributeDispatchV2FullMeshImpl::simt_write_wqe_v5` L2969–L3030 · `f-moedistributedispatchv2fullmeshimpl-simt-write-wqe-v5-f7eac0343f`
- `MoeDistributeDispatchV2FullMeshImpl::simt_write_wqe_v3` L3095–L3158 · `f-moedistributedispatchv2fullmeshimpl-simt-write-wqe-v3-6d8d424864`
- `MoeDistributeDispatchV2FullMeshImpl::simt_write_wqe_v2` L3160–L3231 · `f-moedistributedispatchv2fullmeshimpl-simt-write-wqe-v2-d832a96558`
- `MoeDistributeDispatchV2FullMeshImpl::simt_write_wqe` L3233–L3275 · `f-moedistributedispatchv2fullmeshimpl-simt-write-wqe-5b3a890c15`
- `MoeDistributeDispatchV2FullMeshImpl::URMAPollCQ` L3460–L3498 · `f-moedistributedispatchv2fullmeshimpl-urmapollcq-4eae8cd065`
- `MoeDistributeDispatchV2FullMeshImpl::URMAPollCQ` L3501–L3515 · `f-moedistributedispatchv2fullmeshimpl-urmapollcq-110d72f7d6`

## 全量定义

| # | 稳定 ID | 名称 | 类型 | 范围 | inactive | callers / callees |
|---:|---|---|---|---:|:---:|---|
| 1 | `f-moedistributedispatchv2fullmeshimpl-simt-prepare-mapping-afc96d238b` | `MoeDistributeDispatchV2FullMeshImpl::simt_prepare_mapping` | free_function | L122–L246 | false | URMASendToken, SelfCopyToken / — |
| 2 | `f-moedistributedispatchv2fullmeshimpl-buildremotewqedesc-a49b5a47dd` | `MoeDistributeDispatchV2FullMeshImpl::buildRemoteWqeDesc` | free_function | L250–L299 | false | URMASendToken / — |
| 3 | `f-moedistributedispatchv2fullmeshimpl-calc-rank-token-cnt-dbb2600941` | `MoeDistributeDispatchV2FullMeshImpl::calc_rank_token_cnt` | free_function | L301–L332 | false | RingDoorbell / — |
| 4 | `f-moedistributedispatchv2fullmeshimpl-set-gm-value-b3c17ca3da` | `MoeDistributeDispatchV2FullMeshImpl::set_gm_value` | free_function | L334–L347 | false | RingDoorbell / — |
| 5 | `ctor-moedistributedispatchv2fullmesh-moedistributedispatchv2fullmesh-a94c1aa7ec` | `MoeDistributeDispatchV2FullMesh::MoeDistributeDispatchV2FullMesh` | constructor | L367–L367 | false | — / — |
| 6 | `m-moedistributedispatchv2fullmesh-getheadrecordregionsize-f33b3f5132` | `MoeDistributeDispatchV2FullMesh::GetHeadRecordRegionSize` | method | L431–L437 | false | GetUrmaCtrlReserveSize, GetSqsAddr / — |
| 7 | `m-moedistributedispatchv2fullmesh-geturmactrlreservesize-52bf758842` | `MoeDistributeDispatchV2FullMesh::GetUrmaCtrlReserveSize` | method | L439–L445 | false | GetWindAddrByRankId, GetWindStateBaseAddrByRankId, SetDataStatus / GetHeadRecordRegionSize |
| 8 | `m-moedistributedispatchv2fullmesh-getstagedoneregionsize-5c2a0cf9f6` | `MoeDistributeDispatchV2FullMesh::GetStageDoneRegionSize` | method | L447–L450 | false | GetWindAddrByRankId, GetWindStateBaseAddrByRankId, GetSendBufferAddrByTokenId, GetHeadReadyAddr, SetDataStatus / — |
| 9 | `m-moedistributedispatchv2fullmesh-getactivestagenum-6043683614` | `MoeDistributeDispatchV2FullMesh::GetActiveStageNum` | method | L452–L455 | false | ClearStageDoneFlags, PublishStageDone, WaitAllStageDone, SelfCopyToken, RingDoorbell / — |
| 10 | `m-moedistributedispatchv2fullmesh-getactivemoestagenum-ddba56eb6b` | `MoeDistributeDispatchV2FullMesh::GetActiveMoeStageNum` | method | L457–L460 | false | SendToMoeExpertNew / — |
| 11 | `m-moedistributedispatchv2fullmesh-getwindaddrbyrankid-994ab853c1` | `MoeDistributeDispatchV2FullMesh::GetWindAddrByRankId` | method | L462–L479 | false | Init, SendToSharedExpert, SendToMoeExpert, URMASendToken, SelfCopyToken / GetStageDoneRegionSize, GetUrmaCtrlReserveSize |
| 12 | `m-moedistributedispatchv2fullmesh-getwindstatebaseaddrbyrankid-3d8c15c648` | `MoeDistributeDispatchV2FullMesh::GetWindStateBaseAddrByRankId` | method | L481–L490 | false | GetWindStateAddrByRankId, SetDataStatus / GetStageDoneRegionSize, GetUrmaCtrlReserveSize |
| 13 | `m-moedistributedispatchv2fullmesh-getwindstateaddrbyrankid-68f65ffa74` | `MoeDistributeDispatchV2FullMesh::GetWindStateAddrByRankId` | method | L492–L495 | false | SetDataStatus, Init, CalAndSendCnt / GetWindStateBaseAddrByRankId |
| 14 | `m-moedistributedispatchv2fullmesh-getsendbufferaddrbytokenid-aee7115d35` | `MoeDistributeDispatchV2FullMesh::GetSendBufferAddrByTokenId` | method | L499–L512 | false | SendToMoeExpertNew, URMASendToken, SelfCopyToken / GetStageDoneRegionSize |
| 15 | `m-moedistributedispatchv2fullmesh-getstagedoneaddrbyaivid-d0dc00d0d9` | `MoeDistributeDispatchV2FullMesh::GetStageDoneAddrByAivId` | method | L514–L523 | false | ClearStageDoneFlags, PublishStageDone, WaitAllStageDone / — |
| 16 | `m-moedistributedispatchv2fullmesh-getheadreadyaddr-70fab86c3d` | `MoeDistributeDispatchV2FullMesh::GetHeadReadyAddr` | method | L526–L530 | false | GetHeadRecordAddr, URMASendToken, RingDoorbell / GetStageDoneRegionSize |
| 17 | `m-moedistributedispatchv2fullmesh-getheadrecordaddr-89abc8e6ef` | `MoeDistributeDispatchV2FullMesh::GetHeadRecordAddr` | method | L532–L536 | false | GetSqsAddr, URMASendToken, RingDoorbell / GetHeadReadyAddr |
| 18 | `m-moedistributedispatchv2fullmesh-getsqsaddr-114b933bf9` | `MoeDistributeDispatchV2FullMesh::GetSqsAddr` | method | L538–L542 | false | URMASendToken, RingDoorbell / GetHeadRecordAddr, GetHeadRecordRegionSize |
| 19 | `m-moedistributedispatchv2fullmesh-initelasticinfo-425555e041` | `MoeDistributeDispatchV2FullMesh::InitElasticInfo` | method | L723–L741 | false | SetTilingDataAndCal / — |
| 20 | `m-moedistributedispatchv2fullmesh-settilingdata-2fa0522df9` | `MoeDistributeDispatchV2FullMesh::SetTilingData` | method | L743–L770 | false | SetTilingDataAndCal / — |
| 21 | `m-moedistributedispatchv2fullmesh-settilingdataandcal-95627c6bd4` | `MoeDistributeDispatchV2FullMesh::SetTilingDataAndCal` | method | L772–L831 | false | Init / SetTilingData, InitElasticInfo |
| 22 | `m-moedistributedispatchv2fullmesh-clearstagedoneflags-21e30fca4f` | `MoeDistributeDispatchV2FullMesh::ClearStageDoneFlags` | method | L833–L850 | false | Init / GetActiveStageNum, GetStageDoneAddrByAivId |
| 23 | `m-moedistributedispatchv2fullmesh-publishstagedone-93230832a9` | `MoeDistributeDispatchV2FullMesh::PublishStageDone` | method | L852–L871 | false | Process / GetActiveStageNum, GetStageDoneAddrByAivId |
| 24 | `m-moedistributedispatchv2fullmesh-waitallstagedone-3314d3ceaf` | `MoeDistributeDispatchV2FullMesh::WaitAllStageDone` | method | L873–L895 | false | SelfCopyToken, RingDoorbell / GetActiveStageNum, GetStageDoneAddrByAivId |
| 25 | `m-moedistributedispatchv2fullmesh-setdatastatus-7abd358558` | `MoeDistributeDispatchV2FullMesh::SetDataStatus` | method | L923–L956 | false | Init / GetWindStateBaseAddrByRankId, GetWindStateAddrByRankId, GetStageDoneRegionSize, GetUrmaCtrlReserveSize |
| 26 | `m-moedistributedispatchv2fullmesh-init-c24fae58e8` | `MoeDistributeDispatchV2FullMesh::Init` | method | L958–L1012 | false | — / SetTilingDataAndCal, ClearStageDoneFlags, SetDataStatus, GetWindStateAddrByRankId, GetWindAddrByRankId |
| 27 | `m-moedistributedispatchv2fullmesh-filltriple-f6ec541b45` | `MoeDistributeDispatchV2FullMesh::FillTriple` | method | L1014–L1028 | false | TokenToExpertInQuant, TokenToExpert / — |
| 28 | `m-moedistributedispatchv2fullmesh-tokentoexpertinquant-ada035d1fb` | `MoeDistributeDispatchV2FullMesh::TokenToExpertInQuant` | method | L1030–L1070 | false | SendToSharedExpert, SendToMoeExpert, SendToMoeExpertNew / FillTriple |
| 29 | `m-moedistributedispatchv2fullmesh-tokentoexpert-4209b8d38b` | `MoeDistributeDispatchV2FullMesh::TokenToExpert` | method | L1072–L1110 | false | SendToSharedExpert, SendToMoeExpert, SendToMoeExpertNew / FillTriple |
| 30 | `m-moedistributedispatchv2fullmesh-splittocore-e75b18e982` | `MoeDistributeDispatchV2FullMesh::SplitToCore` | method | L1112–L1137 | false | SendToSharedExpert, CalAndSendCnt, CalCumSum, LocalWindowCopy / — |
| 31 | `m-moedistributedispatchv2fullmesh-sendtosharedexpert-ba8dee0206` | `MoeDistributeDispatchV2FullMesh::SendToSharedExpert` | method | L1139–L1174 | false | AllToAllDispatch / SplitToCore, GetWindAddrByRankId, TokenToExpertInQuant, TokenToExpert |
| 32 | `m-moedistributedispatchv2fullmesh-calexpertsendnum-0ff9e62b02` | `MoeDistributeDispatchV2FullMesh::CalExpertSendNum` | method | L1176–L1200 | true | SendToMoeExpert / — |
| 33 | `m-moedistributedispatchv2fullmesh-splitexpertnumtocore-7e9378cdd9` | `MoeDistributeDispatchV2FullMesh::SplitExpertNumToCore` | method | L1202–L1219 | true | SendToMoeExpert / — |
| 34 | `m-moedistributedispatchv2fullmesh-sendtomoeexpert-388b5146c1` | `MoeDistributeDispatchV2FullMesh::SendToMoeExpert` | method | L1221–L1275 | true | — / SplitExpertNumToCore, CalExpertSendNum, GetWindAddrByRankId, TokenToExpertInQuant, TokenToExpert |
| 35 | `m-moedistributedispatchv2fullmesh-sendtomoeexpertnew-12b59c248e` | `MoeDistributeDispatchV2FullMesh::SendToMoeExpertNew` | method | L1278–L1363 | false | AllToAllDispatch / GetActiveMoeStageNum, GetSendBufferAddrByTokenId, TokenToExpertInQuant, TokenToExpert |
| 36 | `m-moedistributedispatchv2fullmesh-alltoalldispatch-5b12449592` | `MoeDistributeDispatchV2FullMesh::AllToAllDispatch` | method | L1365–L1422 | false | Process / ExpIdsCopyAndMaskCal, SendToSharedExpert, SendToMoeExpertNew |
| 37 | `m-moedistributedispatchv2fullmesh-caltokensendexpertcnt-472b23f1f2` | `MoeDistributeDispatchV2FullMesh::CalTokenSendExpertCnt` | method | L1424–L1447 | false | CalAndSendCnt / — |
| 38 | `m-moedistributedispatchv2fullmesh-calandsendcnt-fd76d0d474` | `MoeDistributeDispatchV2FullMesh::CalAndSendCnt` | method | L1449–L1512 | false | CalCumSum / SplitToCore, CalTokenSendExpertCnt, GetWindStateAddrByRankId |
| 39 | `m-moedistributedispatchv2fullmesh-bufferinit-f41c2b0348` | `MoeDistributeDispatchV2FullMesh::BufferInit` | method | L1513–L1556 | false | CalCumSum / — |
| 40 | `m-moedistributedispatchv2fullmesh-waitdispatchclearstatus-efe4e94078` | `MoeDistributeDispatchV2FullMesh::WaitDispatchClearStatus` | method | L1558–L1571 | false | WaitDispatch / — |
| 41 | `m-moedistributedispatchv2fullmesh-gathersumrecvcnt-62b057b564` | `MoeDistributeDispatchV2FullMesh::GatherSumRecvCnt` | method | L1573–L1609 | false | WaitDispatch / — |
| 42 | `m-moedistributedispatchv2fullmesh-getcumsum-ab0a314dce` | `MoeDistributeDispatchV2FullMesh::GetCumSum` | method | L1611–L1668 | false | CalRecvAndSetFlag / — |
| 43 | `m-moedistributedispatchv2fullmesh-waitdispatch-3e9546ab05` | `MoeDistributeDispatchV2FullMesh::WaitDispatch` | method | L1670–L1726 | false | CalCumSum / RecordRankCommDuration, WaitDispatchClearStatus, GatherSumRecvCnt |
| 44 | `m-moedistributedispatchv2fullmesh-calrecvandsetflag-56c1c11bb0` | `MoeDistributeDispatchV2FullMesh::CalRecvAndSetFlag` | method | L1728–L1764 | false | CalCumSum / GetCumSum |
| 45 | `m-moedistributedispatchv2fullmesh-setexperttokennums-06080341cd` | `MoeDistributeDispatchV2FullMesh::SetExpertTokenNums` | method | L1766–L1798 | false | CalCumSum / — |
| 46 | `m-moedistributedispatchv2fullmesh-recordrankcommduration-17d0d2c4cf` | `MoeDistributeDispatchV2FullMesh::RecordRankCommDuration` | method | L1800–L1824 | false | WaitDispatch / — |
| 47 | `m-moedistributedispatchv2fullmesh-calcumsum-a5faf2a53a` | `MoeDistributeDispatchV2FullMesh::CalCumSum` | method | L1826–L1857 | false | Process / ExpIdsCopyAndMaskCal, CalAndSendCnt, SplitToCore, BufferInit, WaitDispatch, CalRecvAndSetFlag, SetExpertTokenNums |
| 48 | `m-moedistributedispatchv2fullmesh-waitcumsumflag-0b3cb9c8cb` | `MoeDistributeDispatchV2FullMesh::WaitCumSumFlag` | method | L1859–L1892 | false | LocalWindowCopy / — |
| 49 | `m-moedistributedispatchv2fullmesh-setvalidexpertinfo-6b263412eb` | `MoeDistributeDispatchV2FullMesh::SetValidExpertInfo` | method | L1894–L1919 | false | LocalWindowCopy / — |
| 50 | `m-moedistributedispatchv2fullmesh-checkdataarrivewithflag-99021413c7` | `MoeDistributeDispatchV2FullMesh::CheckDataArriveWithFlag` | method | L1921–L2049 | false | WaitAndFormatOutput / — |
| 51 | `m-moedistributedispatchv2fullmesh-copyinandout-da9b81eb3f` | `MoeDistributeDispatchV2FullMesh::CopyInAndOut` | method | L2051–L2098 | false | WaitAndFormatOutput / — |
| 52 | `m-moedistributedispatchv2fullmesh-waitandformatoutput-71e0265973` | `MoeDistributeDispatchV2FullMesh::WaitAndFormatOutput` | method | L2100–L2182 | false | LocalWindowCopy / CheckDataArriveWithFlag, CopyInAndOut |
| 53 | `m-moedistributedispatchv2fullmesh-runposrecord-a1ffd8ca5e` | `MoeDistributeDispatchV2FullMesh::RunPosRecord` | method | L2184–L2193 | true | — / — |
| 54 | `m-moedistributedispatchv2fullmesh-localwindowcopy-68c5075b26` | `MoeDistributeDispatchV2FullMesh::LocalWindowCopy` | method | L2195–L2252 | false | Process / SplitToCore, WaitCumSumFlag, SetValidExpertInfo, WaitAndFormatOutput |
| 55 | `m-moedistributedispatchv2fullmesh-tokenactivemaskcal-962a68fb09` | `MoeDistributeDispatchV2FullMesh::TokenActiveMaskCal` | method | L2254–L2277 | false | ExpIdsCopyAndMaskCal / — |
| 56 | `m-moedistributedispatchv2fullmesh-calvalidbscnt-33a4841789` | `MoeDistributeDispatchV2FullMesh::CalValidBSCnt` | method | L2279–L2309 | false | ExpertActiveMaskCal / — |
| 57 | `m-moedistributedispatchv2fullmesh-calvalidexpidx-8971214ed0` | `MoeDistributeDispatchV2FullMesh::CalValidExpIdx` | method | L2311–L2334 | false | ExpertActiveMaskCal / — |
| 58 | `m-moedistributedispatchv2fullmesh-expertactivemaskinit-af6310d8cb` | `MoeDistributeDispatchV2FullMesh::ExpertActiveMaskInit` | method | L2336–L2346 | false | ExpIdsCopyAndMaskCal / — |
| 59 | `m-moedistributedispatchv2fullmesh-expertactivemaskcal-abd5ee8a73` | `MoeDistributeDispatchV2FullMesh::ExpertActiveMaskCal` | method | L2348–L2365 | false | ExpIdsCopyAndMaskCal / CalValidBSCnt, CalValidExpIdx |
| 60 | `m-moedistributedispatchv2fullmesh-maskzerocomputeexpert-fe6a3a3ce9` | `MoeDistributeDispatchV2FullMesh::MaskZeroComputeExpert` | method | L2367–L2402 | false | ZeroComputeExpertMaskCal / — |
| 61 | `m-moedistributedispatchv2fullmesh-generategathermasktensor-e52513fe4f` | `MoeDistributeDispatchV2FullMesh::GenerateGatherMaskTensor` | method | L2404–L2411 | false | ZeroComputeExpertMaskCal / — |
| 62 | `m-moedistributedispatchv2fullmesh-zerocomputeexpertmaskcal-6c2bf320f2` | `MoeDistributeDispatchV2FullMesh::ZeroComputeExpertMaskCal` | method | L2413–L2427 | false | ExpIdsCopyAndMaskCal / GenerateGatherMaskTensor, MaskZeroComputeExpert |
| 63 | `m-moedistributedispatchv2fullmesh-expidscopyandmaskcal-17a5b857e1` | `MoeDistributeDispatchV2FullMesh::ExpIdsCopyAndMaskCal` | method | L2429–L2478 | false | AllToAllDispatch, CalCumSum, RingDoorbell / ExpertActiveMaskInit, TokenActiveMaskCal, ExpertActiveMaskCal, ZeroComputeExpertMaskCal |
| 64 | `m-moedistributedispatchv2fullmesh-get-sqs-and-cqs-xb-9ca4595de6` | `MoeDistributeDispatchV2FullMesh::get_sqs_and_cqs_xb` | method | L2519–L2594 | false | RingDoorbell / — |
| 65 | `f-moedistributedispatchv2fullmeshimpl-get-sqs-and-cqs-xb-ub-2cc6fc9d77` | `MoeDistributeDispatchV2FullMeshImpl::get_sqs_and_cqs_xb_ub` | free_function | L2596–L2715 | true | — / — |
| 66 | `f-moedistributedispatchv2fullmeshimpl-get-sqs-and-cqs-xb-ub-v2-76be68c05e` | `MoeDistributeDispatchV2FullMeshImpl::get_sqs_and_cqs_xb_ub_v2` | free_function | L2717–L2833 | true | — / — |
| 67 | `f-moedistributedispatchv2fullmeshimpl-get-sqs-and-cqs-xb-ub-v3-5d39e16cd7` | `MoeDistributeDispatchV2FullMeshImpl::get_sqs_and_cqs_xb_ub_v3` | free_function | L2836–L2891 | true | — / — |
| 68 | `f-moedistributedispatchv2fullmeshimpl-get-wqe-content-3e6b7c5e4a` | `MoeDistributeDispatchV2FullMeshImpl::get_wqe_content` | free_function | L2935–L2942 | false | simt_nw_mj_vf / — |
| 69 | `f-moedistributedispatchv2fullmeshimpl-simt-write-wqe-v5-f7eac0343f` | `MoeDistributeDispatchV2FullMeshImpl::simt_write_wqe_v5` | free_function | L2969–L3030 | true | — / — |
| 70 | `f-moedistributedispatchv2fullmeshimpl-simt-write-wqe-v4-48d4eea0cd` | `MoeDistributeDispatchV2FullMeshImpl::simt_write_wqe_v4` | free_function | L3032–L3093 | false | simt_nw_mj_vf / — |
| 71 | `f-moedistributedispatchv2fullmeshimpl-simt-write-wqe-v3-6d8d424864` | `MoeDistributeDispatchV2FullMeshImpl::simt_write_wqe_v3` | free_function | L3095–L3158 | true | — / — |
| 72 | `f-moedistributedispatchv2fullmeshimpl-simt-write-wqe-v2-d832a96558` | `MoeDistributeDispatchV2FullMeshImpl::simt_write_wqe_v2` | free_function | L3160–L3231 | true | — / — |
| 73 | `f-moedistributedispatchv2fullmeshimpl-simt-write-wqe-5b3a890c15` | `MoeDistributeDispatchV2FullMeshImpl::simt_write_wqe` | free_function | L3233–L3275 | true | — / — |
| 74 | `f-moedistributedispatchv2fullmeshimpl-simt-nw-mj-vf-dca9896a43` | `MoeDistributeDispatchV2FullMeshImpl::simt_nw_mj_vf` | free_function | L3277–L3408 | false | simt_nw_mj / get_wqe_content, simt_write_wqe_v4 |
| 75 | `f-moedistributedispatchv2fullmeshimpl-simt-nw-mj-689a46e20d` | `MoeDistributeDispatchV2FullMeshImpl::simt_nw_mj` | free_function | L3411–L3444 | false | URMASendToken / simt_nw_mj_vf |
| 76 | `f-moedistributedispatchv2fullmeshimpl-cachewritethrough-7000c8c3d6` | `MoeDistributeDispatchV2FullMeshImpl::cacheWriteThrough` | free_function | L3447–L3458 | false | URMAPollCQ, RingDoorbell / — |
| 77 | `f-moedistributedispatchv2fullmeshimpl-urmapollcq-4eae8cd065` | `MoeDistributeDispatchV2FullMeshImpl::URMAPollCQ` | free_function | L3460–L3498 | true | URMAPollCQ / cacheWriteThrough |
| 78 | `f-moedistributedispatchv2fullmeshimpl-urmapollcq-110d72f7d6` | `MoeDistributeDispatchV2FullMeshImpl::URMAPollCQ` | free_function | L3501–L3515 | true | — / URMAPollCQ |
| 79 | `m-moedistributedispatchv2fullmesh-urmasendtoken-d440368f92` | `MoeDistributeDispatchV2FullMesh::URMASendToken` | method | L3518–L3889 | false | Process / GetSqsAddr, GetHeadRecordAddr, simt_prepare_mapping, GetWindAddrByRankId, GetSendBufferAddrByTokenId, GetHeadReadyAddr, buildRemoteWqeDesc, simt_nw_mj |
| 80 | `m-moedistributedispatchv2fullmesh-selfcopytoken-2eead1ce43` | `MoeDistributeDispatchV2FullMesh::SelfCopyToken` | method | L3892–L3998 | false | Process / GetActiveStageNum, simt_prepare_mapping, WaitAllStageDone, GetSendBufferAddrByTokenId, GetWindAddrByRankId |
| 81 | `m-moedistributedispatchv2fullmesh-ringdoorbell-a0c423ce68` | `MoeDistributeDispatchV2FullMesh::RingDoorbell` | method | L4001–L4276 | false | Process / GetActiveStageNum, GetSqsAddr, GetHeadReadyAddr, GetHeadRecordAddr, get_sqs_and_cqs_xb, cacheWriteThrough, set_gm_value, ExpIdsCopyAndMaskCal, calc_rank_token_cnt, WaitAllStageDone |
| 82 | `m-moedistributedispatchv2fullmesh-process-0538141e33` | `MoeDistributeDispatchV2FullMesh::Process` | method | L4278–L4354 | false | — / AllToAllDispatch, PublishStageDone, URMASendToken, SelfCopyToken, RingDoorbell, CalCumSum, LocalWindowCopy |

完整签名、声明站点、参数、预处理条件、精确调用行及外部 callee 概览见 `inventory-code-index.json`。
