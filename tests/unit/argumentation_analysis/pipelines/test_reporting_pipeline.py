# tests/unit/argumentation_analysis/pipelines/test_reporting_pipeline.py
import pytest
from unittest.mock import patch, MagicMock, call
import pandas as actual_pandas_module # Renommé pour clarté
# Capture des vrais types pandas avant tout mock potentiel par des fixtures ou autres imports
REAL_PANDAS_DATAFRAME_TYPE = actual_pandas_module.DataFrame
REAL_PANDAS_SERIES_TYPE = actual_pandas_module.Series
from pathlib import Path
import sys

from argumentation_analysis.pipelines.reporting_pipeline import run_comprehensive_report_pipeline

MODULE_PATH = "argumentation_analysis.pipelines.reporting_pipeline"
PANDAS_DATAFRAME_PATH = f"{MODULE_PATH}.pd.DataFrame"
MATPLOTLIB_PYPLOT_FIGURE_PATH = f"{MODULE_PATH}.plt.figure"
MATPLOTLIB_PYPLOT_CLOSE_PATH = f"{MODULE_PATH}.plt.close"
SEABORN_BARPLOT_PATH = f"{MODULE_PATH}.sns.barplot" 

@pytest.fixture
def mock_load_json_file():
    with patch(f"{MODULE_PATH}.load_json_file") as mock:
        yield mock

@pytest.fixture
def mock_load_text_file():
    with patch(f"{MODULE_PATH}.load_text_file") as mock:
        yield mock

@pytest.fixture
def mock_load_csv_file():
    with patch(f"{MODULE_PATH}.load_csv_file") as mock:
        yield mock

@pytest.fixture
def mock_group_results():
    with patch(f"{MODULE_PATH}.group_results_by_corpus") as mock:
        yield mock

@pytest.fixture
def mock_calculate_scores():
    with patch(f"{MODULE_PATH}.calculate_average_scores") as mock:
        yield mock

@pytest.fixture
def mock_generate_md():
    with patch(f"{MODULE_PATH}.generate_markdown_report_for_corpus") as mock:
        yield mock

@pytest.fixture
def mock_save_html():
    with patch(f"{MODULE_PATH}.save_markdown_to_html") as mock:
        yield mock

@pytest.fixture
def default_config():
    return {
        "load_config": {"format": "json"},
        "save_config": {}
    }

@pytest.fixture
def sample_analysis_data_list():
    return [
        {"text_id": "a1", "corpus_id": "corpus_A", "score": 0.8, "argument_type": "pro"},
        {"text_id": "a2", "corpus_id": "corpus_A", "score": 0.6, "argument_type": "con"},
        {"text_id": "b1", "corpus_id": "corpus_B", "score": 0.9, "argument_type": "pro"}
    ]

@pytest.fixture
def grouped_sample_analysis_data(): 
    return {
        "corpus_A": [
            {"text_id": "a1", "corpus_id": "corpus_A", "score": 0.8, "argument_type": "pro"},
            {"text_id": "a2", "corpus_id": "corpus_A", "score": 0.6, "argument_type": "con"}
        ],
        "corpus_B": [
            {"text_id": "b1", "corpus_id": "corpus_B", "score": 0.9, "argument_type": "pro"}
        ]
    }

