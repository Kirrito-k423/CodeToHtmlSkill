// PROTOTYPE — intentionally direct, stateful, and dependency-free.

const DATA = window.WALKTHROUGH_DATA;
const VARIANTS = {
  A: { name: "双图三轨", note: "E2E DAG / 调用 DAG / 源码并排" },
  B: { name: "代码中枢", note: "浅色代码居中，双侧 DAG 跟随" },
  C: { name: "DAG 画布", note: "全局执行图在上，调用图与源码在下" },
};

const CORE_EXTERNAL_APIS = [
  "DataCopy", "DataCopyPad", "InitBuffer", "SetGlobalBuffer", "PipeBarrier", "SyncAll", "SyncFunc",
  "atomicAdd", "atomicOr", "VF_CALL", "st_dev", "GetWindAddrByRankId", "GetSendBufferAddrByTokenId",
];

const E2E_POSITIONS = {
  orchestrate: [50, 7], contract: [17, 20], init: [50, 21], preprocess: [50, 35], pack: [50, 49],
  accounting: [82, 49], transport: [18, 68], selfcopy: [50, 68], doorbell: [82, 68], format: [50, 89],
};

const E2E_WIDE_POSITIONS = {
  orchestrate: [7, 53], contract: [18, 22], init: [18, 63], preprocess: [31, 63], pack: [44, 63],
  accounting: [56, 22], transport: [59, 63], selfcopy: [71, 63], doorbell: [83, 63], format: [94, 53],
};

const E2E_EDGES = [
  ["contract", "init"], ["orchestrate", "init"], ["orchestrate", "accounting"], ["init", "preprocess"],
  ["preprocess", "pack"], ["pack", "transport"], ["pack", "selfcopy"], ["pack", "doorbell"],
  ["accounting", "format"], ["transport", "format"], ["selfcopy", "format"], ["doorbell", "format"],
  ["doorbell", "transport", "handshake"],
];

const state = {
  variant: new URLSearchParams(location.search).get("variant") || "A",
  moduleId: "orchestrate",
  functionName: "Process",
  segmentId: null,
  activeLine: 4279,
  drawerOpen: false,
  search: "",
  searchMatches: [],
  searchIndex: -1,
  lines: [],
  linePresentation: [],
  functions: [],
  annotations: new Map(),
  lastRenderedVariant: null,
  previousVisual: null,
};

if (!VARIANTS[state.variant]) state.variant = "A";

const esc = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

function moduleForLine(line) {
  return DATA.modules.find((item) => line >= item.range[0] && line <= item.range[1])
    || DATA.modules.find((item) => item.id === "orchestrate");
}

