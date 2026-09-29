# Nacos 配置接入

四个服务支持本地 dev/prod profile，默认使用本地配置。设置 NACOS_CONFIG_ENABLED=true 后，按 `{服务名}-{profile}.yaml` 加载远程配置。详细规则见 [配置管理说明](配置管理说明.md)。

`nacos-config-import.zip` 包含 DEFAULT_GROUP 下的13份公开示例：四个服务的dev/prod共8份、4份无profile名称的兼容示例，以及common-config.yaml。启用远程配置时必须发布与实际profile一致的DataId。

```powershell
python it-ticket-cloud/nacos-config/build_import.py
```

网关保留用户、工单、分类、通知、SLA、异常队列入口，并增加咨询、知识搜索和新草稿路由。

用户、工单和咨询必须使用相同的 MYSQL_HOST、MYSQL_PORT、MYSQL_DB=it_ticket_system、MYSQL_USERNAME、MYSQL_PASSWORD；JDBC采用UTC。旧远程配置会覆盖本地配置，部署前须同步。

生成导入包不读取 ai-secrets.yml。真实数据库密码、JWT密钥和模型key使用环境变量或受控的本地配置文件，不提交到仓库。
