"""
选题评分卡生成器 / Topic Scoring Card Generator

为科研价值驱动研究编排团提供选题评分、分档、止损线、复评决策的全自动化输出。
"""

# 八维评分维度
DIMENSIONS = [
    "originality",       # 原创性：研究问题是否首创/突破
    "feasibility",       # 可行性：方法是否成熟可行
    "value_density",     # 价值密度：研究产出价值与投入的比值
    "data_availability", # 数据可得性：关键数据是否可得
    "competition",       # 竞争烈度：同领域研究密度（分数越高竞争越低）
    "cognition",         # 认知层级：前沿/进阶/基础的层级
    "resource_fit",      # 资源匹配：当前资源是否匹配
    "sustainability",    # 可持续性：长期延伸与拓展潜力
]

DIMENSION_LABELS_ZH = {
    "originality": "原创性",
    "feasibility": "可行性",
    "value_density": "价值密度",
    "data_availability": "数据可得性",
    "competition": "竞争烈度（高分=低竞争）",
    "cognition": "认知层级",
    "resource_fit": "资源匹配",
    "sustainability": "可持续性",
}


def grade_bucket(scores: dict) -> tuple:
    """
    根据 8 维评分分档。
    返回: (档位, 入选理由, 资源建议)
    """
    min_score = min(scores.values())
    max_score = max(scores.values())
    avg_score = sum(scores.values()) / len(scores)
    high_count = sum(1 for v in scores.values() if v >= 8)

    if min_score >= 7 and max_score >= 9:
        return (
            "S",
            f"8维均≥7分，至少1维≥9分（min={min_score}, max={max_score}, avg={avg_score:.1f}）",
            "重投入，多团队并行；建议配置 S 级资源包（数据/算力/人月）",
        )
    if min_score >= 6 and high_count >= 2:
        return (
            "A",
            f"8维均≥6分，至少2维≥8分（min={min_score}, max={max_score}, avg={avg_score:.1f}）",
            "标准投入；建议 A 级资源包，注意关键风险监控",
        )
    if min_score >= 5 and max_score >= 8:
        return (
            "B",
            f"8维均≥5分，至少1维≥8分（min={min_score}, max={max_score}, avg={avg_score:.1f}）",
            "保守投入，留退出通道；建议 B 级资源包 + 月度复评",
        )
    return (
        "C",
        f"任一维<5分，或证据等级<3（min={min_score}, max={max_score}, avg={avg_score:.1f}）",
        "不投入/止损；建议重新选题或转向相邻问题",
    )


def stop_loss_matrix(scores: dict) -> dict:
    """
    输出 3 条止损线：数据 / 时间 / 资源
    """
    data_score = scores.get("data_availability", 5)
    feasibility_score = scores.get("feasibility", 5)
    resource_score = scores.get("resource_fit", 5)

    return {
        "数据止损线": (
            f"若关键数据获取率 < {data_score * 10}%，触发降档或转向相邻选题"
        ),
        "时间止损线": (
            f"若核心方法可行性验证超过 {feasibility_score * 2} 周未达标，触发复评"
        ),
        "资源止损线": (
            f"若资源消耗超过预算 {resource_score * 15}%，立即暂停并复评"
        ),
    }


