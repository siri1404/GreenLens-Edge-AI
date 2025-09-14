import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFrame, QStackedWidget,
                             QListWidget, QListWidgetItem, QScrollArea, QLineEdit, QTextEdit)
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QSize, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QPalette, QBrush, QLinearGradient, QPixmap, QIcon
import math

class SidebarButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #06402B;
                border: none;
                text-align: left;
                font-size: 16px;
                font-weight: 500;
                padding: 15px 20px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(6, 64, 43, 0.1);
                color: #06402B;
            }
            QPushButton:pressed {
                background-color: rgba(6, 64, 43, 0.2);
            }
        """)
        
    def enterEvent(self, event):
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(6, 64, 43, 0.1);
                color: #06402B;
                border: none;
                text-align: left;
                font-size: 16px;
                font-weight: 500;
                padding: 15px 20px;
                border-radius: 8px;
            }
        """)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #06402B;
                border: none;
                text-align: left;
                font-size: 16px;
                font-weight: 500;
                padding: 15px 20px;
                border-radius: 8px;
            }
        """)
        super().leaveEvent(event)

class Sidebar(QFrame):
    menu_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.95);
                border-right: 2px solid rgba(6, 64, 43, 0.1);
            }
        """)
        
        # Create main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Logo and App Name Section
        logo_section = QWidget()
        logo_layout = QVBoxLayout()
        logo_layout.setContentsMargins(20, 30, 20, 20)
        logo_layout.setSpacing(15)
        
        # Create SVG leaf icon (using text as placeholder)
        leaf_icon = QLabel("🍃")
        leaf_icon.setStyleSheet("""
            QLabel {
                font-size: 48px;
                color: #06402B;
                text-align: center;
            }
        """)
        leaf_icon.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(leaf_icon)
        
        # App name
        app_name = QLabel("GreenLens")
        app_name.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #06402B;
                text-align: center;
            }
        """)
        app_name.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(app_name)
        
        logo_section.setLayout(logo_layout)
        layout.addWidget(logo_section)
        
        # Menu Items Section
        menu_section = QWidget()
        menu_layout = QVBoxLayout()
        menu_layout.setContentsMargins(10, 10, 10, 10)
        menu_layout.setSpacing(5)
        
        # Create menu buttons
        self.menu_buttons = []
        menu_items = ["Home", "Scan", "Progress", "Eco-copilot", "Inventory", "Diary", "Settings"]
        
        for item in menu_items:
            btn = SidebarButton(item)
            btn.clicked.connect(lambda checked, text=item: self.on_menu_clicked(text))
            self.menu_buttons.append(btn)
            menu_layout.addWidget(btn)
        
        menu_section.setLayout(menu_layout)
        layout.addWidget(menu_section)
        
        # Add stretch to push support section to bottom
        layout.addStretch()
        
        # Support Section
        support_section = QWidget()
        support_layout = QVBoxLayout()
        support_layout.setContentsMargins(20, 20, 20, 30)
        support_layout.setSpacing(10)
        
        # Support title
        support_title = QLabel("Support")
        support_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #06402B;
                text-align: left;
            }
        """)
        support_layout.addWidget(support_title)
        
        # Support buttons
        help_btn = SidebarButton("Help & FAQ")
        contact_btn = SidebarButton("Contact Us")
        about_btn = SidebarButton("About")
        
        support_layout.addWidget(help_btn)
        support_layout.addWidget(contact_btn)
        support_layout.addWidget(about_btn)
        
        support_section.setLayout(support_layout)
        layout.addWidget(support_section)
        
        self.setLayout(layout)
        
    def on_menu_clicked(self, item):
        print(f"Menu clicked: {item}")
        # Reset all buttons to default state
        for btn in self.menu_buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #06402B;
                    border: none;
                    text-align: left;
                    font-size: 16px;
                    font-weight: 500;
                    padding: 15px 20px;
                    border-radius: 8px;
                }
            """)
        
        # Highlight clicked button
        for btn in self.menu_buttons:
            if btn.text() == item:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(6, 64, 43, 0.15);
                        color: #06402B;
                        border: none;
                        text-align: left;
                        font-size: 16px;
                        font-weight: 600;
                        padding: 15px 20px;
                        border-radius: 8px;
                    }
                """)
                break
        
        # Emit signal for page switching
        self.menu_clicked.emit(item)

class EcoCopilotPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header Bar
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(30, 15, 30, 15)
        
        # Breadcrumbs
        breadcrumbs = QLabel("Overview / Dashboard")
        breadcrumbs.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 14px;
            }
        """)
        header_layout.addWidget(breadcrumbs)
        
        header_layout.addStretch()
        
        # Action icons
        new_tab_btn = QPushButton("+")
        new_tab_btn.setFixedSize(32, 32)
        new_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #DDDDDD;
                border-radius: 6px;
                color: #333333;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        
        share_btn = QPushButton("↗")
        share_btn.setFixedSize(32, 32)
        share_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #DDDDDD;
                border-radius: 6px;
                color: #333333;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        
        menu_btn = QPushButton("⋮")
        menu_btn.setFixedSize(32, 32)
        menu_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #DDDDDD;
                border-radius: 6px;
                color: #333333;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        
        header_layout.addWidget(new_tab_btn)
        header_layout.addWidget(share_btn)
        header_layout.addWidget(menu_btn)
        
        header.setLayout(header_layout)
        layout.addWidget(header)
        
        # Main content area
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F5F5F5;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)
        
        # Welcome Card
        welcome_card = QFrame()
        welcome_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: none;
            }
        """)
        
        welcome_layout = QVBoxLayout()
        welcome_layout.setContentsMargins(30, 30, 30, 30)
        welcome_layout.setSpacing(15)
        
        # AI-powered efficiency tag
        ai_tag = QLabel("AI-powered efficiency")
        ai_tag.setStyleSheet("""
            QLabel {
                background-color: #E8F5E8;
                color: #4CAF50;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 20px;
                max-width: 150px;
            }
        """)
        welcome_layout.addWidget(ai_tag)
        
        # Welcome title
        welcome_title = QLabel("Welcome to Technolize")
        welcome_title.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 28px;
                font-weight: bold;
            }
        """)
        welcome_layout.addWidget(welcome_title)
        
        # Description
        welcome_desc = QLabel("Achieve your quarterly/yearly goals with AI-powered efficiency, ensuring smarter management and streamlined success.")
        welcome_desc.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 16px;
                line-height: 1.5;
            }
        """)
        welcome_desc.setWordWrap(True)
        welcome_layout.addWidget(welcome_desc)
        
        # Create New Goal button
        create_goal_btn = QPushButton("Create New Goal")
        create_goal_btn.setFixedHeight(40)
        create_goal_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        welcome_layout.addWidget(create_goal_btn)
        
        welcome_card.setLayout(welcome_layout)
        content_layout.addWidget(welcome_card)
        
        # Recent Goals Card
        recent_card = QFrame()
        recent_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: none;
            }
        """)
        
        recent_layout = QVBoxLayout()
        recent_layout.setContentsMargins(30, 30, 30, 30)
        recent_layout.setSpacing(15)
        
        recent_title = QLabel("Recent Goals")
        recent_title.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        recent_layout.addWidget(recent_title)
        
        # Recent goals list
        goal1 = QLabel("Publish case studies to get 25% hig...")
        goal1.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                padding: 8px 0;
            }
        """)
        recent_layout.addWidget(goal1)
        
        goal2 = QLabel("Publishing 4 Case studies turning..")
        goal2.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                padding: 8px 0;
            }
        """)
        recent_layout.addWidget(goal2)
        
        recent_card.setLayout(recent_layout)
        content_layout.addWidget(recent_card)
        
        # Smart AI Goals Alignment Card
        ai_card = QFrame()
        ai_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: none;
            }
        """)
        
        ai_layout = QVBoxLayout()
        ai_layout.setContentsMargins(0, 0, 0, 0)
        ai_layout.setSpacing(0)
        
        # Gradient bar
        gradient_bar = QFrame()
        gradient_bar.setFixedHeight(50)
        gradient_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9C27B0, stop:1 #E91E63);
                border-radius: 12px 12px 0 0;
            }
        """)
        
        gradient_layout = QHBoxLayout()
        gradient_layout.setContentsMargins(20, 15, 20, 15)
        
        gradient_text = QLabel("Define. Align. Achieve. Precision planning, powered by AI.")
        gradient_text.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        gradient_layout.addWidget(gradient_text)
        gradient_layout.addStretch()
        
        gradient_bar.setLayout(gradient_layout)
        ai_layout.addWidget(gradient_bar)
        
        # Input section
        input_section = QWidget()
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(30, 30, 30, 30)
        input_layout.setSpacing(15)
        
        # Input field with actions
        input_container = QFrame()
        input_container.setStyleSheet("""
            QFrame {
                border: 1px solid #DDDDDD;
                border-radius: 8px;
                background-color: #FFFFFF;
            }
        """)
        
        input_field_layout = QHBoxLayout()
        input_field_layout.setContentsMargins(15, 10, 15, 10)
        
        input_field = QLineEdit()
        input_field.setPlaceholderText("Type your goal here")
        input_field.setStyleSheet("""
            QLineEdit {
                border: none;
                font-size: 16px;
                color: #333333;
                background-color: transparent;
            }
        """)
        input_field_layout.addWidget(input_field)
        
        # Microphone button
        mic_btn = QPushButton("🎤")
        mic_btn.setFixedSize(32, 32)
        mic_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
                border-radius: 4px;
            }
        """)
        input_field_layout.addWidget(mic_btn)
        
        # Generate button
        generate_btn = QPushButton("Generate")
        generate_btn.setFixedHeight(32)
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        input_field_layout.addWidget(generate_btn)
        
        input_container.setLayout(input_field_layout)
        input_layout.addWidget(input_container)
        
        input_section.setLayout(input_layout)
        ai_layout.addWidget(input_section)
        
        ai_card.setLayout(ai_layout)
        content_layout.addWidget(ai_card)
        
        content_layout.addStretch()
        content_widget.setLayout(content_layout)
        content_scroll.setWidget(content_widget)
        layout.addWidget(content_scroll)
        
        self.setLayout(layout)

class ContentArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #96D9C0;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Welcome message
        welcome_label = QLabel("Welcome to GreenLens")
        welcome_label.setStyleSheet("""
            QLabel {
                color: #06402B;
                font-size: 36px;
                font-weight: bold;
                padding: 30px;
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 20px;
                border: 2px solid rgba(6, 64, 43, 0.2);
            }
        """)
        welcome_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_label)
        
        # Description
        desc_label = QLabel("Your AI-powered environmental monitoring companion")
        desc_label.setStyleSheet("""
            QLabel {
                color: #06402B;
                font-size: 20px;
                padding: 20px;
                background-color: rgba(255, 255, 255, 0.6);
                border-radius: 15px;
                margin-top: 20px;
            }
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        # Add some features section
        features_label = QLabel("🌱 Environmental Scanning  📊 Progress Tracking  🤖 AI Eco-Copilot")
        features_label.setStyleSheet("""
            QLabel {
                color: #06402B;
                font-size: 16px;
                padding: 15px;
                background-color: rgba(255, 255, 255, 0.4);
                border-radius: 12px;
                margin-top: 30px;
            }
        """)
        features_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(features_label)
        
        layout.addStretch()
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EcoLens - Environmental AI Assistant")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set background color
        self.setStyleSheet("""
            QMainWindow {
                background-color: #96D9C0;
            }
        """)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout (horizontal for sidebar + content)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Create stacked widget for pages
        self.stacked_widget = QStackedWidget()
        
        # Create pages
        self.home_page = ContentArea()
        self.eco_copilot_page = EcoCopilotPage()
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.eco_copilot_page)
        
        # Set default page
        self.stacked_widget.setCurrentWidget(self.home_page)
        
        main_layout.addWidget(self.stacked_widget)
        
        # Connect sidebar menu clicks to page switching
        self.sidebar.menu_clicked.connect(self.switch_page)
        
        central_widget.setLayout(main_layout)
        
        # Set window properties for transparency
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        
    def paintEvent(self, event):
        # Custom paint event for better background rendering
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set solid background color
        painter.fillRect(self.rect(), QColor(150, 217, 192))  # #96D9C0
        super().paintEvent(event)
    
    def switch_page(self, page_name):
        """Switch between different pages based on menu selection"""
        if page_name == "Eco-copilot":
            self.stacked_widget.setCurrentWidget(self.eco_copilot_page)
        else:
            # For other menu items, show home page for now
            self.stacked_widget.setCurrentWidget(self.home_page)

def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("EcoLens")
    app.setApplicationVersion("1.0")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
