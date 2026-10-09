# 如何使用Ping.exe检查Microsoft宽带网络适配器

本文提供有关使用 Ping.exe 检查Microsoft宽带网络适配器的一些信息。

*原始 KB 数：* 814155

## 总结

本文介绍如何使用 Microsoft Windows Ping.exe 实用工具来确定网络适配器是否正常工作。

## 详细信息

若要有效使用 ping，需要以下信息：

- 要检查的网络适配器的 IP 地址。
- 默认网关的 IP 地址。 它可能是你的基站、调制解调器或路由器，具体取决于网络的配置方式。

若要查找此信息，

1. 单击“开始”，单击“运行”，键入 cmd，然后单击“确定”。
2. 在命令提示符下，键入 ipconfig，然后按 Enter。
3. 请注意以下信息：

   - 要检查的网络适配器的 IP 地址。
   - 默认网关的 IP 地址。

### 使用Ping.exe检查硬件

若要执行此操作，请执行以下操作：

1. 在命令提示符下，键入 ping 环回 /localhost 127.0.0.1，然后按 Enter。 结果应类似于：

   ```
   Reply from 127.0.0.1: bytes=127 time<1ms TTL=128  
   Reply from 127.0.0.1: bytes=127 time<1ms TTL=128  
   Reply from 127.0.0.1: bytes=127 time<1ms TTL=128  
   Reply from 127.0.0.1: bytes=127 time<1ms TTL=128
   ```

   127.0.0.1 的 Ping 统计信息：数据包数：Sent = 4，Received = 4，Lost = 0 （0% loss），近似往返时间（以毫秒为单位）：最小值 = 0 毫秒，最大值 = 0 毫秒，平均 = 0 毫秒  
   如果不起作用，计算机上可能存在 TCP/IP 问题。 可能需要重新安装 TCP/IP，在成功完成此步骤之前，无法完成以下步骤。
2. 在命令提示符处，键入 ping  
   network\_adapter\_IP\_address，然后按 Enter。 例如，如果网络适配器的 IP 地址为 192.168.2.9，请键入 ping 192.168.2.9，然后按 Enter。 结果应类似于：

   ```
   Reply from 192.168.2.9: bytes=32 time<1ms TTL=128  
   Reply from 192.168.2.9: bytes=32 time<1ms TTL=128  
   Reply from 192.168.2.9: bytes=32 time<1ms TTL=128  
   Reply from 192.168.2.9: bytes=32 time<1ms TTL=128
   ```

   192.168.2.9 的 Ping 统计信息：数据包：Sent = 4，Received = 4，Lost = 0 （0% loss），近似往返时间（以毫秒为单位）：最小值 = 0 毫秒，最大值 = 0 毫秒，平均 = 0 毫秒  
   如果不起作用，则网络适配器可能存在问题。
3. 在命令提示符处，键入 ping  
   **gateway\_IP\_address**，然后按 Enter。 例如，如果基站的 IP 地址为 192.168.2.1，请键入 ping 192.168.2.1，然后按 Enter。 结果应类似于：

   ```
   Reply from 192.168.2.1: bytes=32 time=5ms TTL=64  
   Reply from 192.168.2.1: bytes=32 time=4ms TTL=64  
   Reply from 192.168.2.1: bytes=32 time=4ms TTL=64  
   Reply from 192.168.2.1: bytes=32 time=4ms TTL=64
   ```

   192.168.2.1 的 Ping 统计信息：数据包：Sent = 4，Received = 4，Lost = 0 （0% loss），近似往返时间（以毫秒为单位）：最小值 = 4 毫秒，最大值 = 5 毫秒，平均 = 4 毫秒  
   如果不起作用，则基站、调制解调器、路由器或网络电缆可能存在问题。

## 参考

有关如何排查 Microsoft Windows 中的 TCP/IP 问题的其他信息，请单击以下文章编号以查看Microsoft知识库中的文章：

314067如何使用 Windows XP 排查 TCP/IP 连接问题  
[169790](https://support.microsoft.com/help/169790) 如何排查基本 TCP/IP 问题

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/ping-exe-check-microsoft-broadband-network-adapter)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
