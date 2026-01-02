from pickle import dumps, loads
from base64 import b64encode, b64decode


class MySerializer:
    @staticmethod
    def serialize(obj) -> str:
        # 序列化，转为byte
        byte_obj = dumps(obj)
        # 使用base64转换byte为str
        str_obj = b64encode(byte_obj).decode()
        return str_obj

    @staticmethod
    def deserialize(string: str):
        # 字符串转为byte
        byte_string = b64decode(string)
        # 反序列化
        obj = loads(byte_string)
        return obj
