"""
Claude API integration for AI-powered quality analysis.
Includes fallback to rule-based analysis when API is unavailable.
"""
import os
from config import CLAUDE_API_KEY, CLAUDE_MODEL

# AI report prompt template
REPORT_PROMPT_ZH = """你是一位资深质量工程师。请基于以下工厂验货数据，生成一份质量改进建议报告：

## 工厂信息
- 工厂名称: {factory_name}
- 区域: {region}
- 历史质量评分: {quality_rating}

## 近期验货数据摘要
- 验货次数: {inspection_count}
- 通过率: {pass_rate}%
- 主要缺陷类型: {top_defects}
- 触发告警原因: {trigger_reasons}

## 详细缺陷数据
{defect_detail_table}

请输出以下内容：
1. **问题根因分析（Root Cause Analysis）**
2. **短期纠正措施（Corrective Actions，1-2周内）**
3. **长期预防措施（Preventive Actions，1-3个月）**
4. **建议调整的验货策略（如加严检验、增加验货频次等）**
5. **风险等级评估（高/中/低）及理由**

请用中文回答，格式清晰，条目分明。"""

REPORT_PROMPT_EN = """You are a senior quality engineer. Based on the following factory inspection data, generate a quality improvement report:

## Factory Information
- Factory Name: {factory_name}
- Region: {region}
- Historical Quality Rating: {quality_rating}

## Recent Inspection Summary
- Inspection Count: {inspection_count}
- Pass Rate: {pass_rate}%
- Top Defect Types: {top_defects}
- Alert Trigger Reasons: {trigger_reasons}

## Detailed Defect Data
{defect_detail_table}

Please provide:
1. **Root Cause Analysis**
2. **Short-term Corrective Actions (1-2 weeks)**
3. **Long-term Preventive Actions (1-3 months)**
4. **Recommended Inspection Strategy Adjustments**
5. **Risk Level Assessment (High/Medium/Low) with Justification**

Please respond in English with clear formatting."""


def build_prompt(factory_data, lang="zh"):
    """Build the AI analysis prompt from factory data.

    Args:
        factory_data: dict with keys: factory_name, region, quality_rating,
                      inspection_count, pass_rate, top_defects, trigger_reasons,
                      defect_detail_table.
        lang: 'zh' or 'en'.

    Returns:
        Formatted prompt string.
    """
    template = REPORT_PROMPT_ZH if lang == "zh" else REPORT_PROMPT_EN
    return template.format(**factory_data)


def call_claude_api(prompt):
    """Call Claude API to generate analysis report.

    Args:
        prompt: The formatted prompt string.

    Returns:
        tuple: (response_text, success_bool)
    """
    api_key = CLAUDE_API_KEY
    if not api_key:
        return "API key not configured. Using rule-based analysis.", False

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text, True

    except ImportError:
        return "Anthropic package not installed. Using rule-based analysis.", False
    except anthropic.RateLimitError:
        return "API rate limit reached. Using rule-based analysis.", False
    except anthropic.APIError as e:
        return f"API error: {str(e)}. Using rule-based analysis.", False
    except Exception as e:
        return f"Unexpected error: {str(e)}. Using rule-based analysis.", False


def parse_response(response_text):
    """Parse the AI response into structured sections.

    Args:
        response_text: Raw response from Claude API.

    Returns:
        dict with sections: root_cause, corrective_actions, preventive_actions,
        inspection_strategy, risk_assessment.
    """
    sections = {
        "root_cause": "",
        "corrective_actions": "",
        "preventive_actions": "",
        "inspection_strategy": "",
        "risk_assessment": "",
    }

    # Section markers (both zh and en)
    markers = [
        (["根因分析", "Root Cause"], "root_cause"),
        (["短期纠正措施", "Corrective Action", "纠正措施"], "corrective_actions"),
        (["长期预防措施", "Preventive Action", "预防措施"], "preventive_actions"),
        (["验货策略", "Inspection Strategy", "检验策略"], "inspection_strategy"),
        (["风险等级", "Risk Level", "风险评估"], "risk_assessment"),
    ]

    lines = response_text.split("\n")
    current_section = None

    for line in lines:
        # Check if this line starts a new section
        matched = False
        for keywords, section_key in markers:
            if any(kw in line for kw in keywords):
                current_section = section_key
                matched = True
                break

        if current_section and not matched:
            sections[current_section] += line + "\n"

    # If parsing failed, put everything in root_cause
    if all(v.strip() == "" for v in sections.values()):
        sections["root_cause"] = response_text

    return sections


