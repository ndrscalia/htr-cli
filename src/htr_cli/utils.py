import re
import cv2
import numpy as np
from pathlib import Path
from rich.tree import Tree

#---------- GENERAL PURPOSE -----------#

_REGION_TR_PREFIX = re.compile(r"^tr_(\d+)$")
_READING_ORDER_PAT = re.compile(r"readingOrder\s*\{index:(\d+);")
_IMG_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")


def find_extension(images_dir, page_stem: str) -> str | None:
    """
    Locate `{page_stem}.<ext>` under `images_dir`, probing common image
    extensions. Returns the full path as a string, or None if no match.
    """
    for ext in _IMG_EXTS:
        candidate = Path(images_dir) / f"{page_stem}{ext}"
        if candidate.exists():
            return str(candidate)
    return None

def normalize_region(region_id: str) -> str:
    """
    Turns 'tr_1' into 1, 'r' into 'r' and leaves
    everything else as is.
    """
    m = _REGION_TR_PREFIX.match(region_id or "")
    return m.group(1) if m else (region_id or "")


def parse_reading_order(custom: str | None) -> int | None:
    if not custom:
        return None
    m = _READING_ORDER_PAT.search(custom)
    return int(m.group(1)) if m else None

def build_tree(dirs: list) -> Tree:
    tree = Tree(".")
    nodes = {}
    for d in sorted(dirs):
        parts = d.parts
        parent = tree
        for i, part in enumerate(parts):
            key = "/".join(parts[: i +1])
            if key not in nodes:
                nodes[key] = parent.add(part)
            parent = nodes[key]
    return tree

def get_custom_field(custom, group, key):
    """
    Useful to navigate tags in PAGE XML.
    """
    if not custom:
        return None
    match = re.search(rf"{group} \{{{key}:([^;}}]+)", custom)
    return match.group(1) if match else None

#---------- IMAGE PROCESSING -----------#

def contrast_stretch(img_gray, clip_low=0.02, clip_high=0.01):
    """Histogram stretch with clipping, replicating ImageMagick's normalize().
    Clips bottom 2% and top 1% of pixels, then stretches to full [0, 255] range."""
    hist = cv2.calcHist([img_gray], [0], None, [256], [0, 256]).flatten()
    cdf = hist.cumsum()
    total = cdf[-1]
    low = int(np.searchsorted(cdf, total * clip_low))
    high = int(np.searchsorted(cdf, total * (1.0 - clip_high)))
    if high <= low:
        return img_gray
    out = np.clip(img_gray, low, high)
    return ((out - low) / (high - low) * 255).astype(np.uint8)


def moment_normalize(img_gray):
    """Adaptive vertical crop based on edge moments.
    Replicates TextFeatExtractor's momentnorm: computes Sobel edge magnitude,
    finds vertical centroid and spread, crops to 4*sigma centered on centroid."""
    # invert so ink is high
    inv = (255 - img_gray).astype(np.float32)

    # edge magnitude via Sobel
    sob_x = cv2.Sobel(inv, cv2.CV_32F, 1, 0)
    sob_y = cv2.Sobel(inv, cv2.CV_32F, 0, 1)
    mag = cv2.magnitude(sob_x, sob_y)

    m = cv2.moments(mag)
    if m['m00'] == 0:
        return img_gray

    centroid_y = m['m01'] / m['m00']
    sigma_y = np.sqrt(m['mu02'] / m['m00'])
    mom_height = int(round(4 * sigma_y))
    mom_yoff = int(round(centroid_y - 0.5 * mom_height))

    if mom_height <= 0:
        return img_gray

    h, w = img_gray.shape[:2]
    out = np.full((mom_height, w), 255, dtype=np.uint8)

    # source region from input
    src_y0 = max(0, mom_yoff)
    src_y1 = min(h, mom_yoff + mom_height)
    # destination region in output
    dst_y0 = src_y0 - mom_yoff
    dst_y1 = src_y1 - mom_yoff

    if src_y1 > src_y0:
        out[dst_y0:dst_y1, :] = img_gray[src_y0:src_y1, :]

    return out

def deslope(img_gray, bg_color=255):
    """Correct baseline skew via projection profile variance maximization.
    Replicates ImageMagick's deskew() used by TextFeatExtractor with
    threshold at 0.4 * 255 ≈ 102."""
    # fixed threshold at 40% of range, matching ImageMagick's deskew()
    img_bin = (img_gray < 102).astype(np.uint8) * 255
    h, w = img_bin.shape
    best_angle = 0
    best_score = 0

    for angle_10x in range(-50, 51):  # -5.0 to +5.0 degrees, step 0.1
        angle = angle_10x / 10.0
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        rotated = cv2.warpAffine(img_bin, M, (w, h), borderValue=0)
        projection = np.sum(rotated, axis=1)
        score = np.var(projection)
        if score > best_score:
            best_score = score
            best_angle = angle

    M = cv2.getRotationMatrix2D((w / 2, h / 2), best_angle, 1.0)
    return cv2.warpAffine(img_gray, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=bg_color)


