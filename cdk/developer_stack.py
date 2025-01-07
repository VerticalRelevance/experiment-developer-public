from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_events as events,
    aws_events_targets as targets,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    Duration,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_ssm as ssm,
)
from constructs import Construct
from cdk.shared import (
    get_output,
    create_service_role,
)

class DeveloperStack(Stack):
    """AWS CDK Stack for developer infrastructure.
    
    This stack creates the following resources:
    - VPC with private subnets and VPC endpoints
    - ECS Fargate cluster and task definition
    - DynamoDB table
    - Lambda function with API Gateway
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.context = self.validate_context()
        self.bucket_name = get_output(self, "BucketName")
        self.bucket_key = get_output(self, "BucketKey")
        self.repo_uri = get_output(self, "APDECRRepo")
        self.prefix = self.context["prefix"]
        
        # Create infrastructure components
        self.vpc = self.create_networking()
        self.create_ecs_resources()
        self.create_event_rules()
        self.create_dynamodb_table()
        self.create_lambda_api()

    def validate_context(self) -> dict:
        """Validate and return the context configuration.
        
        Raises:
            ValueError: If required context values are missing
        """
        context = self.node.try_get_context("globals")
        required_keys = ["prefix", "appName", "region", "llm", "uningested", 
                        "triggerFile", "repo"]
        
        missing_keys = [key for key in required_keys if key not in context]
        if missing_keys:
            raise ValueError(f"Missing required context keys: {missing_keys}")
            
        if "name" not in context.get("repo", {}):
            raise ValueError("Missing required context key: repo.name")
            
        return context

    def create_networking(self) -> ec2.Vpc:
        """Create VPC and networking components.
        
        Returns:
            The created VPC
        """
        self.vpc = ec2.Vpc(self, "VPC", max_azs=1)

        route_table = ec2.CfnRouteTable(
            self,
            f"{self.prefix}-Routes",
            vpc_id=self.vpc.vpc_id,
        )
        route_table.apply_removal_policy(RemovalPolicy.DESTROY)

        gateway_endpoint = ec2.GatewayVpcEndpoint(
            self,
            f"{self.prefix}-GWEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            vpc=self.vpc,
        )
        self.ecr_endpoint_sg = ec2.SecurityGroup(
            self, f"{self.prefix}-ECREndpointSG",
            vpc=self.vpc,
            allow_all_outbound=True,
            description="Security group for ECR VPC endpoints"
        )
        self.ecr_endpoint_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443))
        vpc_endpoints = [
            self.create_vpc_endpoint(name)
            for name in ["ecr.dkr", "ecr.api", "ecs-agent", "ecs-telemetry", "ecs"]
        ]

        return self.vpc

    def create_vpc_endpoint(self, name: str) -> ec2.InterfaceVpcEndpoint:
        """Create a VPC endpoint for AWS services.
        
        Args:
            name: The AWS service name (e.g., 'ecr.dkr', 'ecs')
            
        Returns:
            An interface VPC endpoint for the specified service
        """
        try:
            endpoint = ec2.InterfaceVpcEndpoint(
                self,
                f"{self.prefix}-{name}Endpoint",
                vpc=self.vpc,
                service=ec2.InterfaceVpcEndpointService(
                    f"com.amazonaws.{self.context['region']}.{name}",
                    443
                ),
                subnets=ec2.SubnetSelection(
                    subnets=[self.vpc.private_subnets[0]]
                ),
                security_groups=[self.ecr_endpoint_sg]
            )
            return endpoint
        except Exception as e:
            raise RuntimeError(f"Failed to create VPC endpoint for {name}: {str(e)}")

    def create_ecs_resources(self) -> None:
        """Create ECS cluster, task definition, and container resources."""
        # Create execution role
        exec_role_policies = [
            {
                "actions": [
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage"
                ],
                "resources": ["*"]
            }
        ]

        self.ecs_exec_role = create_service_role(
            self,
            role_name="Exec",
            principal="ecs-tasks",
            managed_policies=[
                "service-role/AmazonECSTaskExecutionRolePolicy",
                "CloudWatchLogsFullAccess",
            ],
            inline_policies=exec_role_policies,
        )

        task_role_policies = [
            {
                "actions": ["bedrock:InvokeModel"],
                "resources": [
                    f"arn:aws:bedrock:{self.context['region']}::foundation-model/{self.context['llm']['bedrockModel']}"
                ],
            },
            {
                "actions": ["secretsmanager:GetSecretValue"],
                "resources": [
                    f"arn:aws:secretsmanager:*:*:secret:{self.context['llm']['openAiSecret']}*"
                ],
            },
            {
                "actions": [
                    "s3:GetObject",
                    "s3:GetBucketLocation",
                    "s3:ListBucket",
                    "s3:GetObjectVersion",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:GetObjectAcl",
                    "s3:PutObjectAcl",
                ],
                "resources": [
                    f"arn:aws:s3:::{self.bucket_name}/*",
                    f"arn:aws:s3:::{self.bucket_name}",
                ],
            },
            {
                "actions": ["kms:Decrypt", "kms:GenerateDataKey"],
                "resources": [f"arn:*:kms:*:*:key/{self.bucket_key}"],
            },
        ]
        self.ecs_task_role = create_service_role(
            self,
            role_name="Task",
            principal="ecs-tasks",
            managed_policies=["CloudWatchLogsFullAccess"],
            inline_policies=task_role_policies,
        )

        self.cluster = ecs.Cluster(
            self, "Cluster", vpc=self.vpc, container_insights=True
        )

        self.task_definition = ecs.FargateTaskDefinition(
            self,
            f"{self.prefix}-TaskDefinition",
            memory_limit_mib=512,
            cpu=256,
            execution_role=self.ecs_exec_role,
            task_role=self.ecs_task_role,
        )

        self.container = self.task_definition.add_container(
            f"{self.prefix}Container",
            image=ecs.ContainerImage.from_registry(f"{self.repo_uri}:latest"),
            logging=ecs.LogDriver.aws_logs(stream_prefix=self.context["appName"]),
            port_mappings=[
                ecs.PortMapping(container_port=80, host_port=80),
                ecs.PortMapping(container_port=443, host_port=443),
            ],
        )
        self.container.add_environment(name="bucket", value=self.bucket_name)

    def create_event_rules(self) -> None:
        """Create event rules for ECS task execution."""
        rule_role = create_service_role(
            self,
            role_name="Rule",
            principal="events",
            managed_policies=["service-role/AmazonECSTaskExecutionRolePolicy"],
            inline_policies=[
                {
                    "actions": ["iam:PassRole"],
                    "resources": [
                        self.ecs_exec_role.role_arn,
                        self.ecs_task_role.role_arn,
                    ],
                },
                {
                    "actions": ["ecs:RunTask"],
                    "resources": [self.task_definition.task_definition_arn],
                },
            ],
        )

        target = targets.EcsTask(
            cluster=self.cluster,
            task_definition=self.task_definition,
            role=rule_role,
            enable_execute_command=True,
            # launch_type=ecs.LaunchType.FARGATE,
            subnet_selection=ec2.SubnetSelection(subnets=[self.vpc.private_subnets[0]]),
            security_groups=[self.ecr_endpoint_sg],
            tags=[
                targets.Tag(key=f"{self.prefix}_Task", value="ingest"),
            ],
            container_overrides=[
                targets.ContainerOverride(
                    container_name=self.container.container_name,
                    environment=[
                        targets.TaskEnvironmentVariable(
                            name="uningested_path",
                            value=self.context["uningested"],
                        ),
                        targets.TaskEnvironmentVariable(
                            name="trigger_file",
                            value=self.context["triggerFile"],
                        ),
                        targets.TaskEnvironmentVariable(name="CHOICE", value="ingest"),
                    ],
                )
            ],
        )

        rule = events.Rule(
            self,
            f"{self.context['prefix']}BucketRule",
            event_pattern=events.EventPattern(
                detail_type=["Object Created"],
                source=["aws.s3"],
                resources=[f"arn:aws:s3:::{self.bucket_name}"],
                detail={
                    "bucket": {
                        "name": [self.bucket_name],
                    },
                    "object": {
                        "key": [{"prefix": f"{self.context['uningested']}/diff.txt"}]
                    },
                },
            ),
            targets=[target],
        )

    def create_dynamodb_table(self) -> None:
        """Create DynamoDB table for storing data."""
        self.table = dynamodb.Table(
            self,
            "APDeveloperTable",
            table_name="ap-developer",
            partition_key=dynamodb.Attribute(
                name="pk", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PROVISIONED,
            read_capacity=5,
            write_capacity=5,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.table.grant_read_write_data(self.ecs_task_role)

    def create_lambda_api(self) -> None:
        """Create Lambda function with API Gateway."""
        self.lambda_role = iam.Role(
            self,
            "LambdaECSRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ecs:RunTask",
                    "ecs:DescribeTasks",
                ],
                resources=[self.task_definition.task_definition_arn],
            )
        )

        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[self.ecs_exec_role.role_arn, self.ecs_task_role.role_arn],
            )
        )

        lambda_layer = _lambda.LayerVersion(
            self,
            "APILambdaLayer",
            code=_lambda.Code.from_asset("cdk/lambda/layer"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
        )

        lambda_function = _lambda.Function(
            self,
            "APIProxyLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="main.lambda_handler",
            role=self.lambda_role,
            layers=[lambda_layer],
            code=_lambda.Code.from_asset("cdk/lambda/src"),
            timeout=Duration.seconds(30),
            environment={
                "BUCKET": self.bucket_name,
                "CLUSTER_NAME": self.cluster.cluster_name,
                "TASK_DEFINITION": self.task_definition.task_definition_arn,
                "SUBNET_ID": self.vpc.private_subnets[0].subnet_id,
                "SECURITY_GROUP_ID": self.ecr_endpoint_sg.security_group_id,
                "CONTAINER_NAME": self.container.container_name,
            },
        )

        allowed_ips = self.context.get("allowed_ips", ["0.0.0.0/0"])
        resource_policies = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.AnyPrincipal()],
                actions=["execute-api:Invoke"],
                resources=["execute-api:/*/*/*"],
                conditions={"IpAddress": {"aws:SourceIp": allowed_ips}},
            ),
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["execute-api:Invoke"],
                resources=["execute-api:/*/*/*"],
                conditions={"NotIpAddress": {"aws:SourceIp": allowed_ips}},
            ),
        ]

        # Create the REST API with greedy proxy integration
        rest_api = apigw.LambdaRestApi(
            self,
            "APDeveloperApi",
            handler=lambda_function,
            proxy=True,
            deploy_options=apigw.StageOptions(stage_name="prod"),
            policy=iam.PolicyDocument(statements=resource_policies),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=apigw.Cors.DEFAULT_HEADERS
            )
        )

        self.table.grant_read_write_data(self.lambda_role)
