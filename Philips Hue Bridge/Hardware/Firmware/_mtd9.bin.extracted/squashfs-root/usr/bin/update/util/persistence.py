# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import json
import os


def unpack(keys: list, from_dict: dict):
    for key in keys:
        yield from_dict[key]


def remap_keys(keys: list, from_dict: dict, **kwargs) -> dict:
    def mapper():
        for mapping in keys:
            if isinstance(mapping, tuple):
                key, new = mapping
            else:
                key, new = mapping, mapping
            if key in from_dict:
                if field_mapper := kwargs.get(key):
                    yield new, field_mapper(from_dict[key])
                else:
                    yield new, from_dict[key]

    return dict(mapper())


class SchemaError(Exception):
    pass


class DataObject:
    def __init__(self, **kwargs):
        self.__dict__ = dict(kwargs)

    def __getattr__(self, key: str):
        return self.__dict__[key]

    def __getitem__(self, key: str):
        return self.__dict__[key]

    def __delitem__(self, key: str):
        try:
            del self.__dict__[key]
        except KeyError:
            pass

    def __contains__(self, key: str) -> bool:
        return key in self.__dict__

    def __str__(self):
        return f"{type(self).__name__}(fields={self.__dict__})"

    def get(self, key: str, default=None):
        return self.__dict__.get(key, default)

    def update(self, **kwargs) -> "DataObject":
        self.__dict__.update(kwargs)
        return self

    def complement(self, **kwargs) -> "DataObject":
        for k, v in kwargs.items():
            if k not in self.__dict__:
                self.__dict__[k] = v

    def pick(self, *args) -> dict:
        return {key: value for key, value in self.__dict__.items() if key in args}

    def remap(self, *args, **kwargs) -> dict:
        return remap_keys(args, self.__dict__, **kwargs)

    def delete(self, *args):
        for key in args:
            del self[key]

    def validate(self, schema: "DataObject") -> "DataObject":
        if not schema:
            raise SchemaError("schema can't be empty or None")
        own_keys = set(self.__dict__)
        schema_keys = set(schema.__dict__)
        missing_keys = schema_keys - own_keys
        extra_keys = own_keys - schema_keys
        if missing_keys:
            raise SchemaError(f"mandatory keys {missing_keys} missing")
        if extra_keys:
            raise SchemaError(f"extra keys {extra_keys} present")
        for k, v in schema.__dict__.items():
            if not isinstance(self.__dict__[k], v):
                raise SchemaError(f"field {k} is {type(self.__dict__[k]).__name__} but expected {v.__name__}")
        return self

    def store(self, path: str) -> "DataObject":
        with open(path, "w") as file:
            file.write(json.dumps(self.__dict__))
        return self

    @staticmethod
    def load(path: str, delete: bool = False, schema: "DataObject" = None) -> "DataObject":
        with open(path, "r") as file:
            fields = json.loads(file.read())
        if delete:
            os.remove(path)
        return DataObject(**fields).validate(schema) if schema else DataObject(**fields)
