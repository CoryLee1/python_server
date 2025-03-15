#!/usr/bin/env python
"""
视觉模型测试脚本 - 用于测试各种AI模型的图像处理能力
"""
import asyncio
import json
import os
import sys
import base64
from pathlib import Path
from ai_manager import ai_manager, DEFAULT_SYSTEM_PROMPT

# ======= 修改这里测试不同模型 =======
# 默认视觉模型
VISION_MODEL = os.getenv("VISION_MODEL", "gemini")  # 默认使用Gemini

# 测试提示
VISION_PROMPT = "请描述这张图片的内容，尽可能详细。"

# 视觉配置参数
VISION_CONFIG = {
    "temperature": 0.7,   # 控制随机性 (0.0-1.0)
    "max_tokens": 300,    # 输出长度
    "top_p": 0.9,         # 输出多样性
}

# Gemini特有的配置
GEMINI_VISION_CONFIG = VISION_CONFIG.copy()
GEMINI_VISION_CONFIG["top_k"] = 40  # 只对Gemini有效

# 视觉模型列表
VISION_MODELS = [
    "gemini",            # Google Gemini API
    "gpt-4",             # OpenAI GPT-4 Vision
    "claude-3-opus",     # Anthropic Claude-3-Opus
]


async def read_image_as_base64(image_path):
    """从文件路径读取图像并转换为base64编码"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        print(f"读取图像文件失败: {str(e)}")
        return None


async def test_vision_model(model_name, image_path, prompt=VISION_PROMPT):
    """测试指定视觉模型的图像处理能力"""
    print(f"🧪 测试视觉模型: {model_name}")
    
    # 检查图像文件存在
    if not os.path.exists(image_path):
        print(f"❌ 错误: 找不到图像文件 {image_path}")
        return
    
    # 读取图像
    image_base64 = await read_image_as_base64(image_path)
    if not image_base64:
        print(f"❌ 错误: 无法读取图像文件 {image_path}")
        return
    
    print(f"📝 提示: {prompt}")
    
    # 获取适合当前模型的配置
    config = GEMINI_VISION_CONFIG if "gemini" in model_name else VISION_CONFIG
    print(f"⚙️ 配置: {json.dumps(config, indent=2)}")
    
    try:
        # 添加数据URI前缀
        image_data = f"data:image/jpeg;base64,{image_base64}"
        
        # 处理图像
        response = await ai_manager.process_image(
            image_data=image_data,
            prompt=prompt,
            model_name=model_name,
            config=config
        )
        
        print("\n" + "="*50)
        print(f"📊 模型 {model_name} 的响应:")
        if "vision_response" in response:
            print(response["vision_response"])
        else:
            print(response)
        print("="*50 + "\n")
        
        return response
        
    except Exception as e:
        print(f"❌ 测试失败: {model_name} - {str(e)}")
        return None


async def test_multiple_vision_models(image_path, prompt=VISION_PROMPT):
    """测试多个视觉模型的响应"""
    results = {
        "成功": [],
        "失败": []
    }
    
    # 统计测试结果
    total = len(VISION_MODELS)
    success_count = 0
    failure_count = 0
    
    for model in VISION_MODELS:
        try:
            response = await test_vision_model(model, image_path, prompt)
            
            # 检查响应是否有效
            if response and not str(response).startswith("⚠️"):
                results["成功"].append(model)
                success_count += 1
            else:
                results["失败"].append(model)
                failure_count += 1
                
        except Exception as e:
            print(f"❌ 请求错误: {model} - {str(e)}")
            results["失败"].append(model)
            failure_count += 1
    
    # 打印摘要
    print("\n" + "="*50)
    print("📋 视觉模型测试摘要")
    print(f"总计测试模型: {total}")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {failure_count}")
    
    if results["成功"]:
        print("\n✅ 成功的模型:")
        for model in results["成功"]:
            print(f"  • {model}")
    
    if results["失败"]:
        print("\n❌ 失败的模型:")
        for model in results["失败"]:
            print(f"  • {model}")
    
    return results


async def test_text_model(model_name, prompt):
    """测试指定模型的文本能力"""
    print(f"🧪 测试文本模型: {model_name}")
    
    # 获取适合当前模型的配置
    config = GEMINI_VISION_CONFIG if "gemini" in model_name else VISION_CONFIG
    
    try:
        response = await ai_manager.generate_text_response(
            user_input=prompt,
            model_name=model_name,
            config=config
        )
        
        print("\n" + "="*50)
        print(f"📊 模型 {model_name} 的响应:")
        print(response)
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"❌ 测试失败: {model_name} - {str(e)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="视觉模型测试脚本")
    parser.add_argument("-i", "--image", required=True, help="要处理的图像文件路径")
    parser.add_argument("-p", "--prompt", default=VISION_PROMPT, help="自定义提示")
    parser.add_argument("-m", "--model", default=VISION_MODEL, help="指定要测试的视觉模型")
    parser.add_argument("-a", "--all", action="store_true", help="测试所有视觉模型")
    parser.add_argument("-t", "--text", help="测试文本模型（不处理图像）")
    
    args = parser.parse_args()
    
    if args.text:
        # 只测试文本能力
        asyncio.run(test_text_model(args.model, args.text))
    elif args.all:
        # 测试所有视觉模型
        asyncio.run(test_multiple_vision_models(args.image, args.prompt))
    else:
        # 测试指定视觉模型
        asyncio.run(test_vision_model(args.model, args.image, args.prompt))
