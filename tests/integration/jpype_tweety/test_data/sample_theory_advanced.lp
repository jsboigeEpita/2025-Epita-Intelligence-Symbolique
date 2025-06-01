% Exemple de théorie logique pour tests avancés
% Contient des règles, des faits et des propositions pour tester des reasoners plus complexes.

% Faits
bird.
flies.

% Règles
penguin :- bird, NOT flies.
can_swim :- penguin.