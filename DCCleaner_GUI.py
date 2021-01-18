import lxml.html
import requests
import sys

from configparser import ConfigParser

from PyQt5.QtWidgets import *
from PyQt5 import uic

form_class = uic.loadUiType("DCCleaner.ui")[0]


def alertMsgBox(title, text):
    msgbox = QMessageBox()
    msgbox.setWindowTitle(title)
    msgbox.setText(text)
    msgbox.exec_()


def initSession():
    # Make New Login Session Globally
    global sess
    sess = requests.Session()
    sess.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Whale/2.8.107.16 Safari/537.36"
    }


class MyWindow(QMainWindow, form_class):
    isSave = False

    config = ConfigParser()

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        initSession()
        self.loadConf()
        self.isSaveAccount.stateChanged.connect(self.mgrAccount)
        self.loginButton.clicked.connect(self.dcLogin)
        self.idBox.returnPressed.connect(self.focusEvent)
        self.pwBox.returnPressed.connect(self.loginButton.click)

    def closeEvent(self, event):
        result = QMessageBox.question(self, 'Are you sure to Exit?',
                                           "디시 클리너를 종료하시겠습니까?", QMessageBox.Yes |
                                           QMessageBox.No, QMessageBox.No)
        if result == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def focusEvent(self):
        if self.pwBox.text():
            self.loginButton.click()
        else:
            self.pwBox.setFocus()

    def loadConf(self):
        self.config.read("settings.conf")
        if eval(self.config['Settings']['isSaveAccount']):
            self.isSave = True
            self.idBox.setText(self.config['Account']['id'])
            self.pwBox.setText(self.config['Account']['pw'])
            self.isSaveAccount.setChecked(True)

    def dcLogin(self):
        dcid = self.idBox.text()
        dcpw = self.pwBox.text()

        if not dcid or not dcpw:
            alertMsgBox("경고!", "ID와 PW를 입력해주세요.")
            return None

        # Login Headers
        LOGIN_REQ_HEADERS = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "dcid.dcinside.com",
            "Origin": "https://www.dcinside.com",
            "Referer": "https://www.dcinside.com/",
            "Upgrade-Insecure-Requests": "1"
        }
        LOGIN_POST_DATA = {
            's_url': "https://www.dcinside.com/",
            'ssl': "Y",
            'user_id': dcid,
            'pw': dcpw
        }

        # Get Hidden Robot Code
        hidden = requests.get("https://www.dcinside.com/")
        hidden_parsed = lxml.html.fromstring(hidden.text)
        hidden_name = hidden_parsed.xpath('//*[@id="login_process"]/input[3]')[0].get("name")
        hidden_value = hidden_parsed.xpath('//*[@id="login_process"]/input[3]')[0].get("value")
        LOGIN_POST_DATA[hidden_name] = hidden_value

        # Login
        try_login = sess.post("https://dcid.dcinside.com/join/member_check.php", data=LOGIN_POST_DATA,
                              headers=LOGIN_REQ_HEADERS)

        if "history.back(-1);" in try_login.text:
            alertMsgBox("로그인 실패!", "ID와 PW를 확인해주세요.")
        else:
            self.loginStatus.setText(f'로그인 상태 : {dcid}')
            self.loginButton.setText("로그아웃")
            self.idBox.setDisabled(True)
            self.pwBox.setDisabled(True)
            self.loginButton.clicked.connect(self.dcLogout)
            if self.isSave:
                self.config.set('Account', 'id', dcid)
                self.config.set('Account', 'pw', dcpw)
                self.writeConf()

    def dcLogout(self):
        initSession()
        self.loginStatus.setText("로그인 상태 : None")
        self.loginButton.setText("로그인")
        self.idBox.setDisabled(False)
        self.pwBox.setDisabled(False)
        self.loginButton.clicked.connect(self.dcLogin)

    def mgrAccount(self):
        if self.isSaveAccount.isChecked():
            self.isSave = True
            self.config.set("Settings", "isSaveAccount", "True")
            self.writeConf()
        else:
            self.isSave = False
            self.config.set("Settings", "isSaveAccount", "False")
            self.config.set('Account', 'id', "null")
            self.config.set('Account', 'pw', "null")
            self.writeConf()

    def writeConf(self):
        with open('settings.conf', 'w') as conf:
            self.config.write(conf)


app = QApplication(sys.argv)
window = MyWindow()
window.show()
app.exec_()