def generate_rule_based_report(factory_data, lang="zh"):
    """Generate a rule-based fallback report when AI is unavailable.

    Args:
        factory_data: dict with factory analysis data.
        lang: 'zh' or 'en'.

    Returns:
        Formatted report string.
    """
    if lang == "zh":
        report = f"""## 质量改进建议报告 — {factory_data['factory_name']}

### 1. 问题根因分析
- 工厂历史质量评分为 {factory_data['quality_rating']}，{'低于行业平均水平' if factory_data['quality_rating'] < 85 else '处于正常范围'}
- 近期通过率 {factory_data['pass_rate']}%，{'明显偏低，需要重点关注' if factory_data['pass_rate'] < 80 else '需要持续监控'}
- 主要缺陷类型: {factory_data['top_defects']}
- 告警触发原因: {factory_data['trigger_reasons']}

### 2. 短期纠正措施（1-2周内）
- 针对 {factory_data['top_defects']} 进行专项检查和返工
- 加强来料检验和过程检验频次
- 召开质量问题分析会议，明确责任人和整改期限
- 对不合格批次进行100%全检或返工处理

### 3. 长期预防措施（1-3个月）
- 完善质量管理体系，建立缺陷预防机制
- 加强操作员技能培训，特别是针对高频缺陷类型
- 优化生产工艺参数，减少工艺波动
- 建立供应商质量改进计划（SCAR）跟踪机制

### 4. 建议调整的验货策略
"""
        if factory_data['pass_rate'] < 80:
            report += "- **建议切换至加严检验（Tightened Inspection）**\n"
            report += "- 增加验货频次，从抽检改为每批必检\n"
            report += "- 增加关键工序的过程检验点\n"
        elif factory_data['pass_rate'] < 90:
            report += "- 维持正常检验级别，但增加抽样数量\n"
            report += "- 对高风险产品线增加检验频次\n"
        else:
            report += "- 维持当前检验级别\n"
            report += "- 可考虑对稳定产品线适当放宽检验\n"

        report += f"""
### 5. 风险等级评估
"""
        if factory_data['pass_rate'] < 75:
            report += "- **风险等级: 高**\n"
            report += "- 理由: 通过率严重偏低，存在批量质量问题风险，可能影响交期和客户满意度\n"
        elif factory_data['pass_rate'] < 90:
            report += "- **风险等级: 中**\n"
            report += "- 理由: 通过率低于目标值，需要密切关注并采取改进措施\n"
        else:
            report += "- **风险等级: 低**\n"
            report += "- 理由: 质量表现稳定，但仍需持续监控\n"

    else:
        # English version
        report = f"""## Quality Improvement Report — {factory_data['factory_name']}

### 1. Root Cause Analysis
- Factory quality rating: {factory_data['quality_rating']} ({'below industry average' if factory_data['quality_rating'] < 85 else 'within normal range'})
- Recent pass rate: {factory_data['pass_rate']}% ({'significantly low, requires immediate attention' if factory_data['pass_rate'] < 80 else 'needs continuous monitoring'})
- Top defect types: {factory_data['top_defects']}
- Alert triggers: {factory_data['trigger_reasons']}

### 2. Short-term Corrective Actions (1-2 weeks)
- Conduct targeted inspection and rework for {factory_data['top_defects']}
- Increase incoming and in-process inspection frequency
- Hold quality issue review meetings with clear ownership and deadlines
- Perform 100% inspection or rework on rejected batches

### 3. Long-term Preventive Actions (1-3 months)
- Strengthen QMS and establish defect prevention mechanisms
- Enhance operator training, especially for high-frequency defect types
- Optimize production process parameters to reduce variation
- Establish SCAR (Supplier Corrective Action Request) tracking

### 4. Recommended Inspection Strategy
"""
        if factory_data['pass_rate'] < 80:
            report += "- **Switch to Tightened Inspection**\n"
            report += "- Increase inspection frequency: every batch required\n"
            report += "- Add in-process inspection checkpoints\n"
        elif factory_data['pass_rate'] < 90:
            report += "- Maintain Normal inspection level with increased sample size\n"
            report += "- Increase frequency for high-risk product lines\n"
        else:
            report += "- Maintain current inspection level\n"
            report += "- Consider reduced inspection for stable product lines\n"

        report += f"""
### 5. Risk Level Assessment
"""
        if factory_data['pass_rate'] < 75:
            report += "- **Risk Level: HIGH**\n"
            report += "- Justification: Pass rate critically low, batch quality risk affecting delivery and customer satisfaction\n"
        elif factory_data['pass_rate'] < 90:
            report += "- **Risk Level: MEDIUM**\n"
            report += "- Justification: Pass rate below target, close monitoring and improvement actions required\n"
        else:
            report += "- **Risk Level: LOW**\n"
            report += "- Justification: Quality performance stable, continue monitoring\n"

    return report
