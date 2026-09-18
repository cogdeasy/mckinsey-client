# Meridian review app

Streamlit app used in the Thursday review with the Nordfalk category team.

    conda activate meridian
    streamlit run app/meridian_app.py --server.port 8502

It reads the outputs of the kedro pipelines from `data/`, so run the
pipelines first:

    kedro run --pipeline de
    kedro run --pipeline fe
    kedro run --pipeline train
    kedro run --pipeline eval
    kedro run --pipeline scoring

Pages: datakvalitet, prognose, scenarier, modelperformance. Labels and
number formatting are Danish because the app is shown to the client's own
team; the scenario page shows values including VAT, every other page is net.

Paths are duplicated in `components/loaders.py` rather than read from the
kedro catalog, because the app is deployed to the analytics VM on its own.
