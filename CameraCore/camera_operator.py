from typing import Dict, Union
from ctypes import memset, cast, POINTER, CFUNCTYPE, create_string_buffer, c_ubyte, c_void_p, byref, sizeof, c_bool

from MvImport.CameraParams_const import MV_GIGE_DEVICE, MV_ACCESS_Exclusive
from MvImport.MvCameraControl_class import MvCamera
from MvImport.CameraParams_header import (MV_CC_DEVICE_INFO_LIST, MV_CC_DEVICE_INFO, MV_FRAME_OUT_INFO_EX,
                                          MVCC_INTVALUE_EX, MVCC_FLOATVALUE, MVCC_ENUMVALUE, MVCC_STRINGVALUE,
                                          MV_TRANSMISSION_TYPE, MV_GIGE_TRANSTYPE_MULTICAST)
from MvImport.MvErrorDefine_const import MV_OK

from CameraCore.camera_err_header import *


"""
主动取流：
0. SDK提供主动获取图像的接口，用户可以在开启取流后直接调用此接口获取图像，也可以使用异步方式（线程、定时器等）获取图像。
1. 主动获取图像有两种方式（两种方式不能同时使用）：
    方式一：调用 MV_CC_StartGrabbing() 开始采集，
           需要自己开启一个buffer，
           然后在应用层循环调用 MV_CC_GetOneFrameTimeout() 获取指定像素格式的帧数据，
           获取帧数据时上层应用程序需要根据帧率控制好调用该接口的频率
    方式二：调用 MV_CC_StartGrabbing() 开始采集，
           然后在应用层调用 MV_CC_GetImageBuffer() 获取指定像素格式的帧数据，
           然后调用 MV_CC_FreeImageBuffer() 释放buffer，
           获取帧数据时上层应用程序需要根据帧率控制好调用该接口的频率
2. 主动取图方式使用的场景：
    主动取图方式需要先调用 MV_CC_StartGrabbing() 启动图像采集。
    上层应用程序需要根据帧率，控制好调用主动取图接口的频率。
    两种主动取图方式都支持设置超时时间，SDK内部等待直到有数据时返回，可以增加取流平稳性，适合用于对平稳性要求较高的场合
3. 两种主动取图方式的区别：
    a、 MV_CC_GetImageBuffer() 需要与 MV_CC_FreeImageBuffer() 配套使用，
        当处理完取到的数据后，需要用 MV_CC_FreeImageBuffer() 接口将pstFrame内的数据指针权限进行释放
    b、 MV_CC_GetImageBuffer() 与 MV_CC_GetOneFrameTimeout() 相比，有着更高的效率。
        且其取流缓存的分配是由sdk内部自动分配的，而 MV_CC_GetOneFrameTimeout() 接口是需要客户自行分配
4. 注意事项：
    a、两种主动取图方式不能同时使用，且不能与后面的回调取图方式同时使用，三种取图方式只能使用其中一种。
    b、pData返回的是一个地址指针，建议将pData里面的数据copy出来另建线程使用。

流程：
1. （可选）枚举设备                     MV_CC_EnumDevices()        
2. （可选）获取设备信息                  通过nTLayerType在结构 MV_CC_DEVICE_INFO() 中获取设备信息
3. （可选）判断设备是否可达               MV_CC_IsDeviceAccessible()
4.  创建设备句柄                        MV_CC_CreateHandle()
5.  打开设备                           MV_CC_OpenDevice()
6. （可选）获取/设置相机不同类型的参数      MV_CC_GetIntValue() / MV_CC_SetIntValue()        获取/设置Int类型节点值
                                      MV_CC_GetFloatValue() / MV_CC_SetFloatValue()    获取/设置Float类型节点值
                                      MV_CC_GetEnumValue() / MV_CC_SetEnumValue()      获取/设置Enum类型节点值
                                      MV_CC_GetBoolValue() / MV_CC_SetBoolValue()      获取/设置Bool类型节点值
                                      MV_CC_GetStringValue() / MV_CC_SetStringValue()  获取/设置String类型节点值
                                      MV_CC_SetCommandValue()                          设置Command类型节点值 
    6.1 探测网络最佳包大小(只对GigE相机有效)     nPacketSize = MV_CC_GetOptimalPacketSize()
                                            MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)
7. 图像采集
    7.1 设置图像缓存节点个数               MV_CC_SetImageNodeNum()    获取的图像数超过这个设定值，最早的图像数据会被自动丢弃
    7.2 开始取流                         MV_CC_StartGrabbing()
    7.3 获取图片数据                      MV_CC_GetOneFrameTimeout() / MV_CC_GetImageBuffer()   在应用程序层中重复调用
    7.4 转换图像的像素格式                 MV_CC_ConvertPixelType()   对于原始图像数据
    7.5 （可选）转换、保存JPEG或BMP格式图片  MV_CC_SaveImage()   
    7.6 释放图片缓存                      MV_CC_FreeOneFrameTimeout() 在应用程序层中重复调用
8. 停止采集                              MV_CC_StopGrabbing() 
9. 关闭设备                              MV_CC_CloseDevice()
10. 销毁句柄并释放资源                      MV_CC_DestroyHandle()
"""


