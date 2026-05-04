# Archived: 2026-03-24 - Superseded by core/pm/pm_agent.py + factory.create_project_manager_agent()
# Issue: #216 (consolidate agents legacy)
# Features merged: ProjectManagementPlugin setup, prompt loading, invoke_single
#
# Modern equivalents:
#   - argumentation_analysis/agents/core/pm/pm_agent.py (ProjectManagerAgent)
#   - argumentation_analysis/agents/factory.py::create_project_manager_agent()
# Reason: Not wired into factory.py, duplicate of core/pm/pm_agent.py

from typing import Dict, Any, Optional

from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments

from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent
from argumentation_analysis.agents.plugins.project_management_plugin import (
    ProjectManagementPlugin,
)
from argumentation_analysis.utils.path_operations import get_prompt_path


class ProjectManagerAgent(BaseAgent):
    """
    Agent spécialisé dans la gestion de projet, capable de créer des plans,
    d'assigner des tâches et de suivre l'état d'avancement.

    ARCHIVED: Use core/pm/pm_agent.py instead.
    """

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str = "Project_Manager",
        llm_service_id: str = None,
        plugins: list = None,
    ):
        prompt_path = get_prompt_path("ProjectManagerAgent")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        if plugins is None:
            plugins = [ProjectManagementPlugin()]

        super().__init__(
            kernel=kernel,
            agent_name=agent_name,
            system_prompt=prompt,
            description="Un agent chef de projet pour décomposer et organiser le travail.",
            llm_service_id=llm_service_id,
            plugins=plugins,
        )

    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {"plugins": ["ProjectMgmtPlugin"]}

    async def get_response(self, topic: str) -> Any:
        return await self.invoke_single(topic=topic)

    async def invoke_single(self, topic: str) -> Any:
        arguments = KernelArguments(input=topic, tool_choice="required")
        return await self.kernel.invoke_prompt(
            function_name="create_project_plan",
            plugin_name="ProjectMgmtPlugin",
            arguments=arguments,
        )
