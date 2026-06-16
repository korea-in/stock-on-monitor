import os
import sys
import shutil
import subprocess
from PyQt5.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog,
    QApplication, QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

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
QCheckBox {
    color: #aaaaaa; background: transparent; spacing: 6px;
}
QCheckBox::indicator {
    width: 15px; height: 15px;
    background: #1e1e1e;
    border: 1px solid #555;
    border-radius: 3px;
}
QPushButton {
    background: #2a2a2a; color: #aaaaaa;
    border: 1px solid #333; border-radius: 4px;
    padding: 6px 16px;
}
QPushButton:hover { background: #3a3a3a; color: #cccccc; }
"""


class CheckBox(QCheckBox):
    """체크 표시가 명확한 커스텀 체크박스"""
    def __init__(self, text):
        super().__init__(text)
        self._orig_text = text
        self._update_style()
        self.stateChanged.connect(lambda: self._update_style())

    def _update_style(self):
        if self.isChecked():
            self.setText("✔  " + self._orig_text)
            self.setStyleSheet("color: #cccccc; background: transparent; spacing: 8px;")
        else:
            self.setText(self._orig_text)
            self.setStyleSheet("color: #666666; background: transparent; spacing: 8px;")


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
            os.environ.get("PROGRAMFILES", "C:\\Program Files"), "StockFloat"
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
            self.edit_path.setText(d)

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
    """바로가기 옵션 페이지"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setSpacing(14)
        layout.setContentsMargins(40, 40, 40, 40)

        lbl = QLabel("바로가기 생성")
        lbl.setFont(QFont("Malgun Gothic", 11, QFont.Bold))
        lbl.setStyleSheet("color: #cccccc;")
        lbl.setAlignment(Qt.AlignCenter)

        lbl_desc = QLabel("생성할 바로가기 위치를 선택하세요.")
        lbl_desc.setFont(QFont("Malgun Gothic", 9))
        lbl_desc.setStyleSheet("color: #555;")
        lbl_desc.setAlignment(Qt.AlignCenter)

        self.chk_desktop   = CheckBox("바탕화면에 바로가기 생성")
        self.chk_startup   = CheckBox("시작 프로그램에 등록 (Windows 시작 시 자동 실행)")
        self.chk_startmenu = CheckBox("시작 메뉴에 바로가기 생성")

        self.chk_desktop.setChecked(True)
        self.chk_startup.setChecked(False)
        self.chk_startmenu.setChecked(False)

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
    if getattr(sys, "frozen", False):
        # 빌드된 installer.exe 실행 시 → 내장 리소스
        return os.path.join(sys._MEIPASS, "main.exe")
    else:
        # 개발 환경 → dist 폴더
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "dist", "main.exe"
        )


def _create_shortcuts(exe_path: str, opts: dict):
    """바로가기 생성 (pywin32 사용)"""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        targets = []

        if opts.get("desktop"):
            desktop = shell.SpecialFolders("Desktop")
            targets.append(os.path.join(desktop, "StockFloat.lnk"))

        if opts.get("startmenu"):
            start  = shell.SpecialFolders("Programs")
            folder = os.path.join(start, "StockFloat")
            os.makedirs(folder, exist_ok=True)
            targets.append(os.path.join(folder, "StockFloat.lnk"))

        if opts.get("startup"):
            startup = shell.SpecialFolders("Startup")
            targets.append(os.path.join(startup, "StockFloat.lnk"))

        for lnk_path in targets:
            shortcut = shell.CreateShortCut(lnk_path)
            shortcut.Targetpath       = exe_path
            shortcut.WorkingDirectory = os.path.dirname(exe_path)
            shortcut.Description      = "StockFloat 주식 플로팅 위젯"
            shortcut.save()

    except ImportError:
        pass
    except Exception:
        pass


def run_installer():
    app = QApplication.instance() or QApplication(sys.argv)
    wizard = InstallerWizard()

    if wizard.exec_() == QWizard.Accepted:
        install_dir = wizard.get_install_dir()
        opts        = wizard.get_shortcut_opts()

        # ── 내장된 main.exe 경로 확인 ───────────────
        main_src = _get_bundled_main_exe()
        if not os.path.exists(main_src):
            QMessageBox.critical(
                None, "오류",
                "내장된 main.exe를 찾을 수 없습니다.\n"
                "installer를 다시 빌드해주세요."
            )
            return

        # ── 설치 폴더에 main.exe 복사 ───────────────
        main_dst = os.path.join(install_dir, "main.exe")
        try:
            os.makedirs(install_dir, exist_ok=True)
            shutil.copy2(main_src, main_dst)
        except Exception as e:
            QMessageBox.critical(
                None, "복사 오류",
                f"파일 설치에 실패했습니다.\n{e}"
            )
            return

        # ── 기본 설정 / 종목 파일 생성 ──────────────
        # 데이터 파일은 main.exe 와 같은 폴더에 저장
        save_config(install_dir, default_config())
        save_stocks(install_dir, default_stocks())
        save_install_info(install_dir)

        # ── 바로가기 생성 ────────────────────────────
        _create_shortcuts(main_dst, opts)

        # ── 설치된 main.exe 즉시 실행 ───────────────
        try:
            subprocess.Popen(
                [main_dst],
                cwd=install_dir,        # 작업 디렉토리를 설치 폴더로 지정
                creationflags=0x00000008  # DETACHED_PROCESS: installer 종료 후에도 독립 실행
            )
        except Exception as e:
            QMessageBox.warning(
                None, "실행 오류",
                f"설치는 완료됐지만 자동 실행에 실패했습니다.\n"
                f"직접 실행해주세요: {main_dst}\n\n{e}"
            )

        # ── installer 종료 ───────────────────────────
        app.quit()


if __name__ == "__main__":
    run_installer()
