# 端口消耗问题疑难解答

*适用于：*Windows 10

TCP 和 UDP 协议基于用于建立连接的端口号工作。 任何需要建立 TCP/UDP 连接的应用程序或服务都需要其端的端口。

有两种类型的端口：

- 临时端口（动态端口）是默认情况下每台计算机必须建立出站连接的端口集。
- 已知端口是特定应用程序或服务的已定义端口。 例如，文件服务器服务使用 445 端口、HTTPS 使用 443 端口、HTTP 使用 80 端口、RPC 使用 135 端口。 自定义应用程序也将有自己的已定义的端口号。

与应用程序或服务建立连接时，客户端设备使用来自设备的临时端口连接到为该应用程序或服务定义的已知端口。 客户端计算机上的浏览器将使用临时端口连接到 `https://www.microsoft.com` 端口 443。

如果同一浏览器正在与多个网站创建许多连接，则对于浏览器尝试的任何新连接，将使用临时端口。 一段时间后，你会注意到连接将开始失败，并且此失败的可能性很大，因为浏览器已使用所有可用端口在外部建立连接，任何建立连接的新尝试都将失败，因为没有更多可用端口。 使用计算机上的所有端口时，我们将其称为端口耗尽。

## TCP/IP 的默认动态端口范围

为了符合 [Internet 分配号码颁发机构 （IANA）](http://www.iana.org/assignments/port-numbers) 建议，Microsoft增加了传出连接的动态客户端端口范围。 新的默认起始端口为 49152，新的默认结束端口为 65535。 此增加是使用默认端口范围为 1025 到 5000 的早期版本的 Windows 配置的更改。

可以使用以下命令 `netsh` 查看计算机上的动态端口范围：

- ```
  netsh int ipv4 show dynamicport tcp
  ```
- ```
  netsh int ipv4 show dynamicport udp
  ```
- ```
  netsh int ipv6 show dynamicport tcp
  ```
- ```
  netsh int ipv6 show dynamicport udp
  ```

范围是针对每个传输（TCP 或 UDP）单独设置的。 端口范围现在是一个具有起点和终点的范围。 Microsoft部署运行 Windows Server 的服务器的客户在内部网络上使用防火墙时，可能会影响服务器之间的 RPC 通信。 在这些情况下，建议重新配置防火墙，以允许 49152 到 65535 的动态端口范围内服务器之间的流量。 此范围除了服务和应用程序使用的已知端口之外。 或者，可以在每台服务器上修改服务器使用的端口范围。 使用 netsh 命令调整此范围，如下所示。 上述命令设置 TCP 的动态端口范围。

```
netsh int <ipv4|ipv6> set dynamic <tcp|udp> start=number num=range
```

起始端口为数字，端口总数为范围。 下面是示例命令：

- ```
  netsh int ipv4 set dynamicport tcp start=10000 num=1000
  ```
- ```
  netsh int ipv4 set dynamicport udp start=10000 num=1000
  ```
- ```
  netsh int ipv6 set dynamicport tcp start=10000 num=1000
  ```
- ```
  netsh int ipv6 set dynamicport udp start=10000 num=1000
  ```

这些示例命令将动态端口范围设置为从端口 10000 开始，并在端口 10999（1000 端口）处结束。 可设置的最小端口数范围为 255。 可设置的最小起始端口为 1025。 最大结束端口（基于所配置的范围）不能超过 65535。 若要复制 Windows Server 2003 的默认行为，请使用 1025 作为启动端口，然后使用 3976 作为 TCP 和 UDP 的范围。 此使用模式导致起始端口为 1025，结束端口为 5000。

具体而言，关于出站连接，因为传入连接不需要临时端口来接受连接。

由于出站连接开始失败，你将看到以下行为的许多实例：

- 无法使用域凭据登录计算机，但可以使用本地帐户登录。 域登录将要求你联系 DC 进行身份验证，该身份验证再次是出站连接。 如果已设置缓存凭据，则域登录可能仍然有效。

  ![事件查看器中 NETLOGON 的错误屏幕截图。](media/tcp-ip-port-exhaustion-troubleshooting/unable-sign-in-with-domain-credentials.png)
- 组策略更新失败：

  ![组策略失败的事件属性的屏幕截图。](media/tcp-ip-port-exhaustion-troubleshooting/group-policy-update-failure.png)
- 无法访问文件共享：

  ![Windows 无法访问错误消息的屏幕截图。](media/tcp-ip-port-exhaustion-troubleshooting/file-shares-inaccessible.png)
- 来自受影响的服务器的 RDP 失败：

  ![远程桌面无法连接时出错的屏幕截图。](media/tcp-ip-port-exhaustion-troubleshooting/rdp-from-affected-server-fails.png)
- 计算机上运行的任何其他应用程序都将开始发出错误

重新启动服务器将暂时解决问题，但一段时间后，你会看到所有症状都会恢复。

如果怀疑计算机处于端口耗尽状态：

1. 请尝试建立出站连接。 从服务器/计算机访问远程共享，或尝试通过 RDP 连接到另一个服务器或 telnet 到端口上的服务器。 如果所有这些选项的出站连接失败，请转到下一步。
2. 打开事件查看器并在系统日志下查找明确指示当前状态的事件：

   1. 事件 ID 4227

      ![事件查看器中事件 ID 4227 的屏幕截图。](media/tcp-ip-port-exhaustion-troubleshooting/event-id-4227.png)
   2. 事件 ID 4231

      ![事件查看器中事件 ID 4231 的屏幕截图。](media/tcp-ip-port-exhaustion-troubleshooting/event-id-4231.png)
3. `netstat -anob`从服务器收集输出。 netstat 输出将显示单个 PID 的TIME\_WAIT状态的大量条目。

   ![netstate 命令输出的屏幕截图。](media/tcp-ip-port-exhaustion-troubleshooting/time-wait-state-entries.png)

   在正常关闭或会话突然关闭后，在 4 分钟（默认）之后，进程或应用程序使用的端口将释放回可用池。 在这 4 分钟内，TCP 连接状态将为 TIME\_WAIT 状态。 如果怀疑端口耗尽，应用程序或进程将无法释放已使用的所有端口，并且会保持TIME\_WAIT状态。

   还可以在同一输出中看到CLOSE\_WAIT状态连接;但是，CLOSE\_WAIT状态是 TCP 对等方没有更多要发送的数据（FIN 发送）但能够从另一端接收数据时的状态。 此状态不一定表示端口耗尽。

   注意

   具有TIME\_WAIT状态的巨大连接并不总是指示服务器当前已退出端口，除非验证了前两个点。 如果拥有大量 TIME\_WAIT 连接，则确实表明该进程正在创建大量 TCP 连接，并最终可能导致端口耗尽。

   Netstat 已在 Windows 10 中更新，并添加了 `-Q` 开关，以显示在 BOUND 状态下已超时等待的端口。 已发布包含此功能的 Windows 8.1 和 Windows Server 2012 R2 更新。 Windows 10 中的 PowerShell cmdlet `Get-NetTCPConnection` 还显示这些 BOUND 端口。

   在 2016/10 之前，netstat 是不准确的。 修复了 netstat，已移植到 2012 R2，允许 *Netstat.exe* 并 `Get-NetTcpConnection` 正确报告 Windows Server 2012 R2 中的 TCP 或 UDP 端口使用情况。 有关详细信息，请参阅 [Windows Server 2012 R2：临时端口修补程序](https://support.microsoft.com/help/3123245/update-improves-port-exhaustion-identification-in-windows-server-2012) 。
4. 在管理员模式下打开命令提示符，并运行以下命令。

   ```
   Netsh trace start scenario=netconnection capture=yes tracefile=c:\Server.etl
   ```
5. *使用[网络监视器](collect-data-using-network-monitor)打开 server.etl* 文件，并在筛选器部分应用筛选器`Wscore_MicrosoftWindowsWinsockAFD.AFD_EVENT_BIND.Status.LENTStatus.Code == 0x209`。 应会看到显示 **STATUS\_TOO\_MANY\_ADDRESSES**的条目。 如果未找到任何条目，则服务器仍不离开端口。 如果找到这些条目，则可以确认服务器处于端口耗尽状态。

## 排查端口耗尽问题

关键是确定哪个进程或应用程序正在使用所有端口。 以下是一些可用于隔离到单个进程的工具

### 方法 1

首先，查看 netstat 输出。 如果你使用的是 Windows 10 或 Windows Server 2016，则可以运行该命令 `netstat -anobq` 并检查进程 ID 是否具有最大条目作为 BOUND。 或者，也可以运行以下 PowerShell 命令来确定进程：

```
Get-NetTCPConnection | Group-Object -Property State, OwningProcess | Select -Property Count, Name, @{Name="ProcessName";Expression={(Get-Process -PID ($_.Name.Split(',')[-1].Trim(' '))).Name}}, Group | Sort Count -Descending
```

大多数端口泄漏都是由于用户模式进程在遇到错误时未正确关闭端口引起的。 在用户模式级别，端口（实际套接字）是句柄。 **TaskManager** 和 **ProcessExplorer** 都能够显示句柄计数，这使你可以确定哪个进程正在使用所有端口。

对于 Windows 7 和 Windows Server 2008 R2，可以更新 PowerShell 版本以包含上述 cmdlet。

### 方法 2

如果方法 1 不帮助你识别过程（在 Windows 10 和 Windows Server 2012 R2 之前），请查看任务管理器：

1. 在详细信息/进程下添加名为“handles”的列。
2. 对“handles”列进行排序以确定具有最多句柄数的进程。 通常，处理大于 3000 的进程可能是罪魁祸首，但诸如 System、*lsass.exe*、*store.exe、*sqlsvr.exe** 等进程除外。

   ![Windows 任务管理器中句柄列的屏幕截图。](media/tcp-ip-port-exhaustion-troubleshooting/process-highest-number-handles.png)
3. 如果这些进程以外的任何其他进程具有更高的数字，请停止该进程，然后尝试使用域凭据登录，并查看它是否成功。

### 方法 3

如果任务管理器没有帮助确定该过程，请使用进程资源管理器调查问题。

使用“进程资源管理器”的步骤：

1. [下载进程资源管理器](/zh-cn/sysinternals/downloads/process-explorer) 并运行它 **提升**。
2. Alt + 选择列标题，选择“选择列**”，然后在**“**进程性能**”选项卡上添加**句柄计数**。
3. 选择“**视图>显示下窗格”。**
4. 选择“**查看>****下窗格”视图>****句柄。**
5. 选择要按该值排序的 **“句柄** ”列。
6. 检查句柄计数高于其他进程的进程（如果无法建立出站连接，可能会超过 10,000）。
7. 单击以突出显示一个具有高句柄计数的进程。
8. 在下部窗格中，下面列出的句柄是套接字。 （套接字在技术上是文件句柄）。

   文件\设备\AFD

   ![进程资源管理器的屏幕截图，其中的进程按句柄排序。](media/tcp-ip-port-exhaustion-troubleshooting/process-explorer-higher-handle-counts.png)
9. 有些是正常的，但大量的不是（数十到千）。 关闭有问题的进程。 如果还原出站连接，则进一步证明应用是原因。 联系该应用的供应商。

最后，如果上述方法没有帮助你隔离进程，建议收集处于问题状态的计算机的完整内存转储。 转储将会告诉你哪个进程具有最大句柄数。

解决方法是，重启计算机将恢复正常状态，并帮助你暂时解决问题。 但是，无法重启时，还可以考虑使用以下命令增加计算机上的端口数 ：

```
netsh int ipv4 set dynamicport tcp start=10000 num=1000
```

此命令将动态端口范围设置为从端口 10000 开始，并在端口 10999（1000 端口）处结束。 可设置的最小端口数范围为 255。 可设置的最小起始端口为 1025。 最大结束端口（基于所配置的范围）不能超过 65535。

注意

请注意，增加动态端口范围不是永久解决方案，而是临时的。 需要跟踪哪些进程/处理器消耗了最大端口数，并从该进程的角度进行故障排除，了解它消耗如此多的端口数量的原因。

对于 Windows 7 和 Windows Server 2008 R2，可以使用以下脚本以定义的频率收集 netstat 输出。 从输出中，可以看到端口使用趋势。

```
@ECHO ON
set v=%1
:loop
set /a v+=1
ECHO %date% %time% >> netstat.txt
netstat -ano >> netstat.txt
 
PING 1.1.1.1 -n 1 -w 60000 >NUL
 
goto loop
```

## 详细信息

- [端口耗尽和你！](/zh-cn/archive/blogs/askds/port-exhaustion-and-you-or-why-the-netstat-tool-is-your-friend) - 本文详细介绍了 netstat 状态，以及如何使用 netstat 输出来确定端口状态
- [检测临时端口耗尽](/zh-cn/archive/blogs/yongrhee/windows-server-2012-r2-ephemeral-ports-a-k-a-dynamic-ports-hotfixes)：本文包含将在循环中运行的脚本来报告端口状态。 （适用于 Windows 2012 R2、Windows 8、Windows 10 和 Windows 11）

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/tcp-ip-port-exhaustion-troubleshooting)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
