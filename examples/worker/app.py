from pathlib import Path

import aws_cdk as cdk

from company_cdk import ServerlessWebAppStack
from company_cdk.configs import load_config

app = cdk.App()
config = load_config(Path(__file__).parent / "config.yaml")
ServerlessWebAppStack(app, "OrderWorkerStack", config=config)
app.synth()
