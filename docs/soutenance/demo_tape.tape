Require vhs>=0.7

Output demo.gif
Set FontSize 15
Set Padding 10
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"

Type "conda activate projet-is"
Enter
Sleep 800ms

Type "# ═══ Demo EPITA — Analyse Argumentative Multi-Agents ═══"
Enter
Sleep 1s

Type ""
Enter
Sleep 300ms

Type "# 1. Lancer le pipeline spectacular sur un scenario politique"
Enter
Sleep 500ms

Type "python argumentation_analysis/run_orchestration.py \\"
Enter
Type "    --file examples/scenarios/politics.txt \\"
Enter
Type "    --workflow light"
Enter
Sleep 5s

Type ""
Enter
Sleep 500ms

Type "# 2. Resultats : arguments extraits, sophismes detectes, logique formelle"
Enter
Sleep 1s

Type "#    7 arguments | 4 sophismes | 3 formules FOL | 8 croyances JTMS"
Enter
Sleep 2s

Type ""
Enter
Sleep 500ms

Type "# 3. Lancer l'interface Gradio (demo live)"
Enter
Sleep 500ms

Type "python apps/gradio_demo/app.py"
Enter
Sleep 3s

Type "#    → http://localhost:7860"
Enter
Sleep 1s

Type ""
Enter
Sleep 500ms

Type "# 4. Rapport HTML interactif"
Enter
Sleep 300ms

Type "python -m argumentation_analysis.visualization.html_report \\"
Enter
Type "    --input .last_state.json --output report.html"
Enter
Sleep 2s

Type ""
Enter
Sleep 500ms

Type "# 5. Pattern mining — rapport corpus reel (18 documents)"
Enter
Sleep 300ms

Type "cat docs/reports/discourse_patterns.md | head -20"
Enter
Sleep 1s

Type ""
Enter
Sleep 500ms

Type "# ═══ Fin du demo ═══"
Enter
