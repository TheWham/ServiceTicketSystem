# 完整 PRD / spec 数据库字段对齐

> 执行方式：在当前已隔离工作区内逐项实施、测试和评审。

**Goal:** 根目录 SQL 与运行 db/init 同步覆盖 PRD 2.2、DM 和 SQL-007/010 的完整 41 表契约。

**Architecture:** SQL spec 为字段定义来源，生成器一次生成运行 DDL 和包含相同 DDL/种子的根目录单文件。已审核的运行投影字段保留；取消从历史 fixture 复制未开发表。旧的 34 表版本冻结为测试 fixture，历史迁移生成和验证只读取冻结版本。

**Tech Stack:** Python unittest、MySQL 8.0、Java 17 / Maven。

## 约束

- 用户已明确要求两套 SQL 一起强对齐，旧的未开发模块暂缓限制不再适用。
- 41 表建模不代表全部业务 API 已实现；不新增业务功能。
- 不连接或更改真实业务数据库，不执行破坏性初始化。
- V2_0/V2_1/V2_2 已发布迁移字节和目标不变；它们仅升级到旧 34 表版本，不声称能升级到本次完整模型。
- 保留当前未跟踪的远程连接设计文件，不提交用户文件。

## 实施步骤

- [x] 为 41 表、PRD 字段覆盖、两入口一致、JSON/空值/索引以及附件 PASSED 查询补失败回归测试。
- [x] 冻结现有 34 表 DDL；历史迁移生成器和历史 MySQL 验证改用该 fixture。
- [x] 消除 SQL 模板与 DM 必要元数据、唯一约束的遗漏；生成器输出全部规范表和已记录的投影字段。
- [x] 生成两套 SQL，更新静态门禁、当前元数据校验以及文档发布范围。
- [x] 附件实体/列表查询采用当前完整字段和 PASSED 枚举。
- [x] 验证静态测试、Java 测试、隔离 MySQL 建库/种子/数据约束/历史迁移，进行独立代码评审。

## 验证命令

```powershell
python -B -m unittest discover -s docs/tests -p 'test_*.py'
python -B -m unittest discover -s it-ticket-cloud/db/tests -p 'test_*.py'
python -B it-ticket-cloud/db/tools/build_schema.py
python -B it-ticket-cloud/db/tools/validate_schema.py
```

MySQL 测试只对本次启动的本机独立实例、新建 `schema_test_*` 库执行；Java 测试使用本地工具链运行 ticket-service 及依赖模块。

## 2026-09-30 验证结果

- 文档契约 6 项、SQL 静态契约 15 项通过。
- 后端 reactor 222 项通过：common 3、common-web 3、user-service 7、ticket-service 42、consultation-service 165、gateway 2。
- MySQL 8.0.43 本机隔离实例 14 组通过：两入口真实 DDL 和种子行数一致、41 表元数据、新旧枚举和 JSON、消息唯一键、SLA 关联、历史升级与失败门禁。
- 合并种子时发现并修复 UTF-8 BOM 位于 SQL 中间导致的语法错误，增加回归检查。
- 重新生成 V2_2 后 SHA-256 仍为 `51ba471d119b0155006fc31f55f8f109db8105263fa1485c54bd089388921200`；发布迁移文件均无 diff。
- 独立评审未发现必须修复项；静态门禁对普通列默认值/内联主键，以及元数据门禁对投影/CHECK 的覆盖仍有非阻塞改进空间。当前 DDL 已在真实 MySQL 验证。
- 未操作真实业务数据库，未提供或执行存量 34→41 自动迁移。
