# Spec Delta

## Purpose

Enable inexpensive owner-authenticated model-only conversations through browser, AWS CLI, and SDK access to Bedrock.

## ADDED Requirements

### Requirement: Reproducible access provisioning
The system SHALL provide Terraform configuration for separate model-scoped CLI and Lambda roles, defaulting to Amazon Nova Micro in us-east-1. The CLI role SHALL trust only a configured same-account principal. Connection outputs SHALL identify the role ARN, region, and model without creating long-lived credentials.

#### Scenario: Provision access
- **WHEN** valid account credentials and configuration are supplied and Terraform is applied
- **THEN** scoped roles exist and connection outputs identify the model and region

#### Scenario: Restricted invocation permissions
- **WHEN** permissions granted by either runtime role are evaluated
- **THEN** they grant invocation only for the selected model and no model-management permissions

### Requirement: CLI and SDK invocation
The system SHALL provide AWS CLI and Python SDK examples using temporary role credentials and Converse, defaulting to 512 output tokens and reporting answer text and token usage.

#### Scenario: Successful request
- **WHEN** an authorized user runs either example
- **THEN** it returns text and input/output token usage

#### Scenario: Access failure
- **WHEN** credentials, quotas, account restrictions, or model availability prevent invocation
- **THEN** the example exits unsuccessfully with an actionable diagnostic and no silent model/region fallback

### Requirement: Provisioning lifecycle
The system SHALL document authentication, account/model checks, plan/apply/destroy, and role assumption. It SHALL avoid provisioned throughput and always-running compute and exclude secrets, local state, saved plans, and private variables from version control.

#### Scenario: Review and teardown
- **WHEN** the user follows the documented lifecycle
- **THEN** intended resources are reviewable and removal affects only project-managed resources

### Requirement: Owner-only browser access
The application SHALL support current desktop Chrome over HTTPS with Cognito password sign-in and public registration disabled. API authorization SHALL validate access tokens and required scope. The backend SHALL independently validate tokens and permit only the configured owner subject before inference; missing owner configuration SHALL deny all queries.

#### Scenario: Owner query
- **WHEN** the owner signs in and submits a valid prompt
- **THEN** the application returns generated text and token usage

#### Scenario: Unauthorized request
- **WHEN** a token is missing, invalid, expired, wrong-scope, or belongs to another subject
- **THEN** the request is denied without invoking the model

#### Scenario: First deployment
- **WHEN** no owner subject is configured
- **THEN** all queries are denied and documented bootstrap steps explain owner activation

### Requirement: Browser credential and data boundaries
The frontend SHALL contain no AWS keys or OAuth client secret. Browser model calls SHALL use the protected API. The static shell MAY be public but SHALL contain no private user data; prompts and responses SHALL NOT be persisted server-side or recorded in application logs.

#### Scenario: Inspect static assets
- **WHEN** an unauthenticated visitor downloads frontend assets
- **THEN** no secrets/private messages are exposed and model queries still require authorization

### Requirement: Bounded browser requests
The API SHALL accept a current prompt of at most 4,000 Unicode code points and up to 10 completed exchanges, with a combined 32,000-code-point input limit, 256 KiB body limit, and server-enforced 512-token output maximum. It SHALL return safe errors without model fallback.

#### Scenario: Invalid input
- **WHEN** a prompt is empty, oversized, or non-string, history is malformed/oversized, or total limits are exceeded
- **THEN** the request is rejected before inference

#### Scenario: Client output override
- **WHEN** a client attempts to override generation limits
- **THEN** the model output maximum remains 512 tokens

### Requirement: Complete application unit-test coverage
The project SHALL enforce 100% Python statement/branch coverage with pytest and 100% frontend statement/branch/function/line coverage with Jest across all first-party application source, including unimported files. Only tests, dependencies, generated files, declarations, and non-application tooling/configuration SHALL be excluded; application logic SHALL NOT be omitted to satisfy coverage.

#### Scenario: Backend gate
- **WHEN** backend unit tests run locally or in CI
- **THEN** any uncovered statement or branch fails the gate without live AWS calls

#### Scenario: Frontend gate
- **WHEN** frontend unit tests run locally or in CI
- **THEN** any uncovered statement, branch, function, or line fails the gate, including unimported modules

#### Scenario: Exact reports
- **WHEN** clean installs and documented test commands run
- **THEN** terminal/machine-readable reports expose missing coverage and exact uncovered counters fail independently of rounding

### Requirement: Conversational context and complete responses
The application SHALL send the newest 10 completed exchanges plus the current prompt, dropping oldest whole exchanges as needed for input limits. Older saved messages SHALL remain independent of model context, with a context-limit notice. Answers SHALL appear complete after a loading state, without streaming.

#### Scenario: Follow-up
- **WHEN** the owner follows up after a successful answer
- **THEN** retained recent messages accompany the new prompt in order

#### Scenario: Context exceeded
- **WHEN** history exceeds the exchange or aggregate limit
- **THEN** oldest pairs leave model context with a notice, without being deleted merely for leaving context

#### Scenario: Failed request
- **WHEN** inference fails or authentication expires
- **THEN** an error is shown without a fabricated exchange or automatic billable retry

