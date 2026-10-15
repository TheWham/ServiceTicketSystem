# 常用排查命令速查表

> 所属分类：附录：IT故障排查通用流程

— 文档结束 —

维护说明：本知识库由IT部门定期更新维护。
新增或修正条目请联系IT支持团队，将问题和解决方案提交至工单系统 → 知识库更新。

| 场景 | 命令 | 说明 |
| --- | --- | --- |
| 查看IP配置 | ipconfig /all | 查看所有网卡的IP、网关、DNS |
| 释放/续租IP | ipconfig /release && ipconfig /renew | DHCP重新获取IP |
| 刷新DNS缓存 | ipconfig /flushdns | 清除DNS解析缓存 |
| 网络连通测试 | ping 目标IP -t | 测试到目标的连通性和延迟 |
| 路由跟踪 | tracert 目标IP | 查看数据包经过的每一跳路由 |
| DNS查询 | nslookup 域名 | 测试DNS解析是否正常 |
| 查看网络连接 | netstat -ano | 查看所有活动的网络连接及对应PID |
| 系统文件修复 | sfc /scannow | 扫描并修复系统文件 |
| 系统映像修复 | DISM /Online /Cleanup-Image /RestoreHealth | 修复系统映像组件 |
| 磁盘检查 | chkdsk C: /f | 检查并修复C盘文件系统错误 |
| 内存诊断 | mdsched.exe | 重启后进行内存诊断 |
| 查看系统信息 | msinfo32 | 查看系统硬件和软件详细信息 |
| 查看事件日志 | eventvwr.msc | 打开事件查看器 |
| 查看启动项 | taskmgr → 启动 | 管理开机自启动程序 |
