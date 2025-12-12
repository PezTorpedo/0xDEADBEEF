# pylint: disable=pointless-string-statement
class SchemaValidationError(Exception):
    def __init__(self, message):  # pylint: disable=useless-super-delegation
        super().__init__(message)


"""Validates the json object against a schema. This validation can be be used only with objects
   which don't have nested keys i.e. all keys are at same level. 

        Parameters:
            json_obj:     the json object to validate.
            schema:       the schema to validate against.

        Returns:
            Nothing

        Raises:
            SchemaValidationError if the json object does not have all the keys present in schema
"""


def validate_schema(json_obj, schema):
    expected_keys = set(schema)
    actual_keys = set(json_obj)
    missing_keys = expected_keys - actual_keys

    if missing_keys:
        raise SchemaValidationError(f"Missing keys from schema {missing_keys}")
