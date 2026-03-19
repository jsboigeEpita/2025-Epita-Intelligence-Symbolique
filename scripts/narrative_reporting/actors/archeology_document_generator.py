import os
import json
import glob

def generate_archeology_document():
    """
    Generates a software archeology Markdown document from enriched commit data.
    """
    commits_audit_dir = 'docs/commits_audit/'
    output_file = 'docs/audit/rhetoric_system_evolution.md'
    
    json_files = sorted(glob.glob(os.path.join(commits_audit_dir, '*.json')))
    
    markdown_content = "# Évolution du Système de Rhétorique : Une Archéologie Logicielle\n\n"
    
    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            sha = data.get('sha', 'N/A')
            date = data.get('date', 'N/A').split('T')[0]
            author = data.get('author', 'N/A')
            message = data.get('message', 'N/A')
            llm_summary = data.get('llm_summary', 'Non disponible.')
            
            markdown_content += f"### `{sha}` - `{date}`\n\n"
            markdown_content += f"**Auteur :** {author}\n"
            markdown_content += f"**Commit :** {message}\n\n"
            markdown_content += f"**Résumé IA :**\n> {llm_summary}\n\n"
            markdown_content += "---\n\n"
            
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
        
    print(f"Document d'archéologie généré avec succès : {output_file}")

if __name__ == "__main__":
    generate_archeology_document()