def mock_dataframe_with_T_attribute(*args, **kwargs):
    """
    Crée un MagicMock simulant un pd.DataFrame avec .T, .columns, .index,
    et une gestion basique de __getitem__, .loc[], et .iloc[].
    N'utilise pas spec=pd.DataFrame sur le mock principal pour plus de flexibilité
    dans la configuration des méthodes magiques.
    """
    mock_df = MagicMock() # Pas de spec ici pour éviter les restrictions sur __setattr__ des magics
    
    # Log pd et pd.DataFrame dans mock_dataframe_with_T_attribute
    # print(f"[mock_df_helper] id(actual_pandas_module): {id(actual_pandas_module)}, type(actual_pandas_module): {type(actual_pandas_module)}")
    # print(f"[mock_df_helper] id(actual_pandas_module.DataFrame): {id(actual_pandas_module.DataFrame)}, type(actual_pandas_module.DataFrame): {type(actual_pandas_module.DataFrame)}")
    
    # Attributs essentiels d'un DataFrame
    mock_df.T = MagicMock(spec=REAL_PANDAS_DATAFRAME_TYPE)
    mock_df.columns = []
    mock_df.index = []
    
    # Tentative de rendre isinstance(mock_df, pd.DataFrame) vrai
    mock_df.__class__ = REAL_PANDAS_DATAFRAME_TYPE
    
    def mock_getitem_logic(key):
        # logger.debug(f"MockDataFrame.__getitem__ called with key: {key}, type: {type(key)}")
        if isinstance(key, str):
            # logger.debug(f"MockDataFrame.__getitem__ returning new MagicMock for column '{key}'")
            new_mock_series = MagicMock(spec=REAL_PANDAS_SERIES_TYPE, name=f"column_{key}")
            new_mock_series.name = key
            # Simuler le comportement d'une Series qui peut être convertie en liste
            new_mock_series.tolist.return_value = []
            new_mock_series.__class__ = REAL_PANDAS_SERIES_TYPE
            return new_mock_series
        elif isinstance(key, list):
            # logger.debug(f"MockDataFrame.__getitem__ returning new MagicMock (DataFrame) for columns '{key}'")
            new_mock_df_slice = MagicMock(spec=REAL_PANDAS_DATAFRAME_TYPE, name=f"dataframe_slice_{key}")
            new_mock_df_slice.columns = key # Simuler les colonnes du slice
            new_mock_df_slice.index = []
            new_mock_df_slice.T = MagicMock(spec=REAL_PANDAS_DATAFRAME_TYPE)
            new_mock_df_slice.__class__ = REAL_PANDAS_DATAFRAME_TYPE
            # Configurer __getitem__ pour le slice aussi, récursivement si nécessaire ou avec une logique simplifiée
            new_mock_df_slice.__getitem__ = MagicMock(side_effect=mock_getitem_logic, name='slice_getitem_mock')
            return new_mock_df_slice
        # logger.warning(f"MockDataFrame.__getitem__ unhandled key type: {type(key)}")
        # Pour les autres types de clés (ex: slicing numérique, boolean array), retourner un mock générique
        # ou affiner davantage si des erreurs spécifiques apparaissent.
        return MagicMock(name=f"unhandled_getitem_{type(key)}_{key}")

    # Assigner directement la méthode magique
    mock_df.__getitem__ = MagicMock(side_effect=mock_getitem_logic, name='main_df_getitem_mock')
    
    # Configurer .loc et .iloc
    # .loc et .iloc sont des objets accesseurs qui ont eux-mêmes besoin de __getitem__
    loc_accessor_mock = MagicMock(name='loc_accessor_mock')
    loc_accessor_mock.__getitem__ = MagicMock(side_effect=mock_getitem_logic, name='loc_getitem_mock')
    mock_df.loc = loc_accessor_mock

    iloc_accessor_mock = MagicMock(name='iloc_accessor_mock')
    iloc_accessor_mock.__getitem__ = MagicMock(side_effect=mock_getitem_logic, name='iloc_getitem_mock')
    mock_df.iloc = iloc_accessor_mock
        
    # Simuler d'autres méthodes potentiellement utilisées si des erreurs apparaissent
    # mock_df.empty = False # Par exemple
    # mock_df.shape = (0,0) # Par exemple

    return mock_df

