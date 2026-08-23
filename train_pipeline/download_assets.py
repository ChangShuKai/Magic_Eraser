import os
import urllib.request
import zipfile

def download_file(url, save_path):
    print(f"Downloading {url} to {save_path}...")
    urllib.request.urlretrieve(url, save_path)
    print("Download complete.")

def main():
    os.makedirs("assets/fonts", exist_ok=True)

    fonts = [
        {
            "name": "NotoSansTC-Regular (印刷字體 - 黑體)",
            "url": "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf",
            "filename": "assets/fonts/NotoSansTC-Regular.otf"
        },
        {
            "name": "NotoSerifTC-Regular (印刷字體 - 明體)",
            "url": "https://github.com/notofonts/noto-cjk/raw/main/Serif/OTF/TraditionalChinese/NotoSerifCJKtc-Regular.otf",
            "filename": "assets/fonts/NotoSerifTC-Regular.otf"
        },
        {
            "name": "ChenYuluoyan (手寫字體 - 辰宇落雁體)",
            "url": "https://github.com/Chenyu-otf/chenyuluoyan_thin/raw/main/ChenYuluoyan-Thin.ttf",
            "filename": "assets/fonts/ChenYuluoyan-Thin.ttf"
        },
        {
            "name": "SetoFont (手寫字體 - 瀨戶字體)",
            "url": "https://raw.githubusercontent.com/max32002/setofont/master/setofont.ttf",
            "filename": "assets/fonts/setofont.ttf"
        }
    ]

    for font in fonts:
        if not os.path.exists(font["filename"]):
            try:
                download_file(font["url"], font["filename"])
            except Exception as e:
                print(f"Failed to download {font['name']}: {e}")
        else:
            print(f"{font['name']} already exists.")

if __name__ == "__main__":
    main()
