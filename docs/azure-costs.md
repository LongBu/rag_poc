# Azure chat cost estimate

Checked November 16, 2026. USD public list prices, not an invoice or spending cap.
[Setup and staged approval](azure-setup.md) records the account checks. Public
price/model evidence is in [azure-price-evidence.json](azure-price-evidence.json).
The cost preflight itself performed no deployment or inference. The model-only
apply and bounded probe completed; see
[the live model evidence](azure-model-access.md). Hosting and browser acceptance
subsequently completed, followed by owner-authorized Azure/GHCR teardown on
November 17. The reviewed image was published on GHCR; see
[release evidence](azure-release.md).

## Choice and eligibility

Select **East US 2**, `gpt-5-mini` version `2025-08-07`, **GlobalStandard**,
capacity **10**. This is a cost tie-breaker, not a requirement to use East US 2.
Live subscription catalog/usage reads show the following candidates:

| US resource region | GPT-5 mini GlobalStandard / DataZoneStandard | Unused quota (thousands TPM) | Hosting environment allowance |
| --- | --- | --- | --- |
| East US 2 | Both catalog-listed, GA | 1,000 / 300 | 1 unused managed environment |
| East US | Both catalog-listed, GA | 1,000 / 300 | 1 unused managed environment |
| West US 3 | Both catalog-listed, GA | 1,000 / 300 | 1 unused managed environment |

All three have identical verified model, Consumption compute and standard
internet-egress prices below. There is no demonstrated price saving from moving
the existing candidate away from East US 2. Co-locate the eventual app and account
to avoid an intentional cross-region transfer. This comparison is among these
three verified candidates, not proof that every Azure region has been searched.

Microsoft's live model catalog and [lifecycle table](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirement-schedule)
list this model/version as GA with inference retirement **July 13, 2027**.
Recheck before applying. Catalog SKU default capacity is 10 and maximum is
1,000,000; the catalog does not publish a minimum here. Use the reported default,
not an invented minimum. Capacity is quota allocation, not reserved/provisioned
throughput or a dollar limit. Actual deployability/capacity and inference remain
unverified until the reviewed model apply/probe. No provisioned SKU is selected.
Batch offers are excluded because this is synchronous interactive chat.

Global Standard can process inference globally, outside the US resource region.
The owner accepts that geography. Data Zone Standard restricts processing to its
zone and costs 10% more here; US-only inference is not a requirement. See
[deployment types](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/deployment-types).

## Verified rates and units

