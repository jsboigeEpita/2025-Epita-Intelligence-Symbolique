from pyvis.network import Network
import networkx as nx


class Belief:
    def __init__(self, name):
        self.name = name
        self.valid = None  # True would mean that the belief is True, False wold mean that it's undefined
        self.non_monotonic = False  # The belief is only present in a loop
        self.justifications = []
        self.implications = []

    def __str__(self):
        return f"{self.name} -> {'UNKNOWN' if self.valid == None else 'VALID' if self.valid else 'INVALID'}"

    def __repr__(self):
        return f"{self.name}"

    def add_justification(self, justification):
        self.justifications.append(justification)
        self.compute_truth_statement()

    def remove_justification(self, justification):
        self.justifications.pop(self.justifications.index(justification))
        self.compute_truth_statement()

    def add_implication(self, justification):
        self.implications.append(justification)

    def remove_implication(self, justification):
        self.implications.pop(self.implications.index(justification))

    def set_truth_value(self, value):
        self.valid = value
        self.propagate()

    def compute_truth_statement(self):
        if self.non_monotonic:
            self.valid = None
            return

        self.valid = None
        for justification in self.justifications:
            if all([belief.valid for belief in justification.in_list]) and not any(
                [belief.valid for belief in justification.out_list]
            ):
                self.valid = True
                break

        self.propagate()

    def propagate(self):
        for justification in self.implications:
            justification.conclusion.compute_truth_statement()


class Justification:
    def __init__(self, in_list, out_list, conclusion):
        self.in_list: list[Belief] = in_list  # List of belief
        self.out_list: list[Belief] = out_list  # List of belief
        self.conclusion: Belief = conclusion  # Belief object


class JTMS:
    def __init__(self, strict=False):
        self.beliefs = {}
        self.strict = strict

    def add_belief(self, name):
        if name not in self.beliefs:
            self.beliefs[name] = Belief(name)

    def remove_belief(self, belief_name):
        if belief_name not in self.beliefs:
            raise KeyError(f"Unknown belief: {belief_name}")

        for justification in self.beliefs[belief_name].implications:
            self.beliefs[repr(justification.conclusion)].remove_justification(
                justification
            )

        self.beliefs.pop(belief_name)

    def set_belief_validity(self, belief_name, validity):
        if belief_name not in self.beliefs:
            raise KeyError(f"Unknown belief: {belief_name}")
        self.beliefs[belief_name].set_truth_value(validity)

    def add_justification(self, in_list, out_list, conclusion_name):
        for b in in_list + out_list + [conclusion_name]:
            if b not in self.beliefs:
                if self.strict:
                    raise KeyError(f"Unknown belief: {b}")
                else:
                    self.add_belief(b)

        justification = Justification(
            [self.beliefs[in_item] for in_item in in_list],
            [self.beliefs[out_item] for out_item in out_list],
            self.beliefs[conclusion_name],
        )
        self.beliefs[conclusion_name].add_justification(justification)
        for in_belief in justification.in_list:
            self.beliefs[in_belief.name].add_implication(justification)
        for out_belief in justification.out_list:
            self.beliefs[out_belief.name].add_implication(justification)

        self.update_non_monotonic_befielfs()

    def update_non_monotonic_befielfs(self):
        vertices = []
        for belief in self.beliefs.values():
            for justification in belief.justifications:
                for statement in justification.in_list + justification.out_list:
                    vertices.append((statement.name, belief.name))
        graph = nx.DiGraph(vertices)
        CFCs = nx.strongly_connected_components(graph)
        for CFC in CFCs:
            if len(CFC) != 1:
                for belief in CFC:
                    self.beliefs[belief].non_monotonic = True

    def show(self):
        for b in self.beliefs.values():
            print(b)

    def explain_belief(self, belief_name):
        belief = self.beliefs[belief_name]
        if not belief.justifications:
            return "No justification"

        explanations = []
        for j in belief.justifications:
            in_status = [
                f"{b} ({'✅' if self.beliefs[repr(b)].valid else '❌'})"
                for b in j.in_list
            ]
            out_status = [
                f"{b} ({'✅' if self.beliefs[repr(b)].valid else '❌'})"
                for b in j.out_list
            ]

            valid = all(self.beliefs[repr(b)].valid for b in j.in_list) and all(
                not self.beliefs[repr(b)].valid for b in j.out_list
            )

            block = (
                f"Justification :\n"
                f"IN : {', '.join(in_status) or '-'}\n"
                f"OUT : {', '.join(out_status) or '-'}\n"
                f"→ Results: {'✅ Valid' if valid else '❌ Invalid'}"
            )
            explanations.append(block)

        return "".join(explanations)

    def visualize(self, output_file="jtms_graph.html"):
        net = Network(directed=True, notebook=False)
        net.barnes_hut()

        for belief in self.beliefs.values():
            print(belief)
            color = (
                "orange" if belief.non_monotonic else "green" if belief.valid else "red"
            )
            html_explanation = self.explain_belief(belief.name)
            net.add_node(
                belief.name, label=belief.name, color=color, title=f"{html_explanation}"
            )

        for belief in self.beliefs.values():
            for j in belief.justifications:
                for source in j.in_list:
                    net.add_edge(repr(source), repr(belief), color="green", title="IN")
                for source in j.out_list:
                    net.add_edge(
                        repr(source),
                        repr(belief),
                        color="red",
                        dashes=True,
                        title="OUT",
                    )

        net.write_html(output_file)
