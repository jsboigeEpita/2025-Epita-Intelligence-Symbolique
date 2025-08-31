# -*- coding: utf-8 -*-

"""
Tests de performance pour les plugins du projet.
"""

from tests.fixtures.plugins.prefixer.prefixer_plugin import PrefixerPlugin

def test_prefixer_plugin_performance(benchmark):
    """
    Mesure la performance du PrefixerPlugin.
    """
    plugin = PrefixerPlugin()
    benchmark(plugin.add_prefix, text="un texte de test")

from tests.fixtures.plugins.string_concat.string_concat_plugin import StringConcatPlugin

def test_concat_naive_performance(benchmark):
    plugin = StringConcatPlugin()
    string_list = ["test"] * 100
    benchmark.group = "string-concatenation"
    benchmark(plugin.concat_naive, strings=string_list)

def test_concat_optimized_performance(benchmark):
    plugin = StringConcatPlugin()
    string_list = ["test"] * 100
    benchmark.group = "string-concatenation"
    benchmark(plugin.concat_optimized, strings=string_list)