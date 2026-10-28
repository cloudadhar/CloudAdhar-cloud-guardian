"""
CloudAdhar Cloud Guardian - Strands tools (STARTER).

Each tool is a thin wrapper around a plain Python check in checks.py.
The docstring is what the AI reads to decide WHEN to call the tool.
"""
from strands import tool

import checks


@tool
def check_s3_buckets() -> list:
    """SECURITY: Find S3 buckets where Block Public Access is off (risk of public data)."""
    return checks.check_s3_buckets()


@tool
def check_security_groups() -> list:
    """SECURITY: Find security groups with SSH, RDP, database ports or all traffic open to the internet."""
    return checks.check_security_groups()


@tool
def check_iam_users() -> list:
    """SECURITY: Find IAM users without MFA and access keys older than 90 days."""
    return checks.check_iam_users()


@tool
def check_root_mfa() -> list:
    """SECURITY: Check whether the root user of the AWS account has MFA enabled."""
    return checks.check_root_mfa()


@tool
def check_unattached_ebs() -> list:
    """COST: Find EBS volumes not attached to any instance, with estimated monthly waste in USD."""
    return checks.check_unattached_ebs()


@tool
def check_unused_elastic_ips() -> list:
    """COST: Find Elastic IPs not associated with any instance, with estimated monthly waste in USD."""
    return checks.check_unused_elastic_ips()


@tool
def check_old_snapshots() -> list:
    """COST: Find EBS snapshots older than 90 days, with estimated monthly cost in USD."""
    return checks.check_old_snapshots()


@tool
def check_stopped_instances() -> list:
    """COST: Find EC2 instances that have been stopped for more than 7 days."""
    return checks.check_stopped_instances()


ALL_TOOLS = [check_s3_buckets, check_security_groups, check_iam_users, check_root_mfa,
             check_unattached_ebs, check_unused_elastic_ips, check_old_snapshots, check_stopped_instances]
