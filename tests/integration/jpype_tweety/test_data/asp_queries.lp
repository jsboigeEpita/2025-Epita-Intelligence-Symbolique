% Fait
bird(tweety).

% Règle simple
flies(X) :- bird(X), not flightless(X).

% Un oiseau qui ne vole pas
flightless(penguin).
bird(penguin).

% Un autre oiseau
bird(sparrow).