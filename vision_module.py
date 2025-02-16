from google import genai
from google.genai import types
from PIL import Image
import io
import base64

class VisionModule:
    def __init__(self, api_key):
        # 根据官方最新文档，使用 Client 初始化
        self.client = genai.Client(api_key=api_key)

    def process_image(self, image_data):
        try:
            # 解码 Base64 图像数据为字节流
            image_bytes = base64.b64decode(image_data)
            # 使用 PIL 将字节流转为图像对象
            image = Image.open(io.BytesIO(image_bytes))

            # 自定义文本提示
            custom_prompt = "请根据以下图像生成细粒度描述，详细说明图像中的关键视觉细节。"

            # 按官方示例，将文本和图像一起放进 contents 列表
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[custom_prompt, image]
            )

            # 提取并返回描述文本
            description = response.text.strip() if response.text else "AI 没有返回描述"
            return {"vision_response": description}

        except Exception as e:
            # 返回错误信息
            return {"error": f"处理图像时出错: {str(e)}"}
