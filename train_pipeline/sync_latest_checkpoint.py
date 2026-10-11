import os
import glob
import subprocess
import sys

def sync_checkpoint():
    """
    自動確認 train_pipeline/checkpoints 裡最新的 .pth 檔案，
    刪除本地舊版只留最新一版，並同步更新 Git 追蹤。
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ckpt_dir = os.path.join(base_dir, "checkpoints")
    
    if not os.path.exists(ckpt_dir):
        return
        
    pth_files = glob.glob(os.path.join(ckpt_dir, "model_epoch_*.pth"))
    if not pth_files:
        print("[sync_checkpoint] checkpoints 目錄中無 model_epoch_*.pth 檔案。")
        return

    def get_epoch(f):
        try:
            name = os.path.basename(f)
            return int(name.replace("model_epoch_", "").replace(".pth", ""))
        except Exception:
            return -1

    latest_file = max(pth_files, key=get_epoch)
    latest_epoch = get_epoch(latest_file)
    print(f"[sync_checkpoint] 最新模型: {os.path.basename(latest_file)} (Epoch {latest_epoch})")

    # 1. 刪除本地舊版本
    deleted_count = 0
    for f in pth_files:
        if os.path.abspath(f) != os.path.abspath(latest_file):
            try:
                os.remove(f)
                deleted_count += 1
            except Exception as e:
                print(f"[sync_checkpoint] 刪除本地舊檔案失敗 {f}: {e}")
    if deleted_count > 0:
        print(f"[sync_checkpoint] 已清理本地舊版權重: {deleted_count} 個")

    # 2. 同步 Git 追蹤
    repo_root = os.path.dirname(base_dir)
    try:
        rel_latest = os.path.relpath(latest_file, repo_root).replace("\\", "/")
        
        # 查詢目前 Git 追蹤的所有 checkpoints/*.pth
        result = subprocess.run(
            ["git", "ls-files", "train_pipeline/checkpoints/*.pth"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )
        tracked_pth = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]

        for tracked in tracked_pth:
            if tracked != rel_latest:
                print(f"[sync_checkpoint] 從 Git 追蹤移除舊版: {tracked}")
                subprocess.run(["git", "rm", "--cached", "-f", tracked], cwd=repo_root, check=False)

        # 加入最新版至 Git 暫存區
        subprocess.run(["git", "add", rel_latest], cwd=repo_root, check=True)
        print(f"[sync_checkpoint] 已將最新模型加入 Git: {rel_latest}")
    except Exception as e:
        print(f"[sync_checkpoint] Git 同步提示: {e}")

if __name__ == "__main__":
    sync_checkpoint()
