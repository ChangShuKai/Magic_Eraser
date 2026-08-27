import requests

url = "https://changshukai--exam-cleaner-cleanerservice-clean-image.modal.run"
with open("D:\\書愷\\硬碟暫放\\Python\\去手寫\\train_pipeline\\my_test.png", "rb") as f:
    files = {"image": f}
    data = {
        "color_type": "both",
        "fill_method": "inpaint",
        "enhance": "false"
    }
    print("Sending request...")
    response = requests.post(url, files=files, data=data)
    print("Status:", response.status_code)
    if response.status_code != 200:
        print("Error:", response.text)
    else:
        print("Success! Image size:", len(response.content))
