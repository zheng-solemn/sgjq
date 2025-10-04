import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Any
from collections import Counter
from sklearn.cluster import KMeans
from dataclasses import dataclass
import time

# --- 导入核心模块 ---
from app.utils.vision.templates_manager import TemplatesManager

# ==============================================================================
# --- 核心算法模块 (V31 - 终极真理版) ---
# ==============================================================================

@dataclass
class DetectionResult:
    template: object
    location: tuple
    confidence: float
    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        x1, y1 = self.location
        h, w, _ = self.template.image.shape
        return (x1, y1, x1 + w, y1 + h)

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

def find_all_matches_with_color_mask(image: np.ndarray, templates_by_color: Dict[str, List], color_ranges: Dict, threshold: float) -> List[DetectionResult]:
    results = []
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    for color, templates in templates_by_color.items():
        if color not in color_ranges: continue
        lower = np.array(color_ranges[color]['lower']); upper = np.array(color_ranges[color]['upper'])
        mask = cv2.inRange(hsv_image, lower, upper)
        masked_image = cv2.bitwise_and(image, image, mask=mask)
        gray_masked_image = cv2.cvtColor(masked_image, cv2.COLOR_BGR2GRAY)
        for template in templates:
            hsv_template = cv2.cvtColor(template.image, cv2.COLOR_BGR2HSV)
            template_mask = cv2.inRange(hsv_template, lower, upper)
            masked_template = cv2.bitwise_and(template.image, template.image, mask=template_mask)
            gray_masked_template = cv2.cvtColor(masked_template, cv2.COLOR_BGR2GRAY)
            if gray_masked_template.shape[0] > gray_masked_image.shape[0] or \
               gray_masked_template.shape[1] > gray_masked_image.shape[1] or \
               np.sum(gray_masked_template) == 0: continue
            match_result = cv2.matchTemplate(gray_masked_image, gray_masked_template, cv2.TM_CCOEFF_NORMED)
            locs = np.where(match_result >= threshold)
            for pt in zip(*locs[::-1]):
                results.append(DetectionResult(template, pt, match_result[pt[1], pt[0]]))
    return results

