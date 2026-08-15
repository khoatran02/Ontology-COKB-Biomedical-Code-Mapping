from collections.abc import Iterable

from traffic_sign_kg.cokb.facts import Fact, Term
from traffic_sign_kg.cokb.problems import (
    Goal,
    InferenceStep,
    Problem,
    ProblemResult,
    ProblemStatus,
)
from traffic_sign_kg.cokb.rules import Atom, KnowledgeRule, is_variable

Binding = dict[str, Term]


class CokbEngine:
    """Deterministic goal-guided forward-chaining engine for the traffic-sign profile."""

    def __init__(self, rules: Iterable[KnowledgeRule], max_steps: int = 10_000) -> None:
        self.rules = tuple(rules)
        if not self.rules:
            raise ValueError("at least one knowledge rule is required")
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        self.max_steps = max_steps

    def solve(self, problem: Problem) -> ProblemResult:
        facts_by_key = {fact.statement_key(): fact for fact in problem.facts}
        steps: list[InferenceStep] = []
        ordered_rules = self._rank_rules(problem.goals)

        while len(steps) < self.max_steps:
            goal_facts = self._matched_goal_facts(problem.goals, facts_by_key.values())
            negative_goal_facts = self._matched_negative_goal_facts(
                problem.goals, facts_by_key.values()
            )
            goal_conflicts = tuple(
                (positive, negative)
                for positive in goal_facts
                for negative in negative_goal_facts
                if positive.arguments == negative.arguments
                and negative.predicate == f"not:{positive.predicate}"
            )
            conflicts = self._find_conflicts(facts_by_key.values())
            if conflicts or goal_conflicts:
                return self._result(
                    problem,
                    ProblemStatus.INCONSISTENT,
                    facts_by_key.values(),
                    steps,
                    goal_facts,
                    (*conflicts, *goal_conflicts),
                )
            if len(goal_facts) == len(problem.goals):
                return self._result(
                    problem,
                    ProblemStatus.PROVED,
                    facts_by_key.values(),
                    steps,
                    goal_facts,
                    (),
                )
            if len(negative_goal_facts) == len(problem.goals):
                return self._result(
                    problem,
                    ProblemStatus.DISPROVED,
                    facts_by_key.values(),
                    steps,
                    negative_goal_facts,
                    (),
                )

            changed = False
            snapshot = tuple(facts_by_key.values())
            for rule in ordered_rules:
                for binding, premises in self._match_rule(rule, snapshot):
                    conclusion = self._instantiate(rule.conclusion, binding, rule.rule_id)
                    key = conclusion.statement_key()
                    if key in facts_by_key:
                        continue
                    facts_by_key[key] = conclusion
                    steps.append(
                        InferenceStep(
                            sequence=len(steps) + 1,
                            rule_id=rule.rule_id,
                            premises=premises,
                            conclusion=conclusion,
                        )
                    )
                    changed = True
                    if len(steps) >= self.max_steps:
                        break
                if len(steps) >= self.max_steps:
                    break
            if not changed:
                break

        goal_facts = self._matched_goal_facts(problem.goals, facts_by_key.values())
        conflicts = self._find_conflicts(facts_by_key.values())
        status = ProblemStatus.INCONSISTENT if conflicts else ProblemStatus.UNKNOWN
        return self._result(
            problem,
            status,
            facts_by_key.values(),
            steps,
            goal_facts,
            conflicts,
        )

    def _rank_rules(self, goals: tuple[Goal, ...]) -> tuple[KnowledgeRule, ...]:
        goal_predicates = {goal.predicate for goal in goals}
        goal_constants = {
            argument
            for goal in goals
            for argument in goal.arguments
            if not is_variable(argument)
        }

        def score(rule: KnowledgeRule) -> tuple[int, int, str]:
            predicate_score = 1 if rule.conclusion.predicate in goal_predicates else 0
            constant_score = sum(
                1 for value in rule.conclusion.arguments if value in goal_constants
            )
            return (-predicate_score, -constant_score - rule.priority, rule.rule_id)

        return tuple(sorted(self.rules, key=score))

    def _match_rule(
        self,
        rule: KnowledgeRule,
        facts: tuple[Fact, ...],
    ) -> Iterable[tuple[Binding, tuple[Fact, ...]]]:
        def search(
            index: int,
            binding: Binding,
            premises: tuple[Fact, ...],
        ) -> Iterable[tuple[Binding, tuple[Fact, ...]]]:
            if index == len(rule.premises):
                yield binding, premises
                return
            atom = rule.premises[index]
            for fact in facts:
                matched = self._unify(atom, fact, binding)
                if matched is not None:
                    yield from search(index + 1, matched, (*premises, fact))

        yield from search(0, {}, ())

    @staticmethod
    def _unify(atom: Atom, fact: Fact, binding: Binding) -> Binding | None:
        if atom.predicate != fact.predicate or len(atom.arguments) != len(fact.arguments):
            return None
        result = dict(binding)
        for expected, actual in zip(atom.arguments, fact.arguments, strict=True):
            if is_variable(expected):
                variable = str(expected)
                existing = result.get(variable)
                if existing is not None and existing != actual:
                    return None
                result[variable] = actual
            elif expected != actual:
                return None
        return result

    @staticmethod
    def _instantiate(atom: Atom, binding: Binding, rule_id: str) -> Fact:
        arguments = tuple(
            binding[str(value)] if is_variable(value) else value for value in atom.arguments
        )
        return Fact(
            predicate=atom.predicate,
            arguments=arguments,
            kind=atom.kind,
            asserted=False,
            source=rule_id,
        )

    @staticmethod
    def _matched_goal_facts(goals: tuple[Goal, ...], facts: Iterable[Fact]) -> tuple[Fact, ...]:
        by_key = {fact.statement_key(): fact for fact in facts}
        return tuple(
            fact
            for goal in goals
            if (fact := by_key.get((goal.predicate, goal.arguments))) is not None
        )

    @staticmethod
    def _matched_negative_goal_facts(
        goals: tuple[Goal, ...], facts: Iterable[Fact]
    ) -> tuple[Fact, ...]:
        by_key = {fact.statement_key(): fact for fact in facts}
        return tuple(
            fact
            for goal in goals
            if (fact := by_key.get((f"not:{goal.predicate}", goal.arguments))) is not None
        )

    @staticmethod
    def _find_conflicts(facts: Iterable[Fact]) -> tuple[tuple[Fact, ...], ...]:
        grouped: dict[tuple[Term, ...], dict[Term, Fact]] = {}
        for fact in facts:
            if fact.predicate != "maneuverStatus" or len(fact.arguments) != 4:
                continue
            context = fact.arguments[:3]
            grouped.setdefault(context, {})[fact.arguments[3]] = fact
        conflicts: list[tuple[Fact, ...]] = []
        for values in grouped.values():
            prohibited = values.get("PROHIBITED")
            required = values.get("REQUIRED")
            if prohibited is not None and required is not None:
                conflicts.append((prohibited, required))
        return tuple(conflicts)

    @staticmethod
    def _result(
        problem: Problem,
        status: ProblemStatus,
        facts: Iterable[Fact],
        steps: list[InferenceStep],
        goal_facts: tuple[Fact, ...],
        conflicts: tuple[tuple[Fact, ...], ...],
    ) -> ProblemResult:
        ordered_facts = tuple(sorted(facts, key=lambda fact: fact.fact_id))
        return ProblemResult(
            problem_id=problem.problem_id,
            status=status,
            goals=problem.goals,
            facts=ordered_facts,
            steps=tuple(steps),
            goal_facts=goal_facts,
            conflicts=conflicts,
            metadata={"fact_count": len(ordered_facts), "step_count": len(steps)},
        )
