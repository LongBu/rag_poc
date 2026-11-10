# Bedrock application costs

Reviewed 2026-11-09. All amounts are USD, before taxes, with **zero promotional
credits**. Deployment is not required to read this guide. This is a workload
estimate, not a spending ceiling. Region: `us-east-1`; model:
`amazon.nova-micro-v1:0`, standard regional on-demand inference.

## Reference rates and verification

Nova Micro prices are **verified at $0.035 per million input tokens and $0.14
per million output tokens** from the [regional AWS Price List](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrock/current/us-east-1/index.json),
offer version `20261106184538`, published `2026-11-06T18:45:38Z`, read on
2026-11-09. The US East (N. Virginia) standard on-demand SKUs
`USE1-NovaMicro-input-tokens` and `USE1-NovaMicro-output-tokens` quote
$0.000035 and $0.00014 per **1,000** tokens respectively. Their product feature
is `On-demand Inference`, not batch, cached, priority, or cross-region inference.
Recheck before deployment if prices change. The [Bedrock pricing page](https://aws.amazon.com/bedrock/pricing/)
uses a dynamic regional table; the numeric verification came from the catalog.

Other reference rates, checked against the linked AWS pricing pages and examples:

| Component | Gross rate used | Assumptions |
| --- | --- | --- |
| [Lambda](https://aws.amazon.com/lambda/pricing/) | $0.0000166667/GB-second + $0.20/million requests | x86_64, 512 MB, no provisioned concurrency, default ephemeral storage |
| [HTTP API](https://aws.amazon.com/api-gateway/pricing/) | $1/million requests | First request tier; CORS preflight and rejected requests can add requests |
| [S3 Standard](https://aws.amazon.com/s3/pricing/) | $0.023/GB-month; $0.005/1,000 PUT/LIST; $0.0004/1,000 GET | Small frontend and optional deployment ZIP; no replication or version accumulation |
| [CloudFront pay-as-you-go](https://aws.amazon.com/cloudfront/pricing/pay-as-you-go/) | $0.085/GB + $0.01/10,000 HTTPS requests | US viewer example; other viewer locations can cost more; no flat-rate subscription |
| [CloudWatch Logs](https://aws.amazon.com/cloudwatch/pricing/) | $0.50/GB ingested + $0.03/GB-month retained | Standard logs, seven-day retention, no message bodies or credentials |
| [Cognito Lite](https://aws.amazon.com/cognito/pricing/) | $0.0055/MAU first paid band | One direct password user; no Plus, advanced security, SMS, or machine-to-machine clients |
| [Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/) | $0 for notification-only monitoring | No actions or reports; IAM has no additional service charge |

## Request estimates

Input includes **all resent history**, not just the latest question. Output is
capped at 512 tokens; actual shorter answers cost less. Code-point limits bound
payloads but are not exact token budgets.

```text
inference = input_tokens / 1,000,000 * 0.035
          + output_tokens / 1,000,000 * 0.14
lambda    = requests * (0.5 * duration_seconds * 0.0000166667 + 0.20 / 1,000,000)
http_api  = requests / 1,000,000
```

The following assumes 1,000 total input tokens, 512 output tokens, one Lambda
invocation, and five seconds billed duration per query. No retries or rejected
requests are included.

| Queries/month | Bedrock | Lambda | HTTP API | Gross subtotal |
| --- | --- | --- | --- | --- |
| 100 | $0.010668 | $0.004187 | $0.000100 | $0.014955 |
| 1,000 | $0.106680 | $0.041867 | $0.001000 | $0.149547 |
| 10,000 | $1.066800 | $0.418668 | $0.010000 | $1.495468 |

Lambda waits for inference. At 20 seconds the compute portion quadruples:
10,000 queries cost $1.668670 for Lambda and $2.745470 for the three-service
subtotal. Cold starts and retries add usage. Measure the real adapter startup
and generation time rather than relying on five seconds.

## Hosting, authentication, storage, and logging

For a separate illustrative monthly workload, assume 1 GB CloudFront transfer,
10,000 HTTPS asset requests, 0.1 GB of frontend objects, 0.1 GB of optional ZIP
artifacts, 1,000 S3 PUT/LIST requests and 10,000 S3 GET requests. Assume 0.01 GB
log ingestion and conservatively 0.01 GB-month retained, plus one Cognito MAU.

| Component | Gross monthly estimate |
| --- | --- |
| CloudFront | $0.095000 |
| S3 storage, including artifacts | $0.004600 |
| S3 PUT/LIST + GET | $0.009000 |
| CloudWatch Logs | $0.005300 |
| Cognito Lite | $0.005500 |
| Total separate overhead | $0.119400 |

Adding this overhead to 10,000 five-second queries gives **$1.614868 gross**.
Asset traffic does not scale exactly with chat queries because of browser/CDN
caching. API response egress is separate: budget approximately $0.009 for 0.1 GB
at a conservative $0.09/GB if no shared transfer allowance remains. Recheck
regional data transfer rates. S3 transfer to CloudFront has no origin transfer
charge under published S3 terms. Costs can persist at zero queries (stored
assets/artifacts and retained logs); empty unused infrastructure is not a
promise of a zero bill.

## Recurring allowances versus credits

Published recurring allowances include Lambda's one million requests and
400,000 GB-seconds/month, Cognito Lite's 10,000 direct/social MAU per account or
organization, and CloudFront's first TB of transfer plus HTTPS request allowance.
The CloudFront page currently contains both 10-million and 20-million request
examples; use the conservative 10-million figure until account terms are
confirmed. This workload fits either example. CloudWatch includes limited free
log usage; check the current 5-GB terms. These allowances are shared with other
usage and must be confirmed for the account; none is assumed in the gross tables.

If the above recurring Lambda/Cognito/CloudFront/CloudWatch allowances are
available and unused, the 10,000-query example becomes $1.066800 Bedrock +
$0.010000 HTTP API + $0.013600 S3 = **$1.090400**, before any separately billed
transfer or email. No time-limited HTTP API/S3 trial or promotional credit is
assumed. With exhausted allowances, use the gross estimate instead.

Open **Billing and Cost Management → Credits** in the target account and inspect
the remaining balance, expiration date, eligible services, restrictions, and
billing owner. Check **Free Tier** separately for usage/eligibility. Record the
review date without copying account secrets into source. A credit balance is
not recurring free capacity and may not apply to every charge.

## Follow-up costs

Three turns with 100 new user tokens and 200 assistant tokens each bill input
as 100, 400, then 700 tokens: 1,200 input plus 600 output = **$0.000126** at the
reference model rates, excluding any template overhead. Every retained user
and assistant message is input again on the next call. The newest ten completed
exchanges are candidates for context; total-input bounds may remove older pairs.
Browser localStorage retains more history separately and creates no AWS database
or history-storage charge. Copying an answer makes no model call.

## Budget and exclusions

The default $5 monthly budget sends actual-cost emails above 50%, 80%, and 100%.
Its service labels were checked against public AWS Price List product
`servicename` attributes on 2026-11-09: `Amazon Bedrock`, `AWS Lambda`,
`Amazon API Gateway`, `Amazon Cognito`, `Amazon Simple Storage Service`,
`Amazon CloudFront`, and `AmazonCloudWatch`. These deliberately match billing
labels, which can differ from product display names. Catalog service codes are
AmazonBedrock, AWSLambda, AmazonApiGateway, AmazonCognito, AmazonS3,
AmazonCloudFront, and AmazonCloudWatch; use the same regional offer URL pattern
above, with CloudFront's global `current/index.json` offer. Verify deployed
budget filters as part of the live account checks.
It aggregates the configured application services across the account and can
include unrelated workloads. Credits/refunds are excluded from tracked costs.
Billing updates and emails are delayed: **alerts do not stop spending**. The
512-token response cap, API throttling, concurrency one, and timeout bound each
request or request rate, not monthly spending.

Excluded from the estimates: taxes, support plans, developer machines and CI,
bootstrap/recovery email delivery (see [SES pricing](https://aws.amazon.com/ses/pricing/)),
extra uploads/invalidations, failed/unauthorized traffic, model retries, unusual
viewer locations, and unrelated account usage. No custom domain, NAT gateway,
WAF subscription, provisioned model throughput, provisioned Lambda concurrency,
SMS, or paid Cognito security tier is planned. Recheck prices, model lifecycle,
and account access before a saved deployment plan is approved.
