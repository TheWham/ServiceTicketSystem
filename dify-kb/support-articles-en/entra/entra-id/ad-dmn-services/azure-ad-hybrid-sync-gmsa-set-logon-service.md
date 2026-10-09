# Microsoft Entra Hybrid Sync Agent Installation Issues - The gMSA is set to log on as Service

This troubleshooting guide focuses on when the gMSA is set to log on as a service. This situation may block you from successfully installing the Microsoft Entra Connect Provisioning Agent.

## Prerequisites

To install *Cloud Provisioning Agent*, the following prerequisites are required: [Prerequisites for Microsoft Entra Connect cloud sync](/azure/active-directory/cloud-sync/how-to-prerequisites).

## The gMSA is set to log on as Service

While installing Cloud Provisioning Agent, you may get the following error:

> Failed changing Windows service credentials to gMSA.

To resolve this issue, check the System event logs for **EventID 7038**. The following error appears:

> The user name or password is incorrect.

*(image: Screenshot of error when attempting to install the Microsoft Entra Connect Provisioning Agent. It says the user name or password is incorrect.)*

Open the **Microsoft Entra Connect Provisioning Agent** properties and select the **Log On** tab. You'll find the settings aren’t grayed out, as is expected for a managed account service.

*(image: Screenshot of the 'Log On' tab of the Microsoft Azure A D Connect Provisioning Agent window, including the account and password entries.)*

To verify whether the account is managed, open a command prompt and type the following command:

```console
Sc.exe qmanagedaccount aadconnectprovisioningagent
```

The account-managed status is shown as **False**.

*(image: Screenshot of the output for the S c . e x e command, showing the account-managed status as false.)*

To set the status to **True** and resolve this issue, type the following command:

```console
Sc.exe managedaccount aadconnectprovisioningagent true
```

The wizard now completes successfully.


---

> Source: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/ad-dmn-services/azure-ad-hybrid-sync-gmsa-set-logon-service) (Microsoft, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
