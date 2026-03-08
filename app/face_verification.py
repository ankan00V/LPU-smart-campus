import base64
import logging
import os
import shutil
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.error import URLError
from urllib.request import urlopen

import numpy as np

try:
    import cv2
except Exception:  # noqa: BLE001
    cv2 = None


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

_CASCADE_CACHE: dict[str, Any] = {}
_CASCADE_ERROR: dict[str, str] = {}
_DNN_RUNTIME_CACHE: dict[str, Any] = {}
_DNN_RUNTIME_LOCK = threading.Lock()
_DNN_INFERENCE_LOCK = threading.Lock()

_YUNET_MODEL_URL = (
    os.getenv("FACE_YUNET_MODEL_URL")
    or "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx"
).strip()
_SFACE_MODEL_URL = (
    os.getenv("FACE_SFACE_MODEL_URL")
    or "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx"
).strip()


@dataclass(slots=True)
class FaceVerificationConfig:
    min_similarity: float
    min_consecutive_frames: int
    max_frames: int
    min_frame_width: int
    min_frame_height: int
    blur_threshold: float
    min_face_area_ratio: float
    max_center_offset_ratio: float
    min_eye_distance_ratio: float
    min_lower_texture_ratio: float
    min_contrast: float
    min_liveness_motion: float
    min_liveness_pose_delta: float
    min_liveness_yaw_range: float
    min_liveness_pitch_range: float
    min_liveness_texture_jitter: float
    min_liveness_contrast_jitter: float
    min_primary_face_dominance_ratio: float


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return float(default)
    try:
        return float(raw.strip())
    except ValueError:
        return float(default)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return int(default)
    try:
        return int(raw.strip())
    except ValueError:
        return int(default)


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name, "true" if default else "false") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _l2_normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm < 1e-8:
        return np.zeros_like(vector, dtype=np.float32)
    return (vector / norm).astype(np.float32)


def _load_config() -> FaceVerificationConfig:
    requested_similarity = _env_float(
        "FACE_MATCH_MIN_SIMILARITY",
        _env_float("FACE_MATCH_PASS_THRESHOLD", 0.80),
    )
    min_similarity = max(0.80, min(1.0, requested_similarity))
    min_frames = max(5, _env_int("FACE_MATCH_MIN_FRAMES", 5))
    max_frames = max(min_frames, _env_int("FACE_MATCH_MAX_FRAMES", 12))
    return FaceVerificationConfig(
        min_similarity=min_similarity,
        min_consecutive_frames=min_frames,
        max_frames=max_frames,
        min_frame_width=max(160, _env_int("FACE_MIN_FRAME_WIDTH", 280)),
        min_frame_height=max(160, _env_int("FACE_MIN_FRAME_HEIGHT", 280)),
        blur_threshold=max(1.0, _env_float("FACE_ANTI_SPOOF_BLUR_THRESHOLD", 70.0)),
        min_face_area_ratio=max(0.03, min(0.9, _env_float("FACE_ANTI_SPOOF_MIN_FACE_AREA_RATIO", 0.09))),
        max_center_offset_ratio=max(0.05, min(0.95, _env_float("FACE_FACE_CENTER_OFFSET_MAX_RATIO", 0.36))),
        min_eye_distance_ratio=max(0.05, min(0.9, _env_float("FACE_ANTI_SPOOF_MIN_EYE_DISTANCE_RATIO", 0.13))),
        min_lower_texture_ratio=max(0.02, min(2.5, _env_float("FACE_ANTI_SPOOF_MIN_LOWER_TEXTURE_RATIO", 0.18))),
        min_contrast=max(1.0, _env_float("FACE_ANTI_SPOOF_MIN_CONTRAST", 12.0)),
        min_liveness_motion=max(0.001, _env_float("FACE_LIVENESS_MIN_MOTION", 0.018)),
        min_liveness_pose_delta=max(0.001, _env_float("FACE_LIVENESS_MIN_POSE_DELTA", 0.012)),
        min_liveness_yaw_range=max(0.002, _env_float("FACE_LIVENESS_MIN_YAW_RANGE", 0.012)),
        min_liveness_pitch_range=max(0.002, _env_float("FACE_LIVENESS_MIN_PITCH_RANGE", 0.008)),
        min_liveness_texture_jitter=max(0.0001, _env_float("FACE_LIVENESS_MIN_TEXTURE_JITTER", 0.011)),
        min_liveness_contrast_jitter=max(0.01, _env_float("FACE_LIVENESS_MIN_CONTRAST_JITTER", 0.55)),
        min_primary_face_dominance_ratio=max(
            1.3,
            _env_float("FACE_PRIMARY_FACE_DOMINANCE_RATIO", 3.0),
        ),
    )


def _face_provider() -> str:
    provider = (os.getenv("FACE_VERIFICATION_PROVIDER", "auto") or "").strip().lower()
    if provider not in {"auto", "dnn", "heuristic"}:
        return "auto"
    return provider


