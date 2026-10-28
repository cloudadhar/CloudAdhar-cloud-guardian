"""
CloudAdhar Cloud Guardian - security & cost checks (STARTER).

YOUR TASKS in the workshop:
  TODO 1: check_unattached_ebs      (COST)
  TODO 2: check_unused_elastic_ips  (COST)
All security checks are already complete. Read one first to learn the pattern.
Stuck? Compare with ../solution/checks.py

Plain, deterministic Python using READ-ONLY AWS API calls.
Python finds the problems. The AI only explains them.

Every finding is a dict:
  category  "SECURITY" or "COST"
  resource  what is affected
  issue     what is wrong
  severity  CRITICAL / HIGH / MEDIUM / LOW
  fix       AWS Console steps
  link      direct AWS Console link to the resource
  est_monthly_usd  (cost findings only) rough monthly waste in USD
"""
import os
import re
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

REGION = os.getenv("AWS_REGION", "us-east-1")

# Ports that should never be open to the whole internet
RISKY_PORTS = {22: "SSH", 3389: "RDP", 3306: "MySQL", 5432: "PostgreSQL",
               1433: "SQL Server", 27017: "MongoDB", 6379: "Redis"}
KEY_MAX_AGE_DAYS = 90
SNAPSHOT_MAX_AGE_DAYS = 90
STOPPED_MAX_DAYS = 7

# Approximate us-east-1 prices (USD). Good enough to show "you are wasting money".
PRICE_EBS_PER_GB = {"gp3": 0.08, "gp2": 0.10, "io1": 0.125, "io2": 0.125, "st1": 0.045, "sc1": 0.015, "standard": 0.05}
PRICE_SNAPSHOT_PER_GB = 0.05
PRICE_IDLE_EIP_PER_MONTH = 3.60  # $0.005 per hour x 720 hours


def _ec2_link(fragment: str) -> str:
    return f"https://{REGION}.console.aws.amazon.com/ec2/home?region={REGION}#{fragment}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ===========================================================================
# SECURITY CHECKS
# ===========================================================================
def check_s3_buckets() -> list:
    """Find S3 buckets where Block Public Access is OFF or not configured."""
    s3 = boto3.client("s3", region_name=REGION)
    findings = []
    for bucket in s3.list_buckets().get("Buckets", []):
        name = bucket["Name"]
        issue = None
        try:
            cfg = s3.get_public_access_block(Bucket=name)["PublicAccessBlockConfiguration"]
            if not all(cfg.values()):
                issue = "Block Public Access is partly OFF"
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration":
                issue = "Block Public Access is not configured"
            else:
                continue
        if issue:
            findings.append({
                "category": "SECURITY", "resource": f"S3 bucket {name}", "issue": issue, "severity": "HIGH",
                "fix": "Permissions tab > Block public access > Edit > tick 'Block all public access' > Save changes",
                "link": f"https://s3.console.aws.amazon.com/s3/buckets/{name}?tab=permissions",
            })
    return findings


def check_security_groups() -> list:
    """Find security groups with risky ports (SSH, RDP, databases) or ALL traffic open to the internet."""
    ec2 = boto3.client("ec2", region_name=REGION)
    findings = []
    for page in ec2.get_paginator("describe_security_groups").paginate():
        for sg in page["SecurityGroups"]:
            for rule in sg.get("IpPermissions", []):
                world = [r["CidrIp"] for r in rule.get("IpRanges", []) if r.get("CidrIp") == "0.0.0.0/0"]
                world += [r["CidrIpv6"] for r in rule.get("Ipv6Ranges", []) if r.get("CidrIpv6") == "::/0"]
                if not world:
                    continue
                proto, from_p, to_p = rule.get("IpProtocol"), rule.get("FromPort"), rule.get("ToPort")
                if proto == "-1":
                    labels = ["ALL traffic"]
                else:
                    labels = [f"port {p} ({svc})" for p, svc in RISKY_PORTS.items()
                              if from_p is not None and from_p <= p <= to_p]
                for label in labels:
                    findings.append({
                        "category": "SECURITY",
                        "resource": f"Security group {sg['GroupId']} ({sg['GroupName']})",
                        "issue": f"{label} is open to the whole internet ({world[0]})",
                        "severity": "CRITICAL",
                        "fix": "Inbound rules > Edit inbound rules > change Source to 'My IP' (or delete the rule) > Save rules",
                        "link": _ec2_link(f"SecurityGroup:groupId={sg['GroupId']}"),
                    })
    return findings


def check_iam_users() -> list:
    """Find IAM users without MFA and active access keys older than 90 days."""
    iam = boto3.client("iam")
    findings = []
    for page in iam.get_paginator("list_users").paginate():
        for user in page["Users"]:
            name = user["UserName"]
            link = f"https://console.aws.amazon.com/iam/home#/users/details/{name}?section=security_credentials"
            if not iam.list_mfa_devices(UserName=name)["MFADevices"]:
                findings.append({
                    "category": "SECURITY", "resource": f"IAM user {name}", "issue": "No MFA device enabled",
                    "severity": "MEDIUM", "fix": "Security credentials tab > Assign MFA device", "link": link,
                })
            for key in iam.list_access_keys(UserName=name)["AccessKeyMetadata"]:
                age = (_now() - key["CreateDate"]).days
                if key["Status"] == "Active" and age > KEY_MAX_AGE_DAYS:
                    findings.append({
                        "category": "SECURITY", "resource": f"IAM user {name}",
                        "issue": f"Active access key is {age} days old", "severity": "MEDIUM",
                        "fix": "Security credentials tab > create a new access key, update your apps, "
                               "then Deactivate and Delete the old key",
                        "link": link,
                    })
    return findings


