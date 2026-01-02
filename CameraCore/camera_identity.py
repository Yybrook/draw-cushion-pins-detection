from MvImport.CameraParams_header import MV_CC_DEVICE_INFO
from typing import Optional


class CameraIdentity:
    """
    相机身份
    """
    def __init__(self,
                 st_device_info: Optional[MV_CC_DEVICE_INFO] = None,
                 device_index: Optional[int] = None,
                 uid: Optional[str] = None,
                 serial_number: Optional[str] = None,
                 current_ip: Optional[str] = None,
                 model_name: Optional[str] = None):

        self.st_device_info = st_device_info
        self.device_index: Optional[int] = device_index     # 相机序号
        self.uid: Optional[str] = uid                       # 相机用户自定义信息
        self.serial_number: Optional[str] = serial_number   # 相机序列号
        self.current_ip: Optional[str] = current_ip         # 相机IP
        self.model_name: Optional[str] = model_name         # 相机型号

    def __str__(self):
        """
        输出相机身份信息
        :return:
        """
        # return "\tUID[%s]\t序号[%d]\t序列号[%s]\tIP[%s]\t型号[%s]" % (self.uid, self.device_index, self.serial_number, self.current_ip, self.model_name)
        return "UID[{}]\t序号[{}]\t序列号[{}]\tIP[{}]\t型号[{}]".format(self.uid, self.device_index, self.serial_number, self.current_ip, self.model_name)
