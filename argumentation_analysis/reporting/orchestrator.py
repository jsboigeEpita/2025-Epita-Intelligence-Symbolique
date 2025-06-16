from datetime import datetime
from . import data_collector
from . import document_assembler
from .models import ReportMetadata # Import ReportMetadata

class ReportOrchestrator:
    """
    Orchestrates the generation of reports by coordinating data collection
    and document assembly.
    """
    def __init__(self, config):
        """
        Initializes the ReportOrchestrator with necessary services.

        Args:
            config: Configuration object for the services.
                    It's assumed this config might also contain sub-configs
                    for collector and assembler, or they derive from it.
                    Example: config = {"report_format": "html", "source_component": "MySystem", ...}
        """
        self.config = config
        # Assuming DataCollector exists in data_collector.py
        # Pass the relevant part of the config or the whole config
        self.collector = data_collector.DataCollector(config.get("data_collector_config", config))
        
        # Using UnifiedReportTemplate from document_assembler.py
        # Pass the relevant part of the config or the whole config.
        # The assembler's config should specify the desired format, e.g., {"format": "html"}
        assembler_config = config.get("document_assembler_config", {})
        if "format" not in assembler_config: # Default to html if not specified for the orchestrator's purpose
            assembler_config["format"] = config.get("default_report_format", "html")
        self.assembler = document_assembler.UnifiedReportTemplate(assembler_config)

    def generate_report(self, analysis_type: str = "generic_analysis"):
        """
        Generates a complete report.

        Args:
            analysis_type (str): The type of analysis being reported.

        Returns:
            The final generated report (e.g., HTML string, depending on assembler config).
        """
        # 1. Collect data
        # Assuming gather_all_data method exists in DataCollector
        report_data = self.collector.gather_all_data()

        # 2. Create ReportMetadata instance
        # The source_component could come from the orchestrator's config
        source_component = self.config.get("source_component", "ReportOrchestrator")
        report_metadata = ReportMetadata(
            source_component=source_component,
            analysis_type=analysis_type,
            generated_at=datetime.now(),
            # format_type and template_name in ReportMetadata are for informational purposes
            # The actual rendering format is controlled by UnifiedReportTemplate's instance config
            format_type=self.assembler.format_type,
            template_name=self.assembler.name
        )

        # 3. Assemble the final report document
        # The render method in UnifiedReportTemplate handles different formats
        # based on its own 'format_type' attribute.
        final_report = self.assembler.render(data=report_data, metadata=report_metadata)

        # 4. Return the result
        return final_report