class CameraOperator(MvCamera):

    def __init__(self):
        super().__init__()

    @staticmethod
    def enum_devices(device_type: int = MV_GIGE_DEVICE, enum_err_callback=None, enum_none_callback=None, enum_successful_callback=None) -> int:
        """
        枚举设备
        :param device_type:             相机接口形式, 默认GIGE
                                            MV_UNKNOW_DEVICE = 0x00000000       # ch:未知设备类型，保留意义 | en:Unknown Device Type, Reserved
                                            MV_GIGE_DEVICE = 0x00000001         # ch:GigE设备 | en:GigE Device
                                            MV_1394_DEVICE = 0x00000002         # ch:1394-a/b 设备 | en:1394-a/b Device
                                            MV_USB_DEVICE = 0x00000004          # ch:USB3.0 设备 | en:USB3.0 Device
                                            MV_CAMERALINK_DEVICE = 0x00000008   # ch:CameraLink设备 | en:CameraLink Device
        :param enum_err_callback:       枚举错误回调函数
        :param enum_none_callback:      枚举为空回调函数
        :param enum_successful_callback:   枚举成功回调函数
        :return:                        字典
        """

        # 设备列表结构体 -> {nDeviceNum(在线设备数量), pDeviceInfo(设备信息结构体)}
        '''
        _MV_CC_DEVICE_INFO_LIST_    ->  设备信息列表结构体
            [unsigned int           nDeviceNum                          [OUT]   在线设备数量,
            MV_CC_DEVICE_INFO*      pDeviceInfo [MV_MAX_DEVICE_NUM]     [OUT]   支持最多256个设备]
            其中:
                _MV_CC_DEVICE_INFO  ->  设备信息结构体
                unsigned short  nMajorVer       [OUT]   主要版本 
                unsigned short  nMinorVer       [OUT]   次要版本 
                unsigned int    nMacAddrHigh    [OUT]   高MAC地址 
                unsigned int    nMacAddrLow     [OUT]   低MAC地址 
                unsigned int    nTLayerType     [OUT]   设备传输层协议类型，e.g. MV_GIGE_DEVICE 
                unsigned int    nReserved [4]           预留 
                SpecialInfo 结构体 union       { MV_GIGE_DEVICE_INFO   stGigEInfo [OUT] GigE设备信息 
                                                MV_USB3_DEVICE_INFO   stUsb3VInfo [OUT] USB设备信息
                                                MV_CamL_DEV_INFO   stCamLInfo [OUT] CameraLink设备信息 }
                其中: SpecialInfo -> 
                    _MV_GIGE_DEVICE_INFO_ -> GigE设备信息结构体 
                        unsigned int    nIpCfgOption                    [OUT]   IP配置选项 
                        unsigned int    nIpCfgCurrent                   [OUT]   当前IP配置 
                        unsigned int    nCurrentIp                      [OUT]   当前IP地址 
                        unsigned int    nCurrentSubNetMask              [OUT]   当前子网掩码 
                        unsigned int    nDefultGateWay                  [OUT]   当前网关 
                        unsigned char   chManufacturerName [32]         [OUT]   制造商名称 
                        unsigned char   chModelName [32]                [OUT]   型号名称 
                        unsigned char   chDeviceVersion [32]            [OUT]   设备版本 
                        unsigned char   chManufacturerSpecificInfo [48] [OUT]   制造商的具体信息 
                        unsigned char   chSerialNumber [16]             [OUT]   序列号 
                        unsigned char   chUserDefinedName [16]          [OUT]   用户自定义名称 
                        unsigned int    nNetExport                      [OUT]   网口IP地址 
                        unsigned int    nReserved [4]                           预留

        '''
        device_info_list = MV_CC_DEVICE_INFO_LIST()
        # 枚举设备
        '''
        MV_CC_EnumDevices   ->  枚举设备
            参数： nTLayerType  ->  枚举传输层，按位表示，支持复选。
                    协议类型：
                        MV_UNKNOW_DEVICE        0x00000000      未知设备类型
                        MV_GIGE_DEVICE          0x00000001      GigE设备
                        MV_1394_DEVICE          0x00000002      1394-a/b设备
                        MV_USB_DEVICE           0x00000004      USB3.0设备
                        MV_CAMERALINK_DEVICE    0x00000008      CameraLink设备
                  deviceList    ->  设备列表结构体
            返回：成功，返回MV_OK；失败，返回错误码
            备注：设备列表的内存是在SDK内部分配的，多线程调用该接口时会进行设备列表内存的释放和申请，建议尽量避免多线程枚举操作。
        '''
        ret = CameraOperator.MV_CC_EnumDevices(device_type, device_info_list)
        if ret != MV_OK:
            # 枚举设备失败
            err_str: str = CameraOperator.err_code_map(err_code=ret)
            if enum_err_callback is not None:
                enum_err_callback(err_code=ret, err_str=err_str)
        else:
            if device_info_list.nDeviceNum == 0:  # nDeviceNum -> 在线设备数量
                # 没有找到相机
                ret = CAMERA_ENUM_NONE
                err_str: str = CameraOperator.err_code_map(err_code=ret)
                if enum_none_callback is not None:
                    enum_none_callback(err_code=ret, err_str=err_str)
            else:
                # 找到相机
                if enum_successful_callback is not None:
                    enum_successful_callback(device_info_list=device_info_list, device_num=device_info_list.nDeviceNum)
        return ret

    @staticmethod
    def get_st_device_info(device_info_list: MV_CC_DEVICE_INFO_LIST, device_index: int) -> MV_CC_DEVICE_INFO:
        """
        获得相机信息
        :param device_info_list:                    设备列表结构体     ->  MV_CC_DEVICE_INFO_LIST()
        :param device_index:                        设备列表结构体中序号，从0开始，
        :return:
        """
        # 开辟空间
        st_device_info: MV_CC_DEVICE_INFO = cast(device_info_list.pDeviceInfo[device_index], POINTER(MV_CC_DEVICE_INFO)).contents
        return st_device_info

    @staticmethod
    def decode_device_info(st_device_info: MV_CC_DEVICE_INFO, device_index: int, get_device_info_successful_callback=None) -> Dict:
        """
        获得相机信息
        :param st_device_info:                      设备列表结构体     ->  MV_CC_DEVICE_INFO_LIST()
        :param device_index:                        设备列表结构体中序号，从0开始，
        :param get_device_info_successful_callback:
        :return:
        """
        # 设备信息字典
        device_info_dict = dict()
        # 是GIGI设备
        if st_device_info.nTLayerType == MV_GIGE_DEVICE:
            # ['枚举序号', '相机IP', '自定义信息', '序列号', '相机型号', '传输类型', '制造商']
            # 1. 枚举序号
            device_info_dict["DeviceIndex"] = device_index
            # 2. chUserDefinedName 自定义信息
            uid = ""
            for per in st_device_info.SpecialInfo.stGigEInfo.chUserDefinedName:
                # 用于取消字符串结尾乱码
                if per == 0X00:
                    break
                uid = uid + chr(per)
            device_info_dict["Uid"] = uid
            # 3. chSerialNumber 序列号
            serial_number = ""
            for per in st_device_info.SpecialInfo.stGigEInfo.chSerialNumber:
                # 用于取消字符串结尾乱码
                if per == 0X00:
                    break
                serial_number = serial_number + chr(per)
            device_info_dict["SerialNumber"] = serial_number
            # 4. nCurrentIp  当前IP地址
            nip1_1 = ((st_device_info.SpecialInfo.stGigEInfo.nCurrentIp & 0xff000000) >> 24)
            nip1_2 = ((st_device_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x00ff0000) >> 16)
            nip1_3 = ((st_device_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x0000ff00) >> 8)
            nip1_4 = (st_device_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x000000ff)
            current_ip = '%d.%d.%d.%d' % (nip1_1, nip1_2, nip1_3, nip1_4)
            device_info_dict["CurrentIp"] = current_ip
            # 5. chModelName 型号名称
            model_name = ""
            for per in st_device_info.SpecialInfo.stGigEInfo.chModelName:
                # 用于取消字符串结尾乱码
                if per == 0X00:
                    break
                model_name = model_name + chr(per)
            device_info_dict["ModelName"] = model_name

        if get_device_info_successful_callback is not None:
            get_device_info_successful_callback(st_device_info=st_device_info, device_info_dict=device_info_dict)

        return device_info_dict

    @staticmethod
    def is_device_accessible(st_device_info, access_mode=MV_ACCESS_Exclusive, device_is_accessible_callback=None, device_is_inaccessible_callback=None) -> bool:
        """
        判断设备是否可达
        :param st_device_info: 
        :param access_mode: 
        :param device_is_accessible_callback: 
        :param device_is_inaccessible_callback: 
        :return: 
        """
        '''
        MV_CC_IsDeviceAccessible -> 设备是否可达 
        参数：nAccessMode[IN] -> 访问权限     * 不可用
                  MV_ACCESS_Exclusive                     1       独占权限，其他APP只允许读CCP寄存器
                  MV_ACCESS_ExclusiveWithSwitch           2*      可以从5模式下抢占权限，然后以独占权限打开
                  MV_ACCESS_Control                       3       控制权限，其他APP允许读所有寄存器
                  MV_ACCESS_ControlWithSwitch             4*      可以从5的模式下抢占权限，然后以控制权限打开
                  MV_ACCESS_ControlSwitchEnable           5*      以可被抢占的控制权限打开
                  MV_ACCESS_ControlSwitchEnableWithKey    6*      可以从5的模式下抢占权限，然后以可被抢占的控制权限打开
                  MV_ACCESS_Monitor                       7       读模式打开设备，适用于控制权限下         
        返回: 可达，返回true；不可达，返回false 
        备注: 读取设备CCP寄存器的值，判断当前状态是否具有某种访问权限。 
              如果设备不支持MV_ACCESS_ExclusiveWithSwitch、
                          MV_ACCESS_ControlWithSwitch、
                          MV_ACCESS_ControlSwitchEnableWithKey这三种模式，
                          接口返回false。
              目前设备不支持这3种抢占模式，国际上主流的厂商的设备也都暂不支持这3种模式。 
        '''
        ret = CameraOperator.MV_CC_IsDeviceAccessible(stDevInfo=st_device_info, nAccessMode=access_mode)
        if not ret:
            if device_is_inaccessible_callback is not None:
                device_is_inaccessible_callback(st_device_info=st_device_info)
            return False
        else:
            if device_is_accessible_callback is not None:
                device_is_accessible_callback(st_device_info=st_device_info)
            return True

    def create_handle(self, st_device_info: MV_CC_DEVICE_INFO,
                      create_handle_successful_callback=None, create_handle_failed_callback=None) -> int:
        """
        选择设备并创建句柄
        :param st_device_info:                  GigE设备信息结构体，从get_device_info获得  ->  MV_CC_DEVICE_INFO
        :param create_handle_successful_callback:  创建句柄成功回调函数
        :param create_handle_failed_callback:   创建句柄失败回调函数
        :return:                                成功，返回MV_OK；失败，返回错误码
        """
        '''
        MV_CC_CreateHandle  ->      创建设备句柄
            参数              -> pstDevInfo [IN] 设备信息结构体
            返回              -> 成功，返回MV_OK；失败，返回错误码
            备注              -> 根据输入的设备信息，创建库内部必须的资源和初始化内部模块。
                                 通过该接口创建句柄，调用SDK接口，会默认生成SDK日志文件，
                                 如果不需要生成日志文件，可以通过 MV_CC_CreateHandleWithoutLog() 创建句柄。
        '''
        # 创建句柄
        ret = self.MV_CC_CreateHandle(st_device_info)
        # 创建句柄失败
        if ret != MV_OK:
            # 销毁句柄
            self.MV_CC_DestroyHandle()
            if create_handle_failed_callback is not None:
                create_handle_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
        else:
            if create_handle_successful_callback is not None:
                create_handle_successful_callback()
        return ret

    def destroy_handle(self, destroy_handle_successful_callback=None, destroy_handle_failed_callback=None) -> int:
        """
        销毁句柄
        :param destroy_handle_successful_callback:     销毁句柄成功的回调函数
        :param destroy_handle_failed_callback:      销毁句柄失败的回调函数
        :return:                                    成功，返回MV_OK；失败，返回错误码
        """
        '''
        MV_CC_DestroyHandle     ->  销毁设备句柄
        返回                      ->  成功，返回MV_OK；失败，返回错误码
        '''
        ret = self.MV_CC_DestroyHandle()
        if ret != MV_OK:
            if destroy_handle_failed_callback is not None:
                destroy_handle_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
        else:
            if destroy_handle_successful_callback is not None:
                destroy_handle_successful_callback()
        return ret

    def open_device(self, access_mode=MV_ACCESS_Exclusive, open_device_successful_callback=None, open_device_failed_callback=None) -> int:
        """
        打开设备
        :param access_mode:                     访问权限
        :param open_device_successful_callback:    打开设备成功的回调函数
        :param open_device_failed_callback:     打开设备失败的回调函数
        :return:                                成功，返回MV_OK；失败，返回错误码
        :return:
        """
        '''
        MV_CC_OpenDevice        ->  打开设备
            参数：   nAccessMode[IN]     ->      访问权限                  * 不可用
                        MV_ACCESS_Exclusive                     1       独占权限，其他APP只允许读CCP寄存器
                        MV_ACCESS_ExclusiveWithSwitch           2*      可以从5模式下抢占权限，然后以独占权限打开
                        MV_ACCESS_Control                       3       控制权限，其他APP允许读所有寄存器
                        MV_ACCESS_ControlWithSwitch             4*      可以从5的模式下抢占权限，然后以控制权限打开
                        MV_ACCESS_ControlSwitchEnable           5*      以可被抢占的控制权限打开
                        MV_ACCESS_ControlSwitchEnableWithKey    6*      可以从5的模式下抢占权限，然后以可被抢占的控制权限打开
                        MV_ACCESS_Monitor                       7       读模式打开设备，适用于控制权限下
                    nSwitchoverKey[IN] -> 切换访问权限时的密钥
            返回：   成功，返回MV_OK；失败，返回错误码
            备注：   根据设置的设备参数，找到对应的设备，连接设备。
                      调用接口时可不传入nAccessMode和nSwitchoverKey，此时默认设备访问模式为独占权限。
                      ！目前设备暂不支持   MV_ACCESS_ExclusiveWithSwitch            ->  2
                                        MV_ACCESS_ControlWithSwitch             ->  4
                                        MV_ACCESS_ControlSwitchEnable           ->  5
                                        MV_ACCESS_ControlSwitchEnableWithKey    ->  6   这四种抢占模式。
                      对于U3V设备，nAccessMode、nSwitchoverKey这两个参数无效。
        '''
        ret = self.MV_CC_OpenDevice(access_mode, 0)
        if ret != MV_OK:
            if open_device_failed_callback is not None:
                # 销毁句柄
                self.MV_CC_DestroyHandle()
                open_device_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
        else:
            if open_device_successful_callback is not None:
                open_device_successful_callback()
        return ret

    def close_device(self, close_device_successful_callback=None, close_device_failed_callback=None) -> int:
        """
        关闭设备
        :param close_device_successful_callback:   关闭设备成功的回调函数
        :param close_device_failed_callback:    关闭设备失败的回调函数
        :return:                                成功，返回MV_OK；失败，返回错误码
        """
        '''
        MV_CC_CloseDevice   ->  关闭设备
            返回              ->  成功，返回MV_OK；失败，返回错误码
            备注              ->  通过 MV_CC_OpenDevice() 连接设备后，可以通过该接口断开设备连接，释放资源
        '''
        ret = self.MV_CC_CloseDevice()
        if ret != MV_OK:
            if close_device_failed_callback is not None:
                close_device_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
        else:
            if close_device_successful_callback is not None:
                close_device_successful_callback()
        return ret

    def set_multicast_TransmissionType(self, ip: Union[str, list] = "239.192.1.1", port: int = 1042,
                                       set_multicast_successful_callback=None,
                                       set_multicast_failed_callback=None) -> int:
        """
        设置组播模式
        :param ip:          字符串类型 -> "239.192.1.1"  列表类型 -> ["239", "192", "1", "1"]
        :param port:
        :param set_multicast_successful_callback:
        :param set_multicast_failed_callback:
        :return:
        """
        if isinstance(ip, str):
            ip_list = ip.split('.')
        else:
            ip_list = ip

        dest_ip = (int(ip_list[0]) << 24) | (int(ip_list[1]) << 16) | (int(ip_list[2]) << 8) | int(ip_list[3])

        transmission_type = MV_TRANSMISSION_TYPE()
        memset(byref(transmission_type), 0, sizeof(MV_TRANSMISSION_TYPE))

        transmission_type.enTransmissionType = MV_GIGE_TRANSTYPE_MULTICAST
        transmission_type.nDestIp = dest_ip
        transmission_type.nDestPort = port

        ret = self.MV_GIGE_SetTransmissionType(transmission_type)
        if ret == MV_OK:
            if set_multicast_successful_callback is not None:
                set_multicast_successful_callback()
        else:
            if set_multicast_failed_callback is not None:
                set_multicast_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
        return ret

    def start_grabbing(self, start_grabbing_successful_callback=None, start_grabbing_failed_callback=None) -> int:
        """
        开启取流
        :param start_grabbing_successful_callback:     开启取流成功的回调函数
        :param start_grabbing_failed_callback:      开启取流失败的回调函数
        :return:                                    成功，返回MV_OK；失败，返回错误码
        """
        '''
        MV_CC_StartGrabbing     ->  开启取流
            返回                  ->  成功，返回MV_OK；失败，返回错误码
            备注                  ->  该接口不支持CameraLink设备。
        '''
        ret = self.MV_CC_StartGrabbing()
        if ret != MV_OK:
            if start_grabbing_failed_callback is not None:
                # 关闭相机
                self.MV_CC_CloseDevice()
                # 销毁句柄
                self.MV_CC_DestroyHandle()
                start_grabbing_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
        else:
            if start_grabbing_successful_callback is not None:
                start_grabbing_successful_callback()
        return ret

    def stop_grabbing(self, stop_grabbing_successful_callback=None, stop_grabbing_failed_callback=None) -> int:
        """
        停止取流
        :param stop_grabbing_successful_callback:  停止取流成功的回调函数
        :param stop_grabbing_failed_callback:   停止取流失败的回调函数
        :return:                                成功，返回MV_OK；失败，返回错误码
        """
        '''
        MV_CC_StopGrabbing  ->  停止取流
            返回              ->  成功，返回MV_OK；失败，返回错误码
            备注              ->  该接口不支持CameraLink设备。
        '''
        ret = self.MV_CC_StopGrabbing()
        if ret != MV_OK:
            if stop_grabbing_failed_callback is not None:
                stop_grabbing_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
        else:
            if stop_grabbing_successful_callback is not None:
                stop_grabbing_successful_callback()
        return ret

    def register_image_callback(self, image_callback, user_data,
                                register_image_successful_callback=None, register_image_failed_callback=None) -> int:
        """
        注册抓图回调
        :param image_callback:                        调用的回调函数
        :param user_data:                           用户自定义变量指针，int类型 或 None
        :param register_image_successful_callback:     注册抓图回调成功的回调函数
        :param register_image_failed_callback:      注册抓图回调失败的回调函数
        :return:
        """
        '''
        MV_CC_RegisterImageCallBackEx()     ->  注册图像数据回调 
            MV_CAMCTRL_API  int __stdcall   MV_CC_RegisterImageCallBackEx( 
                void *  handle,  
                void(__stdcall *cbOutput)(  unsigned char *pData, 
                                            MV_FRAME_OUT_INFO_EX *pstFrameInfo, 
                                            void *pUser)  ,  
                void *  pUser)   
            参数
                handle      [IN]    设备句柄  
                cbOutput    [IN]    回调函数指针  
                pUser       [IN]    用户自定义变量
            返回  成功，返回MV_OK；失败，返回错误码 
            备注 
                通过该接口可以设置图像数据回调函数，在 MV_CC_CreateHandle() 之后即可调用。 
                图像数据采集有两种方式，两种方式不能复用：
                    1. 调用 MV_CC_RegisterImageCallBackEx() 设置图像数据回调函数，
                        然后调用 MV_CC_StartGrabbing() 开始采集，采集的图像数据在设置的回调函数中返回。 
                    2. 调用 MV_CC_StartGrabbing() 开始采集，
                        然后在应用层循环调用 MV_CC_GetOneFrameTimeout() 获取指定像素格式的帧数据，
                        获取帧数据时上层应用程序需要根据帧率控制好调用该接口的频率。 
        '''

        p_data = POINTER(c_ubyte)                                   # 创建POINTER指针，指向图片数据
        p_st_frame_out_info = POINTER(MV_FRAME_OUT_INFO_EX)         # 创建POINTER指针

        if user_data is None:
            p_user = user_data
        elif isinstance(user_data, int):
            p_user = user_data
        elif isinstance(user_data, str):
            str_user = create_string_buffer(user_data.encode('utf-8'))
            p_user = cast(str_user, c_void_p)
        else:
            p_user = None

        # 创建一个c函数类型的对象
        c_image_callback = CFUNCTYPE(None, p_data, p_st_frame_out_info, c_void_p)
        '''第一个参数是python回调函数的返回值，如果没有就是None；第二个及其以后的就是python回调函数的参数类型'''
        # 根据c函数类型的对象生成python回调函数
        py_image_callback = c_image_callback(image_callback)

        ret = self.MV_CC_RegisterImageCallBackEx(py_image_callback, p_user)
        if ret != MV_OK:
            if register_image_failed_callback is not None:
                # 销毁句柄
                self.MV_CC_DestroyHandle()
                register_image_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
        else:
            if register_image_successful_callback is not None:
                register_image_successful_callback()
        return ret

    def get_device_parameter(self, param_type: str, node_name: str,
                             get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得相机各类型的节点值
        :param param_type:  获取的节点值类型，以字符的形式给出
                                int:        "int"
                                float:      "float"
                                enum:       "enum"      参考于客户端中该选项的 Enum Entry Value 值即可
                                bool:       "bool"      对应 0 为关，1 为开
                                string:     "string"    输入值为数字或者英文字符，不能为汉字
        :param node_name:   节点名称
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:            字典 {'ret': MV_OK/错误代码, }
        """

        # 获得int类型的参数
        if param_type == 'int':
            """
            MVCC_INTVALUE_EX 结构体 -> Int类型值
                int64_t  nCurValue [OUT]    当前值 
                int64_t  nMax [OUT]         最大值 
                int64_t  nMin [OUT]         最小值 
                int64_t  nInc [OUT] Inc     步径
                unsigned int  nReserved [16] 预留
            """
            # 定义结构体
            st_int_value = MVCC_INTVALUE_EX()       # windows
            # st_int_value = MVCC_INTVALUE()        # linux
            # 开辟空间
            # 其中：byref(buffer) -> 返回指针
            #      menset(buffer:为指针或是数组, c：是赋给buffer的值, count：是buffer的长度)
            memset(byref(st_int_value), 0, sizeof(MVCC_INTVALUE_EX))    # windows
            # memset(byref(st_int_value), 0, sizeof(MVCC_INTVALUE))         # linux
            """
            MV_CC_GetIntValueEx -> 获取Integer属性值
                参数： strKey [IN] 属性键值，如获取宽度信息则为"Width"  
                      pstIntValue [IN][OUT] 返回给调用者有关设备属性结构体指针  
                返回： 成功，返回MV_OK；失败，返回错误码 
                备注： 连接设备之后调用该接口可以获取int类型的指定节点的值
            """
            ret = self.MV_CC_GetIntValue(node_name, st_int_value)
            # ret = self.MV_CC_GetIntValueEX(node_name, st_int_value)   # 在linux中,没有相关函数
            if ret == MV_OK:
                if get_value_successful_callback is not None:
                    get_value_successful_callback()
                value_dict = dict(ret=ret, nCurValue=st_int_value.nCurValue,  nMax=st_int_value.nMax, nMin=st_int_value.nMin, nInc=st_int_value.nInc)
            else:
                if get_value_failed_callback is not None:
                    get_value_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
                value_dict = dict(ret=ret)

            return value_dict

        # 获得浮点类型的参数
        elif param_type == 'float':
            """
            _MVCC_FLOATVALUE_T 结构体 -> Float类型值
                float  fCurValue [OUT] 当前值 
                float  fMax [OUT]       最大值 
                float  fMin [OUT]       最小值
                unsigned int  nReserved [4] 预留
            """
            st_float_value = MVCC_FLOATVALUE()
            memset(byref(st_float_value), 0, sizeof(MVCC_FLOATVALUE))
            ret = self.MV_CC_GetFloatValue(node_name, st_float_value)
            if ret == MV_OK:
                if get_value_successful_callback is not None:
                    get_value_successful_callback()
                value_dict = dict(ret=ret, fCurValue=st_float_value.fCurValue, fMax=st_float_value.fMax, fMin=st_float_value.fMin)
            else:
                if get_value_failed_callback is not None:
                    get_value_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
                value_dict = dict(ret=ret)
            return value_dict

        # 获得枚举类型参数
        elif param_type == 'enum':
            """
            _MVCC_ENUMVALUE_T 结构体 -> 枚举类型值 
                    unsigned int  nCurValue [OUT] 当前值 
                    unsigned int  nSupportedNum [OUT] 数据的有效数据个数 
                    unsigned int  nSupportValue [MV_MAX_XML_SYMBOLIC_NUM] [OUT] 支持的枚举值 
                    unsigned int  nReserved [4] 预留 
            """
            st_enum_value = MVCC_ENUMVALUE()
            memset(byref(st_enum_value), 0, sizeof(MVCC_ENUMVALUE))
            ret = self.MV_CC_GetEnumValue(node_name, st_enum_value)
            if ret == MV_OK:
                if get_value_successful_callback is not None:
                    get_value_successful_callback()
                value_dict = dict(ret=ret,
                                  nCurValue=st_enum_value.nCurValue,
                                  nSupportedNum=st_enum_value.nSupportedNum,
                                  nSupportValue=st_enum_value.nSupportValue)
            else:
                if get_value_failed_callback is not None:
                    get_value_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
                value_dict = dict(ret=ret)
            return value_dict

        # 获得bool类型参数
        elif param_type == 'bool':
            st_bool = c_bool(False)
            ret = self.MV_CC_GetBoolValue(node_name, st_bool)
            if ret == MV_OK:
                if get_value_successful_callback is not None:
                    get_value_successful_callback()
                value_dict = dict(ret=ret, bCurValue=st_bool.value)
            else:
                if get_value_failed_callback is not None:
                    get_value_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
                value_dict = dict(ret=ret)
            return value_dict

        # 获得String类型节点值
        elif param_type == 'string':
            """
            _MVCC_STRINGVALUE_T 结构体 -> String类型值 
                char  chCurValue [256] [OUT] 当前值 
                int64_t  nMaxLength [OUT] 最大长度 
                unsigned int  nReserved [2] 预留 
            """
            st_string_value = MVCC_STRINGVALUE()
            memset(byref(st_string_value), 0, sizeof(MVCC_STRINGVALUE))
            ret = self.MV_CC_GetStringValue(node_name, st_string_value)
            if ret == MV_OK:
                if get_value_successful_callback is not None:
                    get_value_successful_callback()
                value_dict = dict(ret=ret, chCurValue=st_string_value.chCurValue, nMaxLength=st_string_value.nMaxLength)
            else:
                if get_value_failed_callback is not None:
                    get_value_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
                value_dict = dict(ret=ret)
            return value_dict

        # 其他，参数类型非法
        else:
            ret = PARAMETER_TYPE_ILLEGAL
            if get_value_failed_callback is not None:
                get_value_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
            value_dict = dict(ret=ret)
            return value_dict

    def set_device_parameter(self, param_type: str, node_name: str, node_value: Union[int, float, str, bool, None],
                             set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置各种类型节点参数
        :param param_type:      需要设置的节点值得类型，以字符的形式给出
                                    int:        "int"
                                    float:      "float"
                                    enum:       "enum"      参考于客户端中该选项的 Enum Entry Value 值即可
                                    bool:       "bool"      对应 0 为关，1 为开
                                    string:     "string"    输入值为数字或者英文字符，不能为汉字
                                    command:    "command"   命令
        :param node_name:       需要设置的节点名
        :param node_value:      设置给节点的值
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        # 设置int类型的参数
        if param_type == 'int':
            if isinstance(node_value, int):
                ret = self.MV_CC_SetIntValueEx(node_name, node_value)       # windows
                # ret = self.MV_CC_SetIntValue(node_name, node_value)       # linux
            else:
                ret = PARAMETER_VALUE_TYPE_ILLEGAL

        # 设置float类型的参数
        elif param_type == 'float':
            if isinstance(node_value, float):
                ret = self.MV_CC_SetFloatValue(node_name, node_value)
            else:
                ret = PARAMETER_VALUE_TYPE_ILLEGAL

        # 设置enum类型的参数
        elif param_type == 'enum':
            if isinstance(node_value, str):
                ret = self.MV_CC_SetEnumValueByString(node_name, node_value)
            elif isinstance(node_value, int):
                ret = self.MV_CC_SetEnumValue(node_name, node_value)
            else:
                ret = PARAMETER_VALUE_TYPE_ILLEGAL

        # 设置bool类型的参数
        elif param_type == 'bool':
            if isinstance(node_value, bool):
                ret = self.MV_CC_SetBoolValue(node_name, node_value)
            else:
                ret = PARAMETER_VALUE_TYPE_ILLEGAL

        # 设置string类型的参数
        elif param_type == 'string':
            if isinstance(node_value, str):
                ret = self.MV_CC_SetStringValue(node_name, node_value)
            else:
                ret = PARAMETER_VALUE_TYPE_ILLEGAL

        # 设置Command型属性值
        elif param_type == 'command':
            ret = self.MV_CC_SetCommandValue(node_name)

        # 其他，参数类型非法
        else:
            ret = PARAMETER_TYPE_ILLEGAL

        if ret != MV_OK:
            if set_value_failed_callback is not None:
                set_value_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
        else:
            if set_value_successful_callback is not None:
                set_value_successful_callback()

        return ret

    def get_OptimalPacketSize(self) -> int:
        """
        获取网络最佳包大小
        :return:
        """
        return self.MV_CC_GetOptimalPacketSize()

    def set_PacketSize(self, PacketSize: int,
                       set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置网络包大小
        :param PacketSize:
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='int', node_name="GevSCPSPacketSize",
                                         node_value=PacketSize,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def optimize_PacketSize(self, get_value_failed_callback=None,
                            set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        优化网络最佳包大小
        :param get_value_failed_callback:
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        PacketSize = self.get_OptimalPacketSize()
        if int(PacketSize) > 0:
            return self.set_PacketSize(PacketSize=PacketSize,
                                       set_value_successful_callback=set_value_successful_callback,
                                       set_value_failed_callback=set_value_failed_callback)
        else:
            ret = CAMERA_GET_OPTIMALPACKETSIZE_ERROR
            if get_value_failed_callback is not None:
                get_value_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
            return ret

    def get_PayloadSize(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获取数据包大小
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='int', node_name="PayloadSize",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_AcquisitionFrameRateEnable(self, AcquisitionFrameRateEnable: bool,
                                       set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        使能手动控制相机的帧率
        :param AcquisitionFrameRateEnable:          使能为True，不使能为False
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='bool', node_name="AcquisitionFrameRateEnable",
                                         node_value=AcquisitionFrameRateEnable,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_AcquisitionFrameRateEnable(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得使能采集帧率控制
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:            使能为True，不使能为False
        """
        return self.get_device_parameter(param_type='bool', node_name="AcquisitionFrameRateEnable",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_AcquisitionFrameRate(self, AcquisitionFrameRate: float, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        控制抓取帧的采集频率
        :param AcquisitionFrameRate:
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='float', node_name="AcquisitionFrameRate",
                                         node_value=AcquisitionFrameRate,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_AcquisitionFrameRate(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        控制抓取帧的采集频率
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='float', node_name="AcquisitionFrameRate",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_TriggerMode(self, TriggerMode: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        触发模式开关
        :param TriggerMode:         触发模式使能，1为打开触发模式(MV_TRIGGER_MODE_ON)，0为关闭触发模式(MV_TRIGGER_MODE_OFF)
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """

        return self.set_device_parameter(param_type='enum', node_name="TriggerMode",
                                         node_value=TriggerMode,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_TriggerMode(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得触发模式开关
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:        1为打开触发模式，0为关闭触发模式
        """
        return self.get_device_parameter(param_type='enum', node_name="TriggerMode",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_TriggerSource(self, TriggerSource: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        指定用作触发源的内部信号或物理输入线路。所选触发器的触发模式必须设置为“开”。
        :param TriggerSource:       7 -> 软触发(MV_TRIGGER_SOURCE_SOFTWARE),
                                    0 -> 线路0(MV_TRIGGER_SOURCE_LINE0),
                                    2 -> 线路2(MV_TRIGGER_SOURCE_LINE2),
                                    4 -> 计数器0(MV_TRIGGER_SOURCE_COUNTER0),
                                    1 -> 线路1(MV_TRIGGER_SOURCE_LINE1),
                                    3 -> 线路3(MV_TRIGGER_SOURCE_LINE3)
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='enum', node_name="TriggerSource",
                                         node_value=TriggerSource,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_TriggerSource(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得触发源的内部信号或物理输入线路。所选触发器的触发模式必须设置为“开”。
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:    7 -> 软触发 "Software",
                    0 -> 线路0 "Line0",
                    2 -> 线路2 "Line2",
                    4 -> 计数器0 "Counter0",
                    1 -> 线路1 "Line1",
                    3 -> 线路3 "Line3"
        """
        return self.get_device_parameter(param_type='enum', node_name="TriggerSource",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_TriggerDelay(self, TriggerDelay: float, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        触发延迟（us） 指定在激活触发接收之前要应用的延迟（以us为单位）
        :param TriggerDelay:           延时时间（以us为单位）
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='float', node_name="TriggerDelay",
                                         node_value=TriggerDelay,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_TriggerDelay(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得触发延迟（us） 指定在激活触发接收之前要应用的延迟（以us为单位）
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:        延时时间（以us为单位）
        """
        return self.get_device_parameter(param_type='float', node_name="TriggerDelay",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_TriggerSoftware(self, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        执行软触发命令。如果触发器源设置为软件，则生成内部触发器 此时，获取到一帧图片
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='command', node_name="TriggerSoftware",
                                         node_value=None,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def set_TriggerActivation(self, TriggerActivation: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        指定触发器的激活模式
        :param TriggerActivation:       上升沿 -> 0, 下降沿 -> 1
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='enum', node_name="TriggerActivation",
                                         node_value=TriggerActivation,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_TriggerActivation(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得触发器的激活模式
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:        上升沿 -> 0, 下降沿 -> 1
        """
        return self.get_device_parameter(param_type='enum', node_name="TriggerActivation",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_ExposureAuto(self, ExposureAuto: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置曝光模式
        :param ExposureAuto:    0 -> 关闭自动曝光(MV_EXPOSURE_AUTO_MODE_OFF),
                                1 -> 一次曝光(MV_EXPOSURE_AUTO_MODE_ONCE),
                                2 -> 连续自动曝光(MV_EXPOSURE_AUTO_MODE_CONTINUOUS)
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='enum', node_name="ExposureAuto",
                                         node_value=ExposureAuto,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_ExposureAuto(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得曝光模式
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:    0 -> 关闭自动曝光(MV_EXPOSURE_AUTO_MODE_OFF),
                    1 -> 一次曝光(MV_EXPOSURE_AUTO_MODE_ONCE),
                    2 -> 连续自动曝光(MV_EXPOSURE_AUTO_MODE_CONTINUOUS)
        """
        return self.get_device_parameter(param_type='enum', node_name="ExposureAuto",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_ExposureTime(self, ExposureTime: float, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置曝光时间（us）  曝光模式定时时的曝光时间
        :param ExposureTime:        曝光时间（us）
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='float', node_name="ExposureTime",
                                         node_value=ExposureTime,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_ExposureTime(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得曝光时间
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='float', node_name="ExposureTime",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_GainAuto(self, GainAuto: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置自动增益
        :param GainAuto:    0 -> 关闭自动增益(MV_GAIN_MODE_OFF),
                            1 -> 一次增益(MV_GAIN_MODE_ONCE),
                            2 -> 连续自动增益(MV_GAIN_MODE_CONTINUOUS)
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='enum', node_name="GainAuto",
                                         node_value=GainAuto,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_GainAuto(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得增益模式
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:    0是关闭自动增益, 1是一次增益, 2是连续自动增益
        """
        return self.get_device_parameter(param_type='enum', node_name="GainAuto",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_Gain(self, Gain: float, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        增益（dB), 应用于图像的增益，单位为dB, 自动增益关闭时使用
        :param Gain:
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='float', node_name="Gain",
                                         node_value=Gain,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_Gain(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        控制增益
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='float', node_name="Gain",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_Brightness(self, Brightness: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        亮度  此值设置选定的亮度控制
        :param Brightness:
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='int', node_name="Brightness",
                                         node_value=Brightness,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_Brightness(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得亮度
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='int', node_name="Brightness",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_Sharpness(self, Sharpness: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置锐度
        :param Sharpness:
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='int', node_name="Sharpness",
                                         node_value=Sharpness,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_Sharpness(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得锐度
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='int', node_name="Sharpness",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_SharpnessEnable(self, SharpnessEnable: bool, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置锐度使能
        :param SharpnessEnable:          使能 -> True，不使能 -> False
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='bool', node_name="SharpnessEnable",
                                         node_value=SharpnessEnable,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_SharpnessEnable(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得锐度使能
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='bool', node_name="SharpnessEnable",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_Gamma(self, Gamma: float, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        伽马校正              [0, 4 ]
        :param Gamma:       [0, 4 ]
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='float', node_name="Gamma",
                                         node_value=Gamma,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_Gamma(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        伽马校正
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='float', node_name="Gamma",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_GammaSelector(self, GammaSelector: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        此枚举选择要应用的伽马类型
        :param GammaSelector:       伽马类型:   1 -> "User"(MV_GAMMA_SELECTOR_USER),
                                               2 -> "sRGB"(MV_GAMMA_SELECTOR_SRGB)
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='enum', node_name="GammaSelector",
                                         node_value=GammaSelector,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_GammaSelector(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        要应用的伽马类型
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:                1 -> "User", 2 -> "sRGB"
        """
        return self.get_device_parameter(param_type='enum', node_name="GammaSelector",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_GammaEnable(self, GammaEnable: bool, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置伽马使能
        :param GammaEnable:
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='bool', node_name="GammaEnable",
                                         node_value=GammaEnable,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_GammaEnable(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得伽马使能
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='bool', node_name="GammaEnable",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def get_WidthMax(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得最大宽度
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='int', node_name="WidthMax",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def get_HeightMax(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得最大高度
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='int', node_name="HeightMax",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_Width(self, Width: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置宽度
        :param Width:
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='int', node_name="Width", node_value=Width,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_Width(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得宽度
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='int', node_name="Width",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_Height(self, Height: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置高度
        :param Height:
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='int', node_name="Height", node_value=Height,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_Height(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得高度
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='int', node_name="Height",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_OffsetX(self, OffsetX: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置x偏移
        :param OffsetX:
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='int', node_name="OffsetX",
                                         node_value=OffsetX,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_OffsetX(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得x偏移
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='int', node_name="OffsetX",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    def set_OffsetY(self, OffsetY: int, set_value_successful_callback=None, set_value_failed_callback=None) -> int:
        """
        设置y偏移
        :param OffsetY:
        :param set_value_successful_callback:
        :param set_value_failed_callback:
        :return:
        """
        return self.set_device_parameter(param_type='int', node_name="OffsetY", node_value=OffsetY,
                                         set_value_successful_callback=set_value_successful_callback,
                                         set_value_failed_callback=set_value_failed_callback)

    def get_OffsetY(self, get_value_successful_callback=None, get_value_failed_callback=None) -> dict:
        """
        获得y偏移
        :param get_value_successful_callback:
        :param get_value_failed_callback:
        :return:
        """
        return self.get_device_parameter(param_type='int', node_name="OffsetY",
                                         get_value_successful_callback=get_value_successful_callback,
                                         get_value_failed_callback=get_value_failed_callback)

    @staticmethod
    def err_code_map(err_code: int) -> str:
        """
        错误代码映射为字符串
        :param err_code:    int 错误代码
        :return:            str 错误提示
        """
        default = "未知错误代码"
        return err_mapping.get(err_code, default)
