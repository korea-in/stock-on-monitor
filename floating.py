import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMenu
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QFont, QColor

from core.fetcher import fetch_price
from core.constants import APP_NAME


class FloatingWidget(QWidget):
    def __init__(self, data_dir, cfg, stocks):
        super().__init__()
        self.data_dir  = data_dir
        self.cfg       = cfg
        self.stocks    = [s for s in stocks if s.get("active", True)]
        self._drag_pos = QPoint()

        self._build_ui()
        self._apply_always_on_top()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_prices)
        self.timer.start(self.cfg.get("interval_ms", 10000))
        self.update_prices()

    # ── 항상 위 설정 적용 ────────────────────────────
    def _apply_always_on_top(self):
        always_on_top = self.cfg.get("always_on_top", True)
        flags = Qt.FramelessWindowHint | Qt.Tool
        if always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.show()

    # ── UI 구성 ──────────────────────────────────────
    def _build_ui(self):
        # 최초 1회 윈도우 플래그 설정
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.card = QWidget(self)
        self.card.setObjectName("card")
        self._apply_card_style()

        self.stock_layout = QVBoxLayout()
        self.stock_layout.setContentsMargins(12, 8, 12, 8)
        self.stock_layout.setSpacing(4)

        self._rebuild_rows()

        self.card.setLayout(self.stock_layout)
        outer.addWidget(self.card)
        self.setLayout(outer)

    def _apply_card_style(self):
        bg    = self.cfg.get("bg_color", "#111111")
        alpha = self.cfg.get("bg_alpha", 210)
        c     = QColor(bg)
        self.card.setStyleSheet(f"""
            QWidget#card {{
                background-color: rgba({c.red()},{c.green()},{c.blue()},{alpha});
                border-radius: 8px;
            }}
        """)

    def _rebuild_rows(self):
        """종목 수만큼 행 위젯 생성 + 합산 행 추가"""
        while self.stock_layout.count():
            item = self.stock_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.row_widgets = []

        # 종목이 없는 경우 안내 메시지 표시
        if not self.stocks:
            empty_widget = QWidget()
            empty_widget.setStyleSheet("background: transparent;")
            empty_layout = QVBoxLayout()
            empty_layout.setContentsMargins(12, 20, 12, 20)
            empty_layout.setSpacing(0)

            lbl_guide = QLabel("우클릭하여 종목을 설정해주세요.")
            lbl_guide.setFont(QFont("Malgun Gothic", self.cfg.get("font_size", 9)))
            lbl_guide.setStyleSheet(f"color:{self.cfg.get('font_color', '#aaaaaa')}; background:transparent;")
            lbl_guide.setAlignment(Qt.AlignCenter)

            empty_layout.addWidget(lbl_guide)
            empty_widget.setLayout(empty_layout)
            self.stock_layout.addWidget(empty_widget)
            return

        for i, stock in enumerate(self.stocks):
            if i > 0:
                line = QWidget()
                line.setFixedHeight(1)
                line.setStyleSheet("background-color: rgba(255,255,255,15);")
                self.stock_layout.addWidget(line)

            row_widget = QWidget()
            row_widget.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            fs = self.cfg.get("font_size", 9)
            fc = self.cfg.get("font_color", "#aaaaaa")

            def make_lbl(size, bold=False, color=None):
                l = QLabel("--")
                l.setFont(QFont("Malgun Gothic", fs,
                                QFont.Bold if bold else QFont.Normal))
                l.setStyleSheet(f"color:{color or fc}; background:transparent;")
                l.setMinimumWidth(45)
                return l

            def sep():
                s = QLabel("|")
                s.setFont(QFont("Malgun Gothic", fs))
                s.setStyleSheet("color:#3a3a3a; background:transparent;")
                s.setFixedWidth(12)
                return s

            lbls = {}

            if self.cfg.get("show_name"):
                lbls["name"] = make_lbl(fs - 1, color="#666666")
                row_layout.addWidget(lbls["name"])
                row_layout.addWidget(sep())

            if self.cfg.get("show_code"):
                lbls["code"] = make_lbl(fs - 1, color="#666666")
                row_layout.addWidget(lbls["code"])
                row_layout.addWidget(sep())

            lbls["price"] = make_lbl(fs, bold=True)
            row_layout.addWidget(lbls["price"])

            if self.cfg.get("show_change_amt"):
                row_layout.addWidget(sep())
                lbls["change_amt"] = make_lbl(fs - 1)
                row_layout.addWidget(lbls["change_amt"])

            if self.cfg.get("show_change_pct"):
                row_layout.addWidget(sep())
                lbls["change_pct"] = make_lbl(fs - 1)
                row_layout.addWidget(lbls["change_pct"])

            if self.cfg.get("show_profit_amt"):
                row_layout.addWidget(sep())
                lbls["profit_amt"] = make_lbl(fs - 1)
                row_layout.addWidget(lbls["profit_amt"])

            if self.cfg.get("show_profit_pct"):
                row_layout.addWidget(sep())
                lbls["profit_pct"] = make_lbl(fs - 1)
                row_layout.addWidget(lbls["profit_pct"])

            if self.cfg.get("show_total"):
                row_layout.addWidget(sep())
                lbls["total"] = make_lbl(fs - 1)
                row_layout.addWidget(lbls["total"])

            row_layout.addStretch()
            row_widget.setLayout(row_layout)
            self.stock_layout.addWidget(row_widget)
            self.row_widgets.append(lbls)

        # ── 합산 총 자산 행 ──────────────────────────
        if self.cfg.get("show_summary"):
            # 구분선
            line = QWidget()
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: rgba(255,255,255,30);")
            self.stock_layout.addWidget(line)

            fs = self.cfg.get("font_size", 9)
            fc = self.cfg.get("font_color", "#aaaaaa")

            summary_widget = QWidget()
            summary_widget.setStyleSheet("background: transparent;")
            summary_layout = QHBoxLayout()
            summary_layout.setContentsMargins(0, 2, 0, 0)
            summary_layout.setSpacing(10)

            def make_s(bold=False, color=None):
                l = QLabel("--")
                l.setFont(QFont("Malgun Gothic", fs,
                                QFont.Bold if bold else QFont.Normal))
                l.setStyleSheet(f"color:{color or fc}; background:transparent;")
                l.setMinimumWidth(80)
                return l

            def sep_s():
                s = QLabel("|")
                s.setFont(QFont("Malgun Gothic", fs))
                s.setStyleSheet("color:#3a3a3a; background:transparent;")
                s.setFixedWidth(12)
                return s

            self.lbl_sum_current = make_s(bold=True)
            summary_layout.addWidget(self.lbl_sum_current)
            summary_layout.addWidget(sep_s())
            self.lbl_sum_profit = make_s()
            summary_layout.addWidget(self.lbl_sum_profit)
            summary_layout.addStretch()
            summary_widget.setLayout(summary_layout)
            self.stock_layout.addWidget(summary_widget)
        else:
            self.lbl_sum_current = None
            self.lbl_sum_profit  = None

    # ── 가격 갱신 ────────────────────────────────────
    def update_prices(self):
        # 종목이 없으면 아무 것도 하지 않음
        if not self.stocks:
            self.card.adjustSize()
            self.resize(self.card.size())
            return

        total_buy     = 0  # 전체 매입총액
        total_current = 0  # 전체 현재총액

        for i, stock in enumerate(self.stocks):
            if i >= len(self.row_widgets):
                break

            lbls = self.row_widgets[i]
            data = fetch_price(stock["market"], stock["code"])

            if data is None:
                lbls["price"].setText("ERR")
                continue

            current    = data["current"]
            change     = data["change"]
            change_pct = data["change_pct"]
            buy_price  = stock["buy_price"]
            quantity   = stock["quantity"]
            profit_amt = (current - buy_price) * quantity
            profit_pct = (current - buy_price) / buy_price * 100
            total      = current * quantity

            # 합산 누적
            total_buy     += buy_price * quantity
            total_current += current * quantity

            arrow = "▲" if change > 0 else ("▼" if change < 0 else "─")
            c_col = self._change_color(change)
            p_col = self._change_color(profit_amt)
            fc    = self.cfg.get("font_color", "#aaaaaa")

            def s(color):
                return f"color:{color}; background:transparent;"

            if "name" in lbls:
                lbls["name"].setText(stock.get("name", ""))
                lbls["name"].setStyleSheet(s("#666666"))

            if "code" in lbls:
                lbls["code"].setText(stock.get("code", ""))
                lbls["code"].setStyleSheet(s("#666666"))

            lbls["price"].setText(f"{int(current):,}")
            lbls["price"].setStyleSheet(
                s(c_col if self.cfg.get("use_change_color") else fc)
            )

            if "change_amt" in lbls:
                lbls["change_amt"].setText(f"{arrow} {change:+,.0f}")
                lbls["change_amt"].setStyleSheet(s(c_col))

            if "change_pct" in lbls:
                lbls["change_pct"].setText(f"{arrow} {change_pct:+.2f}%")
                lbls["change_pct"].setStyleSheet(s(c_col))

            if "profit_amt" in lbls:
                lbls["profit_amt"].setText(
                    f"{'+' if profit_amt >= 0 else ''}{int(profit_amt):,}원"
                )
                lbls["profit_amt"].setStyleSheet(s(p_col))

            if "profit_pct" in lbls:
                lbls["profit_pct"].setText(f"{profit_pct:+.2f}%")
                lbls["profit_pct"].setStyleSheet(s(p_col))

            if "total" in lbls:
                lbls["total"].setText(f"{int(total):,}원")
                lbls["total"].setStyleSheet(s(fc))

        # ── 합산 총 자산 갱신 ────────────────────────
        if self.cfg.get("show_summary") and self.lbl_sum_current:
            total_profit = total_current - total_buy
            p_col = self._change_color(total_profit)
            fc    = self.cfg.get("font_color", "#aaaaaa")

            def s(color):
                return f"color:{color}; background:transparent;"

            self.lbl_sum_current.setText(f"총 자산 {int(total_current):,}")
            self.lbl_sum_current.setStyleSheet(
                s(p_col if self.cfg.get("use_change_color") else fc)
            )

            profit_pct = (total_profit / total_buy * 100) if total_buy > 0 else 0
            self.lbl_sum_profit.setText(
                f"총 손익 {('+' if total_profit >= 0 else '')}{int(total_profit):,}  ({profit_pct:+.2f}%)"
            )
            self.lbl_sum_profit.setStyleSheet(s(p_col))

        self.card.adjustSize()
        self.resize(self.card.size())

    def _change_color(self, value) -> str:
        if not self.cfg.get("use_change_color", True):
            return self.cfg.get("font_color", "#aaaaaa")
        invert = self.cfg.get("invert_color", False)
        if value > 0:   return "#4FC3F7" if invert else "#FF5C5C"
        elif value < 0: return "#FF5C5C" if invert else "#4FC3F7"
        return "#777777"

    def apply_settings(self, cfg):
        self.cfg = cfg
        self._apply_card_style()
        self._apply_always_on_top()
        self._rebuild_rows()
        self.update_prices()

    def apply_stocks(self, stocks):
        self.stocks = [s for s in stocks if s.get("active", True)]
        self._rebuild_rows()
        self.update_prices()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #1a1a1a; color: #aaaaaa;
                border: 1px solid #333; padding: 4px;
            }
            QMenu::item { padding: 6px 20px; border-radius: 3px; }
            QMenu::item:selected { background: #2a2a2a; color: #cccccc; }
            QMenu::separator { background: #333; height: 1px; margin: 3px 0; }
        """)
        menu.addAction("ℹ  정보",         self._open_info)
        menu.addAction("📖  사용법",      self._open_usage)
        menu.addAction("📜  오픈소스 라이선스", self._open_license)
        menu.addSeparator()
        menu.addAction("📈  종목설정",    self._open_stocks)
        menu.addAction("⚙  환경설정",    self._open_settings)
        menu.addSeparator()
        menu.addAction("✕  종료하기",     QApplication.quit)
        menu.exec_(e.globalPos())

    def _open_license(self):
        from dialogs.license_dialog import LicenseDialog
        LicenseDialog(self).exec_()

    def _open_info(self):
        from dialogs.info_dialog import InfoDialog
        InfoDialog(self).exec_()

    def _open_usage(self):
        from dialogs.usage_dialog import UsageDialog
        UsageDialog(self).exec_()

    def _open_stocks(self):
        from dialogs.stock_dialog import StockDialog
        dlg = StockDialog(self.data_dir, self.stocks, self)
        dlg.stocks_updated.connect(self.apply_stocks)
        dlg.exec_()

    def _open_settings(self):
        from dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.data_dir, self.cfg, self)
        dlg.settings_updated.connect(self.apply_settings)
        dlg.exec_()
