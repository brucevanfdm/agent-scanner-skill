# Agent Skill Scanner

[English](README.md) | [中文](README_CN.md)

一款用于检测 Agent Skills 包安全性的扫描工具，支持检测提示注入、数据泄露、工具滥用及其他 AI 特定威胁。

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

## 概述

Agent Skill Scanner 是一款专门的安全工具，用于审计 AI Agent Skill 包（兼容 OpenAI Codex、Cursor Agent Skills 等格式）。它通过静态分析在技能部署到生产环境前识别安全风险。

### 核心特性

- **离线优先设计** - 完全本地运行，无网络依赖
- **级联扫描** - 渐进式分析（quick → balanced → deep），根据发现的问题自动升级
- **80+ 安全模式** - 覆盖 12+ 类威胁，遵循 AITech 分类标准
- **多种输出格式** - 支持 Summary、JSON、Markdown、Table 和 SARIF（CI/CD 集成）
- **跨技能分析** - 检测技能间的触发劫持和描述重叠
- **可扩展架构** - 基于 YARA 规则的插件化分析器

## 威胁分类

| 类别 | AITech 代码 | 描述 |
|------|-------------|------|
| 提示注入 | AITech-1.1 | 直接尝试覆盖系统指令 |
| 间接注入 | AITech-1.2 | 来自外部来源的恶意指令 |
| 命令注入 | AITech-9.1.4 | SQL 注入、命令执行、XSS |
| 数据泄露 | AITech-8.2 | 通过工具未授权暴露数据 |
| 工具链滥用 | AITech-8.2.3 | 可疑的多步数据提取 |
| 硬编码密钥 | AITech-8.2.1 | 代码中的 API 密钥、凭据 |
| 混淆技术 | AITech-9.1.3 | 代码混淆手段 |
| 资源滥用 | AITech-13.1 | Fork 炸弹、无限循环、DoS |
| 社会工程学 | AITech-15.1 | 误导性元数据、品牌冒充 |
| 触发劫持 | AITech-4.3.5 | 过于宽泛的技能描述 |

## 安装

### 方式一：作为 Skill 运行（嵌入式模式）

扫描器自带 Python 运行时，无需安装：

```bash
# 克隆仓库
git clone https://github.com/yourusername/agent-scanner-skill.git
cd agent-scanner-skill

# 直接使用包装脚本运行
./scripts/run-scan.sh scan /path/to/skill quick
```

### 方式二：作为 Python 包安装

```bash
# 从源码安装
pip install -e .

# 或从 PyPI 安装（发布后）
pip install agent-scanner-skill
```

## 快速开始

### 扫描单个技能

```bash
skill-scanner scan /path/to/skill
```

### 扫描多个技能

```bash
skill-scanner scan-all /path/to/skills --recursive
```

### 使用级联扫描配置

```bash
# 快速扫描（发现问题自动升级）
./scripts/run-scan.sh scan ./my-skill quick

# 平衡扫描（包含快速 + 更深入分析）
./scripts/run-scan.sh scan ./my-skill balanced

# 深度扫描（最大覆盖范围）
./scripts/run-scan.sh scan ./my-skill deep-agent

# CI 配置（SARIF + 发现问题即失败）
./scripts/run-scan.sh scan-all ./skills ci --output results.sarif
```

## 使用示例

### 基础安全扫描

```bash
skill-scanner scan ./my-skill --format summary
```

### JSON 格式输出（自动化）

```bash
skill-scanner scan ./my-skill --format json --output report.json
```

### SARIF 格式（GitHub 代码扫描）

```bash
skill-scanner scan-all ./skills --format sarif --output results.sarif
```

### 启用行为分析

```bash
skill-scanner scan ./my-skill --use-behavioral
```

### 使用自定义 YARA 规则

```bash
skill-scanner scan ./my-skill --custom-rules ./my-rules/
```

### CI/CD 集成

```bash
# 发现严重/高级问题时返回错误码
skill-scanner scan ./my-skill --fail-on-findings
```

## CLI 参考

### 命令

| 命令 | 描述 |
|------|------|
| `scan <dir>` | 扫描单个技能包 |
| `scan-all <dir>` | 扫描目录中的所有技能 |
| `list-analyzers` | 列出可用分析器 |
| `validate-rules` | 验证规则签名 |

