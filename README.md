# Ohio BMV Intelligent Online Assistant (POC)

This repository contains a **reference implementation** of an Ohio BMV–style online assistant built with **Azure AI Foundry Agent Service**, **Grounding with Bing Custom Search**, and a **typed MCP tool** backed by **Azure Functions + Azure SQL**.

The goal is to demonstrate how an AI assistant can:

- Answer citizen questions using **only official public information** (Ohio BMV + Ohio Revised Code).
- Guide users through a **driver's license address change** workflow in natural language.
- Submit structured requests into a **back-end data store** using a **safe, typed tool interface** (MCP).
- Leave an **auditable trail** in SQL for downstream processing.

> ⚠️ This is a **demo / proof-of-concept**, not production code.  
> The SQL database, schema, and MCP tool implementation are examples that the Ohio BMV (or any DMV) can adapt to their existing systems.

---

## 1. High-Level Architecture

At a high level, the solution has four layers:

1. **User Experience**
   - Chat interface (e.g., Foundry playground or embedded web chat).
   - Citizen interacts with the **"Ohio BMV Online Assistant"** in natural language.

2. **Intelligence (Azure AI Foundry Agent)**
   - Large language model: **`gpt-4o`** or **`gpt-4o-mini`**.
   - System prompt specialized for Ohio BMV use cases.
   - Uses:
     - **Grounding with Bing Custom Search** for public info.
     - **MCP tool** for address-change submissions.
   - Optional: memory store for short-term conversation context.

3. **Integration (MCP Server)**
   - **Azure Functions** app acting as an MCP server.
   - Exposes a typed tool, `create_license_address_change_request`, via `mcpToolTrigger`.
   - Uses `pyodbc` to talk to Azure SQL in a controlled, parameterized way.

4. **Data Layer (Demo SQL DB)**
   - **Azure SQL Database** with:
     - `dbo.LicenseAddressChangeRequests` – demo table for submitted address-change requests.
     - (Optional) `dbo.BmvFormSubmissions` – example table for other form-based workflows.

---

## 2. Components in Detail

### 2.1 Azure AI Foundry Agent

**Model**

- `gpt-4o` or `gpt-4o-mini`, configured for:
  - Factual, policy-aligned responses.
  - Low hallucination risk.
  - Government-service tone: neutral, clear, and helpful.

**System Prompt (Concept)**

The system prompt defines the agent as the **Ohio BMV Online Assistant** that:

- Uses **only public-facing information** from:
  - `https://www.bmv.ohio.gov/`
  - `https://codes.ohio.gov/ohio-revised-code`
  - `https://bmvonline.dps.ohio.gov/`
  - `https://www.bmv.ohio.gov/about-contact.aspx`
  - `https://bmv.ohio.gov/dl-identity-documents.aspx`
- Must not:
  - Reference, access, or imply access to private records behind OH|ID or any login.
  - Invent policies, fees, or legal interpretations.
- Can:
  - Answer questions about licenses, IDs, registration, titles, fees, required documents, reinstatement rules, locations, and hours.
  - Switch into a **workflow mode** for a driver's license **address change** and call a dedicated MCP tool once all required data is collected.

**Tools attached to the Agent**

1. **Grounding with Bing Custom Search**
2. **MCP Server – [`mcp-server/`](./mcp-server/)** (Azure Functions MCP endpoint)

See [prompts/ohio-bmv-agent-system-prompt.md](./prompts/ohio-bmv-agent-system-prompt.md) for the full system prompt.

---

### 2.2 Grounding with Bing Custom Search

**Purpose:**  
Restrict the agent's retrieval to **approved public sources** and boost official content above everything else.

**Example Custom Search configuration**

Configuration name (example): `ohio-bmv-grounding-only`

**Allowed domains** (Include subpages = `Yes`):

- `https://www.bmv.ohio.gov/`
- `https://codes.ohio.gov/ohio-revised-code`
- `https://bmvonline.dps.ohio.gov/`
- `https://www.bmv.ohio.gov/about-contact.aspx`
- `https://bmv.ohio.gov/dl-identity-documents.aspx`

**Rank adjustments (optional, recommended)**

- `www.bmv.ohio.gov` – Boost
- `codes.ohio.gov` – Boost

This ensures:

- Policy questions are answered from the **Ohio BMV** site.
- Legal questions are answered from the **Ohio Revised Code**.
- The assistant does not drift to unrelated or non-official sources.

See [docs/bing-custom-search-setup.md](./docs/bing-custom-search-setup.md) for detailed configuration steps.

---

### 2.3 MCP Server (Azure Functions)

The MCP server is implemented as an Azure Functions app that exposes tools via the `mcpToolTrigger` binding.

