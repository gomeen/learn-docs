from typing import Protocol, runtime_checkable

@runtime_checkable
class Serializable(Protocol):

  def to_dict(self, d: dict)=>dict:
    return d

  def from_dict(self, data:dict) => Self
    return self

class A:
  def to_dict(self, d: dict)=>dict:
    return d

  def from_dict(self, data:dict) => Self
    return self

assert isinstance(A(),Serializable)