@pytest.mark.use_real_numpy
@patch(f"{MODULE_PATH}.sns.categorical.pd.DataFrame", REAL_PANDAS_DATAFRAME_TYPE)
@patch(f"{MODULE_PATH}.sns.matrix.pd.DataFrame", REAL_PANDAS_DATAFRAME_TYPE)
@patch(SEABORN_BARPLOT_PATH)
@patch(MATPLOTLIB_PYPLOT_CLOSE_PATH)
@patch(MATPLOTLIB_PYPLOT_FIGURE_PATH)
@patch(PANDAS_DATAFRAME_PATH)
@patch(f"{MODULE_PATH}.Path")
def test_run_comprehensive_report_pipeline_success(
    MockPathClass, MockDataFrame, MockPltFigure, MockPltClose, MockSnsBarplot,
    mock_load_json_file, mock_load_text_file, mock_load_csv_file,
    mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config,
    sample_analysis_data_list, grouped_sample_analysis_data
):
    # print(f"\n[test_success_BEGIN] id(actual_pandas_module) in test: {id(actual_pandas_module)}, type(actual_pandas_module): {type(actual_pandas_module)}")
    # print(f"[test_success_BEGIN] id(actual_pandas_module.DataFrame) in test: {id(actual_pandas_module.DataFrame)}, type(actual_pandas_module.DataFrame): {type(actual_pandas_module.DataFrame)}")
    # if 'pandas' in sys.modules:
    #     # Note: sys.modules['pandas'] pourrait être le mock de numpy_setup si pandas a été importé après le nettoyage
    #     # ou le vrai module s'il a été restauré ou re-importé.
    #     print(f"[test_success_BEGIN] id(sys.modules['pandas']): {id(sys.modules['pandas'])}, type: {type(sys.modules['pandas'])}")
    #     # Vérifions si sys.modules['pandas'].DataFrame est le vrai type ou un mock
    #     if hasattr(sys.modules['pandas'], 'DataFrame'):
    #          print(f"[test_success_BEGIN] id(sys.modules['pandas'].DataFrame): {id(sys.modules['pandas'].DataFrame)}, type: {type(sys.modules['pandas'].DataFrame)}")
    #     else:
    #         print("[test_success_BEGIN] sys.modules['pandas'] has no DataFrame attribute")

    # else:
    #     print("[test_success_BEGIN] pandas not in sys.modules")
    
    # MockDataFrame est le mock pour 'argumentation_analysis.pipelines.reporting_pipeline.pd.DataFrame'
    MockDataFrame.side_effect = mock_dataframe_with_T_attribute
    mock_figure_instance = MagicMock(name="figure_instance_success")
    mock_ax_instance = MagicMock(name="ax_instance_success")
    mock_ax_instance.xaxis.set_ticks.return_value = (MagicMock(),)
    mock_ax_instance.yaxis.set_ticks.return_value = (MagicMock(),)

    # Configuration pour set_xticklabels et set_yticklabels
    mock_ticklabel = MagicMock()
    mock_bbox = MagicMock()
    mock_bbox.count_overlaps.return_value = 0 # Simule pas de chevauchement
    mock_ticklabel.get_window_extent.return_value = mock_bbox
    
    mock_ax_instance.set_xticklabels.return_value = [mock_ticklabel]
    mock_ax_instance.set_yticklabels.return_value = [mock_ticklabel]
    mock_ax_instance.xaxis.get_majorticklabels.return_value = [mock_ticklabel] # Ajout pour couvrir d'autres appels potentiels
    mock_ax_instance.yaxis.get_majorticklabels.return_value = [mock_ticklabel] # Ajout pour couvrir d'autres appels potentiels


    mock_figure_instance.gca.return_value = mock_ax_instance
    MockPltFigure.return_value = mock_figure_instance
    MockSnsBarplot.return_value = MagicMock()
    
    results_path_str = "input/results.json"
    advanced_results_file_path_str = "input/advanced_results.json"
    performance_report_file_path_str = "input/performance_report.md"
    performance_metrics_file_path_str = "input/performance_metrics.csv"
    output_dir_for_pipeline = "output_dir_test"

    mock_results_path_instance = MagicMock(spec=Path); mock_results_path_instance.exists.return_value = True
    mock_advanced_results_path_instance = MagicMock(spec=Path); mock_advanced_results_path_instance.exists.return_value = True
    mock_perf_report_path_instance = MagicMock(spec=Path); mock_perf_report_path_instance.exists.return_value = True
    mock_perf_metrics_path_instance = MagicMock(spec=Path); mock_perf_metrics_path_instance.exists.return_value = True
    mock_output_dir_instance = MagicMock(spec=Path); mock_output_dir_instance.exists.return_value = True
    mock_visualization_dir_instance = MagicMock(spec=Path); mock_visualization_dir_instance.is_dir.return_value = True
    mock_visualization_dir_instance.mkdir.return_value = None

    def path_constructor_side_effect(path_arg_str):
        if path_arg_str == results_path_str: return mock_results_path_instance
        if path_arg_str == advanced_results_file_path_str: return mock_advanced_results_path_instance
        if path_arg_str == performance_report_file_path_str: return mock_perf_report_path_instance
        if path_arg_str == performance_metrics_file_path_str: return mock_perf_metrics_path_instance
        if str(path_arg_str) == str(Path(output_dir_for_pipeline) / "visualizations"): return mock_visualization_dir_instance
        if str(path_arg_str).startswith(output_dir_for_pipeline):
            mock_path_in_output = MagicMock(spec=Path)
            mock_path_in_output.exists.return_value = True
            mock_path_in_output.__truediv__.return_value = mock_output_dir_instance
            return mock_path_in_output
        default_mock_path = MagicMock(spec=Path); default_mock_path.exists.return_value = True
        return default_mock_path
    MockPathClass.side_effect = path_constructor_side_effect
    
    mock_load_json_file.side_effect = [sample_analysis_data_list, sample_analysis_data_list]
    mock_load_text_file.return_value = "Performance report content"
    mock_load_csv_file.return_value = MagicMock(spec=actual_pandas_module.DataFrame)

    mock_group_results.return_value = grouped_sample_analysis_data
    
    def calculate_side_effect_success(grouped_data):
        return {"corpus_A": {"average_score": 0.7}, "corpus_B": {"average_score": 0.9}}
    mock_calculate_scores.side_effect = calculate_side_effect_success
    
    mock_generate_md.side_effect = [["Report A line 1"], ["Report B line 1"]]
    mock_save_html.return_value = True

    result = run_comprehensive_report_pipeline(
        results_path_str, advanced_results_file_path_str,
        performance_report_file_path_str, performance_metrics_file_path_str,
        output_dir_for_pipeline
    )

    expected_json_calls = [call(mock_results_path_instance), call(mock_advanced_results_path_instance)]
    mock_load_json_file.assert_has_calls(expected_json_calls, any_order=True)
    mock_load_text_file.assert_called_once_with(mock_perf_report_path_instance)
    mock_load_csv_file.assert_called_once_with(mock_perf_metrics_path_instance)

    expected_group_calls = [call(sample_analysis_data_list), call(sample_analysis_data_list)]
    mock_group_results.assert_has_calls(expected_group_calls)
    
    expected_calculate_calls = [call(grouped_sample_analysis_data), call(grouped_sample_analysis_data)]
    mock_calculate_scores.assert_has_calls(expected_calculate_calls)

    assert mock_generate_md.call_count >= 2
    mock_save_html.assert_called_once()
    assert result is True
    
    mock_results_path_instance.exists.assert_called()
    mock_advanced_results_path_instance.exists.assert_called()
    mock_perf_report_path_instance.exists.assert_called()
    mock_perf_metrics_path_instance.exists.assert_called()
    MockDataFrame.assert_called()
    MockPltFigure.assert_called()
    MockPltClose.assert_called()
    MockSnsBarplot.assert_called()


