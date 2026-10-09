# 在 Spring Boot Web 应用程序中启用 MSAL4J 日志记录

## 概要

本文提供有关在 Spring Boot Web 应用程序中使用 [Logback 框架](https://github.com/AzureAD/microsoft-authentication-library-for-java)启用[用于 Java](https://logback.qos.ch/) 的Microsoft身份验证库（MSAL4J）日志记录的分步说明。

## 代码示例

GitHub [上](https://github.com/bachoang/MSAL4J_SpringBoot_Logging/tree/main/msal-b2c-web-sample)提供了此实现的完整代码示例和配置指南。

## 启用 MSAL4J 日志记录

1. 将以下依赖项添加到Pom.xml文件以包括 Logback 框架：

   ```
   <dependency>
       <groupid>ch.qos.logback</groupid>
       <artifactid>logback-classic</artifactid>
       <version>1.2.3</version>
   </dependency>
   ```
2. 在应用项目中，在 **src/main/resources** 文件夹中创建一个文件，并将文件 **命名为Logback.xml**。 然后，添加以下内容：

   ```
   <?xml version="1.0" encoding="UTF-8"?>
   <configuration>
       <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
           <encoder>
               <pattern>%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n</pattern>
           </encoder>
       </appender>
       <root level="debug">
           <appender-ref ref="STDOUT" />
       </root>
   </configuration>
   ```

   此追加器配置将消息记录到控制台。 可以将日志记录级别调整为`error`、`warn``info`或`verbose`基于偏好。 有关详细信息，请参阅 [LogBack：Appenders](https://logback.qos.ch/manual/appenders.html)。
3. 将 **logging.config** 属性设置为主方法之前Logback.xml**文件的位置**：

   ```
   @SpringBootApplication
   public class MsalB2CWebSampleApplication {

   	static { System.setProperty("logging.config", "C:\\Users\\<your path>\\src\\main\\resources\\logback.xml");}
   	public static void main(String[] args) {
   		// Console.log("main");
   		// System.console().printf("hello");
   		// System.out.printf("Hello %s!%n", "World");
   		System.out.printf("%s%n", "Hello World");
   		SpringApplication.run(MsalB2CWebSampleApplication.class, args);
   	}
   }
   ```

## 运行代码示例的配置

### 启用 HTTP 支持

此代码示例设置为使用 HTTPS 协议在本地服务器（localhost）上运行。 按照配置示例中的 [步骤使用 Azure AD B2C 租户](https://github.com/bachoang/MSAL4J_SpringBoot_Logging/tree/main/msal-b2c-web-sample#step-2--configure-the-sample-to-use-your-azure-ad-b2c-tenant) 生成自签名证书。 将 **keystore.p12** 文件放在资源文件夹中。

### 应用注册配置

若要在 Azure AD B2C 中配置应用注册，请执行以下步骤：

1. 在 Azure AD B2C 租户中创建两个应用注册：一个用于 Web 应用程序，另一个用于 Web API。
2. 在 Web API 中公开所需的范围。 有关详细信息，请参阅 [配置 Web API 应用范围](/zh-cn/azure/active-directory-b2c/configure-authentication-sample-web-app-with-api?tabs=visual-studio#step-22-configure-web-api-app-scopes)。
3. 在 **Web 应用程序的“API 权限”** 边栏选项卡中配置 Web API 范围。
4. 向管理员授予对 Web 应用程序中所有已配置的权限的许可。

有关详细信息，请参阅 [使用 Azure AD B2C](/zh-cn/azure/active-directory-b2c/configure-authentication-sample-web-app-with-api) 在调用 Web API 的示例 Web 应用中配置身份验证。

示例配置：

[![显示已配置的应用注册的关系图。](media/enable-msal4j-logging-spring-boot-webapp/app-reg.png)](media/enable-msal4j-logging-spring-boot-webapp/app-reg.png#lightbox)

## 日志记录输出示例

如果应用配置正确，则日志记录输出应类似于以下输出。

[![显示日志记录输出的关系图。](media/enable-msal4j-logging-spring-boot-webapp/log-sample.png)](media/enable-msal4j-logging-spring-boot-webapp/log-sample.png#lightbox)

**第三方信息免责声明**

本文中提到的第三方产品由 Microsoft 以外的其他公司提供。 Microsoft 不对这些产品的性能或可靠性提供任何明示或暗示性担保。

---

> 来源: [Microsoft Learn](https://learn.microsoft.com/en-us/troubleshoot/entra/entra-id/app-integration/enable-msal4j-logging-spring-boot-webapp)（Microsoft 版权所有，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 协议授权；本文为 Microsoft 官方中文机器翻译，原文见 learn.microsoft.com/zh-cn）
