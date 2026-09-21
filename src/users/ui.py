from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox

class CreateUserDialog(QDialog):
    def __init__(self, user_service, parent=None):
        super().__init__(parent)
        self.user_service = user_service
        self.setWindowTitle("Crear Usuario")
        self.resize(350, 150)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(QLabel("Nombre del usuario:"))
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej. Juan Perez")
        self.name_input.setMinimumHeight(30)

        layout.addWidget(self.name_input)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setMinimumHeight(30)
        self.btn_cancel.setObjectName("secondaryButton")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_save = QPushButton("Guardar")
        self.btn_save.setMinimumHeight(30)
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self._on_save_clicked)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        
        layout.addSpacing(10)
        layout.addLayout(btn_layout)

    def _on_save_clicked(self):
        name = self.name_input.text()
        try:
            self.user_service.create_user(name)
            QMessageBox.information(self, "Éxito", f"Usuario '{name.strip()}' creado exitosamente.")
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Error de validación", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error inesperado", f"Ocurrió un error al crear el usuario:\n{str(e)}")
