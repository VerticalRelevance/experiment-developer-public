from typing import Any, List, Union

from aws_cdk import (
    CfnOutput,
    Fn,
    aws_iam as iam,
)
from constructs import Construct


def create_output(self: Construct, name: str, value: Any) -> CfnOutput:
    """Create a CloudFormation output value.
    
    Args:
        self: CDK construct scope
        name: Name of the output
        value: Value to export
        
    Returns:
        Created CloudFormation output
        
    Raises:
        ValueError: If app name is not found in context
    """
    try:
        app_name = self.node.try_get_context("globals")["appName"]
        return CfnOutput(
            self,
            f"{app_name}-{name}",
            export_name=f"{app_name}:{name}",
            value=str(value)
        )
    except KeyError:
        raise ValueError("Application name not found in context")


def get_output(self: Construct, name: str) -> str:
    """Get a CloudFormation output value.
    
    Args:
        self: CDK construct scope
        name: Name of the output to retrieve
        
    Returns:
        Retrieved output value
        
    Raises:
        ValueError: If app name is not found in context
    """
    try:
        app_name = self.node.try_get_context("globals")["appName"]
        output = CfnOutput(
            self,
            f"{name}Input",
            value=Fn.import_value(f"{app_name}:{name}")
        )
        return output.value
    except KeyError:
        raise ValueError("Application name not found in context")


def create_service_role(
    self: Construct,
    role_name: str,
    principal: str,
    managed_policies: List[str] = [],
    inline_policies: List[dict] = [],
) -> iam.Role:
    """Create an IAM role for AWS services.
    
    Args:
        self: CDK construct scope
        role_name: Name of the role
        principal: AWS service principal (e.g., 'lambda', 'ecs-tasks')
        managed_policies: List of managed policy names to attach
        inline_policies: List of inline policy statements
        
    Returns:
        Created IAM role
        
    Raises:
        ValueError: If required context values are missing
    """
    try:
        context = self.node.try_get_context("globals")
        role = iam.Role(
            self,
            f"{context['prefix']}-{role_name}Role",
            assumed_by=iam.ServicePrincipal(f"{principal}.amazonaws.com"),
            description=f"{role_name} Role for {context['appName']}",
        )
        
        if managed_policies:
            add_managed_policies(role=role, policies=managed_policies)
            
        if inline_policies:
            add_inline_policies(self, role=role, policies=inline_policies)
            
        return role
    except KeyError as e:
        raise ValueError(f"Missing required context value: {str(e)}")


def add_managed_policies(role: iam.Role, policies: List[str]) -> None:
    """Add managed policies to an IAM role.
    
    Args:
        role: IAM role to modify
        policies: List of managed policy names to attach
    """
    for policy_name in policies:
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(policy_name)
        )


def add_inline_policies(
    self: Construct,
    role: iam.Role,
    policies: List[dict]
) -> None:
    """Add inline policies to an IAM role.
    
    Args:
        self: CDK construct scope
        role: IAM role to modify
        policies: List of policy statements in the format:
            [
                {
                    "actions": List[str],
                    "resources": List[str]
                }
            ]
            
    Raises:
        ValueError: If policy statement is missing required fields
    """
    try:
        role.attach_inline_policy(
            iam.Policy(
                self,
                f"ap-dev-{role.role_name.lower()}",
                statements=[
                    iam.PolicyStatement(
                        actions=p["actions"],
                        resources=p["resources"]
                    )
                    for p in policies
                ],
            )
        )
    except KeyError as e:
        raise ValueError(f"Invalid policy statement, missing field: {str(e)}")
