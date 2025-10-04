import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Any
from collections import Counter
from sklearn.cluster import KMeans
from dataclasses import dataclass
from multiprocessing import Pool, cpu_count

# --- 导入核心模块 ---
from vision.templates_manager import TemplatesManager

# ==============================================================================
# --- 并行处理工作函数 (必须定义在顶层) ---
# ==============================================================================
def _parallel_worker(args):
    image, templates, color_ranges, threshold, color_name = args
    results = []
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_bound = np.array(color_ranges[color_name]['lower'])
    upper_bound = np.array(color_ranges[color_name]['upper'])
    mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
    gray_masked_image = cv2.bitwise_and(image, image, mask=mask)
    gray_masked_image = cv2.cvtColor(gray_masked_image, cv2.COLOR_BGR2GRAY)

    for template in templates:
        hsv_template = cv2.cvtColor(template.image, cv2.COLOR_BGR2HSV)
        template_mask = cv2.inRange(hsv_template, lower_bound, upper_bound)
        masked_template = cv2.bitwise_and(template.image, template.image, mask=template_mask)
        gray_masked_template = cv2.cvtColor(masked_template, cv2.COLOR_BGR2GRAY)

        if gray_masked_template.shape[0] > gray_masked_image.shape[0] or \
           gray_masked_template.shape[1] > gray_masked_image.shape[1] or \
           np.sum(gray_masked_template) == 0:
            continue

        match_result = cv2.matchTemplate(gray_masked_image, gray_masked_template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(match_result >= threshold)

        for pt in zip(*locations[::-1]):
            confidence = match_result[pt[1], pt[0]]
            results.append(DetectionResult(template=template, location=pt, confidence=confidence))

    return results

# ==============================================================================
# --- 核心算法模块 ---
# ==============================================================================

@dataclass
class DetectionResult:
    template: object
    location: tuple
    confidence: float

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        x1, y1 = self.location
        x2 = x1 + self.template.shape[0]
        y2 = y1 + self.template.shape[1]
        return (x1, y1, x2, y2)

    @property
    def piece_name(self) -> str:
        return self.template.piece_type

    @property
    def color(self) -> str:
        return self.template.color

def standard_non_max_suppression(detections: List[DetectionResult], iou_threshold: float) -> List[DetectionResult]:
    if not detections: return []
    detections.sort(key=lambda x: x.confidence, reverse=True)
    final_detections = []
    while detections:
        best = detections.pop(0)
        final_detections.append(best)
        remaining = []
        for other in detections:
            x1=max(best.bbox[0],other.bbox[0]); y1=max(best.bbox[1],other.bbox[1])
            x2=min(best.bbox[2],other.bbox[2]); y2=min(best.bbox[3],other.bbox[3])
            intersection=max(0,x2-x1)*max(0,y2-y1)
            area_best=(best.bbox[2]-best.bbox[0])*(best.bbox[3]-best.bbox[1])
            area_other=(other.bbox[2]-other.bbox[0])*(other.bbox[3]-other.bbox[1])
            union=area_best+area_other-intersection
            iou=intersection/union if union>0 else 0
            if iou<iou_threshold: remaining.append(other)
        detections=remaining
    return final_detections

# --- Constants for Piece Roster and Formatting ---
FULL_ROSTER = {
    "司令": 1, "军长": 1, "师长": 2, "旅长": 2, "团长": 2, "营长": 2,
    "连长": 3, "排长": 3, "工兵": 3, "地雷": 3, "炸弹": 2, "军旗": 1
}

COLOR_TAG_MAP = {
    "司令": "p_purple", "军长": "p_red", "师长": "p_orange", "旅长": "p_yellow",
    "团长": "p_blue", "工兵": "p_green", "炸弹": "p_bold_red", "军旗": "p_cyan"
}

class GameAnalyzer:
    def __init__(self, templates_path: str):
        self.templates_manager = TemplatesManager(templates_path)
        if not self.templates_manager.get_all_templates():
            raise Exception("错误: 模板加载失败。")
        self.hsv_color_ranges = {
            'blue':   {'lower': [100, 80, 80], 'upper': [130, 255, 255]},
            'green':  {'lower': [35, 40, 40], 'upper': [95, 255, 255]},
            'orange': {'lower': [5, 150, 150], 'upper': [20, 255, 255]},
            'purple': {'lower': [135, 80, 80], 'upper': [160, 255, 255]}
        }
        self.cn_to_en_map = {
            "司令": "commander", "军长": "general", "师长": "major", "旅长": "colonel",
            "团长": "captain", "营长": "battalion", "连长": "lieutenant", "排长": "sergeant",
            "工兵": "miner", "地雷": "landmine", "炸弹": "bomb", "军旗": "flag"
        }
        self.pool = Pool(processes=cpu_count())

    def analyze_screenshot(self, screenshot: np.ndarray, match_threshold: float = 0.7, return_detections: bool = False) -> Any:
        templates_by_color: Dict[str, List] = {}
        for t in self.templates_manager.get_all_templates():
            if t.piece_type == "xingying": continue
            if t.color not in templates_by_color: templates_by_color[t.color] = []
            templates_by_color[t.color].append(t)

        tasks = [(screenshot, templates, self.hsv_color_ranges, match_threshold, color) for color, templates in templates_by_color.items()]

        results_from_pool = self.pool.map(_parallel_worker, tasks)
        all_matches = [item for sublist in results_from_pool for item in sublist]
        detections = standard_non_max_suppression(all_matches, iou_threshold=0.3)

        if return_detections:
            return detections

        total_detection_count = len(detections)

        if not detections:
            return {
                'total_count': 0,
                'report_items': [{'type': 'header', 'text': "未在截图中识别到任何棋子。"}]
            }

        img_h, img_w, _ = screenshot.shape
        pieces_by_color: Dict[str, List[DetectionResult]] = {}
        for det in detections:
            color = det.template.color
            if color not in pieces_by_color: pieces_by_color[color] = []
            pieces_by_color[color].append(det)

        player_locations: Dict[str, str] = {}
        for color, dets in pieces_by_color.items():
            if not dets: continue
            avg_x = np.mean([d.location[0] for d in dets]); avg_y = np.mean([d.location[1] for d in dets])
            if avg_y < img_h * 0.45: location = "上方"
            elif avg_y > img_h * 0.55: location = "下方"
            elif avg_x < img_w / 2: location = "左侧"
            else: location = "右侧"
            player_locations[color] = location

        report_items = []
        location_order = {"上方": 0, "左侧": 1, "下方": 2, "右侧": 3}
        sorted_players = sorted(pieces_by_color.items(), key=lambda item: location_order.get(player_locations.get(item[0]), 99))

        for color, dets in sorted_players:
            location = player_locations.get(color, "未知")
            player_piece_count = len(dets)
            report_items.append({
                'type': 'header',
                'text': f"--- 【{location}玩家】 ({color.capitalize()}) ---（剩余棋子：{player_piece_count}个）",
                'color': color
            })

            counts = Counter(d.template.piece_type for d in dets)

            player_report_data = []
            for piece_cn, piece_en in self.cn_to_en_map.items():
                current_count = counts.get(piece_en, 0)
                piece_info = {
                    'text': f"{piece_cn}x{current_count}",
                    'color_tag': COLOR_TAG_MAP.get(piece_cn, 'p_default'),
                    'is_eliminated': current_count == 0
                }
                player_report_data.append(piece_info)

            report_items.append({'type': 'piece_line', 'pieces': player_report_data})
            report_items.append({'type': 'separator'})

        return {
            'total_count': total_detection_count,
            'report_items': report_items
        }

    def get_all_detections(self, board_image: np.ndarray, match_threshold: float = 0.8) -> List[DetectionResult]:
        """兼容性方法 - 调用analyze_screenshot获取检测结果"""
        return self.analyze_screenshot(board_image, match_threshold, return_detections=True)

    def get_player_regions(self, screenshot: np.ndarray, match_threshold: float = 0.7) -> Dict[str, Tuple[int, int, int, int]]:
        img_h, img_w, _ = screenshot.shape
        templates_by_color: Dict[str, List] = {}
        for t in self.templates_manager.get_all_templates():
            if t.piece_type == "xingying": continue
            if t.color not in templates_by_color: templates_by_color[t.color] = []
            templates_by_color[t.color].append(t)

        tasks = [(screenshot, templates, self.hsv_color_ranges, match_threshold, color) for color, templates in templates_by_color.items()]
        results_from_pool = self.pool.map(_parallel_worker, tasks)
        all_matches = [item for sublist in results_from_pool for item in sublist]

        detections = standard_non_max_suppression(all_matches, iou_threshold=0.3)
        return self._get_regions_from_clusters(detections, img_w, img_h)

    def _get_regions_from_clusters(self, detections: List[DetectionResult], img_w: int, img_h: int) -> Dict[str, Tuple[int, int, int, int]]:
        if not detections: return {}
        num_clusters = min(4, len(detections))
        if num_clusters < 4: return {"未知": (0,0,img_w,img_h)}
        centers = [(det.location[0], det.location[1]) for det in detections]
        kmeans = KMeans(n_clusters=num_clusters, random_state=0, n_init='auto').fit(centers)
        clustered_dets = {i: [] for i in range(num_clusters)}
        for i, det in enumerate(detections): clustered_dets[kmeans.labels_[i]].append(det)
        player_clusters = {}
        for label, dets in clustered_dets.items():
            if not dets: continue
            avg_x = np.mean([d.location[0] for d in dets]); avg_y = np.mean([d.location[1] for d in dets])
            if avg_y < img_h * 0.4: region_name = "上方"
            elif avg_y > img_h * 0.6: region_name = "下方"
            elif avg_x < img_w / 2: region_name = "左侧"
            else: region_name = "右侧"
            player_clusters[region_name] = dets
        player_bounds = {}
        for name, dets in player_clusters.items():
            min_x=min(d.location[0] for d in dets); min_y=min(d.location[1] for d in dets)
            max_x=max(d.location[0]+d.template.shape[0] for d in dets); max_y=max(d.location[1]+d.template.shape[1] for d in dets)
            player_bounds[name] = (min_x, min_y, max_x, max_y)
        if all(k in player_bounds for k in ["上方", "下方", "左侧", "右侧"]):
            central_x1=player_bounds["左侧"][2]; central_x2=player_bounds["右侧"][0]
            central_y1=player_bounds["上方"][3]; central_y2=player_bounds["下方"][1]
            player_bounds["中央"] = (central_x1, central_y1, central_x2, central_y2)
        return player_bounds

    def visualize_regions_on_image(self, image: np.ndarray, regions: Dict) -> np.ndarray:
        vis_image = image.copy()
        colors = {
            "上方": (255, 0, 0), "下方": (0, 255, 0),
            "左侧": (0, 0, 255), "右侧": (255, 255, 0),
            "中央": (255, 0, 255)
        }
        for name, (x1, y1, x2, y2) in regions.items():
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), colors.get(name, (255,255,255)), 2)
            cv2.putText(vis_image, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colors.get(name, (255,255,255)), 2)
        return vis_image

    def __del__(self):
        self.pool.close()
        self.pool.join()