function extractFunctions(lines) {
  const starts = [];
  const patterns = [
    /MoeDistributeDispatchV2FullMesh<.*>::([A-Za-z_][A-Za-z0-9_]*)\s*\(/,
    /(?:inline\s+)?(?:void|uint32_t|int32_t|uint64_t)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/,
  ];
  for (let i = 0; i < lines.length; i += 1) {
    const windowText = lines[i];
    let name = null;
    for (const pattern of patterns) {
      const match = windowText.match(pattern);
      if (match) { name = match[1]; break; }
    }
    if (!name || starts.some((item) => item.name === name)) continue;
    if (lines.slice(i, i + 5).join(" ").includes(";")) {
      const open = lines.slice(i, i + 5).join(" ").indexOf("{");
      const semicolon = lines.slice(i, i + 5).join(" ").indexOf(";");
      if (semicolon !== -1 && (open === -1 || semicolon < open)) continue;
    }
    starts.push({ name, start: i + 1 });
  }
  return starts.map((item, index) => {
    const next = starts[index + 1];
    const maxEnd = next ? next.start - 1 : lines.length;
    let depth = 0;
    let seenBrace = false;
    let end = Math.min(maxEnd, item.start + 360);
    for (let lineNo = item.start; lineNo <= maxEnd; lineNo += 1) {
      const raw = lines[lineNo - 1].replace(/\/\/.*$/, "");
      for (const ch of raw) {
        if (ch === "{") { depth += 1; seenBrace = true; }
        if (ch === "}") depth -= 1;
      }
      if (seenBrace && depth <= 0) { end = lineNo; break; }
    }
    const module = moduleForLine(item.start);
    return { ...item, end, moduleId: module.id, segments: [] };
  });
}

function inferSegment(lines, start, end, fnName, index) {
  const text = lines.slice(start - 1, end).join(" ");
  const title = `待复查 · ${fnName} L${start}–${end}`;
  const detail = "自动骨架只确认了函数边界和代码范围，尚未经过独立子代理逐行复查；禁止把这一节点当作代码语义解释。";
  const kind = "unreviewed";
  const apis = [...new Set((text.match(/\b[A-Z][A-Za-z0-9_]*(?=\s*\()/g) || []).slice(0, 4))];
  return { id: `${fnName}-${start}`, start, end, title, detail, kind, apis };
}

function buildSegments(fn) {
  const manual = manualSegments[fn.name];
  if (manual) return manual.map((segment) => ({ ...segment, id: `${fn.name}-${segment.start}` }));
  const segments = [];
  let cursor = fn.start;
  let index = 0;
  while (cursor <= fn.end) {
    let end = Math.min(fn.end, cursor + 7);
    const text = state.lines.slice(cursor - 1, end).join(" ");
    if ((text.match(/{/g) || []).length && end < fn.end) end = Math.min(fn.end, end + 2);
    segments.push(inferSegment(state.lines, cursor, end, fn.name, index));
    cursor = end + 1;
    index += 1;
  }
  return segments;
}

const manualSegments = {
  SetTilingDataAndCal: [
    { start: 773, end: 778, title: "载入 tiling，并把输入/输出物理宽度默认设为逻辑 H", detail: "SetTilingData 将 bs、H、K、rank 和 expert 拓扑写入成员；copyInAxisH_、copyOutAxisH_ 先继承 axisH_，后续只在打包类型下修正。", kind: "input", apis: ["SetTilingData"] },
    { start: 779, end: 783, title: "A3 FP4 输出宽度：逻辑 H 折算为打包字节数", detail: "仅在 __NPU_ARCH__ == 3510 且 ExpandXOutType 为两种 FP4 类型时，用 Ceil(axisH_, FP4_ELEMS_PER_BYTE) 得到 DMA 应处理的物理输出宽度。", kind: "guard", apis: ["Std::IsSame", "Ceil"] },
    { start: 784, end: 788, title: "A3 FP4 输入宽度：逻辑 H 折算为打包字节数", detail: "XType 为 FP4 时修正 copyInAxisH_；后续输入 token 地址步长和 hCopyParams_ 都使用这一物理宽度，避免把 FP4 元素数误当字节数。", kind: "guard", apis: ["Std::IsSame", "Ceil"] },
    { start: 789, end: 791, title: "应用弹性缩容映射，得到本轮有效 EP 拓扑", detail: "hasElasticInfoFlag_ 为真时，InitElasticInfo 从 GM 读取缩容映射并覆盖有效 epWorldSize_、epRankId_、sharedExpertRankNum_ 和 moeExpertNum_；后续派生量全部基于新拓扑。", kind: "transform", apis: ["InitElasticInfo"] },
    { start: 792, end: 798, title: "派生 rank/expert 布局与 BS×K 路由项数", detail: "先判断当前 rank 是否属于共享专家区；sharedExpertNum_ 非零时计算每个共享专家覆盖的 rank 数，再得到 MoE rank 数、每 rank expert 数和 expertIdsCnt_=axisBS_×axisK_。", kind: "compute", apis: [] },
    { start: 799, end: 801, title: "量化器确定 token 数据、scale 尾部与三元组起点", detail: "hOutSize_ 记录真实输出 payload 字节数；QuantInit 根据量化模式产出 hAlignSize_、scaleOutBytes_、tokenQuantAlign_ 和基础 hOutSizeAlign_，建立发送端与接收端共享的元数据锚点。", kind: "compute", apis: ["QuantInit"] },
    { start: 802, end: 806, title: "追加 32B 三元组槽和完整 top-k expert 列表", detail: "expandInfoSize 由一个 32B 三元组槽加对齐后的 K 个 expert ID 组成；它扩展 hAlignSize_，并用 tokenQuantAlign_×4+expandInfoSize 重建每 token 的逻辑记录末端，供接收端恢复原始 top-k slot。", kind: "transform", apis: ["Ceil"] },
    { start: 807, end: 810, title: "通信分帧：N×(480B 数据 + 32B 到达标志)", detail: "blockCntPerToken_ 按 480B 有效数据向上取整；hOutSizeAlignBlock_ 是纯数据容量，hCommuSize_ 用 512B 物理步长为每块保留 32B ready flag，axisHCommu_ 再换算为 XOutType 元素数。", kind: "compute", apis: ["Ceil"] },
    { start: 811, end: 814, title: "由通信帧和专家拓扑计算 window/status 容量", detail: "expertPerSizeOnWin_ 为单 expert window 容量；rscvStatusNum_ 根据当前 rank 类型选择 world-size 或 world-size×每 rank expert 数；totalExpertNum_ 和 statusCntAlign_ 建立状态数组长度。", kind: "compute", apis: ["Ceil"] },
    { start: 815, end: 820, title: "将 cumsum 核数夹在 1、半数 AIV、上限和状态数之间", detail: "先按每核约 16 个 expert 估算 aivUsedCumSum_，再依次限制为至少 1、最多一半 AIV、不超过 CUMSUM_MAX_CORE_NUM 且每核至少处理一个状态，最后从尾部划出 cumsum 核。", kind: "guard", apis: [] },
    { start: 821, end: 831, title: "划分 stage、共享专家、远端 WQE 与 self-copy AIV 角色", detail: "扣除 cumsum 与 doorbell 核得到 stage 核；共享专家存在时按 sharedExpertNum_ 与 axisK_ 比例分核且至少 1 个，剩余为 MoE staging；再划出 remote WQE/self-copy，并计算全局 jetty 数。", kind: "output", apis: [] },
  ],
  Process: [
    { start: 4279, end: 4294, title: "进入 AIV 调度域", detail: "记录时钟并确认当前核为 AIV；Process 是整份代码的导航入口。", kind: "input", apis: ["DebugClock", "ASCEND_IS_AIV"] },
    { start: 4295, end: 4305, title: "Stage：本地重排并发布完成", detail: "负责 stage 的 AIV 先执行 AllToAllDispatch，把 token 写入发送区，再发布完成标记。", kind: "transform", apis: ["AllToAllDispatch", "PublishStageDone"] },
    { start: 4306, end: 4311, title: "发送角色分流", detail: "前一组 AIV 构造远端 URMA 发送；其余 stage AIV 处理本 rank 快路径。", kind: "guard", apis: ["URMASendToken", "SelfCopyToken"] },
    { start: 4313, end: 4324, title: "Doorbell / CumSum 并发角色", detail: "未参与 stage 的 AIV 分别通知队列或计算 expert token 前缀和。", kind: "reduce", apis: ["RingDoorbell", "CalCumSum"] },
    { start: 4325, end: 4333, title: "汇合：整理目标侧窗口", detail: "每个角色完成自身任务后进入 LocalWindowCopy；依赖 flag 收敛，不是全核 barrier。", kind: "output", apis: ["PipeBarrier", "LocalWindowCopy"] },
    { start: 4337, end: 4352, title: "性能时钟回写", detail: "调试模式下计算各阶段 cycle 差并写入 sendTpCountOutGM_，不属于业务数据路径。", kind: "debug", apis: ["DataCopy", "SyncAll"] },
  ],
  AllToAllDispatch: [
    { start: 1366, end: 1377, title: "准备双缓冲与输入队列", detail: "根据当前 dataState 选择窗口并为 x 输入建立核内队列。", kind: "input", apis: ["InitBuffer"] },
    { start: 1378, end: 1395, title: "计算 mask 与量化临时区", detail: "只在需要时初始化 expert mask；量化模式决定 scale 与临时 buffer。", kind: "guard", apis: ["ExpertActiveMaskCal"] },
    { start: 1396, end: 1407, title: "复制并筛选 expertIds", detail: "生成有效 token/expert 索引；若没有有效 token 则提前结束。", kind: "filter", apis: ["ExpIdsCopyAndMaskCal"] },
    { start: 1408, end: 1416, title: "共享 expert 分支", detail: "共享专家使用独立 AIV 分区与目标 rank 规则。", kind: "guard", apis: ["SendToSharedExpert"] },
    { start: 1417, end: 1423, title: "MoE expert 重排", detail: "普通 MoE expert 路径计算 token 目标位置并写入发送暂存区。", kind: "output", apis: ["SendToMoeExpertNew"] },
  ],
  URMASendToken: [
    { start: 3519, end: 3537, title: "划出本 rank expert 空洞", detail: "计算本 rank 前后的远端 expert 数；单 WQE 核场景由后续 helper 过滤本卡。", kind: "guard", apis: [] },
    { start: 3538, end: 3583, title: "分配远端 expert worker", detail: "按两侧 expert 比例划分 WQE AIV，并处理余数与上下界。", kind: "transform", apis: [] },
    { start: 3588, end: 3664, title: "建立 mapping / SQ 工作区", detail: "空任务提前返回；其余核分配 expert offset、远端地址、SQ head 与 WQE 描述符缓冲。", kind: "memory", apis: ["InitBuffer", "GetSqsAddr"] },
    { start: 3673, end: 3736, title: "expert → token 稳定映射", detail: "搬入 expertIds，并行计数每 expert 的 token slot，再按源 offset 建立稳定顺序。", kind: "transform", apis: ["DataCopyPad", "simt_prepare_mapping", "atomicAdd"] },
    { start: 3746, end: 3781, title: "远端地址表与 head-ready 握手", detail: "构造各目标 rank 窗口基址；自旋等待 doorbell 核发布可预留的 SQ head。", kind: "sync", apis: ["GetWindAddrByRankId", "GetHeadReadyAddr"] },
    { start: 3783, end: 3818, title: "批量构造 WQE 描述符", detail: "按批次把 expert slot 转换为 token staging 源地址和远端 expert window 目的地址。", kind: "loop", apis: ["buildRemoteWqeDesc"] },
    { start: 3819, end: 3865, title: "写 SQ 并发布 ready bitmap", detail: "为每个 SQ 原子预留连续 head，写硬件 WQE，再把完成位发布给 doorbell 核。", kind: "api", apis: ["simt_nw_mj", "atomicAdd", "atomicOr"] },
    { start: 3868, end: 3889, title: "结束 WQE 生产阶段", detail: "记录阶段结束时间；CQ quiet 逻辑当前被注释，不属于主调用链。", kind: "debug", apis: ["DebugClock"] },
  ],
  RingDoorbell: [
    { start: 4002, end: 4047, title: "准备 SQ / CQ 控制面", detail: "分配 rank 计数与 head 工作区，定位共享内存中的队列结构。", kind: "input", apis: ["get_sqs_and_cqs_xb", "cacheWriteThrough"] },
    { start: 4066, end: 4104, title: "清 head-record 并发布 ready", detail: "先清上轮 bitmap，再读取 SQ head，把 head-ready 信号交给 WQE 生产核。", kind: "sync", apis: ["DataCopy", "headReadyFlag"] },
    { start: 4108, end: 4153, title: "统计各远端 rank token", detail: "根据 expertIds 计算每个非本 rank 的 token 数，决定 doorbell 完成条件。", kind: "reduce", apis: ["calc_rank_token_cnt"] },
    { start: 4157, end: 4159, title: "等待 staging 完成", detail: "确保本地 token staging 已对后续远端 DMA 可见。", kind: "sync", apis: ["WaitAllStageDone"] },
    { start: 4163, end: 4225, title: "扫描连续 ready bitmap", detail: "从旧 head 起只消费连续置位的 WQE，正确处理 32-bit word 内偏移和环回。", kind: "loop", apis: [] },
    { start: 4244, end: 4276, title: "敲 doorbell 并判断全局完成", detail: "把连续 ready 数推进到 SQ head；所有目标 rank 完成后退出。", kind: "output", apis: ["st_dev"] },
  ],
  CalCumSum: [
    { start: 1827, end: 1840, title: "统计并发送本 rank 计数", detail: "预处理 expertIds/mask，按 expert 统计 token 数并写目标 rank 状态窗口。", kind: "input", apis: ["ExpIdsCopyAndMaskCal", "CalAndSendCnt"] },
    { start: 1841, end: 1847, title: "划分并等待远端计数", detail: "把状态项分给多个 cumsum 核，自旋等待负责区间的 ready flag 全部到齐。", kind: "sync", apis: ["SplitToCore", "WaitDispatch"] },
    { start: 1849, end: 1857, title: "前缀和与专家计数输出", detail: "生成 sendCountsOut / AIV workspace；首个 cumsum 核额外汇总 expertTokenNums。", kind: "output", apis: ["CalRecvAndSetFlag", "SetExpertTokenNums"] },
  ],
  LocalWindowCopy: [
    { start: 2196, end: 2209, title: "重建接收阶段缓冲", detail: "重置 pipe，分配 cumsum/status 缓冲，并把接收状态项拆分给各 AIV。", kind: "input", apis: ["InitBuffer", "SplitToCore"] },
    { start: 2210, end: 2214, title: "等待 cumsum 完成", detail: "自旋等待所有 cumsum 核的完成 flag；没有接收任务的 AIV 可提前返回。", kind: "sync", apis: ["WaitCumSumFlag"] },
    { start: 2215, end: 2235, title: "建立有效来源工作集", detail: "分配 expert map / finished / left 状态，并从前缀和中筛出非零来源块。", kind: "transform", apis: ["SetValidExpertInfo"] },
    { start: 2237, end: 2252, title: "轮询到达并格式化输出", detail: "初始化 flag 检测状态，轮询完整 batch，写 expandX / scales / expandIdx 后清 flag。", kind: "output", apis: ["WaitAndFormatOutput"] },
  ],
  WaitAndFormatOutput: [
    { start: 2101, end: 2121, title: "布局接收轮询 UB", detail: "把通用缓冲切分为输入、输出、scale 和三元组索引视图。", kind: "memory", apis: [] },
    { start: 2125, end: 2132, title: "轮转选择有效来源", detail: "跳过已经完成或无需收集的来源块，维持环形轮询公平性。", kind: "loop", apis: [] },
    { start: 2135, end: 2146, title: "计算窗口地址并检查到达", detail: "定位当前源 expert 的窗口块，用尾部 flag 判断完整可消费 token 数。", kind: "sync", apis: ["CheckDataArriveWithFlag"] },
    { start: 2150, end: 2170, title: "搬运输出并清消费 flag", detail: "完整 batch 到达后写 expandX / scales / expandIdx，推进计数；来源完成后清对应 flag。", kind: "output", apis: ["CopyInAndOut"] },
    { start: 2172, end: 2182, title: "推进来源并退出", detail: "未到齐则轮询下一来源；所有有效来源完成后退出接收状态机。", kind: "guard", apis: [] },
  ],
};

function indexSource() {
  state.functions = extractFunctions(state.lines);
  for (const fn of state.functions) fn.segments = buildSegments(fn);
  for (let line = 1; line <= state.lines.length; line += 1) {
    const fn = [...state.functions].reverse().find((item) => line >= item.start && line <= item.end);
    const segment = fn?.segments.find((item) => line >= item.start && line <= item.end);
    state.annotations.set(line, { fn, segment, module: moduleForLine(line) });
  }
  state.linePresentation = state.lines.map((raw) => ({
    html: syntax(raw) || "&nbsp;",
    tags: lineTags(raw).map((tag) => `<i class="tag tag-${tag.type}" title="${esc(tag.label)}">${tag.type}</i>`).join(""),
    types: [...new Set(lineTags(raw).map((tag) => tag.type))],
  }));
}

function activeModule() {
  return DATA.modules.find((item) => item.id === state.moduleId) || DATA.modules[0];
}

function activeFunction() {
  return state.functions.find((item) => item.name === state.functionName)
    || state.functions.find((item) => item.moduleId === state.moduleId)
    || state.functions[0];
}

function chooseModule(moduleId, preferredFunction = null) {
  state.moduleId = moduleId;
  const module = activeModule();
  const primary = preferredFunction || module.functions.find((name) => state.functions.some((item) => item.name === name));
  const fn = state.functions.find((item) => item.moduleId === moduleId && item.name === primary)
    || state.functions.find((item) => item.moduleId === moduleId)
    || activeFunction();
  state.functionName = fn.name;
  state.segmentId = fn.segments[0]?.id || null;
  state.activeLine = fn.start;
  render();
  requestAnimationFrame(() => scrollToLine(fn.start));
}

function chooseFunction(name) {
  const fn = state.functions.find((item) => item.name === name);
  if (!fn) return;
  state.functionName = name;
  state.moduleId = fn.moduleId;
  state.segmentId = fn.segments[0]?.id || null;
  state.activeLine = fn.start;
  render();
  requestAnimationFrame(() => scrollToLine(fn.start));
}

function chooseSegment(id) {
  const fn = activeFunction();
  const segment = fn.segments.find((item) => item.id === id);
  if (!segment) return;
  state.segmentId = id;
  state.activeLine = segment.start;
  render();
  requestAnimationFrame(() => scrollToLine(segment.start));
}

function reverseNavigate(line) {
  const hit = state.annotations.get(line);
  if (!hit) return;
  state.activeLine = line;
  state.moduleId = hit.module.id;
  if (hit.fn) state.functionName = hit.fn.name;
  if (hit.segment) state.segmentId = hit.segment.id;
  render();
  requestAnimationFrame(() => scrollToLine(line));
}

function scrollToLine(line) {
  const target = document.querySelector(`[data-line="${line}"]`);
  const container = target?.closest(".code-scroll");
  if (target && container) container.scrollTop = Math.max(0, target.offsetTop - container.clientHeight / 2);
}

function e2eDag(mode = "tall") {
  const current = activeModule();
  const positions = mode === "wide" ? E2E_WIDE_POSITIONS : E2E_POSITIONS;
  const paths = E2E_EDGES.map(([fromId, toId, type]) => {
    const [x1, y1] = positions[fromId];
    const [x2, y2] = positions[toId];
    const midY = (y1 + y2) / 2;
    return `<path class="dag-edge ${type || ""}" d="M ${x1} ${y1 + 4} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2 - 4}" marker-end="url(#dag-arrow)" />`;
  }).join("");
  return `<div class="e2e-dag dag-${mode}">
    <svg class="dag-wires" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <defs><marker id="dag-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="4" markerHeight="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z"></path></marker></defs>
      ${paths}
    </svg>
    ${DATA.modules.map((module) => {
      const [x, y] = positions[module.id];
      return `<button class="dag-node e2e-node ${module.id === current.id ? "selected" : ""}" data-action="module" data-value="${module.id}" style="--node:${module.color};--x:${x};--y:${y}">
        <span>${module.step}</span><strong>${esc(module.name.split(" · ")[0])}</strong><small>${esc(module.name.split(" · ")[1] || module.short)}</small><em>L${module.range[0]}–${module.range[1]}</em>
      </button>`;
    }).join("")}
    <div class="dag-legend"><span><i></i>调用 / 数据依赖</span><span><i class="dash"></i>head 握手</span></div>
  </div>`;
}

function syntax(raw) {
  const commentAt = raw.indexOf("//");
  const code = commentAt === -1 ? raw : raw.slice(0, commentAt);
  const comment = commentAt === -1 ? "" : raw.slice(commentAt);
  const registry = [];
  const seen = new Set();
  DATA.coreSymbols.forEach((item) => {
    if (!seen.has(item.pattern)) { registry.push(item); seen.add(item.pattern); }
  });
  state.functions.forEach((item) => {
    if (!seen.has(item.name)) { registry.push({ pattern: item.name, type: "call", label: "内部函数接口" }); seen.add(item.name); }
  });
  CORE_EXTERNAL_APIS.forEach((name) => {
    if (!seen.has(name)) { registry.push({ pattern: name, type: "api", label: "底层 API" }); seen.add(name); }
  });
  registry.sort((a, b) => b.pattern.length - a.pattern.length);
  const placeholders = [];
  let protectedCode = code;
  registry.forEach((item) => {
    const pattern = item.pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    protectedCode = protectedCode.replace(new RegExp(`\\b${pattern}\\b`, "g"), (match) => {
      const marker = String.fromCodePoint(0xE100 + placeholders.length);
      placeholders.push({ marker, match, ...item });
      return marker;
    });
  });
  let html = esc(protectedCode);
  html = html.replace(/\b(template|typename|class|struct|if|else|for|while|return|constexpr|inline|void|auto|int|int32_t|uint32_t|uint64_t|bool|float|using|namespace|static_cast|reinterpret_cast)\b/g, '<span class="tok-key">$1</span>');
  html = html.replace(/\b(\d+(?:U|UL|F)?)\b/g, '<span class="tok-num">$1</span>');
  placeholders.forEach((item) => {
    html = html.replace(item.marker, `<strong class="sym sym-${item.type}" title="${esc(item.label)}">${esc(item.match)}</strong>`);
  });
  if (comment) html += `<span class="tok-comment">${esc(comment)}</span>`;
  return html;
}

function lineTags(raw) {
  const tags = [];
  for (const symbol of DATA.coreSymbols) {
    if (raw.includes(symbol.pattern)) tags.push(symbol);
  }
  if (/\b(for|while)\s*\(/.test(raw) && !tags.some((x) => x.type === "loop")) tags.push({ type: "loop", label: "循环" });
  if (/\bif\s*\(/.test(raw)) tags.push({ type: "guard", label: "分支" });
  return tags.slice(0, 2);
}

function codeRows() {
  const module = activeModule();
  const fn = activeFunction();
  const segment = fn.segments.find((item) => item.id === state.segmentId);
  const query = state.search.trim().toLowerCase();
  return state.lines.map((raw, index) => {
    const line = index + 1;
    const inModule = line >= module.range[0] && line <= module.range[1];
    const inFunction = line >= fn.start && line <= fn.end;
    const inSegment = segment && line >= segment.start && line <= segment.end;
    const isSearch = query && raw.toLowerCase().includes(query);
    const isCurrentSearch = state.searchIndex >= 0 && state.searchMatches[state.searchIndex]?.line === line;
    const presented = state.linePresentation[index];
    const classes = ["code-line", ...presented.types.map((type) => `semantic-${type}`), inModule ? "in-module" : "muted", inFunction ? "in-function" : "", inSegment ? "in-segment" : "", isSearch ? "search-hit" : "", isCurrentSearch ? "current-search-hit" : "", line === state.activeLine ? "active-line" : ""].filter(Boolean).join(" ");
    return `<div class="${classes}" data-line="${line}" style="--module:${module.color}">
      <button class="line-no" data-action="reverse" data-value="${line}" title="同步解释到第 ${line} 行">${line}</button>
      <code>${presented.html}</code>
      <span class="line-tags">${presented.tags}</span>
      <button class="line-jump" data-action="reverse" data-value="${line}" aria-label="反向定位到解释">↖ 解释</button>
    </div>`;
  }).join("");
}

function flowNodes(horizontal = false) {
  const current = activeModule();
  return `<div class="flow-list ${horizontal ? "flow-horizontal" : ""}">
    ${DATA.modules.map((module, index) => `<button class="flow-node ${module.id === current.id ? "selected" : ""}" data-action="module" data-value="${module.id}" style="--node:${module.color}">
      <span class="flow-step">${module.step}</span>
      <span class="flow-copy"><strong>${esc(module.name)}</strong><small>${esc(module.short)}</small></span>
      <span class="flow-range">L${module.range[0]}–${module.range[1]}</span>
      ${index < DATA.modules.length - 1 ? '<span class="flow-link" aria-hidden="true"></span>' : ""}
    </button>`).join("")}
  </div>`;
}

function callsForSegment(fn, segment) {
  const text = state.lines.slice(segment.start - 1, segment.end).map((line) => line.replace(/\/\/.*$/, "")).join("\n");
  const names = [...(segment.apis || []), ...state.functions.map((item) => item.name), ...CORE_EXTERNAL_APIS];
  const unique = [];
  names.forEach((name) => {
    if (!name || name === fn.name || unique.includes(name)) return;
    const pattern = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    if (new RegExp(`\\b${pattern}\\b`).test(text) || (segment.apis || []).includes(name)) unique.push(name);
  });
  return unique.slice(0, 5).map((name) => ({ name, fn: state.functions.find((item) => item.name === name) }));
}

function objectsForFunction(fn, type) {
  const text = state.lines.slice(fn.start - 1, fn.end).join("\n");
  return DATA.coreSymbols.filter((item) => item.type === type && text.includes(item.pattern)).slice(0, 5);
}

function functionPanel() {
  const module = activeModule();
  const fn = activeFunction();
  const segment = fn.segments.find((item) => item.id === state.segmentId) || fn.segments[0];
  const inputs = objectsForFunction(fn, "input");
  const outputs = objectsForFunction(fn, "output");
  return `<div class="logic-head">
      <div><span class="eyebrow">函数调用 DAG · 点击节点</span><h2>${esc(fn.name)}</h2></div>
      <span class="range-pill">L${fn.start}–${fn.end}</span>
    </div>
    <div class="object-strip">
      <div><span class="object-label input">IN</span>${(inputs.length ? inputs : [{ pattern: "函数参数 / GM tensor" }]).map((item) => `<b class="object-pill input">${esc(item.pattern)}</b>`).join("")}</div>
      <div><span class="object-label output">OUT</span>${(outputs.length ? outputs : [{ pattern: "目标窗口 / 状态" }]).map((item) => `<b class="object-pill output">${esc(item.pattern)}</b>`).join("")}</div>
    </div>
    <div class="call-dag-scroll"><div class="call-dag">
      <button class="call-root" data-action="function" data-value="${esc(fn.name)}"><span>ROOT</span><strong>${esc(fn.name)}</strong><em>L${fn.start}–${fn.end}</em></button>
      <div class="call-trunk">${fn.segments.map((item, index) => {
        const calls = callsForSegment(fn, item);
        return `<div class="call-row ${item.id === segment?.id ? "selected" : ""}">
          <button class="logic-node" data-action="segment" data-value="${item.id}">
            <span>${String(index + 1).padStart(2, "0")}</span><strong>${esc(item.title)}</strong><small>${esc(item.detail)}</small><em>L${item.start}–${item.end}</em>
          </button>
          <div class="child-calls">${calls.length ? calls.map((call) => `<button class="child-call ${call.fn ? "internal" : "external"}" data-action="${call.fn ? "function" : "segment"}" data-value="${call.fn ? esc(call.name) : item.id}"><span>${call.fn ? "子函数" : "底层 API"}</span><strong>${esc(call.name)}</strong>${call.fn ? `<em>L${call.fn.start}–${call.fn.end}</em>` : ""}</button>`).join("") : '<span class="leaf-node">数据变换 · 无子调用</span>'}</div>
        </div>`;
      }).join("")}</div>
    </div></div>`;
}

function codePanel() {
  return `<div class="code-head">
      <div><span class="eyebrow">完整源码 · 未省略</span><h2>${esc(DATA.source.name)}</h2></div>
      <div class="code-actions">
        <div class="search ${state.search ? "has-query" : ""}">
          <span class="search-icon">⌕</span>
          <input value="${esc(state.search)}" placeholder="查找符号" aria-label="在完整源码中查找" data-action="search" />
          <output class="search-count" aria-live="polite">${searchCountText()}</output>
          <button data-action="search-prev" title="上一处（Shift+Enter）" aria-label="上一处匹配" ${state.searchMatches.length ? "" : "disabled"}>↑</button>
          <button data-action="search-next" title="下一处（Enter）" aria-label="下一处匹配" ${state.searchMatches.length ? "" : "disabled"}>↓</button>
        </div>
        <button data-action="drawer" class="context-button">术语 / API <span>⌘K</span></button>
      </div>
    </div>
    <div class="code-context">${codeContextContent()}</div>
    <div class="code-scroll" tabindex="0">${codeRows()}</div>`;
}

function searchCountText() {
  if (!state.search.trim()) return "0 / 0";
  if (!state.searchMatches.length) return "无结果";
  return `${state.searchIndex + 1} / ${state.searchMatches.length}`;
}

function collectSearchMatches(query) {
  const needle = query.trim().toLowerCase();
  if (!needle) return [];
  const matches = [];
  state.lines.forEach((raw, index) => {
    const haystack = raw.toLowerCase();
    let cursor = 0;
    while (cursor <= haystack.length - needle.length) {
      const found = haystack.indexOf(needle, cursor);
      if (found === -1) break;
      matches.push({ line: index + 1, column: found + 1 });
      cursor = found + Math.max(needle.length, 1);
    }
  });
  return matches;
}

function refreshSearchControls() {
  const count = document.querySelector(".search-count");
  if (count) {
    count.textContent = searchCountText();
    const uniqueLines = new Set(state.searchMatches.map((match) => match.line)).size;
    count.title = state.searchMatches.length ? `共 ${state.searchMatches.length} 处，分布在 ${uniqueLines} 行` : "没有匹配结果";
  }
  const box = document.querySelector(".search");
  box?.classList.toggle("has-query", Boolean(state.search.trim()));
  box?.classList.toggle("no-result", Boolean(state.search.trim()) && !state.searchMatches.length);
  document.querySelectorAll('[data-action="search-prev"], [data-action="search-next"]').forEach((button) => {
    button.disabled = !state.searchMatches.length;
  });
}

function applySearchHighlights() {
  const matchedLines = new Set(state.searchMatches.map((match) => match.line));
  const currentLine = state.searchIndex >= 0 ? state.searchMatches[state.searchIndex]?.line : null;
  document.querySelectorAll(".code-line").forEach((element) => {
    const line = Number(element.dataset.line);
    element.classList.toggle("search-hit", matchedLines.has(line));
    element.classList.toggle("current-search-hit", line === currentLine);
  });
  refreshSearchControls();
}

function navigateSearch(delta) {
  if (!state.searchMatches.length) return;
  state.searchIndex = (state.searchIndex + delta + state.searchMatches.length) % state.searchMatches.length;
  const match = state.searchMatches[state.searchIndex];
  reverseNavigate(match.line);
  applySearchHighlights();
}

function updateSearch(query) {
  state.search = query;
  state.searchMatches = collectSearchMatches(query);
  state.searchIndex = state.searchMatches.length ? 0 : -1;
  applySearchHighlights();
  if (state.searchMatches.length) navigateSearch(0);
}

function codeContextContent() {
  const module = activeModule();
  const fn = activeFunction();
  return `<span style="--dot:${module.color}"><i></i>${esc(module.name)}</span>
    <b>${esc(fn.name)}</b>
    <span>当前行 ${state.activeLine}</span>
    <span class="coverage">覆盖 ${state.lines.length}/${DATA.source.expectedLines} 行</span>`;
}

function tipsPanel() {
  const module = activeModule();
  return `<section class="tips-card" style="--tip:${module.color}">
    <div class="tips-title"><span>ALG</span><strong>算法提示</strong></div>
    ${module.tips.map((tip) => `<p>${esc(tip)}</p>`).join("")}
  </section>`;
}

function header() {
  const module = activeModule();
  return `<header class="topbar">
    <div class="brand"><span class="brand-mark">C/</span><span><b>Code Walkthrough</b><small>THROWAWAY PROTOTYPE</small></span></div>
    <div class="source-summary"><span class="pulse" style="--pulse:${module.color}"></span><b>${esc(DATA.source.purpose)}</b></div>
    <div class="meta"><span>${DATA.source.language}</span><span>${state.lines.length.toLocaleString()} LOC</span><button data-action="drawer" aria-label="打开上下文抽屉">☰</button></div>
  </header>`;
}

function variantA() {
  return `<div class="app-shell variant-a">${header()}
    <main class="tracks">
      <section class="panel flow-panel"><div class="panel-head"><span class="eyebrow">E2E DAG · 点击节点</span><h1>Token dispatch 全景</h1><p>实线表示执行/数据依赖，虚线表示 WQE 与 doorbell 的 head 握手。</p></div>${e2eDag("tall")}${tipsPanel()}</section>
      <section class="panel logic-panel">${functionPanel()}</section>
      <section class="panel source-panel">${codePanel()}</section>
    </main>${drawer()}${switcher()}</div>`;
}

function variantB() {
  const module = activeModule();
  return `<div class="app-shell variant-b">${header()}
    <main class="focus-grid">
      <aside class="rail"><div class="rail-title"><span>E2E DAG</span><strong>执行依赖</strong></div>${e2eDag("compact")}</aside>
      <section class="panel source-panel focus-code">${codePanel()}</section>
      <aside class="inspector"><div class="inspector-module" style="--accent:${module.color}"><span>${module.step} / MODULE DAG</span><h1>${esc(module.name)}</h1><p>${esc(module.short)}</p></div>${functionPanel()}${tipsPanel()}</aside>
    </main>${drawer()}${switcher()}</div>`;
}

function variantC() {
  const module = activeModule();
  return `<div class="app-shell variant-c">${header()}
    <main class="atlas">
      <section class="atlas-map"><div class="atlas-intro"><span class="eyebrow">E2E DAG 画布</span><h1>从 ${esc(module.name)} 观察 token</h1><p>${esc(DATA.source.purpose)}</p></div>${e2eDag("wide")}</section>
      <section class="atlas-bottom">
        <div class="panel logic-panel atlas-logic">${functionPanel()}${tipsPanel()}</div>
        <div class="panel source-panel atlas-code">${codePanel()}</div>
      </section>
    </main>${drawer()}${switcher()}</div>`;
}

function drawer() {
  const module = activeModule();
  return `<aside class="context-drawer ${state.drawerOpen ? "open" : ""}" aria-hidden="${!state.drawerOpen}">
    <div class="drawer-head"><div><span class="eyebrow">隐藏第 4 列</span><h2>上下文与术语</h2></div><button data-action="drawer">×</button></div>
    <section><h3>当前模块</h3><div class="drawer-module" style="--accent:${module.color}"><b>${esc(module.name)}</b><p>${esc(module.short)}</p><span>L${module.range[0]}–${module.range[1]}</span></div></section>
    <section><h3>视觉图例</h3><div class="legend"><span><i class="input"></i>输入对象</span><span><i class="output"></i>输出对象</span><span><i class="api"></i>核心 API</span><span><i class="sync"></i>同步点</span></div></section>
    <section><h3>术语词典</h3><div class="glossary">${DATA.glossary.map(([term, text]) => `<details><summary>${esc(term)}<span>＋</span></summary><p>${esc(text)}</p></details>`).join("")}</div></section>
    <section><h3>联动状态</h3><pre>${esc(JSON.stringify({ variant: state.variant, module: state.moduleId, function: state.functionName, segment: state.segmentId, line: state.activeLine }, null, 2))}</pre></section>
  </aside><button class="drawer-scrim ${state.drawerOpen ? "show" : ""}" data-action="drawer" aria-label="关闭抽屉"></button>`;
}

function switcher() {
  const keys = Object.keys(VARIANTS);
  const index = keys.indexOf(state.variant);
  return `<nav class="prototype-switcher" aria-label="原型变体切换">
    <button data-action="variant" data-value="${keys[(index - 1 + keys.length) % keys.length]}" aria-label="上一个变体">←</button>
    <span><small>UI PROTOTYPE</small><b>${state.variant} — ${VARIANTS[state.variant].name}</b><em>${VARIANTS[state.variant].note}</em></span>
    <button data-action="variant" data-value="${keys[(index + 1) % keys.length]}" aria-label="下一个变体">→</button>
  </nav>`;
}

function bind(root = document) {
  root.querySelectorAll("[data-action]:not([data-bound])").forEach((element) => {
    const action = element.dataset.action;
    element.dataset.bound = "true";
    if (action === "search") {
      element.addEventListener("input", (event) => {
        updateSearch(event.target.value);
      });
      element.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          navigateSearch(event.shiftKey ? -1 : 1);
        }
        if (event.key === "Escape" && state.search) {
          event.preventDefault();
          element.value = "";
          updateSearch("");
        }
      });
      return;
    }
    element.addEventListener("click", () => {
      const value = element.dataset.value;
      if (action === "module") chooseModule(value);
      if (action === "function") chooseFunction(value);
      if (action === "segment") chooseSegment(value);
      if (action === "reverse") reverseNavigate(Number(value));
      if (action === "search-prev") navigateSearch(-1);
      if (action === "search-next") navigateSearch(1);
      if (action === "drawer") toggleDrawer();
      if (action === "variant") setVariant(value);
    });
  });
}

function setVariant(variant) {
  state.variant = variant;
  const params = new URLSearchParams(location.search);
  params.set("variant", variant);
  history.replaceState({}, "", `${location.pathname}?${params}`);
  render(true);
  requestAnimationFrame(() => scrollToLine(state.activeLine));
}

function lineClass(line) {
  const module = activeModule();
  const fn = activeFunction();
  const segment = fn.segments.find((item) => item.id === state.segmentId);
  const raw = state.lines[line - 1];
  const query = state.search.trim().toLowerCase();
  const inModule = line >= module.range[0] && line <= module.range[1];
  const inFunction = line >= fn.start && line <= fn.end;
  const inSegment = segment && line >= segment.start && line <= segment.end;
  const isSearch = query && raw.toLowerCase().includes(query);
  const isCurrentSearch = state.searchIndex >= 0 && state.searchMatches[state.searchIndex]?.line === line;
  const types = state.linePresentation[line - 1]?.types || [];
  return ["code-line", ...types.map((type) => `semantic-${type}`), inModule ? "in-module" : "muted", inFunction ? "in-function" : "", inSegment ? "in-segment" : "", isSearch ? "search-hit" : "", isCurrentSearch ? "current-search-hit" : "", line === state.activeLine ? "active-line" : ""].filter(Boolean).join(" ");
}

function visualSnapshot() {
  const module = activeModule();
  const fn = activeFunction();
  const segment = fn.segments.find((item) => item.id === state.segmentId);
  return {
    moduleId: module.id,
    moduleRange: module.range,
    functionName: fn.name,
    functionRange: [fn.start, fn.end],
    segmentId: segment?.id || null,
    segmentRange: segment ? [segment.start, segment.end] : null,
    activeLine: state.activeLine,
  };
}

function refreshCodeState() {
  const module = activeModule();
  const next = visualSnapshot();
  const previous = state.previousVisual;
  const elements = document.querySelectorAll(".code-line");
  const affected = new Set();
  const addRange = (range) => {
    if (!range) return;
    for (let line = range[0]; line <= range[1]; line += 1) affected.add(line);
  };
  if (!previous) {
    addRange([1, state.lines.length]);
  } else {
    if (previous.moduleId !== next.moduleId) { addRange(previous.moduleRange); addRange(next.moduleRange); }
    if (previous.functionName !== next.functionName) { addRange(previous.functionRange); addRange(next.functionRange); }
    if (previous.segmentId !== next.segmentId) { addRange(previous.segmentRange); addRange(next.segmentRange); }
    affected.add(previous.activeLine);
    affected.add(next.activeLine);
  }
  affected.forEach((line) => {
    const element = elements[line - 1];
    if (!element) return;
    element.className = lineClass(line);
    element.style.setProperty("--module", module.color);
  });
  const context = document.querySelector(".code-context");
  if (context) context.innerHTML = codeContextContent();
  state.previousVisual = next;
}

function refreshDynamic() {
  const module = activeModule();
  document.querySelectorAll(".flow-node, .e2e-node").forEach((element) => element.classList.toggle("selected", element.dataset.value === module.id));
  let logicRoot;
  if (state.variant === "A") {
    logicRoot = document.querySelector(".logic-panel");
    logicRoot.innerHTML = functionPanel();
    const tip = document.querySelector(".flow-panel .tips-card");
    if (tip) tip.outerHTML = tipsPanel();
  } else if (state.variant === "B") {
    logicRoot = document.querySelector(".inspector");
    logicRoot.innerHTML = `<div class="inspector-module" style="--accent:${module.color}"><span>${module.step} / MODULE DAG</span><h1>${esc(module.name)}</h1><p>${esc(module.short)}</p></div>${functionPanel()}${tipsPanel()}`;
  } else {
    logicRoot = document.querySelector(".atlas-logic");
    logicRoot.innerHTML = `${functionPanel()}${tipsPanel()}`;
    const title = document.querySelector(".atlas-intro h1");
    if (title) title.textContent = `从 ${module.name} 观察 token`;
  }
  bind(logicRoot);
  refreshCodeState();
  if (state.drawerOpen) refreshDrawerContent();
}

function refreshDrawerContent() {
  const module = activeModule();
  const box = document.querySelector(".drawer-module");
  if (box) {
    box.style.setProperty("--accent", module.color);
    box.innerHTML = `<b>${esc(module.name)}</b><p>${esc(module.short)}</p><span>L${module.range[0]}–${module.range[1]}</span>`;
  }
  const pre = document.querySelector(".context-drawer pre");
  if (pre) pre.textContent = JSON.stringify({ variant: state.variant, module: state.moduleId, function: state.functionName, segment: state.segmentId, line: state.activeLine }, null, 2);
}

function toggleDrawer(force) {
  state.drawerOpen = typeof force === "boolean" ? force : !state.drawerOpen;
  const drawerElement = document.querySelector(".context-drawer");
  const scrim = document.querySelector(".drawer-scrim");
  drawerElement?.classList.toggle("open", state.drawerOpen);
  drawerElement?.setAttribute("aria-hidden", String(!state.drawerOpen));
  scrim?.classList.toggle("show", state.drawerOpen);
  if (state.drawerOpen) refreshDrawerContent();
}

function render(force = false) {
  if (!force && state.lastRenderedVariant === state.variant && document.querySelector(".code-scroll")) {
    refreshDynamic();
    return;
  }
  const app = document.getElementById("app");
  app.innerHTML = state.variant === "B" ? variantB() : state.variant === "C" ? variantC() : variantA();
  document.documentElement.dataset.variant = state.variant;
  state.lastRenderedVariant = state.variant;
  bind();
  state.previousVisual = visualSnapshot();
}

document.addEventListener("keydown", (event) => {
  const tag = event.target.tagName?.toLowerCase();
  if (["input", "textarea"].includes(tag) || event.target.isContentEditable) return;
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    const keys = Object.keys(VARIANTS);
    const index = keys.indexOf(state.variant);
    const delta = event.key === "ArrowLeft" ? -1 : 1;
    setVariant(keys[(index + delta + keys.length) % keys.length]);
  }
  if (event.key === "F3" && state.searchMatches.length) {
    event.preventDefault();
    navigateSearch(event.shiftKey ? -1 : 1);
  }
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    toggleDrawer();
  }
  if (event.key === "Escape" && state.drawerOpen) toggleDrawer(false);
});

fetch("./source.h")
  .then((response) => {
    if (!response.ok) throw new Error(`source.h ${response.status}`);
    return response.text();
  })
  .then((text) => {
    state.lines = text.replace(/\r/g, "").split("\n");
    if (state.lines.at(-1) === "") state.lines.pop();
    indexSource();
    const process = state.functions.find((item) => item.name === "Process");
    if (process) {
      state.functionName = process.name;
      state.segmentId = process.segments[0]?.id || null;
    }
    render(true);
    requestAnimationFrame(() => scrollToLine(state.activeLine));
  })
  .catch((error) => {
    document.getElementById("app").innerHTML = `<div class="fatal"><span>C/</span><h1>源码没有加载成功</h1><p>${esc(error.message)}</p><code>python3 prototype-code-walkthrough/server.py</code></div>`;
  });
