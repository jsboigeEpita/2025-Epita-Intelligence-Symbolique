import numpy as np

class Agent:
    """
    Represents an agent with a personality, preferences, trust, memory, coalition logic, argumentation, and learning.
    Agents can adapt, negotiate, form coalitions, exchange arguments, and learn optimal strategies.
    """
    def __init__(self, name, personality, preferences, strategy=None, n_agents=None):
        self.name = name
        self.personality = personality
        self.preferences = preferences
        self.strategy = strategy
        self.memory = []  # Stores (decision, outcome, context)
        self.trust = {}   # trust[other_name] = score in [0,1]
        self.coalition = None  # coalition id or None
        self.satisfaction_history = []
        self.argument_history = []  # Stores arguments exchanged
        self.q_table = {}  # Q-learning: (state, action) -> value
        self.epsilon = 0.1  # Exploration rate
        self.alpha = 0.5    # Learning rate
        self.gamma = 0.9    # Discount factor
        if n_agents:
            self.trust = {f"Agent{i+1}": 0.5 for i in range(n_agents) if f"Agent{i+1}" != self.name}

    def get_state(self, options, context):
        # State can be tuple of (top preference, coalition, round, etc.)
        coalition = self.coalition if self.coalition else 'none'
        top_pref = self.preferences[0] if self.preferences else 'none'
        return (top_pref, coalition)

    def choose_action(self, options, context):
        """
        Choose an action (option) using epsilon-greedy policy from Q-table.
        """
        state = self.get_state(options, context)
        if np.random.rand() < self.epsilon:
            return np.random.choice(options)
        q_values = [self.q_table.get((state, o), 0.0) for o in options]
        max_q = max(q_values)
        best_options = [o for o, q in zip(options, q_values) if q == max_q]
        return np.random.choice(best_options)

    def update_q(self, options, context, action, reward, next_options, next_context):
        """
        Update Q-value for (state, action) using Q-learning update rule.
        """
        state = self.get_state(options, context)
        next_state = self.get_state(next_options, next_context)
        max_next_q = max([self.q_table.get((next_state, o), 0.0) for o in next_options]) if next_options else 0.0
        old_q = self.q_table.get((state, action), 0.0)
        self.q_table[(state, action)] = old_q + self.alpha * (reward + self.gamma * max_next_q - old_q)

    def decide(self, options, context=None):
        if self.coalition and 'coalition_leader' in context:
            return context['coalition_leader']
        if len(self.satisfaction_history) >= 3 and np.mean(self.satisfaction_history[-3:]) < 0.3:
            if self.personality == 'stubborn':
                self.personality = 'flexible'
        if self.personality == 'stubborn':
            return self.preferences[0]
        elif self.personality == 'flexible':
            if context and 'majority_hint' in context:
                majority = context['majority_hint']
                if majority in options:
                    return majority
            return self.preferences[0]
        elif self.personality == 'strategic':
            if context and 'likely_winner' in context and self.trust:
                likely = context['likely_winner']
                if likely in self.preferences and max(self.trust.values()) > 0.7:
                    return likely
            return self.preferences[1] if len(self.preferences) > 1 else self.preferences[0]
        else:
            return self.choose_action(options, context)

    def update_memory(self, decision, outcome, context=None):
        self.memory.append({'decision': decision, 'outcome': outcome, 'context': context})
        if outcome in self.preferences:
            sat = 1.0 - self.preferences.index(outcome)/max(1, len(self.preferences)-1)
        else:
            sat = 0
        self.satisfaction_history.append(sat)
        # Q-learning update: reward is satisfaction
        if len(self.memory) > 1:
            prev = self.memory[-2]
            prev_options = prev['context']['options'] if prev['context'] and 'options' in prev['context'] else options
            prev_context = prev['context']
            self.update_q(prev_options, prev_context, prev['decision'], sat, options, context)
        if context and 'proposed_by' in context:
            proposer = context['proposed_by']
            if proposer != self.name:
                self.trust[proposer] = min(1.0, self.trust.get(proposer, 0.5) + 0.1)

    def negotiate(self, options, context=None):
        if self.trust and max(self.trust.values()) > 0.8:
            partner = max(self.trust, key=self.trust.get)
            return ('form_coalition', partner)
        if self.personality == 'stubborn':
            return ('propose', self.preferences[0])
        elif self.personality == 'flexible':
            if context and 'proposed' in context and context['proposed'] in self.preferences[:2]:
                return ('accept', context['proposed'])
            return ('propose', self.preferences[0])
        elif self.personality == 'strategic':
            if context and 'proposed' in context and context['proposed'] != self.preferences[0]:
                return ('argue', self.preferences[1] if len(self.preferences) > 1 else self.preferences[0])
            return ('propose', self.preferences[0])
        else:
            return ('propose', np.random.choice(options))

    def propose_argument(self, option, reason):
        """
        Propose an argument for an option (e.g., 'Option A is best because...').
        """
        argument = {'agent': self.name, 'option': option, 'reason': reason}
        self.argument_history.append(argument)
        return argument

    def receive_argument(self, argument):
        """
        Receive and process an argument from another agent. May update preferences.
        """
        self.argument_history.append(argument)
        # If reason is compelling and agent is flexible, may update preferences
        if self.personality == 'flexible' and argument['option'] in self.preferences:
            idx = self.preferences.index(argument['option'])
            if idx > 0:
                # Move option up in preferences
                self.preferences.pop(idx)
                self.preferences.insert(0, argument['option'])

    def counter_argument(self, option, reason):
        """
        Counter an argument with a new reason.
        """
        return self.propose_argument(option, reason) 