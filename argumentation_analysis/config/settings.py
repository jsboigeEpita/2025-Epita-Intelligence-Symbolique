# argumentation_analysis/config/settings.py
from pydantic import SecretStr, HttpUrl, Field, DirectoryPath, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pathlib import Path

class OpenAISettings(BaseSettings):
    api_key: Optional[SecretStr] = Field(default="sk-dummy-key-for-testing", alias='OPENAI_API_KEY')
    chat_model_id: str = 'gpt-4o-mini'
    base_url: Optional[HttpUrl] = None
    model_config = SettingsConfigDict(
        env_prefix='OPENAI_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

class AzureOpenAISettings(BaseSettings):
    api_key: Optional[SecretStr] = Field(None, alias='AZURE_OPENAI_API_KEY')
    endpoint: Optional[HttpUrl] = Field(None, alias='AZURE_OPENAI_ENDPOINT')
    deployment_name: Optional[str] = Field(None, alias='AZURE_OPENAI_CHAT_DEPLOYMENT_NAME')
    chat_model_id: str = 'gpt-4o-mini'
    model_config = SettingsConfigDict(
        env_prefix='AZURE_OPENAI_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

class TikaSettings(BaseSettings):
    server_endpoint: HttpUrl = "https://tika.open-webui.myia.io/tika"
    server_timeout: int = 600
    model_config = SettingsConfigDict(env_prefix='TIKA_')

class JinaSettings(BaseSettings):
    reader_prefix: HttpUrl = "https://r.jina.ai/"
    model_config = SettingsConfigDict(env_prefix='JINA_')

class NetworkSettings(BaseSettings):
    breaker_fail_max: int = 5
    breaker_reset_timeout: int = 60
    retry_stop_after_attempt: int = 3
    retry_wait_multiplier: int = 1
    retry_wait_min: int = 2
    retry_wait_max: int = 10
    default_timeout: float = 15.0
    model_config = SettingsConfigDict(env_prefix='NETWORK_')

class UISettings(BaseSettings):
    temp_download_dir: Path = Path("temp_downloads")
    plaintext_extensions: List[str] = [".txt", ".md", ".json", ".xml", ".html", ".css", ".js"]
    model_config = SettingsConfigDict(env_prefix='UI_')

class ServiceManagerSettings(BaseSettings):
    enable_hierarchical: bool = True
    enable_specialized_orchestrators: bool = True
    enable_communication_middleware: bool = True
    max_concurrent_analyses: int = 10
    analysis_timeout: int = 300  # 5 minutes
    auto_cleanup: bool = True
    save_results: bool = True
    results_dir: Path = Path("_temp/service_manager_results")
    data_dir: Path = Path("data")
    default_llm_service_id: str = "openai"
    hierarchical_channel_id: str = "hierarchical_main"
    model_config = SettingsConfigDict(env_prefix='SERVICE_MANAGER_')

class JVMSettings(BaseSettings):
    min_java_version: int = 11
    min_heap_size: str = "256m"
    max_heap_size: str = "2048m"

    # Configuration JDK portable
    jdk_version: str = "17.0.2"
    jdk_build: str = "8"
    jdk_url_template: str = "https://github.com/adoptium/temurin{maj_v}-binaries/releases/download/jdk-{v}%2B{b}/OpenJDK{maj_v}U-jdk_{arch}_{os}_hotspot_{v}_{b_flat}.zip"
    # Configuration des librairies Java (Tweety)
    tweety_version: str = "1.28"
    tweety_libs_dir: Path = Path("libs/tweety")
    native_libs_dir: Path = Path("libs/native")

    azure_openai: AzureOpenAISettings = AzureOpenAISettings()
    model_config = SettingsConfigDict(env_prefix='JVM_')

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Child settings
    openai: OpenAISettings = OpenAISettings()
    tika: TikaSettings = TikaSettings()
    jina: JinaSettings = JinaSettings()
    network: NetworkSettings = NetworkSettings()
    ui: UISettings = UISettings()
    service_manager: ServiceManagerSettings = ServiceManagerSettings()
    jvm: JVMSettings = JVMSettings()

    # App-level settings
    debug_mode: bool = Field(False, alias='DEBUG')
    environment: str = "development"
    passphrase: Optional[SecretStr] = Field(None, alias='TEXT_CONFIG_PASSPHRASE')
    encryption_key: Optional[SecretStr] = Field(None, alias='ENCRYPTION_KEY')
    enable_jvm: bool = Field(True, alias='ENABLE_JVM')
    use_mock_llm: bool = Field(False, alias='USE_MOCK_LLM')
    MOCK_LLM: bool = Field(False, alias='MOCK_LLM')
    libs_dir: Optional[DirectoryPath] = Field(None, alias='LIBS_DIR')
    
    # Derived Paths
    project_root: Path = Path(__file__).resolve().parents[2]

    @computed_field
    @property
    def config_dir(self) -> Path:
        return self.project_root / "argumentation_analysis" / "data"

    @computed_field
    @property
    def config_file_json(self) -> Path:
        return self.config_dir / "extract_sources.json"

    @computed_field
    @property
    def config_file_enc(self) -> Path:
        return self.config_dir / "extract_sources.json.gz.enc"
    
    @computed_field
    @property
    def config_file(self) -> Path:
        # For legacy compatibility, CONFIG_FILE pointed to the encrypted file
        return self.config_file_enc

settings = AppSettings()