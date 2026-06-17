import os
import sys
import shutil
import subprocess
import urllib.request
import ssl
from PyQt5.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog,
    QApplication, QCheckBox, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QRect, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPainter, QColor, QPen

from core.config import save_install_info, save_config, save_stocks
from core.config import default_config, default_stocks
from core.constants import APP_NAME, APP_VERSION

STYLE = """
QWizard     { background: #111111; }
QWizardPage { background: #111111; }
QLabel      { color: #aaaaaa; background: transparent; }
QLineEdit {
    background: #1e1e1e; color: #cccccc;
    border: 1px solid #333; border-radius: 4px;
    padding: 4px 8px;
}
QPushButton {
    background: #2a2a2a; color: #aaaaaa;
    border: 1px solid #333; border-radius: 4px;
    padding: 6px 16px;
}
QPushButton:hover { background: #3a3a3a; color: #cccccc; }
"""


class CustomCheckBox(QCheckBox):
    """체크마크를 직접 그리는 커스텀 체크박스"""
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("color: #000000; background: transparent; spacing: 8px;")
        self.setMinimumHeight(24)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 체크박스 indicator 영역
        indicator_size = 16
        indicator_rect = QRect(0, (self.height() - indicator_size) // 2, indicator_size, indicator_size)

        # 배경색과 테두리
        if self.isChecked():
            painter.fillRect(indicator_rect, QColor("#000000"))
            painter.setPen(QPen(QColor("#cccccc"), 2))
        else:
            painter.fillRect(indicator_rect, QColor("#ffffff"))
            painter.setPen(QPen(QColor("#999999"), 2))

        painter.drawRect(indicator_rect)

        # 체크마크 그리기
        if self.isChecked():
            painter.setPen(QPen(QColor("#ffffff"), 2.5))
            painter.drawLine(4, 10, 7, 14)
            painter.drawLine(7, 14, 14, 4)

        # 텍스트 그리기
        text_rect = QRect(indicator_size + 8, 0, self.width() - indicator_size - 8, self.height())
        painter.setPen(QColor("#000000"))
        painter.drawText(text_rect, Qt.AlignVCenter, self.text())

        painter.end()





class WelcomePage(QWizardPage):
    """환영 페이지"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(40, 40, 40, 40)

        lbl_title = QLabel(f"✦  {APP_NAME}")
        lbl_title.setFont(QFont("Malgun Gothic", 22, QFont.Bold))
        lbl_title.setStyleSheet("color: #cccccc;")
        lbl_title.setAlignment(Qt.AlignCenter)

        lbl_ver = QLabel(f"Version {APP_VERSION}")
        lbl_ver.setFont(QFont("Malgun Gothic", 9))
        lbl_ver.setStyleSheet("color: #555;")
        lbl_ver.setAlignment(Qt.AlignCenter)

        lbl_desc = QLabel(
            "실시간 주식 플로팅 위젯에 오신 것을 환영합니다.\n"
            "다음 단계에서 설치 위치를 설정합니다."
        )
        lbl_desc.setFont(QFont("Malgun Gothic", 10))
        lbl_desc.setStyleSheet("color: #888;")
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_ver)
        layout.addSpacing(20)
        layout.addWidget(lbl_desc)
        layout.addStretch()
        self.setLayout(layout)


class DirPage(QWizardPage):
    """설치 경로 선택 페이지"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(40, 40, 40, 40)

        lbl = QLabel("설치 위치를 선택하세요")
        lbl.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        lbl.setStyleSheet("color: #cccccc;")
        lbl.setAlignment(Qt.AlignCenter)

        lbl_desc = QLabel(
            "프로그램과 데이터 파일이 해당 폴더에 설치됩니다.\n"
            "폴더가 없으면 자동으로 생성됩니다."
        )
        lbl_desc.setFont(QFont("Malgun Gothic", 9))
        lbl_desc.setStyleSheet("color: #555;")
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setWordWrap(True)

        row = QHBoxLayout()
        self.edit_path = QLineEdit()
        default_path = os.path.join(
            os.environ.get("PROGRAMFILES", "C:\\Program Files"), "StockOnMonitor"
        )
        self.edit_path.setText(default_path)
        self.edit_path.setFont(QFont("Malgun Gothic", 9))
        self.edit_path.textChanged.connect(lambda: self.completeChanged.emit())

        btn_browse = QPushButton("찾아보기")
        btn_browse.setFixedWidth(80)
        btn_browse.clicked.connect(self._browse)

        row.addWidget(self.edit_path)
        row.addWidget(btn_browse)

        self.registerField("install_dir", self.edit_path)

        layout.addStretch()
        layout.addWidget(lbl)
        layout.addWidget(lbl_desc)
        layout.addSpacing(16)
        layout.addLayout(row)
        layout.addStretch()
        self.setLayout(layout)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "폴더 선택", self.edit_path.text())
        if d:
            # 사용자가 루트 드라이브나 상위 폴더를 선택해도
            # 설치 폴더로 항상 'StockOnMonitor'를 붙여서 입력하도록 함
            norm = os.path.normpath(d)
            base = os.path.basename(norm)
            if base.lower() != "stockonmonitor":
                new_path = os.path.join(norm, "StockOnMonitor")
            else:
                new_path = norm
            self.edit_path.setText(new_path)

    def isComplete(self):
        return bool(self.edit_path.text().strip())

    def validatePage(self):
        path = self.edit_path.text().strip()
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            QMessageBox.warning(self, "오류", f"폴더를 생성할 수 없습니다.\n{e}")
            return False


