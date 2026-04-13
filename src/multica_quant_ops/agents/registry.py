from dataclasses import dataclass, field

from multica_quant_ops.models import AgentProfile


@dataclass
class AgentRegistry:
    _agents: dict[str, AgentProfile] = field(default_factory=dict)

    def register(self, agent: AgentProfile) -> None:
        if agent.name in self._agents:
            raise ValueError(f"Agent already registered: {agent.name}")
        self._agents[agent.name] = agent

    def get(self, name: str) -> AgentProfile:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise ValueError(f"Unknown agent: {name}") from exc

    def list_agents(self) -> list[AgentProfile]:
        return sorted(self._agents.values(), key=lambda agent: agent.name)
