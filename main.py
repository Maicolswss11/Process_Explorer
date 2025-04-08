from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QHBoxLayout,
    QFileDialog, QAbstractItemView, QLabel, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QMovie
import psutil
import sys

from PySide6.QtGui import QPainter, QColor

class Spinner(QWidget):
    def __init__(self, parent=None, radius=10, lines=12, line_width=2, speed=100):
        super().__init__(parent)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.rotate)
        self._radius = radius
        self._lines = lines
        self._line_width = line_width
        self._speed = speed
        self.setFixedSize(radius * 2 + 4, radius * 2 + 4)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def start(self):
        self._timer.start(self._speed)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def rotate(self):
        self._angle = (self._angle + 1) % self._lines
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        for i in range(self._lines):
            alpha = 255 * ((i + self._angle) % self._lines) / self._lines
            color = QColor(100, 100, 255, int(alpha))
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(
                -self._line_width / 2,
                -self._radius,
                self._line_width,
                self._radius / 3,
                2,
                2
            )
            painter.rotate(360 / self._lines)

class ProcessFinderThread(QThread):
    results_ready = Signal(list)

    def __init__(self, target):
        super().__init__()
        self.target = target.lower()

    def run(self):
        results = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for f in proc.open_files():
                    if self.target in f.path.lower():
                        results.append({
                            'pid': proc.pid,
                            'name': proc.name(),
                            'path': f.path
                        })
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        self.results_ready.emit(results)


class ProcessExplorer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mini Process Explorer")
        self.setGeometry(100, 100, 800, 500)

        layout = QVBoxLayout()

        # Input + browse + search button
        input_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Inserisci percorso o nome file...")
        input_layout.addWidget(self.file_input)

        browse_button = QPushButton("📂 Sfoglia")
        browse_button.clicked.connect(self.browse_file)
        input_layout.addWidget(browse_button)

        self.search_button = QPushButton("🔍 Cerca")
        self.search_button.clicked.connect(self.start_search)
        input_layout.addWidget(self.search_button)

        layout.addLayout(input_layout)
        self.spinner = Spinner(self)
        self.spinner.hide()
        layout.addWidget(self.spinner, alignment=Qt.AlignCenter)


        # Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["PID", "Processo", "File"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # Termina processo
        self.terminate_button = QPushButton("🛑 Termina processo selezionato")
        self.terminate_button.clicked.connect(self.terminate_selected_process)
        layout.addWidget(self.terminate_button)

        self.setLayout(layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleziona file da cercare")
        if file_path:
            self.file_input.setText(file_path)

    def start_search(self):
        target = self.file_input.text().strip()
        if not target:
            QMessageBox.warning(self, "Attenzione", "Inserisci un nome di file o percorso.")
            return

        self.search_button.setEnabled(False)
        self.terminate_button.setEnabled(False)
        self.spinner.start()
        self.spinner.setVisible(True)
        self.table.setRowCount(0)

        self.thread = ProcessFinderThread(target)
        self.thread.results_ready.connect(self.display_results)
        self.thread.start()

    def display_results(self, results):
        self.table.setRowCount(0)
        for row, result in enumerate(results):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(result['pid'])))
            self.table.setItem(row, 1, QTableWidgetItem(result['name']))
            self.table.setItem(row, 2, QTableWidgetItem(result['path']))

        self.search_button.setEnabled(True)
        self.terminate_button.setEnabled(True)
        self.spinner.stop()
        self.spinner.setVisible(False)
        

        if not results:
            QMessageBox.information(self, "Nessun risultato", "Nessun processo sta usando quel file.")

    def terminate_selected_process(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.information(self, "Info", "Seleziona un processo da terminare.")
            return

        pid_item = self.table.item(selected, 0)
        pid = int(pid_item.text())

        try:
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(3)
            QMessageBox.information(self, "Successo", f"Processo PID {pid} terminato.")
            self.table.removeRow(selected)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Non è stato possibile terminare il processo:\n{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProcessExplorer()
    window.show()
    sys.exit(app.exec())
