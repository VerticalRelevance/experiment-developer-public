from aws_cdk import (
    Stack,
    aws_ecr as ecr,
    RemovalPolicy,
    aws_s3 as s3,
    aws_kms as kms,
    Tags,
)
from constructs import Construct
from cdk.shared import create_output


class RepoStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.app_name = self.node.try_get_context("globals")["appName"]

        ecr_repo = self.create_repo(repo_name="agent")
        bucket = self.create_bucket(
            bucket_name=self.node.try_get_context("globals")["bucketName"],
            events_enabled=True,
        )

        kms_key = kms.Key(
            self, f"{self.app_name}-KMSKey", removal_policy=RemovalPolicy.DESTROY
        )
        Tags.of(kms_key).add("App", self.app_name)

        # Cfn Outputs
        for name, value in {
            "BucketName": bucket.bucket_name,
            "BucketKey": bucket.encryption_key.key_id,
            "APDECRRepo": ecr_repo.repository_uri,
            "RepoName": ecr_repo.repository_uri,
        }.items():
            create_output(self, name=name, value=value)

    def create_repo(self, repo_name: str):
        repo = ecr.Repository(
            self,
            f"{self.app_name}-{repo_name}-repo",
            repository_name=f"{self.app_name}-{repo_name}-repo".lower(),
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True,
            encryption=ecr.RepositoryEncryption.AES_256,
        )
        return repo

    def create_bucket(self, bucket_name: str, events_enabled: bool = False):
        bucket = s3.Bucket(
            self,
            bucket_name,
            bucket_name=bucket_name,
            bucket_key_enabled=True,
            encryption=s3.BucketEncryption.KMS,
            event_bridge_enabled=events_enabled,
        )
        return bucket
