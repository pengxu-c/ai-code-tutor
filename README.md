# AI 编程题讲解机器人

面向编程学习者的错解代码诊断与变式训练系统。用户输入题目描述、错误代码、报错信息和测试用例后，系统会生成包含代码结构分析、错误诊断、运行验证和变式练习的 Markdown 讲解报告。

## 功能

- Python AST 代码结构分析
- DeepSeek 大模型错误诊断与代码解释
- 子进程沙箱运行测试用例
- 本地题库与 LLM 结合生成变式训练题
- LeetCode 在线题库按需检索与导入
- Gradio Web 界面展示诊断报告

## 安装

```bash
pip install -r requirements.txt
```

## 配置

建议通过环境变量配置 DeepSeek API Key：

```bash
export DEEPSEEK_API_KEY=your-deepseek-api-key
```

也可以在 Gradio 页面中的配置区域临时输入 API Key。

LeetCode 在线题库默认使用 `https://leetcode.cn/graphql/`，如需切换可设置：

```bash
export LEETCODE_GRAPHQL_URL=https://leetcode.cn/graphql/
```

## 启动

```bash
python app.py
```

或在类 Unix 环境中运行：

```bash
bash run.sh
```

默认访问地址为 `http://127.0.0.1:7860`。

## LeetCode 题库说明

项目不会批量复制或内置 LeetCode 全量题面。页面中的“LeetCode 在线题库”支持按需检索，并在用户输入题目 slug 或链接后临时导入单题内容用于讲解。
