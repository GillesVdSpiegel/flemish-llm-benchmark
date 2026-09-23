# Licence for the dataset

Everything under `items/`, `data/curation/` and `data/items.jsonl`, together with the model
responses in `runs/`, is licensed under
[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

The code (everything else in this repository) is under the MIT licence; see `LICENSE`.

## Attribution

> Flemish-Dutch LLM benchmark (flembench), Gilles (@GillesVdSpiegel), 2026.
> https://github.com/GillesVdSpiegel/flemish-llm-benchmark — CC BY 4.0

## Third-party material

**Word selection** is derived from the prevalence norms of the Dutch Crowdsourcing Project:

> Brysbaert, M., Keuleers, E., Mandera, P., & Stevens, M. (2019). Recognition Times for 54
> Thousand Dutch Words: Data from the Dutch Crowdsourcing Project. *Psychologica Belgica*, 59(1).
> Data: https://osf.io/5fk8d/ — licensed **CC BY-NC 4.0**.

Those norms are **not redistributed** here. This dataset contains only words (which are not
copyrightable) plus our own decisions and meanings. Anyone who wants the prevalence values
downloads them from OSF under their own licence; `scripts/` does this automatically.

**Model responses** in `runs/cache/` were produced by third-party models. Check each provider's
terms before using them for training.

**Model weights** are not included; `config/local_models.yaml` pins them by SHA-256. GEITje-7B-ultra
and ChocoLlama-8B carry CC BY-NC 4.0 terms and were used here for non-commercial research only.
