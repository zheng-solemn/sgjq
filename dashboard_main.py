
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
import win32gui
import win32process
import win32con
import psutil
import ctypes
import sys
import time
from typing import Optional
import cv2
import numpy as np

# --- 动态添加项目根目录到系统路径 ---
try:
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
except NameError:
    project_root = Path.cwd()
    sys.path.insert(0, str(project_root))

from capture.realtime_capture import WindowCapture
from game_analyzer import GameAnalyzer

# --- 窗口检测逻辑 (保持不变) ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception: pass

def find_window_ultimate(process_name: str, title_substring: str) -> int:
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'].lower() == process_name.lower():
            pid_from_name = proc.info['pid']
            def callback(hwnd, hwnds):
                if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                    _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if found_pid == pid_from_name and title_substring in win32gui.GetWindowText(hwnd):
                        hwnds.append(hwnd)
                return True
            hwnds = []
            win32gui.EnumWindows(callback, hwnds)
            if hwnds: return hwnds[0]
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and title_substring in win32gui.GetWindowText(hwnd):
            hwnds.append(hwnd)
        return True
    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    if hwnds: return hwnds[0]
    return 0

# --- GUI 应用 (终极存档点 - 完美版) ---

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("陆战棋-实时战情室 (终极存档点 - 完美版)")
        self.root.geometry("800x800")
        self.root.resizable(False, False)
        
        self.game_hwnd = 0
        self.window_capture = None
        self.game_analyzer = None

        # UI 布局...
        self.info_frame = ttk.Frame(root, height=600)
        self.info_frame.pack(fill="both", expand=True)
        self.info_frame.pack_propagate(False)
        self.control_frame = ttk.Frame(root, height=200)
        self.control_frame.pack(fill="x")
        self.control_frame.pack_propagate(False)
        self.info_text = scrolledtext.ScrolledText(self.info_frame, wrap=tk.WORD, state='disabled', font=("Microsoft YaHei", 10), bg="white", fg="black")
        self.info_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.setup_control_buttons()

        self.initialize_analyzer()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        if self.game_hwnd and win32gui.IsWindow(self.game_hwnd):
            try:
                win32gui.SetWindowPos(self.game_hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            except Exception: pass
        self.root.destroy()

    def initialize_analyzer(self):
        try:
            templates_dir = "vision/new_templates"
            self.game_analyzer = GameAnalyzer(templates_dir)
            self.log_to_dashboard("--- 战情室启动成功 (终极存档点) ---")
            self.log_to_dashboard(f"已成功加载 {len(self.game_analyzer.templates_manager.get_all_templates())} 个棋子模板。")
            self.log_to_dashboard("请先点击“检测游戏窗口”锁定目标。")
        except Exception as e:
            self.log_to_dashboard(f"[严重错误] 分析器初始化失败: {e}")

    def setup_control_buttons(self):
        button_frame_1 = ttk.Frame(self.control_frame)
        button_frame_1.pack(fill='x', expand=True, padx=20, pady=15)
        button_frame_2 = ttk.Frame(self.control_frame)
        button_frame_2.pack(fill='x', expand=True, padx=20, pady=15)
        
        buttons_row1 = ["检测游戏窗口", "开始识别", "按钮3", "按钮4"]
        buttons_row2 = ["查看区域划分", "显示检测区域", "查看节点分布", "退出"]

        for i, text in enumerate(buttons_row1):
            button = ttk.Button(button_frame_1, text=text)
            button.pack(side="left", fill="x", expand=True, padx=10)
            if i == 0: button.config(command=self.detect_game_window)
            elif i == 1: button.config(command=lambda: self.start_recognition(0.7))
            
        for i, text in enumerate(buttons_row2):
            button = ttk.Button(button_frame_2, text=text)
            button.pack(side="left", fill="x", expand=True, padx=10)
            if i == 0: button.config(command=self.visualize_regions)
            elif i == 1: button.config(command=self.visualize_plus_region)
            elif i == 2: button.config(command=self.visualize_all_nodes)
            elif i == 3: button.config(command=self.on_closing)

    def log_to_dashboard(self, message: str):
        self.info_text.config(state='normal')
        self.info_text.insert(tk.END, message + "\n")
        self.info_text.see(tk.END)
        self.info_text.config(state='disabled')

    def clear_dashboard(self):
        self.info_text.config(state='normal')
        self.info_text.delete('1.0', tk.END)
        self.info_text.config(state='disabled')

    def _force_set_topmost(self):
        if self.game_hwnd and win32gui.IsWindow(self.game_hwnd):
            try:
                win32gui.SetWindowPos(self.game_hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            except Exception: pass

    def detect_game_window(self):
        self.clear_dashboard()
        self.log_to_dashboard("--- 开始检测游戏窗口 ---")
        process_name = "JunQiRpg.exe"
        title_substring = "四国军棋角色版"
        hwnd = find_window_ultimate(process_name, title_substring)
        self.game_hwnd = hwnd
        if hwnd:
            self.log_to_dashboard("[成功] 已锁定游戏窗口！")
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                self._force_set_topmost()
                self.log_to_dashboard("  -> 已成功将游戏窗口激活并置顶。")
            except Exception as e:
                self.log_to_dashboard(f"  -> [警告] 尝试激活或置顶窗口时失败: {e}")
            self.window_capture = WindowCapture(process_name=process_name, title_substring=title_substring)
            try:
                title = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                self.log_to_dashboard("-" * 20)
                self.log_to_dashboard(f"窗口标题: {title}")
                self.log_to_dashboard(f"窗口句柄 (HWND): {self.game_hwnd}")
                self.log_to_dashboard(f"窗口类名: {class_name}")
                self.log_to_dashboard(f"进程 PID: {found_pid}")
                self.log_to_dashboard(f"屏幕位置 (Rect): Left={left}, Top={top}, Right={right}, Bottom={bottom}")
                self.log_to_dashboard(f"界面大小: Width={right-left}, Height={bottom-top}")
            except Exception as e:
                self.log_to_dashboard(f"[错误] 获取详细信息失败: {e}")
        else:
            self.log_to_dashboard("[失败] 未检测到游戏窗口。")

    def start_recognition(self, threshold: float):
        # 1. 生成唯一的识别ID
        recognition_id = time.strftime("%Y%m%d%H%M%S")
        
        self.log_to_dashboard("\n" + "="*50 + "\n")
        self.log_to_dashboard(f"--- 开始新一轮识别 [ID: {recognition_id}] ---")
        self.log_to_dashboard(f"使用阈值: {threshold}")

        if not self.window_capture or not self.game_analyzer:
            self.log_to_dashboard("[错误] 核心组件未初始化。")
            return
            
        screenshot = self.window_capture.get_screenshot()
        if screenshot is None or screenshot.size == 0:
            self.log_to_dashboard("[错误] 获取截图失败。")
            return
            
        save_path = Path(__file__).parent / f"screenshot_{recognition_id}.png"
        cv2.imwrite(str(save_path), screenshot)
        self.log_to_dashboard(f"截图成功，已保存至 {save_path.name}")
        
        self.log_to_dashboard("正在提交分析...")
        self.root.update_idletasks()
        
        try:
            # (未来) 可以在这里将 recognition_id 传递给分析器
            report = self.game_analyzer.analyze_screenshot(screenshot, match_threshold=threshold)
            self.log_to_dashboard("分析完成！")
            self.log_to_dashboard(report)
        except Exception as e:
            self.log_to_dashboard(f"[严重错误] 分析过程中发生错误: {e}")
        finally:
            self._force_set_topmost()

    def visualize_regions(self):
        self.log_to_dashboard("\n" + "="*50 + "\n")
        self.log_to_dashboard("--- 开始生成区域可视化 ---")
        if not self.window_capture or not self.game_analyzer:
            self.log_to_dashboard("[错误] 核心组件未初始化。")
            return
        screenshot = self.window_capture.get_screenshot()
        if screenshot.size == 0:
            self.log_to_dashboard("[错误] 获取截图失败。")
            return
        try:
            regions_with_bounds = self.game_analyzer.get_player_regions(screenshot)
            overlay = screenshot.copy()
            colors = {"上方": (0, 0, 255), "下方": (255, 0, 0), "左侧": (0, 255, 255), "右侧": (255, 0, 255), "中央": (128, 128, 128)}
            for name, bounds in regions_with_bounds.items():
                x1, y1, x2, y2 = bounds
                color = colors.get(name.split('_')[0], (255, 255, 255))
                sub_img = overlay[y1:y2, x1:x2]
                color_rect = np.full(sub_img.shape, color, dtype=np.uint8)
                res = cv2.addWeighted(sub_img, 0.6, color_rect, 0.4, 1.0)
                overlay[y1:y2, x1:x2] = res
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 3)
                cv2.putText(overlay, name, (x1 + 10, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            cv2.imshow("Fixed Region Visualization", overlay)
            self.log_to_dashboard("已弹出“Fixed Region Visualization”窗口显示区域划分。")
        except Exception as e:
            self.log_to_dashboard(f"[严重错误] 生成可视化时出错: {e}")
        finally:
            self._force_set_topmost()

    def visualize_plus_region(self):
        self.log_to_dashboard("\n" + "="*50 + "\n")
        self.log_to_dashboard("--- 开始生成“+”号总检测区域可视化 ---")
        if not self.window_capture or not self.game_analyzer:
            self.log_to_dashboard("[错误] 核心组件未初始化。")
            return
        screenshot = self.window_capture.get_screenshot()
        if screenshot.size == 0:
            self.log_to_dashboard("[错误] 获取截图失败。")
            return
        try:
            regions = self.game_analyzer.get_player_regions(screenshot)
            if not regions or not all(k in regions for k in ["上方", "下方", "左侧", "右侧"]):
                self.log_to_dashboard("[错误] 无法获取足够的区域信息来构建“+”号区域。")
                return
            overlay = screenshot.copy()
            color = (0, 255, 0)
            h_x1 = regions["左侧"][0]; h_y1 = regions["左侧"][1]
            h_x2 = regions["右侧"][2]; h_y2 = regions["右侧"][3]
            cv2.rectangle(overlay, (h_x1, h_y1), (h_x2, h_y2), color, 2)
            v_x1 = regions["上方"][0]; v_y1 = regions["上方"][1]
            v_x2 = regions["下方"][2]; v_y2 = regions["下方"][3]
            cv2.rectangle(overlay, (v_x1, v_y1), (v_x2, v_y2), color, 2)
            cv2.putText(overlay, "Total Activity Region (+)", (v_x1 + 10, v_y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.imshow("Plus Shape Region", overlay)
            self.log_to_dashboard("已弹出“Plus Shape Region”窗口。")
        except Exception as e:
            self.log_to_dashboard(f"[严重错误] 生成“+”号可视化时出错: {e}")
        finally:
            self._force_set_topmost()

    def visualize_all_nodes(self):
        """
        按钮7功能: 可视化棋盘上所有的129个节点。
        """
        self.log_to_dashboard("\n" + "="*50 + "\n")
        self.log_to_dashboard("--- 开始生成全节点分布图 ---")
        if not self.window_capture or not self.game_analyzer:
            self.log_to_dashboard("[错误] 核心组件未初始化。")
            return
        
        screenshot = self.window_capture.get_screenshot()
        if screenshot is None or screenshot.size == 0:
            self.log_to_dashboard("[错误] 获取截图失败。")
            return

        try:
            # 1. 获取所有棋子的中心点 (代表了100个节点)
            # We need to get the raw detections from the analyzer
            all_detections = self.game_analyzer.analyze_screenshot(screenshot, match_threshold=0.7, return_detections=True)
            if not all_detections:
                self.log_to_dashboard("[错误] 未识别到任何棋子，无法计算节点。")
                return
            
            piece_nodes = []
            for det in all_detections:
                x1, y1, x2, y2 = det.bbox
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                piece_nodes.append((int(cx), int(cy)))

            # 2. 获取中央区域的9个节点 + 5个行营节点
            # We'll reuse the logic from our analysis scripts
            regions = self.game_analyzer.get_player_regions(screenshot)
            
            # Find central nodes
            central_nodes = []
            if "中央" in regions:
                x1, y1, x2, y2 = map(int, regions["中央"])
                central_image = screenshot[y1:y2, x1:x2]
                gray = cv2.cvtColor(central_image, cv2.COLOR_BGR2GRAY)
                _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
                corners = cv2.goodFeaturesToTrack(binary, 100, 0.02, 10)
                if corners is not None:
                    points = np.intp(corners).reshape(-1, 2)
                    clustering = DBSCAN(eps=20, min_samples=1).fit(points)
                    for label in set(clustering.labels_):
                        pts = points[clustering.labels_ == label]
                        cx, cy = np.mean(pts, axis=0)
                        central_nodes.append((int(cx) + x1, int(cy) + y1)) # Re-add offset

            # Find camp nodes (xingying)
            camp_nodes = []
            # This is a simplified version of camp detection for integration
            hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
            lower_orange_yellow = np.array([15, 100, 100])
            upper_orange_yellow = np.array([35, 255, 255])
            mask = cv2.inRange(hsv, lower_orange_yellow, upper_orange_yellow)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                if 100 < cv2.contourArea(cnt) < 1000:
                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        camp_nodes.append((cx, cy))

            # 3. Combine all nodes and remove duplicates
            all_nodes = piece_nodes + central_nodes + camp_nodes
            
            # Use clustering to merge very close points (e.g., a piece on a camp)
            final_nodes_clustering = DBSCAN(eps=15, min_samples=1).fit(all_nodes)
            final_nodes = []
            for label in set(final_nodes_clustering.labels_):
                pts = np.array(all_nodes)[final_nodes_clustering.labels_ == label]
                cx, cy = np.mean(pts, axis=0)
                final_nodes.append((int(cx), int(cy)))

            self.log_to_dashboard(f"共找到 {len(final_nodes)} 个独立节点。")

            # 4. Draw the nodes on the image
            overlay = screenshot.copy()
            for (cx, cy) in final_nodes:
                cv2.circle(overlay, (cx, cy), 5, (0, 255, 0), -1) # Green filled circle
                cv2.circle(overlay, (cx, cy), 6, (0, 0, 0), 1)   # Black outline

            cv2.imshow("All Nodes Distribution", overlay)
            self.log_to_dashboard("已弹出“All Nodes Distribution”窗口。")

        except Exception as e:
            self.log_to_dashboard(f"[严重错误] 生成节点分布图时出错: {e}")
        finally:
            self._force_set_topmost()

if __name__ == "__main__":
    root = tk.Tk()
    app = DashboardApp(root)
    root.mainloop()
