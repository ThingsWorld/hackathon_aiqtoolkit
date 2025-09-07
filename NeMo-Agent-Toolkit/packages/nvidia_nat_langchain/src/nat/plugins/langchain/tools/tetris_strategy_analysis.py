# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Dict, Any, Optional
from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig


class TetrisStrategyAnalysisConfig(FunctionBaseConfig, name="tetris_strategy_analysis"):
    """
    俄罗斯方块策略分析工具
    基于游戏状态提供专业的策略建议
    """
    llm_name: LLMRef
    timeout: int = 25
    verbose: bool = False


@register_function(config_type=TetrisStrategyAnalysisConfig)
async def tetris_strategy_analysis(tool_config: TetrisStrategyAnalysisConfig, builder: Builder):
    import logging
    logger = logging.getLogger(__name__)

    # 获取配置的策略LLM
    llm = await builder.get_llm(tool_config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)

    async def _tetris_strategy_analysis(
        game_state: Dict[str, Any],
        difficulty: str = "intermediate",
        next_pieces: int = 3
    ) -> Dict[str, Any]:
        """
        基于游戏状态提供俄罗斯方块策略建议
        
        Args:
            game_state: 游戏状态字典
            difficulty: 难度级别
            next_pieces: 考虑的未来方块数量
            
        Returns:
            Dict: 包含策略建议的字典
        """
        try:
            # 构建策略提示词
            strategy_prompt = _build_strategy_prompt(game_state, difficulty, next_pieces)
            
            messages = [
                {
                    "role": "system",
                    "content": """你是一个俄罗斯方块策略专家，基于游戏状态提供专业的策略建议。
                    请用中文回复，提供具体、可操作的建议。"""
                },
                {
                    "role": "user",
                    "content": strategy_prompt
                }
            ]
            
            # 调用LLM生成策略
            response = await llm.ainvoke(messages)
            
            return {
                "status": "success",
                "strategy_analysis": response.content,
                "difficulty": difficulty,
                "next_pieces_considered": next_pieces,
                "raw_game_state": game_state
            }
            
        except Exception as e:
            logger.error(f"策略生成失败: {str(e)}")
            return {"status": "error", "message": f"策略生成失败: {str(e)}"}

    def _build_strategy_prompt(game_state: Dict[str, Any], difficulty: str, next_pieces: int) -> str:
        """构建策略分析提示词"""
        return f"""基于以下俄罗斯方块游戏状态，提供{difficulty}难度的策略建议：

游戏状态: {json.dumps(game_state, ensure_ascii=False, indent=2)}

考虑未来{next_pieces}个方块的策略。

请提供：
1. 立即行动建议 - 具体的移动操作
2. 中期策略规划 - 未来几步的布局思路
3. 风险预警 - 需要注意的危险情况
4. 机会识别 - 可以利用的优势机会
5. 分数优化建议 - 如何最大化得分

请用中文回复，提供具体、可操作的建议。"""

    # 创建函数信息
    yield FunctionInfo.from_fn(
        _tetris_strategy_analysis,
        description=("""俄罗斯方块策略分析工具。基于游戏状态提供策略建议。

参数:
    game_state: 游戏状态字典（包含分数、等级、方块布局等信息）
    difficulty: 难度级别 (beginner, intermediate, advanced)
    next_pieces: 考虑的未来方块数量

返回:
    Dict: 包含策略建议的字典，包括具体操作建议和风险评估
"""),
    )
