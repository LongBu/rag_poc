# Cost verification, rollback and teardown

> Privacy: account names, application origins, image digests and request IDs in this document are synthetic placeholders; replace them before use.

## Observed costs

Cost review performed November 17, 2026 (UTC). These are partial current-month
observations, not a final invoice or monthly forecast.

- Budget readback: existing project resource-group scope; amount USD 5/month;
  actual thresholds 50/80/100 enabled; notification recipient matches the private
  model input. Billing currency was independently verified as USD during activation.
  The group covers both model and hosting roots. Email delivery is not proven.
- The first Cost Management query returned 429. One bounded retry succeeded.
  Month-to-date daily grouping by service returned a single row: November 16,
  `Foundry Models`, USD **0.000042**, with no next page.
- The original model access probe recorded 24 input and 18 output tokens.
  `(24 × 0.25 + 18 × 2.00) / 1,000,000 = USD 0.000042` at the verified Global
  Standard rates. The reported service/day charge matches that single-probe
  estimate. This does not reconcile later browser calls or prove they were free.
- No Container Apps row is present in the successful cost result. Do not treat
  absence as proof of no usage/charges, nor assume dedicated free allowances.
  Hosting and later inference cost visibility/reconciliation remain pending.
- The owner supplied GitHub's current-month November report: November 2 gross
  $0.07/billed $0; November 3 $0.04/$0; November 10 $0.02/$0. Combined listed
  gross **$0.13**, billed **$0**. The excerpt is account-level and lacks product,
  repository and SKU attribution. No claim is made that those amounts came from
  this chat project or that all future publisher/build usage is free.
- GitHub's current policy separately provides free container-registry storage
  and bandwidth. Builds observed in this session ran locally. Authenticated
  GitHub CLI billing/run reads were unavailable; the unauthenticated repository
  Actions endpoint returned 404, which does not prove absence of workflow runs.
  Publisher/Actions charges remain outside the Azure budget.

Detailed Azure budget/cost evidence is owner-only and Git-ignored in
`infra/azure/app/cost-evidence-private.log`. It contains private identifiers and
recipient information; do not publish it. No access token was saved in it.
Do not put billing exports into image layers or commit them.

Cost Management data is delayed, and new subscriptions can take up to 48 hours
for all features to become available. Recheck the same project group after data
updates, grouped by Service name/resource/meter as available. Record actual
model and hosting amounts and covered dates. Reconcile later model charges only
against matching available usage totals; do not invent prompt/history lengths or
reconstruct private conversations. No usable model token metric definitions were
returned by the attempted definition lookup, so no aggregate token total was
inferred. Compare reported zero hosting cost with actual allowance/usage evidence
rather than assuming it. Task 6.4 stays unchecked until this remaining verification
is performed or its completion scope is explicitly revised by the owner.

## Historical cost query after teardown (November 17, 2026)

A subscription-scope Cost Management query still returned history after the
resource group and accounts were deleted. Filter: resource group
`private-azure-chat`, November 1 through 17 UTC; grouped by usage date, resource
ID and meter. The returned resource ID was the project's Azure OpenAI account.
Amounts are USD:

| Date | Meter | Usage | Cost |
|---|---|---:|---:|
| Nov 16 | GPT-5 Mini input, 1M tokens | 24 tokens | $0.000006 |
| Nov 16 | GPT-5 Mini output, 1M tokens | 18 tokens | $0.000036 |
| Nov 17 | GPT-5 Mini input, 1M tokens | 7,045 tokens | $0.00176125 |
| Nov 17 | GPT-5 Mini output, 1M tokens | 3,674 tokens | $0.007348 |

The observed total is 7,069 input tokens and 3,692 output tokens, costing
$0.00915125. Meter quantities and amounts reconcile at the recorded rates;
November 16's row matches the earlier 24/18-token probe. No Container Apps
meter row appeared in this query, which does not establish zero hosting cost or
that no delayed charge will arrive. The query was run during an open billing
period. Recheck after the data delay and invoice close before treating it as
final. Azure documents 8–24 hour typical availability for EA/MCA and up to 72
hours for pay-as-you-go; available cost history is retained at least seven years
([Cost Management data freshness and retention](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/understand-cost-mgt-data)).