@patch(f"{MODULE_PATH}.Path")
def test_run_comprehensive_report_pipeline_load_failure(
    MockPathClass, mock_load_json_file, mock_load_text_file, mock_load_csv_file,
    mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config
):
    mock_input_json_path_instance = MagicMock(spec=Path); mock_input_json_path_instance.exists.return_value = False
    mock_advanced_json_path_instance = MagicMock(spec=Path); mock_advanced_json_path_instance.exists.return_value = True 

    def path_constructor_side_effect(path_str):
        if path_str == "input.json": return mock_input_json_path_instance
        if path_str == "advanced_input.json": return mock_advanced_json_path_instance
        default_mock_path = MagicMock(spec=Path); default_mock_path.exists.return_value = True
        return default_mock_path
    MockPathClass.side_effect = path_constructor_side_effect

    result = run_comprehensive_report_pipeline("input.json", "advanced_input.json", None, None, "output_dir_failure_test")
    
    MockPathClass.assert_any_call("input.json")
    mock_input_json_path_instance.exists.assert_called_once()
    mock_load_json_file.assert_not_called()
    mock_group_results.assert_not_called()
    mock_calculate_scores.assert_not_called()
    mock_generate_md.assert_not_called()
    mock_save_html.assert_not_called()
    assert result is False

