import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path

from app.app_state import AppState
import app.gui.callbacks as callbacks

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("陆战棋-智能战情室 (V33-模块化)")
        self.root.geometry("800x800")
        self.root.resizable(False, False)
        
        self.app_state = AppState()
        self.regions_file = Path("data/regions.json")
        self.is_recognizing = False
        self.recognition_thread = None
        self.button3 = None
        self.button4 = None

        self.setup_ui()
        self.setup_bindings()

    def setup_ui(self):
        self.info_frame = ttk.Frame(self.root, height=650)
        self.info_frame.pack(fill="both", expand=True)
        self.info_frame.pack_propagate(False)
        self.control_frame = ttk.Frame(self.root, height=150)
        self.control_frame.pack(fill="x", padx=10, pady=5)
        self.control_frame.pack_propagate(False)
        self.info_text = scrolledtext.ScrolledText(self.info_frame, wrap=tk.WORD, state='disabled', font=("Microsoft YaHei", 10), bg="#f0f0f0")
        self.info_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.setup_control_buttons()

    def setup_control_buttons(self):
        for i in range(4): self.control_frame.grid_columnconfigure(i, weight=1)
        for i in range(3): self.control_frame.grid_rowconfigure(i, weight=1)
        
        buttons = {
            (0,0):("1. 检测窗口", lambda: callbacks.detect_game_window(self)),
            (0,1):("2. 识别 (ROI)", lambda: callbacks.start_recognition(self, use_roi=True)),
            (0,2):("3. 连续识别", lambda: callbacks.start_continuous_recognition(self)),
            (0,3):("4. 停止识别", lambda: callbacks.stop_continuous_recognition(self)),
            (1,0):("5. 查看分区", lambda: callbacks.visualize_regions(self)),
            (1,1):("6. 检测区 (ROI)", lambda: callbacks.visualize_plus_region(self)),
            (1,2):("7. 理论节点", lambda: callbacks.visualize_theoretical_nodes(self)),
            (1,3):("8. 清空日志", lambda: callbacks.clear_log(self)),
            (2,0):("9. 检测区 (旧)", lambda: callbacks.visualize_legacy_plus_region(self)),
            (2,1):("10. 检测节点", lambda: callbacks.visualize_detected_nodes(self)),
            (2,2):("11. 识别 (全图)", lambda: callbacks.start_recognition(self, use_roi=False)),
            (2,3):("12. 退出", lambda: callbacks.on_closing(self))
        }

        for (r,c), (txt,cmd) in buttons.items():
            b = ttk.Button(self.control_frame, text=txt, command=cmd)
            b.grid(row=r, column=c, sticky="nsew", padx=5, pady=5)
            if r==0 and c==2: self.button3 = b
            if r==0 and c==3: self.button4 = b; b.config(state='disabled')

    def setup_bindings(self):
        self.root.protocol("WM_DELETE_WINDOW", lambda: callbacks.on_closing(self))