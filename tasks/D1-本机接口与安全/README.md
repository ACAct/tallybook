# D1 · 本机接口与安全

| 项目 | 内容 |
| --- | --- |
| 所属层 | 接口层（D） |
| 负责文件 | `ledger/server.py` `app.py` |
| 负责函数 | `create_server()`、`Handler.dispatch()`、`app.main()` |
| 依赖 | B/C 组全部业务接口 |
| 验收测试 | `tests/test_server.py` 全部用例 |

## 任务说明

实现本机 HTTP 适配层与启动入口：路由、安全响应头、本机访问限制、静态资源白名单、命令行参数。

## 交付标准

- 实现 `/api/dashboard`、`/api/records`(GET 合并进 dashboard/POST/PUT/DELETE)、`/api/export`、`/api/import` 路由与错误码（400/403/404/500）。
- Host/Origin 仅允许本机；CSP、`X-Content-Type-Options`、`Referrer-Policy` 等安全头齐备；静态资源走白名单，无法越权访问源码与数据目录。
- 请求体上限 `MAX_BODY`；`app.py` 支持 `--port`/`--data`/`--no-browser` 并校验端口。

接口细节对照本地完整项目 `docs/接口契约.md` 第 4 节；本分支只提交 D1 文件，公共契约和其余模块待团队整合。

## 提交清单

- [x] 使用 GitHub 账号 `2074599796-cpu` 提交 D1 文件
- [x] 附测试方法与运行结果，见[提交说明](../../docs/D1-沈冠宇.md)
- [ ] 博客据实记录贡献（不照搬参考实现）

## 认领

- 认领人：沈冠宇
- 整理与验证日期：2026-11-07
- GitHub 分支：`D1-本机接口与安全`

## 本次提交范围

- `app.py`：启动入口、端口校验、数据路径和浏览器启动开关。
- `ledger/server.py`：HTTP 路由、本机访问限制、安全响应头、静态资源白名单和请求体大小限制。
- `tests/test_server.py`：4 项接口与安全验收测试。
- 本任务认领说明及 `docs/D1-沈冠宇.md` 测试记录。

代码来源为本地 `qingji` 中已有的 D1 参考实现，本次工作是按职责提取、验证并提交，不声称从零独立编写。测试依赖完整项目的业务、数据和静态资源模块；本分支不能单独启动，需待团队整合依赖后运行。
