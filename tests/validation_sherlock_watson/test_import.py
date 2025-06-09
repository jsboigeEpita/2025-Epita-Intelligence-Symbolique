#!/usr/bin/env python3

# ===== ONE-LINER AUTO-ACTIVATEUR D'ENVIRONNEMENT =====
# Assure l'activation automatique de l'environnement projet
import scripts.core.auto_env  # Auto-activation environnement intelligent

try:
    from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatCompletionAgent
    print("Import works - ChatCompletionAgent found")
except ImportError as e:
    print(f"Import failed: {e}")
    
    # Test avec une version alternative
    try:
        from semantic_kernel.agents import ChatCompletionAgent
        print("Alternative import works - ChatCompletionAgent found in agents module")
    except ImportError as e2:
        print(f"Alternative import failed: {e2}")
        
        # Test pour voir ce qui est disponible dans semantic_kernel
        try:
            import semantic_kernel
            print("Available in semantic_kernel:", dir(semantic_kernel))
            
            # Essaie de voir si agents existe
            if hasattr(semantic_kernel, 'agents'):
                print("Agents module exists:", dir(semantic_kernel.agents))
            else:
                print("No agents module found")
                
            # Regarde dans les autres agents existants
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            sherlock_path = os.path.join(script_dir, "argumentation_analysis", "agents", "core", "pm", "sherlock_enquete_agent.py")
            if os.path.exists(sherlock_path):
                with open(sherlock_path, 'r') as f:
                    content = f.read()
                    if "ChatCompletionAgent" in content:
                        print("ChatCompletionAgent is used in sherlock_enquete_agent.py")
                        # Extraire l'import line
                        for line in content.split('\n'):
                            if 'ChatCompletionAgent' in line and 'import' in line:
                                print(f"Import line found: {line.strip()}")
                    
        except Exception as e3:
            print(f"Failed to analyze semantic_kernel: {e3}")