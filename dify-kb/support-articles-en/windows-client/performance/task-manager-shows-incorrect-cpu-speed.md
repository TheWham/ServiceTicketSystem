# Windows Task Manager shows incorrect CPU speed when Hyper-V is enabled

This article provides a workaround for an issue where Windows Task Manager shows incorrect CPU speed when Hyper-V is enabled.

_Applies to:_ &nbsp; Windows 10 - all editions, Window Server 2012 R2  
_Original KB number:_ &nbsp; 3003081

## Symptoms

If the Hyper-V role is enabled in any of the products that are listed at the beginning of this article, the **CPU Frequency** speed value that is displayed in Task Manager is not the current speed, as expected. When the Hyper-V Role is not enabled, Task Manager correctly displays the current speed for this value.

## Workaround

To work around this issue, use the built-in Performance Monitor tool (perfmon.exe), and add the "\\Hyper-V Hypervisor Logical Processor\\Frequency" performance counter.

## Status

This is a known issue in the product versions that are listed at the beginning of this article.


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/task-manager-shows-incorrect-cpu-speed) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
