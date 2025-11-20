# Contributing to ConfigStream

We welcome contributions! Please follow these guidelines.

## Getting Started

1. Fork the repository.
2. Clone your fork: `git clone https://github.com/yourusername/configstream.git`
3. Install dependencies: `pip install -e ".[dev]"`
4. Create a branch: `git checkout -b feature/awesome-feature`

## Development

- Follow PEP 8.
- Run tests: `pytest`
- Format code: `black .`
- Check types: `mypy .`

## Project Suggestions

We are looking for help with the following features (No AI or DevOps please):

- **Protocol Support**: Add WireGuard generic config parsing.
- **Localization**: Translate README and UI to multiple languages (Chinese, Russian, Farsi).
- **GUI**: Create a desktop dashboard using Electron or Tauri.
- **Performance**: Optimize JSON serialization with Rust extensions (e.g. `orjson` advanced usage).
- **Accessibility**: Improve ARIA labels and keyboard navigation in the Web UI.
- **Mobile**: Create a React Native or Flutter companion app for subscription management.
- **Database**: Migrate from JSON/SQLite to PostgreSQL for high-scale deployments.
- **Filters**: Implement advanced regex-based exclusion rules for proxies.
- **Themes**: Add more color themes to the frontend.
- **Documentation**: Create a video tutorial or comprehensive wiki.

## Submitting Changes

1. Push your branch.
2. Open a Pull Request.
3. Ensure CI passes.