The GitHub screenshot remains account-level evidence ($0.13 gross, $0 billed)
without product/repository attribution. GitHub's Usage page can filter by
product, SKU and repository and generate a detailed CSV for a custom range up to
31 days ([usage reporting](https://docs.github.com/en/billing/tutorials/gather-insights)).
The authenticated CLI billing request returned 404 and stated the current token
needs the `user` scope. Use the GitHub web UI rather than broadening that token.
The report has since been checked below. Task 6.4 remains open for hosting-cost
visibility and final Azure reconciliation.

## Task 6.4 billing recheck (November 17, 2026)

The owner supplied a detailed GitHub usage CSV, inspected locally without copying
the export into the repository. Its three rows reconcile exactly:

| Attribution | Linux Actions minutes | Gross USD | Discount USD | Billed USD |
|---|---:|---:|---:|---:|
| `rag_poc`, November 10, `.github/workflows/checks.yml` | 4 | 0.024 | 0.024 | 0 |
| Other repository, November 2–3 | 17 | 0.102 | 0.102 | 0 |
| All supplied rows | 21 | 0.126 | 0.126 | 0 |

Each row uses $0.006/minute; quantity × rate equals gross, and gross minus
discount equals net. The $0.126 total rounds to the previously reported $0.13.
The authenticated repository Actions API independently lists two November 10
`Application checks` runs, one failed and one successful. These establish run
history, not a per-run allocation of the four billed-report minutes. Image builds
for the Azure release were observed locally. No registry/storage/bandwidth row
appears in the supplied CSV; registry pricing policy remains separate from this
observed Actions usage. The export's full date-range coverage was not supplied,
so it does not establish final monthly usage or absence of later charges.

A fresh read-only subscription Cost Management query filtered to the deleted
project group, November 1–17 UTC, grouped by day/service/meter, returned the same
four model rows above, USD currency, and no next page. Arithmetic checked with
decimal values: `(7069 × 0.25 + 3692 × 2) / 1,000,000 = $0.00915125`.
This reconciles reported input/output meter usage against the estimate's rates,
including later inference. The estimate's 1,000-input/512-output request scenario
is not an observed request count and cannot establish actual hosting time.

- [x] Historical budget scope, USD currency, recipient match and actual thresholds.
- [x] Available model-meter quantities reconciled at the documented rates.
- [x] Supplied GitHub report attributed by product/repository and reconciled.
- [x] Rollback, ordered teardown, retained state and separate package cleanup documented.
- [ ] Actual hosting usage/cost or allowance evidence; no hosting row was returned.
- [ ] Final Azure reconciliation after delayed usage and billing-period close.
- [ ] Final monthly GitHub report coverage and any later usage.
- [ ] Actual budget email delivery; configuration verification does not prove delivery.

No resources were recreated, model requests made, credentials changed or cleanup
performed in this recheck. Task 6.4 remains unchecked for the unresolved costs.

Sources:
[Azure cost data and latency](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/understand-cost-mgt-data),
[GitHub container registry billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages).

## Rollback (only when requested)

The last deployed digest was (the app and package have since been deleted):

```text
ghcr.io/example/private-azure-chat@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

The previous verified rollback digest was:

```text
ghcr.io/example/private-azure-chat@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

Neither digest is currently available for rollback following the owner's package
deletion. The steps below describe rollback while a deployment and its images
still exist; they cannot restore the deleted deployment. A new deployment needs
a reviewed build/publication and fresh infrastructure plans.

The previous image uses the old visible Bedrock name; the runtime Azure identity
and infrastructure contracts are the same. Verify anonymous access to the chosen
rollback digest before planning. Edit only `image_digest` in the ignored private
app inputs; keep tenant, owner, identity and hosting values current. With an
owner-only umask, prepare and review a fresh plan:

```sh
umask 077
terraform -chdir=infra/azure/app plan -var-file=private.tfvars.json -out=rollback.tfplan
terraform -chdir=infra/azure/app show rollback.tfplan
# Apply only after the rollback is requested and the actual plan reviewed:
terraform -chdir=infra/azure/app apply rollback.tfplan
```

Expect one app image update, not identity/model replacement or deletion. After
apply, verify readiness, denied anonymous query, exact digest, HTTPS and owner
login, and run a fresh no-change plan. Rollback can briefly overlap revisions
and is not zero-cost. Retain the consumed plan as a private historical artifact;
never reuse it or edit state to force a rollback. Nothing here was executed.

## Teardown (separate explicit request required)

1. Preserve owner-only backups of each root's current state and private inputs.
   Inventory managed resources, reviewed image digests and any unrelated group
   contents. State deletion is not resource deletion.
2. Prepare the **app root's** destroy plan using its current private inputs:

   ```sh
   umask 077
   terraform -chdir=infra/azure/app plan -destroy -var-file=private.tfvars.json -out=app-destroy.tfplan
   terraform -chdir=infra/azure/app show app-destroy.tfplan
   ```

   Review hosting, callback registrations, service principals, identity and the
   cross-root account-scoped inference assignment. Only after the separate
   teardown request/plan review may that saved destroy plan be applied. Confirm
   those managed resources are actually removed before proceeding to the model.
3. Prepare/review the **model root's** destroy plan with the actual original
   private model input file or original explicitly selected environment inputs.
   The path below is a placeholder, not a checked-in example to apply:

   ```sh
   terraform -chdir=infra/azure/model plan -destroy -var-file=/absolute/private/model.tfvars -out=model-destroy.tfplan
   terraform -chdir=infra/azure/model show model-destroy.tfplan
   ```

   Verify the dedicated model/deployment, developer assignment, budget and group
   are the intended resources and that unrelated resources will not be swept up
   by resource-group deletion. Apply only with the requested teardown and reviewed
   plan. Preserve state after partial errors and regenerate plans after changes.
4. Verify actual removal. Keep state/backups until teardown is confirmed; retain
   any required audit/rollback records afterward. Earlier charges, delayed billing
   and unrelated account permissions do not disappear with resource deletion.
5. Terraform teardown does **not** delete GHCR packages. Package/version deletion
   requires a separate explicit request identifying the versions. Preserve active
   and rollback digests until intentionally retired. Do not revoke shared publisher
   credentials or delete the repository as an implicit cleanup step.

No destroy plan was applied, resource deleted, state removed, package version
deleted or publisher credential changed during this review.

## Teardown completed (November 17, 2026)

The owner authorized deletion of all project Azure resources, the two inventoried
Foundry extras, and the GHCR package, while retaining Terraform state/backups and
the source repository. The app registrations, app, identity and environment were
removed first. Environment deletion completed in Azure after Terraform polling
lost DNS; a refresh confirmed it absent and removed its stale state entry. The
approved Foundry project and account were then deleted. A fresh five-delete model
plan removed the model deployment/account, budget, role assignment and resource
group. Azure confirmed the group absent and the Terraform states are empty.

GHCR deletion was attempted under the verified `example` account but GitHub
returned 403 because that CLI credential lacks `delete:packages` and
`read:packages`. The owner subsequently deleted the package through GitHub
package settings. The CLI scopes and exact endpoint/403 remain documented in
`azure-release.md` for a future API-based cleanup. The GitHub source repository,
state/backups and unrelated Azure resources were retained. Task 6.4 cost
reconciliation remains incomplete; teardown does not reconcile delayed charges.

## Prepared teardown review (not applied)

At the owner's request, current state/input backups for both roots were
created under ignored `teardown-backups/` directories with owner-only access
and SHA-256 verification. Model teardown inputs were reconstructed from current
state and the verified selected subscription/tenant because no original local
model input file remained. Recipient values were not printed or committed.

The app-only destroy plan proposes 15 managed deletions, no creates/updates,
and does not delete the group or model account/deployment. Resource inventory
found an additional unmanaged AIServices account and its project in the same
resource group. They are outside both Terraform states. The model destroy
preview proposes five managed deletions including the group; deleting that
group could also delete those unmanaged resources, which do not appear as
individual actions in the Terraform plan. The model preview is not approved
for apply until the owner decides whether to retain or explicitly remove them.

No destroy plan was applied. Apply order, if later authorized, remains app first,
verify removal, then regenerate/review the model plan using the agreed resource
scope. Keep GHCR deployment/rollback digests until Azure teardown is verified.
Package/version deletion remains a separate request; public registry storage/
bandwidth remains free under the currently verified policy. No package, state
or backup was deleted.

## Task 6.4 closed by owner acceptance (November 17, 2026)

The owner explicitly approved closing task 6.4 on the assumption that total
project Azure costs were below USD 5 given the small usage. This is an accepted
closeout assumption, not a newly verified billing result. Verified evidence
remains USD 0.00915125 in model charges and USD 0.024 gross / USD 0 net in
repository-attributed GitHub Actions usage.

The owner-approved completion scope no longer requires actual hosting-cost
attribution, final Azure billing reconciliation or final monthly GitHub report
coverage. Those checks remain unverified, as does budget email delivery; the
uncompleted evidence checkboxes remain unchecked. Earlier statements that task
6.4 was open describe the status before this acceptance. Task 6.4 is now complete
and the change has 27/27 tasks complete. No resources, billing settings, retained
state or packages were changed for closeout.
