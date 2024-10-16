#!/usr/bin/env python3

import os
import secrets
from typing import Any, MutableMapping

from pydantic import BaseModel, ConfigDict, AnyUrl, Field, model_validator


class Git(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: AnyUrl
    revision: str


class Source(BaseModel):
    model_config = ConfigDict(frozen=True)

    git: Git


class ContainerImage(BaseModel):
    model_config = ConfigDict(frozen=True)

    image: str
    sha: str


class Component(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    container_image: ContainerImage = Field(alias="containerImage")
    source: Source

    @model_validator(mode='before')
    @classmethod
    def container_image_validator(cls, data: Any) -> Any:
        if not isinstance(data, MutableMapping):
            raise ValueError(f"{data} is not of mapping type")

        image, sha = data["containerImage"].split("@sha256:")
        data["containerImage"] = ContainerImage(image=image, sha=sha)
        return data


class Snapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    application: str
    components: list[Component]


def main() -> None:
    prefix = ""
    snapshot_str = os.environ.get("SNAPSHOT")
    pr_number = os.environ.get("PR_NUMBER")
    if pr_number:
        prefix = f"pr-{pr_number}-"

    if snapshot_str is None:
        raise RuntimeError("SNAPSHOT environment variable wasn't declared or empty")

    snapshot: Snapshot = Snapshot.model_validate_json(snapshot_str)
    ret = []
    for component in snapshot.components:
        component_name = os.environ.get('BONFIRE_COMPONENT_NAME') or component.name
        ret.extend((
            "--set-template-ref",
            f"{component_name}={component.source.git.revision}",
            "--set-parameter",
            f"{component_name}/IMAGE={component.container_image.image}",
            "--set-parameter",
            f"{component_name}/IMAGE_TAG={prefix}{component.source.git.revision[:7]}",
            "--set-parameter",
            f"{component_name}/DBM_IMAGE={component.container_image.image}",
            "--set-parameter",
            f"{component_name}/DBM_IMAGE_TAG={prefix}{component.source.git.revision[:7]}",
            "--set-parameter",
            f"{component_name}/DBM_INVOCATION={secrets.randbelow(100)}",
        ))
    print(" ".join(ret))


if __name__ == "__main__":
    main()
