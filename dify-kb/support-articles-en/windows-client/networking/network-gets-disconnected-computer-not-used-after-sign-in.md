# Network gets disconnected for several seconds if the computer isn't used after you sign in to Windows 10

_Applies to:_ &nbsp; Windows 10

## Symptoms

When you sign in to a computer running Windows 10 and leave it unused for more than 10 minutes, the network gets disconnected for several seconds.

Applications and services that communicate with the computer through LAN will get disconnected from the computer during that period.

> [!Note]
> This is a common scenario in [Windows 10 IoT](/windows/iot-core/windows-iot-enterprise#fixed-purpose-devices).

## Cause

The Logon pre-scheduled task starts the ProvTool.exe file. This file processes provisioning packages on the system. The ndisuio.sys driver is loaded when the ProvTool.exe starts the DMWapPushService service for the process. When the ndisuio.sys driver binds to the network, the existing connection is interrupted and resumes after a few seconds.

## Resolution

### Method1: Change the loading time of the ndisuio.sys driver

Here's how to change the loading time of ndisuio.sys driver:

1. [Open **Registry Editor**](https://support.microsoft.com/windows/how-to-open-registry-editor-in-windows-10-deab38e6-91d6-e0aa-4b7c-8878d9e07b11).
2. Go to `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Ndisuio`.
3. Double-click **Start** and change the value data to **1**.
> **Note**
    > The value data **1** represents starting the driver when the system starts.
4. Close **Registry Editor**.
5. Restart the system.

### Method 2: Change the start timing of the DMWapPushSvc service

Here's how to change the start timing of the DMWapPushSvc service:

1. [Open **Registry Editor**](https://support.microsoft.com/windows/how-to-open-registry-editor-in-windows-10-deab38e6-91d6-e0aa-4b7c-8878d9e07b11).
2. Go to `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\dmwappushservice`.
3. Double-click **Start** and change the value data to **2**.
> **Note**
    > The value data **2** represents setting the service to start automatically.
4. Close **Registry Editor**.
5. Restart the system.


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/network-gets-disconnected-computer-not-used-after-sign-in) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