def estimate_slant(img_gray, slant_min=-6.0, slant_max=48.0, slant_step=1.0, hsteps=4):
    """Port of TextFeatExtractor's estimateSlant (pyramidal Vinciarelli & Luettin).
    Returns the estimated slant angle in degrees.

    Uses a coarse-to-fine (pyramidal) search over the angle range, scoring each
    candidate by the variance of the normalised vertical projection profile."""
    h, w = img_gray.shape[:2]

    # work on inverted image so ink pixels have high values
    img = (255 - img_gray).astype(np.float64)

    best_angle = 0.0

    xs = np.arange(w)  # column indices, reused across all steps

    for step in range(hsteps):
        skip = 1 << (hsteps - 1 - step)  # 8, 4, 2, 1
        best_score = -1.0

        rows = np.arange(0, h, skip)
        img_rows = img[rows]  # (n_rows, w) — pixel values for sampled rows

        ang = slant_min
        while ang <= slant_max:
            tan_a = np.tan(np.deg2rad(ang))
            shear_w = w + int(abs(h * tan_a)) + 1
            offset = int(abs(min(0.0, h * tan_a)))

            # (n_rows, 1) + (w,) → (n_rows, w) broadcast
            xx = xs[np.newaxis, :] + offset + (rows[:, np.newaxis] * tan_a).astype(int)

            # bincount needs flat 1-d arrays
            valid = (xx >= 0) & (xx < shear_w)
            proj = np.bincount(xx[valid], weights=img_rows[valid],
                               minlength=shear_w).astype(np.float64)

            total = proj.sum()
            if total > 0:
                proj /= total
            score = np.var(proj)

            if score > best_score:
                best_score = score
                best_angle = ang

            ang += slant_step

        # narrow the search around the best angle found so far
        slant_min = best_angle - slant_step
        slant_max = best_angle + slant_step
        slant_step /= 2.0

    return best_angle


def deslant(img_gray, bg_color=255, slant_min=-6.0, slant_max=48.0):
    """Deslant an image using TFE's estimateSlant algorithm.
    Returns the corrected image and the shear value applied."""
    angle = estimate_slant(img_gray, slant_min=slant_min, slant_max=slant_max)
    if abs(angle) < 1e-6:
        return img_gray, 0.0

    h, w = img_gray.shape[:2]
    tan_a = np.tan(np.deg2rad(angle))

    # shear matrix: shifts each row horizontally by y * tan(angle)
    M = np.array([[1, tan_a, -min(0.0, h * tan_a)],
                   [0, 1, 0]], dtype=np.float64)
    new_w = w + int(abs(h * tan_a))
    result = cv2.warpAffine(img_gray, M, (new_w, h),
                            flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_CONSTANT,
                            borderValue=int(bg_color))
    return result, tan_a


def enhance_sauvola(img_gray, win_size=30, k=0.1, slope=0.5):
    """Modified Sauvola: grayscale-preserving local contrast normalization.
    Replicates enhSauvola_single from TextFeatExtractor (intimg.cc).
    Uses integral images with window clipping at borders and geometric window
    expansion (1.05x per step) for uniform regions, matching TFE's C++ implementation."""
    img = img_gray.astype(np.float64)
    h, w = img.shape
    half_win = win_size // 2
    R = 128.0

    # integral images, matching TFE's cv::integral(img, sum, sqsum)
    integ = cv2.integral(img)            # (h+1, w+1)
    integ_sq = cv2.integral(img * img)   # (h+1, w+1)

    # initial pass: clipped window boundaries for every pixel
    ys = np.arange(h)
    xs = np.arange(w)
    y1 = np.maximum(0, ys - half_win)
    y2 = np.minimum(h, ys + half_win + 1)
    x1 = np.maximum(0, xs - half_win)
    x2 = np.minimum(w, xs + half_win + 1)

    local_sum = (integ[y2[:, None], x2[None, :]]
               - integ[y1[:, None], x2[None, :]]
               - integ[y2[:, None], x1[None, :]]
               + integ[y1[:, None], x1[None, :]])
    local_sq_sum = (integ_sq[y2[:, None], x2[None, :]]
                  - integ_sq[y1[:, None], x2[None, :]]
                  - integ_sq[y2[:, None], x1[None, :]]
                  + integ_sq[y1[:, None], x1[None, :]])

    area = (y2 - y1)[:, None] * (x2 - x1)[None, :]
    local_mean = local_sum / area
    local_std = np.sqrt(np.maximum(local_sq_sum / area - local_mean ** 2, 0))

    # enhance pixels with sufficient contrast
    result = np.full((h, w), 255.0)
    has_contrast = local_std > 1e-4

    safe_std = np.maximum(local_std, 1e-4)
    T = local_mean * (1.0 + k * (safe_std / R - 1.0))
    m = 255.0 / (2.0 * slope * safe_std)
    c = 128.0 - m * T
    result[has_contrast] = np.clip(m * img + c, 0, 255)[has_contrast]

    # window expansion for uniform pixels (TFE grows window by 1.05x per step)
    uniform = ~has_contrast
    W = 1.05 * half_win
    max_w = 2 * max(h, w)

    while np.any(uniform) and W < max_w:
        hw = int(W + 0.5)
        uy, ux = np.where(uniform)

        py1 = np.maximum(0, uy - hw)
        py2 = np.minimum(h, uy + hw + 1)
        px1 = np.maximum(0, ux - hw)
        px2 = np.minimum(w, ux + hw + 1)

        s = integ[py2, px2] - integ[py1, px2] - integ[py2, px1] + integ[py1, px1]
        sq = integ_sq[py2, px2] - integ_sq[py1, px2] - integ_sq[py2, px1] + integ_sq[py1, px1]
        a = (py2 - py1) * (px2 - px1)
        mn = s / a
        sd = np.sqrt(np.maximum(sq / a - mn ** 2, 0))

        found = sd > 1e-4
        if np.any(found):
            T_f = mn[found] * (1.0 + k * (sd[found] / R - 1.0))
            m_f = 255.0 / (2.0 * slope * sd[found])
            c_f = 128.0 - m_f * T_f
            pixel_vals = img[uy[found], ux[found]]
            result[uy[found], ux[found]] = np.clip(m_f * pixel_vals + c_f, 0, 255)
            uniform[uy[found], ux[found]] = False

        W *= 1.05

    # remaining uniform pixels stay 255 (entire image has no contrast)
    return result.astype(np.uint8)
