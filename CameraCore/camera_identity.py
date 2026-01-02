from typing import Union
import ipaddress


# 子码
# rtsp://service:Schuler.2019@192.168.1.32:554/rtsp_tunnel?h26x=h264&line=1&inst=2
# 主码
# rtsp://service:Schuler.2019@192.168.1.32:554/rtsp_tunnel?h26x=h264&line=1&inst=0


class CameraIdentity:
    """
    相机身份
    """

    def __init__(self,
                 user: str,
                 password: str,
                 ip: str,
                 port: int,
                 inst: int = 2,
                 **kwargs
                 ):

        self.user = user  # 角色
        self.password = password  # 密码
        self.ip = ip  # 相机IP
        self.port = port  # 相机PORT
        self.inst = inst  # 2->子码流; 0->主码流

        self.address = ''           # ip:port
        self.serial_number = ''     # ip+port
        self.url = ''               # url
        self.generate_url()

        # 附加信息
        # line, location
        for k, v in kwargs.items():
            setattr(self, k, v)

    def set_attached_attribute(self, key, value):
        """
        设置附加信息
        :param key:
        :param value:
        :return:
        """
        setattr(self, key, value)

    def get_attached_attribute(self, key):
        """
        获取附加信息
        :param key:
        :return:
        """
        # return getattr(self, key)
        return self.__dict__.get(key)

    def generate_url(self):
        """
        生成 address and url
        :return:
        """
        self.address = '{ip}:{port}'.format(ip=self.ip, port=self.port)
        self.serial_number = self.generate_serial_number(ip=self.ip, port=self.port)
        self.url = r'rtsp://{user}:{password}@{address}/rtsp_tunnel?h26x=h264&line=1&inst={inst}'.format(
            user=self.user,
            password=self.password,
            address=self.address,
            inst=self.inst
        )
        return self.url, self.address, self.serial_number

    @staticmethod
    def generate_serial_number(ip: str, port: Union[int, str]) -> str:
        """
        生成 serial_number
        :param ip:
        :param port:
        :return:
        """
        serial_number = ''

        addr = ip.split('.')
        for a in addr:
            serial_number += CameraIdentity.pad_string(original_string=a)

        serial_number += str(port)

        return serial_number

    @staticmethod
    def pad_string(original_string, length=3, pad_char='0') -> str:
        """
        前补零
        :param original_string:
        :param length:
        :param pad_char:
        :return:
        """
        padding = pad_char * (length - len(original_string))
        return f"{padding}{original_string}"

    @staticmethod
    def decode_serial_number(serial_number: str) -> tuple:
        ip = ''
        for i in range(4):
            ip += '{}.'.format(int(serial_number[i * 3: (i + 1) * 3]))
        ip = ip[:-1]

        port = int(serial_number[12:])

        return ip, port

    @staticmethod
    def is_ip_valid(ip: str) -> bool:
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def __str__(self):
        """

        :return:
        """
        out = ""
        for k, v in self.__dict__.items():

            if k == "address" or k == "url":
                continue

            if isinstance(v, str):
                out += "\t{}[{:15s}]".format(k, v)
            else:
                out += "\t{}[{}]".format(k, v)
        return out


if __name__ == '__main__':
    print(CameraIdentity.decode_serial_number('19216800300340012'))
