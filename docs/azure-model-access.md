# Live Azure model access evidence

> Privacy: account names, application origins, image digests and request IDs in this document are synthetic placeholders; replace them before use.

Checked 2026-11-16T20:16:50.449160+00:00. Task 2.7 only; hosting remains undeployed.

## Model stage

- The fresh reviewed plan was rechecked against the approved five creates and applied successfully.
- Created: dedicated resource group, OpenAI account, GPT-5 mini deployment, RG budget and scoped developer inference role.
- Model: `gpt-5-mini`, version `2025-08-07`, resource region `eastus2`, deployment type `GlobalStandard`, capacity 10 (10,000 TPM allocation).
- Model API: `2025-04-01-preview`. Key authentication is disabled.
- Actual model/account provisioning status was verified as Succeeded.
- Billing-property API reports active USD billing. Budget readback verifies amount 5/month, project resource-group scope, actual 50/80/100 thresholds and the private recipient input.
- The developer OpenAI User assignment was verified at the exact model-account scope using bounded read-only role checks.
- Actual account/tenant/object identifiers, endpoint and recipient remain in private Terraform inputs/outputs/state. They are not copied into this evidence.

## Authorized synthetic probe

- One `Hello` request, minimal reasoning, low verbosity, 32 completion tokens, two-second connect and fifteen-second request timeouts, zero automatic inference retries.
- HTTP request count: 1.
- HTTP status: 200.
- Sanitized request ID: `00000000-0000-0000-0000-000000000006`.
- Result category: `success`.
- Usable text: true.
- Finish reason: `stop`.
- Measured probe elapsed time: 2.223 seconds (includes local credential acquisition).
- Actual token usage: 24 input; 18 output (including reasoning where applicable).
- Reasoning-token detail: 0.
- Estimated gross token charge from verified public prices: USD 0.00004200. This is arithmetic, not observed invoice/cost visibility; promotional credits are not assumed.

Synthetic returned text:

```json
"Hi \u2014 how can I help you today?"
```

Usable model access is established for the tested deployment. Task 2.7 is complete.

## Price and remaining operational checks

- Refreshed Microsoft USD retail prices before apply: Global Standard input $0.25, cached input $0.025 and output $2.00 per million tokens; unchanged from `azure-costs.md`.
- Source: [Microsoft Retail Prices API](https://prices.azure.com/api/retail/prices), product `Azure OpenAI GPT5`, East US 2 `GPT 5 Mini` Global meters.
- Model catalog/lifecycle and available Global Standard quota were rechecked before apply. The reported model retirement remains July 13, 2027.
- Budget alerts are configured; actual email delivery and delayed Cost Management charges are not yet verified. The budget is not a spending cap.
- No app root, Entra SPA/API registrations, Container Apps hosting, GHCR publication, Chrome acceptance or destructive cleanup was performed.
- Terraform state/backups are retained, ignored by Git and owner-readable only. Partial-failure recovery must retain state and generate a fresh plan; never reuse the consumed pre-apply plan.