def review_decision(scores_old: dict, scores_new: dict, risks: list = None) -> tuple:
    """
    复评闭环决策：维持 / 升档 / 降档 / 止损
    返回: (决策, 决策依据, 后续行动建议)
    """
    risks = risks or []
    high_risks = sum(1 for r in risks if r in ["high", "高"])
    critical_risks = sum(1 for r in risks if r in ["critical", "极高"])

    # 检查关键评分变化
    deltas = {k: scores_new.get(k, 0) - scores_old.get(k, 0) for k in DIMENSIONS}
    avg_delta = sum(deltas.values()) / len(deltas)

    # 检查最低分
    min_new = min(scores_new.values())
    min_old = min(scores_old.values())

    # 决策逻辑
    if min_new <= 3 or critical_risks >= 1 or high_risks >= 2:
        return (
            "止损",
            f"min={min_new} 或 ≥1项极高风险 / ≥2项高风险不可控",
            "立即暂停当前方向；召开复盘会议；考虑转向相邻选题或放弃",
        )
    if any(d < -1 for d in deltas.values()) or high_risks >= 1:
        return (
            "降档",
            f"关键评分退步（min={min_old}→{min_new}）或新增 ≥1 项高风险",
            "收缩研究范围；降低预期产出；增加月度复评频率",
        )
    if avg_delta >= 1 and sum(1 for d in deltas.values() if d >= 1) >= 3:
        return (
            "升档",
            f"前 3 项评分进步（avg_delta={avg_delta:.1f}），≥3 维提升",
            "增加资源投入；扩大研究规模；考虑多团队并行",
        )
    return (
        "维持",
        f"当前路径稳定（min={min_new}, avg_delta={avg_delta:.1f}）",
        "继续当前路径；保持当前资源投入；季度复评",
    )


def score_topic(topic_name: str, scores: dict, risks: list = None) -> dict:
    """
    主入口：对一个选题做完整评分。
    返回: {
        "topic": 选题名,
        "scores": 评分,
        "scores_labeled": 中文标注评分,
        "bucket": (档位, 入选理由, 资源建议),
        "stop_loss": 止损线矩阵,
        "min_score": 最低分,
        "avg_score": 平均分,
        "max_score": 最高分,
    }
    """
    # 校验
    missing = [d for d in DIMENSIONS if d not in scores]
    if missing:
        raise ValueError(f"缺少评分维度: {missing}")

    bucket = grade_bucket(scores)
    stop_loss = stop_loss_matrix(scores)
    scores_labeled = {DIMENSION_LABELS_ZH[k]: v for k, v in scores.items()}

    return {
        "topic": topic_name,
        "scores": scores,
        "scores_labeled": scores_labeled,
        "bucket": bucket,
        "stop_loss": stop_loss,
        "min_score": min(scores.values()),
        "avg_score": round(sum(scores.values()) / len(scores), 2),
        "max_score": max(scores.values()),
        "risks": risks or [],
    }


def format_report(result: dict) -> str:
    """
    格式化输出 Markdown 报告。
    """
    bucket, reason, resource = result["bucket"]

    lines = []
    lines.append(f"# 选题评分卡：{result['topic']}\n")
    lines.append(f"**分档**：{bucket}  档")
    lines.append(f"**最低分 / 平均分 / 最高分**：{result['min_score']} / {result['avg_score']} / {result['max_score']}\n")

    lines.append("## 8 维评分\n")
    lines.append("| 维度 | 评分 |")
    lines.append("|------|------|")
    for k, v in result["scores_labeled"].items():
        lines.append(f"| {k} | {v} |")
    lines.append("")

    lines.append("## 分档依据与资源建议\n")
    lines.append(f"- **入选理由**：{reason}")
    lines.append(f"- **资源建议**：{resource}\n")

    lines.append("## 止损线矩阵\n")
    lines.append("| 止损类型 | 触发条件 |")
    lines.append("|---------|---------|")
    for k, v in result["stop_loss"].items():
        lines.append(f"| {k} | {v} |")

    if result.get("risks"):
        lines.append("\n## 关键风险\n")
        for i, r in enumerate(result["risks"], 1):
            lines.append(f"{i}. {r}")

    return "\n".join(lines)


if __name__ == "__main__":
    # CLI 示例
    import argparse

    parser = argparse.ArgumentParser(description="选题评分卡生成器")
    parser.add_argument("--topic", required=True, help="选题名称")
    for d in DIMENSIONS:
        parser.add_argument(f"--{d.replace('_', '-')}", type=int, required=True, help=DIMENSION_LABELS_ZH[d])

    args = parser.parse_args()
    scores = {d: getattr(args, d.replace("-", "_")) for d in DIMENSIONS}
    result = score_topic(args.topic, scores)
    print(format_report(result))
