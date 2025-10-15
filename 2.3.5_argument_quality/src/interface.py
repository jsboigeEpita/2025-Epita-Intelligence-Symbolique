import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QFileDialog,
    QSplitter,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from agent import evaluer_argument, VERTUES, ARGUMENTS_EXAMPLE


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Évaluateur d'Arguments")
        self.resize(800, 600)

        # Widgets
        self.text_input = QTextEdit()
        self.evaluate_btn = QPushButton("Évaluer")
        self.load_btn = QPushButton("Charger un fichier .txt")

        self.examples_combo = QComboBox()
        self.examples_combo.addItem("-- Choisir un exemple --")
        for i, ex in enumerate(ARGUMENTS_EXAMPLE):
            display = ex if len(ex) < 60 else ex[:57] + "..."
            self.examples_combo.addItem(f"Exemple {i}", ex)

        self.result_table = QTableWidget(0, 3)
        self.result_table.setHorizontalHeaderLabels(["Vertu", "Note", "Commentaire"])
        self.result_table.horizontalHeader().setStretchLastSection(True)

        self.final_label = QLabel("Note finale: 0 | Note moyenne: 0.0")

        # Layouts
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.evaluate_btn)
        top_layout.addWidget(self.load_btn)
        top_layout.addWidget(self.examples_combo)

        v_layout = QVBoxLayout()
        v_layout.addLayout(top_layout)
        v_layout.addWidget(self.text_input)
        v_layout.addWidget(self.result_table)
        v_layout.addWidget(self.final_label)

        container = QWidget()
        container.setLayout(v_layout)
        self.setCentralWidget(container)

        # Connexions
        self.evaluate_btn.clicked.connect(self.on_evaluate)
        self.load_btn.clicked.connect(self.on_load_file)
        self.examples_combo.currentIndexChanged.connect(self.on_example)

    def on_evaluate(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(
                self, "Aucun texte", "Veuillez entrer ou charger un texte à évaluer."
            )
            return
        result = evaluer_argument(text)
        self.display_results(result)

    def on_load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir un fichier texte", "", "Text Files (*.txt)"
        )
        if path:
            with open(path, encoding="utf-8") as f:
                self.text_input.setPlainText(f.read())

    def on_example(self, index):
        if index > 0:
            text = self.examples_combo.itemData(index)
            self.text_input.setPlainText(text)

    def display_results(self, result):
        scores = result["scores_par_vertu"]
        details = result["rapport_detaille"]
        self.result_table.setRowCount(0)
        for i, v in enumerate(VERTUES):
            note = scores.get(v, 0)
            comment = details.get(v, "")
            self.result_table.insertRow(i)
            self.result_table.setItem(i, 0, QTableWidgetItem(v))
            self.result_table.setItem(i, 1, QTableWidgetItem(f"{note:.2f}"))
            self.result_table.setItem(i, 2, QTableWidgetItem(comment))
        final = result.get("note_finale", 0)
        moyenne = result.get("note_moyenne", 0)
        self.final_label.setText(
            f"Note finale: {final:.2f} | Note moyenne: {moyenne:.2f}"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
