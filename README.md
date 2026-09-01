# CodeToHtmlSkill

代码走读 HTML 的完整原型与可复现分析数据。示例把 4,357 行 AscendC / C++ 源码转换为自包含交互页面，同时展示 E2E 执行 DAG、函数嵌套 DAG、逐段解释与完整源码。

## 目录

- `samples/`：用于复现实验的源码快照；
- `analysis-work/`：冻结函数清单、E2E 架构、16 批逐函数复查蓝图及严格合并器；
- `prototype-code-walkthrough/`：原型页面、完整分析 JSON 和最终单文件 HTML；
- 正式渲染器位于同账号私有仓库 `hugoMinos/skills/code-to-html-walkthrough`。

## 直接查看

打开 `prototype-code-walkthrough/code-to-html-skill-output.html` 即可离线阅读。也可以运行：

```bash
python3 prototype-code-walkthrough/server.py
```

然后访问 `http://127.0.0.1:4173/?variant=B`。

## 从分析蓝图重建

先在本仓库根目录合并分析数据：

```bash
blueprint_args=()
for blueprint in analysis-work/blueprint-batch-*.json; do
  blueprint_args+=(--blueprint "$blueprint")
done

python3 analysis-work/build_full_analysis.py \
  --source samples/deepep_moe_dis_dispatch.h \
  --source-label samples/deepep_moe_dis_dispatch.h \
  --inventory analysis-work/inventory-code-index.json \
  --e2e analysis-work/e2e-and-inventory.json \
  "${blueprint_args[@]}" \
  --output prototype-code-walkthrough/full-analysis.json
```

再使用 `code-to-html-walkthrough` Skill 的正式渲染器：

```bash
skill_dir=../hugoMinos/skills/code-to-html-walkthrough
python3 "$skill_dir/scripts/render_walkthrough.py" \
  --source samples/deepep_moe_dis_dispatch.h \
  --source-label samples/deepep_moe_dis_dispatch.h \
  --analysis prototype-code-walkthrough/full-analysis.json \
  --output prototype-code-walkthrough/code-to-html-skill-output.html
```

严格门禁应报告：4,357 行源码、15 个模块、82 个函数、318 个语义块，且 82/82 函数均有独立 `PASS` 复查记录。

## 示例源码说明

示例源码来自私有仓库 `Kirrito-k423/TmpCode` 的 `deepep_moe_dis_dispatch.h`，仓库对象 SHA 为 `3e9e07bb3797f9666e10ff4c4fe344792c214d53`。文件头声明适用 CANN Open Software License Agreement Version 2.0；复制或分发时请保留原文件头并遵循上游许可。
