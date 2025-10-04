import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
import win32gui
import win32con
import win32api
from threading import Thread
import time
from typing import Optional, List, Dict, Any
import cv2
import json
from multiprocessing import freeze_support

# --- 导入核心模块 ---
from capture.realtime_capture import WindowCapture
from game_analyzer import GameAnalyzer

# --- AppState Class ---
class AppState:
    def __init__(self):
        self.hwnd = 0
        self.window_capture = None
        self.game_analyzer = None
        self.locked_regions = None

# --- GUI Application ---
class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("陆战棋-智能战情室 (V32-最终修复版)")
        self.root.geometry("800x800")
        self.root.resizable(False, False)
        
        self.app_state = AppState()
        self.regions_file = Path("data/regions.json")
        self.is_recognizing = False
        self.recognition_thread = None
        self.button3 = None
        self.button4 = None

        # --- UI ---
        self.info_frame = ttk.Frame(root, height=650)
        self.info_frame.pack(fill="both", expand=True)
        self.info_frame.pack_propagate(False)
        self.control_frame = ttk.Frame(root, height=150)
        self.control_frame.pack(fill="x", padx=10, pady=5)
        self.control_frame.pack_propagate(False)
        self.info_text = scrolledtext.ScrolledText(self.info_frame, wrap=tk.WORD, state='disabled', font=("Microsoft YaHei", 10), bg="#f0f0f0")
        self.info_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # --- Tag Configs for Rich Logging ---
        self.info_text.tag_config("p_purple", foreground="#8A2BE2")
        self.info_text.tag_config("p_red", foreground="#DC143C")
        self.info_text.tag_config("p_orange", foreground="#FF8C00")
        self.info_text.tag_config("p_yellow", foreground="#BDB76B")
        self.info_text.tag_config("p_blue", foreground="#4169E1")
        self.info_text.tag_config("p_green", foreground="#2E8B57")
        self.info_text.tag_config("p_bold_red", foreground="#FF0000", font=("Microsoft YaHei", 10, "bold"))
        self.info_text.tag_config("p_cyan", foreground="#008B8B")
        self.info_text.tag_config("h_default", font=("Microsoft YaHei", 11, "bold"), foreground="#000080")
        self.info_text.tag_config("eliminated", overstrike=True, foreground="#888888")
        self.info_text.tag_config("h_blue", foreground="blue", font=("Microsoft YaHei", 11, "bold"))
        self.info_text.tag_config("h_green", foreground="green", font=("Microsoft YaHei", 11, "bold"))
        self.info_text.tag_config("h_orange", foreground="orange", font=("Microsoft YaHei", 11, "bold"))
        self.info_text.tag_config("h_purple", foreground="purple", font=("Microsoft YaHei", 11, "bold"))

        self.setup_control_buttons()
        self.initialize_analyzer()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.is_recognizing = False
        if hasattr(self.app_state.game_analyzer, 'pool'):
            self.app_state.game_analyzer.pool.close()
            self.app_state.game_analyzer.pool.join()
        if self.app_state.hwnd and win32gui.IsWindow(self.app_state.hwnd):
            try:
                win32gui.ShowWindow(self.app_state.hwnd, win32con.SW_MINIMIZE)
                win32gui.SetWindowPos(self.app_state.hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            except Exception: pass
        self.root.destroy()

    def initialize_analyzer(self):
        try:
            self.app_state.game_analyzer = GameAnalyzer("vision/new_templates")
            self.log_message("--- 战情室启动成功 (V32-最终修复版) ---")
            if self.regions_file.exists():
                try:
                    with open(self.regions_file, 'r') as f: self.app_state.locked_regions = json.load(f)
                    self.log_message("[信息] 已成功从文件加载锁定的分区数据。")
                except Exception as e: self.log_message(f"[错误] 加载分区文件失败: {e}")
            else:
                self.log_message("[信息] 未找到分区数据文件。请点击“2. 开始识别”以在首次识别时自动生成。")
                self.regions_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e: self.log_message(f"[严重错误] 分析器初始化失败: {e}")

    def setup_control_buttons(self):
        for i in range(4): self.control_frame.grid_columnconfigure(i, weight=1)
        for i in range(3): self.control_frame.grid_rowconfigure(i, weight=1)
        buttons = {
            (0,0):("1. 检测窗口", self.detect_game_window), 
            (0,1):("2. 识别 (ROI)", lambda: self.start_recognition(use_roi=True)),
            (0,2):("3. 连续识别", self.start_continuous_recognition), 
            (0,3):("4. 停止识别", self.stop_continuous_recognition),
            (1,0):("5. 查看分区", self.visualize_regions), 
            (1,1):("6. 检测区 (ROI)", self.visualize_plus_region),
            (1,2):("7. 理论节点", self.visualize_theoretical_nodes),
            (1,3):("8. 清空日志", self.clear_log),
            (2,0):("9. 检测区 (旧)", self.visualize_legacy_plus_region), 
            (2,1):("10. 检测节点", self.visualize_detected_nodes),
            (2,2):("11. 识别 (全图)", lambda: self.start_recognition(use_roi=False)), 
            (2,3):("12. 退出", self.on_closing)
        }
        for (r,c), (txt,cmd) in buttons.items():
            b = ttk.Button(self.control_frame, text=txt, command=cmd)
            b.grid(row=r, column=c, sticky="nsew", padx=5, pady=5)
            if r==0 and c==2: self.button3 = b
            if r==0 and c==3: self.button4 = b; b.config(state='disabled')

    def clear_log(self):
        self.info_text.config(state='normal')
        self.info_text.delete('1.0', tk.END)
        self.info_text.config(state='disabled')

    def log_message(self, message: str, tag: str = None):
        self.info_text.config(state='normal')
        self.info_text.insert(tk.END, message + "\n\n")
        self.info_text.see(tk.END)
        self.info_text.config(state='disabled')

    def log_rich_report(self, report_data: Dict):
        self.info_text.config(state='normal')
        
        timestamp = time.strftime("%Y%m%d%H%M-%S")
        header = f"=============== [ {timestamp} ] (总棋子数: {report_data.get('total_count', 0)}个) ===============\n"
        self.info_text.insert(tk.END, header, "h_default")

        for item in report_data.get('report_items', []):
            if item['type'] == 'header':
                color_tag = f"h_{item['color']}" if item.get('color') else "h_default"
                self.info_text.insert(tk.END, f"\n{item['text']}\n", color_tag)
            elif item['type'] == 'piece_line':
                for piece in item['pieces']:
                    tags = (piece['color_tag'], 'eliminated') if piece.get('eliminated') else (piece['color_tag'],)
                    self.info_text.insert(tk.END, f"{piece['text']:<8s}", tags)
                self.info_text.insert(tk.END, "\n")
        self.info_text.see(tk.END)
        self.info_text.config(state='disabled')

    def _force_set_topmost(self):
        if self.app_state.hwnd and win32gui.IsWindow(self.app_state.hwnd):
            try: win32gui.SetWindowPos(self.app_state.hwnd, win32con.HWND_TOPMOST, 0,0,0,0, win32con.SWP_NOMOVE|win32con.SWP_NOSIZE)
            except Exception: pass

    def detect_game_window(self):
        self.log_message("--- 开始检测游戏窗口 ---")
        try:
            self.app_state.window_capture = WindowCapture("JunQiRpg.exe", "四国军棋")
            self.app_state.hwnd = self.app_state.window_capture.hwnd
            if self.app_state.hwnd:
                win32gui.ShowWindow(self.app_state.hwnd, win32con.SW_RESTORE)
                self._force_set_topmost()
                win32gui.SetForegroundWindow(self.app_state.hwnd)
                rect = win32gui.GetWindowRect(self.app_state.hwnd)
                self.log_message(f"成功检测到游戏窗口！句柄: {self.app_state.hwnd}, 尺寸: {rect[2]-rect[0]}x{rect[3]-rect[1]}")
            else: self.log_message("错误: 未找到匹配的游戏窗口。")
        except Exception as e: self.log_message(f"检测窗口时发生未知错误: {e}")

    def start_recognition(self, use_roi: bool):
        if not self.app_state.window_capture: return self.log_message("[错误] 请先检测游戏窗口。")
        screenshot = self.app_state.window_capture.get_screenshot()
        if screenshot is None: return self.log_message("[错误] 获取截图失败。")

        if not self.app_state.locked_regions:
            self.log_message("[信息] 首次运行，正在自动分析并锁定分区...")
            try:
                regions = self.app_state.game_analyzer.get_player_regions(screenshot)
                if len(regions) < 5: return self.log_message("[错误] 未能计算出完整的5个区域。")
                self.app_state.locked_regions = {k: tuple(map(int, v)) for k, v in regions.items()}
                with open(self.regions_file, 'w') as f: json.dump(self.app_state.locked_regions, f, indent=4)
                self.log_message("[成功] 初始分区已自动锁定并保存！")
            except Exception as e: return self.log_message(f"[严重错误] 自动锁定分区时出错: {e}")

        image_to_analyze = screenshot
        if use_roi:
            x1, y1, x2, y2 = self._get_full_roi()
            if x1 is None: return self.log_message("[错误] 分区数据不完整，无法计算ROI。")
            image_to_analyze = screenshot[y1:y2, x1:x2]
        
        report = self.app_state.game_analyzer.analyze_screenshot(image_to_analyze, match_threshold=0.8)
        self.log_rich_report(report) # Use the correct rich report function
        self._force_set_topmost()

    def start_continuous_recognition(self):
        if self.is_recognizing: return
        if not self.app_state.window_capture: return self.log_message("[错误] 请先检测游戏窗口。")
        self.is_recognizing = True
        self.button3.config(state='disabled'); self.button4.config(state='normal')
        self.recognition_thread = Thread(target=self._continuous_recognition_worker, daemon=True)
        self.recognition_thread.start()
        self.log_message("--- 连续识别已启动 ---")

    def stop_continuous_recognition(self):
        if not self.is_recognizing: return
        self.is_recognizing = False
        self.button3.config(state='normal'); self.button4.config(state='disabled')
        self.log_message("--- 连续识别已停止 ---")

    def _continuous_recognition_worker(self):
        while self.is_recognizing:
            screenshot = self.app_state.window_capture.get_screenshot()
            if screenshot is None: time.sleep(0.5); continue
            report = self.app_state.game_analyzer.analyze_screenshot(screenshot, match_threshold=0.8)
            self.root.after(0, self.log_rich_report, report) # Use the correct rich report function
            time.sleep(1)

    def _get_full_roi(self):
        if not self.app_state.locked_regions or len(self.app_state.locked_regions) < 5: return None, None, None, None
        regions = self.app_state.locked_regions.values()
        min_x=min(r[0] for r in regions); min_y=min(r[1] for r in regions)
        max_x=max(r[2] for r in regions); max_y=max(r[3] for r in regions)
        return int(min_x), int(min_y), int(max_x), int(max_y)

    def visualize_regions(self): # Button 5
        if not self.app_state.locked_regions: return self.log_message("[错误] 未找到分区数据。")
        screenshot = self.app_state.window_capture.get_screenshot();
        if screenshot is None: return
        vis_image = screenshot.copy()
        colors = {"上方":(255,0,0),"下方":(0,255,0),"左侧":(0,0,255),"右侧":(255,255,0),"中央":(255,0,255)}
        for name, (x1,y1,x2,y2) in self.app_state.locked_regions.items():
            cv2.rectangle(vis_image, (x1,y1), (x2,y2), colors.get(name,(255,255,255)), 2)
            cv2.putText(vis_image, name, (x1+5,y1+20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colors.get(name,(255,255,255)), 2)
        cv2.imshow("分区图 (按钮5)", vis_image); cv2.waitKey(1); self._force_set_topmost()

    def visualize_plus_region(self): # Button 6
        x1, y1, x2, y2 = self._get_full_roi()
        if x1 is None: return self.log_message("[错误] 分区数据不完整。")
        screenshot = self.app_state.window_capture.get_screenshot();
        if screenshot is None: return
        vis_image = screenshot.copy()
        cv2.rectangle(vis_image, (x1,y1), (x2,y2), (0,0,255), 2)
        cv2.imshow("ROI检测区域 (按钮6)", vis_image); cv2.waitKey(1); self._force_set_topmost()

    def visualize_theoretical_nodes(self): # Button 7
        if not self.app_state.locked_regions: return self.log_message("[错误] 未找到分区数据。")
        screenshot = self.app_state.window_capture.get_screenshot();
        if screenshot is None: return
        vis_image = screenshot.copy()
        all_nodes = []
        specs = {"上方":(6,5),"下方":(6,5),"左侧":(6,5),"右侧":(6,5),"中央":(3,3)}
        for key, (rows,cols) in specs.items():
            if key in self.app_state.locked_regions:
                x1,y1,x2,y2 = map(int, self.app_state.locked_regions[key])
                cell_w, cell_h = (x2-x1)/cols, (y2-y1)/rows
                for r in range(rows):
                    for c in range(cols):
                        all_nodes.append((int(x1+(c+0.5)*cell_w), int(y1+(r+0.5)*cell_h)))
        for (cx,cy) in all_nodes: cv2.circle(vis_image, (cx,cy), 5, (0,255,0), -1)
        self.log_message(f"成功生成了 {len(all_nodes)} 个理论棋盘节点。")
        cv2.imshow("理论节点分布 (按钮7)", vis_image); cv2.waitKey(1); self._force_set_topmost()

    def visualize_legacy_plus_region(self): # Button 9
        if not self.app_state.locked_regions: return self.log_message("[错误] 未找到分区数据。")
        screenshot = self.app_state.window_capture.get_screenshot();
        if screenshot is None: return
        regions = self.app_state.locked_regions
        if not all(k in regions for k in ["上方","下方","左侧","右侧"]): return self.log_message("[错误] 区域信息不完整。")
        vis_image = screenshot.copy()
        h_x1,h_y1,_,h_y2 = map(int,regions["左侧"]); _,_,h_x2,_ = map(int,regions["右侧"])
        v_x1,v_y1,v_x2,_ = map(int,regions["上方"]); _,_,_,v_y2 = map(int,regions["下方"])
        cv2.rectangle(vis_image, (h_x1,h_y1), (h_x2,h_y2), (0,255,0), 2)
        cv2.rectangle(vis_image, (v_x1,v_y1), (v_x2,v_y2), (0,255,0), 2)
        cv2.imshow("旧版'+'区域 (按钮9)", vis_image); cv2.waitKey(1); self._force_set_topmost()

    def visualize_detected_nodes(self): # Button 10
        if not self.app_state.window_capture: return self.log_message("[错误] 请先检测游戏窗口。")
        screenshot = self.app_state.window_capture.get_screenshot();
        if screenshot is None: return
        self.log_message("[信息] 正在全图搜索棋子节点...")
        detections = self.app_state.game_analyzer.analyze_screenshot(screenshot, return_detections=True)
        vis_image = screenshot.copy()
        for det in detections:
            b_x1,b_y1,b_x2,b_y2 = det.bbox
            cv2.rectangle(vis_image, (b_x1,b_y1), (b_x2,b_y2), (0,255,0), 2)
        self.log_message(f"全图共检测到 {len(detections)} 个节点。")
        cv2.imshow("全图检测节点 (按钮10)", vis_image); cv2.waitKey(1); self._force_set_topmost()

if __name__ == "__main__":
    freeze_support()
    root = tk.Tk()
    app = DashboardApp(root)
    root.mainloop()