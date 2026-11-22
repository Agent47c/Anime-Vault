"""Password prompt, setup, and recovery dialog for adult anime content."""
from app.ui.manga_style import set_material
from typing import List, Optional
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from app.core import adult_content as sec
from app.ui.home_style import colors, px


class AdultPasswordDialog(QDialog):
    """Secure PIN/password dialog with 3 security questions recovery."""

    MODE_UNLOCK = "unlock"
    MODE_SET_INITIAL = "set_initial"
    MODE_RECOVER = "recover"
    MODE_CHANGE = "change"

    def __init__(self, parent=None, mode: str = MODE_UNLOCK):
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle("Adult Content Access")
        self.setObjectName('adult_access')
        self.setMinimumWidth(px(460))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        from app.ui.manga_pages import active
        if active():self.setWindowFlags(Qt.Dialog|Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(px(24), px(24), px(24), px(24))
        root.setSpacing(px(16))
        self.access_header=QWidget();self.access_header.setObjectName('adult_header');header=QHBoxLayout(self.access_header);header.setContentsMargins(0,0,0,0)
        from app.ui.manga_pages import active
        if active():
            from PyQt5.QtGui import QIcon
            from pathlib import Path
            mark=QLabel();mark.setPixmap(QIcon(str(Path(__file__).resolve().parents[3]/'assets'/'app.ico')).pixmap(18,18));header.addWidget(mark)
        kicker=QLabel('Adult Content Access');kicker.setObjectName('adult_kicker');header.addWidget(kicker,1)
        from app.ui.components.close_button import CloseButton
        close=CloseButton();close.clicked.connect(self.reject);header.addWidget(close);root.addWidget(self.access_header)

        # Header
        self.title_label = QLabel()
        self.title_label.setObjectName("dialog_title")
        root.addWidget(self.title_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("dialog_subtitle")
        self.subtitle_label.setWordWrap(True)
        root.addWidget(self.subtitle_label)

        # Dynamic Content Container
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(px(12))
        root.addWidget(self.content_widget)

        # Error / Status label
        self.error_label = QLabel()
        self.error_label.setObjectName("dialog_error")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        root.addWidget(self.error_label)

        # Actions Layout
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(px(10))
        root.addLayout(self.actions_layout)
        from app.ui.manga_pages import active
        if active():
            from PyQt5.QtWidgets import QSizePolicy
            self.access_header.setFixedHeight(28)
            for label in (self.title_label,self.subtitle_label):label.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Maximum)
            self.content_widget.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Maximum)

        self._switch_mode(self.mode)

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.actions_layout.count():
            item = self.actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.error_label.hide()
        self.error_label.setText("")

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()

    def _switch_mode(self, mode: str):
        self.mode = mode
        self._clear_content()

        if mode == self.MODE_UNLOCK:
            self._setup_unlock_view()
        elif mode == self.MODE_SET_INITIAL:
            self._setup_initial_view()
        elif mode == self.MODE_RECOVER:
            self._setup_recover_view()
        elif mode == self.MODE_CHANGE:
            self._setup_change_view()
        self._modal_initial_focus=(getattr(self,'pwd_input',None) if mode==self.MODE_UNLOCK else
                                   getattr(self,'curr_pwd',None) if mode==self.MODE_CHANGE else
                                   getattr(self,'new_pwd_input',None) if mode==self.MODE_SET_INITIAL else
                                   next(iter(getattr(self,'answer_inputs',[])),None))

    def _create_line_edit(self, placeholder: str, is_password: bool = True) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        if is_password:
            edit.setEchoMode(QLineEdit.Password)
        edit.setMinimumHeight(px(38))
        return edit

    # -------------------------------------------------------------------------
    # 1. Unlock View
    # -------------------------------------------------------------------------
    def _setup_unlock_view(self):
        self.title_label.setText("Unlock Adult Anime")
        self.subtitle_label.setText("Enter your PIN or password to display adult titles in the library and updates.")

        self.pwd_input = self._create_line_edit("Enter password")
        from app.ui.manga_pages import active
        if active():
            from app.ui.icons import icon
            self.pwd_input.addAction(icon('lock','#8e95a5'),QLineEdit.TrailingPosition).setEnabled(False)
        self.pwd_input.returnPressed.connect(self._handle_unlock)
        self.content_layout.addWidget(self.pwd_input)

        # Action bar
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self.actions_layout.addWidget(cancel_btn)

        if sec.get_security_questions():
            forgot_btn = QPushButton("Forgot password?")
            forgot_btn.setObjectName("link_button")
            forgot_btn.clicked.connect(lambda: self._switch_mode(self.MODE_RECOVER))
            self.actions_layout.addWidget(forgot_btn)

        self.actions_layout.addStretch()

        unlock_btn = QPushButton("Unlock")
        unlock_btn.setProperty("accent", True)
        unlock_btn.clicked.connect(self._handle_unlock)
        self.actions_layout.addWidget(unlock_btn)

        self.pwd_input.setFocus()

    def _handle_unlock(self):
        password = self.pwd_input.text()
        if not password:
            self._show_error("Please enter your password.")
            return
        if sec.unlock(password):
            self.accept()
        else:
            self._show_error("Incorrect password. Please try again.")

    # -------------------------------------------------------------------------
    # 2. Set Initial Password & 3 Security Questions View
    # -------------------------------------------------------------------------
    def _setup_initial_view(self):
        self.title_label.setText("Set Adult Content Password")
        self.subtitle_label.setText(
            "Create a password and answer 3 security questions to protect and recover adult content settings."
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(px(320))

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, px(4), 0)
        layout.setSpacing(px(10))

        layout.addWidget(QLabel("Password (minimum 4 characters):"))
        self.new_pwd_input = self._create_line_edit("Create password")
        layout.addWidget(self.new_pwd_input)

        self.confirm_pwd_input = self._create_line_edit("Confirm password")
        layout.addWidget(self.confirm_pwd_input)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("dialog_divider")
        layout.addWidget(divider)

        layout.addWidget(QLabel("Recovery Security Questions (used if you forget your password):"))

        self.qa_widgets = []
        for i in range(3):
            q_combo = QComboBox()
            # Select different default prompts for each slot
            for q in sec.DEFAULT_SECURITY_QUESTIONS:
                q_combo.addItem(q)
            q_combo.setCurrentIndex(i % len(sec.DEFAULT_SECURITY_QUESTIONS))
            q_combo.setMinimumHeight(px(32))
            layout.addWidget(q_combo)

            ans_edit = self._create_line_edit(f"Answer to question {i + 1}", is_password=False)
            layout.addWidget(ans_edit)
            self.qa_widgets.append((q_combo, ans_edit))

        scroll.setWidget(container)
        self.content_layout.addWidget(scroll)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self.actions_layout.addWidget(cancel_btn)

        self.actions_layout.addStretch()

        save_btn = QPushButton("Save & Enable")
        save_btn.setProperty("accent", True)
        save_btn.clicked.connect(self._handle_save_initial)
        self.actions_layout.addWidget(save_btn)

        self.new_pwd_input.setFocus()

    def _handle_save_initial(self):
        pwd = self.new_pwd_input.text()
        confirm = self.confirm_pwd_input.text()
        if len(pwd) < 4:
            self._show_error("Password must be at least 4 characters long.")
            return
        if pwd != confirm:
            self._show_error("Passwords do not match.")
            return

        qa_list = []
        for combo, ans_edit in self.qa_widgets:
            q = combo.currentText().strip()
            a = ans_edit.text().strip()
            if not a:
                self._show_error("Please provide answers to all 3 security questions.")
                return
            qa_list.append({"question": q, "answer": a})

        try:
            sec.set_password(pwd, qa_list)
            sec.unlock(pwd)
            self.accept()
        except Exception as e:
            self._show_error(str(e))

    # -------------------------------------------------------------------------
    # 3. Forgot Password Recovery View
    # -------------------------------------------------------------------------
    def _setup_recover_view(self):
        self.title_label.setText("Reset Password")
        self.subtitle_label.setText("Answer your 3 security questions to verify your identity and set a new password.")

        questions = sec.get_security_questions()
        if len(questions) < 3:
            self._show_error("No security questions are configured for this installation.")
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(px(320))

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, px(4), 0)
        layout.setSpacing(px(10))

        self.answer_inputs = []
        for i, q in enumerate(questions):
            q_label = QLabel(f"Q{i + 1}: {q}")
            q_label.setWordWrap(True)
            layout.addWidget(q_label)

            ans_edit = self._create_line_edit("Your answer", is_password=False)
            layout.addWidget(ans_edit)
            self.answer_inputs.append(ans_edit)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("dialog_divider")
        layout.addWidget(divider)

        layout.addWidget(QLabel("New Password:"))
        self.reset_new_pwd = self._create_line_edit("Enter new password")
        layout.addWidget(self.reset_new_pwd)

        self.reset_confirm_pwd = self._create_line_edit("Confirm new password")
        layout.addWidget(self.reset_confirm_pwd)

        scroll.setWidget(container)
        self.content_layout.addWidget(scroll)

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(lambda: self._switch_mode(self.MODE_UNLOCK))
        self.actions_layout.addWidget(back_btn)

        self.actions_layout.addStretch()

        reset_btn = QPushButton("Verify & Reset Password")
        reset_btn.setProperty("accent", True)
        reset_btn.clicked.connect(self._handle_recover)
        self.actions_layout.addWidget(reset_btn)

        if self.answer_inputs:
            self.answer_inputs[0].setFocus()

    def _handle_recover(self):
        answers = [edit.text().strip() for edit in self.answer_inputs]
        if any(not a for a in answers):
            self._show_error("Please answer all 3 security questions.")
            return

        new_pwd = self.reset_new_pwd.text()
        confirm = self.reset_confirm_pwd.text()
        if len(new_pwd) < 4:
            self._show_error("New password must be at least 4 characters long.")
            return
        if new_pwd != confirm:
            self._show_error("New passwords do not match.")
            return

        try:
            sec.reset_password_with_answers(answers, new_pwd)
            sec.unlock(new_pwd)
            self.accept()
        except ValueError as ve:
            self._show_error(str(ve))
        except Exception as e:
            self._show_error(f"Error resetting password: {e}")

    # -------------------------------------------------------------------------
    # 4. Change Password View
    # -------------------------------------------------------------------------
    def _setup_change_view(self):
        self.title_label.setText("Change Password")
        self.subtitle_label.setText("Enter your current password and choose a new password.")

        self.curr_pwd = self._create_line_edit("Current password")
        self.content_layout.addWidget(self.curr_pwd)

        self.change_new_pwd = self._create_line_edit("New password (minimum 4 characters)")
        self.content_layout.addWidget(self.change_new_pwd)

        self.change_confirm_pwd = self._create_line_edit("Confirm new password")
        self.content_layout.addWidget(self.change_confirm_pwd)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self.actions_layout.addWidget(cancel_btn)

        self.actions_layout.addStretch()

        update_btn = QPushButton("Update Password")
        update_btn.setProperty("accent", True)
        update_btn.clicked.connect(self._handle_change)
        self.actions_layout.addWidget(update_btn)

        self.curr_pwd.setFocus()

    def _handle_change(self):
        current = self.curr_pwd.text()
        new_pwd = self.change_new_pwd.text()
        confirm = self.change_confirm_pwd.text()

        if not current:
            self._show_error("Please enter your current password.")
            return
        if len(new_pwd) < 4:
            self._show_error("New password must be at least 4 characters long.")
            return
        if new_pwd != confirm:
            self._show_error("New passwords do not match.")
            return

        try:
            sec.change_password(current, new_pwd)
            self.accept()
        except ValueError as ve:
            self._show_error(str(ve))
        except Exception as e:
            self._show_error(f"Error updating password: {e}")

    # -------------------------------------------------------------------------
    # Styling
    # -------------------------------------------------------------------------
    def refresh_home_style(self):self._apply_style()

    def _apply_style(self):
        from app.ui.manga_pages import active
        self.access_header.setVisible(active())
        if active():
            from app.ui.manga_additional import qss
            from app.ui.components.compact_modal import install,modal_qss
            install(self,480,'成人' if self.mode==self.MODE_UNLOCK else '暗号')
            self.setStyleSheet(qss('adult_access')+modal_qss('adult_access'));return
        c = colors()
        bg = c.get("bg", "#14121d")
        panel = c.get("panel", "#1c1a27")
        border = c.get("border", "#2e2b40")
        text_color = c.get("text", "#f0eef6")
        muted = c.get("muted", "#9b97b0")
        accent = c.get("accent", "#ff6584")

        set_material(self,f"""
            QDialog {{
                background-color: {panel};
                color: {text_color};
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
            QLabel#dialog_title {{
                font-size: {px(17)}px;
                font-weight: bold;
                color: {text_color};
                background: transparent;
            }}
            QLabel#dialog_subtitle {{
                font-size: {px(12)}px;
                color: {muted};
                background: transparent;
                line-height: 1.4;
            }}
            QLabel#dialog_error {{
                font-size: {px(12)}px;
                color: #ff6b6b;
                background: rgba(255, 107, 107, 0.1);
                border: 1px solid rgba(255, 107, 107, 0.3);
                border-radius: {px(4)}px;
                padding: {px(6)}px {px(10)}px;
            }}
            QLineEdit {{
                background-color: {bg};
                color: {text_color};
                border: 1px solid {border};
                border-radius: {px(6)}px;
                padding: {px(6)}px {px(10)}px;
                font-size: {px(13)}px;
                selection-background-color: {accent};
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
            }}
            QComboBox {{
                background-color: {bg};
                color: {text_color};
                border: 1px solid {border};
                border-radius: {px(6)}px;
                padding: {px(6)}px {px(10)}px;
                font-size: {px(12)}px;
            }}
            QComboBox:focus {{
                border: 1px solid {accent};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QPushButton {{
                background-color: #262338;
                color: {text_color};
                border: 1px solid {border};
                border-radius: {px(6)}px;
                padding: {px(8)}px {px(16)}px;
                font-size: {px(12)}px;
                font-weight: 500;
                min-height: {px(24)}px;
                cursor: pointer;
            }}
            QPushButton:hover {{
                background-color: #312d47;
                border-color: #433e61;
            }}
            QPushButton[accent="true"] {{
                background-color: {accent};
                color: #14121d;
                border: none;
                font-weight: bold;
            }}
            QPushButton[accent="true"]:hover {{
                background-color: #ff7d99;
            }}
            QPushButton#link_button {{
                background: transparent;
                border: none;
                color: {muted};
                text-decoration: underline;
                padding: 0;
            }}
            QPushButton#link_button:hover {{
                color: {accent};
            }}
            QFrame#dialog_divider {{
                color: {border};
                height: 1px;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
        """)

