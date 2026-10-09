# 在 Windows 10 版本 1803 及更高版本中按文本解释的 UNC 路径中的 URI 编码

本文提供有关 WINDOWS 10 版本 1803 及更高版本中解释的 UNC 路径中的 URI 编码的一些信息。

*适用于：*Windows 10 - 所有版本  
*原始 KB 数：* 4467268

## 总结

在 Windows 10 版本 1803 及更高版本的 Windows 中，包含 URI 编码字符的通用命名约定（UNC）路径不能引用 URL（如 SharePoint 文档库）。

例如，当路径 `http://myserver/Shared Documents` 经过 URI 编码时，路径将变为 `http://myserver/Shared%20Documents`。 在 Windows 10 版本 1803 之前，可以使用 UNC 路径 \\myserver\shared%20documents。 升级到版本 1803 后，“%20”不再解释为空格，而是文本值“%20”。 这可以防止以前生成的链接解析到正确的 http 路径。

## 详细信息

这是设计的结果。 应更新 UNC 路径以反映文本路径，并且应删除任何 URI 编码字符。 或者，使用解码路径的 file://so 方案。 （例如：file://\\myserver\shared%20documents.）

为了实现与本地 Windows 文件系统命名约定的奇偶一致，Windows 10 版本 1803 引入了对基于 Web 的路径的文件名和文件夹中的其他字符的支持。

以前不支持的字符之一是百分比符号 \。 由于此字符是用于 URI 编码的转义字符，因此已对 URI 编码的 UNC 路径不再进行 URI 解码。 相反，它将被视为文本路径。

Windows 样式路径不是 URI，因此不遵循常规 URI 编码规则，因此在将 WebDAV 样式路径转换回 Windows 样式路径时，应在 URI 中使用百分比编码的任何字符进行解码。 同样，Windows 样式路径不使用百分比编码来表示文件名中的特殊字符，因此，每当 WebClient 服务在转换为 URI 时观察 Windows 样式路径中的百分比字符时，即使“%”字符后跟两个十六进制数字，“%”字符也会替换为“%25”。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/url-encoding-unc-paths-not-url-decoded)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
