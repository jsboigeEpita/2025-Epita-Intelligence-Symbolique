import git
from typing import List
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from project_core.llm.models.commit_analysis import CommitAnalysis

class NativeGitAudit:
    """
    A native plugin for analyzing Git commits using qualitative analysis.
    """

    def __init__(self):
        """Initializes the NativeGitAudit plugin."""
        try:
            # Assumes the script runs within a Git repository
            self.repo = git.Repo('.', search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            self.repo = None

    @kernel_function(
        name="analyze_commit",
        description="Analyzes git commit data to extract qualitative insights and returns a CommitAnalysis object."
    )
    def analyze_commit(
        self,
        detailed_summary: str,
        technical_debt_signals: List[str],
        quality_leaps: List[str],
    ) -> CommitAnalysis:
        """
        This function is the data contract for the LLM.
        The SK framework uses this signature to guide the LLM's output
        and automatically constructs the CommitAnalysis object.
        The body of this function is NOT executed when the LLM is called via tool_choice.

        Args:
            detailed_summary (str): A detailed, factual summary of the commit's purpose and changes.
            technical_debt_signals (List[str]): A list of observations indicating potential new or increased technical debt.
            quality_leaps (List[str]): A list of observations indicating significant quality improvements.
        """
        # This return is a fallback and helps with type hinting, but is not used by the LLM tool call.
        return CommitAnalysis(
            detailed_summary=detailed_summary,
            technical_debt_signals=technical_debt_signals,
            quality_leaps=quality_leaps,
        )

    @kernel_function(
        name="get_commit_diff",
        description="Retrieves the full git diff for a given commit hash."
    )
    def get_commit_diff(self, commit_hash: str) -> str:
        """
        Retrieves the diff of a specific commit.

        Args:
            commit_hash (str): The SHA hash of the commit.

        Returns:
            str: The full diff of the commit, or an error message if not found.
        """
        if not self.repo:
            return "Erreur: Dépôt Git non initialisé."
        try:
            commit = self.repo.commit(commit_hash)
            # Diff against the first parent. This is standard for most commits.
            if not commit.parents:
                return f"Le commit {commit_hash} est un commit initial et n'a pas de parent pour le diff."
            
            diff_content = self.repo.git.diff(commit.parents[0].hexsha, commit.hexsha)
            return diff_content
        except Exception as e:
            return f"Erreur lors de la récupération du diff pour le commit {commit_hash}: {str(e)}"