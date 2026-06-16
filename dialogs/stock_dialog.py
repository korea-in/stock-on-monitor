from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from core.config import save_stocks
from core.fetcher import search_stocks

STYLE = """
QDialog    { background: #1a1a1a; }
QWidget    { background: #1a1a1a; }
QLabel     { color: #aaaaaa; background: transparent; }
QLineEdit, QComboBox {
    background: #2a2a2a; color: #aaaaaa;
    border: 1px solid #333; border-radius: 4px; padding: 4px 8px;
}
QComboBox::drop-down  { border: none; }
QComboBox QAbstractItemView {
    background: #2a2a2a; color: #aaaaaa; border: 1px solid #333;
}
QPushButton {
    background: #2a2a2a; color: #aaaaaa;
    border: 1px solid #333; border-radius: 4px; padding: 5px 12px;
}
QPushButton:hover  { background: #3a3a3a; color: #cccccc; }
QPushButton#btn_del { background: #2a1a1a; border-color: #4a2a2a; }
QPushButton#btn_del:hover { background: #3a2a2a; color: #cccccc; }
QPushButton#btn_del:disabled { background: #1a1a1a; color: #444444; border-color: #2a2a2a; }
QTableWidget {
    background: #1a1a1a; color: #aaaaaa;
    border: 1px solid #2a2a2a; gridline-color: #2a2a2a;
}
QTableWidget::item { background: #1a1a1a; color: #aaaaaa; }
QTableWidget::item:selected { background: #2a2a3a; color: #cccccc; }
QHeaderView::section {
    background: #2a2a2a; color: #888888;
    border: none;
    border-right: 1px solid #333;
    border-bottom: 1px solid #333;
    padding: 4px;
}
QTableCornerButton::section {
    background: #2a2a2a; border: none;
}
QScrollBar:vertical {
    background: #1a1a1a; width: 8px; border: none;
}
QScrollBar::handle:vertical {
    background: #3a3a3a; border-radius: 4px; min-height: 20px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0px; }
"""


class SearchThread(QThread):
    """별도 스레드에서 종목 검색"""
    result = pyqtSignal(list)  # 결과 리스트 반환

    def __init__(self, market, query):
        super().__init__()
        self.market = market
        self.query  = query

    def run(self):
        try:
            results = search_stocks(self.query, self.market)
            self.result.emit(results)
        except Exception:
            self.result.emit([])


