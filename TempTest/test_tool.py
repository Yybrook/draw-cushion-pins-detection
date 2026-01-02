import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow,
                             QAction, QPlainTextEdit, QStyle, QFileDialog, QLabel, QCheckBox, QStatusBar, QMessageBox,
                             QToolBar)
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon


class ToolButton(QMainWindow):
    def __init__(self):
        super().__init__()
        self.path = None
        self.setWindowTitle("ToolButton and QAction Demo")
        self.resize(500, 400)
        self.init_ui()

    def init_ui(self):
        # 设置一个文本编辑器作为中心小部件, setCentralWidget设置窗口中心部件
        self.text_editor = QPlainTextEdit(self)
        self.setCentralWidget(self.text_editor)

        mbar = self.menuBar()
        m_file = mbar.addMenu('文件(&F)')
        m_edit = mbar.addMenu('编辑(&E)')
        m_format = mbar.addMenu('格式(&O)')
        m_help = mbar.addMenu('帮助(&H)')
        style = QApplication.style()

        # -------------------------------- 文件操作部分 -------------------------------- #
        # 新建文件
        act_file_new = QAction('新建(&N)', self)
        act_file_new.setIcon(style.standardIcon(QStyle.SP_FileIcon))
        act_file_new.setShortcut(Qt.CTRL + Qt.Key_N)
        act_file_new.triggered.connect(self.slot_file_new)
        m_file.addAction(act_file_new)

        # 打开文件
        act_file_open = QAction('打开(&O)...', self)
        act_file_open.setIcon(style.standardIcon(QStyle.SP_DialogOpenButton))
        act_file_open.setShortcut(Qt.CTRL + Qt.Key_O)
        act_file_open.triggered.connect(self.slot_file_open)
        m_file.addAction(act_file_open)

        # 保存
        act_file_save = QAction('保存(&S)', self)
        act_file_save.setIcon(style.standardIcon(QStyle.SP_DialogSaveButton))
        act_file_save.setShortcut(Qt.CTRL + Qt.Key_S)
        act_file_save.triggered.connect(self.slot_file_save)
        m_file.addAction(act_file_save)

        # 另存为
        act_file_saveas = QAction('另存为(&A)...', self)
        act_file_saveas.triggered.connect(self.slot_file_saveas)
        m_file.addAction(act_file_saveas)
        m_file.addSeparator()

        # 退出菜单
        aFileExit = QAction('退出(&X)', self)
        aFileExit.triggered.connect(self.close)
        m_file.addAction(aFileExit)

        # -------------------------------- 编辑部分 -------------------------------- #
        # 撤销编辑
        act_edit_undo = QAction('撤销(&U)', self)
        act_edit_undo.setShortcut(Qt.CTRL + Qt.Key_Z)
        act_edit_undo.triggered.connect(self.text_editor.undo)
        m_edit.addAction(act_edit_undo)

        # 恢复编辑
        aEditRedo = QAction('恢复(&R)', self)
        aEditRedo.setShortcut(Qt.CTRL + Qt.Key_Y)
        act_edit_undo.triggered.connect(self.text_editor.redo)
        m_edit.addAction(aEditRedo)
        m_edit.addSeparator()

        # 剪切操作
        act_edit_cut = QAction('剪切(&T)', self)
        act_edit_cut.setShortcut(Qt.CTRL + Qt.Key_X)
        act_edit_cut.triggered.connect(self.text_editor.cut)
        m_edit.addAction(act_edit_cut)

        # 复制操作
        act_edit_copy = QAction('复制(&C)', self)
        act_edit_copy.setShortcut(Qt.CTRL + Qt.Key_C)
        act_edit_copy.triggered.connect(self.text_editor.copy)
        m_edit.addAction(act_edit_copy)

        # 粘贴操作
        act_edit_paste = QAction('粘贴(&P)', self)
        act_edit_paste.setShortcut(Qt.CTRL + Qt.Key_V)
        act_edit_paste.triggered.connect(self.text_editor.paste)
        m_edit.addAction(act_edit_paste)

        # 删除操作
        act_edit_del = QAction('删除(&L)', self)
        act_edit_del.setShortcut(Qt.Key_Delete)
        act_edit_del.triggered.connect(self.slot_edit_delete)
        m_edit.addAction(act_edit_del)
        m_edit.addSeparator()

        # 全选操作
        act_edit_select_all = QAction('全选(&A)', self)
        act_edit_select_all.setShortcut(Qt.CTRL + Qt.Key_A)
        act_edit_select_all.triggered.connect(self.text_editor.selectAll)
        m_edit.addAction(act_edit_select_all)

        # ==== 格式设置部分 ==== #
        act_fmt_auto_line = QAction('自动换行(&W)', self)
        act_fmt_auto_line.setCheckable(True)
        act_fmt_auto_line.setChecked(True)
        act_fmt_auto_line.triggered.connect(self.slot_format_auto_line)
        m_format.addAction(act_fmt_auto_line)

        # ==== 帮助部分 ==== #
        act_help_about = QAction('关于(&A)...', self)
        act_help_about.triggered.connect(self.slot_help_about)
        m_help.addAction(act_help_about)

    def msg_critical(self, strInfo):
        dlg = QMessageBox(self)
        dlg.setIcon(QMessageBox.Critical)
        dlg.setText(strInfo)
        dlg.show()

    def slot_file_new(self):
        self.text_editor.clear()

    def slot_file_open(self):
        path, _ = QFileDialog.getOpenFileName(self, '打开文件', '', '文本文件 (*.txt)')
        if path:
            try:
                with open(path, 'rU') as f:
                    text = f.read()
            except Exception as e:
                self.msg_critical(str(e))
            else:
                self.path = path
                self.text_editor.setPlainText(text)

    def slot_file_save(self):
        if self.path is None:
            return self.slot_file_saveas()
        self._saveToPath(self.path)

    def slot_file_saveas(self):
        path, _ = QFileDialog.getSaveFileName(self, '保存文件', '', '文本文件 (*.txt)')
        if not path:
            return self._slot_save_to_path(path)

    def _slot_save_to_path(self, path):
        text = self.text_editor.toPlainText()
        try:
            with open(path, 'w') as f:
                f.write(text)
        except Exception as e:
            self.msg_critical(str(e))
        else:
            self.path = path

    def slot_edit_delete(self):
        tc = self.text_editor.textCursor()
        # tc.select(QtGui.QTextCursor.BlockUnderCursor) 这样删除一行
        tc.removeSelectedText()

    def slot_format_auto_line(self, autoLine):
        if autoLine:
            self.text_editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self.text_editor.setLineWrapMode(QPlainTextEdit.NoWrap)

    def slot_help_about(self):
        QMessageBox.information(self, '实战PyQt5', 'PyQt5实现的文本编辑器演示版')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ToolButton()
    window.show()
    sys.exit(app.exec())





