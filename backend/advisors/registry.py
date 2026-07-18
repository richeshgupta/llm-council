"""Advisor registry and adapter factory."""

from __future__ import annotations

from .base import Advisor, AdvisorRole
from .config import AdvisorConfig, AdvisorsConfig, load_advisors_config
from .adapters.claude_cli import ClaudeCliAdvisor
from .adapters.codex_cli import CodexCliAdvisor
from .adapters.openrouter import OpenRouterAdvisor


class AdvisorRegistry:
    """Creates and resolves enabled advisors."""

    def __init__(self, config: AdvisorsConfig | None = None):
        self.config = config or load_advisors_config()
        self._advisors = [self._create_advisor(c) for c in self.config.advisors if c.enabled]
        self._by_id = {advisor.id: advisor for advisor in self._advisors}

    def _create_advisor(self, config: AdvisorConfig) -> Advisor:
        if config.provider == "openrouter":
            return OpenRouterAdvisor(config)
        if config.provider == "claude_cli":
            return ClaudeCliAdvisor(config)
        if config.provider == "codex_cli":
            return CodexCliAdvisor(config)
        raise ValueError(f"Unsupported advisor provider: {config.provider}")

    def get_enabled_advisors(self) -> list[Advisor]:
        return list(self._advisors)

    def get_council_advisors(self) -> list[Advisor]:
        return [a for a in self._advisors if AdvisorRole.COUNCIL_MEMBER in a.roles]

    def get_chairman_advisor(self) -> Advisor:
        chairman_id = self.config.chairman.advisor_id
        if chairman_id and chairman_id in self._by_id:
            return self._by_id[chairman_id]

        for advisor in self._advisors:
            if AdvisorRole.CHAIRMAN in advisor.roles:
                return advisor

        council_advisors = self.get_council_advisors()
        if not council_advisors:
            raise ValueError("No enabled chairman or council advisor configured")
        return council_advisors[0]

    def get_title_generator_advisor(self) -> Advisor:
        title_id = self.config.title_generator.advisor_id
        if title_id and title_id in self._by_id:
            return self._by_id[title_id]

        for advisor in self._advisors:
            if AdvisorRole.TITLE_GENERATOR in advisor.roles:
                return advisor

        return self.get_chairman_advisor()

