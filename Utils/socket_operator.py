import socket
from Utils.correspondent import COMMAND_STOP_LISTEN, COMMAND_PREFIX, MyCorrespondent

'''
{"command":"stop listen"}

{"command":"enum device"}
    {"result":"enum error"}
    {"result":"enum none"}
    {"result":"05100^_^15100^_^0meb100^_^1meb100^_^2meb100^_^3meb100"}

{"command":"open and check","userDefined":"05100","line":"5-100","model":"5100PART1"}
    {"result":"check right","picture":"xxx"}
    {"result":"check wrong","picture":"xxx"}
    {"result":"open failed"}
    {"result":"check error"}


'''


class SocketOperator:

    conn_dict = dict()

    def __init__(self):
        self.ip = None          # 本地的IP地址
        self.port = -1          # 本地TCP端口

        self.server = None      # tcp服务端对象

    def __del__(self):
        for conn in SocketOperator.conn_dict.values():
            conn.close()
        SocketOperator.conn_dict = dict()

        if self.server is not None:
            self.server.close()

    @staticmethod
    def pop_conn(address: tuple):
        SocketOperator.conn_dict.pop(address)

    @staticmethod
    def get_all_ips() -> list:
        """
        获取所有的IP地址
        :return:  所有ip列表
        """
        host_name = socket.gethostname()
        _, _, ips = socket.gethostbyname_ex(host_name)
        return ips

    @staticmethod
    def get_valid_ip() -> tuple:
        """
        获取有效的IP地址
        :return: 有效ip和ip列表
        """
        ips = SocketOperator.get_all_ips()
        ip = None
        try:
            # 创建一个udp协议
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            i, _ = s.getsockname()      # 返回（ip,port）
            if i in ips:
                ip = i
            # 关闭socket
            s.close()
        except:
            pass
        return ip, ips

    def stop_listen(self):
        """
        发送停止监听命令，用于停止tcp监听，并且关闭多线程
        命令："{"command":"stop listen"}"
        :return:
        """
        if self.server is not None:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 创建 TCP socket
            client.connect((self.ip, self.port))                        # 连接服务器

            command = MyCorrespondent.create_message(COMMAND_PREFIX, COMMAND_STOP_LISTEN)
            client.send(command.encode("gbk"))                          # 发送停止监听命令

            client.close()                                              # 关闭TCP socket客户端

    def start_listen(self, ip: str, port: int,
                     server_created_successful_callback=None, server_created_failed_callback=None, server_closed_callback=None,
                     client_online_callback=None, client_offline_callback=None):
        """
        开始监听后执行的函数
        :return:
        """
        try:
            self.ip, self.port = ip, port

            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                 # 创建 TCP socket
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)    # 设置端口复用
            self.server.bind((self.ip, self.port))                                          # 绑定socket地址
            # 使用socket创建的套接字默认的属性是主动的，使用listen将其变为被动的，这样就可以接收别人的链接了
            # listen(10) 中10表示可以连接客户端的个数
            self.server.listen(24)

            SocketOperator.conn_dict = dict()     # 重置conn_dict

            # 监听成功的回调函数
            if server_created_successful_callback is not None:
                server_created_successful_callback()

            while True:
                # 接受一个连接
                # 如果有新的客户端来链接服务器，那么就产生一个新的套接字专门为这个客户端服务
                # 会产生阻塞，等待客户端连接
                try:
                    conn, address = self.server.accept()

                    # 加入conn_dict
                    SocketOperator.conn_dict[address] = conn

                    # print('[server] get connection from %s' % str(address))  # 输出客户端信息(ip, port)
                    if client_online_callback is not None:
                        client_online_callback(address=address)

                    # 在多线程接受、解析、执行指令
                    t = MyCorrespondent(server=self.server, conn=conn, address=address,
                                        client_offline_callback=client_offline_callback, pop_conn_callback=SocketOperator.pop_conn)
                    t.setDaemon(True)
                    t.start()

                    # 打印多线程信息
                    # thread_info = threading.enumerate()
                    # length = len(thread_info)
                    # print('thread -> thread num：%d, info: %s' % (length, str(thread_info)))

                except Exception as err:
                    # print('[server] accept failed, err content: %s' % str(err))
                    # "[WinError 10038] 在一个非套接字上尝试了一个操作。"
                    if '10038' in str(err):
                        if server_closed_callback is not None:
                            server_closed_callback()
                        break

        except Exception as err:
            # print('[server] listen failed, err content: %s' % str(err))

            # 监听失败的回调函数
            if server_created_failed_callback is not None:
                server_created_failed_callback(error=str(err))

        for conn in SocketOperator.conn_dict.values():
            conn.close()
        SocketOperator.conn_dict = dict()

        self.server.close()
        self.server = None