def check_root_mfa() -> list:
    """Check whether the AWS account root user has MFA enabled."""
    summary = boto3.client("iam").get_account_summary()["SummaryMap"]
    if summary.get("AccountMFAEnabled", 0) != 1:
        return [{
            "category": "SECURITY", "resource": "Root user", "issue": "Root user has no MFA", "severity": "CRITICAL",
            "fix": "Sign in as root > Security credentials > Assign MFA device",
            "link": "https://console.aws.amazon.com/iam/home#/security_credentials",
        }]
    return []


# ===========================================================================
# COST CHECKS
# ===========================================================================
def check_unattached_ebs() -> list:
    """Find EBS volumes not attached to any EC2 instance (you still pay for them)."""
    ec2 = boto3.client("ec2", region_name=REGION)
    findings = []
    # TODO 1a: get volumes whose status is "available" (= not attached).
    #   Hint: ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])["Volumes"]
    volumes = []

    for v in volumes:
        # TODO 1b: estimate the monthly cost.
        #   Hint: v["Size"] (GiB) * PRICE_EBS_PER_GB.get(v["VolumeType"], 0.10)
        cost = 0

        # TODO 1c: append a finding dict. Copy the shape from check_s3_buckets and add:
        #   "category": "COST", "severity": "MEDIUM", "est_monthly_usd": round(cost, 2)
        #   "link": _ec2_link(f"VolumeDetails:volumeId={v['VolumeId']}")
        pass
    return findings


def check_unused_elastic_ips() -> list:
    """Find Elastic IP addresses not associated with anything (AWS charges for idle public IPs)."""
    ec2 = boto3.client("ec2", region_name=REGION)
    findings = []
    for a in ec2.describe_addresses()["Addresses"]:
        # TODO 2: if the address has NO "AssociationId" key, it's idle.
        #   Append a finding with "category": "COST", "severity": "LOW",
        #   "est_monthly_usd": PRICE_IDLE_EIP_PER_MONTH,
        #   "link": _ec2_link(f"ElasticIpDetails:AllocationId={a.get('AllocationId', '')}")
        pass
    return findings


def check_old_snapshots() -> list:
    """Find EBS snapshots you own that are older than 90 days."""
    ec2 = boto3.client("ec2", region_name=REGION)
    findings = []
    for page in ec2.get_paginator("describe_snapshots").paginate(OwnerIds=["self"]):
        for s in page["Snapshots"]:
            age = (_now() - s["StartTime"]).days
            if age > SNAPSHOT_MAX_AGE_DAYS:
                findings.append({
                    "category": "COST", "resource": f"EBS snapshot {s['SnapshotId']} ({s['VolumeSize']} GiB)",
                    "issue": f"Snapshot is {age} days old", "severity": "LOW",
                    "fix": "If no longer needed: Actions > Delete snapshot",
                    "link": _ec2_link(f"SnapshotDetails:snapshotId={s['SnapshotId']}"),
                    "est_monthly_usd": round(s["VolumeSize"] * PRICE_SNAPSHOT_PER_GB, 2),  # upper estimate
                })
    return findings


def check_stopped_instances() -> list:
    """Find EC2 instances stopped for more than 7 days (their EBS disks are still billed)."""
    ec2 = boto3.client("ec2", region_name=REGION)
    findings = []
    pages = ec2.get_paginator("describe_instances").paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}])
    for page in pages:
        for r in page["Reservations"]:
            for i in r["Instances"]:
                m = re.search(r"\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", i.get("StateTransitionReason", ""))
                days = None
                if m:
                    stopped = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    days = (_now() - stopped).days
                if days is not None and days <= STOPPED_MAX_DAYS:
                    continue
                name = next((t["Value"] for t in i.get("Tags", []) if t["Key"] == "Name"), "")
                findings.append({
                    "category": "COST", "resource": f"EC2 instance {i['InstanceId']} {name}".strip(),
                    "issue": f"Stopped for {days} days" if days is not None else "Stopped (stop date unknown)",
                    "severity": "LOW",
                    "fix": "If you don't need it: Instance state > Terminate (its EBS disks keep costing money while stopped)",
                    "link": _ec2_link(f"InstanceDetails:instanceId={i['InstanceId']}"),
                })
    return findings


SECURITY_CHECKS = [check_s3_buckets, check_security_groups, check_iam_users, check_root_mfa]
COST_CHECKS = [check_unattached_ebs, check_unused_elastic_ips, check_old_snapshots, check_stopped_instances]
ALL_CHECKS = SECURITY_CHECKS + COST_CHECKS


def run_all_checks() -> list:
    """Run every check. A failing check is reported instead of stopping the whole scan."""
    findings = []
    for check in ALL_CHECKS:
        try:
            findings.extend(check())
        except Exception as e:  # e.g. missing permission
            findings.append({"category": "INFO", "resource": check.__name__, "issue": f"Check could not run: {e}",
                             "severity": "LOW", "fix": "Check IAM permissions", "link": ""})
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    return sorted(findings, key=lambda f: order.get(f["severity"], 9))
