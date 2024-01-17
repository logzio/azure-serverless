**This project is under development**

---

# logzio-azure-serverless-python
This repository contains the Python code and instructions necessary to ship logs from your Azure services to Logz.io using an Azure Function. After completing the setup, your Azure Function will forward logs from an Azure Event Hub to your Logz.io account.

![Integration-architecture](img/logzio-evethub-Diagram.png)

## Setting up Log Shipping from Azure

### 1. Deploy the Logz.io Python Template👇 

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Flogzio%2Fazure-serverless%2Fserverless-function%2Fdeployments%2Fazuredeploylogs.json)

This deployment will create the following services:
* Serverless Function App (Python-based)
* Event Hubs Namespace
* Event Hubs Instance
* Storage account: - Function's Logs Storage Account
									 - Container for failed shipments
* App Service Plan
* Application Insights

### 2. Configure the Template

Use these settings when configuring the template:

| Parameter | Description |
|---|---|
| Resource group* | Create a new resource group or select an existing one. |
| Region* | Select the region closest to your Azure services. |
| LogzioURL* | Use the listener URL specific to your Logz.io account region. |
| LogzioToken* | Your Logz.io logs shipping token. |
| ThreadCount* | Number of threads for the Function App (default: 4). |
| bufferSize* | Maximum number of messages to accumulate before sending (default: 100). |
| intervalTime* | Interval time for sending logs in milliseconds (default: 10000). |

*Required fields.

After setting the parameters, click **Review + Create**, and then **Create** to deploy.

### 3. Stream Azure Service Data

Configure your Azure services to stream logs to the newly created Event Hub. For each service:

1. Create diagnostic settings.
2. Under 'Event hub policy name', select the appropriate policy (e.g., 'LogzioLSharedAccessKey').

For more details, see [Microsoft's documentation](https://docs.microsoft.com/en-us/azure/monitoring-and-diagnostics/monitor-stream-monitoring-data-event-hubs).

### 4. Verify Data Reception in Logz.io

Allow some time for data to flow from Azure to Logz.io, then check your Logz.io account. You should see logs of the type `eventHub` in Logz.io.

### Backup for Unshipped Logs

The deployment includes a backup mechanism for logs that fail to ship to Logz.io. These logs are stored in the 'logziologsbackupstorage' blob container.

### Post-Deployment Configuration

To modify configuration after deployment, visit your Function App's 'Configuration' tab. You can adjust settings such as LogzioURL, LogzioToken, bufferSize, and more.

![Function's Configuration](img/configuration-settings-python.png)

## Changelog

- Version 1.0.0:
  * Initial release with Python Azure Function.
  * Implement log shipping to Logz.io.
  * Backup mechanism for failed log shipments.
  * Customizable log batching and threading.

---

Remember to replace placeholders like `your_template_link_here` with actual links or values relevant to your project. You might also want to add or modify the version history in the changelog according to your project's development history.