@patch(SEABORN_BARPLOT_PATH)
@patch(MATPLOTLIB_PYPLOT_CLOSE_PATH)
@patch(MATPLOTLIB_PYPLOT_FIGURE_PATH)
@patch(PANDAS_DATAFRAME_PATH)
@patch(f"{MODULE_PATH}.Path") 
def test_run_comprehensive_report_pipeline_grouping_failure(
    MockPathClass, MockDataFrame, MockPltFigure, MockPltClose, MockSnsBarplot,
    mock_load_json_file, mock_load_text_file, mock_load_csv_file, 
    mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config, sample_analysis_data_list
):
    MockDataFrame.side_effect = mock_dataframe_with_T_attribute
    MockPathClass.return_value.exists.return_value = True
    mock_figure_instance_group_fail = MagicMock(name="figure_instance_group_fail")
    mock_ax_instance_group_fail = MagicMock(name="ax_instance_group_fail")
    # Bien que ce test ne devrait pas atteindre la visualisation à cause du ValueError simulé,
    # configurons les mocks d'axe correctement par cohérence et pour le futur.
    mock_ax_instance_group_fail.xaxis.set_ticks.return_value = (MagicMock(),)
    mock_ax_instance_group_fail.yaxis.set_ticks.return_value = (MagicMock(),)

    mock_ticklabel_group_fail = MagicMock(name="ticklabel_group_fail")
    mock_bbox_group_fail = MagicMock(name="bbox_group_fail")
    mock_bbox_group_fail.count_overlaps.return_value = 0
    mock_ticklabel_group_fail.get_window_extent.return_value = mock_bbox_group_fail

    mock_ax_instance_group_fail.set_xticklabels.return_value = [mock_ticklabel_group_fail]
    mock_ax_instance_group_fail.set_yticklabels.return_value = [mock_ticklabel_group_fail]
    mock_ax_instance_group_fail.xaxis.get_majorticklabels.return_value = [mock_ticklabel_group_fail]
    mock_ax_instance_group_fail.yaxis.get_majorticklabels.return_value = [mock_ticklabel_group_fail]
    
    mock_figure_instance_group_fail.gca.return_value = mock_ax_instance_group_fail
    MockPltFigure.return_value = mock_figure_instance_group_fail
    MockSnsBarplot.return_value = MagicMock()

    mock_load_json_file.side_effect = [sample_analysis_data_list, sample_analysis_data_list]
    mock_group_results.side_effect = ValueError("Simulated Grouping issue")

    result = run_comprehensive_report_pipeline("input.json", "advanced_input.json", None, None, "output_dir_group_fail")
    
    assert mock_load_json_file.call_count == 2
    mock_group_results.assert_called_once_with(sample_analysis_data_list)
    mock_calculate_scores.assert_not_called()
    mock_generate_md.assert_not_called()
    mock_save_html.assert_not_called()
    assert result is False
    MockDataFrame.assert_called()

@pytest.mark.use_real_numpy
@patch(f"{MODULE_PATH}.sns.categorical.pd.DataFrame", REAL_PANDAS_DATAFRAME_TYPE)
@patch(f"{MODULE_PATH}.sns.matrix.pd.DataFrame", REAL_PANDAS_DATAFRAME_TYPE)
@patch(SEABORN_BARPLOT_PATH)
@patch(MATPLOTLIB_PYPLOT_CLOSE_PATH)
@patch(MATPLOTLIB_PYPLOT_FIGURE_PATH)
@patch(PANDAS_DATAFRAME_PATH)
@patch(f"{MODULE_PATH}.Path")
def test_run_comprehensive_report_pipeline_calculate_score_failure_for_one_corpus(
    MockPathClass, MockDataFrame, MockPltFigure, MockPltClose, MockSnsBarplot,
    mock_load_json_file, mock_load_text_file, mock_load_csv_file,
    mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config,
    sample_analysis_data_list, grouped_sample_analysis_data
):
    MockDataFrame.side_effect = mock_dataframe_with_T_attribute
    MockPathClass.return_value.exists.return_value = True
    mock_figure_instance_calc_fail = MagicMock(name="figure_instance_calc_fail")
    mock_ax_instance_calc_fail = MagicMock(name="ax_instance_calc_fail")
    mock_ax_instance_calc_fail.xaxis.set_ticks.return_value = (MagicMock(),)
    mock_ax_instance_calc_fail.yaxis.set_ticks.return_value = (MagicMock(),)
    
    # Configuration pour set_xticklabels et set_yticklabels
    mock_ticklabel_calc_fail = MagicMock()
    mock_bbox_calc_fail = MagicMock()
    mock_bbox_calc_fail.count_overlaps.return_value = 0
    mock_ticklabel_calc_fail.get_window_extent.return_value = mock_bbox_calc_fail
    
    mock_ax_instance_calc_fail.set_xticklabels.return_value = [mock_ticklabel_calc_fail]
    mock_ax_instance_calc_fail.set_yticklabels.return_value = [mock_ticklabel_calc_fail]
    mock_ax_instance_calc_fail.xaxis.get_majorticklabels.return_value = [mock_ticklabel_calc_fail]
    mock_ax_instance_calc_fail.yaxis.get_majorticklabels.return_value = [mock_ticklabel_calc_fail]

    mock_figure_instance_calc_fail.gca.return_value = mock_ax_instance_calc_fail
    MockPltFigure.return_value = mock_figure_instance_calc_fail
    MockSnsBarplot.return_value = MagicMock()
    
    mock_load_json_file.side_effect = [sample_analysis_data_list, sample_analysis_data_list]
    mock_group_results.return_value = grouped_sample_analysis_data
    
    mock_calculate_scores.return_value = {"corpus_A": {}, "corpus_B": {"average_score": 0.9}}
    mock_generate_md.return_value = ["Report B line 1"]
    mock_save_html.return_value = True

    result = run_comprehensive_report_pipeline("input.json", "advanced_input.json", None, None, "output_dir_calc_fail_one")

    assert mock_load_json_file.call_count == 2
    assert mock_group_results.call_count == 2
    mock_group_results.assert_has_calls([call(sample_analysis_data_list), call(sample_analysis_data_list)])
    assert mock_calculate_scores.call_count == 2
    mock_generate_md.assert_called()
    mock_save_html.assert_called_once()
    assert result is True
    MockDataFrame.assert_called()
    MockPltFigure.assert_called()
    MockPltClose.assert_called()
    MockSnsBarplot.assert_called()