class StockDialog(QDialog):
    stocks_updated = pyqtSignal(list)

    def __init__(self, data_dir, stocks, parent=None):
        super().__init__(parent)
        self.data_dir       = data_dir
        self.stocks         = [s.copy() for s in stocks]
        self._search_result = None  # 검색 결과에서 선택된 종목

        self.setWindowTitle("종목 설정")
        self.setMinimumSize(640, 500)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        main = QVBoxLayout()
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(10)

        # ── 검색/추가 영역 ────────────────────────────
        main.addWidget(self._section_label("▸ 종목 검색 및 추가"))

        search_row = QHBoxLayout()
        self.cmb_market = QComboBox()
        self.cmb_market.addItems(["한국(KR)", "미국(US)"])
        self.cmb_market.setFixedWidth(90)

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("종목코드 또는 종목명 입력 (예: 005930, 삼성전자)")
        self.edit_search.returnPressed.connect(self._search)

        btn_search = QPushButton("조회")
        btn_search.setFixedWidth(60)
        btn_search.clicked.connect(self._search)

        search_row.addWidget(self.cmb_market)
        search_row.addWidget(self.edit_search)
        search_row.addWidget(btn_search)
        main.addLayout(search_row)

        # 검색 결과 테이블 (3컬럼: 코드 / 종목명 / 현재가)
        self.tbl_search = QTableWidget(0, 3)
        self.tbl_search.setHorizontalHeaderLabels(["코드", "종목명", "현재가"])
        self.tbl_search.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_search.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_search.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_search.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_search.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_search.setFixedHeight(110)
        self.tbl_search.itemClicked.connect(self._on_search_row_clicked)
        main.addWidget(self.tbl_search)

        # 매수 정보 입력
        input_row = QHBoxLayout()
        self.edit_buy = QLineEdit()
        self.edit_buy.setPlaceholderText("매수단가")
        self.edit_qty = QLineEdit()
        self.edit_qty.setPlaceholderText("보유수량")
        self.btn_add = QPushButton("추가")
        self.btn_add.setFixedWidth(60)
        self.btn_add.clicked.connect(self._add_stock)

        input_row.addWidget(QLabel("매수단가"))
        input_row.addWidget(self.edit_buy)
        input_row.addWidget(QLabel("수량"))
        input_row.addWidget(self.edit_qty)
        input_row.addWidget(self.btn_add)
        main.addLayout(input_row)

        # ── 저장된 종목 ───────────────────────────────
        main.addWidget(self._section_label("▸ 저장된 종목"))

        self.tbl_stocks = QTableWidget(0, 5)
        self.tbl_stocks.setHorizontalHeaderLabels(
            ["시장", "코드", "종목명", "매수단가", "수량"]
        )
        self.tbl_stocks.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_stocks.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_stocks.setEditTriggers(QAbstractItemView.NoEditTriggers)
        main.addWidget(self.tbl_stocks)

        # 하단 버튼
        btn_row = QHBoxLayout()
        self.btn_del = QPushButton("선택 삭제")
        self.btn_del.setObjectName("btn_del")
        self.btn_del.clicked.connect(self._delete_selected)

        btn_save  = QPushButton("저장하기")
        btn_save.clicked.connect(self._save)
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.close)

        btn_row.addWidget(self.btn_del)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_close)
        main.addLayout(btn_row)

        self.setLayout(main)
        self._update_del_btn()

    def _section_label(self, text):
        l = QLabel(text)
        l.setFont(QFont("Malgun Gothic", 9, QFont.Bold))
        l.setStyleSheet("color: #666666; background: transparent;")
        return l

    # ── 검색 ─────────────────────────────────────────
    def _search(self):
        query  = self.edit_search.text().strip()
        market = "KR" if self.cmb_market.currentIndex() == 0 else "US"
        if not query:
            return

        # 조회 중 표시
        self.tbl_search.setRowCount(1)
        self.tbl_search.setSpan(0, 0, 1, 3)
        item = QTableWidgetItem("조회 중...")
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(QColor("#666666"))
        item.setBackground(QColor("#1a1a1a"))
        self.tbl_search.setItem(0, 0, item)

        self._search_thread = SearchThread(market, query)
        self._search_thread.result.connect(self._on_search_result)
        self._search_thread.start()

    def _on_search_result(self, results: list):
        # span 초기화
        self.tbl_search.setSpan(0, 0, 1, 1)
        self.tbl_search.clearContents()

        if not results:
            # 결과 없음 → 1행 colspan 메시지
            self.tbl_search.setRowCount(1)
            self.tbl_search.setSpan(0, 0, 1, 3)
            item = QTableWidgetItem("존재하지 않는 종목 코드입니다. 다시 확인해주세요.")
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor("#666666"))
            item.setBackground(QColor("#1a1a1a"))
            self.tbl_search.setItem(0, 0, item)
            self._search_result = None
            return

        self.tbl_search.setRowCount(len(results))
        for i, r in enumerate(results):
            for col, val in enumerate([
                r["code"],
                r["name"],
                f"{r['price']:,.0f}",
            ]):
                item = QTableWidgetItem(val)
                item.setBackground(QColor("#1a1a1a"))
                item.setForeground(QColor("#aaaaaa"))
                self.tbl_search.setItem(i, col, item)

        # 결과 1건이면 자동 선택
        if len(results) == 1:
            self._search_result = results[0]
            self.tbl_search.selectRow(0)

    def _on_search_row_clicked(self, item):
        """검색 결과 행 클릭 시 해당 종목 선택"""
        row = item.row()
        # span 중인 행(조회중/결과없음)은 무시
        if self.tbl_search.columnSpan(row, 0) > 1:
            return
        code_item = self.tbl_search.item(row, 0)
        name_item = self.tbl_search.item(row, 1)
        price_item = self.tbl_search.item(row, 2)
        if not code_item:
            return
        market = "KR" if self.cmb_market.currentIndex() == 0 else "US"
        try:
            price = float(price_item.text().replace(",", ""))
        except Exception:
            price = 0.0
        self._search_result = {
            "code"  : code_item.text(),
            "name"  : name_item.text() if name_item else "",
            "market": market,
            "price" : price,
        }

    # ── 종목 추가 ─────────────────────────────────────
    def _add_stock(self):
        if not self._search_result:
            QMessageBox.warning(self, "알림", "먼저 종목을 조회하고 선택하세요.")
            return
        try:
            buy_price = float(self.edit_buy.text().replace(",", ""))
            quantity  = int(self.edit_qty.text().replace(",", ""))
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "매수단가와 수량을 올바르게 입력하세요.")
            return
        if buy_price <= 0 or quantity <= 0:
            QMessageBox.warning(self, "입력 오류", "매수단가와 수량은 0보다 커야 합니다.")
            return

        market = "KR" if self.cmb_market.currentIndex() == 0 else "US"
        self.stocks.append({
            "market"   : market,
            "code"     : self._search_result["code"],
            "name"     : self._search_result["name"],
            "buy_price": buy_price,
            "quantity" : quantity,
            "active"   : True,
        })
        self._search_result = None
        self.edit_buy.clear()
        self.edit_qty.clear()
        self._refresh_table()
        self._update_del_btn()

    # ── 종목 삭제 ─────────────────────────────────────
    def _delete_selected(self):
        # 1건 이하 삭제 방어
        if len(self.stocks) <= 1:
            QMessageBox.warning(self, "삭제 불가", "최소 1개 종목은 유지해야 합니다.")
            return

        rows = sorted(
            set(i.row() for i in self.tbl_stocks.selectedItems()), reverse=True
        )
        if not rows:
            QMessageBox.warning(self, "알림", "삭제할 종목을 선택하세요.")
            return

        # 삭제 후 0건이 되는 경우 방어
        if len(self.stocks) - len(rows) < 1:
            QMessageBox.warning(self, "삭제 불가", "최소 1개 종목은 유지해야 합니다.")
            return

        for r in rows:
            del self.stocks[r]
        self._refresh_table()
        self._update_del_btn()

    def _update_del_btn(self):
        """종목이 1건이면 삭제 버튼 비활성화"""
        self.btn_del.setEnabled(len(self.stocks) > 1)

    # ── 테이블 갱신 ───────────────────────────────────
    def _refresh_table(self):
        self.tbl_stocks.setRowCount(len(self.stocks))
        for i, s in enumerate(self.stocks):
            for col, val in enumerate([
                s["market"], s["code"], s["name"],
                f"{s['buy_price']:,.0f}", str(s["quantity"])
            ]):
                item = QTableWidgetItem(val)
                item.setBackground(QColor("#1a1a1a"))
                item.setForeground(QColor("#aaaaaa"))
                self.tbl_stocks.setItem(i, col, item)

    def _save(self):
        save_stocks(self.data_dir, self.stocks)
        self.stocks_updated.emit(self.stocks)
        QMessageBox.information(self, "저장 완료", "종목 정보가 저장되었습니다.")
