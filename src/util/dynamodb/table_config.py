from dataclasses import dataclass, asdict


@dataclass
class AttributeDefinition:
    AttributeName: str
    AttributeType: str

    def __post_init__(self):
        # Validate attribute type
        pass


@dataclass
class KeySchema:
    AttributeName: str
    KeyType: str

    def __post_init__(self):
        if self.KeyType not in ["HASH", "RANGE"]:
            raise Exception("DynamoDB table key schema key type must be "
                            "\"HASH\" or \"RANGE\"")


@dataclass
class TableConfig:
    AttributeDefinitions: list[AttributeDefinition]
    TableName: str
    KeySchema: list[KeySchema]

    def get_attr_def(self):
        return [asdict(item) for item in self.AttributeDefinitions]

    def get_key_schema(self):
        return [asdict(item) for item in self.KeySchema]
