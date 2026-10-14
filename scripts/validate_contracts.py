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
    "数字核验关卡（V1 引用）": r"verify_numbers|verify_member_output|数字核验|未溯源",
    "知识态注入（hypotheses/knowledge_index）": r"confirmed_hypotheses|knowledge_index|RESEARCH_OPS_DIR|知识态",
}

# B（2026-10-21）：skills 层契约（SKILL.md 唯一入口须索引团队工具+核心铁律）
SKILL_CONTRACTS = {
    "团队工具索引（scripts/ 全清单）": r"assemble_spawn_prompt|verify_member_output|check_scope|write_checklist|find_knowledge|validate_contracts",
    "数字必溯源铁律": r"数字必溯源|未溯源|待人工核验",
    "禁项目叙事铁律（P2）": r"禁项目叙事|GOVERNANCE_BOUNDARIES|check_scope",
    "契约源回指（主理人 MD）": r"team-lead|主理人",
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


def check_skill(skill_md: Path) -> list[dict]:
    """B（2026-10-21）：skills 层契约孤岛检查。
    SKILL.md 是成员任务型入口，须索引团队工具 + 两条铁律（数字溯源/禁项目叙事）。
    references/*.md 按需加载，不强检（避免过度扩散）。
    """
    try:
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return [{"contract": "FILE_READ_ERROR", "missing_pattern": ""}]
    miss = []
    for name, pat in SKILL_CONTRACTS.items():
        if not re.search(pat, text, re.M | re.I):
            miss.append({"contract": name, "missing_pattern": pat})
    return miss


def main() -> int:
    base = Path(__file__).resolve().parent.parent
    total_missing = 0

    # ① agents 层（9 员）
    for ag in sorted((base / "agents").glob("*.md")):
        miss = check_agent(ag)
        if miss:
            total_missing += len(miss)
            print(f"❌ agents/{ag.name}: 缺 {len(miss)} 项契约条款")
            for m in miss[:2]:
                print(f"   - {m['contract']}（需匹配: /{m['missing_pattern'][:40]}/）")
        else:
            print(f"✅ agents/{ag.name}")

    # ② skills 层（viral-evo-core/SKILL.md 唯一入口）
    skill_md = base / "skills/viral-evo-core/SKILL.md"
    if skill_md.is_file():
        miss = check_skill(skill_md)
        if miss:
            total_missing += len(miss)
            print(f"❌ skills/SKILL.md: 缺 {len(miss)} 项契约条款")
            for m in miss[:2]:
                print(f"   - {m['contract']}（需匹配: /{m['missing_pattern'][:40]}/）")
        else:
            print(f"✅ skills/SKILL.md（工具索引+铁律完整）")

    if total_missing:
        print(f"\n总计 {total_missing} 处契约缺失——影响层间一致性，建议补齐")
        return 5
    print("\n✅ 全员契约完整（agents 9 + skills 1）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
