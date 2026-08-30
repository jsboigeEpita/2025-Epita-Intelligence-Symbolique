# argumentation_analysis/config/settings.py
from pydantic import SecretStr, HttpUrl, Field, DirectoryPath, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pathlib import Path


class OpenAISettings(BaseSettings):
    api_key: Optional[SecretStr] = Field(
        default="sk-dummy-key-for-testing", alias="OPENAI_API_KEY"
    )
    chat_model_id: str = "gpt-5.6-luna"
    base_url: Optional[HttpUrl] = None
    model_config = SettingsConfigDict(
        env_prefix="OPENAI_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class AzureOpenAISettings(BaseSettings):
    api_key: Optional[SecretStr] = Field(None, alias="AZURE_OPENAI_API_KEY")
    endpoint: Optional[HttpUrl] = Field(None, alias="AZURE_OPENAI_ENDPOINT")
    deployment_name: Optional[str] = Field(
        None, alias="AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"
    )
    chat_model_id: str = "gpt-5.6-luna"
    model_config = SettingsConfigDict(
        env_prefix="AZURE_OPENAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class TikaSettings(BaseSettings):
    server_endpoint: HttpUrl = "https://tika.open-webui.myia.io/tika"
    server_timeout: int = 600
    model_config = SettingsConfigDict(env_prefix="TIKA_")


class JinaSettings(BaseSettings):
    reader_prefix: HttpUrl = "https://r.jina.ai/"
    model_config = SettingsConfigDict(env_prefix="JINA_")


class NetworkSettings(BaseSettings):
    breaker_fail_max: int = 5
    breaker_reset_timeout: int = 60
    retry_stop_after_attempt: int = 3
    retry_wait_multiplier: int = 1
    retry_wait_min: int = 2
    retry_wait_max: int = 10
    default_timeout: float = (
        90.0  # Increased from 15.0s to 90.0s for gpt-5.6-luna compatibility (D3.1.1)
    )
    model_config = SettingsConfigDict(env_prefix="NETWORK_")


class UISettings(BaseSettings):
    temp_download_dir: Path = Path("temp_downloads")
    plaintext_extensions: List[str] = [
        ".txt",
        ".md",
        ".json",
        ".xml",
        ".html",
        ".css",
        ".js",
    ]
    model_config = SettingsConfigDict(env_prefix="UI_")


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
    default_model_id: str = "gpt-5.6-luna"
    hierarchical_channel_id: str = "hierarchical_main"
    model_config = SettingsConfigDict(env_prefix="SERVICE_MANAGER_")


class JVMSettings(BaseSettings):
    # 15, not 11, and not 17. Measured 2026-08-24 across the 1.28 fat jar, the
    # 1.29 fat jar and a 1.31 Maven assembly: the highest class-file major
    # outside META-INF/versions/ is 59 = Java 15 in all three, carried by a real
    # class (org/tweetyproject/action/grounding/VarsNeqRequirement), and 120 of
    # the 129 Tweety classes this repo names by FQCN sit above major 55. A JDK 11
    # therefore passes this floor and then fails EVERY class load -- silently, as
    # skips rather than errors. 17 would also be true today but would over-claim:
    # the library asks for 15, and pinning the floor to what we happen to ship
    # would make the next JDK bump look like a requirement change.
    #
    # This is a latent trap, not the CI blocker: jvm_setup ignores JAVA_HOME and
    # provisions its own portable JDK 17, so the Java 11 from setup-java never
    # reaches the JVM. It bites whoever drops a JDK 11 into portable_jdk/.
    min_java_version: int = 15
    min_heap_size: str = "256m"
    max_heap_size: str = "2048m"

    # Configuration JDK portable
    jdk_version: str = "17.0.12"
    jdk_build: str = "7"
    jdk_url_template: str = (
        "https://github.com/adoptium/temurin{maj_v}-binaries/releases/download/jdk-{v}%2B{b}/OpenJDK{maj_v}U-jdk_{arch}_{os}_hotspot_{v}_{b_flat}.zip"
    )
    # Configuration des librairies Java (Tweety)
    tweety_version: str = "1.31"
    tweety_libs_dir: Path = Path("libs/tweety")
    # #1874 / #1959: modules held at a version other than tweety_version, as
    # "groupId:artifactId:version" separated by commas. Empty by default because
    # a pin is only needed when the target version REMOVES a CLASS a consumer
    # names. The 1.31 bump (handled here, see #1959 R896 rework) resolved every
    # name the production code resolves through ``jpype.JClass`` in
    # ``bipolar_handler.__init__``:
    #   - BArgument   -> dung.syntax.Argument
    #   - BinaryAttack / Attack -> dung.syntax.Attack
    #   - BinarySupport -> bipolar.syntax.Support(Argument, Argument)
    #   - EvidentialArgumentationFramework /
    #     NecessityArgumentationFramework -> BipolarArgumentationFramework
    #     parameterised by Support.Type.EVIDENTIAL / NECESSITY.
    # Hence the previous ``bipolar:1.30`` pin is no longer needed at 1.31 -- the
    # capability is preserved by migration, not by pinning back. A pin would
    # only be required if a future bump REMOVES something we expose.
    tweety_pinned_modules: str = ""
    # Modules kept OUT of the assembly, as "groupId:artifactId" separated by
    # commas. Default exclusions under #1874 / #1959:
    #   - ``org.tweetyproject:web``         (Servlet/JSP UI; never imported here)
    #   - ``gurobi:gurobi``                  (commercial solver licence; 404 on Central)
    #   - ``isula:isula``                    (iSAT research licence; 404 on Central)
    #   - ``jspf:core``                      (Java Solver Pathfinding; 404 on Central)
    # Excluding these shrinks the closure from 155 to 74 jars, all 74 served
    # by Maven Central, so ``tweetyproject.org/mvn/`` is no longer a required
    # host (it was the SPOF #1874 treated).
    tweety_excluded_modules: str = (
        "org.tweetyproject:web,gurobi:gurobi,isula:isula,jspf:core"
    )
    native_libs_dir: Path = Path("libs/native")

    # External tools
    ext_tools_dir: Path = Path("ext_tools")
    clingo_version: str = "5.4.0"

    azure_openai: AzureOpenAISettings = AzureOpenAISettings()
    # env_file is not inherited: without it JVM_TWEETY_PINNED_MODULES set in
    # .env -- the channel this project documents -- silently resolves to the
    # empty string, parse_pin_spec('') returns {} without complaint, and the
    # assembly proceeds unpinned. The pin is then lost one layer below where
    # parse_pin_spec promises never to drop one. Measured on #1883 review.
    model_config = SettingsConfigDict(
        env_prefix="JVM_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Child settings
    openai: OpenAISettings = OpenAISettings()
    tika: TikaSettings = TikaSettings()
    jina: JinaSettings = JinaSettings()
    network: NetworkSettings = NetworkSettings()
    ui: UISettings = UISettings()
    service_manager: ServiceManagerSettings = ServiceManagerSettings()
    jvm: JVMSettings = JVMSettings()

    # App-level settings
    debug_mode: bool = Field(False, alias="DEBUG")
    environment: str = "development"
    passphrase: Optional[SecretStr] = Field(None, alias="TEXT_CONFIG_PASSPHRASE")
    encryption_key: Optional[SecretStr] = Field(None, alias="ENCRYPTION_KEY")
    enable_jvm: bool = Field(True, alias="ENABLE_JVM")
    use_mock_llm: bool = Field(False, alias="USE_MOCK_LLM")
    MOCK_LLM: bool = Field(False, alias="MOCK_LLM")
    libs_dir: Optional[DirectoryPath] = Field(None, alias="LIBS_DIR")

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