The [Microsoft Retail Prices API](https://prices.azure.com/api/retail/prices)
was queried for USD prices in each candidate region. Model product name is
`Azure OpenAI GPT5`, service `Foundry Models`, meter names `GPT 5 Mini ...`,
with spaces rather than the API model identifier `gpt-5-mini`. The evidence file
retains the exact public meter IDs, prices, units, regions and effective dates.

| Pay-per-token type | Input / 1M | Cached input / 1M | Output / 1M |
| --- | ---: | ---: | ---: |
| Global Standard | $0.25 | $0.025 | $2.00 |
| Data Zone Standard | $0.275 | $0.0275 | $2.20 |

No cache hit is assumed. Every request rebills all sent history and the
server-owned instruction. Reasoning tokens count as billed output within the
**512 completion-token** cap. Low verbosity, minimal reasoning and concise-answer
instructions limit output but do not guarantee that text fits or appears within
the cap. Empty reasoning-only output is a failure, not a reason to retry or raise
the cap automatically. See [reasoning behavior](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning).

Container Apps Consumption rates are **$0.000024/vCPU-second**,
**$0.000003/GiB-second**, and **$0.40/million external HTTP requests** in all
three regions. For 0.25 vCPU and 0.5 GiB, active compute is $0.0000075/second.
Use minimum zero, maximum one replica, single revision and no Dedicated profile,
private endpoint, planned maintenance, GPU or extra gateway/database. Readiness
probes are not billable HTTP requests. [Consumption billing](https://learn.microsoft.com/en-us/azure/container-apps/billing)
provides subscription-shared monthly grants: 180,000 vCPU-seconds, 360,000
GiB-seconds and two million external HTTP requests. Their availability to this
project depends on other subscription use. At zero replicas there is no replica
compute charge; startup, inference and scale-down tails are active costs.

Standard Microsoft-network internet data transfer out has a first 100 GB/month
zero-price tier, then **$0.087/GB** in these regions at the first paid tier.
The evidence also lists inter-region transfer separately. Do not use an
inter-region rate as internet egress. Budget for requests/assets/answers and
recheck actual metering, routing and shared free-tier usage. The gross examples
below deliberately charge 1 GB at the first paid rate, without claiming the free
allowance is dedicated to this application. Source: [bandwidth pricing](https://azure.microsoft.com/en-us/pricing/details/bandwidth/).

## Reproducible workload arithmetic

Assume **1,000 input tokens per request**, including prompt, instruction and
rebilled history, and the full **512 output tokens**. Input/history token counts
are assumptions, not a conversion from the app's code-point limits. Longer
history costs more. Assume 30 active replica-seconds per query including an
allocated share of startup/tail overhead, ten external HTTP requests per query
including assets/auth/config, and 1 GB total monthly internet egress. Real cold
starts and scale-down tails are unmeasured; this is a scenario, not an upper bound.

```text
model(N) = N * (1000 * 0.25 + 512 * 2.00) / 1,000,000
         = N * 0.001274
active_seconds = N * 30
compute(N) = active_seconds * (0.25 * 0.000024 + 0.5 * 0.000003)
HTTP(N) = N * 10 * 0.40 / 1,000,000
egress = 1 GB * 0.087 = 0.087
gross = model + compute + HTTP + egress
```

| Requests/month | Model | Active compute | HTTP | Gross egress | Gross Azure total | Azure net if all recurring grants remain unused |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | $0.1274 | $0.0225 | $0.0004 | $0.0870 | $0.2373 | $0.1274 |
| 1,000 | $1.2740 | $0.2250 | $0.0040 | $0.0870 | $1.5900 | $1.2740 |
| 10,000 | $12.7400 | $2.2500 | $0.0400 | $0.0870 | $15.1170 | $12.7400 |

At 10,000 requests, the assumed 300,000 active seconds consume 75,000 vCPU-seconds
and 150,000 GiB-seconds, below both grants if otherwise unused; 100,000 HTTP
requests and 1 GB egress also fit. Net costs apply recurring allowances only;
**zero promotional credit** is assumed for every estimate. The verified trial
credit is not an ongoing allowance or justification for provisioning.

With 8,000 input/history tokens, model cost rises to $0.003024/request: $0.3024,
$3.0240 and $30.2400 at these volumes, before hosting/egress. Actual output may be
shorter; none of these scenarios permits an automatic increase over 512.
At the original 1,000-token scenario, Data Zone model cost would be $0.14014,
$1.4014 and $14.014; compute/egress stay the same, making Global Standard cheaper.

True idle baseline under the proposed design is $0 metered model/replica usage
when there are no tokens and no running replicas, with no paid registry,
retained logs or Dedicated resources provisioned. Do not confuse this with
zero-cost startup/scale-down, no traffic, or guaranteed monthly spend below $5.
The 10,000-request scenario already exceeds $5 from tokens alone. A continuously
active replica for 30 days would cost $19.44 gross compute before grants, so
scale-to-zero and actual observed active time matter.

## Registry, identity, logging and other exclusions

[GitHub's current container-registry policy](https://docs.github.com/en/billing/concepts/product-billing/github-packages)
provides free container-image storage and bandwidth and promises notice before a
policy change. Record public GHCR as $0 registry storage/transfer at today's
policy, not a perpetual guarantee. Its costs are outside the Azure RG budget.
Check the publisher's GitHub plan, Actions minutes/artifact retention and runner
costs separately before publication; no unverified free build allowance is
assumed. Local builds consume the owner's own compute/network. CI must neither
publish images nor deploy cloud resources.

Public GHCR images are anonymously inspectable regardless of repository
visibility. Review every layer and build history before the separately approved
release. Pull by immutable digest; use no registry secret or Azure Container
Registry. Microsoft-hosted image pulls may incur startup compute; don't assume
registry-free means compute-free. Retain known-good digests for rollback.

Base Entra app registrations/managed identity require no paid Entra license for
this design; premium conditional-access licensing is excluded. Logs destination
is disabled (`logs_destination = ""` in the pinned AzureRM provider); no Log Analytics workspace, diagnostic retention or ingestion is
assumed. Live logs must omit tokens, callback values, prompts, answers and raw
provider exceptions. Enabling retained diagnostics requires another cost review.
Taxes, exchange rates, support plans, custom domains, unrelated subscription
resources and external build/publisher charges are outside the sample Azure
numbers. Actual billing must be checked after an approved probe and hosting test.

## Budget and release gate

Billing-property API currently reports **USD**, active FreeTrial billing and
spending protection. Subscription budget listing succeeds. The subsequent model-stage apply verified
the actual RG budget, recipient and thresholds; delivered emails are not yet verified. Cost Management now reports the original
model usage at USD 0.00915125 (7,069 input / 3,692 output tokens), matching these
rates. Actual hosting-cost visibility remains unverified. The supplied GitHub
report attributes $0.024 gross Actions usage to this repository, fully discounted
to $0 billed; final monthly coverage remains unverified. See
[actual cost/lifecycle evidence](azure-operations.md). The historical budget was
removed during teardown. Its default amount is **USD 5/month**,
with actual-cost notifications at 50%, 80%, 100%, to an explicitly supplied email.
The model root owns this budget over the same RG used by the later app root, so
both Azure stages are in scope; GitHub is excluded. Budgets do not stop spend and
cost/notification evaluation is delayed. Do not rely on trial-credit protection
as an application cap or turn it off automatically.

Block billable probing until budget creation/readback and scoped inference RBAC
are verified. A non-USD subscription requires an explicit equivalent amount and
conversion date before changing inputs/guards. Recheck model retirement,
capacity, model API compatibility, pricing, public registry terms and a fresh
plan before each stage. A failed probe leaves app hosting and publication pending.
No Terraform apply, inference, browser acceptance, cost delivery or publication
check is complete merely because this guide or an offline test passes.
