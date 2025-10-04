import tkinter as tk
from pathlib import Path
import win32gui
import win32con
import win32api
from threading import Thread
import time
import cv2
import json

from app.utils.capture import WindowCapture
from app.services.game_analyzer import GameAnalyzer

# --- SINGLE UNIFIED LOGGER ---
def log_message(app, message: str):
    """Appends a message to the log panel."""
    app.info_text.config(state='normal')
    app.info_text.insert(tk.END, message + "\n\n")
    app.info_text.see(tk.END)
    app.info_text.config(state='disabled')

# --- UTILITY FUNCTIONS ---
def _force_set_topmost(app):
    if app.app_state.hwnd and win32gui.IsWindow(app.app_state.hwnd):
        try:
            win32gui.SetWindowPos(app.app_state.hwnd, win32con.HWND_TOPMOST, 0,0,0,0, win32con.SWP_NOMOVE|win32con.SWP_NOSIZE)
        except Exception: pass

def _get_full_roi(app):
    if not app.app_state.locked_regions or len(app.app_state.locked_regions) < 5: return None, None, None, None
    regions = app.app_state.locked_regions.values()
    min_x=min(r[0] for r in regions); min_y=min(r[1] for r in regions)
    max_x=max(r[2] for r in regions); max_y=max(r[3] for r in regions)
    return int(min_x), int(min_y), int(max_x), int(max_y)

# --- INITIALIZATION AND UI CALLBACKS ---

def initialize_analyzer(app):
    try:
        app.app_state.game_analyzer = GameAnalyzer("pictures/qizi_samples")
        log_message(app, "--- 战情室启动成功 (V32-最终修复版) ---")
        if app.regions_file.exists():
            try:
                with open(app.regions_file, 'r') as f: app.app_state.locked_regions = json.load(f)
                log_message(app, "[信息] 已成功从文件加载锁定的分区数据。")
            except Exception as e: log_message(app, f"[错误] 加载分区文件失败: {e}")
        else:
            log_message(app, "[信息] 未找到分区数据文件。请点击“2. 开始识别”以在首次识别时自动生成。")
            app.regions_file.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e: log_message(app, f"[严重错误] 分析器初始化失败: {e}")

def on_closing(app):
    app.is_recognizing = False
    if app.app_state.hwnd and win32gui.IsWindow(app.app_state.hwnd):
        try:
            win32gui.ShowWindow(app.app_state.hwnd, win32con.SW_MINIMIZE)
            win32gui.SetWindowPos(app.app_state.hwnd, win32con.HWND_NOTOPMOST, 0,0,0,0, win32con.SWP_NOMOVE|win32con.SWP_NOSIZE)
        except Exception: pass
    app.root.destroy()

def clear_log(app):
    app.info_text.config(state='normal')
    app.info_text.delete('1.0', tk.END)
    app.info_text.config(state='disabled')

# --- CORE FUNCTIONALITY CALLBACKS ---

def detect_game_window(app):
    log_message(app, "--- 开始检测游戏窗口 ---")
    try:
        app.app_state.window_capture = WindowCapture("JunQiRpg.exe", "四国军棋")
        app.app_state.hwnd = app.app_state.window_capture.hwnd
        if app.app_state.hwnd:
            win32gui.ShowWindow(app.app_state.hwnd, win32con.SW_RESTORE)
            _force_set_topmost(app)
            win32gui.SetForegroundWindow(app.app_state.hwnd)
            rect = win32gui.GetWindowRect(app.app_state.hwnd)
            log_message(app, f"成功检测到游戏窗口！句柄: {app.app_state.hwnd}, 尺寸: {rect[2]-rect[0]}x{rect[3]-rect[1]}")
        else: log_message(app, "错误: 未找到匹配的游戏窗口。")
    except Exception as e: log_message(app, f"检测窗口时发生未知错误: {e}")

def start_recognition(app, use_roi: bool):
    if not app.app_state.window_capture: return log_message(app, "[错误] 请先检测游戏窗口。")
    screenshot = app.app_state.window_capture.get_screenshot()
    if screenshot is None: return log_message(app, "[错误] 获取截图失败。")

    if not app.app_state.locked_regions:
        log_message(app, "[信息] 首次运行，正在自动分析并锁定分区...")
        try:
            regions = app.app_state.game_analyzer.get_player_regions(screenshot)
            if len(regions) < 5: return log_message(app, "[错误] 未能计算出完整的5个区域。")
            app.app_state.locked_regions = {k: tuple(map(int, v)) for k, v in regions.items()}
            with open(app.regions_file, 'w') as f: json.dump(app.app_state.locked_regions, f, indent=4)
            log_message(app, "[成功] 初始分区已自动锁定并保存！")
        except Exception as e: return log_message(app, f"[严重错误] 自动锁定分区时出错: {e}")

    image_to_analyze = screenshot
    if use_roi:
        x1, y1, x2, y2 = _get_full_roi(app)
        if x1 is None: return log_message(app, "[错误] 分区数据不完整，无法计算ROI。")
        image_to_analyze = screenshot[y1:y2, x1:x2]
    
    report = app.app_state.game_analyzer.analyze_screenshot(image_to_analyze, match_threshold=0.8)
    log_message(app, report)
    _force_set_topmost(app)

