# Error 0x80071779 when removing network components in Windows 10

This article helps fix an error 0x80071779 that occurs when you uninstall the **Client for Microsoft Networks** or other network components.

_Applies to:_ &nbsp; Window 10 – all editions  
_Original KB number:_ &nbsp; 4340181

## Symptoms

Starting with Windows 10, version 1803 and newer based device or computer, you can't uninstall the **Client for Microsoft Networks** or other network components. You receive the following error message:

> Could not uninstall the Client for Microsoft Networks feature.  
>
> The error is 0x80071779.

*(image: Screenshot of the 0x80071779 error message.)*

## Cause

This behavior is by design.

## Resolution

Microsoft doesn't support using this GUI or **netcfg** to uninstall protocols or built-in drivers. Instead, you can unbind the driver from Network Adapters either by using this GUI or the PowerShell cmdlet `Disable-NetAdapterBinding`. This is effectively the same as uninstalling the driver.

## More information

If there are specific drivers that you want to remove but that are currently not part of an optional feature, file a feature request in the [Feedback Hub](https://www.microsoft.com/store/productId/9NBLGGH4R32N).


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/cannot-uninstall-client-for-microsoft-networks) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
