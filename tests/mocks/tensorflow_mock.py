"""
Mock complet pour TensorFlow
"""


class MockTensor:
    def __init__(self, data=None, shape=None):
        self.data = data or []
        self.shape = shape or (1,)

    def numpy(self):
        return self.data


class MockKeras:
    class layers:
        @staticmethod
        def Dense(*args, **kwargs):
            return MockTensor()

        @staticmethod
        def Input(*args, **kwargs):
            return MockTensor()

    class Model:
        def __init__(self, *args, **kwargs):
            pass

        def compile(self, *args, **kwargs):
            pass

        def fit(self, *args, **kwargs):
            return {"loss": 0.1, "accuracy": 0.9}


def constant(value, dtype=None):
    return MockTensor(value)


def Variable(initial_value, **kwargs):
    return MockTensor(initial_value)


keras = MockKeras()