@pytest.mark.use_real_numpy
@patch(f"{MODULE_PATH}.sns.categorical.pd.DataFrame", REAL_PANDAS_DATAFRAME_TYPE)
@patch(f"{MODULE_PATH}.sns.matrix.pd.DataFrame", REAL_PANDAS_DATAFRAME_TYPE)
@patch(SEABORN_BARPLOT_PATH)
@patch(MATPLOTLIB_PYPLOT_CLOSE_PATH)
@patch(MATPLOTLIB_PYPLOT_FIGURE_PATH)
@patch(PANDAS_DATAFRAME_PATH)
@patch(f"{MODULE_PATH}.Path")
def test_run_comprehensive_report_pipeline_generate_md_failure_for_one_corpus(
    MockPathClass, MockDataFrame, MockPltFigure, MockPltClose, MockSnsBarplot,
    mock_load_json_file, mock_load_text_file, mock_load_csv_file,
    mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config,
    sample_analysis_data_list, grouped_sample_analysis_data
):
    MockDataFrame.side_effect = mock_dataframe_with_T_attribute
    MockPathClass.return_value.exists.return_value = True
    mock_figure_instance_md_fail = MagicMock(name="figure_instance_md_fail")
    mock_ax_instance_md_fail = MagicMock(name="ax_instance_md_fail")
    mock_ax_instance_md_fail.xaxis.set_ticks.return_value = (MagicMock(),)
    mock_ax_instance_md_fail.yaxis.set_ticks.return_value = (MagicMock(),)

    # Configuration pour set_xticklabels et set_yticklabels
    mock_ticklabel_md_fail = MagicMock()
    mock_bbox_md_fail = MagicMock()
    mock_bbox_md_fail.count_overlaps.return_value = 0
    mock_ticklabel_md_fail.get_window_extent.return_value = mock_bbox_md_fail

    mock_ax_instance_md_fail.set_xticklabels.return_value = [mock_ticklabel_md_fail]
    mock_ax_instance_md_fail.set_yticklabels.return_value = [mock_ticklabel_md_fail]
    mock_ax_instance_md_fail.xaxis.get_majorticklabels.return_value = [mock_ticklabel_md_fail]
    mock_ax_instance_md_fail.yaxis.get_majorticklabels.return_value = [mock_ticklabel_md_fail]
    
    mock_figure_instance_md_fail.gca.return_value = mock_ax_instance_md_fail
    MockPltFigure.return_value = mock_figure_instance_md_fail
    MockSnsBarplot.return_value = MagicMock()

    mock_load_json_file.side_effect = [sample_analysis_data_list, sample_analysis_data_list]
    mock_group_results.return_value = grouped_sample_analysis_data
    mock_calculate_scores.return_value = {"corpus_A": {"average_score": 0.7}, "corpus_B": {"average_score": 0.9}}
    mock_generate_md.side_effect = [ValueError("MD gen error for A"), ["Report B line 1"]]
    mock_save_html.return_value = True

    result = run_comprehensive_report_pipeline("input.json", "advanced_input.json", None, None, "output_dir_md_fail_one")
    
    assert mock_generate_md.call_count > 0
    mock_save_html.assert_called_once()
    assert result is True
    MockDataFrame.assert_called()
    MockPltFigure.assert_called()
    MockPltClose.assert_called()
    MockSnsBarplot.assert_called()

