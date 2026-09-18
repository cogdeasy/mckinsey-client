# Testing notes

Coverage is uneven by accident rather than by design.

- `tests/utils` and `tests/pipelines/data_engineering` are the parts anyone has
  actually maintained. If you change cleansing, these will tell you.
- `tests/pipelines/feature_engineering` covers the promo and calendar nodes
  only. Lags and encoding are untested.
- Model training, evaluation and scoring have no unit tests. The evaluation
  metric helpers are tested; the nodes around them are not.
- The app has no tests.

The fixtures in `tests/conftest.py` are cut from a real weekly extract with the
volumes changed. They therefore encode the client's conventions: four character
store ids, `9` prefixed depots, `99` suffixed test stores, Danish dates,
deposit class C on the drinks line and the 25 per cent VAT rate. A couple of
the cleansing tests pass because of those conventions rather than because the
code is general.

Run everything with:

    make test

Before a delivery, run the pipelines on the sample extract as well. The unit
tests do not catch catalog or parameter mistakes.
