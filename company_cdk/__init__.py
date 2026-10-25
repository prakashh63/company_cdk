"""company_cdk: reusable, secure AWS CDK constructs for serverless web apps."""

from .stacks import ServerlessWebAppStack

__version__ = "0.2.0"
__all__ = ["ServerlessWebAppStack", "__version__"]