### 选项

| 选项 | 描述 |
|------|------|
| `--format` | 输出格式：summary、json、markdown、table、sarif |
| `--output, -o` | 将报告写入文件 |
| `--detailed` | 包含详细发现 |
| `--recursive, -r` | 递归搜索技能 |
| `--use-behavioral` | 启用行为数据流分析 |
| `--use-trigger` | 启用触发器特异性分析 |
| `--yara-mode` | YARA 模式：strict、balanced、permissive |
| `--custom-rules` | 自定义 YARA 规则路径 |
| `--disable-rule` | 禁用特定规则（可重复） |
| `--fail-on-findings` | 发现严重/高级问题时退出并返回错误 |
| `--check-overlap` | 检查技能间的描述重叠 |

## 输出格式

### 摘要格式

```
============================================================
技能: my-skill
============================================================
状态: [FAIL] 发现问题
最高严重性: HIGH
发现问题总数: 3
扫描耗时: 1.23s

问题汇总:
  Critical: 1
  High:     1
  Medium:   1
  Low:      0
  Info:     0
```

### JSON 格式

```json
{
  "skill_name": "my-skill",
  "is_safe": false,
  "max_severity": "HIGH",
  "findings": [...]
}
```

### SARIF 格式

兼容 GitHub Advanced Security、Azure DevOps 及其他 SARIF 消费工具。

## 架构

### 分析器

1. **StaticAnalyzer**（默认）
   - 基于 YAML 规则的模式检测
   - 兼容 YARA 的规则引擎
   - 80+ 安全签名

2. **BehavioralAnalyzer**
   - 静态数据流分析
   - 基于 AST 的污点跟踪
   - 跨文件关联分析

3. **TriggerAnalyzer**
   - 描述特异性分析
   - 关键词诱饵检测
   - 触发劫持风险评估

### 项目结构

```
agent-scanner-skill/
├── skill_scanner/           # 核心扫描器代码
│   ├── core/
│   │   ├── analyzers/       # 分析引擎
│   │   ├── models.py        # 数据模型
│   │   ├── scanner.py       # 主扫描器
│   │   └── reporters/       # 输出格式化器
│   ├── data/
│   │   └── rules/           # 安全签名
│   ├── threats/             # 威胁分类
│   └── cli/                 # 命令行界面
├── scripts/                 # 实用脚本
├── vendor/                  # Python 运行时
├── references/              # 文档
└── agents/                  # Agent 配置
```

## 贡献

欢迎贡献！请参阅我们的贡献指南了解详情。

### 添加自定义规则

在自定义规则目录中创建 YARA 规则文件：

```yaml
# custom-rules/my-rule.yaml
- id: MY_CUSTOM_RULE
  category: command_injection
  severity: HIGH
  patterns:
    - "dangerous_pattern"
  file_types: [python, bash]
  description: "我的自定义安全检查"
  remediation: "如何修复此问题"
```

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/agent-scanner-skill.git
cd agent-scanner-skill

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 以开发模式安装
pip install -e .

# 运行测试
pytest
```

## 文档

- [扫描配置](references/scan-profiles.md) - 预配置扫描配置文件
- [修复指南](references/remediation-playbook.md) - 如何修复发现的问题
- [威胁分类](skill_scanner/threats/threats.py) - AITech 分类参考
- [供应商运行时](vendor/README.md) - 离线运行时设置

## 许可证

版权所有 2026 Cisco Systems, Inc.

根据 Apache 许可证 2.0 版（"许可证"）授权；
除非遵守许可证，否则您不得使用此文件。
您可以在以下网址获取许可证副本：

    http://www.apache.org/licenses/LICENSE-2.0

除非适用法律要求或以书面形式同意，否则根据许可证分发的软件
按"原样"分发，不附带任何明示或暗示的担保或条件。
有关许可证下特定语言的权限和
限制，请参阅许可证。

SPDX-License-Identifier: Apache-2.0

## 安全

如发现安全漏洞，请遵循我们的[安全策略](SECURITY.md)。

## 致谢

采用 AITech 分类法实现标准化威胁分类。
兼容 OpenAI Codex 和 Cursor Agent Skills 格式。
