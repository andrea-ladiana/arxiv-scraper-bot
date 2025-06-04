import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QFileDialog,
    QPlainTextEdit,
    QStackedWidget,
    QProgressBar,
)
from PyQt6.QtCore import QProcess
from PyQt6.QtGui import QColor

# Available commands
COMMANDS = [
    "scrape",
    "search",
    "categories",
    "stats",
    "cleanup",
    "session",
    "cache",
    "info",
]


class ScrapeOptions(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout()
        self.categories = QLineEdit()
        self.categories.setPlaceholderText("cs.AI math.CO")
        self.field = QComboBox()
        self.field.addItems(["", "math", "cs", "physics", "biology"])
        self.total = QSpinBox()
        self.total.setMaximum(10000)
        self.total.setValue(100)
        self.download_dir = QLineEdit("./downloads")
        self.jsonl_path = QLineEdit("./downloaded_ids.jsonl")
        self.batch_size = QSpinBox()
        self.batch_size.setMaximum(1000)
        self.batch_size.setValue(10)
        self.max_retries = QSpinBox()
        self.max_retries.setValue(3)
        self.max_concurrent = QSpinBox()
        self.max_concurrent.setValue(5)
        self.export_metadata = QCheckBox()
        self.export_bibtex = QCheckBox()
        self.format = QComboBox()
        self.format.addItems(["source", "pdf", "both"])
        layout.addRow("Categories (space separated)", self.categories)
        layout.addRow("Field", self.field)
        layout.addRow("Total", self.total)
        layout.addRow("Download dir", self.download_dir)
        layout.addRow("JSONL path", self.jsonl_path)
        layout.addRow("Batch size", self.batch_size)
        layout.addRow("Max retries", self.max_retries)
        layout.addRow("Max concurrent", self.max_concurrent)
        layout.addRow("Export metadata", self.export_metadata)
        layout.addRow("Export BibTeX", self.export_bibtex)
        layout.addRow("Format", self.format)
        self.setLayout(layout)

    def args(self):
        args = []
        if self.categories.text().strip():
            for cat in self.categories.text().split():
                args += ["--categories", cat]
        if self.field.currentText():
            args += ["--field", self.field.currentText()]
        args += ["--total", str(self.total.value())]
        args += ["--download-dir", self.download_dir.text()]
        args += ["--jsonl-path", self.jsonl_path.text()]
        args += ["--batch-size", str(self.batch_size.value())]
        args += ["--max-retries", str(self.max_retries.value())]
        args += ["--max-concurrent", str(self.max_concurrent.value())]
        if self.export_metadata.isChecked():
            args.append("--export-metadata")
        if self.export_bibtex.isChecked():
            args.append("--export-bibtex")
        args += ["--format", self.format.currentText()]
        return args


class SearchOptions(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("quantum computing")
        self.max_results = QSpinBox()
        self.max_results.setMaximum(1000)
        self.max_results.setValue(10)
        self.categories = QLineEdit()
        self.categories.setPlaceholderText("cs.AI math.CO")
        self.download = QCheckBox()
        self.format = QComboBox()
        self.format.addItems(["pdf", "source"])
        self.output_dir = QLineEdit("./downloads")
        layout.addRow("Query", self.query)
        layout.addRow("Max results", self.max_results)
        layout.addRow("Categories (space separated)", self.categories)
        layout.addRow("Download", self.download)
        layout.addRow("Format", self.format)
        layout.addRow("Output dir", self.output_dir)
        self.setLayout(layout)

    def args(self):
        args = [self.query.text()]
        args += ["--max-results", str(self.max_results.value())]
        if self.categories.text().strip():
            for cat in self.categories.text().split():
                args += ["--categories", cat]
        if self.download.isChecked():
            args.append("--download")
        args += ["--format", self.format.currentText()]
        args += ["--output-dir", self.output_dir.text()]
        return args


class CategoriesOptions(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout()
        self.field = QComboBox()
        self.field.addItems(["", "math", "cs", "physics", "biology"])
        layout.addRow("Field", self.field)
        self.setLayout(layout)

    def args(self):
        args = []
        if self.field.currentText():
            args += ["--field", self.field.currentText()]
        return args


class StatsOptions(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout()
        self.jsonl_path = QLineEdit("./downloaded_ids.jsonl")
        self.format = QComboBox()
        self.format.addItems(["table", "json"])
        layout.addRow("JSONL path", self.jsonl_path)
        layout.addRow("Format", self.format)
        self.setLayout(layout)

    def args(self):
        return ["--jsonl-path", self.jsonl_path.text(), "--format", self.format.currentText()]


class CleanupOptions(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout()
        self.download_dir = QLineEdit("./downloads")
        self.days_old = QSpinBox()
        self.days_old.setValue(30)
        self.dry_run = QCheckBox()
        layout.addRow("Download dir", self.download_dir)
        layout.addRow("Days old", self.days_old)
        layout.addRow("Dry run", self.dry_run)
        self.setLayout(layout)

    def args(self):
        args = [
            "--download-dir",
            self.download_dir.text(),
            "--days-old",
            str(self.days_old.value()),
        ]
        if self.dry_run.isChecked():
            args.append("--dry-run")
        return args


class SessionOptions(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout()
        self.session_id = QLineEdit()
        self.session_id.setPlaceholderText("abcd1234")
        self.list_sessions = QCheckBox()
        self.errors = QCheckBox()
        layout.addRow("Session ID", self.session_id)
        layout.addRow("List sessions", self.list_sessions)
        layout.addRow("Errors only", self.errors)
        self.setLayout(layout)

    def args(self):
        args = []
        if self.session_id.text().strip():
            args.append(self.session_id.text())
        if self.list_sessions.isChecked():
            args.append("--list")
        if self.errors.isChecked():
            args.append("--errors")
        return args


class CacheOptions(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout()
        self.days = QSpinBox()
        self.days.setValue(7)
        layout.addRow("Days", self.days)
        self.setLayout(layout)

    def args(self):
        return ["--days", str(self.days.value())]


class InfoOptions(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("No options"))
        self.setLayout(layout)

    def args(self):
        return []


OPTION_WIDGETS = {
    "scrape": ScrapeOptions,
    "search": SearchOptions,
    "categories": CategoriesOptions,
    "stats": StatsOptions,
    "cleanup": CleanupOptions,
    "session": SessionOptions,
    "cache": CacheOptions,
    "info": InfoOptions,
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArXiv Scraper GUI")
        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)
        top = QHBoxLayout()
        vbox.addLayout(top)

        self.command_combo = QComboBox()
        self.command_combo.addItems(COMMANDS)
        top.addWidget(QLabel("Command:"))
        top.addWidget(self.command_combo)
        self.run_button = QPushButton("Run")
        self.run_button.setStyleSheet("padding: 6px 12px;")
        top.addWidget(self.run_button)

        self.stack = QStackedWidget()
        vbox.addWidget(self.stack)

        for cmd in COMMANDS:
            widget = OPTION_WIDGETS[cmd]()
            self.stack.addWidget(widget)
        self.command_combo.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet(
            "background-color: #1e1e1e; color: #e0e0e0; font-family: monospace;"
        )
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        vbox.addWidget(QLabel("Output:"))
        vbox.addWidget(self.output)
        vbox.addWidget(self.progress)

        self.process = None
        self.run_button.clicked.connect(self.run_command)

    def run_command(self):
        cmd = COMMANDS[self.command_combo.currentIndex()]
        opts_widget = self.stack.currentWidget()
        args = [sys.executable, "-m", "arxiv_scraper.cli.main", cmd] + opts_widget.args()
        self.output.clear()
        self.process = QProcess(self)
        self.process.setProgram(sys.executable)
        self.process.setArguments(["-m", "arxiv_scraper.cli.main", cmd] + opts_widget.args())
        self.process.readyReadStandardOutput.connect(
            lambda: self.read_output(self.process.readAllStandardOutput())
        )
        self.process.readyReadStandardError.connect(
            lambda: self.read_output(self.process.readAllStandardError())
        )
        self.process.finished.connect(self.process_finished)
        self.run_button.setEnabled(False)
        self.progress.show()
        self.process.start()

    def process_finished(self):
        self.run_button.setEnabled(True)
        self.progress.hide()

    def read_output(self, data):
        text = bytes(data).decode("utf-8")
        self.output.appendPlainText(text)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.WindowText, QColor(220, 220, 220))
    palette.setColor(palette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(palette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.ToolTipBase, QColor(220, 220, 220))
    palette.setColor(palette.ColorRole.ToolTipText, QColor(220, 220, 220))
    palette.setColor(palette.ColorRole.Text, QColor(220, 220, 220))
    palette.setColor(palette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.ButtonText, QColor(220, 220, 220))
    palette.setColor(palette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(palette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(palette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(palette.ColorRole.HighlightedText, QColor(35, 35, 35))
    app.setPalette(palette)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