@pytest.mark.use_real_numpy
@patch(f"{MODULE_PATH}.sns.categorical.pd.DataFrame", REAL_PANDAS_DATAFRAME_TYPE)
@patch(f"{MODULE_PATH}.sns.matrix.pd.DataFrame", REAL_PANDAS_DATAFRAME_TYPE)
@patch(SEABORN_BARPLOT_PATH)
@patch(MATPLOTLIB_PYPLOT_CLOSE_PATH)
@patch(MATPLOTLIB_PYPLOT_FIGURE_PATH)
@patch(PANDAS_DATAFRAME_PATH)
@patch(f"{MODULE_PATH}.Path")
def test_run_comprehensive_report_pipeline_save_html_failure(
    MockPathClass, MockDataFrame, MockPltFigure, MockPltClose, MockSnsBarplot,
    mock_load_json_file, mock_load_text_file, mock_load_csv_file,
    mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config,
    sample_analysis_data_list, grouped_sample_analysis_data
):
    MockDataFrame.side_effect = mock_dataframe_with_T_attribute
    MockPathClass.return_value.exists.return_value = True
    mock_figure_instance_save_fail = MagicMock(name="figure_instance_save_fail")
    mock_ax_instance_save_fail = MagicMock(name="ax_instance_save_fail")
    mock_ax_instance_save_fail.xaxis.set_ticks.return_value = (MagicMock(),)
    mock_ax_instance_save_fail.yaxis.set_ticks.return_value = (MagicMock(),)

    # Configuration pour set_xticklabels et set_yticklabels
    mock_ticklabel_save_fail = MagicMock()
    mock_bbox_save_fail = MagicMock()
    mock_bbox_save_fail.count_overlaps.return_value = 0
    mock_ticklabel_save_fail.get_window_extent.return_value = mock_bbox_save_fail

    mock_ax_instance_save_fail.set_xticklabels.return_value = [mock_ticklabel_save_fail]
    mock_ax_instance_save_fail.set_yticklabels.return_value = [mock_ticklabel_save_fail]
    mock_ax_instance_save_fail.xaxis.get_majorticklabels.return_value = [mock_ticklabel_save_fail]
    mock_ax_instance_save_fail.yaxis.get_majorticklabels.return_value = [mock_ticklabel_save_fail]

    mock_figure_instance_save_fail.gca.return_value = mock_ax_instance_save_fail
    MockPltFigure.return_value = mock_figure_instance_save_fail
    MockSnsBarplot.return_value = MagicMock()

    mock_load_json_file.side_effect = [sample_analysis_data_list, sample_analysis_data_list]
    mock_group_results.return_value = grouped_sample_analysis_data
    mock_calculate_scores.return_value = {"corpus_A": {"average_score": 0.75}, "corpus_B": {"average_score": 0.75}}
    mock_generate_md.return_value = ["Some Report line 1"]
    mock_save_html.return_value = False

    result = run_comprehensive_report_pipeline("input.json", "advanced_input.json", None, None, "output_dir_save_fail")

    mock_save_html.assert_called()
    assert result is False
    MockDataFrame.assert_called()
    MockPltFigure.assert_called()
    MockPltClose.assert_called()
    MockSnsBarplot.assert_called()

@patch(SEABORN_BARPLOT_PATH)
@patch(MATPLOTLIB_PYPLOT_CLOSE_PATH)
@patch(MATPLOTLIB_PYPLOT_FIGURE_PATH)
@patch(PANDAS_DATAFRAME_PATH)
@patch(f"{MODULE_PATH}.Path")
def test_run_comprehensive_report_pipeline_no_data_loaded(
    MockPathClass, MockDataFrame, MockPltFigure, MockPltClose, MockSnsBarplot,
    mock_load_json_file, mock_load_text_file, mock_load_csv_file, 
    mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config
):
    MockDataFrame.side_effect = mock_dataframe_with_T_attribute
    MockPathClass.return_value.exists.return_value = True
    mock_figure_instance_no_data = MagicMock(name="figure_instance_no_data")
    mock_ax_instance_no_data = MagicMock(name="ax_instance_no_data")
    # Bien que ce test ne devrait pas atteindre la visualisation, par cohérence:
    mock_ax_instance_no_data.xaxis.set_ticks.return_value = (MagicMock(),)
    mock_ax_instance_no_data.yaxis.set_ticks.return_value = (MagicMock(),)
    mock_figure_instance_no_data.gca.return_value = mock_ax_instance_no_data
    MockPltFigure.return_value = mock_figure_instance_no_data
    MockSnsBarplot.return_value = MagicMock()
    
    mock_load_json_file.return_value = [] 
    mock_group_results.return_value = {}
    mock_save_html.return_value = True

    result = run_comprehensive_report_pipeline("input.json", "advanced_input.json", None, None, "output_dir_no_data")
            
    assert mock_load_json_file.call_count == 2
    mock_group_results.assert_not_called()
    mock_calculate_scores.assert_not_called()
    mock_generate_md.assert_not_called()
    mock_save_html.assert_not_called() # Ne devrait pas être appelé si le pipeline sort tôt
    assert result is False # Le pipeline devrait retourner False si aucune donnée n'est chargée
    # DataFrame might be called with empty data if performance files are absent, or not at all.
    # MockDataFrame.assert_called() # This might be too strict.
    # Visualizations might not be called if no data
    # MockPltFigure.assert_not_called() # More precise
    # MockPltClose.assert_not_called()  # More precise
    # MockSnsBarplot.assert_not_called() # More precise


