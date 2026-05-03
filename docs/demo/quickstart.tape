Require golang 1.21
Require vhs>=0.7

Output quickstart.gif
Set FontSize 14
Set Padding 8
Set Width 900
Set Height 500

Type "conda activate projet-is-roo-new"
Enter
Sleep 500ms

Type "# Run spectacular analysis on a scenario"
Enter
Sleep 300ms

Type "python -m argumentation_analysis.run_orchestration \\"
Enter
Type "    --input examples/scenarios/politics.txt \\"
Enter
Type "    --workflow spectacular \\"
Enter
Type "    --rich-output"
Enter
Sleep 3s

Type ""
Enter
Sleep 300ms

Type "# Render interactive HTML report"
Enter
Sleep 300ms

Type "python -m argumentation_analysis.visualization.html_report \\"
Enter
Type "    .last_state.json report.html"
Enter
Sleep 1s

Type ""
Enter
Sleep 300ms

Type "# Build presentation slides"
Enter
Sleep 300ms

Type "python scripts/build_deck.py"
Enter
Sleep 500ms

Type ""
Enter
Sleep 300ms

Type "# Open the Jupyter notebook tour"
Enter
Sleep 300ms

Type "jupyter lab examples/notebooks/spectacular_full_tour.ipynb"
Enter
Sleep 2s
