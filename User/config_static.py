CF_VERSION = '3.2.3.1'
CF_CREATE_TIME = '2024年2月27日'
CF_CONTACTS = {
    "安洪涛": "AnHongtao@csvw.com",
    "尹研": "YinYan@csvw.com",
    "王雷": "523010696@qq.com",
    }

CF_README_PATH = r'./PinsCtrlData/ReadMe/Pins-Ctrl软件说明书_V3.2.0_20240313.pdf'

CF_CAMERAS_TABLE_HEADER = {
    '枚举序号': "DeviceIndex",
    '角色': "Role",
    '生产线': "Line",
    '位置': "Location",
    '方向': "Side",
    '自定义信息': "Uid",
    '序列号': "SerialNumber",
    '相机IP': "CurrentIp",
    '相机型号': "ModelName",
    }

CF_PARTS_TABLE_HEADER = {
    '序号': "ID",
    '生产线': "Line",
    '零件': "Part"
    }

CF_IMPORT_TABLE_HEADER = {
    '序号': "ID",
    '生产线': "Line",
    '零件': "Part",
    '行': "Rows",
    '列': "Columns"
    }

CF_RECORDS_TABLE_HEADER = {
    '序号': "ID",
    '时间': "When",
    '生产线': "Line",
    '零件': "Part",
    '位置': "Location",
    '结果': "Result",
    '作者': "User",
    }

NULL_CAMERA_LOCATION = {"Line": "", "Location": "", 'Side': "", "Role": ""}

CF_PROJECT_ROLE = "PINS"

CF_APP_TITLE = "Pins-Ctrl"
CF_APP_ICON = r".\PinsCtrlData\Static\Pictures\camera_yy.ico"
CF_NULL_PICTURE = r".\PinsCtrlData\Static\Pictures\dog.jpg"
CF_CAMERA_YY_PICTURE = r".\PinsCtrlData\Static\Pictures\camera_yy.jpg"
CF_CAMERA_PICTURE = r".\PinsCtrlData\Static\Pictures\camera.jpg"
CF_CAR_PICTURE = r".\PinsCtrlData\Static\Pictures\car.jpg"
CF_PART_PICTURE = r".\PinsCtrlData\Static\Pictures\part.jpg"
CF_RECORD_PICTURE = r".\PinsCtrlData\Static\Pictures\record.png"
CF_ID_PICTURE = r".\PinsCtrlData\Static\Pictures\id.png"
CF_DATABASE_PATH = r".\PinsCtrlData\Database\pins_ctrl_database.accdb"
CF_TEMP_TEACH_DIR = r".\PinsCtrlData\Temp\Teach"
CF_RECORDS_DETECTION_PICTURES_DIR = r".\PinsCtrlData\DetectionRecords\DetectionPictures"
CF_RECORDS_ORIGIN_PICTURES_DIR = r".\PinsCtrlData\DetectionRecords\OriginPictures"
CF_RUNNING_SEQUENCE_FILE = r".\PinsCtrlData\Temp\sequence"

CF_TEACH_INFO_PAGE = 0
CF_TEACH_KEYSTONE_PAGE = 1
CF_TEACH_DIVISION_PAGE = 2
CF_TEACH_BINARIZATION_PAGE = 3
CF_TEACH_DENOISE_PAGE = 4
CF_TEACH_CONTOURS_PAGE = 5
CF_TEACH_PINS_MAP_PAGE = 6

CF_ROOT_CAMERAS_PAGE = 0
CF_ROOT_PARTS_PAGE = 1
CF_ROOT_RECORDS_PAGE = 2

CF_RUNNING_ROOT_FLAG = 1
CF_RUNNING_GRAB_FLAG = 2
CF_RUNNING_TEACH_FLAG = 3

CF_TEACH_REFERENCE_SIDE = "RIGHT"

TB_CAMERAS_IDENTITY = "CamerasIdentity"
TB_PROCESS_PARAMETERS = "ProcessParameters"
TB_PARTS_PINSMAP = "PartsPinsMap"
TB_DETECTION_RECORDS = "DetectionRecords"
TB_SOCKET_CONFIG = "SocketConfig"

# RGB
CF_COLOR_PINSMAP_PIN = (105, 105, 105)
CF_COLOR_PINSMAP_NULL = (255, 255, 255)
CF_COLOR_PINSMAP_FREE = (0, 215, 255)
CF_COLOR_PINSMAP_DOWEL = (87, 139, 46)

# BGR
CF_COLOR_KEYSTONE_POINT = (60, 20, 220)
CF_COLOR_KEYSTONE_LINE = (180, 105, 255)
CF_COLOR_DIVISION_VERTICAL_LINE = (238, 130, 238)
CF_COLOR_DIVISION_HORIZONTAL_LINE = (127, 255, 0)
CF_COLOR_CONTOURS_CIRCLE = (0, 69, 255)
CF_COLOR_ERROR_PINS = (87, 139, 46)
CF_COLOR_ERROR_NULL = (255, 105, 65)

CF_PART_NUMBER_IGNORE_SYMBOLS = [' ', '-', '_', '\\', '/', '|']

CF_PINSMAP_PIN_CODE = '●'
CF_PINSMAP_NULL_CODE = '×'
CF_PINSMAP_FREE_CODE = '○'
CF_PINSMAP_DOWEL_CODE = '◎'

CF_PINSMAP_CODES_LIST = ["禁用", CF_PINSMAP_PIN_CODE, CF_PINSMAP_NULL_CODE, CF_PINSMAP_FREE_CODE, CF_PINSMAP_DOWEL_CODE]

CF_DATA_REPLACE_ONCE = 0
CF_DATA_REPLACE_ALL = 1
CF_DATA_REPLACE_NONE = -1

CF_TEACH_AUTHORITY_PASSWORD = "123"
