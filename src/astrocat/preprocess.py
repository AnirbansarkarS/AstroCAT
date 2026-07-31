import cv2
import numpy as np
from typing import Union, Tuple

def standard_prep(
    image_input: Union[str, np.ndarray],
    target_size: Tuple[int, int] = (256, 256),
    denoise: bool = True
) -> np.ndarray:
    """
    Standard OpenCV preprocessing:
    1. Read / convert to grayscale
    2. Resize to target dimensions
    3. Denoise using GaussianBlur or fastNlMeansDenoising
    """
    if isinstance(image_input, str):
        img = cv2.imread(image_input, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(f"Failed to load image from path: {image_input}")
    elif isinstance(image_input, np.ndarray):
        if len(image_input.shape) == 3 and image_input.shape[2] == 3:
            img = cv2.cvtColor(image_input, cv2.COLOR_BGR2GRAY)
        else:
            img = image_input.copy()
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    # Resize
    img_resized = cv2.resize(img, target_size, interpolation=cv2.INTER_AREA)

    # Denoise
    if denoise:
        img_prep = cv2.GaussianBlur(img_resized, (3, 3), 0)
    else:
        img_prep = img_resized

    return img_prep

def align(
    reference_img: np.ndarray,
    moving_img: np.ndarray
) -> np.ndarray:
    """
    Align moving image to reference image using ORB feature matching and Homography.
    If alignment fails (not enough matches or RANSAC failure), returns moving_img.
    """
    orb = cv2.ORB_create(nfeatures=500)
    kp1, des1 = orb.detectAndCompute(reference_img, None)
    kp2, des2 = orb.detectAndCompute(moving_img, None)

    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        return moving_img

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)

    if len(matches) < 4:
        return moving_img

    src_pts = np.float32([kp2[m.trainIdx].pt for m in matches[:50]]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp1[m.queryIdx].pt for m in matches[:50]]).reshape(-1, 1, 2)

    matrix, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

    if matrix is None:
        return moving_img

    h, w = reference_img.shape[:2]
    aligned_moving = cv2.warpPerspective(moving_img, matrix, (w, h))
    return aligned_moving
