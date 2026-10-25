"""TaggingAspect: stamps standard company tags on every taggable resource."""

import jsii
from aws_cdk import IAspect, TagManager
from constructs import IConstruct


@jsii.implements(IAspect)
class TaggingAspect:
    """Visits every construct at synth time and sets the company tags."""

    def __init__(self, tags: dict[str, str]) -> None:
        self._tags = tags

    def visit(self, node: IConstruct) -> None:
        if TagManager.is_taggable(node):
            for key, value in self._tags.items():
                node.tags.set_tag(key, value)  # type: ignore[attr-defined]