@pytest.mark.use_real_numpy
@patch(f"{MODULE_PATH}.sns.categorical.pd.DataFrame", REAL_PANDAS_DATAFRAME_TYPE)
@patch(f"{MODULE_PATH}.sns.matrix.pd.DataFrame", REAL_PANDAS_DATAFRAME_TYPE)
@patch(SEABORN_BARPLOT_PATH)
@patch(MATPLOTLIB_PYPLOT_CLOSE_PATH)
@patch(MATPLOTLIB_PYPLOT_FIGURE_PATH)
@patch(PANDAS_DATAFRAME_PATH)
@patch(f"{MODULE_PATH}.Path")
def test_run_comprehensive_report_pipeline_all_corpora_fail_processing(
    MockPathClass, MockDataFrame, MockPltFigure, MockPltClose, MockSnsBarplot,
    mock_load_json_file, mock_load_text_file, mock_load_csv_file,
    mock_group_results, mock_calculate_scores,
    mock_generate_md, mock_save_html, default_config,
    sample_analysis_data_list, grouped_sample_analysis_data
):
    MockDataFrame.side_effect = mock_dataframe_with_T_attribute
    MockPathClass.return_value.exists.return_value = True
    mock_figure_instance_all_fail_proc = MagicMock(name="figure_instance_all_fail_proc")
    mock_ax_instance_all_fail_proc = MagicMock(name="ax_instance_all_fail_proc")
    mock_ax_instance_all_fail_proc.xaxis.set_ticks.return_value = (MagicMock(),)
    mock_ax_instance_all_fail_proc.yaxis.set_ticks.return_value = (MagicMock(),)

    # Configuration pour set_xticklabels et set_yticklabels
    mock_ticklabel_all_fail_proc = MagicMock()
    mock_bbox_all_fail_proc = MagicMock()
    mock_bbox_all_fail_proc.count_overlaps.return_value = 0
    mock_ticklabel_all_fail_proc.get_window_extent.return_value = mock_bbox_all_fail_proc

    mock_ax_instance_all_fail_proc.set_xticklabels.return_value = [mock_ticklabel_all_fail_proc]
    mock_ax_instance_all_fail_proc.set_yticklabels.return_value = [mock_ticklabel_all_fail_proc]
    mock_ax_instance_all_fail_proc.xaxis.get_majorticklabels.return_value = [mock_ticklabel_all_fail_proc]
    mock_ax_instance_all_fail_proc.yaxis.get_majorticklabels.return_value = [mock_ticklabel_all_fail_proc]

    mock_figure_instance_all_fail_proc.gca.return_value = mock_ax_instance_all_fail_proc
    MockPltFigure.return_value = mock_figure_instance_all_fail_proc
    MockSnsBarplot.return_value = MagicMock()

    mock_load_json_file.side_effect = [sample_analysis_data_list, sample_analysis_data_list]
    mock_group_results.return_value = grouped_sample_analysis_data
    mock_calculate_scores.return_value = {"corpus_A": {}, "corpus_B": {}}

    result = run_comprehensive_report_pipeline("input.json", "advanced_input.json", None, None, "output_dir_all_fail_proc")
 
    assert mock_generate_md.call_count > 0
    mock_save_html.assert_called_once()
    assert result is True
    MockDataFrame.assert_called()
    MockPltFigure.assert_called()
    MockPltClose.assert_called()
    MockSnsBarplot.assert_called()