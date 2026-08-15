from traffic_sign_kg.cokb.facts import Fact
from traffic_sign_kg.cokb.problems import InferenceStep, ProblemResult


def relevant_steps(result: ProblemResult, conclusion: Fact) -> tuple[InferenceStep, ...]:
    by_conclusion = {step.conclusion.statement_key(): step for step in result.steps}
    selected: dict[int, InferenceStep] = {}

    def visit(fact: Fact) -> None:
        step = by_conclusion.get(fact.statement_key())
        if step is None or step.sequence in selected:
            return
        selected[step.sequence] = step
        for premise in step.premises:
            visit(premise)

    visit(conclusion)
    return tuple(selected[key] for key in sorted(selected))


def explanation_payload(result: ProblemResult) -> dict[str, object]:
    conclusions = result.goal_facts or tuple(
        fact for conflict in result.conflicts for fact in conflict
    )
    steps: dict[int, InferenceStep] = {}
    for conclusion in conclusions:
        for step in relevant_steps(result, conclusion):
            steps[step.sequence] = step
    return {
        "problem_id": result.problem_id,
        "status": result.status.value,
        "conclusions": [_fact_payload(fact) for fact in conclusions],
        "steps": [
            {
                "sequence": step.sequence,
                "rule_id": step.rule_id,
                "premises": [_fact_payload(fact) for fact in step.premises],
                "conclusion": _fact_payload(step.conclusion),
            }
            for step in (steps[key] for key in sorted(steps))
        ],
    }


def _fact_payload(fact: Fact) -> dict[str, object]:
    return {
        "fact_id": fact.fact_id,
        "kind": fact.kind.value,
        "predicate": fact.predicate,
        "arguments": [str(value) for value in fact.arguments],
        "asserted": fact.asserted,
        "source": fact.source,
    }