class GameAnalyzer:
    def __init__(self, templates_path: str):
        self.tm = TemplatesManager(templates_path)
        self.hsv_color_ranges = {'blue':{'lower':[100,80,80],'upper':[130,255,255]},'green':{'lower':[35,40,40],'upper':[95,255,255]},'orange':{'lower':[5,150,150],'upper':[20,255,255]},'purple':{'lower':[135,80,80],'upper':[160,255,255]}}
        self.cn_to_en_map = {"司令":"commander","军长":"general","师长":"major","旅长":"colonel","团长":"captain","营长":"battalion","连长":"lieutenant","排长":"sergeant","工兵":"miner","地雷":"landmine","炸弹":"bomb","军旗":"flag", "行营":"xingying"}
        self.all_piece_types_cn = list(self.cn_to_en_map.keys())[:-1]

    def analyze_screenshot(self, screenshot: np.ndarray, match_threshold: float = 0.8, return_detections: bool = False) -> Any:
        templates_by_color = {}
        xingying_template = None
        for t in self.tm.get_all_templates():
            if t.piece_type == "xingying":
                xingying_template = t; continue
            if t.color not in templates_by_color: templates_by_color[t.color] = []
            templates_by_color[t.color].append(t)
        
        matches = find_all_matches_with_color_mask(screenshot, templates_by_color, self.hsv_color_ranges, match_threshold)
        
        if xingying_template:
            hsv_image = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
            all_color_mask = np.zeros(screenshot.shape[:2], dtype=np.uint8)
            for color in self.hsv_color_ranges:
                lower = np.array(self.hsv_color_ranges[color]['lower']); upper = np.array(self.hsv_color_ranges[color]['upper'])
                all_color_mask = cv2.bitwise_or(all_color_mask, cv2.inRange(hsv_image, lower, upper))
            neutral_mask = cv2.bitwise_not(all_color_mask)
            neutral_image = cv2.bitwise_and(screenshot, screenshot, mask=neutral_mask)
            gray_neutral_image = cv2.cvtColor(neutral_image, cv2.COLOR_BGR2GRAY)
            gray_template = cv2.cvtColor(xingying_template.image, cv2.COLOR_BGR2GRAY)
            match_result = cv2.matchTemplate(gray_neutral_image, gray_template, cv2.TM_CCOEFF_NORMED)
            locs = np.where(match_result >= 0.8)
            for pt in zip(*locs[::-1]):
                matches.append(DetectionResult(xingying_template, pt, match_result[pt[1], pt[0]]))

        detections = standard_non_max_suppression(matches, iou_threshold=0.3)
        if return_detections: return detections
        if not detections: return "未在截图中识别到任何棋子。"

        pieces_by_color: Dict[str, List[DetectionResult]] = {}
        for det in detections:
            color = det.template.color
            if color not in pieces_by_color: pieces_by_color[color] = []
            pieces_by_color[color].append(det)
            
        player_locations: Dict[str, str] = {}
        img_h, img_w, _ = screenshot.shape
        for color, dets in pieces_by_color.items():
            if not dets or color == 'neutral': continue
            avg_y = np.mean([d.location[1] for d in dets])
            if avg_y < img_h * 0.45: location = "上方"
            elif avg_y > img_h * 0.55: location = "下方"
            else: location = "左侧" if np.mean([d.location[0] for d in dets]) < img_w / 2 else "右侧"
            player_locations[color] = location

        timestamp = time.strftime("%Y%m%d%H%M-%S")
        report = [f"=============== [ {timestamp} ] (总棋子数: {len(detections)}个) ==============="]
        sorted_players = sorted(pieces_by_color.items(), key=lambda i: {"上方":0,"左侧":1,"下方":2,"右侧":3}.get(player_locations.get(i[0]), 99))

        for color, dets in sorted_players:
            if color == 'neutral': continue
            location = player_locations.get(color, "未知")
            report.append(f"【{location}玩家】 ({color.capitalize()})（棋子总数: {len(dets)}）")
            piece_counts = Counter(d.template.piece_type for d in dets)
            details = []
            for piece_cn in self.all_piece_types_cn:
                piece_en = self.cn_to_en_map[piece_cn]
                count = piece_counts.get(piece_en, 0)
                if count > 0: details.append(f"{piece_cn}x{count}")
            if details: report.append("  " + ", ".join(details))
            report.append("")

        return "\n".join(report)

    def get_player_regions(self, screenshot: np.ndarray, match_threshold: float = 0.7) -> Dict[str, Tuple[int, int, int, int]]:
        img_h, img_w, _ = screenshot.shape
        templates_by_color = {}
        for t in self.tm.get_all_templates():
            if t.piece_type == "xingying": continue
            if t.color not in templates_by_color: templates_by_color[t.color] = []
            templates_by_color[t.color].append(t)
        matches = find_all_matches_with_color_mask(screenshot, templates_by_color, self.hsv_color_ranges, threshold=match_threshold)
        detections = standard_non_max_suppression(matches, iou_threshold=0.3)
        return self._get_regions_from_clusters(detections, img_w, img_h)

    def _get_regions_from_clusters(self, detections: List[DetectionResult], img_w: int, img_h: int) -> Dict[str, Tuple[int, int, int, int]]:
        if len(detections) < 4: return {}
        points = np.array([((d.bbox[0]+d.bbox[2])/2, (d.bbox[1]+d.bbox[3])/2) for d in detections])
        kmeans = KMeans(n_clusters=4, random_state=0, n_init=10).fit(points)
        centers = kmeans.cluster_centers_
        img_cx, img_cy = img_w/2, img_h/2
        label_map = {}
        for i, (cx,cy) in enumerate(centers):
            if abs(cx-img_cx) > abs(cy-img_cy): label_map[i] = "左侧" if cx < img_cx else "右侧"
            else: label_map[i] = "上方" if cy < img_cy else "下方"
        bounds = {}
        for i in range(4):
            pts = points[kmeans.labels_ == i]
            if len(pts) > 0:
                min_x, min_y = np.min(pts, axis=0); max_x, max_y = np.max(pts, axis=0)
                bounds[label_map[i]] = (int(min_x), int(min_y), int(max_x), int(max_y))
        if all(k in bounds for k in ["上方","下方","左侧","右侧"]):
            bounds["中央"] = (bounds["左侧"][2], bounds["上方"][3], bounds["右侧"][0], bounds["下方"][1])
        return bounds
