import sys
import os
from PyQt5.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 다이얼로그 닫아도 종료 안 됨

    # ── 설치 여부 확인 ──────────────────────────────────
    from core.config import get_install_info, load_config, load_stocks

    install = get_install_info()

    if install is None:
        # 최초 실행: 설치 마법사
        from installer import run_installer
        data_dir = run_installer()
        if data_dir is None:
            # 사용자가 취소
            sys.exit(0)
    else:
        data_dir = install["data_dir"]

    # ── 설정 / 종목 로드 ────────────────────────────────
    cfg    = load_config(data_dir)
    stocks = load_stocks(data_dir)

    # ── 플로팅 위젯 실행 ────────────────────────────────
    from floating import FloatingWidget
    widget = FloatingWidget(data_dir, cfg, stocks)
    widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
