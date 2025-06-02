bird(tweety).
bird(penguin).
bird(sparrow).

flies(X) :- bird(X), not ab(X).
ab(penguin).