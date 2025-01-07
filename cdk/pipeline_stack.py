from constructs import Construct
from importlib.machinery import SourceFileLoader
from aws_cdk import (
    Stack,
    Stage,
    pipelines as pipelines,
    aws_codebuild as codebuild,
    aws_iam as iam,
)
from cdk.shared import get_output
from typing import List, Optional, Type

class PipelineStack(Stack):
    """AWS CDK Stack for CI/CD pipeline infrastructure.
    
    This stack creates a CodePipeline with stages for:
    - Source code from GitHub
    - CDK synthesis
    - Stack deployment stages
    - Git diff tracking and file uploads
    """

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.context = self.validate_context()
        self.app_name = self.context["appName"]
        self.prefix = self.context["prefix"]
        self.bucket_name = self.context["bucketName"]
        
        self.policies = self._create_pipeline_policies()
        self.pipeline = self.create_pipeline()
        
        # Create deployment stages
        self._create_deployment_stages()

    def validate_context(self) -> dict:
        """Validate and return the context configuration.
        
        Raises:
            ValueError: If required context values are missing
        """
        context = self.node.try_get_context("globals")
        required_keys = [
            "appName", "prefix", "region", "bucketName", 
            "pipelineName", "uningested", "triggerFile",
            "code", "llm", "repo"
        ]
        
        missing_keys = [key for key in required_keys if key not in context]
        if missing_keys:
            raise ValueError(f"Missing required context keys: {missing_keys}")
            
        return context

    def _create_pipeline_policies(self) -> List[dict]:
        """Create IAM policies for the pipeline.
        
        Returns:
            List of policy statements for the pipeline
        """
        return [
            {
                "actions": ["codepipeline:ListPipelineExecutions"],
                "resources": [
                    f"arn:aws:codepipeline:{self.context['region']}:*:{self.context['pipelineName']}"
                ],
            },
            {
                "actions": [
                    "s3:GetBucket*",
                    "s3:GetObject*",
                    "s3:List*",
                    "s3:PutObject",
                ],
                "resources": [
                    f"arn:aws:s3:::{self.bucket_name}",
                    f"arn:aws:s3:::{self.bucket_name}/*",
                ],
            },
            {"actions": ["s3:ListAllMyBuckets"], "resources": ["*"]},
            {
                "actions": ["kms:GenerateDataKey", "kms:Encrypt", "kms:Decrypt"],
                "resources": [f"arn:aws:kms:{self.context['region']}:*:key/*"],
                "Condition": {"StringEquals": {"kms:ResourceTag/App": self.app_name}},
            },
        ]

    def create_pipeline(self, num: str = "") -> pipelines.CodePipeline:
        """Create the main CodePipeline.
        
        Args:
            num: Optional suffix for pipeline name
            
        Returns:
            Configured CodePipeline instance
        """
        return pipelines.CodePipeline(
            self,
            f"{self.prefix}-Pipeline{num}",
            docker_enabled_for_synth=True,
            self_mutation=True,
            pipeline_name=self.context["pipelineName"],
            synth_code_build_defaults=self._get_synth_build_options(),
            synth=self._create_synth_step(),
            code_build_defaults=pipelines.CodeBuildOptions(
                role_policy=[
                    iam.PolicyStatement(actions=p["actions"], resources=p["resources"])
                    for p in self.policies
                ]
            ),
        )

    def _get_synth_build_options(self) -> pipelines.CodeBuildOptions:
        """Get CodeBuild options for synthesis stage."""
        return pipelines.CodeBuildOptions(
            build_environment=codebuild.BuildEnvironment(
                environment_variables=self._get_build_environment_vars()
            )
        )

    def _get_build_environment_vars(self) -> dict:
        """Get environment variables for build environment."""
        return {
            "OPENAI_SECRET_NAME": codebuild.BuildEnvironmentVariable(
                value=self.context["llm"]["openAiSecret"]
            ),
            "GITHUB_OWNER": codebuild.BuildEnvironmentVariable(
                value=self.context["repo"]["owner"]
            ),
            "GITHUB_REPO_NAME": codebuild.BuildEnvironmentVariable(
                value=self.context["repo"]["name"]
            ),
            "GIT_BRANCH": codebuild.BuildEnvironmentVariable(
                value=self.context["repo"]["branch"]
            ),
            "GITHUB_CONN": codebuild.BuildEnvironmentVariable(
                value=self.context["repo"]["connection"]
            ),
        }

    def _create_synth_step(self) -> pipelines.ShellStep:
        """Create synthesis step for the pipeline."""
        return pipelines.ShellStep(
            "Synth",
            input=pipelines.CodePipelineSource.connection(
                repo_string=f"{self.context['repo']['owner']}/{self.context['repo']['name']}",
                branch=self.context["repo"]["branch"],
                connection_arn=self.context["repo"]["connection"],
                code_build_clone_output=True,
            ),
            commands=[
                "npm install -g aws-cdk",
                "cd cdk",
                "python -m pip install -r cdk_requirements.txt",
                "cd ..",
                "sh cdk/lambda/prep_script.sh",
                "cdk synth",
            ],
            primary_output_directory="cdk.out",
        )

    def _create_deployment_stages(self) -> None:
        """Create and configure pipeline deployment stages."""
        upload_git_diff_files = self._create_git_diff_step()
        
        # Add deployment stages
        repo_stage = self.add_stack_deployment_stage("Repo")
        developer_stage = self.add_stack_deployment_stage(
            "Developer", post=[upload_git_diff_files]
        )

    def _create_git_diff_step(self) -> pipelines.CodeBuildStep:
        """Create step for tracking and uploading git diffs."""
        return pipelines.CodeBuildStep(
            "Upload Git Diff Files",
            commands=self._get_git_diff_commands(),
        )

    def _get_git_diff_commands(self) -> List[str]:
        """Get shell commands for git diff processing."""
        return [
            f"pipeline_name={self.context['pipelineName']}",
            f"bucket={self.bucket_name}",
            "echo $bucket",
            f"uningested={self.context['uningested']}",
            "COMMIT=$(aws codepipeline list-pipeline-executions --pipeline-name $pipeline_name | jq -r '.pipelineExecutionSummaries[0].sourceRevisions[0].revisionId')",
            "DIFF=$(git diff-tree --stat $COMMIT | grep '+' | sed '/changed/d;s/|[^|]*$//')",
            "echo $DIFF",
            f"TRIGGER={self.context['triggerFile']}",
            "UPLOAD=false",
            "for change in $DIFF; do"
            "\necho $change"
            "\ncase $change in"
            f"\n    {self.context['code']}*)"
            "\n    echo 'Uploading new code'"
            "\n    UPLOAD=true"
            "\n    aws s3 cp $change s3://$bucket/$uningested/$change"
            "\n    ;;"
            "\nesac"
            "\ndone",
            "echo $UPLOAD",
            "if $UPLOAD; then"
            "\n    echo Starting task with trigger file upload."
            "\n    touch $TRIGGER"
            "\n    aws s3 cp $TRIGGER s3://$bucket/$uningested/$TRIGGER"
            "\nfi",
        ]

    def add_stack_deployment_stage(
        self, 
        stack_name: str, 
        pre: Optional[List[pipelines.Step]] = None,
        post: Optional[List[pipelines.Step]] = None,
        **kwargs
    ) -> pipelines.StageDeployment:
        """Add a deployment stage to the pipeline.
        
        Args:
            stack_name: Name of the stack to deploy
            pre: Optional pre-deployment steps
            post: Optional post-deployment steps
            **kwargs: Additional arguments for stage creation
            
        Returns:
            Configured stage deployment
        """
        stack = self.dynamic_import(
            f"{stack_name.lower()}_stack",
            f"{stack_name.capitalize()}Stack"
        )
        stage = NewStage(
            self,
            f"{self.prefix}-{stack_name}Stage",
            stack=stack,
            stack_name=stack_name,
            **kwargs,
        )
        return self.pipeline.add_stage(stage, pre=pre, post=post)

    def dynamic_import(self, module_name: str, class_name: str) -> Type[Stack]:
        """Dynamically import a stack class.
        
        Args:
            module_name: Name of the module to import
            class_name: Name of the class to import
            
        Returns:
            Stack class
        """
        try:
            module = SourceFileLoader(module_name, f"cdk/{module_name}.py").load_module()
            return getattr(module, class_name)
        except Exception as e:
            raise ImportError(f"Failed to import {class_name} from {module_name}: {str(e)}")


class NewStage(Stage):
    """Stage for deploying CDK stacks."""
    
    def __init__(
        self,
        scope: Construct,
        id: str,
        stack: Type[Stack],
        stack_name: str,
        **kwargs
    ) -> None:
        """Initialize a new deployment stage.
        
        Args:
            scope: CDK app scope
            id: Stage identifier
            stack: Stack class to instantiate
            stack_name: Name for the stack
            **kwargs: Additional arguments for stack creation
        """
        super().__init__(scope, id, **kwargs)
        stack(self, stack_name, **kwargs)
