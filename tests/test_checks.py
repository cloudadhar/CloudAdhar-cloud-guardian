"""
Offline tests using moto (fake AWS). No AWS account or cost needed.
Run:  pip install -r requirements-dev.txt && pytest -q
"""
import importlib.util
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import boto3
import pytest
from moto import mock_aws

os.environ.update(AWS_DEFAULT_REGION="us-east-1", AWS_REGION="us-east-1",
                  AWS_ACCESS_KEY_ID="testing", AWS_SECRET_ACCESS_KEY="testing")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "solution"))
import checks  # noqa: E402


def load_lambda():
    spec = importlib.util.spec_from_file_location("lambda_function", ROOT / "lambda" / "lambda_function.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_bad_account():
    """Recreate the workshop's deliberate mistakes in fake AWS."""
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="cloudadhar-demo-bad")
    s3.create_bucket(Bucket="cloudadhar-demo-good")
    s3.put_public_access_block(Bucket="cloudadhar-demo-good", PublicAccessBlockConfiguration={
        "BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2.describe_vpcs()["Vpcs"][0]["VpcId"]
    sg = ec2.create_security_group(GroupName="cloudadhar-demo-open-ssh", Description="d", VpcId=vpc)["GroupId"]
    ec2.authorize_security_group_ingress(GroupId=sg, IpPermissions=[{
        "IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
    vol = ec2.create_volume(AvailabilityZone="us-east-1a", Size=1, VolumeType="gp3")["VolumeId"]
    eip = ec2.allocate_address(Domain="vpc")["PublicIp"]
    boto3.client("iam").create_user(UserName="cloudadhar-demo-user")
    return {"sg": sg, "vol": vol, "eip": eip}


# ---------------- security ----------------
@mock_aws
def test_public_bucket_flagged_with_link():
    make_bad_account()
    f = checks.check_s3_buckets()
    names = [x["resource"] for x in f]
    assert "S3 bucket cloudadhar-demo-bad" in names
    assert "S3 bucket cloudadhar-demo-good" not in names
    assert f[0]["link"].startswith("https://s3.console.aws.amazon.com/s3/buckets/")


@mock_aws
def test_open_ssh_and_database_ports_flagged():
    ids = make_bad_account()
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2.describe_vpcs()["Vpcs"][0]["VpcId"]
    db = ec2.create_security_group(GroupName="open-mysql", Description="d", VpcId=vpc)["GroupId"]
    ec2.authorize_security_group_ingress(GroupId=db, IpPermissions=[{
        "IpProtocol": "tcp", "FromPort": 3306, "ToPort": 3306, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
    web = ec2.create_security_group(GroupName="https", Description="d", VpcId=vpc)["GroupId"]
    ec2.authorize_security_group_ingress(GroupId=web, IpPermissions=[{
        "IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
    f = checks.check_security_groups()
    text = " ".join(x["resource"] + x["issue"] for x in f)
    assert ids["sg"] in text and "port 22 (SSH)" in text
    assert db in text and "3306 (MySQL)" in text
    assert web not in text
    assert all(x["severity"] == "CRITICAL" and "#SecurityGroup:groupId=" in x["link"] for x in f)


@mock_aws
def test_iam_user_without_mfa_flagged():
    make_bad_account()
    assert any(x["resource"] == "IAM user cloudadhar-demo-user" and "MFA" in x["issue"]
               for x in checks.check_iam_users())


@mock_aws
def test_old_access_key_flagged():
    iam = boto3.client("iam")
    iam.create_user(UserName="old-key-user")
    iam.create_access_key(UserName="old-key-user")
    with mock.patch.object(checks, "_now", return_value=datetime.now(timezone.utc) + timedelta(days=200)):
        assert any("days old" in x["issue"] for x in checks.check_iam_users())


# ---------------- cost ----------------
@mock_aws
def test_unattached_ebs_flagged_with_cost():
    ids = make_bad_account()
    f = checks.check_unattached_ebs()
    assert len(f) == 1 and ids["vol"] in f[0]["resource"]
    assert f[0]["est_monthly_usd"] == 0.08 and f[0]["category"] == "COST"


@mock_aws
def test_idle_elastic_ip_flagged():
    ids = make_bad_account()
    f = checks.check_unused_elastic_ips()
    assert len(f) == 1 and ids["eip"] in f[0]["resource"] and f[0]["est_monthly_usd"] == 3.60


@mock_aws
def test_old_snapshot_flagged():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vol = ec2.create_volume(AvailabilityZone="us-east-1a", Size=8)["VolumeId"]
    snap = ec2.create_snapshot(VolumeId=vol)["SnapshotId"]
    assert not any(snap in x["resource"] for x in checks.check_old_snapshots())   # new snapshot: OK
    with mock.patch.object(checks, "_now", return_value=datetime.now(timezone.utc) + timedelta(days=120)):
        assert any(snap in x["resource"] for x in checks.check_old_snapshots())  # 120 days later: flagged


@mock_aws
def test_stopped_instance_flagged_after_7_days():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    iid = ec2.run_instances(ImageId="ami-12c6146b", MinCount=1, MaxCount=1)["Instances"][0]["InstanceId"]
    ec2.stop_instances(InstanceIds=[iid])
    later = datetime.now(timezone.utc) + timedelta(days=30)
    with mock.patch.object(checks, "_now", return_value=later):
        f = checks.check_stopped_instances()
    assert any(iid in x["resource"] for x in f)


@mock_aws
def test_clean_account_has_no_cost_findings():
    assert checks.check_unattached_ebs() == []
    assert checks.check_unused_elastic_ips() == []


# ---------------- lambda ----------------
@mock_aws
def test_lambda_sends_email_with_links_even_if_bedrock_fails():
    ids = make_bad_account()
    topic = boto3.client("sns", region_name="us-east-1").create_topic(Name="cloudadhar-guardian-alerts")["TopicArn"]
    lf = load_lambda()
    lf.TOPIC_ARN = topic
    sent = {}
    real_client = boto3.client

    def fake_client(name, *a, **kw):
        c = real_client(name, *a, **kw)
        if name == "sns":
            orig = c.publish
            def publish(**kwargs):
                sent.update(kwargs)
                return orig(**kwargs)
            c.publish = publish
        return c

    with mock.patch.object(lf.boto3, "client", side_effect=fake_client):
        out = lf.lambda_handler({}, None)
    assert out["email_sent"] and out["critical"] >= 1
    body = sent["Message"]
    assert "AI summary unavailable" in body          # Bedrock not available in moto -> graceful fallback
    assert ids["sg"] in body and ids["vol"] in body and ids["eip"] in body
    assert "Open: https://" in body
    assert sent["Subject"].startswith("Cloud Guardian:")


@mock_aws
def test_lambda_uses_ai_summary_when_bedrock_works():
    make_bad_account()
    lf = load_lambda()
    fake = {"output": {"message": {"content": [{"text": "Fix the open SSH port first."}]}}}
    real_client = boto3.client

    def fake_client(name, *a, **kw):
        if name == "bedrock-runtime":
            m = mock.Mock()
            m.converse.return_value = fake
            return m
        return real_client(name, *a, **kw)

    with mock.patch.object(lf.boto3, "client", side_effect=fake_client):
        body = lf.build_email(lf.run_all_checks(), lf.ai_summary(lf.run_all_checks()))
    assert "Fix the open SSH port first." in body


def test_lambda_file_is_up_to_date():
    """lambda_function.py must be rebuilt after changing checks.py."""
    built = (ROOT / "lambda" / "lambda_function.py").read_text()
    assert (ROOT / "solution" / "checks.py").read_text() in built
