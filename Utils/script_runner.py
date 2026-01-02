import os
import sys
from subprocess import Popen, PIPE
from typing import Optional


class ScriptRunner:

    @staticmethod
    def create_python_script(python_path: str, script_path: str, parameters: Optional[dict]) -> str:
        """
        生成 python 脚本
        :param python_path:
        :param script_path:
        :param parameters:
        :return:
        """
        command = "{} {}".format(python_path, script_path)
        if parameters:
            for k, v in parameters.items():
                command += " --{} {}".format(k, str(v))
        return command

    @staticmethod
    def run_script(script: str, password: Optional[str], parameters: Optional[dict], terminal: bool = False, is_linux: bool = False) -> Popen:
        """
        运行脚本
        :param script:
        :param password:
        :param parameters:
        :param terminal:
        :param is_linux:
        :return:
        """
        if password is not None:
            if is_linux:
                command = "echo {} | sudo -S {}".format(script, password)
            else:
                raise Exception("windows system not supported")
        else:
            command = script

        if parameters:
            for k, v in parameters.items():
                command += " --{} {}".format(k, v)

        if terminal:
            if is_linux:
                # command = ['gnome-terminal', '--', 'bash', '-c', command]
                # exec bash -> 保持终端窗口打开而不退出
                command = 'gnome-terminal -- bash -c {};exec bash'.format(command)
            else:
                # /k -> 保持终端窗口打开而不退出  /c -> 自动退出终端窗口
                command = 'start cmd.exe /k {}'.format(command)

        # print(command)

        subprocess = Popen(
            command,
            shell=True,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            # preexec_fn=lambda: os.setsid()       # 设置成为守护进程（daemon）,linux
        )

        return subprocess

    @staticmethod
    def get_output_from_subprocess(subprocess: Popen, decode_output_callback):
        """
        从子进程获取 stdout
        :param subprocess:
        :param decode_output_callback:
        :return:
        """
        while True:
            # subprocess.poll() == None 表示程序正在运行
            if subprocess.poll() is not None:
                break

            # 接受字符串 带有 \r\n 转义字符
            message = subprocess.stdout.readline().decode('utf-8')[:-2]

            if message != "":
                if decode_output_callback is not None:

                    decode_output_callback(pid=subprocess.pid, message=message)

    @staticmethod
    def get_error_from_subprocess(subprocess: Popen, decode_error_callback):
        """
        从子进程获取 stderr
        :param subprocess:
        :param decode_error_callback:
        :return:
        """
        while True:
            if subprocess.poll() is not None:
                break

            # 接受字符串 带有 \r\n 转义字符
            message = subprocess.stderr.readline().decode('utf-8')[:-2]
            if message != "":
                if decode_error_callback is not None:
                    decode_error_callback(pid=subprocess.pid, message=message)

    @staticmethod
    def put_input_2_subprocess(subprocess: Popen, message: str):
        """
        向子进程发送 stdin
        :param subprocess:
        :param message:
        :return:
        """
        # 增加 \n , 用于被 sys.stdin.readline() 接受
        if message.endswith('\r\n'):
            message = "{}\n".format(message[:-2])
        elif message.endswith('\n'):
            pass
        else:
            message += "\n"

        # 发送
        subprocess.stdin.write(message.encode('utf-8'))
        # 刷新缓冲区，用于立即发送
        subprocess.stdin.flush()

    @staticmethod
    def get_input_in_subprocess(decode_input_callback):
        """
        在子进程获取输入, sys.stdin
        :param decode_input_callback:
        :return:
        """
        while True:
            # 接受到的 带有 \n 转义字符
            message = sys.stdin.readline()[:-1]
            if message != "":
                if decode_input_callback is not None:
                    decode_input_callback(message=message)

    @staticmethod
    def put_output_in_subprocess(message: str):
        """
        在子进程发送输出, sys.stdout
        :param message:
        :return:
        """
        # 发送的字符串 带有 \r\n 转义字符
        sys.stdout.write("{}\n".format(message))
        # 刷新缓冲区，用于立即发送
        sys.stdout.flush()

    @staticmethod
    def put_error_in_subprocess(message: str):
        """
        在子进程发送error, sys.stderr
        :param message:
        :return:
        """
        # 发送的字符串 带有 \r\n 转义字符
        sys.stderr.write("{}\n".format(message))
        # 刷新缓冲区，用于立即发送
        sys.stderr.flush()


if __name__ == '__main__':
    from threading import Thread
    from time import sleep

    print("### mainprocess[pid:{}] start ###".format(os.getpid()))

    to_exit = False
    my_exit_flag = "###SubprocessStart###"

    def decode_output(message: str, exit_flag: Optional[str]):
        global to_exit
        print("\n\tsubprocess output[{}]".format(message))
        if exit_flag is not None and message == exit_flag:
            to_exit = True

    def decode_error(message: str, exit_flag: Optional[str]):
        global to_exit
        print("\n\tsubprocess error[{}]".format(message))
        if exit_flag is not None and message == exit_flag:
            to_exit = True

    def get_input(p: Popen):
        while True:
            # 接受到的 没有转义字符
            my_input = input(">>> input: ")
            if my_input == "exit sub":
                ScriptRunner.put_input_2_subprocess(subprocess=p, message="exit")
                continue
            elif my_input == "poll":
                poll = p.poll()
                print("\n\tsubprocess poll[{}]".format(poll))
            else:
                ScriptRunner.put_input_2_subprocess(subprocess=p, message=my_input)


    my_script = ScriptRunner.create_python_script(
        python_path="C:/Users/yy/anaconda3/envs/py36/python.exe",
        script_path="./popen_test.py",
        parameters={"exit_flag": my_exit_flag}
    )

    my_p = ScriptRunner.run_script(
        script=my_script,
        password=None,
        parameters=None,
        terminal=False,
        is_linux=False
    )

    t1 = Thread(
        target=get_input,
        args=(my_p,),
        daemon=True
    )
    t1.start()

    t2 = Thread(
        target=ScriptRunner.get_output_from_subprocess,
        args=(my_p, lambda message: decode_output(message=message, exit_flag=my_exit_flag)),
        daemon=True
    )
    t2.start()

    t3 = Thread(
        target=ScriptRunner.get_error_from_subprocess,
        args=(my_p, lambda message: decode_error(message=message, exit_flag=None)),
        daemon=True
    )
    t3.start()

    while True:
        if to_exit:
            break

        sleep(1)

    print("### mainprocess terminated ###")
