from pyvis.network import Network
from itertools import product

class Node:
    def __init__(self, name, is_assumption=False):
        self.name = name
        self.label = set()  # Environnements valides
        self.justifications = []
        self.is_assumption = is_assumption
        if is_assumption:
            self.label.add(frozenset({name}))

    def add_env(self, env):
        is_absent = env not in self.label
        if is_absent:
            self.label.add(env)
        return is_absent

    def __repr__(self):
        return self.name

class Justification:
    def __init__(self, in_nodes, out_nodes, conclusion):
        self.in_nodes = in_nodes
        self.out_nodes = out_nodes
        self.conclusion = conclusion

class ATMS:
    def __init__(self):
        self.nodes = {}
        self.contradiction_node = self.add_node("⊥")

    def add_node(self, name, is_assumption=False):
        if name not in self.nodes:
            self.nodes[name] = Node(name, is_assumption)
        return self.nodes[name]

    def add_assumption(self, name):
        return self.add_node(name, is_assumption=True)

    def add_justification(self, in_names, out_names, conclusion_name):
        in_nodes = [self.nodes[name] for name in in_names]
        out_nodes = [self.nodes[name] for name in out_names]
        conclusion = self.nodes[conclusion_name]

        justification = Justification(in_nodes, out_nodes, conclusion)
        conclusion.justifications.append(justification)
        
        in_env_lists = [node.label for node in justification.in_nodes]
        out_nodes = justification.out_nodes

        for combination in product(*in_env_lists):
            merged_env = frozenset().union(*combination)

            if any(any(env.issubset(merged_env) for env in out_node.label) for out_node in out_nodes):
                continue

            if self.is_consistent(merged_env):
                justification.conclusion.add_env(merged_env)
                if justification.conclusion.name == "⊥":
                    self.invalidate_environment(merged_env)

    def invalidate_environment(self, env):
        for node in self.nodes.values():
            node.label = {node_env for node_env in node.label if not env.issubset(node_env)}

    def get_environments(self, node_name):
        return self.nodes[node_name].label

    def is_consistent(self, env):
        return frozenset(env) not in self.nodes["⊥"].label

    def print_labels(self):
        for name, node in self.nodes.items():
            print(f"{name}: {sorted([sorted(e) for e in node.label])}")
