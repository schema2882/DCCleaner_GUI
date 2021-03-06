import json
import os
import threading

import lxml.html
import re
import requests
import sys
import time
import webbrowser

from bs4 import BeautifulSoup
from configparser import ConfigParser

from PyQt5.QtWidgets import *
from PyQt5 import uic

from qt_material import apply_stylesheet

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

form = resource_path('DCCleaner.ui')
form_class = uic.loadUiType(form)[0]

VER = 1.0


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
    delProcess = False

    commentGallNo = []
    postGallNo = []

    config = ConfigParser()

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setFixedSize(361, 744)
        initSession()
        #self.updateAlert()
        self.loadConf()
        self.isSaveAccount.stateChanged.connect(self.mgrAccount)
        self.commentGallList.setDisabled(True)
        self.delCommentButton.setDisabled(True)
        self.delCommentButton.clicked.connect(self.cleanComment)
        self.postGallList.setDisabled(True)
        self.delPostButton.setDisabled(True)
        self.delPostButton.clicked.connect(self.cleanPost)
        self.loginButton.clicked.connect(self.dcLogin)
        self.devInfoButton.clicked.connect(self.devInfoMsg)
        self.idBox.returnPressed.connect(self.focusEvent)
        self.pwBox.returnPressed.connect(self.loginButton.click)
        self.idBox.setFocus()
        self.commentGallList.currentIndexChanged.connect(self.commentGallSelectionChanged)
        self.postGallList.currentIndexChanged.connect(self.postGallSelectionChanged)

    def updateAlert(self):
        verParse = requests.get(
            "https://raw.githubusercontent.com/SerenityS/DCCleaner_GUI/master/ver.txt")
        if VER < float(verParse.text):
            result = QMessageBox.question(self, '???????????? ??????!',
                                          "?????? ???????????? ???????????? ???????????????????\n????????? ????????? ???????????? ????????? ???????????????.", QMessageBox.Yes |
                                          QMessageBox.No, QMessageBox.No)
            if result == QMessageBox.Yes:
                webbrowser.open("https://github.com/SerenityS/DCCleaner_GUI/releases")
                sys.exit()

    def closeEvent(self, event):
        result = QMessageBox.question(self, 'Are you sure to Exit?',
                                      "?????? ???????????? ?????????????????????????", QMessageBox.Yes |
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
        self.log.setText("????????? ??????????????????.")

    def dcLogin(self):
        dcid = self.idBox.text()
        dcpw = self.pwBox.text()

        if not dcid or not dcpw:
            alertMsgBox("??????!", "ID??? PW??? ??????????????????.")
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
            alertMsgBox("????????? ??????!", "ID??? PW??? ??????????????????.")
        else:
            self.loginStatus.setText("????????? ?????? : " + dcid)
            self.loginButton.setText("????????????")
            self.idBox.setDisabled(True)
            self.pwBox.setDisabled(True)
            if self.isSave:
                self.config.set('Account', 'id', dcid)
                self.config.set('Account', 'pw', dcpw)
                self.writeConf()
            self.getGallList(dcid)
            self.loginButton.clicked.disconnect()
            self.loginButton.clicked.connect(self.dcLogout)
            self.log.setText("???????????? ?????????????????????. - " + dcid)

    def dcLogout(self):
        initSession()
        self.commentGallList.clear()
        self.totalComment.setText("?????? ?????? : ")
        self.commentGallList.setDisabled(True)
        self.delCommentButton.setDisabled(True)
        self.postGallList.clear()
        self.totalPost.setText("?????? ????????? : ")
        self.postGallList.setDisabled(True)
        self.delPostButton.setDisabled(True)
        self.loginStatus.setText("????????? ?????? : Not Logged In")
        self.loginButton.setText("?????????")
        self.idBox.setDisabled(False)
        self.pwBox.setDisabled(False)
        self.loginButton.clicked.disconnect()
        self.loginButton.clicked.connect(self.dcLogin)
        self.log.setText("??????????????? ???????????????????????????.")

    def getGallList(self, dcid):
        # Clear Old Data
        self.commentGallNo.clear()
        self.commentGallList.clear()
        self.postGallNo.clear()
        self.postGallList.clear()

        # Prevent unexpected behavior when loading is not finished
        self.commentGallList.setDisabled(True)
        self.postGallList.setDisabled(True)

        # Get Gallog
        comment_gallog = sess.get("https://gallog.dcinside.com/" + dcid + "/comment")
        if comment_gallog.text == "":
            alertMsgBox("IP ?????? ???!", "IP ????????? ?????????????????????.\n?????? ????????? ?????? ??? ??????????????????.\n?????? ????????? ???????????? ???????????? ???????????????.")
            sys.exit()
        comment_gallog_parsed = BeautifulSoup(comment_gallog.text, "lxml")

        # Parse optionbox for Listing All Galleries
        comment_option_box = comment_gallog_parsed.find_all(class_="option_box")[1]
        comment_option_box = comment_option_box.find_all("li")

        comment_gall_list = ["?????? ?????????"]
        self.commentGallNo += [dcid + "/comment"]
        for gall in range(1, len(comment_option_box)):
            comment_gall_list += [comment_option_box[gall].text]
            self.commentGallNo += [comment_option_box[gall]['onclick'][15:-1]]

        # Get Gallog
        post_gallog = sess.get("https://gallog.dcinside.com/" + dcid + "/posting")
        post_gallog_parsed = BeautifulSoup(post_gallog.text, "lxml")

        # Parse optionbox for Listing All Galleries
        post_option_box = post_gallog_parsed.find_all(class_="option_box")[1]
        post_option_box = post_option_box.find_all("li")

        post_gall_list = ["?????? ?????????"]
        self.postGallNo += [dcid + "/posting"]
        for gall in range(1, len(post_option_box)):
            post_gall_list += [post_option_box[gall].text]
            self.postGallNo += [post_option_box[gall]['onclick'][15:-1]]

        # Add Gallary Title to QComboBox
        for gallTitle in comment_gall_list:
            self.commentGallList.addItem(gallTitle)
        self.commentGallList.setDisabled(False)
        self.delCommentButton.setDisabled(False)

        for gallTitle in post_gall_list:
            self.postGallList.addItem(gallTitle)
        self.postGallList.setDisabled(False)
        self.delPostButton.setDisabled(False)

    def commentGallSelectionChanged(self):
        idx = self.commentGallList.currentIndex()

        if idx != -1:
            gall_url = self.commentGallNo[idx]

            num = self.getGallTotalNum(gall_url, idx)
            if num == '0':
                self.delCommentButton.setDisabled(True)
            else:
                self.delCommentButton.setDisabled(False)
            self.totalComment.setText("?????? ?????? : %s???" % num)

    def postGallSelectionChanged(self):
        idx = self.postGallList.currentIndex()

        if idx != -1:
            gall_url = self.postGallNo[idx]

            num = self.getGallTotalNum(gall_url, idx)
            if num == '0':
                self.delPostButton.setDisabled(True)
            else:
                self.delPostButton.setDisabled(False)
            self.totalPost.setText("?????? ????????? : %s???" % num)

    def getGallTotalNum(self, gall_url, idx):
        # Get Gallog
        gallog = sess.get("https://gallog.dcinside.com/" + gall_url)
        if gallog.text == "":
            alertMsgBox("IP ?????? ???!", "IP ????????? ?????????????????????.\n?????? ????????? ?????? ??? ??????????????????.\n?????? ????????? ???????????? ???????????? ???????????????.")
            sys.exit()
        gallog_parsed = lxml.html.fromstring(gallog.text)

        # Get num
        if idx == 0:
            num = gallog_parsed.xpath('//*[@id="container"]/article/div/section/div[1]/header/div/div[1]/button[1]/span')[0].text.replace(",", "")
        else:
            num = gallog_parsed.xpath('//*[@id="container"]/article/div/section/div[1]/header/div/h2/span[3]')[0].text.replace(",", "")
        return (re.findall("\d+", num)[0])


    # JS For decoding Service Code
    def decodeServiceCode(self, _svc, _r):
        _r_key = 'yL/M=zNa0bcPQdReSfTgUhViWjXkYIZmnpo+qArOBs1Ct2D3uE4Fv5G6wHl78xJ9K'
        _r = re.sub('[^A-Za-z0-9+/=]', '', _r)

        tmp = ''
        i = 0
        for a in [_r[i * 4:(i + 1) * 4] for i in range((len(_r) + 3) // 4)]:
            t, f, d, h = [_r_key.find(x) for x in a]
            tmp += chr(t << 2 | f >> 4)
            if d != 64:
                tmp += chr((15 & f) << 4 | (d >> 2))
            if h != 64:
                tmp += chr((3 & d) << 6 | h)
        _r = str(int(tmp[0]) + 4) + tmp[1:]
        if int(tmp[0]) > 5:
            _r = str(int(tmp[0]) - 5) + tmp[1:]

        _r = [float(x) for x in _r.split(',')]
        t = ''
        for i in range(len(_r)):
            t += chr(int(2 * (_r[i] - i - 1) / (13 - i - 1)))
        return _svc[0:len(_svc) - 10] + t

    def cleanComment(self):
        self.delProcess = True

        self.delCommentButton.setText("?????? ??????")
        self.delCommentButton.clicked.disconnect()
        self.delCommentButton.clicked.connect(self.cancelCommentDelProcess)
        self.commentGallList.setDisabled(True)
        self.delPostButton.setDisabled(True)
        self.loginButton.setDisabled(True)

        dcid = self.idBox.text()
        idx = self.commentGallList.currentIndex()
        gall_url = self.commentGallNo[idx]

        self.cleanCommentThread = (threading.Thread(target=self.cleanProcess, args=(dcid, idx, gall_url)))
        self.cleanCommentThread.start()

    def cleanPost(self):
        self.delProcess = True

        self.delPostButton.setText("?????? ??????")
        self.delPostButton.clicked.disconnect()
        self.delPostButton.clicked.connect(self.cancelPostDelProcess)
        self.postGallList.setDisabled(True)
        self.delCommentButton.setDisabled(True)
        self.loginButton.setDisabled(True)

        dcid = self.idBox.text()
        idx = self.commentGallList.currentIndex()
        gall_url = self.postGallNo[idx]

        self.cleanPostThread = (threading.Thread(target=self.cleanProcess, args=(dcid, idx, gall_url)))
        self.cleanPostThread.start()

    def cleanProcess(self, dcid, idx, gall_url):
        while self.delProcess:
            # DELETE Headers
            DELETE_REQ_HEADERS = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "gallog.dcinside.com",
                "Origin": "https://gallog.dcinside.com",
                "Referer": "https://gallog.dcinside.com/" + gall_url,
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "X-Requested-With": "XMLHttpRequest"
            }

            # Parse Gallog
            gallog = sess.get("https://gallog.dcinside.com/" + gall_url)
            if gallog.text == "":
                alertMsgBox("IP ?????? ???!", "IP ????????? ?????????????????????.\n?????? ????????? ?????? ??? ??????????????????.\n?????? ????????? ???????????? ???????????? ???????????????.")
                sys.exit()
            gallog_parsed = lxml.html.fromstring(gallog.text)

            try:
                # Refresh Total Num
                if idx == 0:
                    num = \
                    gallog_parsed.xpath('//*[@id="container"]/article/div/section/div[1]/header/div/div[1]/button[1]/span')[
                        0].text.replace(",", "")
                else:
                    num = gallog_parsed.xpath('//*[@id="container"]/article/div/section/div[1]/header/div/h2/span[3]')[
                        0].text.replace(",", "")
                num = re.findall("\d+", num)[0]

                if "/comment" in gall_url:
                    self.totalComment.setText("?????? ?????? : %s???" % num)
                else:
                    self.totalPost.setText("?????? ????????? : %s???" % num)

                # Get Values for Service Code
                hidden_r = gallog_parsed.xpath('//*[@id="container"]/article/div/section/script[2]')[0].text.strip()
                hidden_r = re.findall("_d\('([\w\0-Z]*)'\)", hidden_r)[0]
                hidden_svc_code = gallog_parsed.xpath('//*[@id="container"]/article/div/section/div[1]/input')[0].get("value")

                # Generate Service Code
                svc_code = self.decodeServiceCode(hidden_svc_code, hidden_r)

                # Get Information
                gall = gallog_parsed.xpath('//*[@id="container"]/article/div/section/div[1]/div/ul/li[1]/div[3]/span/a')[0].text
                no = gallog_parsed.xpath('//*[@id="container"]/article/div/section/div[1]/div/ul/li[1]')[0].get(
                        "data-no")
            except IndexError:
                if "/comment" in gall_url:
                    self.commentGallList.setCurrentIndex(0)
                    self.cancelCommentDelProcess()
                else:
                    self.postGallList.setCurrentIndex(0)
                    self.cancelPostDelProcess()
                self.log.setText("????????? ?????????????????????.")
                self.getGallList(dcid)
                self.commentGallList.setCurrentIndex(0)
                self.postGallList.setCurrentIndex(0)
                return

            delete_url = "https://gallog.dcinside.com/" + dcid + "/ajax/log_list_ajax/delete"

            DELETE_REQ_DATA = {
                "ci_t": sess.cookies['ci_c'],
                "no": no,
                "service_code": svc_code
            }

            # POST & GET Result
            delete_result = sess.post(delete_url, data=DELETE_REQ_DATA, headers=DELETE_REQ_HEADERS)
            result = json.loads(delete_result.text)['result']

            # IF reCaptcha
            if result == "captcha":
                alertMsgBox("????????? ??????!", "????????? ????????? ?????????????????????.<br><a href='https://gallog.dcinside.com/%s'>?????????</a>?????? ???????????? ?????? ???????????? ???????????? ??????????????????." % gall_url)
                if "/comment" in gall_url:
                    self.cancelCommentDelProcess()
                else:
                    self.cancelPostDelProcess()
                break

            if result == "fail":
                if "/comment" in gall_url:
                    self.cancelCommentDelProcess()
                else:
                    self.cancelPostDelProcess()
                break
                alertMsgBox("?????? ??????!",
                            "?????? ?????? ????????? ????????? ?????????????????????.<br><a href='https://gallog.dcinside.com/%s'>?????????</a>?????? ???????????? 1~2?????? ?????? ?????????????????????." % gall_url)

                self.log.setText(f'GallName : {gall}\nDataNo : {no}\nResult : {result}')

            time.sleep(1)

    def cancelCommentDelProcess(self):
        self.delProcess = False

        self.commentGallSelectionChanged()

        self.delCommentButton.setText("?????? ??????")
        self.delCommentButton.clicked.disconnect()
        self.delCommentButton.clicked.connect(self.cleanComment)
        self.commentGallList.setDisabled(False)
        self.delPostButton.setDisabled(False)
        self.loginButton.setDisabled(False)

    def cancelPostDelProcess(self):
        self.delProcess = False

        self.postGallSelectionChanged()

        self.delPostButton.setText("????????? ??????")
        self.delPostButton.clicked.disconnect()
        self.delPostButton.clicked.connect(self.cleanPost)
        self.postGallList.setDisabled(False)
        self.delCommentButton.setDisabled(False)
        self.loginButton.setDisabled(False)

    def mgrAccount(self):
        if self.isSaveAccount.isChecked():
            self.isSave = True
            self.config.set("Settings", "isSaveAccount", "True")
            self.writeConf()
            self.log.setText("????????? ????????? ???????????????.")
        else:
            self.isSave = False
            self.config.set("Settings", "isSaveAccount", "False")
            self.config.set('Account', 'id', "null")
            self.config.set('Account', 'pw', "null")
            self.writeConf()
            self.log.setText("????????? ????????? ???????????? ????????????.")

    def writeConf(self):
        with open('settings.conf', 'w') as conf:
            self.config.write(conf)

    def devInfoMsg(self):
        alertMsgBox("????????? ??????", "DCCleaner V%.1f<br>Dev : qwertycvb(SerenityS)<br>E-Mail : jins4218@gmail.com<br>Github : <a href='https://github.com/SerenityS'>https://github.com/SerenityS</a><br><br><a href='https://github.com/augustapple/ThanosCleaner'>Inspired by ThanosCleaner</a>" % VER)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    apply_stylesheet(app, theme='dark_teal.xml')
    window.show()
    app.exec_()
