# Plugin Architecture

This directory contains the core components of the plugin system, designed for modularity and extensibility.

## Key Components

### 1. `PluginLoader`

The `PluginLoader` (`plugin_loader.py`) is the cornerstone of the system. It is responsible for discovering and loading all available plugins at runtime.

-   **Discovery:** The loader scans the subdirectories within `src/core/plugins/` (specifically `standard/` and `workflows/`) for `plugin_manifest.json` files.
-   **Loading:** It reads the metadata from each manifest to understand the plugin's properties and entry points.

This mechanism ensures that the system can be extended simply by adding a new plugin in its own directory with a valid manifest, without needing to modify the core application logic.

### 2. Plugin Manifest (`plugin_manifest.json`)

The manifest is a JSON file that acts as the "identity card" for each plugin. It provides essential metadata that the `PluginLoader` uses to register and manage the plugin.

Every plugin **must** have a `plugin_manifest.json` file at its root.

#### Manifest Structure

```json
{
  "manifest_version": "1.0",
  "plugin_name": "UniquePluginName",
  "version": "0.1.0",
  "author": "Author Name",
  "description": "A brief description of what this plugin does.",
  "entry_point": "main.py" 
}
```

-   **`manifest_version`**: The version of the manifest schema itself.
-   **`plugin_name`**: A unique identifier for the plugin.
-   **`version`**: The semantic version of the plugin's code.
-   **`author`**: The author or team responsible for the plugin.
-   **`description`**: A human-readable summary of the plugin's purpose.
-   **`entry_point`**: The main Python file that contains the plugin's implementation (e.g., the class inheriting from `BasePlugin`).

This declarative approach, driven by the manifest, is central to the system's design, promoting loose coupling and clear separation of concerns.