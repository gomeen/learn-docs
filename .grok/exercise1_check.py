"""Correct reference solution for exercise 1."""
from typing import Protocol, Self, runtime_checkable


@runtime_checkable
class Serializable(Protocol):
    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> Self: ...


class User:
    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

    def to_dict(self) -> dict:
        return {"name": self.name, "age": self.age}

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(data["name"], data["age"])


class Product:
    def __init__(self, sku: str, price: float) -> None:
        self.sku = sku
        self.price = price

    def to_dict(self) -> dict:
        return {"sku": self.sku, "price": self.price}

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(data["sku"], data["price"])


def dump(obj: Serializable) -> dict:
    return obj.to_dict()


user = User("alice", 30)
product = Product("P-001", 9.9)

assert isinstance(user, Serializable)
assert isinstance(product, Serializable)

roundtrip_user = User.from_dict(user.to_dict())
roundtrip_product = Product.from_dict(product.to_dict())

assert roundtrip_user.name == "alice"
assert roundtrip_product.sku == "P-001"
assert dump(user) == {"name": "alice", "age": 30}

print("all checks passed")