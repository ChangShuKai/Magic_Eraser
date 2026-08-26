import cv2
import numpy as np
import glob
import os

def align_images(im1_path, im2_path, out_path):
    print(f"Aligning {os.path.basename(im1_path)}...")
    # 讀取圖片，以灰階模式進行特徵比對
    img1 = cv2.imread(im1_path, cv2.IMREAD_GRAYSCALE) # Input (dirty)
    img2 = cv2.imread(im2_path, cv2.IMREAD_GRAYSCALE) # Target (clean)
    
    if img1 is None or img2 is None:
        print(f"Error reading images: {im1_path} or {im2_path}")
        return False

    # 由於原圖很大，為了加速特徵擷取，先縮小圖片
    max_dim = 2000
    scale1 = max_dim / max(img1.shape)
    scale2 = max_dim / max(img2.shape)
    
    img1_small = cv2.resize(img1, (0,0), fx=scale1, fy=scale1)
    img2_small = cv2.resize(img2, (0,0), fx=scale2, fy=scale2)

    # 使用 SIFT 擷取特徵點 (比 ORB 穩定，特別是對於文字與線條)
    sift = cv2.SIFT_create(nfeatures=5000)
    kp1, des1 = sift.detectAndCompute(img1_small, None)
    kp2, des2 = sift.detectAndCompute(img2_small, None)

    # FLANN 特徵匹配
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    
    try:
        matches = flann.knnMatch(des1, des2, k=2)
    except Exception as e:
        print(f"Matching failed for {os.path.basename(im1_path)}: {e}")
        return False

    # Lowe's ratio test 過濾優良匹配點
    good_matches = []
    for m, n in matches:
        if m.distance < 0.7 * n.distance:
            good_matches.append(m)

    if len(good_matches) < 10:
        print(f"Not enough matches found for {os.path.basename(im1_path)} ({len(good_matches)}/10)")
        return False

    # 取得原始尺度下的座標點
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2) / scale1
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2) / scale2

    # 計算 Homography 變換矩陣 (RANSAC 排除錯誤點)
    M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
    
    if M is None:
        print(f"Homography calculation failed for {os.path.basename(im1_path)}")
        return False

    # 讀取彩色目標圖片進行變換
    img2_color = cv2.imread(im2_path)
    h, w = img1.shape
    
    # 執行幾何變換，將 img2 扭曲成 img1 的視角與大小
    aligned_img2 = cv2.warpPerspective(img2_color, M, (w, h), borderValue=(255, 255, 255))
    
    # 存檔
    cv2.imwrite(out_path, aligned_img2)
    print(f"Success! Aligned image saved to {out_path}")
    return True

def main():
    input_dir = "../real_data/input"
    target_dir = "../real_data/target"
    out_dir = "../real_data/target_aligned"
    
    os.makedirs(out_dir, exist_ok=True)
    
    input_files = sorted(glob.glob(os.path.join(input_dir, "*.*")))
    
    success_count = 0
    for inp_path in input_files:
        basename = os.path.basename(inp_path)
        tgt_path = os.path.join(target_dir, basename)
        
        if os.path.exists(tgt_path):
            out_path = os.path.join(out_dir, basename)
            if align_images(inp_path, tgt_path, out_path):
                success_count += 1
        else:
            print(f"Target not found for {basename}")
            
    print(f"\nAlignment Complete! {success_count}/{len(input_files)} images successfully aligned.")

if __name__ == '__main__':
    main()
