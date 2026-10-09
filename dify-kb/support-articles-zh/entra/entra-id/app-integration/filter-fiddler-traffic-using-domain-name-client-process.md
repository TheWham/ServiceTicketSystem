# 使用域名和客户端进程筛选 Fiddler 流量

本文介绍如何使用由 Microsoft Entra 和客户端进程拥有的域/主机名筛选 Fiddler 捕获的流量。

## 先决条件

在进行筛选之前，请确保 Fiddler 已配置为捕获所有进程的流量。 在 Fiddler 窗口的左下角，可以选择 **“所有进程** ”以更改所选内容。

![显示“所有进程”按钮的屏幕截图。](media/filter-fiddler-traffic-using-domain-name-client-process/all-processes.png)

## 使用 Fiddler 的内置筛选器功能筛选流量

若要使用 Fiddler 的内置筛选器功能筛选流量，请执行以下步骤：

1. 打开 Fiddler 并导航到右侧面板。
2. 选择“ **筛选器** ”选项卡，然后选择“ **使用筛选器** ”复选框。
3. 在“ **主机** ”部分下，选择“ **仅显示以下主机**”。
4. 在文本框中，输入要筛选的主机名列表，以分号分隔， `localhost;login.microsoftonline.com;graph.microsoft.com`例如。

   注释

   编辑列表时，此文本框将显示黄色背景，指示未保存的更改。
5. 选择**“操作”**按钮以保存列表。 背景色将更改为白色，确认列表已保存。

![显示如何基于主机名筛选流量的屏幕截图。](media/filter-fiddler-traffic-using-domain-name-client-process/show-only-the-following-hosts.png)

在 **“客户端进程** ”部分下，还可以选择要筛选的特定进程。 这对于筛选独立应用程序特别有用。 捕获浏览器流量可能不太有效，因为具有相同名称的多个进程可能难以识别正确的进程。

## 在 OnBeforeRequest 函数中使用 JavaScript 代码筛选流量

注释

此选项特别用于基于浏览器的应用程序。

1. 在 Fiddler 中，转到 **“规则**>**自定义规则**”。 此作将在 FiddlerScript 编辑器中打开 **CustomRules.js** 文件。
2. 在 FiddlerScript 编辑器中找到 **OnBeforeRequest** 函数。
3. 在函数开头插入以下 JavaScript 代码：

   ```
   // begin filter

   // set this to false to disable filter and true to enable filter
   var filterOn = true;

   if (filterOn)
   {
       // hide all requests by default
       oSession["ui-hide"] = "true";

       // list of domain names to filter on
       var host = ["localhost", "login.microsoftonline.com", "graph.microsoft.com"];

       // list of processes to filter on
       var processlist = ["chrome", "microsoftedgecp", "iisexpress", "powershell"];

       for (var j = 0; j < processlist.length; j++)
       {
           if (oSession.LocalProcess.Contains(processlist[j]))
           {
               for (var i = 0; i < host.length; i++)
               {
                   if (oSession.HostnameIs(host[i]))
                   {
                       oSession["ui-hide"] = null;
                   }
               }
           }
       }
   }

   // end filter
   ```

   [![显示 OnBeforeRequest 函数中添加的 JavaScript 代码的屏幕截图。](media/filter-fiddler-traffic-using-domain-name-client-process/add-javascript-code-onbeforerequest-function.png)](media/filter-fiddler-traffic-using-domain-name-client-process/add-javascript-code-onbeforerequest-function.png#lightbox)

   下面是 JavaScript 代码中某些变量的说明：

   - `filterOn`：将其设置为 `true` 启用筛选器并 `false` 禁用它。
   - `host`：包含要筛选的域名列表。
   - `processlist`：包含要筛选的进程名称列表。
4. 保存对 **CustomRules.js** 文件的更改。

## 参考

- [修改请求或响应](http://docs.telerik.com/fiddler/KnowledgeBase/FiddlerScript/ModifyRequestOrResponse)
- [FiddlerScript 食谱](http://fiddlerbook.com/Fiddler/dev/ScriptSamples.asp)
- [了解 FiddlerScript](https://www.telerik.com/blogs/understanding-fiddlerscript)

**第三方信息免责声明**

本文讨论的第三方产品由独立于Microsoft的公司制造。 Microsoft对这些产品的性能或可靠性不作任何默示或其他保证。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/filter-fiddler-traffic-using-domain-name-client-process)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