### Requirement: Owner-specific local conversation persistence
The frontend SHALL save bounded versioned messages in owner-keyed localStorage and restore them only after authentication. Tokens SHALL remain outside persistent storage. Explicit logout and Clear conversation SHALL remove saved messages; invalid data and storage failures SHALL be handled visibly without crashing or exposing another user's messages.

#### Scenario: Restore
- **WHEN** the same owner authenticates after refresh or reopening Chrome
- **THEN** valid saved messages are restored and can supply bounded follow-up context

#### Scenario: Clear or logout
- **WHEN** the owner clears the conversation or explicitly signs out
- **THEN** saved/visible history is erased and late responses or stale tabs cannot recreate it

#### Scenario: Invalid storage
- **WHEN** records are malformed, unsupported, oversized, or storage is unavailable
- **THEN** invalid records are ignored or the app continues in memory with a persistence warning

### Requirement: Model-only general-question answers
The application SHALL use only the selected model and supplied conversation context, without web search, external retrieval, or tool calls. The browser and documentation SHALL explain that answers are not verified against live sources.

#### Scenario: Current information question
- **WHEN** the owner asks about changing information
- **THEN** no search is initiated and the application does not claim live-source verification

### Requirement: Simple chat layout and submission controls
The frontend SHALL show a scrollable conversation with distinct You and Assistant labels, a multiline input, Submit, Clear conversation, and Sign out. Enter SHALL submit a valid draft and Shift+Enter SHALL insert a newline. Submission SHALL be disabled for invalid drafts or while a request is pending; keyboard handling SHALL NOT submit during input-method composition.

#### Scenario: Submit a question
- **WHEN** the owner clicks Submit or presses Enter on a valid draft while no request is pending
- **THEN** exactly one request starts, a loading indicator appears, and submission remains disabled until it settles

#### Scenario: Multiline or composed input
- **WHEN** the owner presses Shift+Enter or is composing text with an input method
- **THEN** the composer allows newline insertion or composition without sending the question

#### Scenario: Conversation display
- **WHEN** a complete answer is received
- **THEN** the interface displays labeled messages, token usage, and applicable context-limit notices in the scrollable conversation

### Requirement: Copy assistant answers
Each completed assistant answer SHALL have a Copy answer button that copies only that answer's text. The frontend SHALL report success only after copying succeeds and SHALL display an actionable message if clipboard access fails, without submitting another model request.

#### Scenario: Copy succeeds
- **WHEN** the owner selects Copy answer and clipboard writing succeeds
- **THEN** the clipboard contains exactly that assistant answer and the interface announces copy success

#### Scenario: Copy fails
- **WHEN** clipboard access is unavailable or rejected
- **THEN** the interface reports the failure, keeps the answer selectable for manual copying, and makes no model request

### Requirement: OAuth callback privacy
The frontend SHALL validate OAuth state and complete S256 PKCE through its OIDC client before accepting authentication. After capturing required callback parameters it SHALL replace the current browser-history entry with the clean application URL on both successful and failed callbacks, clear transient authentication state, and display only sanitized errors. Callback codes, state, OAuth error parameters, tokens, and full callback URLs SHALL NOT enter application logs. The frontend SHALL deliver `Referrer-Policy: no-referrer`. Any enabled frontend/API/origin access logs SHALL exclude query strings, cookies, Authorization headers, and callback-bearing referrers using an explicit safe field allowlist; incompatible logging formats SHALL remain disabled.

#### Scenario: Successful callback
- **WHEN** a valid authorization-code callback completes
- **THEN** authentication succeeds, the current history entry contains no OAuth parameters, transient state is removed, and subsequent requests disclose no referrer

#### Scenario: Failed callback
- **WHEN** callback validation or token exchange fails, or Cognito returns an OAuth error
- **THEN** authentication is not accepted, callback parameters and transient state are removed, and visible errors and logs contain no raw callback values

#### Scenario: Initial callback request logging
- **WHEN** a callback request reaches infrastructure before browser URL cleanup
- **THEN** enabled access-log configurations exclude its query parameters, cookies, authorization headers, and callback-bearing referrers while retaining safe operational metadata

### Requirement: Browser persistence safeguards
The frontend SHALL retain bounded owner-keyed localStorage persistence and in-memory authentication tokens. It SHALL explain that saved messages survive browser restarts and are readable by same-origin JavaScript and someone with access to the unlocked browser profile; owner-keying SHALL NOT be represented as encryption or protection against those actors. Prompts and answers SHALL render as inert text. The frontend SHALL serve an enforced Content Security Policy restricting scripts to bundled same-origin assets without unsafe inline scripts or eval, connections to required API/Cognito endpoints, and blocking objects and framing while restricting base URLs. It SHALL serve `X-Content-Type-Options: nosniff` and SHALL NOT load analytics or third-party scripts.

#### Scenario: HTML-like conversation content
- **WHEN** a prompt, restored message, or model answer contains HTML or script-like content
- **THEN** it appears as text without executing scripts or initiating embedded resource requests

#### Scenario: Delivered browser policy
- **WHEN** Chrome loads the deployed frontend and completes sign-in and a query
- **THEN** security headers are present, the enforced policy permits required application behavior and blocks disallowed scripts and connections

#### Scenario: Persistent data boundaries
- **WHEN** messages are saved and the owner clears the conversation or signs out
- **THEN** tokens never enter localStorage, saved history is removed under the existing erasure requirements, and the persistence notice accurately explains browser-profile and same-origin access
