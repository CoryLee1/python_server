#!/usr/bin/env python
"""
简单的模型测试脚本 - 只需修改MODEL_NAME变量即可测试不同模型
改进版：移除Vertex模型，增强错误处理
"""
import asyncio
import json
import os
import sys
from ai_manager import ai_manager, DEFAULT_SYSTEM_PROMPT

# ======= 修改这里测试不同模型 =======
# 可以从环境变量加载默认模型，或者在这里直接指定
MODEL_NAME = os.getenv("DEFAULT_MODEL", "openai")  # 修改此变量测试不同模型

# 测试提示
TEST_PROMPT = "请用简单的语言解释量子计算的基本原理"

# 可选: 修改这些参数测试不同设置 - 移除了top_k参数，因为不是所有模型都支持
MODEL_CONFIG = {
    "temperature": 0.7,  # 控制随机性 (0.0-1.0)
    "max_tokens": 200,  # 输出长度
    "top_p": 0.9,  # 输出多样性
}

# 可选: 添加Gemini特有的参数
GEMINI_CONFIG = MODEL_CONFIG.copy()
GEMINI_CONFIG["top_k"] = 40  # 只对Gemini有效

# 可选: 自定义系统提示
SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT

# 模型到提供商的映射关系
MODEL_PROVIDER_MAP = {
    "gpt-4": "OpenAI",
    "gpt-3.5-turbo": "OpenAI",
    "openai": "OpenAI",  # 添加直接使用"openai"的映射
    "claude-3-opus": "Anthropic",
    "claude-3-sonnet": "Anthropic",
    "claude-3-haiku": "Anthropic",
    "claude-3": "Anthropic",
    "claude": "Anthropic",
    "gemini": "Google Gemini",
    "gemini-pro": "Google Gemini",
    "deepseek-chat": "DeepSeek",
    "deepseek-coder": "DeepSeek"
}


# 检查模型对应的API是否配置
def is_model_configured(model_name):
    """检查指定模型的API密钥是否正确配置"""
    provider = MODEL_PROVIDER_MAP.get(model_name, "Unknown")
    
    # 根据提供商检查配置
    if provider == "OpenAI":
        return bool(ai_manager.api_keys["openai"])
    elif provider == "Anthropic":
        return bool(ai_manager.api_keys["anthropic"])
    elif provider == "Google Gemini":
        return bool(ai_manager.api_keys["gemini"])
    elif provider == "DeepSeek":
        return bool(ai_manager.api_keys["deepseek"])
    else:
        # 对于未知提供商，检查它是否在模型映射中存在
        return model_name in ai_manager.model_map


# 根据模型选择合适的配置
def get_model_config(model_name):
    """根据模型类型返回适合的配置"""
    if "gemini" in model_name:
        return GEMINI_CONFIG  # Gemini模型使用含top_k的配置
    else:
        return MODEL_CONFIG  # 其他模型使用标准配置

        
async def test_model():
    """测试指定的模型"""
    print(f"🧪 测试模型: {MODEL_NAME}")
    
    # 检查模型配置
    if not is_model_configured(MODEL_NAME):
        provider = MODEL_PROVIDER_MAP.get(MODEL_NAME, "未知提供商")
        print(f"❌ 错误: {MODEL_NAME} 模型未正确配置")
        print(f"   需要配置 {provider} 的API密钥")
        return
    
    print(f"📝 提示: {TEST_PROMPT}")
    
    # 获取适合当前模型的配置
    model_config = get_model_config(MODEL_NAME)
    print(f"⚙️ 配置: {json.dumps(model_config, indent=2)}")
    
    try:
        response = await ai_manager.generate_text_response(
            user_input=TEST_PROMPT,
            system_prompt=SYSTEM_PROMPT,
            model_name=MODEL_NAME,
            config=model_config
        )
        
        print("\n" + "="*50)
        print(f"📊 模型 {MODEL_NAME} 的响应:")
        print(response)
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"❌ 测试失败: {MODEL_NAME} - {str(e)}")