def _dnn_model_cache_dir() -> Path:
    raw = (os.getenv("FACE_MODEL_CACHE_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return PROJECT_ROOT / ".model_cache" / "opencv"


def _dnn_model_path(env_name: str, default_name: str) -> Path:
    raw = (os.getenv(env_name) or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _dnn_model_cache_dir() / default_name


def _download_file(url: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
    try:
        with urlopen(url, timeout=45) as response, temp_path.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        if temp_path.stat().st_size < 4096:
            raise RuntimeError(f"Downloaded model file is too small: {target_path.name}")
        temp_path.replace(target_path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _ensure_model_file(path: Path, url: str) -> Path:
    if path.exists() and path.stat().st_size >= 4096:
        return path
    if not _env_bool("FACE_DNN_AUTO_DOWNLOAD", default=True):
        raise RuntimeError(f"Missing OpenCV model file: {path}")
    if not url:
        raise RuntimeError(f"Missing download URL for OpenCV model: {path.name}")
    try:
        _download_file(url, path)
    except (URLError, OSError, RuntimeError) as exc:
        raise RuntimeError(f"Unable to fetch OpenCV model {path.name}: {exc}") from exc
    return path


def _load_dnn_runtime() -> tuple[dict[str, Any] | None, str | None]:
    if cv2 is None:
        return None, "OpenCV is not installed"

    with _DNN_RUNTIME_LOCK:
        cached = _DNN_RUNTIME_CACHE.get("runtime")
        cached_error = _DNN_RUNTIME_CACHE.get("error")
        if cached or cached_error:
            return cached, cached_error

        detector_path = _dnn_model_path("FACE_YUNET_MODEL_PATH", "face_detection_yunet_2023mar.onnx")
        recognizer_path = _dnn_model_path("FACE_SFACE_MODEL_PATH", "face_recognition_sface_2021dec.onnx")
        try:
            detector_path = _ensure_model_file(detector_path, _YUNET_MODEL_URL)
            recognizer_path = _ensure_model_file(recognizer_path, _SFACE_MODEL_URL)
            detector = cv2.FaceDetectorYN_create(
                str(detector_path),
                "",
                (320, 320),
                max(0.5, min(0.98, _env_float("FACE_DNN_DETECTION_SCORE_THRESHOLD", 0.88))),
                max(0.1, min(0.9, _env_float("FACE_DNN_DETECTION_NMS_THRESHOLD", 0.3))),
                max(100, _env_int("FACE_DNN_DETECTION_TOPK", 5000)),
            )
            recognizer = cv2.FaceRecognizerSF_create(str(recognizer_path), "")
            runtime = {
                "detector": detector,
                "recognizer": recognizer,
                "detector_path": str(detector_path),
                "recognizer_path": str(recognizer_path),
            }
            _DNN_RUNTIME_CACHE["runtime"] = runtime
            _DNN_RUNTIME_CACHE["error"] = None
            return runtime, None
        except Exception as exc:  # noqa: BLE001
            error = str(exc).strip() or "Unable to initialize OpenCV DNN face runtime"
            _DNN_RUNTIME_CACHE["runtime"] = None
            _DNN_RUNTIME_CACHE["error"] = error
            return None, error


def _resolve_active_provider(*, strict: bool = False) -> tuple[str, str | None]:
    provider = _face_provider()
    if provider == "heuristic":
        return "heuristic", None

    runtime, error = _load_dnn_runtime()
    if runtime is not None:
        return "dnn", None
    if provider == "dnn" or strict:
        return "heuristic", error or "OpenCV DNN runtime unavailable"
    return "heuristic", error


def _relaxed_enrollment_config(config: FaceVerificationConfig) -> FaceVerificationConfig:
    # Enrollment capture should stay secure, but tolerate real-world lighting/camera variance.
    return FaceVerificationConfig(
        min_similarity=config.min_similarity,
        min_consecutive_frames=max(3, config.min_consecutive_frames - 1),
        max_frames=max(config.max_frames, 16),
        min_frame_width=max(180, int(config.min_frame_width * 0.85)),
        min_frame_height=max(180, int(config.min_frame_height * 0.85)),
        blur_threshold=max(25.0, config.blur_threshold * 0.25),
        min_face_area_ratio=max(0.045, config.min_face_area_ratio * 0.55),
        max_center_offset_ratio=min(0.56, config.max_center_offset_ratio + 0.18),
        min_eye_distance_ratio=max(0.10, config.min_eye_distance_ratio * 0.65),
        min_lower_texture_ratio=max(0.08, config.min_lower_texture_ratio * 0.45),
        min_contrast=max(6.0, config.min_contrast * 0.45),
        min_liveness_motion=max(0.001, config.min_liveness_motion * 0.75),
        min_liveness_pose_delta=max(0.001, config.min_liveness_pose_delta * 0.75),
        min_liveness_yaw_range=max(0.002, config.min_liveness_yaw_range * 0.60),
        min_liveness_pitch_range=max(0.002, config.min_liveness_pitch_range * 0.60),
        min_liveness_texture_jitter=max(0.0001, config.min_liveness_texture_jitter * 0.75),
        min_liveness_contrast_jitter=max(0.05, config.min_liveness_contrast_jitter * 0.55),
        min_primary_face_dominance_ratio=max(1.2, config.min_primary_face_dominance_ratio * 0.82),
    )


def _decode_data_url_to_bgr(image_data_url: str) -> np.ndarray | None:
    if not image_data_url or "," not in image_data_url:
        return None
    if cv2 is None:
        return None
    try:
        payload = image_data_url.split(",", 1)[1]
        raw = base64.b64decode(payload, validate=False)
        arr = np.frombuffer(raw, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:  # noqa: BLE001
        return None


def _load_cascade(filename: str) -> tuple[Any | None, str | None]:
    if cv2 is None:
        return None, "OpenCV is not installed"
    if filename in _CASCADE_CACHE:
        return _CASCADE_CACHE[filename], _CASCADE_ERROR.get(filename)
    try:
        path = cv2.data.haarcascades + filename
        cascade = cv2.CascadeClassifier(path)
        if cascade.empty():
            _CASCADE_ERROR[filename] = f"Unable to load cascade: {filename}"
            return None, _CASCADE_ERROR[filename]
        _CASCADE_CACHE[filename] = cascade
        return cascade, None
    except Exception as exc:  # noqa: BLE001
        _CASCADE_ERROR[filename] = str(exc)
        return None, _CASCADE_ERROR[filename]


def _detect_face_boxes(gray: np.ndarray) -> list[tuple[int, int, int, int]]:
    def _normalize(faces: Any) -> list[tuple[int, int, int, int]]:
        normalized = [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]
        normalized.sort(key=lambda item: int(item[2]) * int(item[3]), reverse=True)
        return normalized

    primary, _ = _load_cascade("haarcascade_frontalface_default.xml")
    if primary is not None:
        quick_passes = [
            (gray, 1.08, 5, (60, 60)),
            (gray, 1.06, 4, (50, 50)),
        ]
        for source, scale_factor, min_neighbors, min_size in quick_passes:
            faces = primary.detectMultiScale(
                source,
                scaleFactor=scale_factor,
                minNeighbors=min_neighbors,
                minSize=min_size,
            )
            if len(faces) > 0:
                return _normalize(faces)

    fallback_sources = [gray]
    try:
        fallback_sources.append(cv2.equalizeHist(gray))
    except Exception:  # noqa: BLE001
        pass
    fallback_cascades = [
        "haarcascade_frontalface_default.xml",
        "haarcascade_frontalface_alt2.xml",
    ]
    fallback_passes = [
        (1.05, 3, (44, 44)),
        (1.03, 2, (36, 36)),
    ]
    for source in fallback_sources:
        for cascade_name in fallback_cascades:
            cascade, _ = _load_cascade(cascade_name)
            if cascade is None:
                continue
            for scale_factor, min_neighbors, min_size in fallback_passes:
                faces = cascade.detectMultiScale(
                    source,
                    scaleFactor=scale_factor,
                    minNeighbors=min_neighbors,
                    minSize=min_size,
                )
                if len(faces) > 0:
                    return _normalize(faces)
    return []


def _select_eye_pair(
    eyes: Sequence[tuple[int, int, int, int]],
    face_width: int,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    if len(eyes) < 2:
        return None
    best: tuple[float, tuple[float, float], tuple[float, float]] | None = None
    for i in range(len(eyes)):
        ex1, ey1, ew1, eh1 = eyes[i]
        c1 = (ex1 + ew1 / 2.0, ey1 + eh1 / 2.0)
        a1 = float(ew1 * eh1)
        for j in range(i + 1, len(eyes)):
            ex2, ey2, ew2, eh2 = eyes[j]
            c2 = (ex2 + ew2 / 2.0, ey2 + eh2 / 2.0)
            a2 = float(ew2 * eh2)
            horizontal = abs(c2[0] - c1[0]) / max(float(face_width), 1.0)
            vertical = abs(c2[1] - c1[1]) / max(float(face_width), 1.0)
            if horizontal < 0.12:
                continue
            score = horizontal - (0.6 * vertical) + (0.0005 * min(a1, a2))
            if best is None or score > best[0]:
                if c1[0] <= c2[0]:
                    best = (score, c1, c2)
                else:
                    best = (score, c2, c1)
    if best is None:
        return None
    return best[1], best[2]


def _extract_eye_pair(
    gray: np.ndarray,
    face_box: tuple[int, int, int, int],
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    eye_cascade, _ = _load_cascade("haarcascade_eye_tree_eyeglasses.xml")
    if eye_cascade is None:
        eye_cascade, _ = _load_cascade("haarcascade_eye.xml")
    if eye_cascade is None:
        return None

    x, y, w, h = face_box
    upper = gray[y : y + int(h * 0.62), x : x + w]
    if upper.size == 0:
        return None
    eye_detection_passes = [
        (upper, 1.08, 4, (14, 14)),
        (cv2.equalizeHist(upper), 1.05, 3, (10, 10)),
    ]

    for source, scale_factor, min_neighbors, min_size in eye_detection_passes:
        eyes = eye_cascade.detectMultiScale(
            source,
            scaleFactor=scale_factor,
            minNeighbors=min_neighbors,
            minSize=min_size,
        )
        if len(eyes) == 0:
            continue
        local_eyes = [(int(ex), int(ey), int(ew), int(eh)) for ex, ey, ew, eh in eyes]
        pair = _select_eye_pair(local_eyes, w)
        if pair is None:
            continue
        left, right = pair
        return (left[0] + x, left[1] + y), (right[0] + x, right[1] + y)

    return None


def _fallback_eye_pair_from_face_box(
    face_box: tuple[int, int, int, int],
) -> tuple[tuple[float, float], tuple[float, float]]:
    x, y, w, h = face_box
    eye_y = y + (h * 0.38)
    left = (x + (w * 0.33), eye_y)
    right = (x + (w * 0.67), eye_y)
    return left, right


def _most_common_reason(reasons: Sequence[str]) -> str:
    counts: dict[str, int] = {}
    for reason in reasons:
        text = str(reason or "").strip() or "Face not recognized"
        counts[text] = counts.get(text, 0) + 1
    if not counts:
        return "Face not recognized"
    return max(counts.items(), key=lambda item: item[1])[0]


def _passes_relaxed_enrollment_quality(
    bundle: dict[str, Any],
    *,
    config: FaceVerificationConfig,
) -> bool:
    face_area = float(bundle.get("face_area_ratio", 0.0))
    center_offset = float(bundle.get("center_offset_ratio", 1.0))
    eye_distance = float(bundle.get("eye_distance_ratio", 0.0))
    blur = float(bundle.get("blur", 0.0))
    contrast = float(bundle.get("contrast", 0.0))
    texture_ratio = float(bundle.get("texture_ratio", 0.0))

    if face_area < config.min_face_area_ratio:
        return False
    if center_offset > min(0.62, config.max_center_offset_ratio + 0.1):
        return False
    if eye_distance < config.min_eye_distance_ratio:
        return False
    if blur < max(12.0, config.blur_threshold * 0.42):
        return False
    if contrast < max(4.5, config.min_contrast * 0.58):
        return False
    if texture_ratio < max(0.03, config.min_lower_texture_ratio * 0.45):
        return False
    return True


def _align_face_crop(
    gray: np.ndarray,
    face_box: tuple[int, int, int, int],
    eye_pair: tuple[tuple[float, float], tuple[float, float]] | None,
) -> np.ndarray:
    x, y, w, h = face_box
    roi = gray[y : y + h, x : x + w]
    if roi.size == 0:
        return cv2.resize(gray, (128, 128))

    if eye_pair is not None:
        left, right = eye_pair
        lx, ly = left[0] - x, left[1] - y
        rx, ry = right[0] - x, right[1] - y
        angle = np.degrees(np.arctan2(ry - ly, rx - lx))
        matrix = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle, 1.0)
        roi = cv2.warpAffine(roi, matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    y0 = int(h * 0.08)
    y1 = int(h * 0.94)
    x0 = int(w * 0.12)
    x1 = int(w * 0.88)
    inner = roi[y0:y1, x0:x1]
    if inner.size == 0:
        inner = roi
    return cv2.resize(inner, (128, 128))


def _blur_score(gray_face: np.ndarray) -> float:
    lap = cv2.Laplacian(gray_face, cv2.CV_64F)
    return float(np.var(lap))


def _edge_density(gray_face: np.ndarray) -> float:
    edges = cv2.Canny(gray_face, 45, 135)
    if edges.size == 0:
        return 0.0
    return float(np.count_nonzero(edges)) / float(edges.size)


def _occlusion_texture_ratio(gray_face: np.ndarray) -> float:
    h = gray_face.shape[0]
    split = int(h * 0.56)
    upper = gray_face[:split, :]
    lower = gray_face[split:, :]
    upper_density = _edge_density(upper)
    lower_density = _edge_density(lower)
    return lower_density / max(upper_density, 1e-6)


def _face_width_span_ratio(gray_face: np.ndarray, row_ratio: float) -> float:
    row = int(np.clip(row_ratio, 0.0, 1.0) * (gray_face.shape[0] - 1))
    edges = cv2.Canny(gray_face, 45, 135)
    xs = np.flatnonzero(edges[row] > 0)
    if xs.size < 2:
        return 0.0
    return float(xs[-1] - xs[0]) / float(gray_face.shape[1])


def _hog_embedding(gray_face: np.ndarray) -> np.ndarray:
    gx = cv2.Sobel(gray_face, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray_face, cv2.CV_32F, 0, 1, ksize=3)
    magnitude, angle = cv2.cartToPolar(gx, gy, angleInDegrees=False)
    angle = angle % np.pi
    bins = np.floor((angle / np.pi) * 9).astype(np.int32)
    bins = np.clip(bins, 0, 8)

    cell = 16
    histograms: list[np.ndarray] = []
    for y in range(0, 128, cell):
        for x in range(0, 128, cell):
            mag_cell = magnitude[y : y + cell, x : x + cell]
            bin_cell = bins[y : y + cell, x : x + cell]
            hist = np.bincount(bin_cell.ravel(), weights=mag_cell.ravel(), minlength=9).astype(np.float32)
            histograms.append(hist)
    return _l2_normalize(np.concatenate(histograms, axis=0))


def _lbp_histogram(gray_face: np.ndarray) -> np.ndarray:
    img = gray_face.astype(np.uint8)
    center = img[1:-1, 1:-1]
    lbp = np.zeros_like(center, dtype=np.uint8)
    lbp |= ((img[:-2, :-2] > center) << 7).astype(np.uint8)
    lbp |= ((img[:-2, 1:-1] > center) << 6).astype(np.uint8)
    lbp |= ((img[:-2, 2:] > center) << 5).astype(np.uint8)
    lbp |= ((img[1:-1, 2:] > center) << 4).astype(np.uint8)
    lbp |= ((img[2:, 2:] > center) << 3).astype(np.uint8)
    lbp |= ((img[2:, 1:-1] > center) << 2).astype(np.uint8)
    lbp |= ((img[2:, :-2] > center) << 1).astype(np.uint8)
    lbp |= (img[1:-1, :-2] > center).astype(np.uint8)
    hist, _ = np.histogram(lbp.ravel(), bins=64, range=(0, 256))
    return _l2_normalize(hist.astype(np.float32))


def _frequency_embedding(gray_face: np.ndarray) -> np.ndarray:
    spectrum = np.fft.fftshift(np.fft.fft2(gray_face.astype(np.float32)))
    magnitude = np.log1p(np.abs(spectrum))
    reduced = cv2.resize(magnitude, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32)
    return _l2_normalize(reduced.ravel())


def _geometry_embedding(
    gray_face: np.ndarray,
    face_box: tuple[int, int, int, int],
    eye_pair: tuple[tuple[float, float], tuple[float, float]] | None,
) -> tuple[np.ndarray, dict[str, float]]:
    x, y, w, h = face_box
    face_aspect = float(w) / max(float(h), 1.0)
    cheek_span = _face_width_span_ratio(gray_face, 0.52)
    jaw_span = _face_width_span_ratio(gray_face, 0.78)
    upper_span = _face_width_span_ratio(gray_face, 0.32)

    strip_l = int(gray_face.shape[1] * 0.44)
    strip_r = int(gray_face.shape[1] * 0.56)
    central_strip = gray_face[:, strip_l:strip_r]
    gx = cv2.Sobel(central_strip, cv2.CV_32F, 1, 0, ksize=3)
    nose_strength = min(1.0, float(np.mean(np.abs(gx))) / 38.0)

    eye_distance_ratio = 0.0
    eye_mid_y_ratio = 0.0
    eye_slope = 0.0
    yaw_proxy = 0.0
    pitch_proxy = 0.0
    if eye_pair is not None:
        (lx, ly), (rx, ry) = eye_pair
        eye_distance_ratio = np.hypot(rx - lx, ry - ly) / max(float(w), 1.0)
        eye_mid_x_ratio = ((((lx + rx) * 0.5) - x) / max(float(w), 1.0))
        eye_mid_y_ratio = ((((ly + ry) * 0.5) - y) / max(float(h), 1.0))
        eye_slope = np.arctan2((ry - ly), max((rx - lx), 1.0)) / np.pi
        yaw_proxy = eye_mid_x_ratio - 0.5
        pitch_proxy = eye_mid_y_ratio - 0.42

    vector = np.array(
        [
            face_aspect,
            eye_distance_ratio,
            eye_mid_y_ratio,
            eye_slope,
            upper_span,
            cheek_span,
            jaw_span,
            nose_strength,
            max(0.0, cheek_span - jaw_span),
            max(0.0, jaw_span - upper_span),
            yaw_proxy,
            pitch_proxy,
        ],
        dtype=np.float32,
    )
    metrics = {
        "eye_distance_ratio": float(eye_distance_ratio),
        "eye_slope": float(eye_slope),
        "yaw_proxy": float(yaw_proxy),
        "pitch_proxy": float(pitch_proxy),
    }
    return _l2_normalize(vector), metrics


def _cosine_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    a = _l2_normalize(vector_a)
    b = _l2_normalize(vector_b)
    if a.size != b.size:
        n = min(a.size, b.size)
        if n < 16:
            return 0.0
        a = a[:n]
        b = b[:n]
    return _clamp01((float(np.dot(a, b)) + 1.0) / 2.0)


def _frame_reason_bucket(frame_audit: Sequence[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for item in frame_audit:
        reason = str(item.get("reason") or "Face not recognized")
        if item.get("accepted"):
            continue
        counts[reason] = counts.get(reason, 0) + 1
    if not counts:
        return "Face not recognized"
    return max(counts.items(), key=lambda pair: pair[1])[0]


def _extract_embedding_bundle(
    image_bgr: np.ndarray,
    *,
    config: FaceVerificationConfig,
    strict_anti_spoof: bool,
    allow_landmark_fallback: bool = False,
) -> dict[str, Any]:
    if cv2 is None:
        return {"ok": False, "reason": "OpenCV not installed"}

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    image_h, image_w = gray.shape[:2]
    if image_w < config.min_frame_width or image_h < config.min_frame_height:
        return {
            "ok": False,
            "reason": "Low resolution frame",
            "frame_width": int(image_w),
            "frame_height": int(image_h),
        }

    faces = _detect_face_boxes(gray)
    if not faces:
        return {"ok": False, "reason": "No face detected"}
    face_box = faces[0]
    if len(faces) > 1:
        if strict_anti_spoof:
            return {
                "ok": False,
                "reason": "Multiple faces detected",
                "faces_detected": len(faces),
            }
        primary_area = float(face_box[2] * face_box[3])
        secondary_area = float(faces[1][2] * faces[1][3])
        dominance = primary_area / max(1.0, secondary_area)
        if dominance < config.min_primary_face_dominance_ratio:
            return {
                "ok": False,
                "reason": "Multiple faces detected",
                "primary_face_dominance": dominance,
                "faces_detected": len(faces),
            }

    x, y, w, h = face_box
    image_area = max(1, image_h * image_w)
    face_area_ratio = float(w * h) / float(image_area)

    center_x = (x + (w / 2.0)) / max(float(image_w), 1.0)
    center_y = (y + (h / 2.0)) / max(float(image_h), 1.0)
    center_offset_ratio = float(np.hypot(center_x - 0.5, center_y - 0.5) / np.hypot(0.5, 0.5))

    if face_area_ratio < config.min_face_area_ratio:
        return {"ok": False, "reason": "Low detection confidence", "face_area_ratio": face_area_ratio}

    if strict_anti_spoof and center_offset_ratio > config.max_center_offset_ratio:
        return {
            "ok": False,
            "reason": "Face not centered",
            "center_offset_ratio": center_offset_ratio,
        }

    eye_pair = _extract_eye_pair(gray, face_box)
    used_eye_fallback = False
    if eye_pair is None and strict_anti_spoof:
        return {"ok": False, "reason": "No facial landmarks detected", "face_area_ratio": face_area_ratio}
    if eye_pair is None and allow_landmark_fallback and not strict_anti_spoof:
        eye_pair = _fallback_eye_pair_from_face_box(face_box)
        used_eye_fallback = True
    if eye_pair is None:
        return {"ok": False, "reason": "No facial landmarks detected", "face_area_ratio": face_area_ratio}

    aligned = _align_face_crop(gray, face_box, eye_pair)
    aligned = cv2.equalizeHist(aligned)
    aligned = cv2.GaussianBlur(aligned, (3, 3), 0)

    blur = _blur_score(aligned)
    contrast = float(np.std(aligned))
    texture_ratio = _occlusion_texture_ratio(aligned)

    geom, geom_metrics = _geometry_embedding(aligned, face_box, eye_pair)
    eye_distance_ratio = float(geom_metrics["eye_distance_ratio"])
    if eye_distance_ratio < config.min_eye_distance_ratio:
        return {
            "ok": False,
            "reason": "Face partially covered or landmarks unstable",
            "face_area_ratio": face_area_ratio,
            "eye_distance_ratio": eye_distance_ratio,
        }

    if strict_anti_spoof:
        if blur < (config.blur_threshold * (0.92 if used_eye_fallback else 1.0)):
            return {"ok": False, "reason": "Face is blurry", "blur": blur}
        if contrast < (config.min_contrast * (0.92 if used_eye_fallback else 1.0)):
            return {"ok": False, "reason": "Poor lighting or low contrast", "contrast": contrast}
        if texture_ratio < config.min_lower_texture_ratio:
            return {"ok": False, "reason": "Face appears covered", "texture_ratio": texture_ratio}

    hog = _hog_embedding(aligned)
    lbp = _lbp_histogram(aligned)
    freq = _frequency_embedding(aligned)
    embedding = _l2_normalize(np.concatenate((0.45 * hog, 0.2 * lbp, 0.2 * freq, 0.15 * geom), axis=0))

    return {
        "ok": True,
        "embedding": embedding,
        "face_area_ratio": face_area_ratio,
        "center_offset_ratio": center_offset_ratio,
        "center_x": center_x,
        "center_y": center_y,
        "blur": blur,
        "contrast": contrast,
        "texture_ratio": texture_ratio,
        "eye_distance_ratio": eye_distance_ratio,
        "eye_slope": float(geom_metrics["eye_slope"]),
        "yaw_proxy": float(geom_metrics["yaw_proxy"]),
        "pitch_proxy": float(geom_metrics["pitch_proxy"]),
    }


def _detect_face_rows_dnn(image_bgr: np.ndarray) -> tuple[list[np.ndarray], str | None]:
    runtime, error = _load_dnn_runtime()
    if runtime is None:
        return [], error or "OpenCV DNN runtime unavailable"

    detector = runtime["detector"]
    image_h, image_w = image_bgr.shape[:2]
    try:
        with _DNN_INFERENCE_LOCK:
            detector.setInputSize((int(image_w), int(image_h)))
            _, faces = detector.detect(image_bgr)
    except Exception as exc:  # noqa: BLE001
        return [], str(exc).strip() or "OpenCV face detection failed"

    face_rows = np.asarray(faces if faces is not None else [], dtype=np.float32)
    rows = [np.asarray(item, dtype=np.float32).ravel() for item in face_rows]
    rows = [row for row in rows if row.size >= 15]
    rows.sort(key=lambda row: float(row[2]) * float(row[3]), reverse=True)
    return rows, None


def _extract_embedding_bundle_dnn(
    image_bgr: np.ndarray,
    *,
    config: FaceVerificationConfig,
    strict_anti_spoof: bool,
) -> dict[str, Any]:
    if cv2 is None:
        return {"ok": False, "reason": "OpenCV not installed"}

    image_h, image_w = image_bgr.shape[:2]
    if image_w < config.min_frame_width or image_h < config.min_frame_height:
        return {
            "ok": False,
            "reason": "Low resolution frame",
            "frame_width": int(image_w),
            "frame_height": int(image_h),
        }

    faces, error = _detect_face_rows_dnn(image_bgr)
    if error:
        return {"ok": False, "reason": error}
    if not faces:
        return {"ok": False, "reason": "No face detected"}

    face = faces[0]
    if len(faces) > 1:
        primary_area = float(face[2] * face[3])
        secondary_area = float(faces[1][2] * faces[1][3])
        dominance = primary_area / max(1.0, secondary_area)
        if strict_anti_spoof or dominance < config.min_primary_face_dominance_ratio:
            return {
                "ok": False,
                "reason": "Multiple faces detected",
                "primary_face_dominance": dominance,
                "faces_detected": len(faces),
            }

    x, y, w, h = [float(value) for value in face[:4]]
    detection_score = float(face[14]) if face.size >= 15 else 1.0
    face_area_ratio = float((w * h) / max(float(image_w * image_h), 1.0))
    center_x = (x + (w / 2.0)) / max(float(image_w), 1.0)
    center_y = (y + (h / 2.0)) / max(float(image_h), 1.0)
    center_offset_ratio = float(np.hypot(center_x - 0.5, center_y - 0.5) / np.hypot(0.5, 0.5))

    if detection_score < max(0.5, min(0.98, _env_float("FACE_DNN_DETECTION_SCORE_THRESHOLD", 0.88))):
        return {"ok": False, "reason": "Low detection confidence", "face_area_ratio": face_area_ratio}
    if face_area_ratio < config.min_face_area_ratio:
        return {"ok": False, "reason": "Low detection confidence", "face_area_ratio": face_area_ratio}
    if strict_anti_spoof and center_offset_ratio > config.max_center_offset_ratio:
        return {
            "ok": False,
            "reason": "Face not centered",
            "center_offset_ratio": center_offset_ratio,
        }

    runtime, error = _load_dnn_runtime()
    if runtime is None:
        return {"ok": False, "reason": error or "OpenCV DNN runtime unavailable"}
    recognizer = runtime["recognizer"]

    try:
        with _DNN_INFERENCE_LOCK:
            aligned_bgr = recognizer.alignCrop(image_bgr, face)
            face_feature = recognizer.feature(aligned_bgr)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": str(exc).strip() or "OpenCV face recognition failed"}

    if face_feature is None:
        return {"ok": False, "reason": "Embedding extraction failed"}

    embedding = _l2_normalize(np.asarray(face_feature, dtype=np.float32).ravel())
    if embedding.size < 16:
        return {"ok": False, "reason": "Embedding extraction failed"}

    aligned_gray = cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2GRAY)
    blur = _blur_score(aligned_gray)
    contrast = float(np.std(aligned_gray))
    texture_ratio = _occlusion_texture_ratio(aligned_gray)

    left_eye = (float(face[4]), float(face[5]))
    right_eye = (float(face[6]), float(face[7]))
    if left_eye[0] > right_eye[0]:
        left_eye, right_eye = right_eye, left_eye
    nose = (float(face[8]), float(face[9]))
    eye_distance_ratio = float(np.hypot(right_eye[0] - left_eye[0], right_eye[1] - left_eye[1]) / max(w, 1.0))
    eye_mid_x = (left_eye[0] + right_eye[0]) * 0.5
    eye_mid_y = (left_eye[1] + right_eye[1]) * 0.5
    eye_slope = float(np.arctan2((right_eye[1] - left_eye[1]), max((right_eye[0] - left_eye[0]), 1.0)) / np.pi)
    yaw_proxy = float((nose[0] - eye_mid_x) / max(w, 1.0))
    pitch_proxy = float(((nose[1] - eye_mid_y) / max(h, 1.0)) - 0.18)

    if eye_distance_ratio < config.min_eye_distance_ratio:
        return {
            "ok": False,
            "reason": "Face partially covered or landmarks unstable",
            "face_area_ratio": face_area_ratio,
            "eye_distance_ratio": eye_distance_ratio,
        }

    if strict_anti_spoof:
        if blur < config.blur_threshold:
            return {"ok": False, "reason": "Face is blurry", "blur": blur}
        if contrast < config.min_contrast:
            return {"ok": False, "reason": "Poor lighting or low contrast", "contrast": contrast}
        if texture_ratio < config.min_lower_texture_ratio:
            return {"ok": False, "reason": "Face appears covered", "texture_ratio": texture_ratio}

    return {
        "ok": True,
        "embedding": embedding,
        "face_area_ratio": face_area_ratio,
        "center_offset_ratio": center_offset_ratio,
        "center_x": center_x,
        "center_y": center_y,
        "blur": blur,
        "contrast": contrast,
        "texture_ratio": texture_ratio,
        "eye_distance_ratio": eye_distance_ratio,
        "eye_slope": eye_slope,
        "yaw_proxy": yaw_proxy,
        "pitch_proxy": pitch_proxy,
        "detection_score": detection_score,
    }


def _as_profile_embedding_list(profile_embedding: np.ndarray | Sequence[np.ndarray]) -> list[np.ndarray]:
    if isinstance(profile_embedding, np.ndarray):
        return [_l2_normalize(profile_embedding)]
    normalized: list[np.ndarray] = []
    for item in profile_embedding:
        arr = np.asarray(item, dtype=np.float32).ravel()
        if arr.size:
            normalized.append(_l2_normalize(arr))
    return normalized


def evaluate_embedding_sequence(
    profile_embedding: np.ndarray | Sequence[np.ndarray],
    frame_embeddings: Sequence[np.ndarray],
    *,
    min_similarity: float,
    min_consecutive_frames: int,
    frame_valid_flags: Sequence[bool] | None = None,
    frame_reasons: Sequence[str] | None = None,
    frame_timestamps: Sequence[str] | None = None,
) -> dict[str, Any]:
    profile_embeddings = _as_profile_embedding_list(profile_embedding)
    if not profile_embeddings:
        return {
            "match": False,
            "confidence": 0.0,
            "best_streak": 0,
            "required_streak": int(min_consecutive_frames),
            "frame_audit": [],
        }

    streak = 0
    best_streak = 0
    best_streak_scores: list[float] = []
    streak_scores: list[float] = []
    accepted_scores: list[float] = []
    frame_audit: list[dict[str, Any]] = []

    for idx, frame_embedding in enumerate(frame_embeddings):
        timestamp = (
            frame_timestamps[idx]
            if frame_timestamps and idx < len(frame_timestamps)
            else datetime.now(timezone.utc).isoformat()
        )
        valid = (
            bool(frame_valid_flags[idx])
            if frame_valid_flags is not None and idx < len(frame_valid_flags)
            else True
        )
        reason = (
            str(frame_reasons[idx])
            if frame_reasons is not None and idx < len(frame_reasons)
            else "Face not recognized"
        )

        similarity = 0.0
        if valid:
            similarity = max(_cosine_similarity(ref, frame_embedding) for ref in profile_embeddings)
        accepted = bool(valid and similarity >= min_similarity)

        if accepted:
            streak += 1
            streak_scores.append(similarity)
            accepted_scores.append(similarity)
            if streak > best_streak:
                best_streak = streak
                best_streak_scores = streak_scores.copy()
        else:
            streak = 0
            streak_scores = []
            if valid and not reason:
                reason = "Face not recognized"

        frame_audit.append(
            {
                "frame_index": idx,
                "timestamp_utc": timestamp,
                "confidence": similarity,
                "accepted": accepted,
                "reason": "ok" if accepted else reason,
            }
        )

    total_frames = int(len(frame_embeddings))
    if frame_valid_flags is not None:
        valid_frames = int(sum(1 for idx in range(total_frames) if idx < len(frame_valid_flags) and bool(frame_valid_flags[idx])))
    else:
        valid_frames = total_frames
    accepted_frames = int(sum(1 for item in frame_audit if bool(item.get("accepted"))))
    majority_required = int(max(min_consecutive_frames, int(np.ceil(total_frames * 0.60)))) if total_frames else int(min_consecutive_frames)
    majority_met = accepted_frames >= majority_required
    confidence_pool = best_streak_scores or accepted_scores
    confidence = float(np.mean(confidence_pool)) if confidence_pool else 0.0
    return {
        "match": bool(best_streak >= min_consecutive_frames and majority_met),
        "confidence": _clamp01(confidence),
        "best_streak": int(best_streak),
        "required_streak": int(min_consecutive_frames),
        "accepted_frames": accepted_frames,
        "valid_frames": valid_frames,
        "total_frames": total_frames,
        "majority_required": majority_required,
        "majority_met": majority_met,
        "frame_audit": frame_audit,
    }


def evaluate_liveness_sequence(
    frame_live_meta: Sequence[dict[str, float]],
    *,
    config: FaceVerificationConfig,
    min_frames: int,
) -> dict[str, Any]:
    if len(frame_live_meta) < min_frames:
        return {
            "ok": False,
            "reason": "Liveness check failed: insufficient valid frames",
            "metrics": {},
        }

    cx = np.array([float(item.get("center_x", 0.0)) for item in frame_live_meta], dtype=np.float32)
    cy = np.array([float(item.get("center_y", 0.0)) for item in frame_live_meta], dtype=np.float32)
    yaw = np.array([float(item.get("yaw_proxy", 0.0)) for item in frame_live_meta], dtype=np.float32)
    pitch = np.array([float(item.get("pitch_proxy", 0.0)) for item in frame_live_meta], dtype=np.float32)
    texture = np.array([float(item.get("texture_ratio", 0.0)) for item in frame_live_meta], dtype=np.float32)
    contrast = np.array([float(item.get("contrast", 0.0)) for item in frame_live_meta], dtype=np.float32)

    center_motion = float(np.ptp(cx) + np.ptp(cy))
    pose_motion = float(np.ptp(yaw) + np.ptp(pitch))
    yaw_range = float(np.ptp(yaw))
    pitch_range = float(np.ptp(pitch))
    texture_jitter = float(np.std(texture))
    contrast_jitter = float(np.std(contrast))

    metrics = {
        "center_motion": center_motion,
        "pose_motion": pose_motion,
        "yaw_range": yaw_range,
        "pitch_range": pitch_range,
        "texture_jitter": texture_jitter,
        "contrast_jitter": contrast_jitter,
    }

    if center_motion < config.min_liveness_motion and pose_motion < config.min_liveness_pose_delta:
        return {
            "ok": False,
            "reason": "Liveness check failed: insufficient head movement",
            "metrics": metrics,
        }

    if yaw_range < config.min_liveness_yaw_range and pitch_range < config.min_liveness_pitch_range:
        return {
            "ok": False,
            "reason": "Liveness check failed: head movement challenge incomplete",
            "metrics": metrics,
        }

    movement_factor = max(
        center_motion / max(config.min_liveness_motion, 1e-6),
        pose_motion / max(config.min_liveness_pose_delta, 1e-6),
    )
    if (
        movement_factor < 1.3
        and
        texture_jitter < config.min_liveness_texture_jitter
        and contrast_jitter < config.min_liveness_contrast_jitter
    ):
        return {
            "ok": False,
            "reason": "Liveness check failed: spoof texture pattern",
            "metrics": metrics,
        }

    return {"ok": True, "reason": "ok", "metrics": metrics}


def _template_embeddings_from_payload(profile_template: dict[str, Any] | None) -> list[np.ndarray]:
    if not isinstance(profile_template, dict):
        return []
    embeddings_raw = profile_template.get("embeddings")
    embeddings: list[np.ndarray] = []
    if isinstance(embeddings_raw, list):
        for item in embeddings_raw:
            arr = np.asarray(item, dtype=np.float32).ravel()
            if arr.size:
                embeddings.append(_l2_normalize(arr))
    signature_raw = profile_template.get("signature")
    if not embeddings and isinstance(signature_raw, list):
        arr = np.asarray(signature_raw, dtype=np.float32).ravel()
        if arr.size:
            embeddings.append(_l2_normalize(arr))
    return embeddings


def _embedding_to_list(vector: np.ndarray) -> list[float]:
    return [float(f"{float(value):.6f}") for value in vector.astype(np.float32).tolist()]


def _build_profile_face_template_dnn(profile_photo_data_url: str, *, config: FaceVerificationConfig) -> dict[str, Any]:
    if cv2 is None:
        raise ValueError("OpenCV not installed")

    profile_bgr = _decode_data_url_to_bgr(profile_photo_data_url)
    if profile_bgr is None:
        raise ValueError("Invalid profile photo payload")

    variants = [
        profile_bgr,
        cv2.convertScaleAbs(profile_bgr, alpha=1.03, beta=4),
        cv2.convertScaleAbs(profile_bgr, alpha=0.97, beta=-4),
    ]

    embeddings: list[np.ndarray] = []
    quality: dict[str, float] = {}
    for variant in variants:
        bundle = _extract_embedding_bundle_dnn(variant, config=config, strict_anti_spoof=False)
        if not bundle.get("ok"):
            continue
        embedding = bundle.get("embedding")
        if isinstance(embedding, np.ndarray) and embedding.size:
            embeddings.append(embedding)
            quality = {
                "face_area_ratio": float(bundle.get("face_area_ratio", 0.0)),
                "contrast": float(bundle.get("contrast", 0.0)),
                "blur": float(bundle.get("blur", 0.0)),
                "detection_score": float(bundle.get("detection_score", 0.0)),
            }

    if not embeddings:
        raise ValueError("Unable to extract stable facial embedding from profile photo")

    signature = _l2_normalize(np.mean(np.stack(embeddings, axis=0), axis=0))
    return {
        "version": "opencv-dnn-yunet-sface-v1",
        "provider": "opencv-dnn",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedding_dim": int(signature.size),
        "embeddings": [_embedding_to_list(vector) for vector in embeddings[:3]],
        "signature": _embedding_to_list(signature),
        "quality": quality,
    }


def _build_enrollment_template_from_frames_dnn(
    frames_data_urls: Sequence[str],
    *,
    config: FaceVerificationConfig,
    min_valid_frames: int = 8,
) -> dict[str, Any]:
    enrollment_config = _relaxed_enrollment_config(config)
    if cv2 is None:
        raise ValueError("OpenCV not installed")
    if not frames_data_urls:
        raise ValueError("No enrollment frames provided")

    frames = list(frames_data_urls[: max(config.max_frames * 2, 20)])
    embeddings: list[np.ndarray] = []
    live_meta: list[dict[str, float]] = []
    invalid_reasons: list[str] = []

    for frame_data_url in frames:
        frame_bgr = _decode_data_url_to_bgr(frame_data_url)
        if frame_bgr is None:
            invalid_reasons.append("Invalid frame payload")
            continue

        bundle = _extract_embedding_bundle_dnn(
            frame_bgr,
            config=enrollment_config,
            strict_anti_spoof=True,
        )
        if not bundle.get("ok"):
            invalid_reasons.append(str(bundle.get("reason", "Face not recognized")))
            continue

        embedding = bundle.get("embedding")
        if not isinstance(embedding, np.ndarray) or not embedding.size:
            invalid_reasons.append("Embedding extraction failed")
            continue

        embeddings.append(embedding)
        live_meta.append(
            {
                "center_x": float(bundle.get("center_x", 0.0)),
                "center_y": float(bundle.get("center_y", 0.0)),
                "yaw_proxy": float(bundle.get("yaw_proxy", 0.0)),
                "pitch_proxy": float(bundle.get("pitch_proxy", 0.0)),
                "texture_ratio": float(bundle.get("texture_ratio", 0.0)),
                "contrast": float(bundle.get("contrast", 0.0)),
            }
        )

    if len(embeddings) < min_valid_frames:
        dominant_reason = _most_common_reason(invalid_reasons)
        raise ValueError(
            f"Insufficient valid enrollment frames ({len(embeddings)}/{min_valid_frames}). "
            f"Most frames failed due to: {dominant_reason}. Keep one centered, fully visible face with front lighting."
        )

    liveness = evaluate_liveness_sequence(
        live_meta,
        config=enrollment_config,
        min_frames=max(4, min_valid_frames // 2),
    )
    if not bool(liveness.get("ok")):
        raise ValueError(str(liveness.get("reason") or "Liveness check failed"))

    yaw_values = np.array([item["yaw_proxy"] for item in live_meta], dtype=np.float32)
    pitch_values = np.array([item["pitch_proxy"] for item in live_meta], dtype=np.float32)
    yaw_range = float(np.ptp(yaw_values)) if yaw_values.size else 0.0
    pitch_range = float(np.ptp(pitch_values)) if pitch_values.size else 0.0
    if yaw_range < 0.02 or pitch_range < 0.01:
        raise ValueError("Head movement range is too low. Look left, right, up, and down while recording.")

    stride = max(1, len(embeddings) // 12)
    sampled = embeddings[::stride][:12]
    signature = _l2_normalize(np.mean(np.stack(sampled, axis=0), axis=0))
    return {
        "version": "opencv-dnn-yunet-sface-v1-enrollment",
        "provider": "opencv-dnn",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedding_dim": int(signature.size),
        "embeddings": [_embedding_to_list(vector) for vector in sampled],
        "signature": _embedding_to_list(signature),
        "quality": {
            "valid_frames_used": int(len(sampled)),
            "valid_frames_total": int(len(embeddings)),
            "frames_received": int(len(frames)),
            "yaw_range": yaw_range,
            "pitch_range": pitch_range,
            "liveness": liveness.get("metrics", {}),
            "top_rejection_reason": _most_common_reason(invalid_reasons),
        },
        "invalid_samples": invalid_reasons[:20],
    }


def build_profile_face_template(profile_photo_data_url: str) -> dict[str, Any]:
    config = _load_config()
    provider, provider_error = _resolve_active_provider()
    if provider == "dnn":
        return _build_profile_face_template_dnn(profile_photo_data_url, config=config)
    if _face_provider() == "dnn" and provider_error:
        raise ValueError(provider_error)
    if cv2 is None:
        raise ValueError("OpenCV not installed")

    profile_bgr = _decode_data_url_to_bgr(profile_photo_data_url)
    if profile_bgr is None:
        raise ValueError("Invalid profile photo payload")

    variants = [
        profile_bgr,
        cv2.convertScaleAbs(profile_bgr, alpha=1.03, beta=4),
        cv2.convertScaleAbs(profile_bgr, alpha=0.97, beta=-4),
    ]

    embeddings: list[np.ndarray] = []
    quality: dict[str, float] = {}
    for variant in variants:
        bundle = _extract_embedding_bundle(variant, config=config, strict_anti_spoof=False)
        if not bundle.get("ok"):
            continue
        embedding = bundle.get("embedding")
        if isinstance(embedding, np.ndarray) and embedding.size:
            embeddings.append(embedding)
            quality = {
                "face_area_ratio": float(bundle.get("face_area_ratio", 0.0)),
                "contrast": float(bundle.get("contrast", 0.0)),
                "blur": float(bundle.get("blur", 0.0)),
            }

    if not embeddings:
        raise ValueError("Unable to extract stable facial embedding from profile photo")

    signature = _l2_normalize(np.mean(np.stack(embeddings, axis=0), axis=0))
    return {
        "version": "opencv-embedding-v3",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedding_dim": int(signature.size),
        "embeddings": [_embedding_to_list(vector) for vector in embeddings[:3]],
        "signature": _embedding_to_list(signature),
        "quality": quality,
    }


def build_enrollment_template_from_frames(
    frames_data_urls: Sequence[str],
    *,
    min_valid_frames: int = 8,
) -> dict[str, Any]:
    config = _load_config()
    provider, provider_error = _resolve_active_provider()
    if provider == "dnn":
        return _build_enrollment_template_from_frames_dnn(
            frames_data_urls,
            config=config,
            min_valid_frames=min_valid_frames,
        )
    if _face_provider() == "dnn" and provider_error:
        raise ValueError(provider_error)
    enrollment_config = _relaxed_enrollment_config(config)
    if cv2 is None:
        raise ValueError("OpenCV not installed")
    if not frames_data_urls:
        raise ValueError("No enrollment frames provided")

    frames = list(frames_data_urls[: max(config.max_frames * 2, 20)])
    embeddings: list[np.ndarray] = []
    live_meta: list[dict[str, float]] = []
    valid_reasons: list[str] = []
    invalid_reasons: list[str] = []

    for frame_data_url in frames:
        frame_bgr = _decode_data_url_to_bgr(frame_data_url)
        if frame_bgr is None:
            invalid_reasons.append("Invalid frame payload")
            continue

        acceptance_mode = "strict"
        bundle = _extract_embedding_bundle(frame_bgr, config=config, strict_anti_spoof=True)
        if not bundle.get("ok"):
            acceptance_mode = "relaxed_strict"
            bundle = _extract_embedding_bundle(
                frame_bgr,
                config=enrollment_config,
                strict_anti_spoof=True,
            )
        if not bundle.get("ok"):
            acceptance_mode = "relaxed_fallback"
            bundle = _extract_embedding_bundle(
                frame_bgr,
                config=enrollment_config,
                strict_anti_spoof=False,
                allow_landmark_fallback=True,
            )
            if bundle.get("ok") and not _passes_relaxed_enrollment_quality(bundle, config=enrollment_config):
                bundle = {"ok": False, "reason": "Low detection confidence"}
        if not bundle.get("ok"):
            invalid_reasons.append(str(bundle.get("reason", "Face not recognized")))
            continue

        embedding = bundle.get("embedding")
        if not isinstance(embedding, np.ndarray) or not embedding.size:
            invalid_reasons.append("Embedding extraction failed")
            continue
        embeddings.append(embedding)
        live_meta.append(
            {
                "center_x": float(bundle.get("center_x", 0.0)),
                "center_y": float(bundle.get("center_y", 0.0)),
                "yaw_proxy": float(bundle.get("yaw_proxy", 0.0)),
                "pitch_proxy": float(bundle.get("pitch_proxy", 0.0)),
                "texture_ratio": float(bundle.get("texture_ratio", 0.0)),
                "contrast": float(bundle.get("contrast", 0.0)),
            }
        )
        valid_reasons.append(acceptance_mode)

    if len(embeddings) < min_valid_frames:
        dominant_reason = _most_common_reason(invalid_reasons)
        raise ValueError(
            f"Insufficient valid enrollment frames ({len(embeddings)}/{min_valid_frames}). "
            f"Most frames failed due to: {dominant_reason}. Keep one centered, fully visible face with front lighting."
        )

    liveness = evaluate_liveness_sequence(
        live_meta,
        config=enrollment_config,
        min_frames=max(4, min_valid_frames // 2),
    )
    if not bool(liveness.get("ok")):
        raise ValueError(str(liveness.get("reason") or "Liveness check failed"))

    yaw_values = np.array([item["yaw_proxy"] for item in live_meta], dtype=np.float32)
    pitch_values = np.array([item["pitch_proxy"] for item in live_meta], dtype=np.float32)
    yaw_range = float(np.ptp(yaw_values)) if yaw_values.size else 0.0
    pitch_range = float(np.ptp(pitch_values)) if pitch_values.size else 0.0
    if yaw_range < 0.025 or pitch_range < 0.012:
        raise ValueError("Head movement range is too low. Look left, right, up, and down while recording.")

    # Keep a compact but diverse template for fast runtime matching.
    stride = max(1, len(embeddings) // 12)
    sampled = embeddings[::stride][:12]
    signature = _l2_normalize(np.mean(np.stack(sampled, axis=0), axis=0))
    quality = {
        "valid_frames_used": int(len(sampled)),
        "valid_frames_total": int(len(embeddings)),
        "frames_received": int(len(frames)),
        "yaw_range": yaw_range,
        "pitch_range": pitch_range,
        "liveness": liveness.get("metrics", {}),
        "top_rejection_reason": _most_common_reason(invalid_reasons),
        "acceptance_modes": {
            mode: int(valid_reasons.count(mode))
            for mode in sorted(set(valid_reasons))
        },
    }

    return {
        "version": "opencv-embedding-v3-enrollment",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedding_dim": int(signature.size),
        "embeddings": [_embedding_to_list(vector) for vector in sampled],
        "signature": _embedding_to_list(signature),
        "quality": quality,
        "invalid_samples": invalid_reasons[:20],
    }


def _verify_face_sequence_dnn(
    profile_photo_data_url: str,
    selfie_frames_data_urls: Sequence[str],
    *,
    subject_label: str,
    min_consecutive_frames: int | None,
    profile_template: dict[str, Any] | None,
) -> dict[str, Any]:
    config = _load_config()
    if min_consecutive_frames is not None:
        config.min_consecutive_frames = max(1, int(min_consecutive_frames))

    if not selfie_frames_data_urls:
        return {
            "available": True,
            "match": False,
            "confidence": 0.0,
            "engine": "opencv-dnn-yunet-sface-v1",
            "reason": "No live frames provided",
        }

    frames = list(selfie_frames_data_urls[: config.max_frames])
    if len(frames) < config.min_consecutive_frames:
        return {
            "available": True,
            "match": False,
            "confidence": 0.0,
            "engine": "opencv-dnn-yunet-sface-v1",
            "reason": "Insufficient frames for verification",
            "required_consecutive_frames": config.min_consecutive_frames,
            "consecutive_frames_matched": 0,
            "frame_audit": [],
        }

    profile_embeddings = _template_embeddings_from_payload(profile_template)
    if not profile_embeddings:
        profile_bgr = _decode_data_url_to_bgr(profile_photo_data_url)
        if profile_bgr is None:
            return {
                "available": False,
                "match": False,
                "confidence": 0.0,
                "engine": "opencv-dnn-yunet-sface-v1",
                "reason": "Invalid profile photo payload",
            }
        profile_bundle = _extract_embedding_bundle_dnn(profile_bgr, config=config, strict_anti_spoof=False)
        if not profile_bundle.get("ok"):
            return {
                "available": False,
                "match": False,
                "confidence": 0.0,
                "engine": "opencv-dnn-yunet-sface-v1",
                "reason": str(profile_bundle.get("reason", "Invalid profile photo for recognition")),
            }
        profile_embeddings = [_l2_normalize(profile_bundle["embedding"])]

    frame_embeddings: list[np.ndarray] = []
    frame_valid_flags: list[bool] = []
    frame_reasons: list[str] = []
    frame_timestamps: list[str] = []
    frame_live_meta: list[dict[str, float]] = []
    rejection_reasons: list[str] = []
    zero_vector = np.zeros_like(profile_embeddings[0], dtype=np.float32)

    for frame_data_url in frames:
        timestamp = datetime.now(timezone.utc).isoformat()
        frame_timestamps.append(timestamp)

        selfie_bgr = _decode_data_url_to_bgr(frame_data_url)
        if selfie_bgr is None:
            frame_embeddings.append(zero_vector)
            frame_valid_flags.append(False)
            frame_reasons.append("Invalid frame payload")
            rejection_reasons.append("Invalid frame payload")
            continue

        frame_bundle = _extract_embedding_bundle_dnn(selfie_bgr, config=config, strict_anti_spoof=True)
        if not frame_bundle.get("ok"):
            reason = str(frame_bundle.get("reason", "Face not recognized"))
            frame_embeddings.append(zero_vector)
            frame_valid_flags.append(False)
            frame_reasons.append(reason)
            rejection_reasons.append(reason)
            continue

        embedding = frame_bundle["embedding"]
        assert isinstance(embedding, np.ndarray)
        frame_embeddings.append(embedding)
        frame_valid_flags.append(True)
        frame_reasons.append("")
        frame_live_meta.append(
            {
                "center_x": float(frame_bundle.get("center_x", 0.0)),
                "center_y": float(frame_bundle.get("center_y", 0.0)),
                "yaw_proxy": float(frame_bundle.get("yaw_proxy", 0.0)),
                "pitch_proxy": float(frame_bundle.get("pitch_proxy", 0.0)),
                "texture_ratio": float(frame_bundle.get("texture_ratio", 0.0)),
                "contrast": float(frame_bundle.get("contrast", 0.0)),
            }
        )

    sequence = evaluate_embedding_sequence(
        profile_embeddings,
        frame_embeddings,
        min_similarity=config.min_similarity,
        min_consecutive_frames=config.min_consecutive_frames,
        frame_valid_flags=frame_valid_flags,
        frame_reasons=frame_reasons,
        frame_timestamps=frame_timestamps,
    )
    liveness = evaluate_liveness_sequence(
        frame_live_meta,
        config=config,
        min_frames=config.min_consecutive_frames,
    )

    frame_audit = sequence["frame_audit"]
    for item in frame_audit:
        logger.info(
            "face_frame_audit subject=%s ts=%s confidence=%.4f accepted=%s reason=%s",
            subject_label,
            item.get("timestamp_utc"),
            float(item.get("confidence", 0.0)),
            bool(item.get("accepted")),
            str(item.get("reason", "")),
        )

    fatal_reasons = {
        "Multiple faces detected",
        "Face not centered",
        "Low resolution frame",
        "Poor lighting or low contrast",
        "Face appears covered",
        "Face is blurry",
        "No face detected",
    }
    fatal_reason = next((reason for reason in rejection_reasons if reason in fatal_reasons), "")

    match = bool(sequence["match"]) and bool(liveness["ok"]) and not fatal_reason
    confidence = float(sequence["confidence"])
    if not match:
        confidence = min(confidence, max(0.0, confidence * 0.65))

    if match:
        reason = (
            f"Verified with {sequence['best_streak']} consecutive frames "
            f"and {sequence.get('accepted_frames', 0)}/{sequence.get('total_frames', 0)} accepted "
            f"(similarity>={config.min_similarity:.2f}, liveness=pass)"
        )
    elif fatal_reason:
        reason = fatal_reason
    elif not liveness["ok"]:
        reason = str(liveness.get("reason") or "Liveness check failed")
    elif not bool(sequence.get("majority_met", False)):
        reason = (
            "Face match consistency failed across frames "
            f"({sequence.get('accepted_frames', 0)}/{sequence.get('total_frames', 0)} accepted)"
        )
    else:
        reason = _frame_reason_bucket(frame_audit)
        if not reason:
            reason = rejection_reasons[0] if rejection_reasons else "Face not recognized"
        if reason == "ok":
            reason = "Face not recognized"

    logger.info(
        "face_verification_summary subject=%s match=%s confidence=%.4f streak=%s/%s accepted=%s/%s majority_required=%s liveness=%s reason=%s",
        subject_label,
        match,
        confidence,
        sequence.get("best_streak", 0),
        config.min_consecutive_frames,
        sequence.get("accepted_frames", 0),
        sequence.get("total_frames", 0),
        sequence.get("majority_required", config.min_consecutive_frames),
        bool(liveness.get("ok")),
        reason,
    )

    return {
        "available": True,
        "match": bool(match),
        "confidence": _clamp01(confidence),
        "engine": "opencv-dnn-yunet-sface-v1",
        "reason": reason,
        "required_consecutive_frames": config.min_consecutive_frames,
        "consecutive_frames_matched": int(sequence["best_streak"]),
        "accepted_frames": int(sequence.get("accepted_frames", 0)),
        "total_frames": int(sequence.get("total_frames", len(frames))),
        "majority_required": int(sequence.get("majority_required", config.min_consecutive_frames)),
        "frame_audit": frame_audit,
        "liveness": liveness,
    }


def verify_face_sequence_opencv(
    profile_photo_data_url: str,
    selfie_frames_data_urls: Sequence[str],
    *,
    subject_label: str = "unknown",
    min_consecutive_frames: int | None = None,
    profile_template: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider, provider_error = _resolve_active_provider()
    if provider == "dnn":
        return _verify_face_sequence_dnn(
            profile_photo_data_url,
            selfie_frames_data_urls,
            subject_label=subject_label,
            min_consecutive_frames=min_consecutive_frames,
            profile_template=profile_template,
        )
    if _face_provider() == "dnn" and provider_error:
        return {
            "available": False,
            "match": False,
            "confidence": 0.0,
            "engine": "opencv-dnn-yunet-sface-v1",
            "reason": provider_error,
        }
    config = _load_config()
    if min_consecutive_frames is not None:
        config.min_consecutive_frames = max(1, int(min_consecutive_frames))
    if cv2 is None:
        return {
            "available": False,
            "match": False,
            "confidence": 0.0,
            "engine": "opencv-embedding-v4",
            "reason": "OpenCV not installed",
        }

    if not selfie_frames_data_urls:
        return {
            "available": True,
            "match": False,
            "confidence": 0.0,
            "engine": "opencv-embedding-v4",
            "reason": "No live frames provided",
        }

    frames = list(selfie_frames_data_urls[: config.max_frames])
    if len(frames) < config.min_consecutive_frames:
        return {
            "available": True,
            "match": False,
            "confidence": 0.0,
            "engine": "opencv-embedding-v4",
            "reason": "Insufficient frames for verification",
            "required_consecutive_frames": config.min_consecutive_frames,
            "consecutive_frames_matched": 0,
            "frame_audit": [],
        }

    profile_embeddings = _template_embeddings_from_payload(profile_template)
    if not profile_embeddings:
        profile_bgr = _decode_data_url_to_bgr(profile_photo_data_url)
        if profile_bgr is None:
            return {
                "available": False,
                "match": False,
                "confidence": 0.0,
                "engine": "opencv-embedding-v4",
                "reason": "Invalid profile photo payload",
            }
        profile_bundle = _extract_embedding_bundle(profile_bgr, config=config, strict_anti_spoof=False)
        if not profile_bundle.get("ok"):
            return {
                "available": False,
                "match": False,
                "confidence": 0.0,
                "engine": "opencv-embedding-v4",
                "reason": str(profile_bundle.get("reason", "Invalid profile photo for recognition")),
            }
        profile_embeddings = [_l2_normalize(profile_bundle["embedding"])]

    frame_embeddings: list[np.ndarray] = []
    frame_valid_flags: list[bool] = []
    frame_reasons: list[str] = []
    frame_timestamps: list[str] = []
    frame_live_meta: list[dict[str, float]] = []
    rejection_reasons: list[str] = []

    zero_vector = np.zeros_like(profile_embeddings[0], dtype=np.float32)

    for frame_data_url in frames:
        timestamp = datetime.now(timezone.utc).isoformat()
        frame_timestamps.append(timestamp)

        selfie_bgr = _decode_data_url_to_bgr(frame_data_url)
        if selfie_bgr is None:
            frame_embeddings.append(zero_vector)
            frame_valid_flags.append(False)
            frame_reasons.append("Invalid frame payload")
            rejection_reasons.append("Invalid frame payload")
            continue

        frame_bundle = _extract_embedding_bundle(selfie_bgr, config=config, strict_anti_spoof=True)
        if not frame_bundle.get("ok"):
            reason = str(frame_bundle.get("reason", "Face not recognized"))
            frame_embeddings.append(zero_vector)
            frame_valid_flags.append(False)
            frame_reasons.append(reason)
            rejection_reasons.append(reason)
            continue

        embedding = frame_bundle["embedding"]
        assert isinstance(embedding, np.ndarray)
        frame_embeddings.append(embedding)
        frame_valid_flags.append(True)
        frame_reasons.append("")
        frame_live_meta.append(
            {
                "center_x": float(frame_bundle.get("center_x", 0.0)),
                "center_y": float(frame_bundle.get("center_y", 0.0)),
                "yaw_proxy": float(frame_bundle.get("yaw_proxy", 0.0)),
                "pitch_proxy": float(frame_bundle.get("pitch_proxy", 0.0)),
                "texture_ratio": float(frame_bundle.get("texture_ratio", 0.0)),
                "contrast": float(frame_bundle.get("contrast", 0.0)),
            }
        )

    sequence = evaluate_embedding_sequence(
        profile_embeddings,
        frame_embeddings,
        min_similarity=config.min_similarity,
        min_consecutive_frames=config.min_consecutive_frames,
        frame_valid_flags=frame_valid_flags,
        frame_reasons=frame_reasons,
        frame_timestamps=frame_timestamps,
    )

    liveness = evaluate_liveness_sequence(
        frame_live_meta,
        config=config,
        min_frames=config.min_consecutive_frames,
    )

    frame_audit = sequence["frame_audit"]
    for item in frame_audit:
        logger.info(
            "face_frame_audit subject=%s ts=%s confidence=%.4f accepted=%s reason=%s",
            subject_label,
            item.get("timestamp_utc"),
            float(item.get("confidence", 0.0)),
            bool(item.get("accepted")),
            str(item.get("reason", "")),
        )

    fatal_reasons = {
        "Multiple faces detected",
        "Face not centered",
        "Low resolution frame",
        "Poor lighting or low contrast",
        "Face appears covered",
        "Face is blurry",
        "No face detected",
    }
    fatal_reason = next((reason for reason in rejection_reasons if reason in fatal_reasons), "")

    match = bool(sequence["match"]) and bool(liveness["ok"]) and not fatal_reason
    confidence = float(sequence["confidence"])
    if not match:
        confidence = min(confidence, max(0.0, confidence * 0.65))

    if match:
        reason = (
            f"Verified with {sequence['best_streak']} consecutive frames "
            f"and {sequence.get('accepted_frames', 0)}/{sequence.get('total_frames', 0)} accepted "
            f"(similarity>={config.min_similarity:.2f}, liveness=pass)"
        )
    elif fatal_reason:
        reason = fatal_reason
    elif not liveness["ok"]:
        reason = str(liveness.get("reason") or "Liveness check failed")
    elif not bool(sequence.get("majority_met", False)):
        reason = (
            "Face match consistency failed across frames "
            f"({sequence.get('accepted_frames', 0)}/{sequence.get('total_frames', 0)} accepted)"
        )
    else:
        reason = _frame_reason_bucket(frame_audit)
        if not reason:
            reason = rejection_reasons[0] if rejection_reasons else "Face not recognized"
        if reason == "ok":
            reason = "Face not recognized"

    logger.info(
        "face_verification_summary subject=%s match=%s confidence=%.4f streak=%s/%s accepted=%s/%s majority_required=%s liveness=%s reason=%s",
        subject_label,
        match,
        confidence,
        sequence.get("best_streak", 0),
        config.min_consecutive_frames,
        sequence.get("accepted_frames", 0),
        sequence.get("total_frames", 0),
        sequence.get("majority_required", config.min_consecutive_frames),
        bool(liveness.get("ok")),
        reason,
    )

    return {
        "available": True,
        "match": bool(match),
        "confidence": _clamp01(confidence),
        "engine": "opencv-embedding-v4",
        "reason": reason,
        "required_consecutive_frames": config.min_consecutive_frames,
        "consecutive_frames_matched": int(sequence["best_streak"]),
        "accepted_frames": int(sequence.get("accepted_frames", 0)),
        "total_frames": int(sequence.get("total_frames", len(frames))),
        "majority_required": int(sequence.get("majority_required", config.min_consecutive_frames)),
        "frame_audit": frame_audit,
        "liveness": liveness,
    }


def verify_face_pair_opencv(profile_photo_data_url: str, selfie_photo_data_url: str) -> dict[str, Any]:
    result = verify_face_sequence_opencv(
        profile_photo_data_url,
        [selfie_photo_data_url],
        subject_label="single-frame",
        min_consecutive_frames=1,
    )
    result.setdefault("profile_face_detected", bool(result.get("available")))
    result.setdefault("selfie_face_detected", bool(result.get("available")))
    return result


def compare_face_templates(
    template_a: dict[str, Any] | None,
    template_b: dict[str, Any] | None,
) -> float:
    embeddings_a = _template_embeddings_from_payload(template_a)
    embeddings_b = _template_embeddings_from_payload(template_b)
    if not embeddings_a or not embeddings_b:
        return 0.0
    return max(
        _cosine_similarity(reference, candidate)
        for reference in embeddings_a
        for candidate in embeddings_b
    )
