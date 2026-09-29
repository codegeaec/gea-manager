from gea.agents import log, stats


def _b(agent, tier, result="done", ok=True, s=60):
    log.append(
        {"kind": "build", "agent_id": agent, "tier": tier, "result": result, "verify_ok": ok,
         "duration_s": s}
    )


def test_summarize_groups_by_agent_and_tier_and_ignores_reviews():
    _b("a", "L")
    _b("a", "L", ok=False, s=120)
    _b("a", "L", result="timeout", ok=None, s=180)
    _b("b", "S")
    log.append({"kind": "review", "agent_id": "a", "tier": "L", "result": "done"})
    rows = {(r["agent"], r["tier"]): r for r in stats.summarize(log.read())}
    a = rows[("a", "L")]
    assert a["attempts"] == 3 and round(a["success"], 2) == 0.33
    assert a["avg_s"] == 120 and a["timeouts"] == 1
    assert rows[("b", "S")]["success"] == 1.0


def test_run_stats_prints_a_table_or_a_hint(capsys):
    stats.run_stats()
    assert "no delegations" in capsys.readouterr().out
    _b("a", "M")
    stats.run_stats()
    assert "100%" in capsys.readouterr().out
