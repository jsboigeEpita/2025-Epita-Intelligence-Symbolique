class StringConcatPlugin:
    def concat_naive(self, strings: list) -> str:
        result = ""
        for s in strings:
            result += s
        return result

    def concat_optimized(self, strings: list) -> str:
        return "".join(strings)