**Repository:** [`mcp-server/`](./mcp-server/) (git submodule pointing to [john-carroll-sw/ohio-bmv-sql-mcp](https://github.com/john-carroll-sw/ohio-bmv-sql-mcp))

Key file: `mcp-server/src/function_app.py`

#### 2.3.1 Tools

The main tool of interest for this POC:

- **`create_license_address_change_request`**

Additional demo tools (optional):

- `hello_mcp`
- `get_snippet`
- `save_snippet`

These are primarily there to validate MCP wiring.

#### 2.3.2 `create_license_address_change_request` Tool

**Purpose:**

Submit a structured driver's license **address-change request** that is written into Azure SQL.

**Trigger attributes (conceptual):**

```python
@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="create_license_address_change_request",
    description="Create a driver's license address-change request record in SQL (example: Ohio BMV).",
    toolProperties=tool_properties_license_address_change_json
)
def create_license_address_change_request(context) -> str:
    ...
```

**Schema (toolProperties)**

Input schema includes (all `string` types in the MCP definition):

* `driverLicenseNumber` (required)
* `dateOfBirth` (required, `YYYY-MM-DD`)
* `firstName` (required)
* `middleName` (optional)
* `lastName` (required)
* `email` (optional)
* `phone` (optional)
* `oldAddressLine1` (required)
* `oldAddressLine2` (optional)
* `oldCity` (required)
* `oldState` (required)
* `oldZip` (required)
* `newAddressLine1` (required)
* `newAddressLine2` (optional)
* `newCity` (required)
* `newState` (required)
* `newZip` (required)
* `preferredContactMethod` (optional; `"email" | "phone" | "mail"`)
* `conversationSummary` (optional short text summary for audit)

**Function behavior (high level)**

1. Parse the MCP JSON payload (`context`).
2. Extract `arguments`.
3. Validate required fields; return an error string if any are missing.
4. Open an ODBC connection:
   ```python
   conn = pyodbc.connect(os.environ["SQL_CONNECTION_STRING"])
   cursor = conn.cursor()
   ```
5. Execute a parameterized `INSERT` into `dbo.LicenseAddressChangeRequests`.
6. Fetch `SCOPE_IDENTITY()` to get the new request ID.
7. Return a human-readable confirmation string back to the agent, e.g.:
   > Created address-change request #123 for license OH99887766.

This pattern is **safe** because:

* The model can only populate the **defined parameters** of the tool.
* There are no free-form SQL queries generated by the LLM.
* All SQL statements are static and parameterized in the function code.

---

### 2.4 Azure SQL Database (Demo Schema)

The POC uses a simple Azure SQL database to show how agent-submitted requests can be stored for later processing.

#### 2.4.1 `dbo.LicenseAddressChangeRequests`

Example schema:

```sql
CREATE TABLE dbo.LicenseAddressChangeRequests (
    Id                     INT IDENTITY(1,1) PRIMARY KEY,
    CreatedAt              DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME(),
    DriverLicenseNumber    NVARCHAR(50)   NOT NULL,
    DateOfBirth            DATE           NOT NULL,
    FirstName              NVARCHAR(100)  NOT NULL,
    MiddleName             NVARCHAR(100)  NULL,
    LastName               NVARCHAR(100)  NOT NULL,
    Email                  NVARCHAR(255)  NULL,
    Phone                  NVARCHAR(50)   NULL,
    OldAddressLine1        NVARCHAR(255)  NOT NULL,
    OldAddressLine2        NVARCHAR(255)  NULL,
    OldCity                NVARCHAR(100)  NOT NULL,
    OldState               NVARCHAR(50)   NOT NULL,
    OldZip                 NVARCHAR(50)   NOT NULL,
    NewAddressLine1        NVARCHAR(255)  NOT NULL,
    NewAddressLine2        NVARCHAR(255)  NULL,
    NewCity                NVARCHAR(100)  NOT NULL,
    NewState               NVARCHAR(50)   NOT NULL,
    NewZip                 NVARCHAR(50)   NOT NULL,
    PreferredContactMethod NVARCHAR(50)   NULL,
    ConversationSummary    NVARCHAR(MAX)  NULL
);
```

See [sql/license_address_change_schema.sql](./sql/license_address_change_schema.sql) for the complete schema.

> In a real deployment, BMV can:
>
> * Map these fields to existing case-management systems.
> * Add status columns (e.g., `Status`, `CaseNumber`, `ProcessedBy`, etc.).
> * Replace the SQL insert with calls to their internal APIs or queues, keeping the same MCP pattern.

---

## 3. End-to-End Flow (Example)

1. **Citizen asks a general question**

   * Example:
     *"What services does the Ohio BMV offer, and where can I find information about fees and renewal options?"*
   * Agent uses **Grounding with Bing Custom Search** restricted to BMV + ORC.
   * Responds with accurate information and links to official pages.

2. **Citizen starts an address change**

   * Example:
     *"I need to update the address on my Ohio driver's license. Can you help me submit the change?"*
   * Agent explains the process and required fields.

3. **Multi-turn data collection**

   The agent asks for and confirms:

   * License number and DOB
   * Full legal name
   * Old address (street, city, state, ZIP)
   * New address
   * Preferred contact method
   * Optional email/phone

4. **Tool call**

   Once all required fields are collected and confirmed, the agent calls:

   ```jsonc
   create_license_address_change_request({
     "driverLicenseNumber": "OH99887766",
     "dateOfBirth": "1982-11-30",
     "firstName": "Marcus",
     "middleName": "",
     "lastName": "Bennett",
     "email": "m.bennett82@example.org",
     "phone": "419-555-3456",
     "oldAddressLine1": "222 River Road",
     "oldAddressLine2": "",
     "oldCity": "Toledo",
     "oldState": "OH",
     "oldZip": "43604",
     "newAddressLine1": "333 Highland Square",
     "newAddressLine2": "",
     "newCity": "Akron",
     "newState": "OH",
     "newZip": "44303",
     "preferredContactMethod": "phone",
     "conversationSummary": "Marcus Bennett requested an official driver's license address change."
   })
   ```

5. **Database write**

   * Azure Function inserts a row into `dbo.LicenseAddressChangeRequests`.
   * Example query to view latest entries:

     ```sql
     SELECT TOP 10 *
     FROM dbo.LicenseAddressChangeRequests
     ORDER BY Id DESC;
     ```

6. **Confirmation to the user**

   * The agent returns a friendly message, such as:

     > Your Ohio BMV address-change request for license OH99887766 has been submitted.
     > You will be contacted via your preferred method (phone) once processing is complete.

---

## 4. How Ohio BMV Could Adopt This Pattern

This POC is designed to be **adaptable**:

1. **Deploy in a BMV-owned Azure subscription**

   * Recreate the Foundry agent configuration.
   * Provision Bing Search + Custom Search configuration with BMV-owned keys.
   * Deploy the Azure Functions MCP server and point it at BMV's non-prod systems.

2. **Integrate with existing systems of record**

   * Replace the demo SQL table with:
     * Existing case-management database
     * APIs
     * Queues or workflow engines
   * Keep the MCP tool interface the same (structured, typed inputs).

3. **Extend workflows**

   * New MCP tools for:
     * Suspensions / reinstatement review requests
     * Plate replacement
     * Title-related requests
     * Document readiness checklists before in-person visits
   * All follow the same pattern: **grounded Q&A + guided workflow + typed MCP action**.

---

## 5. Repository Structure

```text
.
├── mcp-server/                        # Git submodule: Azure Functions MCP server
│   ├── src/
│   │   └── function_app.py           # MCP tools implementation
│   ├── infra/                        # Bicep infrastructure as code
│   └── README.md                     # MCP server documentation
├── sql/
│   └── license_address_change_schema.sql   # CREATE TABLE script for demo table
├── prompts/
│   └── ohio-bmv-agent-system-prompt.md     # System prompt used in Foundry agent
├── docs/
│   └── bing-custom-search-setup.md         # Bing Custom Search configuration guide
└── README.md                          # This file
```

---

## 6. Getting Started

### Prerequisites

- Azure subscription with access to:
  - Azure AI Foundry
  - Bing Custom Search API
  - Azure Functions
  - Azure SQL Database
- [Azure Developer CLI (azd)](https://aka.ms/azd)
- [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local)

### Quick Start

1. **Clone this repository with submodules:**

   ```bash
   git clone --recurse-submodules https://github.com/john-carroll-sw/ohio-bmv-foundry-agent.git
   cd ohio-bmv-foundry-agent
   ```

2. **Set up Bing Custom Search:**

   Follow the guide in [docs/bing-custom-search-setup.md](./docs/bing-custom-search-setup.md)

3. **Deploy the MCP Server:**

   ```bash
   cd mcp-server
   azd up
   ```

   Follow the prompts to deploy to your Azure subscription.

4. **Configure the Foundry Agent:**

   - Create a new agent in Azure AI Foundry
   - Use the system prompt from [prompts/ohio-bmv-agent-system-prompt.md](./prompts/ohio-bmv-agent-system-prompt.md)
   - Attach the Bing Custom Search grounding
   - Connect the MCP server endpoint

5. **Test the integration:**

   Try asking the agent questions like:
   - "What services does the Ohio BMV offer?"
   - "I need to update my driver's license address"

---

## 7. Notes & Next Steps

* **Secrets**

  * Connection strings, keys, and credentials should be stored in **Azure Key Vault** or application settings, not in source control.

* **Environment parity**

  * This POC was built for demo purposes; a production rollout should include:
    * Monitoring + logging
    * Retry and error-handling flows
    * Role-based access control around the MCP endpoint
    * Formal testing and validation against BMV policies

* **Questions / Handoff**

  * This repo is intended as a **starting point** for Ohio BMV and the Microsoft account/engineering teams to explore productionization paths.

---

## 8. License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 9. Contributing

This is a proof-of-concept repository. For questions or suggestions, please open an issue.
