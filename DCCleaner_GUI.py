import lxml.html
import re
import requests
import sys

from bs4 import BeautifulSoup
from configparser import ConfigParser

from PyQt5.QtWidgets import *
from PyQt5 import uic

from qt_material import apply_stylesheet

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

    commentGallNo = []
    postGallNo = []

    config = ConfigParser()

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        initSession()
        self.loadConf()
        self.isSaveAccount.stateChanged.connect(self.mgrAccount)
        self.commentGallList.setDisabled(True)
        self.delComment.setDisabled(True)
        self.postGallList.setDisabled(True)
        self.delPost.setDisabled(True)
        self.loginButton.clicked.connect(self.dcLogin)
        self.devInfoButton.clicked.connect(self.devInfoMsg)
        self.idBox.returnPressed.connect(self.focusEvent)
        self.pwBox.returnPressed.connect(self.loginButton.click)
        self.idBox.setFocus()
        self.commentGallList.currentIndexChanged.connect(self.commentGallSelectionChanged)
        self.postGallList.currentIndexChanged.connect(self.postGallSelectionChanged)

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
            self.getGallList(dcid)

    def dcLogout(self):
        initSession()
        self.loginStatus.setText("로그인 상태 : None")
        self.loginButton.setText("로그인")
        self.idBox.setDisabled(False)
        self.pwBox.setDisabled(False)
        self.commentGallList.clear()
        self.commentGallList.setDisabled(True)
        self.delComment.setDisabled(True)
        self.postGallList.clear()
        self.postGallList.setDisabled(True)
        self.delPost.setDisabled(True)
        self.loginButton.clicked.connect(self.dcLogin)

    def getGallList(self, dcid):
        # Get Gallog
        comment_gallog = sess.get("https://gallog.dcinside.com/" + dcid + "/comment")
        comment_gallog_parsed = BeautifulSoup(comment_gallog.text, "lxml")

        post_gallog = sess.get("https://gallog.dcinside.com/" + dcid + "/posting")
        post_gallog_parsed = BeautifulSoup(post_gallog.text, "lxml")

        # Parse optionbox for Listing All Galleries
        comment_option_box = comment_gallog_parsed.find_all(class_="option_box")[1]
        comment_option_box = comment_option_box.find_all("li")

        post_option_box = post_gallog_parsed.find_all(class_="option_box")[1]
        post_option_box = post_option_box.find_all("li")

        comment_gall_list = ["전체 갤러리"]
        self.commentGallNo += [dcid + "/comment"]
        for gall in range(1, len(comment_option_box)):
            comment_gall_list += [comment_option_box[gall].text]
            self.commentGallNo += [comment_option_box[gall]['onclick'][15:-1]]

        post_gall_list = ["전체 갤러리"]
        self.postGallNo += [dcid + "/posting"]
        for gall in range(1, len(post_option_box)):
            post_gall_list += [post_option_box[gall].text]
            self.postGallNo += [post_option_box[gall]['onclick'][15:-1]]

        for s in comment_gall_list:
            self.commentGallList.addItem(s)
        self.commentGallList.setDisabled(False)
        self.delComment.setDisabled(False)

        for s in post_gall_list:
            self.postGallList.addItem(s)
        self.postGallList.setDisabled(False)
        self.delPost.setDisabled(False)

    def commentGallSelectionChanged(self):
        idx = self.commentGallList.currentIndex()

        # Get Gallog
        gallog = sess.get("https://gallog.dcinside.com/" + self.commentGallNo[idx])
        gallog_parsed = lxml.html.fromstring(gallog.text)

        # Get num
        if idx == 0:
            num = gallog_parsed.xpath('//*[@id="container"]/article/div/section/div[1]/header/div/div[1]/button[1]/span')[0].text.replace(",", "")
        else:
            num = gallog_parsed.xpath('//*[@id="container"]/article/div/section/div[1]/header/div/h2/span[3]')[0].text.replace(",", "")
        num = re.findall("\d+", num)[0]

        self.totalComment.setText("전체 댓글 : %s개" % num)

    def postGallSelectionChanged(self):
        idx = self.postGallList.currentIndex()

        # Get Gallog
        gallog = sess.get("https://gallog.dcinside.com/" + self.postGallNo[idx])
        gallog_parsed = lxml.html.fromstring(gallog.text)

        # Get num
        if idx == 0:
            num = gallog_parsed.xpath('//*[@id="container"]/article/div/section/div[1]/header/div/div[1]/button[1]/span')[0].text.replace(",", "")
        else:
            num = gallog_parsed.xpath('//*[@id="container"]/article/div/section/div[1]/header/div/h2/span[3]')[0].text.replace(",", "")
        num = re.findall("\d+", num)[0]

        self.totalPost.setText("전체 게시글 : %s개" % num)


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

    def devInfoMsg(self):
        alertMsgBox("개발자 정보", "Dev : qwertycvb(SerenityS)<br>E-Mail : jins4218@gmail.com<br>Github : <a href='https://github.com/SerenityS'>https://github.com/SerenityS</a><br><br><a href='https://github.com/augustapple/ThanosCleaner'>Inspired by ThanosCleaner</a>")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    apply_stylesheet(app, theme='dark_teal.xml')
    window.show()
    app.exec_()
