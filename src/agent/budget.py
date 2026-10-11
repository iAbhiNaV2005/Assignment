from dataclasses import dataclass, field


class BudgetExceededError(RuntimeError):
    pass


@dataclass
class BudgetTracker:
    yutori_tasks_max: int = 2
    yutori_tasks_used: int = 0
    yutori_cost_usd: float = 0.0

    hunter_credits_max: int = 6
    hunter_credits_used: float = 0.0

    sends_max: int = 1
    sends_used: int = 0

    llm_calls: int = 0
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0

    def check_yutori_task(self) -> None:
        if self.yutori_tasks_used >= self.yutori_tasks_max:
            raise BudgetExceededError(
                f"Yutori task limit reached: {self.yutori_tasks_used}/{self.yutori_tasks_max}"
            )

    def record_yutori_task(self, cost_usd: float = 0.35) -> None:
        self.yutori_tasks_used += 1
        self.yutori_cost_usd += cost_usd

    def check_hunter_credits(self, credits: float = 1.0) -> None:
        if (self.hunter_credits_used + credits) > self.hunter_credits_max:
            raise BudgetExceededError(
                f"Hunter credits limit exceeded: {self.hunter_credits_used + credits} > {self.hunter_credits_max}"
            )

    def record_hunter_credit(self, credits: float) -> None:
        self.hunter_credits_used += credits

    def check_send(self) -> None:
        if self.sends_used >= self.sends_max:
            raise BudgetExceededError(
                f"Maximum send limit reached: {self.sends_used}/{self.sends_max}"
            )

    def record_send(self) -> None:
        self.sends_used += 1

    def record_llm(self, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        self.llm_calls += 1
        self.llm_prompt_tokens += prompt_tokens
        self.llm_completion_tokens += completion_tokens
