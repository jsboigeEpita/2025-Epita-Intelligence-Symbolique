import string
import pytest
from argumentation_analysis.core.utils.text_utils import normalize_text, tokenize_text

# Tests for normalize_text
def test_normalize_text_lowercase():
    assert normalize_text("UPPERCASE") == "uppercase"

def test_normalize_text_remove_punctuation():
    assert normalize_text("Hello, World!") == "hello world"

def test_normalize_text_normalize_spaces():
    assert normalize_text("Extra   spaces  here.") == "extra spaces here" # Corrected: strip removes trailing period if space before

def test_normalize_text_with_accents():
    assert normalize_text("Voilà un résumé.") == "voila un resume" # Corrected: strip removes trailing period

def test_normalize_text_empty_string():
    assert normalize_text("") == ""

def test_normalize_text_already_normalized():
    assert normalize_text("already normalized text") == "already normalized text"

def test_normalize_text_mixed_punctuation_and_spaces():
    assert normalize_text("  Test,,, with   multiple issues!!  ") == "test with multiple issues"

def test_normalize_text_apostrophes_internal():
    assert normalize_text("l'important c'est d'avoir l'apostrophe") == "l'important c'est d'avoir l'apostrophe"

def test_normalize_text_apostrophes_external_and_multiple():
    assert normalize_text("'début' et ''fin'' et 'isolée' et l'''exemple'''") == "debut et fin et isolee et l'exemple"

def test_normalize_text_all_punctuations():
    # Test with string.punctuation, excluding apostrophe as it's specially handled
    all_punct = string.punctuation.replace("'", "")
    assert normalize_text(f"test{all_punct}punct") == "test punct"

def test_normalize_text_type_error():
    with pytest.raises(TypeError, match="L'entrée doit être une chaîne de caractères."):
        normalize_text(123)

# Tests for tokenize_text
def test_tokenize_text_simple_sentence():
    # normalize_text is called internally, so punctuation will be removed, text lowercased, accents removed
    assert tokenize_text("This is a simple sentence.") == ["this", "is", "a", "simple", "sentence"]

def test_tokenize_text_with_punctuation_and_accents():
    assert tokenize_text("  Ceci est un EXEMPLE, avec des accents (éàç) et des espaces !  ") == \
           ['ceci', 'est', 'un', 'exemple', 'avec', 'des', 'accents', 'eac', 'et', 'des', 'espaces']

def test_tokenize_text_with_apostrophes():
    # Based on normalize_text behavior for apostrophes
    assert tokenize_text("L'important c'est d'essayer. Et l''autre aussi.") == \
           ['l', 'important', 'c', 'est', 'd', 'essayer', 'et', 'l', 'autre', 'aussi']

def test_tokenize_text_multiple_spaces_and_tabs():
    assert tokenize_text("Word  another \t word.  ") == ["word", "another", "word"]

def test_tokenize_text_empty_string():
    assert tokenize_text("") == []

def test_tokenize_text_string_with_only_spaces_or_punctuation():
    assert tokenize_text("   ,,, !!!   ") == []

def test_tokenize_text_type_error():
    with pytest.raises(TypeError, match="L'entrée doit être une chaîne de caractères."):
        tokenize_text(None)

def test_tokenize_text_from_normalize_text_example():
    # Example from normalize_text docstring
    text = "  Ceci est un EXEMPLE, avec des accents (éàç) et des espaces !  "
    # Expected from normalize_text: 'ceci est un exemple avec des accents eac et des espaces'
    assert tokenize_text(text) == ['ceci', 'est', 'un', 'exemple', 'avec', 'des', 'accents', 'eac', 'et', 'des', 'espaces']

def test_tokenize_text_from_normalize_text_apostrophe_example():
    text = "L'important c'est d'essayer."
    # Expected from normalize_text: "l'important c'est d'essayer"
    # Then split:
    assert tokenize_text(text) == ['l', 'important', 'c', 'est', 'd', 'essayer']