class ShortcutPage(QWizardPage):
    """환경 설정 페이지"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setSpacing(14)
        layout.setContentsMargins(40, 40, 40, 40)

        lbl = QLabel("환경 설정")
        lbl.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        lbl.setStyleSheet("color: #cccccc;")
        lbl.setAlignment(Qt.AlignCenter)

        lbl_desc = QLabel("설정할 옵션을 선택하세요.")
        lbl_desc.setFont(QFont("Malgun Gothic", 9))
        lbl_desc.setStyleSheet("color: #555;")
        lbl_desc.setAlignment(Qt.AlignCenter)

        self.chk_desktop   = CustomCheckBox("바탕화면에 바로가기 생성")
        self.chk_startup   = CustomCheckBox("시작 프로그램에 등록 (Windows 시작 시 자동 실행)")
        self.chk_startmenu = CustomCheckBox("시작 메뉴에 바로가기 생성")

        self.chk_desktop.setChecked(True)
        self.chk_startup.setChecked(True)
        self.chk_startmenu.setChecked(True)

        self.registerField("shortcut_desktop",   self.chk_desktop)
        self.registerField("shortcut_startup",   self.chk_startup)
        self.registerField("shortcut_startmenu", self.chk_startmenu)

        layout.addStretch()
        layout.addWidget(lbl)
        layout.addWidget(lbl_desc)
        layout.addSpacing(20)
        layout.addWidget(self.chk_desktop)
        layout.addWidget(self.chk_startup)
        layout.addWidget(self.chk_startmenu)
        layout.addStretch()
        self.setLayout(layout)


class InstallerThread(QThread):
    """설치 작업을 수행하는 별도 스레드"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # (성공여부, 에러메시지)

    def __init__(self, install_dir, opts):
        super().__init__()
        self.install_dir = install_dir
        self.opts = opts

    def run(self):
        try:
            self.status.emit("설치 폴더 준비 중...")
            self.progress.emit(10)

            # ── GitHub에서 main.exe 다운로드 ─────────
            self.status.emit("main.exe 다운로드 중...")
            self.progress.emit(20)

            main_dst = os.path.join(self.install_dir, "main.exe")
            download_url = (
                "https://github.com/korea-in/stock-on-monitor/releases/latest/download/main.exe"
            )

            ok, err = _download_main_exe(download_url, main_dst)
            if not ok:
                self.finished.emit(False, f"다운로드 실패: {err}")
                return

            self.progress.emit(50)

            # ── 기본 설정 / 종목 파일 생성 ──────────────
            self.status.emit("설정 파일 생성 중...")
            self.progress.emit(60)

            save_config(self.install_dir, default_config())
            save_stocks(self.install_dir, default_stocks())
            save_install_info(self.install_dir)

            self.progress.emit(75)

            # ── 바로가기 생성 ────────────────────────────
            self.status.emit("바로가기 생성 중...")
            self.progress.emit(85)

            _create_shortcuts(main_dst, self.opts)

            self.progress.emit(95)

            # ── 설치 완료 ───────────────────────────────
            self.status.emit("설치 완료!")
            self.progress.emit(100)

            self.finished.emit(True, "")

        except Exception as e:
            self.finished.emit(False, str(e))


