#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_contracts.py —— 团队契约文本检查（V2 · 2026-10-21）
执行：扫描 agents/*.md 是否含关键契约条款（输入信封/工具白名单/纪律审判等）
边界：仅做"关键词存在性"确定性检查；不判断语义
返回：EXIT=0 全过；EXIT=5 缺条款
"""
import re
import sys
from pathlib import Path

# 契约条款黑名单（仅团队契约——v1.2.3 体系；项目治理约束 R1-R9 不在此查）
# 设计：每条仅需命中 1 个关键词即过；主理人 MD 自身不需含"团队契约回指"段
CONTRACTS = {
    "回传信封（上行）": r"result_envelope|上行信封|6 必填字段|agent_id.*task_id.*phase.*status",
    "下行 task_payload": r"task_payload|下行|input.*output_contract",
    "工具白名单（只读/写分清）": r"白名单|工具权限|只读.*分析|ANALYZER.*EXECUTOR",
    "纪律审判（discipline-sentinel 痕迹）": r"纪律审判|discipline-sentinel|T0.*派 spawn|T1.*收 envelope",
    "数字核验关卡（V1 引用）": r"verify_numbers|数字核验|未溯源|权威源",
    "知识态注入（hypotheses/knowledge_index）": r"confirmed_hypotheses|knowledge_index|RESEARCH_OPS_DIR|知识态",
}


def check_agent(agent_path: Path) -> list[dict]:
    """返回该 agent 缺失的契约条款列表。"""
    try:
        text = agent_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return [{"contract": "FILE_READ_ERROR", "missing_pattern": ""}]
    miss = []
    for name, pat in CONTRACTS.items():
        if not re.search(pat, text, re.M | re.I):
            miss.append({"contract": name, "missing_pattern": pat})
    return miss


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    agents = sorted((base / "agents").glob("*.md"))
    total_missing = 0
    for ag in agents:
        miss = check_agent(ag)
        if miss:
            total_missing += len(miss)
            print(f"❌ {ag.name}: 缺 {len(miss)} 项契约条款")
            for m in miss[:2]:
                print(f"   - {m['contract']}（需匹配: /{m['missing_pattern'][:40]}/）")
        else:
            print(f"✅ {ag.name}")
    if total_missing:
        print(f"\n总计 {total_missing} 处契约缺失——影响层间一致性，建议补齐")
        return 5
    print("\n✅ 全员契约完整")
    return 0


if __name__ == "__main__":
    sys.exit(main())
