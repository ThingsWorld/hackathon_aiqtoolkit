#!/bin/bash

echo "🚀 启动 NVIDIA NeMo Agent Toolkit - 俄罗斯方块分析系统"
echo "======================================================"

# 设置环境变量
export TAVILY_API_KEY=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

# 启动后端服务
echo "📡 启动俄罗斯方块分析后端服务..."
aiq serve --config_file configs/tetris_agent_config.yml --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!

# 等待后端启动
echo "⏳ 等待后端服务启动..."
sleep 8

# 检查后端是否正常启动
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ 后端服务启动成功"
else
    echo "❌ 后端服务启动失败，请检查配置"
    exit 1
fi

# 启动前端服务
echo "🎨 启动前端服务..."
cd external/aiqtoolkit-opensource-ui
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ 俄罗斯方块分析系统启动完成！"
echo ""
echo "🌐 访问地址:"
echo "   前端界面: http://localhost:3000"
echo "   API文档:  http://localhost:8001/docs"
echo ""
echo "🎮 使用说明:"
echo "   1. 上传俄罗斯方块游戏截图或提供图片URL"
echo "   2. 系统将自动分析游戏状态"
echo "   3. 获取详细的策略建议和分析报告"
echo ""
echo "📝 示例输入:"
echo "   - '分析这张俄罗斯方块截图: https://example.com/tetris.jpg'"
echo "   - '帮我分析当前的游戏局势'"
echo "   - '给出下一步的最佳操作建议'"
echo ""
echo "🛑 停止服务: 按 Ctrl+C 或运行 ./stop.sh"
echo ""

# 保存进程ID
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

# 等待用户中断
wait