class ProgressPage(QWizardPage):
    """설치 진행 상황 페이지"""
    def __init__(self):
        super().__init__()
        self.setFinalPage(True)
        self.setCommitPage(True)

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(40, 40, 40, 40)

        lbl_title = QLabel("프로그램 설치 중...")
        lbl_title.setFont(QFont("Malgun Gothic", 14, QFont.Bold))
        lbl_title.setStyleSheet("color: #cccccc;")
        lbl_title.setAlignment(Qt.AlignCenter)

        self.lbl_status = QLabel("준비 중...")
        self.lbl_status.setFont(QFont("Malgun Gothic", 10))
        self.lbl_status.setStyleSheet("color: #aaaaaa;")
        self.lbl_status.setAlignment(Qt.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                border-radius: 4px;
                background: #1e1e1e;
                text-align: center;
                color: #aaaaaa;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 3px;
            }
        """)

        layout.addStretch()
        layout.addWidget(lbl_title)
        layout.addSpacing(12)
        layout.addWidget(self.lbl_status)
        layout.addSpacing(12)
        layout.addWidget(self.progress_bar)
        layout.addStretch()
        self.setLayout(layout)

        self.installer_thread = None

    def initializePage(self):
        """페이지가 나타날 때 설치 시작"""
        wizard = self.wizard()
        install_dir = wizard.field("install_dir")
        opts = {
            "desktop": wizard.field("shortcut_desktop"),
            "startup": wizard.field("shortcut_startup"),
            "startmenu": wizard.field("shortcut_startmenu"),
        }

        # 스레드 시작
        self.installer_thread = InstallerThread(install_dir, opts)
        self.installer_thread.progress.connect(self._on_progress)
        self.installer_thread.status.connect(self._on_status)
        self.installer_thread.finished.connect(self._on_finished)
        self.installer_thread.start()

    def _on_progress(self, value):
        self.progress_bar.setValue(value)

    def _on_status(self, message):
        self.lbl_status.setText(message)

    def _on_finished(self, success, error):
        if success:
            # 설치 완료 후 프로그램 실행
            wizard = self.wizard()
            install_dir = wizard.field("install_dir")
            main_exe = os.path.join(install_dir, "main.exe")

            try:
                subprocess.Popen(
                    [main_exe],
                    cwd=install_dir,
                    creationflags=0x00000008
                )
            except Exception as e:
                QMessageBox.warning(
                    self, "실행 오류",
                    f"설치는 완료됐지만 자동 실행에 실패했습니다.\n{e}"
                )

            # Wizard 종료
            self.wizard().accept()
        else:
            QMessageBox.critical(
                self, "설치 오류",
                f"설치 중 오류가 발생했습니다.\n{error}"
            )
            self.wizard().reject()


class FinishPage(QWizardPage):
    """완료 페이지"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        lbl = QLabel("✔  설치 준비가 완료되었습니다!")
        lbl.setFont(QFont("Malgun Gothic", 14, QFont.Bold))
        lbl.setStyleSheet("color: #aaaaaa;")
        lbl.setAlignment(Qt.AlignCenter)

        lbl2 = QLabel("완료 버튼을 누르면 설치 후 프로그램이 자동으로 실행됩니다.")
        lbl2.setFont(QFont("Malgun Gothic", 9))
        lbl2.setStyleSheet("color: #555;")
        lbl2.setWordWrap(True)
        lbl2.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(lbl)
        layout.addSpacing(12)
        layout.addWidget(lbl2)
        layout.addStretch()
        self.setLayout(layout)
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        lbl = QLabel("✔  설치 준비가 완료되었습니다!")
        lbl.setFont(QFont("Malgun Gothic", 14, QFont.Bold))
        lbl.setStyleSheet("color: #aaaaaa;")
        lbl.setAlignment(Qt.AlignCenter)

        lbl2 = QLabel("완료 버튼을 누르면 설치 후 프로그램이 자동으로 실행됩니다.")
        lbl2.setFont(QFont("Malgun Gothic", 9))
        lbl2.setStyleSheet("color: #555;")
        lbl2.setWordWrap(True)
        lbl2.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(lbl)
        layout.addSpacing(12)
        layout.addWidget(lbl2)
        layout.addStretch()
        self.setLayout(layout)


class InstallerWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} 설치")
        self.setFixedSize(480, 320)
        self.setStyleSheet(STYLE)
        self.setWizardStyle(QWizard.ModernStyle)

        self.setButtonText(QWizard.NextButton,   "다음 ›")
        self.setButtonText(QWizard.BackButton,   "‹ 이전")
        self.setButtonText(QWizard.FinishButton, "완료 및 실행")
        self.setButtonText(QWizard.CancelButton, "취소")

        self.addPage(WelcomePage())
        self.addPage(DirPage())
        self.addPage(ShortcutPage())
        self.addPage(ProgressPage())
        self.addPage(FinishPage())

    def get_install_dir(self) -> str:
        return self.field("install_dir")

    def get_shortcut_opts(self) -> dict:
        return {
            "desktop"  : self.field("shortcut_desktop"),
            "startup"  : self.field("shortcut_startup"),
            "startmenu": self.field("shortcut_startmenu"),
        }


def _get_bundled_main_exe() -> str:
    """
    PyInstaller로 내장된 main.exe 경로 반환
    빌드 시 _MEIPASS 임시폴더에 압축 해제됨
    개발 환경에서는 dist/main.exe 사용
    """
    # 이전에는 인클루드된 main.exe 경로를 반환했지만
    # 이제 installer는 내장 exe 대신 GitHub에서 main.exe를 다운로드합니다.
    return None


def _download_main_exe(url: str, dst_path: str, timeout: int = 30) -> (bool, str):
    """
    URL에서 바이너리 파일을 다운로드해 `dst_path`에 저장합니다.
    반환: (성공여부, 오류메시지 또는 None)
    """
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(url, context=ctx, timeout=timeout) as resp:
            code = resp.getcode()
            if code != 200:
                return False, f"HTTP {code}"
            # 스트리밍으로 저장
            with open(dst_path, "wb") as f:
                shutil.copyfileobj(resp, f)
        return True, None
    except Exception as e:
        return False, str(e)


def _create_shortcuts(exe_path: str, opts: dict):
    """바로가기 생성 (pywin32 사용)"""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        targets = []

        if opts.get("desktop"):
            desktop = shell.SpecialFolders("Desktop")
            targets.append(os.path.join(desktop, "StockOnMonitor.lnk"))

        if opts.get("startmenu"):
            start  = shell.SpecialFolders("Programs")
            folder = os.path.join(start, "StockOnMonitor")
            os.makedirs(folder, exist_ok=True)
            targets.append(os.path.join(folder, "StockOnMonitor.lnk"))

        if opts.get("startup"):
            startup = shell.SpecialFolders("Startup")
            targets.append(os.path.join(startup, "StockOnMonitor.lnk"))

        for lnk_path in targets:
            shortcut = shell.CreateShortCut(lnk_path)
            shortcut.Targetpath       = exe_path
            shortcut.WorkingDirectory = os.path.dirname(exe_path)
            shortcut.Description      = "StockOnMonitor 주식 플로팅 위젯"
            shortcut.save()

    except ImportError:
        pass
    except Exception:
        pass


def run_installer():
    app = QApplication.instance() or QApplication(sys.argv)
    wizard = InstallerWizard()
    wizard.exec_()


if __name__ == "__main__":
    run_installer()

