from __future__ import annotations

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


class _UniqueKeySafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[object, object]:
        explicit: set[object] = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                key: object = "<<"
            else:
                key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in explicit
                explicit.add(key)
            except TypeError as exc:
                raise ConstructorError(None, None, "unhashable mapping key", key_node.start_mark) from exc
            if duplicate:
                raise ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
        return super().construct_mapping(node, deep=deep)


def dump_yaml(data: dict[str, object]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def load_yaml(text: str) -> object:
    # The loader subclasses SafeLoader and only adds duplicate-key rejection, so no arbitrary objects are built.
    return yaml.load(text, Loader=_UniqueKeySafeLoader)  # noqa: S506