# 测试一批模型
async def test_multiple_models():
    """测试多个模型的响应"""
    # 定义要测试的模型 - 移除了Vertex模型
    models = [
        "gemini",          # Google Gemini API
        "gpt-3.5-turbo",   # OpenAI
        "claude-3-haiku",  # Anthropic 
        "claude-3-sonnet", # Anthropic (更稳定的模型)
        "deepseek-chat",   # DeepSeek
    ]
    
    results = {
        "成功": [],
        "配置错误": [],
        "请求错误": []
    }
    
    # 统计测试结果
    total = len(models)
    success_count = 0
    config_error_count = 0
    request_error_count = 0
    
    for model in models:
        print(f"\n🧪 测试模型: {model}")
        
        # 检查模型配置
        if not is_model_configured(model):
            provider = MODEL_PROVIDER_MAP.get(model, "未知提供商")
            print(f"❌ 配置错误: {model} 模型未正确配置")
            print(f"   需要配置 {provider} 的API密钥")
            results["配置错误"].append(model)
            config_error_count += 1
            continue
        
        try:
            # 获取适合当前模型的配置
            model_config = get_model_config(model)
            
            response = await ai_manager.generate_text_response(
                user_input=TEST_PROMPT,
                system_prompt=SYSTEM_PROMPT,
                model_name=model,
                config=model_config
            )
            
            # 检查响应是否含有错误标记
            if response and response.startswith("⚠️"):
                print(f"❌ 请求错误: {response}")
                results["请求错误"].append(model)
                request_error_count += 1
            else:
                print(f"✅ 成功: {response[:150]}...")
                results["成功"].append(model)
                success_count += 1
                
        except Exception as e:
            print(f"❌ 请求错误: {model} - {str(e)}")
            results["请求错误"].append(model)
            request_error_count += 1
    
    # 打印摘要
    print("\n" + "="*50)
    print("📋 测试摘要")
    print(f"总计测试模型: {total}")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 配置错误: {config_error_count}")
    print(f"❌ 请求错误: {request_error_count}")
    
    if results["成功"]:
        print("\n✅ 成功的模型:")
        for model in results["成功"]:
            print(f"  • {model}")
    
    if results["配置错误"]:
        print("\n❌ 配置错误的模型:")
        for model in results["配置错误"]:
            provider = MODEL_PROVIDER_MAP.get(model, "未知提供商")
            print(f"  • {model} (需要配置 {provider} API密钥)")
    
    if results["请求错误"]:
        print("\n❌ 请求错误的模型:")
        for model in results["请求错误"]:
            print(f"  • {model}")
    
    return results


async def check_available_models():
    """检查可用模型"""
    print("🔍 检查可用模型...")
    available_models = ai_manager.get_available_models()
    
    print("\n可用的文本模型:")
    for model in available_models["text"]:
        # 跳过Vertex模型
        if "vertex" in model:
            continue
            
        if is_model_configured(model):
            print(f"  ✅ {model}")
        else:
            provider = MODEL_PROVIDER_MAP.get(model, "未知提供商")
            print(f"  ❌ {model} (配置不正确，需要 {provider} API密钥)")
    
    print("\n可用的视觉模型:")
    for model in available_models["vision"]:
        # 跳过Vertex模型
        if "vertex" in model:
            continue
            
        if is_model_configured(model):
            print(f"  ✅ {model}")
        else:
            provider = MODEL_PROVIDER_MAP.get(model, "未知提供商")
            print(f"  ❌ {model} (配置不正确，需要 {provider} API密钥)")
    
    return available_models


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="简单的模型测试脚本")
    parser.add_argument("-a", "--all", action="store_true", help="测试所有列出的模型")
    parser.add_argument("-p", "--prompt", help="自定义测试提示")
    parser.add_argument("-m", "--model", help="指定要测试的模型")
    parser.add_argument("-l", "--list", action="store_true", help="列出所有可用模型")
    
    args = parser.parse_args()
    
    if args.prompt:
        TEST_PROMPT = args.prompt
    
    if args.model:
        MODEL_NAME = args.model
    
    if args.list:
        asyncio.run(check_available_models())
    elif args.all:
        asyncio.run(test_multiple_models())
    else:
        asyncio.run(test_model())