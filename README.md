# CodeToHtmlSkill

代码走读 HTML 的完整原型与可复现分析数据。示例把 4,357 行 AscendC / C++ 源码转换为自包含交互页面，同时展示 E2E 执行 DAG、函数嵌套 DAG、逐段解释与完整源码。

## 目录

- `skills/code-to-html-walkthrough/`：可直接安装的 Codex Skill，包含严格校验渲染器、前端资源、分析数据契约和逐函数复查协议；
- `samples/`：用于复现实验的源码快照；
- `analysis-work/`：冻结函数清单、E2E 架构、16 批逐函数复查蓝图及严格合并器；
- `prototype-code-walkthrough/`：原型页面、完整分析 JSON 和最终单文件 HTML；

## 安装 Skill

```bash
git clone https://github.com/Kirrito-k423/CodeToHtmlSkill.git
mkdir -p ~/.codex/skills
cp -R CodeToHtmlSkill/skills/code-to-html-walkthrough ~/.codex/skills/
```

重启 Codex 后，可在提示词中直接使用 `$code-to-html-walkthrough`。Skill 会要求先冻结完整函数清单，再由独立 reviewer 逐函数复查；只有函数清单、最终分析和 `PASS` 集合完全一致时，才能生成正式 HTML。

渲染器只依赖 Python 标准库。已有符合[分析数据契约](skills/code-to-html-walkthrough/references/analysis-schema.md)的 JSON 时，可以直接执行：

```bash
python3 skills/code-to-html-walkthrough/scripts/render_walkthrough.py \
  --source /absolute/path/source.cc \
  --source-label path/in/repository/source.cc \
  --analysis /absolute/path/source.analysis.json \
  --output /absolute/path/source.walkthrough.html
```

运行渲染器测试：

```bash
python3 -m unittest discover \
  -s skills/code-to-html-walkthrough/scripts \
  -p 'test_*.py' -v
```

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
skill_dir=skills/code-to-html-walkthrough
python3 "$skill_dir/scripts/render_walkthrough.py" \
  --source samples/deepep_moe_dis_dispatch.h \
  --source-label samples/deepep_moe_dis_dispatch.h \
  --analysis prototype-code-walkthrough/full-analysis.json \
  --output prototype-code-walkthrough/code-to-html-skill-output.html
```

严格门禁应报告：4,357 行源码、15 个模块、82 个函数、318 个语义块，且 82/82 函数均有独立 `PASS` 复查记录。

## 示例源码说明

示例源码来自私有仓库 `Kirrito-k423/TmpCode` 的 `deepep_moe_dis_dispatch.h`，仓库对象 SHA 为 `3e9e07bb3797f9666e10ff4c4fe344792c214d53`。文件头声明适用 CANN Open Software License Agreement Version 2.0；复制或分发时请保留原文件头并遵循上游许可。

## 许可证

`skills/code-to-html-walkthrough/` 及本仓原创代码采用 [MIT License](LICENSE)。`samples/deepep_moe_dis_dispatch.h` 以及包含该源码的生成物仍适用华为的 [CANN Open Software License Agreement Version 2.0](third_party/CANN_OSL_2.0.txt)，不因本仓的 MIT License 而重新授权。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
