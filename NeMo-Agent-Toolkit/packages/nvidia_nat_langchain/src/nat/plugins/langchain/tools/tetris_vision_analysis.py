# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import base64
import io
import os
import asyncio
import aiohttp
import json
import re
from typing import Optional, Dict, Any, Union, List
from PIL import Image
from urllib.parse import urlparse

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig


class TetrisVisionAnalysisConfig(FunctionBaseConfig, name="tetris_vision_analysis"):
    """
    俄罗斯方块游戏视觉分析工具
    专门分析俄罗斯方块游戏截图并提取游戏状态信息
    """
    llm_name: LLMRef
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    supported_formats: list = ["jpg", "jpeg", "png", "webp"]
    detail_level: str = "detailed"  # 选项: "basic", "detailed", "expert"
    timeout: int = 60
    verbose: bool = True


@register_function(config_type=TetrisVisionAnalysisConfig)
async def tetris_vision_analysis(tool_config: TetrisVisionAnalysisConfig, builder: Builder):
    import logging
    logger = logging.getLogger(__name__)

    # 获取配置的多模态LLM
    llm = await builder.get_llm(tool_config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)

    async def _tetris_vision_analysis(
        image_input: Union[str, bytes, Image.Image], 
        detail_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析俄罗斯方块游戏截图并提取游戏状态信息
        
        Args:
            image_input: 游戏截图，支持多种格式
            detail_level: 分析详细程度
            
        Returns:
            Dict: 包含游戏状态分析的字典
        """
        try:
            # 处理图片输入
            processed_image_data = await _process_image_input(image_input, tool_config)
            if isinstance(processed_image_data, Dict) and 'error' in processed_image_data:
                return {"status": "error", "message": processed_image_data['error']}
            
            actual_detail_level = detail_level or tool_config.detail_level
            
            # 生成游戏状态分析
            analysis = await _generate_tetris_analysis(
                processed_image_data, 
                actual_detail_level,
                tool_config,
                llm
            )
            
            return {
                "status": "success",
                "analysis": analysis,
                "detail_level": actual_detail_level
            }
            
        except Exception as e:
            logger.error(f"俄罗斯方块分析失败: {str(e)}")
            return {"status": "error", "message": f"游戏分析失败: {str(e)}"}

    async def _generate_tetris_analysis(
        image_data: str, 
        detail_level: str,
        config: TetrisVisionAnalysisConfig,
        llm
    ) -> Dict[str, Any]:
        """生成详细的俄罗斯方块游戏状态分析"""
        
        # 构建游戏特定的提示词
        prompt = _build_tetris_prompt(detail_level)
        
        # 创建多模态LLM的消息 - 使用标准的OpenAI格式
        messages = [
            {
                "role": "system",
                "content": """你是一个专业的俄罗斯方块游戏分析师，专门分析游戏截图并提取游戏状态信息。
                请严格按照JSON格式回复，包含以下字段：
                - current_score: 当前分数
                - current_level: 当前等级
                - lines_cleared: 已消除行数
                - next_piece: 下一个方块类型
                - hold_piece: Hold区域中的方块类型
                - game_status: 游戏状态
                - board_state: 棋盘状态描述
                - active_piece: 当前活跃方块信息
                - risks: 风险分析
                - opportunities: 机会分析
                - recommended_actions: 推荐操作"""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
        
        try:
            # 使用配置的LLM生成分析
            response = await llm.ainvoke(messages)
            
            if config.verbose:
                logger.debug(f"俄罗斯方块分析生成: {response.content}")
            
            analysis = _parse_tetris_analysis(response.content)
            
            return {
                "raw_response": response.content,
                "parsed_analysis": analysis,
                "detail_level": detail_level
            }
                        
        except Exception as e:
            logger.error(f"游戏分析生成失败: {str(e)}")
            return {"error": f"游戏分析生成失败: {str(e)}"}

    def _parse_tetris_analysis(analysis_text: str) -> Dict[str, Any]:
        """解析LLM响应为结构化的游戏状态数据"""
        try:
            # 尝试从文本中提取JSON
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed_data = json.loads(json_str)
                
                # 确保基本字段存在
                required_fields = [
                    "current_score", "current_level", "lines_cleared", 
                    "next_piece", "game_status", "board_state"
                ]
                
                for field in required_fields:
                    if field not in parsed_data:
                        parsed_data[field] = None
                
                return parsed_data
            else:
                # 如果找不到JSON，返回原始文本分析
                return {
                    "text_analysis": analysis_text,
                    "parsing_status": "json_not_found"
                }
        except json.JSONDecodeError:
            # JSON解析失败，返回结构化错误信息
            return {
                "text_analysis": analysis_text,
                "parsing_status": "json_parse_error",
                "error": "Failed to parse JSON response"
            }

    def _build_tetris_prompt(detail_level: str) -> str:
        """构建俄罗斯方块特定的分析提示词"""
        base_prompt = """请分析这张俄罗斯方块游戏截图，提供详细的游戏状态信息。

需要分析的内容：
1. 当前游戏状态（playing-进行中, paused-暂停, game_over-游戏结束）
2. 当前分数、等级和已消除行数
3. 下一个方块预览和Hold区域中的方块
4. 游戏区域中现有的方块布局（10x20网格）
5. 当前活跃的方块位置、类型和方向
6. 潜在的风险和机会分析
7. 建议的最佳移动策略

详细程度要求: {detail_level}

请用严格的JSON格式回复，包含以下字段：
- current_score: 整数
- current_level: 整数  
- lines_cleared: 整数
- next_piece: 字符串 (I, J, L, O, S, T, Z)
- hold_piece: 字符串 (I, J, L, O, S, T, Z 或 null)
- game_status: 字符串
- board_state: 字符串描述
- active_piece: 对象 {type: 类型, position: 位置, rotation: 旋转状态}
- risks: 字符串数组
- opportunities: 字符串数组
- recommended_actions: 字符串数组"""

        prompt = base_prompt.format(detail_level=detail_level)
        
        if detail_level == "expert":
            prompt += "\n\n额外要求：提供未来3步的预测和详细的策略分析。"
        elif detail_level == "detailed":
            prompt += "\n\n提供中等详细程度的分析，包括主要风险和机会。"
            
        return prompt

    # ========== 复用 image_description 的图片处理逻辑 ==========
    
    async def _process_image_input(
        image_input: Union[str, bytes, Image.Image], 
        config: TetrisVisionAnalysisConfig
    ) -> Union[Dict[str, Any], str]:
        """处理图片输入并返回base64编码的字符串"""
        try:
            if isinstance(image_input, str):
                # URL或文件路径
                if _is_url(image_input):
                    return await _download_image(image_input, config)
                else:
                    return await _load_local_image(image_input, config)
            elif isinstance(image_input, bytes):
                return _process_image_bytes(image_input, config)
            elif isinstance(image_input, Image.Image):
                return _process_pil_image(image_input, config)
            else:
                return {"error": "不支持的图片输入格式"}
        except Exception as e:
            return {"error": f"图片处理失败: {str(e)}"}

    def _is_url(string: str) -> bool:
        """检查字符串是否为有效的URL"""
        try:
            result = urlparse(string)
            return all([result.scheme, result.netloc])
        except:
            return False

    async def _download_image(url: str, config: TetrisVisionAnalysisConfig) -> str:
        """从URL下载图片并转换为base64"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return {"error": f"图片下载失败: HTTP {response.status}"}
                    
                    image_data = await response.read()
                    if len(image_data) > config.max_file_size:
                        return {"error": f"图片太大: {len(image_data)} 字节"}
                    
                    return _process_image_bytes(image_data, config)
        except Exception as e:
            return {"error": f"下载失败: {str(e)}"}

    async def _load_local_image(file_path: str, config: TetrisVisionAnalysisConfig) -> str:
        """加载本地图片文件并转换为base64"""
        try:
            if not os.path.exists(file_path):
                return {"error": f"文件不存在: {file_path}"}
            
            with open(file_path, 'rb') as f:
                image_data = f.read()
                if len(image_data) > config.max_file_size:
                    return {"error": f"图片太大: {len(image_data)} 字节"}
                
                return _process_image_bytes(image_data, config)
        except Exception as e:
            return {"error": f"文件读取失败: {str(e)}"}

    def _process_image_bytes(image_data: bytes, config: TetrisVisionAnalysisConfig) -> str:
        """处理图片字节并验证格式"""
        try:
            # 验证图片格式
            image = Image.open(io.BytesIO(image_data))
            image.verify()
            
            # 检查格式支持
            if image.format.lower() not in [fmt.lower() for fmt in config.supported_formats]:
                return {"error": f"不支持的图片格式: {image.format}"}
            
            # 转换为base64
            return base64.b64encode(image_data).decode('utf-8')
            
        except Exception as e:
            return {"error": f"无效的图片数据: {str(e)}"}

    def _process_pil_image(image: Image.Image, config: TetrisVisionAnalysisConfig) -> str:
        """处理PIL Image并转换为base64"""
        try:
            # 转换为字节
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='JPEG')
            image_data = img_buffer.getvalue()
            
            if len(image_data) > config.max_file_size:
                return {"error": f"图片太大: {len(image_data)} 字节"}
            
            return base64.b64encode(image_data).decode('utf-8')
            
        except Exception as e:
            return {"error": f"PIL图片处理失败: {str(e)}"}

    # 创建函数信息
    yield FunctionInfo.from_fn(
        _tetris_vision_analysis,
        description=("""俄罗斯方块游戏视觉分析工具。分析游戏截图并提取游戏状态信息。

参数:
    image_input: 游戏截图，支持URL、文件路径、字节数据或PIL图像
    detail_level: 分析详细程度 (basic, detailed, expert)

返回:
    Dict: 包含游戏状态分析的字典，包括分数、等级、方块布局等信息
"""),
    )