def start_continuous_recognition(app):
    if app.is_recognizing: return
    if not app.app_state.window_capture: return log_message(app, "[错误] 请先检测游戏窗口。")
    app.is_recognizing = True
    app.button3.config(state='disabled'); app.button4.config(state='normal')
    app.recognition_thread = Thread(target=_continuous_recognition_worker, args=(app,), daemon=True)
    app.recognition_thread.start()
    log_message(app, "--- 连续识别已启动 ---")

def stop_continuous_recognition(app):
    if not app.is_recognizing: return
    app.is_recognizing = False
    app.button3.config(state='normal'); app.button4.config(state='disabled')
    log_message(app, "--- 连续识别已停止 ---")

def _continuous_recognition_worker(app):
    while app.is_recognizing:
        screenshot = app.app_state.window_capture.get_screenshot()
        if screenshot is None: time.sleep(0.5); continue
        report = app.app_state.game_analyzer.analyze_screenshot(screenshot, match_threshold=0.8)
        app.root.after(0, log_message, app, report)
        time.sleep(1)

# --- VISUALIZATION CALLBACKS ---

def visualize_regions(app):
    if not app.app_state.locked_regions: return log_message(app, "[错误] 未找到分区数据。")
    screenshot = app.app_state.window_capture.get_screenshot();
    if screenshot is None: return
    vis_image = screenshot.copy()
    colors = {"上方":(255,0,0),"下方":(0,255,0),"左侧":(0,0,255),"右侧":(255,255,0),"中央":(255,0,255)}
    for name, (x1,y1,x2,y2) in app.app_state.locked_regions.items():
        cv2.rectangle(vis_image, (x1,y1), (x2,y2), colors.get(name,(255,255,255)), 2)
        cv2.putText(vis_image, name, (x1+5,y1+20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colors.get(name,(255,255,255)), 2)
    cv2.imshow("分区图 (按钮5)", vis_image); cv2.waitKey(1); _force_set_topmost(app)

def visualize_plus_region(app):
    x1, y1, x2, y2 = _get_full_roi(app)
    if x1 is None: return log_message(app, "[错误] 分区数据不完整。")
    screenshot = app.app_state.window_capture.get_screenshot();
    if screenshot is None: return
    vis_image = screenshot.copy()
    cv2.rectangle(vis_image, (x1,y1), (x2,y2), (0,0,255), 2)
    cv2.imshow("ROI检测区域 (按钮6)", vis_image); cv2.waitKey(1); _force_set_topmost(app)

def visualize_theoretical_nodes(app):
    if not app.app_state.locked_regions: return log_message(app, "[错误] 未找到分区数据。")
    screenshot = app.app_state.window_capture.get_screenshot();
    if screenshot is None: return
    vis_image = screenshot.copy()
    all_nodes = []
    specs = {"上方":(6,5),"下方":(6,5),"左侧":(6,5),"右侧":(6,5),"中央":(3,3)}
    for key, (rows,cols) in specs.items():
        if key in app.app_state.locked_regions:
            x1,y1,x2,y2 = map(int, app.app_state.locked_regions[key])
            cell_w, cell_h = (x2-x1)/cols, (y2-y1)/rows
            for r in range(rows):
                for c in range(cols):
                    all_nodes.append((int(x1+(c+0.5)*cell_w), int(y1+(r+0.5)*cell_h)))
    for (cx,cy) in all_nodes: cv2.circle(vis_image, (cx,cy), 5, (0,255,0), -1)
    log_message(app, f"成功生成了 {len(all_nodes)} 个理论棋盘节点。")
    cv2.imshow("理论节点分布 (按钮7)", vis_image); cv2.waitKey(1); _force_set_topmost(app)

def visualize_legacy_plus_region(app):
    if not app.app_state.locked_regions: return log_message(app, "[错误] 未找到分区数据。")
    screenshot = app.app_state.window_capture.get_screenshot();
    if screenshot is None: return
    regions = app.app_state.locked_regions
    if not all(k in regions for k in ["上方","下方","左侧","右侧"]): return log_message(app, "[错误] 区域信息不完整。")
    vis_image = screenshot.copy()
    h_x1,h_y1,_,h_y2 = map(int,regions["左侧"]); _,_,h_x2,_ = map(int,regions["右侧"])
    v_x1,v_y1,v_x2,_ = map(int,regions["上方"]); _,_,_,v_y2 = map(int,regions["下方"])
    cv2.rectangle(vis_image, (h_x1,h_y1), (h_x2,h_y2), (0,255,0), 2)
    cv2.rectangle(vis_image, (v_x1,v_y1), (v_x2,v_y2), (0,255,0), 2)
    cv2.imshow("旧版'+'区域 (按钮9)", vis_image); cv2.waitKey(1); _force_set_topmost(app)

def visualize_detected_nodes(app):
    if not app.app_state.window_capture: return log_message(app, "[错误] 请先检测游戏窗口。")
    screenshot = app.app_state.window_capture.get_screenshot();
    if screenshot is None: return
    log_message(app, "[信息] 正在全图搜索棋子节点...")
    detections = app.app_state.game_analyzer.analyze_screenshot(screenshot, return_detections=True)
    vis_image = screenshot.copy()
    for det in detections:
        b_x1,b_y1,b_x2,b_y2 = det.bbox
        cv2.rectangle(vis_image, (b_x1,b_y1), (b_x2,b_y2), (0,255,0), 2)
    log_message(app, f"全图共检测到 {len(detections)} 个节点。")
    cv2.imshow("全图检测节点 (按钮10)", vis_image); cv2.waitKey(1); _force_set_topmost(app)
