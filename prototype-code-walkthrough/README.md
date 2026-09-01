# Code Walkthrough UI — PROTOTYPE

验证问题：三列联动、分层解释和代码反向索引，是否能降低阅读 4,357 行 NPU kernel 的压力？

这是一次性 UI 原型，不是生产实现。三个结构不同的变体放在同一路由，通过 `?variant=A|B|C` 或页面底部切换器选择。第二轮重点验证：真实 DAG、浅色代码中枢，以及代码正文中的输入/输出/API 语义强调。

```bash
python3 prototype-code-walkthrough/server.py
```

默认读取仓库中的 `samples/deepep_moe_dis_dispatch.h`。也可覆盖：

```bash
CODE_WALKTHROUGH_SOURCE=/absolute/path/to/source.h python3 prototype-code-walkthrough/server.py
```

- A：双图三轨（E2E DAG / 调用 DAG / 源码等权并排）
- B：代码中枢（浅色，E2E DAG 在左、代码居中、函数调用 DAG 在右）
- C：DAG 画布（全局执行图横向铺开，调用图与源码在下方）

代码语义颜色：琥珀色表示关键输入对象，蓝色表示关键输出对象，紫色胶囊表示核心 API，紫色下划线表示内部函数接口。

页面状态只存在内存和 URL 中，不会修改源码。
