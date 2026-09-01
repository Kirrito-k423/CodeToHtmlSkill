#!/usr/bin/env python3
"""把冻结事实、E2E 架构和逐函数蓝图合并为 schema_version=2 分析 JSON。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:<[^;{}()]*>)?\s*\(")
ASSIGN_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*"
    r"(?:\+\+|--|\+=|-=|\*=|/=|%=|&=|\|=|\^=|=(?!=))"
)
PREFIX_UPDATE_RE = re.compile(r"(?:\+\+|--)\s*([A-Za-z_][A-Za-z0-9_]*)\b")
DECL_RE = re.compile(
    r"^(?:(?:const|constexpr|static|volatile|register|unsigned|signed|typename)\s+)*"
    r"(?:auto|bool|char|short|int|long|float|double|size_t|u?int(?:8|16|32|64)_t|"
    r"[A-Za-z_][A-Za-z0-9_:]*(?:\s*<[^;{}=]+>)?)"
    r"\s*(?:[*&]+\s*)?([A-Za-z_][A-Za-z0-9_]*)\b"
)

CPP_KEYWORDS = {
    "alignas", "alignof", "and", "asm", "auto", "bitand", "bitor", "bool", "break",
    "case", "catch", "char", "class", "compl", "concept", "const", "consteval",
    "constexpr", "constinit", "const_cast", "continue", "co_await", "co_return", "co_yield",
    "decltype", "default", "delete", "do", "double", "dynamic_cast", "else", "enum",
    "explicit", "export", "extern", "false", "float", "for", "friend", "goto", "if",
    "inline", "int", "long", "mutable", "namespace", "new", "noexcept", "not", "nullptr",
    "operator", "or", "private", "protected", "public", "register", "reinterpret_cast",
    "requires", "return", "short", "signed", "sizeof", "static", "static_assert",
    "static_cast", "struct", "switch", "template", "this", "thread_local", "throw", "true",
    "try", "typedef", "typeid", "typename", "union", "unsigned", "using", "virtual", "void",
    "volatile", "wchar_t", "while", "xor",
}
TYPE_WORDS = {
    "size_t", "int8_t", "int16_t", "int32_t", "int64_t", "uint8_t", "uint16_t",
    "uint32_t", "uint64_t", "GM_ADDR", "LocalTensor", "GlobalTensor", "TBuf", "TQue",
    "DataCopyParams", "DataCopyExtParams", "DataCopyPadParams", "DataCopyPadExtParams",
}
SYNC_APIS = {
    "SyncFunc", "PipeBarrier", "SyncAll", "ThreadBarrier", "__syncthreads", "set_flag",
    "wait_flag", "asc_threadfence", "DataCacheCleanAndInvalid", "aclshmemx_udma_quiet",
    "URMAPollCQ", "st_dev",
}
LINE_NOTE_KINDS = {
    "signature", "statement", "declaration", "branch", "loop", "call", "sync",
    "comment", "preprocessor", "brace", "blank",
}
WRITE_FIRST_ARG_APIS = {
    "DataCopy", "DataCopyPad", "Duplicate", "Copy", "Cast", "Add", "Sub", "Mul", "Muls",
    "Abs", "Sum", "ReduceSum", "GatherMask", "CompareScalar", "atomicAdd", "atomicOr",
}
BANNED_PHRASES = {
    "语义块 04", "条件守卫 / 路径选择", "继续执行当前函数的数据变换",
    "循环处理一批任务", "执行当前逻辑",
}
SEGMENT_FIELDS = {
    "id", "start", "end", "title", "detail", "kind", "input_state", "mechanism",
    "output_state", "why", "calls",
}
BLUEPRINT_FIELDS = {
    "module_id", "summary", "inputs", "outputs", "side_effects", "segments",
}
REVIEW_ARRAY_FIELDS = ("gaps", "overlaps", "unresolved", "required_changes")
PALETTE = (
    "#2457d6", "#1687a7", "#7a4db3", "#b66516", "#27805c", "#a4476a",
    "#51627a", "#846b20",
)


class ValidationError(RuntimeError):
    """输入事实或蓝图不满足正式分析门禁。"""


class ChineseArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        replacements = {
            "the following arguments are required:": "缺少必需参数：",
            "unrecognized arguments:": "无法识别的参数：",
            "expected one argument": "参数缺少取值",
        }
        for source, target in replacements.items():
            message = message.replace(source, target)
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: 参数错误：{message}\n")


def fail(message: str) -> None:
    raise ValidationError(message)


def load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"找不到{label}：{path}")
    except UnicodeDecodeError as exc:
        fail(f"{label}不是 UTF-8 文本：{path}（{exc}）")
    except json.JSONDecodeError as exc:
        fail(f"{label}不是有效 JSON：{path}:{exc.lineno}:{exc.colno}（{exc.msg}）")
    raise AssertionError("unreachable")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_sha(document: dict[str, Any], label: str) -> str:
    candidates: list[tuple[str, Any]] = []
    source = document.get("source")
    if isinstance(source, dict):
        candidates.append(("source.sha256", source.get("sha256")))
    candidates.extend(
        [
            ("source_sha256", document.get("source_sha256")),
            ("review_summary.source_sha256", (document.get("review_summary") or {}).get("source_sha256")
             if isinstance(document.get("review_summary"), dict) else None),
            ("review.source_sha256", (document.get("review") or {}).get("source_sha256")
             if isinstance(document.get("review"), dict) else None),
        ]
    )
    values = [(name, value) for name, value in candidates if value is not None]
    if not values:
        fail(f"{label}缺少源码 SHA-256（支持 source.sha256 或 source_sha256）")
    unique = {value for _, value in values}
    if len(unique) != 1:
        detail = "，".join(f"{name}={value}" for name, value in values)
        fail(f"{label}内部 SHA-256 不一致：{detail}")
    value = values[0][1]
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        fail(f"{label}的 SHA-256 必须是 64 位十六进制字符串")
    return value.lower()


def require_sha(document: dict[str, Any], label: str, expected: str) -> None:
    actual = artifact_sha(document, label)
    if actual != expected:
        fail(f"{label}的源码 SHA-256 与当前源码不一致：期望 {expected}，实际 {actual}")


def require_fields(record: dict[str, Any], fields: Iterable[str], label: str) -> None:
    missing = sorted(field for field in fields if field not in record)
    if missing:
        fail(f"{label}缺少必填字段：{', '.join(missing)}")


def ensure_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        fail(f"{label}必须是数组")
    return value


def ordered_unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def blueprint_symbol_name(value: Any, label: str) -> str:
    """允许蓝图用“源码标识符：解释”书写，同时返回可核对的标识符。"""
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} 必须是非空字符串")
    candidate = value.strip().split("：", 1)[0].split(":", 1)[0].strip().strip("`")
    if IDENT_RE.fullmatch(candidate) is None:
        fail(f"{label} 必须以单个真实源码标识符开头：{value!r}")
    return candidate


def compact(text: str, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", text.strip())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def normalized_explanation(text: str) -> str:
    """与正式渲染器一致地比较解释文本，防止同函数多行失去位置语境。"""
    return re.sub(r"[\s，。；：、,.!！?？/]+", "", text).lower()


def contextualize_duplicate_line_notes(
    notes: list[dict[str, Any]], segments: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """给重复动作补上所属语义段和行号，让相同 API 的多次出现仍可区分。"""
    counts: dict[str, int] = {}
    for note in notes:
        key = normalized_explanation(note["explanation"])
        counts[key] = counts.get(key, 0) + 1

    result: list[dict[str, Any]] = []
    for note in notes:
        item = copy.deepcopy(note)
        key = normalized_explanation(item["explanation"])
        if item["kind"] not in {"brace", "blank"} and counts.get(key, 0) > 1:
            segment = next(
                (candidate for candidate in segments
                 if candidate["start"] <= item["line"] <= candidate["end"]),
                None,
            )
            segment_title = segment["title"] if segment else "函数主体"
            item["explanation"] = (
                f"{item['explanation'].rstrip('。')}；此处位于「{segment_title}」语义段的 "
                f"L{item['line']}。"
            )
        result.append(item)
    return result


def extract_identifiers(code: str) -> list[str]:
    return ordered_unique(
        token for token in IDENT_RE.findall(code)
        if token not in CPP_KEYWORDS and token not in TYPE_WORDS
    )


def extract_calls(code: str) -> list[str]:
    return ordered_unique(name for name in CALL_RE.findall(code) if name not in CPP_KEYWORDS)


def extract_writes(code: str, calls: Sequence[str]) -> list[str]:
    writes = [match.group(1) for match in ASSIGN_RE.finditer(code)]
    writes.extend(match.group(1) for match in PREFIX_UPDATE_RE.finditer(code))
    declaration = DECL_RE.match(code.strip())
    if declaration and ";" in code:
        writes.append(declaration.group(1))
    writes.extend(
        match.group(1)
        for match in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\.|->)\s*SetValue\s*\(", code)
    )
    for api in calls:
        if api not in WRITE_FIRST_ARG_APIS:
            continue
        match = re.search(
            rf"\b{re.escape(api)}\s*(?:<[^;{{}}()]*>)?\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)",
            code,
        )
        if match:
            writes.append(match.group(1))
    return ordered_unique(writes)


def normalize_function_io(
    values: Sequence[Any], function_source: str, field: str
) -> tuple[list[str], list[str]]:
    """把 reviewer 的“标识符：说明”归一为前端可高亮的精确源码标识符。"""
    source_ids = set(IDENT_RE.findall(function_source))
    call_names = set(extract_calls(function_source))
    written_ids: set[str] = set()
    for line in function_source.splitlines():
        line_calls = extract_calls(line)
        written_ids.update(extract_writes(line, line_calls))
    normalized: list[str] = []
    details: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            fail(f"函数蓝图 {field}[{index}] 必须是非空字符串")
        text = value.strip()
        details.append(text)
        prefix = re.split(r"[：:]", text, maxsplit=1)[0]
        candidates = [
            token for token in IDENT_RE.findall(prefix)
            if token in source_ids and token not in CPP_KEYWORDS and token not in TYPE_WORDS
            and token not in call_names
        ]
        if not candidates and field.endswith("outputs"):
            candidates = [
                token for token in IDENT_RE.findall(text)
                if token in source_ids and token in written_ids
            ]
        normalized.extend(candidates)
    return ordered_unique(normalized), details


def strip_code_comments(line: str, in_block_comment: bool) -> tuple[str, bool]:
    """移除注释和字符串内容，同时保留括号位置以便做轻量结构识别。"""
    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    while index < len(line):
        char = line[index]
        nxt = line[index + 1] if index + 1 < len(line) else ""
        if in_block_comment:
            if char == "*" and nxt == "/":
                in_block_comment = False
                output.extend("  ")
                index += 2
            else:
                output.append(" ")
                index += 1
            continue
        if quote:
            output.append(" ")
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            output.append(" ")
            index += 1
        elif char == "/" and nxt == "/":
            output.extend(" " * (len(line) - index))
            break
        elif char == "/" and nxt == "*":
            in_block_comment = True
            output.extend("  ")
            index += 2
        else:
            output.append(char)
            index += 1
    return "".join(output), in_block_comment


def comment_only(line: str, was_in_block: bool) -> bool:
    stripped = line.strip()
    return was_in_block or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*")


def nearby_nonblank(lines: Sequence[str], index: int, direction: int) -> str:
    cursor = index + direction
    while 0 <= cursor < len(lines):
        candidate = compact(lines[cursor], 72)
        if candidate:
            return candidate
        cursor += direction
    return "函数边界"


def scope_label(code: str, previous_code: str, function_name: str) -> str:
    context = compact(code if code.strip(" {") else previous_code, 96)
    if re.search(r"\belse\s+if\b", context):
        return f"else-if 分支 `{context}`"
    if re.search(r"\bif\s*\(", context):
        return f"if 分支 `{context}`"
    if re.search(r"\belse\b", context):
        return "else 备选分支"
    if re.search(r"\bfor\s*\(", context):
        return f"for 循环 `{context}`"
    if re.search(r"\bwhile\s*\(", context):
        return f"while 循环 `{context}`"
    if re.search(r"\bswitch\s*\(", context):
        return f"switch 分派 `{context}`"
    if re.search(r"\bdo\b", context):
        return "do-while 循环"
    if not previous_code:
        return f"函数 `{function_name}` 主体"
    return f"代码块 `{context or function_name}`"


def sync_explanation(calls: Sequence[str], identifiers: Sequence[str]) -> str:
    names = "、".join(f"`{name}`" for name in calls if name in SYNC_APIS)
    if "PipeBarrier" in calls:
        return f"调用 {names}，等待源码指定流水线上的先前操作完成后再继续。"
    if "SyncFunc" in calls or "set_flag" in calls or "wait_flag" in calls:
        return f"调用 {names}，在本行指定的硬件事件或流水线之间建立先后关系。"
    if "ThreadBarrier" in calls or "__syncthreads" in calls or "SyncAll" in calls:
        return f"调用 {names}，使参与当前 `{identifiers[0] if identifiers else '函数'}` 阶段的线程或核在此汇合。"
    if "DataCacheCleanAndInvalid" in calls or "asc_threadfence" in calls:
        return f"调用 {names}，发布或刷新本行涉及地址的缓存可见性。"
    return f"调用同步相关 API {names}，完成其源码参数指定的通知或可见性动作。"


def make_line_notes(
    definition: dict[str, Any], source_lines: Sequence[str]
) -> list[dict[str, Any]]:
    start = definition["start"]
    end = definition["end"]
    name = definition["name"]
    signature_end = definition.get("signature_end")
    if not isinstance(signature_end, int):
        signature_end = definition.get("body_start", start)
    body_start = definition.get("body_start")
    if not isinstance(body_start, int):
        body_start = signature_end

    function_lines = list(source_lines[start - 1 : end])
    notes: list[dict[str, Any]] = []
    in_block_comment = False
    pp_stack: list[str] = []
    scope_stack: list[str] = []
    previous_code = ""

    for offset, raw in enumerate(function_lines):
        line_number = start + offset
        stripped = raw.strip()
        was_in_block = in_block_comment
        code, in_block_comment = strip_code_comments(raw, in_block_comment)
        code_stripped = code.strip()
        calls = extract_calls(code_stripped)
        writes = extract_writes(code_stripped, calls)
        identifiers = extract_identifiers(code_stripped)
        reads = [item for item in identifiers if item not in writes and item not in calls]

        closing_labels: list[str] = []
        for _ in range(code_stripped.count("}")):
            closing_labels.append(scope_stack.pop() if scope_stack else f"函数 `{name}` 的外层")

        preprocessor = stripped.startswith("#")
        is_comment = comment_only(raw, was_in_block) and not code_stripped
        brace_only = bool(code_stripped) and re.fullmatch(r"[{}();,\s]+", code_stripped) is not None

        if not stripped:
            before = nearby_nonblank(function_lines, offset, -1)
            after = nearby_nonblank(function_lines, offset, 1)
            kind = "blank"
            explanation = (
                f"空行在 `{name}` 的 L{line_number} 分隔 `{before}` 与 `{after}` 两段源码。"
            )
            reads = []
            writes = []
        elif preprocessor:
            kind = "preprocessor"
            directive = compact(stripped)
            if re.match(r"#\s*(if|ifdef|ifndef)\b", stripped):
                pp_stack.append(directive)
                explanation = f"用预处理条件 `{directive}` 决定后续实现是否进入本次编译。"
            elif re.match(r"#\s*(elif|else)\b", stripped):
                parent = pp_stack[-1] if pp_stack else "前述条件"
                explanation = f"从 `{parent}` 切换到备选预处理分支 `{directive}`。"
            elif re.match(r"#\s*endif\b", stripped):
                parent = pp_stack.pop() if pp_stack else "前述条件编译区"
                explanation = f"结束由 `{parent}` 打开的条件编译区域。"
            elif re.match(r"#\s*define\b", stripped):
                explanation = f"定义预处理宏 `{directive}`，供 `{name}` 的本编译单元使用。"
            else:
                explanation = f"应用预处理指令 `{directive}`，改变 `{name}` 所在编译单元的构建内容。"
            reads = []
            writes = []
        elif is_comment:
            kind = "comment"
            text = compact(re.sub(r"^\s*(?://+|/\*+|\*+|\*/)", "", stripped), 130)
            if not text:
                explanation = f"注释分隔符在 `{name}` 的 L{line_number} 标记说明区域边界，不产生运行时动作。"
            elif re.search(r"\b(?:printf|cout|DataCopy|return|if|for|while)\b|[;{}]", text):
                explanation = f"保留被注释的调试或历史代码 `{text}`；该内容当前不参与 `{name}` 执行。"
            else:
                explanation = f"注释记录 `{text}`，说明 `{name}` 在此处的实现意图或约束。"
            reads = []
            writes = []
        elif line_number <= signature_end and not brace_only:
            kind = "signature"
            explanation = f"构成函数 `{name}` 的签名片段 `{compact(code_stripped)}`。"
            reads = []
            writes = []
        elif brace_only:
            kind = "brace"
            if closing_labels:
                explanation = (
                    f"在 `{name}` 的 L{line_number} 结束 "
                    + "、".join(closing_labels)
                    + " 作用域。"
                )
            else:
                label = scope_label(code_stripped, previous_code, name)
                explanation = f"在 `{name}` 的 L{line_number} 打开 {label} 作用域。"
        elif any(call in SYNC_APIS for call in calls):
            kind = "sync"
            explanation = sync_explanation(calls, identifiers)
        elif re.search(r"\b(for|while|do)\b", code_stripped):
            kind = "loop"
            loop_type = re.search(r"\b(for|while|do)\b", code_stripped).group(1)
            explanation = (
                f"启动或推进 `{loop_type}` 循环 `{compact(code_stripped)}`；"
                f"迭代式涉及 `{('、'.join(identifiers) or '源码常量')}`。"
            )
        elif re.search(r"\b(if|else|switch|case|default)\b", code_stripped):
            kind = "branch"
            explanation = (
                f"按分支表达式 `{compact(code_stripped)}` 选择 `{name}` 的后续路径；"
                f"判定涉及 `{('、'.join(reads) or '编译期/字面量条件')}`。"
            )
        elif re.match(r"^return\b", code_stripped):
            kind = "statement"
            expression = compact(re.sub(r"^return\s*|;\s*$", "", code_stripped)) or "void"
            explanation = f"从 `{name}` 返回表达式 `{expression}`，把结果交还直接调用者。"
        elif calls:
            kind = "call"
            targets = "、".join(f"`{call}`" for call in calls)
            if writes:
                explanation = (
                    f"调用 {targets} 并更新 `{('、'.join(writes))}`；"
                    f"本行实参或对象来自 `{('、'.join(reads) or '字面量')}`。"
                )
            else:
                explanation = (
                    f"调用 {targets}，传入或访问 `{('、'.join(reads) or compact(code_stripped))}`。"
                )
        else:
            declaration = DECL_RE.match(code_stripped)
            if declaration and ";" in code_stripped:
                kind = "declaration"
                declared = declaration.group(1)
                explanation = (
                    f"声明 `{declared}`；源码初始化式 `{compact(code_stripped)}`"
                    f"读取 `{('、'.join(reads) or '无运行时对象')}`。"
                )
            elif writes:
                kind = "statement"
                explanation = (
                    f"按表达式 `{compact(code_stripped)}` 更新 `{('、'.join(writes))}`；"
                    f"右侧读取 `{('、'.join(reads) or '字面量')}`。"
                )
            else:
                kind = "statement"
                explanation = (
                    f"求值源码语句 `{compact(code_stripped)}`；"
                    f"该语句明确涉及 `{('、'.join(identifiers) or '标点/字面量')}`。"
                )

        notes.append(
            {
                "line": line_number,
                "kind": kind,
                "explanation": explanation,
                "reads": ordered_unique(reads),
                "writes": ordered_unique(writes),
            }
        )

        opening_count = code_stripped.count("{")
        for _ in range(opening_count):
            scope_stack.append(scope_label(code_stripped, previous_code, name))
        if code_stripped:
            previous_code = code_stripped

    return notes


def reviewed_line_notes(
    blueprint: dict[str, Any], definition: dict[str, Any], source_lines: Sequence[str]
) -> list[dict[str, Any]]:
    """优先采用 reviewer 显式逐行解释；未提供时才使用语法感知生成器。"""
    raw_notes = blueprint.get("line_notes")
    if raw_notes is None:
        return make_line_notes(definition, source_lines)
    notes = ensure_list(raw_notes, f"函数蓝图 {definition['id']}.line_notes")
    expected_lines = list(range(definition["start"], definition["end"] + 1))
    if [item.get("line") for item in notes if isinstance(item, dict)] != expected_lines:
        fail(
            f"函数蓝图 {definition['id']}.line_notes 必须按顺序逐行覆盖 "
            f"L{definition['start']}–L{definition['end']}"
        )
    normalized: list[dict[str, Any]] = []
    for index, note in enumerate(notes):
        label = f"函数蓝图 {definition['id']}.line_notes[{index}]"
        if not isinstance(note, dict):
            fail(f"{label}必须是对象")
        require_fields(note, ("line", "kind", "explanation", "reads", "writes"), label)
        if note["kind"] not in LINE_NOTE_KINDS:
            fail(f"{label}.kind 非法：{note['kind']!r}")
        if not isinstance(note["explanation"], str) or not note["explanation"].strip():
            fail(f"{label}.explanation 必须是非空具体说明")
        if any(phrase in note["explanation"] for phrase in BANNED_PHRASES):
            fail(f"{label}.explanation 含泛化占位短语")
        source_ids = set(IDENT_RE.findall(source_lines[note["line"] - 1]))
        for field in ("reads", "writes"):
            values = ensure_list(note[field], f"{label}.{field}")
            if any(not isinstance(value, str) for value in values):
                fail(f"{label}.{field} 只能包含字符串标识符")
        clean_note = copy.deepcopy(note)
        clean_note["reads"] = [value for value in note["reads"] if value in source_ids]
        clean_note["writes"] = [value for value in note["writes"] if value in source_ids]
        normalized.append(clean_note)
    return normalized


def inventory_parts(inventory: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if isinstance(inventory.get("definitions"), list):
        definitions = inventory["definitions"]
        declarations = inventory.get("declaration_only", [])
    elif isinstance(inventory.get("function_inventory"), list):
        all_items = inventory["function_inventory"]
        definitions = [
            item for item in all_items
            if item.get("unit_kind") != "declaration_only" and not item.get("declaration_only", False)
        ]
        declarations = [item for item in all_items if item not in definitions]
    else:
        fail("冻结 inventory 缺少 definitions 或 function_inventory 数组")
    ensure_list(definitions, "inventory.definitions")
    ensure_list(declarations, "inventory.declaration_only")
    if not definitions:
        fail("冻结 inventory 没有函数定义")
    return definitions, declarations


def validate_inventory(
    definitions: list[dict[str, Any]], declarations: list[dict[str, Any]], line_count: int
) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(definitions):
        label = f"inventory.definitions[{index}]"
        if not isinstance(item, dict):
            fail(f"{label}必须是对象")
        require_fields(item, ("id", "name", "start", "end"), label)
        function_id = item["id"]
        if not isinstance(function_id, str) or not ID_RE.fullmatch(function_id):
            fail(f"{label}.id 只能包含字母、数字、短横线和下划线")
        if function_id in by_id:
            fail(f"冻结 inventory 出现重复函数 ID：{function_id}")
        start, end = item["start"], item["end"]
        if not isinstance(start, int) or not isinstance(end, int) or not (1 <= start <= end <= line_count):
            fail(f"{label} 行范围越界：{start}–{end}，源码共 {line_count} 行")
        by_id[function_id] = item

    known_ids = set(by_id)
    for function_id, item in by_id.items():
        for relation in ("callers", "callees"):
            values = item.get(relation, [])
            if not isinstance(values, list):
                fail(f"函数 {function_id} 的 {relation} 必须是数组")
            for edge in values:
                if not isinstance(edge, dict) or not isinstance(edge.get("id"), str):
                    fail(f"函数 {function_id} 的 {relation} 含无效目标记录")
                if edge["id"] not in known_ids:
                    fail(f"函数 {function_id} 的 {relation} 指向冻结清单外目标：{edge['id']}")
                lines = edge.get("lines", [])
                owner = by_id[edge["id"]] if relation == "callers" else item
                if not isinstance(lines, list) or any(
                    not isinstance(line, int) or line < owner["start"] or line > owner["end"]
                    for line in lines
                ):
                    fail(
                        f"函数 {function_id} 的 {relation} 含越界调用行；"
                        f"应落在调用者 {owner['id']} 的 L{owner['start']}–L{owner['end']}"
                    )

    for index, item in enumerate(declarations):
        if not isinstance(item, dict):
            fail(f"inventory.declaration_only[{index}] 必须是对象")
    return by_id


def normalize_blueprint_records(document: Any, path: Path) -> list[dict[str, Any]]:
    if isinstance(document, list):
        records = document
    elif isinstance(document, dict) and isinstance(document.get("functions"), list):
        records = document["functions"]
    elif isinstance(document, dict) and isinstance(document.get("blueprints"), list):
        records = document["blueprints"]
    elif isinstance(document, dict):
        records = [document]
    else:
        fail(f"函数蓝图必须是对象、对象数组或包含 functions/blueprints 的对象：{path}")

    result: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            fail(f"函数蓝图 {path} 的第 {index + 1} 条记录必须是对象")
        if isinstance(record.get("function"), dict):
            merged = copy.deepcopy(record["function"])
            for key, value in record.items():
                if key != "function" and key not in merged:
                    merged[key] = copy.deepcopy(value)
            record = merged
        result.append(record)
    return result


def review_from_blueprint(record: dict[str, Any], function_id: str, definition: dict[str, Any]) -> dict[str, Any]:
    review = record.get("review")
    if review is None:
        review = record
    if not isinstance(review, dict):
        fail(f"函数蓝图 {function_id} 的 review 必须是对象")

    required = {
        "reviewer", "draft_author", "revision", "line_range",
        "gaps", "overlaps", "unresolved", "required_changes",
    }
    require_fields(review, required, f"函数蓝图 {function_id}.review")
    status = review.get("status", review.get("verdict"))
    if status != "PASS":
        fail(f"函数蓝图 {function_id} 尚未 PASS：{status!r}")
    reviewer = review["reviewer"]
    draft_author = review["draft_author"]
    if not isinstance(reviewer, str) or not reviewer.strip():
        fail(f"函数蓝图 {function_id} 的 reviewer 不能为空")
    if not isinstance(draft_author, str) or not draft_author.strip():
        fail(f"函数蓝图 {function_id} 的 draft_author 不能为空")
    if reviewer == draft_author:
        fail(f"函数蓝图 {function_id} 的 reviewer 不能与 draft_author 相同")
    if not isinstance(review["revision"], int) or review["revision"] < 1:
        fail(f"函数蓝图 {function_id} 的 revision 必须是正整数")
    if review["line_range"] != [definition["start"], definition["end"]]:
        fail(
            f"函数蓝图 {function_id} 的 line_range 必须精确等于 "
            f"[{definition['start']}, {definition['end']}]"
        )
    for field in REVIEW_ARRAY_FIELDS:
        if review[field] != []:
            fail(f"函数蓝图 {function_id} 的 PASS review 要求 {field} 为空数组")
    return {
        "status": "PASS",
        "reviewer": reviewer,
        "draft_author": draft_author,
        "revision": review["revision"],
        "line_range": list(review["line_range"]),
        "gaps": [],
        "overlaps": [],
        "unresolved": [],
        "required_changes": [],
    }


def validate_segments(
    function_id: str,
    definition: dict[str, Any],
    segments: Any,
    source_lines: Sequence[str],
    known_function_ids: set[str],
) -> list[dict[str, Any]]:
    values = ensure_list(segments, f"函数蓝图 {function_id}.segments")
    if not values:
        fail(f"函数蓝图 {function_id} 至少需要一个 segment")
    seen_ids: set[str] = set()
    expected_line = definition["start"]
    normalized: list[dict[str, Any]] = []
    actual_internal_edges: set[tuple[str, int]] = set()

    for index, segment in enumerate(values):
        label = f"函数蓝图 {function_id}.segments[{index}]"
        if not isinstance(segment, dict):
            fail(f"{label}必须是对象")
        require_fields(segment, SEGMENT_FIELDS, label)
        segment_id = segment["id"]
        if not isinstance(segment_id, str) or not ID_RE.fullmatch(segment_id):
            fail(f"{label}.id 只能包含字母、数字、短横线和下划线")
        if segment_id in seen_ids:
            fail(f"函数 {function_id} 出现重复 segment ID：{segment_id}")
        seen_ids.add(segment_id)
        start, end = segment["start"], segment["end"]
        if not isinstance(start, int) or not isinstance(end, int) or start != expected_line or end < start:
            fail(f"函数 {function_id} 的 segment {segment_id} 未从 L{expected_line} 连续覆盖")
        if end > definition["end"]:
            fail(f"函数 {function_id} 的 segment {segment_id} 越过函数结尾 L{definition['end']}")
        expected_line = end + 1

        for field in ("title", "detail", "mechanism", "why"):
            if not isinstance(segment[field], str) or not segment[field].strip():
                fail(f"{label}.{field} 必须是非空中文说明")
            if any(phrase in segment[field] for phrase in BANNED_PHRASES):
                fail(f"{label}.{field} 含泛化占位短语：{segment[field]}")
        for field in ("input_state", "output_state", "calls"):
            ensure_list(segment[field], f"{label}.{field}")

        source_slice = "\n".join(source_lines[start - 1 : end])
        source_ids = set(extract_identifiers(source_slice))
        semantic_text = " ".join(
            [segment["title"], segment["detail"], segment["mechanism"], segment["why"]]
            + [str(item) for item in segment["input_state"]]
            + [str(item) for item in segment["output_state"]]
        )
        if source_ids and not any(re.search(rf"\b{re.escape(name)}\b", semantic_text) for name in source_ids):
            fail(f"函数 {function_id} 的 segment {segment_id} 未引用本段真实标识符")

        for call_index, call in enumerate(segment["calls"]):
            call_label = f"{label}.calls[{call_index}]"
            if not isinstance(call, dict):
                fail(f"{call_label}必须是对象")
            require_fields(call, ("name", "line", "type"), call_label)
            line = call["line"]
            if not isinstance(line, int) or not (start <= line <= end):
                fail(f"{call_label}.line 必须位于 segment L{start}–L{end}")
            name = call["name"]
            if not isinstance(name, str) or not name:
                fail(f"{call_label}.name 不能为空")
            source_line = source_lines[line - 1]
            if re.search(rf"\b{re.escape(name)}\b", source_line) is None:
                fail(f"{call_label} 声称的调用 `{name}` 未出现在源码 L{line}")
            if call["type"] == "internal":
                target = call.get("target")
                if target not in known_function_ids:
                    fail(f"{call_label} 指向冻结函数集合外目标：{target!r}")
                actual_internal_edges.add((target, line))
            elif call["type"] == "external":
                if call.get("target") not in (None, ""):
                    fail(f"{call_label} 是 external 调用，不能伪造 target")
            else:
                fail(f"{call_label}.type 只能是 internal 或 external")
        normalized.append(copy.deepcopy(segment))

    if expected_line != definition["end"] + 1:
        fail(f"函数 {function_id} 的 segments 未覆盖到函数结尾 L{definition['end']}")

    expected_internal_edges = {
        (edge["id"], line)
        for edge in definition.get("callees", [])
        for line in edge.get("lines", [])
    }
    if expected_internal_edges and actual_internal_edges != expected_internal_edges:
        missing = sorted(expected_internal_edges - actual_internal_edges)
        extra = sorted(actual_internal_edges - expected_internal_edges)
        fail(f"函数 {function_id} 的内部 caller/callee 记录不一致：缺少 {missing}，多出 {extra}")
    return normalized


def normalize_modules(e2e: dict[str, Any], line_count: int) -> list[dict[str, Any]]:
    modules = ensure_list(e2e.get("modules"), "E2E modules")
    if not modules:
        fail("E2E modules 不能为空")
    top_edges = ensure_list(e2e.get("edges", []), "E2E edges")
    module_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    row_count = (len(modules) + 1) // 2

    for index, module in enumerate(modules):
        label = f"E2E modules[{index}]"
        if not isinstance(module, dict):
            fail(f"{label}必须是对象")
        require_fields(module, ("id", "name", "summary", "ranges", "inactive"), label)
        module_id = module["id"]
        if not isinstance(module_id, str) or not ID_RE.fullmatch(module_id):
            fail(f"{label}.id 只能包含字母、数字、短横线和下划线")
        if module_id in module_ids:
            fail(f"E2E modules 出现重复 ID：{module_id}")
        module_ids.add(module_id)
        ranges = ensure_list(module["ranges"], f"{label}.ranges")
        for value in ranges:
            if (
                not isinstance(value, list) or len(value) != 2
                or not all(isinstance(item, int) for item in value)
                or not (1 <= value[0] <= value[1] <= line_count)
            ):
                fail(f"{label}.ranges 含非法范围：{value!r}")
        item = copy.deepcopy(module)
        row = index // 2
        default_y = 50 if row_count == 1 else 8 + row * 84 / (row_count - 1)
        item.setdefault("position", {"x": 28 if index % 2 == 0 else 72, "y": default_y})
        item.setdefault("color", PALETTE[index % len(PALETTE)])
        item.setdefault("tips", [])
        item.setdefault("edges", [])
        normalized.append(item)

    by_id = {module["id"]: module for module in normalized}
    for edge_index, edge in enumerate(top_edges):
        label = f"E2E edges[{edge_index}]"
        if not isinstance(edge, dict):
            fail(f"{label}必须是对象")
        require_fields(edge, ("from", "to", "kind"), label)
        if edge["from"] not in by_id or edge["to"] not in by_id:
            fail(f"{label} 指向不存在模块：{edge['from']} -> {edge['to']}")
        embedded = {key: copy.deepcopy(value) for key, value in edge.items() if key != "from"}
        by_id[edge["from"]]["edges"].append(embedded)

    architecture_tips = ensure_list(e2e.get("architecture_tips", []), "E2E architecture_tips")
    if architecture_tips:
        preferred = by_id.get("process-entry", normalized[-1])
        preferred["tips"] = ordered_unique(
            [*preferred["tips"], *[compact(str(tip), 240) for tip in architecture_tips]]
        )
    protocols = ensure_list(e2e.get("synchronization_protocols", []), "E2E synchronization_protocols")
    for index, protocol in enumerate(protocols):
        label = f"E2E synchronization_protocols[{index}]"
        if not isinstance(protocol, dict):
            fail(f"{label}必须是对象")
        require_fields(protocol, ("name", "meaning"), label)
        if not all(
            isinstance(protocol[field], str) and protocol[field].strip()
            for field in ("name", "meaning")
        ):
            fail(f"{label}.name/meaning 必须是非空字符串")
        evidence_lines = ensure_list(protocol.get("evidence_lines", []), f"{label}.evidence_lines")
        if any(not isinstance(line, int) or not 1 <= line <= line_count for line in evidence_lines):
            fail(f"{label}.evidence_lines 含源码范围外行号")
        tip = f"{protocol['name']}：{protocol['meaning']}"
        owners = [
            module for module in normalized
            if any(start <= line <= end for line in evidence_lines for start, end in module["ranges"])
        ]
        for module in owners or [by_id.get("process-entry", normalized[-1])]:
            module["tips"] = ordered_unique([*module["tips"], tip])

    for module in normalized:
        position = module["position"]
        if not isinstance(position, dict) or not all(
            isinstance(position.get(axis), (int, float)) and 5 <= position[axis] <= 95
            for axis in ("x", "y")
        ):
            fail(f"模块 {module['id']} 的 position.x/y 必须位于 5–95")
        ensure_list(module["tips"], f"模块 {module['id']}.tips")
        for edge in module["edges"]:
            if edge.get("to") not in by_id:
                fail(f"模块 {module['id']} 的边指向不存在模块：{edge.get('to')}")
            if edge.get("kind") not in {"control", "data", "sync", "handshake"}:
                fail(f"模块 {module['id']} 的边 kind 非法：{edge.get('kind')}")

    covered = [False] * line_count
    for module in normalized:
        for start, end in module["ranges"]:
            covered[start - 1 : end] = [True] * (end - start + 1)
    gaps = [index + 1 for index, value in enumerate(covered) if not value]
    if gaps:
        preview = gaps[:20]
        fail(f"E2E modules 未覆盖全部源码行，缺口示例：{preview}")
    return normalized


def validate_primary_path(e2e: dict[str, Any], modules: Sequence[dict[str, Any]]) -> None:
    """校验典型执行路径真实沿 E2E 有向边前进，避免前端靠名称猜主干。"""
    if "primary_path" not in e2e:
        return
    path = ensure_list(e2e["primary_path"], "E2E primary_path")
    if len(path) < 2 or any(not isinstance(module_id, str) for module_id in path):
        fail("E2E primary_path 至少包含两个模块 ID")
    if len(set(path)) != len(path):
        fail("E2E primary_path 不能重复经过同一模块")
    by_id = {module["id"]: module for module in modules}
    for module_id in path:
        module = by_id.get(module_id)
        if module is None:
            fail(f"E2E primary_path 指向不存在模块：{module_id}")
        if module.get("inactive", False):
            fail(f"E2E primary_path 不能包含未激活模块：{module_id}")
    for source_id, target_id in zip(path, path[1:]):
        if not any(edge.get("to") == target_id for edge in by_id[source_id]["edges"]):
            fail(f"E2E primary_path 缺少真实有向边：{source_id} -> {target_id}")


def normalize_inventory_output(
    definitions: Sequence[dict[str, Any]], declarations: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in definitions:
        normalized = copy.deepcopy(item)
        original_kind = normalized.get("unit_kind")
        if original_kind not in (None, "definition"):
            normalized["definition_kind"] = original_kind
        normalized["unit_kind"] = "definition"
        normalized.setdefault("signature", normalized.get("signature_text", normalized["name"]))
        normalized["inactive"] = bool(normalized.get("inactive", False))
        result.append(normalized)
    for item in declarations:
        normalized = copy.deepcopy(item)
        normalized["unit_kind"] = "declaration_only"
        normalized.setdefault("signature", normalized.get("signature_text", normalized.get("name", "")))
        normalized["inactive"] = bool(normalized.get("inactive", False))
        result.append(normalized)
    return result


def validate_e2e_function_set(
    e2e: dict[str, Any], definitions: Sequence[dict[str, Any]]
) -> dict[tuple[int, int, str], dict[str, Any]]:
    records = e2e.get("function_inventory")
    if records is None:
        return {}
    ensure_list(records, "E2E function_inventory")
    frozen_keys = {(item["start"], item["end"], item["name"]) for item in definitions}
    e2e_keys = {
        (item.get("start"), item.get("end"), item.get("name"))
        for item in records if isinstance(item, dict)
    }
    if frozen_keys != e2e_keys:
        fail(
            "E2E function_inventory 与冻结 definitions 的函数集合不一致："
            f"E2E 缺少 {sorted(frozen_keys - e2e_keys)}；E2E 多出 {sorted(e2e_keys - frozen_keys)}"
        )
    return {
        (item["start"], item["end"], item["name"]): item
        for item in records
    }


def build_symbols(e2e: dict[str, Any], functions: Sequence[dict[str, Any]]) -> list[dict[str, str]]:
    symbols: dict[str, dict[str, str]] = {}
    for item in e2e.get("symbols", []):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            fail("E2E symbols 含无效记录")
        symbols[item["name"]] = copy.deepcopy(item)

    priority = {"api": 1, "call": 2, "sync": 3, "input": 4, "output": 5}

    def add(name: str, kind: str, description: str) -> None:
        current = symbols.get(name)
        if current is None or priority.get(kind, 0) > priority.get(current.get("type", ""), 0):
            symbols[name] = {"name": name, "type": kind, "description": description}

    for function in functions:
        for value in function["inputs"]:
            name = blueprint_symbol_name(value, f"函数 {function['id']}.inputs")
            add(name, "input", f"`{function['name']}` 的关键输入：{value}")
        for value in function["outputs"]:
            name = blueprint_symbol_name(value, f"函数 {function['id']}.outputs")
            add(name, "output", f"`{function['name']}` 的关键输出：{value}")
        for segment in function["segments"]:
            for call in segment["calls"]:
                kind = "call" if call["type"] == "internal" else "api"
                add(call["name"], kind, f"`{function['name']}` 在 L{call['line']} 调用 `{call['name']}`。")
        for note in function["line_notes"]:
            if note["kind"] == "sync":
                source = note["explanation"]
                for name in SYNC_APIS:
                    if f"`{name}`" in source:
                        add(name, "sync", f"`{function['name']}` 在 L{note['line']} 使用同步 API `{name}`。")
    return list(symbols.values())


def build_glossary(e2e: dict[str, Any]) -> list[dict[str, str]]:
    glossary: dict[str, dict[str, str]] = {}
    for index, item in enumerate(ensure_list(e2e.get("glossary", []), "E2E glossary")):
        if not isinstance(item, dict):
            fail(f"E2E glossary[{index}] 必须是对象")
        require_fields(item, ("term", "description"), f"E2E glossary[{index}]")
        if not all(
            isinstance(item[field], str) and item[field].strip()
            for field in ("term", "description")
        ):
            fail(f"E2E glossary[{index}].term/description 必须是非空字符串")
        glossary[item["term"]] = copy.deepcopy(item)
    for protocol in ensure_list(e2e.get("synchronization_protocols", []), "E2E synchronization_protocols"):
        if isinstance(protocol, dict) and isinstance(protocol.get("name"), str) and isinstance(protocol.get("meaning"), str):
            glossary.setdefault(
                protocol["name"],
                {"term": protocol["name"], "description": protocol["meaning"]},
            )
    return list(glossary.values())


def build_analysis(args: argparse.Namespace) -> dict[str, Any]:
    source_path = args.source.resolve()
    try:
        source_bytes = source_path.read_bytes()
        source_text = source_bytes.decode("utf-8")
    except FileNotFoundError:
        fail(f"找不到源码文件：{source_path}")
    except UnicodeDecodeError as exc:
        fail(f"源码不是 UTF-8 文本：{source_path}（{exc}）")
    source_lines = source_text.splitlines()
    source_sha = sha256_bytes(source_bytes)
    line_count = len(source_lines)
    if line_count == 0:
        fail("源码文件为空，无法生成函数分析")

    inventory = load_json(args.inventory.resolve(), "冻结 inventory")
    e2e = load_json(args.e2e.resolve(), "E2E JSON")
    if not isinstance(inventory, dict) or not isinstance(e2e, dict):
        fail("冻结 inventory 与 E2E JSON 顶层都必须是对象")
    require_sha(inventory, "冻结 inventory", source_sha)
    require_sha(e2e, "E2E JSON", source_sha)
    inventory_source = inventory.get("source", {})
    if isinstance(inventory_source, dict) and inventory_source.get("line_count") not in (None, line_count):
        fail(f"冻结 inventory 的 line_count 与源码不一致：{inventory_source.get('line_count')} != {line_count}")
    e2e_source = e2e.get("source", {})
    if isinstance(e2e_source, dict) and e2e_source.get("line_count") not in (None, line_count):
        fail(f"E2E JSON 的 line_count 与源码不一致：{e2e_source.get('line_count')} != {line_count}")

    definitions, declarations = inventory_parts(inventory)
    definition_by_id = validate_inventory(definitions, declarations, line_count)
    e2e_function_map = validate_e2e_function_set(e2e, definitions)
    modules = normalize_modules(e2e, line_count)
    validate_primary_path(e2e, modules)
    module_ids = {module["id"] for module in modules}

    blueprint_by_id: dict[str, dict[str, Any]] = {}
    for path in args.blueprint:
        blueprint_path = path.resolve()
        document = load_json(blueprint_path, "函数蓝图")
        records = normalize_blueprint_records(document, blueprint_path)
        document_sha: str | None = None
        if isinstance(document, dict) and len(records) > 1:
            document_sha = artifact_sha(document, f"函数蓝图集合 {blueprint_path}")
            if document_sha != source_sha:
                fail(f"函数蓝图集合 {blueprint_path} 的源码 SHA-256 与当前源码不一致")
        for record in records:
            function_id = record.get("id", record.get("function_id"))
            if not isinstance(function_id, str) or not function_id:
                fail(f"函数蓝图 {blueprint_path} 含缺少 id/function_id 的记录")
            if function_id in blueprint_by_id:
                fail(f"函数 {function_id} 提供了重复 blueprint")
            if document_sha is None:
                require_sha(record, f"函数蓝图 {function_id}", source_sha)
            blueprint_by_id[function_id] = record

    expected_ids = set(definition_by_id)
    blueprint_ids = set(blueprint_by_id)
    if expected_ids != blueprint_ids:
        fail(
            "函数 blueprint 集合与冻结 definitions 不一致："
            f"缺少 {sorted(expected_ids - blueprint_ids)}；多出 {sorted(blueprint_ids - expected_ids)}"
        )

    functions: list[dict[str, Any]] = []
    known_ids = set(definition_by_id)
    for definition in definitions:
        function_id = definition["id"]
        blueprint = blueprint_by_id[function_id]
        require_fields(blueprint, BLUEPRINT_FIELDS, f"函数蓝图 {function_id}")
        if not isinstance(blueprint["summary"], str) or not blueprint["summary"].strip():
            fail(f"函数蓝图 {function_id}.summary 必须是非空字符串")
        if any(phrase in blueprint["summary"] for phrase in BANNED_PHRASES):
            fail(f"函数蓝图 {function_id}.summary 含泛化占位短语")
        for field in ("inputs", "outputs", "side_effects"):
            values = ensure_list(blueprint[field], f"函数蓝图 {function_id}.{field}")
            if any(not isinstance(value, str) or not value.strip() for value in values):
                fail(f"函数蓝图 {function_id}.{field} 只能包含非空字符串")
        if blueprint["module_id"] not in module_ids:
            fail(f"函数蓝图 {function_id} 指向不存在的 E2E module：{blueprint['module_id']}")
        for field in ("start", "end", "name"):
            if field in blueprint and blueprint[field] != definition[field]:
                fail(
                    f"函数蓝图 {function_id}.{field}={blueprint[field]!r} 与冻结 inventory "
                    f"的 {definition[field]!r} 不一致"
                )
        function_source = "\n".join(source_lines[definition["start"] - 1 : definition["end"]])
        normalized_inputs, input_details = normalize_function_io(
            blueprint["inputs"], function_source, f"{function_id}.inputs"
        )
        normalized_outputs, output_details = normalize_function_io(
            blueprint["outputs"], function_source, f"{function_id}.outputs"
        )

        e2e_item = e2e_function_map.get((definition["start"], definition["end"], definition["name"]))
        if e2e_item and e2e_item.get("module_id") not in (None, blueprint["module_id"]):
            fail(
                f"函数 {function_id} 的 blueprint module_id={blueprint['module_id']} 与 E2E "
                f"module_id={e2e_item.get('module_id')} 不一致"
            )

        review = review_from_blueprint(blueprint, function_id, definition)
        segments = validate_segments(
            function_id, definition, blueprint["segments"], source_lines, known_ids
        )
        line_notes = contextualize_duplicate_line_notes(
            reviewed_line_notes(blueprint, definition, source_lines), segments
        )
        expected_lines = list(range(definition["start"], definition["end"] + 1))
        actual_lines = [note["line"] for note in line_notes]
        if actual_lines != expected_lines:
            fail(f"内部错误：函数 {function_id} 的 line_notes 未逐行覆盖完整范围")
        for note in line_notes:
            source_ids = set(IDENT_RE.findall(source_lines[note["line"] - 1]))
            if any(name not in source_ids for name in note["reads"] + note["writes"]):
                fail(f"内部错误：函数 {function_id} L{note['line']} 的 reads/writes 含非本行标识符")
            if any(phrase in note["explanation"] for phrase in BANNED_PHRASES):
                fail(f"内部错误：函数 {function_id} L{note['line']} 生成了泛化解释")

        functions.append(
            {
                "id": function_id,
                "module_id": blueprint["module_id"],
                "name": definition["name"],
                "start": definition["start"],
                "end": definition["end"],
                "summary": blueprint["summary"],
                "inactive": bool(definition.get("inactive", False)),
                "inputs": normalized_inputs,
                "outputs": normalized_outputs,
                "input_details": input_details,
                "output_details": output_details,
                "side_effects": copy.deepcopy(blueprint["side_effects"]),
                "review": review,
                "line_notes": line_notes,
                "segments": segments,
            }
        )

    result: dict[str, Any] = {
        "schema_version": 2,
        "title": e2e.get("title"),
        "summary": e2e.get("summary"),
        "language": e2e.get("language", (e2e.get("source") or {}).get("language", "cpp")),
        "source": {
            "path": args.source_label or str(source_path),
            "sha256": source_sha,
            "line_count": line_count,
        },
        "review_summary": {
            "status": "PASS",
            "source_sha256": source_sha,
            "inventory_count": len(definitions),
            "reviewed_count": len(functions),
            "pending_functions": [],
            "rework_functions": [],
        },
        "function_inventory": normalize_inventory_output(definitions, declarations),
        "modules": modules,
        "functions": functions,
        "symbols": [],
        "glossary": build_glossary(e2e),
    }
    for field in ("title", "summary", "language"):
        if not isinstance(result[field], str) or not result[field].strip():
            fail(f"E2E JSON 缺少非空顶层字段 {field}")
    result["symbols"] = build_symbols(e2e, functions)
    for optional in (
        "entry_contract", "primary_path", "synchronization_protocols", "architecture_tips"
    ):
        if optional in e2e:
            result[optional] = copy.deepcopy(e2e[optional])
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = ChineseArgumentParser(
        description="合并冻结函数清单、E2E 架构与独立函数蓝图，生成严格 schema_version=2 分析 JSON。"
    )
    parser.add_argument("--source", type=Path, help="UTF-8 源码文件")
    parser.add_argument(
        "--source-label",
        help="写入分析 JSON 的源码位置标签；省略时使用源码绝对路径",
    )
    parser.add_argument("--inventory", type=Path, help="冻结函数 inventory JSON")
    parser.add_argument("--e2e", type=Path, help="E2E 模块与连边 JSON")
    parser.add_argument(
        "--blueprint", type=Path, action="append", default=[],
        help="函数 blueprint JSON；可重复传入，也可一次传入包含 functions/blueprints 数组的文件",
    )
    parser.add_argument("--output", type=Path, help="输出的 schema_version=2 分析 JSON")
    args = parser.parse_args(argv)
    missing = [
        option for option, value in (
            ("--source", args.source), ("--inventory", args.inventory), ("--e2e", args.e2e),
            ("--blueprint", args.blueprint), ("--output", args.output),
        ) if not value
    ]
    if missing:
        parser.error("缺少必需参数：" + "、".join(missing))
    resolved_inputs = {args.source.resolve(), args.inventory.resolve(), args.e2e.resolve()}
    resolved_inputs.update(path.resolve() for path in args.blueprint)
    if args.output.resolve() in resolved_inputs:
        parser.error("--output 不能覆盖源码或任何输入 JSON")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        analysis = build_analysis(args)
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"构建成功：{output}；函数 {len(analysis['functions'])} 个，"
            f"模块 {len(analysis['modules'])} 个，源码 {analysis['source']['line_count']} 行。"
        )
        return 0
    except (ValidationError, OSError) as exc:
        print(f"构建失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
