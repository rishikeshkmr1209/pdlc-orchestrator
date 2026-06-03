# AWS Security Checklist — Project Reference

Reference for the `security-scan` skill. Covers IAM, S3, Lambda, API Gateway, and other AWS services used in the project.

---

## IAM

### Roles and Policies
- [ ] No `"Effect": "Allow"` with both `"Action": "*"` and `"Resource": "*"` in production
- [ ] Lambda execution roles have only the permissions the function actually uses
- [ ] No inline policies on users — use roles and groups
- [ ] Service roles attached to EC2/ECS/Lambda (no IAM user access keys for services)
- [ ] Access keys rotated if they exist (prefer OIDC/roles instead)

**Red flags in CDK/SAM/CFN templates:**
```yaml
# BAD — wildcard on sensitive service
Statement:
  - Effect: Allow
    Action: "s3:*"
    Resource: "*"

# GOOD — specific actions and resources
Statement:
  - Effect: Allow
    Action:
      - s3:GetObject
      - s3:PutObject
    Resource: !Sub "arn:aws:s3:::${BucketName}/*"
```

### Permission Boundaries
- [ ] Developers cannot create IAM entities without permission boundaries (if org policy requires)
- [ ] CDK bootstrap policies are reviewed and not overly permissive

---

## S3

- [ ] `BlockPublicAccess` enabled on all buckets (unless explicitly serving public static assets)
- [ ] Bucket policies do not grant `s3:GetObject` to `"Principal": "*"` unless intentional
- [ ] Server-side encryption enabled (SSE-S3 minimum; SSE-KMS for sensitive data)
- [ ] Versioning enabled on buckets storing critical data
- [ ] Access logging enabled for audit trails
- [ ] CORS configured with specific origins (not `AllowedOrigins: ["*"]` on private buckets)

**CDK check:**
```typescript
// GOOD
const bucket = new s3.Bucket(this, 'DataBucket', {
  blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
  encryption: s3.BucketEncryption.KMS_MANAGED,
  versioned: true,
  serverAccessLogsBucket: logsBucket,
});
```

---

## Lambda

- [ ] No hardcoded AWS credentials in function code or environment variables
- [ ] Environment variables for secrets reference SSM Parameter Store or Secrets Manager — not plain values
- [ ] Reserved concurrency set to prevent runaway invocations on high-traffic functions
- [ ] Timeout set appropriately — not left at default 3 seconds for complex operations
- [ ] Dead Letter Queue (DLQ) configured for async invocations
- [ ] VPC placement if the function accesses RDS, ElastiCache, or internal services
- [ ] Least-privilege execution role (not `AdministratorAccess` or `PowerUserAccess`)

**Secrets access pattern:**
```typescript
// BAD — secret in env var plain text
const apiKey = process.env.MY_API_KEY;

// GOOD — fetch from Secrets Manager (cached)
import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';
const client = new SecretsManagerClient({});
let cachedSecret: string;

async function getApiKey(): Promise<string> {
  if (!cachedSecret) {
    const response = await client.send(new GetSecretValueCommand({
      SecretId: process.env.API_KEY_SECRET_ARN,
    }));
    cachedSecret = response.SecretString!;
  }
  return cachedSecret;
}
```

---

## API Gateway

- [ ] Authentication configured (Cognito authorizer, Lambda authorizer, or IAM auth)
- [ ] Throttling configured at stage or method level
- [ ] WAF associated with API Gateway (for internet-facing APIs)
- [ ] Custom domain uses TLS 1.2+ security policy
- [ ] Access logging enabled
- [ ] No resources with `"authorizationType": "NONE"` unless truly public

---

## DynamoDB

- [ ] Encryption at rest enabled (enabled by default, but verify)
- [ ] Point-in-time recovery (PITR) enabled for production tables
- [ ] No `Scan` operations in production code paths (use `Query` with key conditions)
- [ ] TTL configured for ephemeral data (sessions, temporary tokens)
- [ ] VPC endpoint used if Lambda is in VPC (avoid internet traffic)

---

## SQS / SNS

- [ ] Server-side encryption enabled (SSE-SQS or SSE-KMS)
- [ ] Dead letter queues configured for all standard queues
- [ ] Queue policies do not allow `"AWS": "*"` principal
- [ ] VPC endpoints used for Lambda-to-SQS within same VPC

---

## CloudWatch / Logging

- [ ] Log groups have retention policies (not "Never expire")
- [ ] Log groups with PII/sensitive data have encryption with KMS
- [ ] No sensitive data in metric filters or dashboards
- [ ] Alarms configured for security-relevant metrics (failed auth, error rates)

---

## Secrets Manager / SSM Parameter Store

- [ ] Secrets stored in Secrets Manager (not SSM plain text for sensitive values)
- [ ] Rotation configured for database credentials
- [ ] Resource-based policies on secrets restrict access to specific roles
- [ ] SecureString used in SSM (not String) for credentials

---

## Network Security

- [ ] Security groups: ingress rules are as specific as possible
- [ ] No `0.0.0.0/0` ingress on port 22 (SSH) or port 3389 (RDP)
- [ ] VPC Flow Logs enabled on production VPCs
- [ ] PrivateLink or VPC endpoints for AWS service access (avoid internet routing)
- [ ] NACLs complement security groups for defense-in-depth

---

## CloudTrail

- [ ] CloudTrail enabled in all regions (or organization trail)
- [ ] Management events logged
- [ ] S3 data events logged for sensitive buckets
- [ ] CloudTrail log file validation enabled
- [ ] Trail logs stored in a dedicated, write-protected S3 bucket

---

## GitHub Actions — AWS Authentication

**Never use:**
```yaml
env:
  AWS_ACCESS_KEY_ID: AKIA...      # BAD — long-lived credential
  AWS_SECRET_ACCESS_KEY: xxx
```

**Always use OIDC:**
```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/github-actions-deploy
      aws-region: ${{ vars.AWS_REGION }}
      role-session-name: GitHubActions-${{ github.run_id }}
```

The IAM role's trust policy should restrict to your specific GitHub org and repo:
```json
{
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:rbi-org/my-service:ref:refs/heads/main"
    }
  }
}
```
